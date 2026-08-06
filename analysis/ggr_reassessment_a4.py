"""GGR-002a/002b/010 recomputation on Activity Snapshot A4, under the
Project-Owner-approved GDR-010/011/012/013/014 policies.

Uses ONLY orthosteric.data.comparability, orthosteric.data.mmp_candidates,
and orthosteric.data.noise_floor -- the governed modules -- never ad-hoc
inline key construction or aggregation. This supersedes the prior version
of this script, which built its own last-write-wins panel index; that
defect is fixed by GDR-013's replicate_aggregation module, now used here.

This is ANALYSIS / not governed pipeline code in itself (it reads A4 and
writes a report; it does not decide new policy). No MMP transformation
rule beyond GDR-012's EXPLORATORY_BEMIS_MURCKO classification, no switch-
magnitude multiplier, and no dual-inhibitor inclusion rule is invented
here. A4 is read-only throughout; this script does not modify it.
"""

from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "src")

from orthosteric.data.mmp_candidates import generate_exploratory_scaffold_pairs
from orthosteric.data.noise_floor import compute_isoform_noise_floors, switch_magnitude_multiplier_status
from orthosteric.data.replicate_aggregation import ReplicateType, aggregate_records_by_cell

A4 = Path("data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)
acc = [r for r in recs if not r.get("exclusion_reason")]

# ══════════════════════════════════════════════════════════════════════════════
# GGR-002a -- exploratory scaffold-pair candidates (GDR-012)
# ══════════════════════════════════════════════════════════════════════════════
print(f"{'=' * 70}\nGGR-002a (GDR-012)\n{'=' * 70}")

scaffold_report = generate_exploratory_scaffold_pairs(acc)

print("GOVERNANCE STATUS (GDR-012, accepted): every candidate below carries")
print("evidence_class=EXPLORATORY_BEMIS_MURCKO. This is NOT matched molecular")
print("pair (MMP) evidence -- see GDR-012 for the exact reasons why.")
print()
print("CORPUS-DERIVED OBSERVATION (deterministic aggregation, GDR-013):")
print(f"  Same-scaffold, same-C1-panel, complete-4-isoform pairs examined: "
      f"{scaffold_report.n_pairs_examined}")
print(f"  Pairs with >=1 isoform showing an alpha-vs-X selectivity SIGN change: "
      f"{scaffold_report.n_sign_flip_candidates}")
print(f"  Distinct studies (study_id) contributing such pairs: "
      f"{scaffold_report.n_studies_involved}")
print(f"  Compounds excluded (censored/unclassified required-isoform cell, "
      f"GDR-012 sec 3.3): {scaffold_report.n_compounds_excluded_censored_required_isoform}")

sigma_basis_counts = Counter(c.sigma_diff_basis for c in scaffold_report.candidates)
print(f"\n  sigma_diff basis used for magnitude_over_sigma (fallback order, "
      f"never invented): {dict(sigma_basis_counts)}")

ratios = [c.magnitude_over_sigma for c in scaffold_report.candidates if c.magnitude_over_sigma]
if ratios:
    below_2 = sum(1 for r in ratios if r < 2)
    below_3 = sum(1 for r in ratios if r < 3)
    print(f"  Of {len(ratios)} candidates with a usable sigma_diff reference:")
    print(f"    magnitude < 2x sigma_diff: {below_2} ({100*below_2/len(ratios):.1f}%)")
    print(f"    magnitude < 3x sigma_diff: {below_3} ({100*below_3/len(ratios):.1f}%)")
    print(f"  (descriptive only -- neither 2x nor 3x is a chosen governance threshold)")

print(f"\n  switch_magnitude_multiplier_status(): {switch_magnitude_multiplier_status()}")

ggr002a_status = "GDR_REQUIRED"
print(f"\nGGR-002a = {ggr002a_status}")
print("  Rationale: candidate pairs are now deterministic and provenance-preserving")
print("  (GDR-013), and explicitly classified EXPLORATORY_BEMIS_MURCKO, not MMP")
print("  (GDR-012). No accepted GDR defines a true MMP transformation or a switch-")
print("  magnitude multiplier -- both remain explicit Project Owner decisions.")

# ══════════════════════════════════════════════════════════════════════════════
# GGR-002b -- per-isoform / per-isoform-pair noise floor (GDR-013)
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}\nGGR-002b (GDR-013)\n{'=' * 70}")

