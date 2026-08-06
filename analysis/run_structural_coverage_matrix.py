"""Full cross-isoform structural evidence coverage matrix, using the
already-computed alpha/beta/gamma/delta matching results
(docs/governance/STAGE_D_PI3KG_MATCHING_A4.json,
STAGE_D_ALL_ISOFORMS_MATCHING_A4.json) plus the raw per-compound match
sets recovered from the persisted StructuralEvidenceRecord files.

Computes, for the 1,267-compound modeling set:
  - exactly-N-isoform structural overlap (N=1,2,3,4)
  - pairwise usable-comparison counts (compounds with evidence in BOTH
    isoforms of a given pair -- needed for a genuine alpha-vs-X structural
    comparison)
  - scaffold diversity of the structurally-supported population

A4 is read-only throughout.
"""

from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, "src")

from orthosteric.eval._target_construction import build_selectivity_targets

A4 = Path("data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)
accepted = [r for r in recs if not r.get("exclusion_reason")]
targets = build_selectivity_targets(recs)
target_ids = {t.compound_id for t in targets}

# scaffold_family_id per compound (first-seen, deterministic)
scaffold_of: dict[str, str] = {}
for r in sorted(accepted, key=lambda r: str(r.get("source_record_id", ""))):
    ik = r.get("inchikey")
    fam = r.get("scaffold_family_id")
    if ik and fam and ik not in scaffold_of:
        scaffold_of[ik] = str(fam)

# ── Per-isoform matched-compound sets (from persisted evidence records) ────
def matched_set(path: str) -> set[str]:
    if not Path(path).exists():
        return set()
    records = json.loads(Path(path).read_text())
    return {r["compound_id"] for r in records if r.get("evidence_class") == "experimental_complex"}

matched = {
    "PI3Kalpha": matched_set("data/structural_evidence/pik3ca_experimental_complex_A4.json"),
    "PI3Kbeta": set(),  # 0 human PDB entries; verified, not a search failure
    "PI3Kgamma": matched_set("data/structural_evidence/pi3kg_experimental_complex_A4.json"),
    "PI3Kdelta": matched_set("data/structural_evidence/pik3cd_experimental_complex_A4.json"),
}
overlap = {iso: s & target_ids for iso, s in matched.items()}

print("=== Per-isoform coverage table ===")
for iso in ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"):
    print(f"  {iso}: matched_corpus={len(matched[iso])}  overlap_with_modeling_set={len(overlap[iso])}")

# ── Exactly-N-isoform breakdown ──────────────────────────────────────────────
n_isoforms_with_evidence: Counter[int] = Counter()
per_compound_isoforms: dict[str, set[str]] = {}
for iso, s in overlap.items():
    for ik in s:
        per_compound_isoforms.setdefault(ik, set()).add(iso)
for ik in target_ids:
    n = len(per_compound_isoforms.get(ik, set()))
    n_isoforms_with_evidence[n] += 1

print("\n=== Exactly-N-isoform structural coverage (of 1,267 modeling compounds) ===")
for n in range(5):
    print(f"  exactly {n} isoform(s): {n_isoforms_with_evidence[n]}")
print(f"  at least 1: {sum(v for k, v in n_isoforms_with_evidence.items() if k >= 1)}")

# ── Pairwise usable-comparison counts ────────────────────────────────────────
print("\n=== Pairwise structural comparison usability (BOTH isoforms present) ===")
isoforms = ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")
pairwise = {}
for a, b in combinations(isoforms, 2):
    both = overlap[a] & overlap[b]
    pairwise[f"{a}-{b}"] = len(both)
    print(f"  {a} & {b}: {len(both)}")

# ── Scaffold diversity of the structurally-supported population ────────────
any_overlap = set().union(*overlap.values())
scaffolds_supported = {scaffold_of.get(ik) for ik in any_overlap if scaffold_of.get(ik)}
print(f"\n=== Scaffold diversity of the {len(any_overlap)}-compound structurally-supported population ===")
print(f"  distinct scaffold families: {len(scaffolds_supported)}")
print(f"  compounds per scaffold (median): "
      f"{sorted(Counter(scaffold_of.get(ik) for ik in any_overlap).values())}")

# ── GDR-006 AlphaFold fallback assessment ────────────────────────────────────
print("\n=== GDR-006 AlphaFold fallback assessment ===")
print("GDR-006 (accepted) governs HOW AlphaFold-sourced structural features")
print("are treated ONCE THEY EXIST (Option B: include with is_alphafold")
print("indicator) -- it does not itself provide compound-level structural")
print("evidence. AlphaFold predicts one static, ligand-agnostic receptor")
print("structure per UniProt accession; it does NOT predict where a specific")
print("compound binds. Deriving compound-specific structural evidence from")
print("an AlphaFold receptor requires DOCKING -- and per")
print("docs/governance/STAGE_D_STRUCTURAL_EVIDENCE_STATE.md: 'All docking")
print("parameters are RULE_MISSING' (not governed; a GDR is explicitly")
print("required before any docking proceeds). Therefore GDR-006 cannot, by")
print("itself, increase COMPOUND-level structural coverage this session --")
print("only a per-isoform receptor-existence flag, which (as previously")
print("noted) is constant across all compounds for a given isoform and adds")
print("no compound-specific signal to the ligand-keyed model interface.")
print("\nOutcome: C -- even considering the governed AlphaFold fallback,")
print("compound-level structural evidence remains insufficient, and this is")
print("a hard architectural fact (docking ungoverned), not a search gap.")

out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "n_modeling_compounds": len(target_ids),
    "per_isoform": {iso: {"matched_corpus": len(matched[iso]), "overlap_modeling_set": len(overlap[iso])} for iso in isoforms},
    "exactly_n_isoform_overlap": {str(k): v for k, v in sorted(n_isoforms_with_evidence.items())},
    "pairwise_usable_comparisons": pairwise,
    "n_any_isoform_overlap": len(any_overlap),
    "n_scaffold_families_supported": len(scaffolds_supported),
    "alphafold_fallback_outcome": "C",
    "alphafold_fallback_rationale": (
        "GDR-006 governs treatment of AlphaFold features once they exist; it "
        "does not provide compound-specific evidence. AlphaFold gives one "
        "ligand-agnostic receptor per isoform; deriving compound-level "
        "evidence requires docking, which is RULE_MISSING (ungoverned) per "
        "docs/governance/STAGE_D_STRUCTURAL_EVIDENCE_STATE.md."
    ),
}
Path("docs/governance/STAGE_D_COVERAGE_MATRIX_A4.json").write_text(json.dumps(out, indent=2))
print(f"\nWrote docs/governance/STAGE_D_COVERAGE_MATRIX_A4.json (A4 not modified)")