cells = aggregate_records_by_cell(acc)
n_true = sum(1 for c in cells.values() if c.replicate_type is ReplicateType.TRUE_REPLICATE)
n_cross = sum(1 for c in cells.values() if c.replicate_type is ReplicateType.CROSS_ASSAY)
print(f"C1_PRIMARY cells with >=2 exact obs -- TRUE_REPLICATE: {n_true}, CROSS_ASSAY: {n_cross}")

per_iso_report = {}
for iso, floor in compute_isoform_noise_floors(cells).items():
    per_iso_report[iso] = floor
    print(f"\n  {iso}:")
    print(f"    TRUE_REPLICATE:  n={floor.n_true_replicate_groups:4}  "
          f"median sigma={floor.sigma_true_replicate}")
    print(f"    CROSS_ASSAY:     n={floor.n_cross_assay_groups:4}  "
          f"median sigma={floor.sigma_cross_assay}")
    print(f"    pooled (reference only, NOT recommended): n={floor.n_pooled_groups:4}  "
          f"median sigma={floor.sigma_pooled}")

pair_floors = scaffold_report.isoform_pair_noise_floors
print(f"\n  Per-isoform-pair sigma_diff (sqrt-sum-of-squares, independence assumed):")
for (a, b), pf in pair_floors.items():
    print(f"    ({a}, {b}): true_replicate={pf.sigma_diff_true_replicate}  "
          f"cross_assay={pf.sigma_diff_cross_assay}  pooled={pf.sigma_diff_pooled}")

ggr002b_status = "GDR_REQUIRED"
print(f"\nGGR-002b = {ggr002b_status}")
print("  Rationale: per-isoform, per-replicate-type noise statistics are now")
print("  corpus-derived, deterministic, and reproducible (GDR-013). No accepted")
print("  GDR specifies which figure (if any) becomes a downstream noise-floor")
print("  multiplier for a specific consumer (e.g. a loss-function scale).")

# ══════════════════════════════════════════════════════════════════════════════
# GGR-010 -- dual PI3K/mTOR census (GDR-014: evidence gap, not a hard gate)
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}\nGGR-010 (GDR-014)\n{'=' * 70}")
print("mTOR ChEMBL target: NOT ACQUIRED. Activity Snapshot A4 contains no")
print("mTOR activity records. Per GDR-014 (accepted): this is a documented")
print("evidence gap, explicitly scoped OUT of Model Generation 1 eligibility --")
print("not a hard training gate. No pathway-, docking-, structural-similarity-,")
print("or model-based inference substitutes for direct mTOR activity evidence.")
print(f"\nGGR-010 = CORPUS_INSUFFICIENT (evidence gap, non-blocking per GDR-014)")

# ── Write machine-readable summary ────────────────────────────────────────────
out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "governance": {
        "ggr002a_gdr": "GDR-012",
        "ggr002b_gdr": "GDR-013",
        "ggr010_gdr": "GDR-014",
    },
    "ggr002a": {
        "status": ggr002a_status,
        "evidence_class": "EXPLORATORY_BEMIS_MURCKO",
        "n_pairs_examined": scaffold_report.n_pairs_examined,
        "n_sign_flip_candidates": scaffold_report.n_sign_flip_candidates,
        "n_studies_involved": scaffold_report.n_studies_involved,
        "n_compounds_excluded_censored_required_isoform":
            scaffold_report.n_compounds_excluded_censored_required_isoform,
        "switch_magnitude_multiplier_status": switch_magnitude_multiplier_status(),
    },
    "ggr002b": {
        "status": ggr002b_status,
        "n_true_replicate_cells": n_true,
        "n_cross_assay_cells": n_cross,
        "per_isoform": {
            iso: {
                "n_true_replicate_groups": f.n_true_replicate_groups,
                "sigma_true_replicate": f.sigma_true_replicate,
                "n_cross_assay_groups": f.n_cross_assay_groups,
                "sigma_cross_assay": f.sigma_cross_assay,
            }
            for iso, f in per_iso_report.items()
        },
        "per_isoform_pair_sigma_diff": {
            f"{a}_{b}": {
                "true_replicate": pf.sigma_diff_true_replicate,
                "cross_assay": pf.sigma_diff_cross_assay,
                "pooled_reference_only": pf.sigma_diff_pooled,
            }
            for (a, b), pf in pair_floors.items()
        },
    },
    "ggr010": {
        "status": "CORPUS_INSUFFICIENT",
        "scope": "evidence_gap_non_blocking_per_gdr014",
        "mtor_records": 0,
    },
}
(A4 / "ggr_reassessment.json").write_text(json.dumps(out, indent=2))
print(f"\nWrote {A4}/ggr_reassessment.json (A4 itself not modified)")
