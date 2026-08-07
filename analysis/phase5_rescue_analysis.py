"""Phase 5 -- Rescue analysis (SS13.1, SS13.2), corrected.

Bug fixed from the first run: SS13.2's counts were incremented once per
(LOST record, losing_isoform) PAIR -- since a single LOST_AT_MAPPED_POSITION
record can have more than one losing isoform out of the four, this
produced fractions above 100% when divided by the RECORD count alone.
Fixed by making the denominator match the numerator's own granularity:
every count and fraction below is reported per (record, losing_isoform)
pair, consistently.

SS13.1 (same-position chemical rescue): per the mandate's own correction,
this is expected to be EXACTLY zero, not just empirically near-zero --
Representation 1's key already excludes residue identity, so a
LOST_AT_MAPPED_POSITION record means occupancy=0 for that
(interaction_type, canonical_position) in the losing isoform, meaning
there is, by construction, no observed interaction there to derive a
Representation-2 functional class from. A Representation-2 bin can only
list a canonical position in `contributing_canonical_positions` if an
interaction was actually observed there. This script computes it anyway
(never assert a result without checking) to confirm the mathematical
necessity empirically and catch any implementation bug that would
produce a nonzero count.

SS13.2 (pocket-level chemical-role redundancy): does the LOSING isoform
show the same interaction_type fulfilled by Representation 2 SOMEWHERE
ELSE in its own pocket (a different, non-homologous canonical position),
even though it is absent at the specific position where the OTHER
isoform has it? Reported at two evidentiary strictness levels:
  LOOSE:   same interaction_type present anywhere else in that isoform's
           Rep2 results for this compound.
  STRICT:  same interaction_type AND the SAME residue_functional_class
           the comparison isoform shows at that canonical position.
Never combined with SS13.1.

SS20 (gamma specificity-pocket carve-out): every pair touching the
Gate-0-verified specificity-pocket anchors (alpha-referenced canonical
positions 780 = Trp780, 772 = Met772) is tagged, and gamma's
contribution to SS13.2 in that specific region is broken out separately
from alpha/delta rather than pooled -- because 6AUD's Gate-1 failure was
diagnosed to incompleteness exactly in that region.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence")

#: Gate-0-verified specificity-pocket anchors, alpha-referenced (see
#: docs/governance/GATE0_CORRESPONDENCE_VALIDATION.json).
_SPECIFICITY_POCKET_CANONICAL_POSITIONS = frozenset({780, 772})


def load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text())


def _residue_functional_class_at_position(
    rep2_records: list[dict], canonical_position: int, interaction_type: str
) -> set[str]:
    """Which residue_functional_class(es) does isoform's Rep2 output
    associate with this canonical position for this interaction type?
    Empty set if none (position not observed for this type in Rep2)."""
    out = set()
    for r in rep2_records:
        if r["interaction_type"] != interaction_type:
            continue
        if canonical_position in r["contributing_canonical_positions"]:
            out.add(r["residue_functional_class"])
    return out


def analyze_dataset(label: str, residue_comp_file: str, rep2_file: str) -> dict:
    residue_comp = load(residue_comp_file)
    rep2 = load(rep2_file)

    same_position_rescues = 0
    lost_records_examined = 0
    lost_pairs_examined = 0  # (record, losing_isoform) pairs -- the correct denominator
    loose_pocket_redundancies = 0
    strict_pocket_redundancies = 0
    no_redundancy = 0
    examples: list[dict] = []

    # SS20: gamma-specific breakdown, specificity-pocket region only.
    specificity_pocket_pairs_by_isoform: dict[str, int] = defaultdict(int)
    specificity_pocket_loose_redundancy_by_isoform: dict[str, int] = defaultdict(int)

    for cid, records in residue_comp.items():
        rep2_by_iso = rep2.get(cid, {})
        for rec in records:
            if rec["pattern"] != "lost_at_mapped_position":
                continue
            lost_records_examined += 1
            interaction_type = rec["interaction_type"]
            canonical_position = rec["canonical_position"]
            occ_by_iso = rec["occupancy_by_isoform"]
            losing_isoforms = [iso for iso, occ in occ_by_iso.items() if occ == 0.0]
            winning_isoforms = [iso for iso, occ in occ_by_iso.items() if occ > 0.0]
            if not losing_isoforms or not winning_isoforms or canonical_position is None:
                continue

            winning_classes: set[str] = set()
            for wiso in winning_isoforms:
                winning_classes |= _residue_functional_class_at_position(
                    rep2_by_iso.get(wiso, []), canonical_position, interaction_type
                )

            touches_specificity_pocket = (
                canonical_position in _SPECIFICITY_POCKET_CANONICAL_POSITIONS
            )

            for liso in losing_isoforms:
                lost_pairs_examined += 1
                liso_rep2 = rep2_by_iso.get(liso, [])

                classes_at_this_position_in_loser = _residue_functional_class_at_position(
                    liso_rep2, canonical_position, interaction_type
                )
                if classes_at_this_position_in_loser:
                    same_position_rescues += 1
                    if len(examples) < 5:
                        examples.append(
                            {
                                "compound_id": cid,
                                "interaction_type": interaction_type,
                                "canonical_position": canonical_position,
                                "losing_isoform": liso,
                                "unexpected_classes_found": sorted(
                                    classes_at_this_position_in_loser
                                ),
                                "note": "SS13.1 same-position rescue -- should not occur; investigate",
                            }
                        )

                loose_hit = any(
                    r["interaction_type"] == interaction_type
                    and canonical_position not in r["contributing_canonical_positions"]
                    for r in liso_rep2
                )
                strict_hit = any(
                    r["interaction_type"] == interaction_type
                    and r["residue_functional_class"] in winning_classes
                    and canonical_position not in r["contributing_canonical_positions"]
                    for r in liso_rep2
                )
                if loose_hit:
                    loose_pocket_redundancies += 1
                if strict_hit:
                    strict_pocket_redundancies += 1
                if not loose_hit:
                    no_redundancy += 1

                if touches_specificity_pocket:
                    specificity_pocket_pairs_by_isoform[liso] += 1
                    if loose_hit:
                        specificity_pocket_loose_redundancy_by_isoform[liso] += 1

    n_pairs = max(lost_pairs_examined, 1)
    specificity_pocket_breakdown = {
        iso: {
            "pairs_examined": specificity_pocket_pairs_by_isoform.get(iso, 0),
            "loose_redundancy_hits": specificity_pocket_loose_redundancy_by_isoform.get(iso, 0),
            "loose_redundancy_fraction": (
                round(
                    specificity_pocket_loose_redundancy_by_isoform.get(iso, 0)
                    / specificity_pocket_pairs_by_isoform[iso],
                    4,
                )
                if specificity_pocket_pairs_by_isoform.get(iso, 0) > 0
                else None
            ),
        }
        for iso in ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")
    }

    return {
        "label": label,
        "lost_at_mapped_position_records_examined": lost_records_examined,
        "lost_record_losing_isoform_pairs_examined": lost_pairs_examined,
        "denominator_note": (
            "All SS13.1/SS13.2 counts below are per (LOST record, losing_isoform) "
            "pair, not per record -- a single record can have more than one "
            "losing isoform out of the four. This is the corrected denominator; "
            "an earlier run of this script divided by the record count alone "
            "and produced fractions above 100%, a real bug caught and fixed "
            "before this result was reported."
        ),
        "13_1_same_position_rescue_count": same_position_rescues,
        "13_1_interpretation": (
            "Expected to be exactly 0 by mathematical construction (see module "
            "docstring), not merely empirically rare -- a nonzero count would "
            "indicate an implementation bug, not evidence of chemical rescue."
        ),
        "13_1_examples_if_any": examples,
        "13_2_loose_pocket_redundancy_count": loose_pocket_redundancies,
        "13_2_loose_pocket_redundancy_fraction": round(loose_pocket_redundancies / n_pairs, 4),
        "13_2_strict_pocket_redundancy_count": strict_pocket_redundancies,
        "13_2_strict_pocket_redundancy_fraction": round(strict_pocket_redundancies / n_pairs, 4),
        "13_2_no_redundancy_count": no_redundancy,
        "13_2_no_redundancy_fraction": round(no_redundancy / n_pairs, 4),
        "13_2_interpretation": (
            "LOOSE: the losing isoform expresses the SAME interaction_type "
            "somewhere else in its pocket for this compound, regardless of "
            "residue functional class. STRICT: same interaction_type AND "
            "the same residue_functional_class the winning isoform shows at "
            "the original position. Neither establishes conservation of a "
            "SPECIFIC determinant -- both describe pocket-level functional "
            "redundancy, distinct from same-position rescue (SS13.1)."
        ),
        "ss20_specificity_pocket_breakdown_by_isoform": specificity_pocket_breakdown,
        "ss20_note": (
            "Canonical positions 780 (Trp780) and 772 (Met772), Gate-0-verified "
            "specificity-pocket anchors. Gamma's Gate-1 self-docking FAILED and "
            "was diagnosed to incompleteness in exactly this region of 6AUD -- "
            "its row above must be read with that evidentiary caveat and never "
            "pooled with alpha/delta's rows for any claim about this region."
        ),
    }


results_24 = analyze_dataset(
    "24-compound", "residue_level_comparative_24_rebuilt.json", "representation2_24.json"
)
results_50 = analyze_dataset(
    "50-compound", "residue_level_comparative_50_rebuilt.json", "representation2_50.json"
)

out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/PHASE5_RESCUE_ANALYSIS.json")
out_path.write_text(json.dumps({"24_compound": results_24, "50_compound": results_50}, indent=2))

for r in (results_24, results_50):
    print(f"\n=== {r['label']} ===")
    print(
        f"LOST records: {r['lost_at_mapped_position_records_examined']}, "
        f"record x losing-isoform pairs: {r['lost_record_losing_isoform_pairs_examined']}"
    )
    print(f"SS13.1 same-position rescue: {r['13_1_same_position_rescue_count']} (expect 0)")
    print(
        f"SS13.2 LOOSE redundancy: {r['13_2_loose_pocket_redundancy_count']} "
        f"({100 * r['13_2_loose_pocket_redundancy_fraction']:.1f}%)"
    )
    print(
        f"SS13.2 STRICT redundancy: {r['13_2_strict_pocket_redundancy_count']} "
        f"({100 * r['13_2_strict_pocket_redundancy_fraction']:.1f}%)"
    )
    print(
        f"No redundancy: {r['13_2_no_redundancy_count']} "
        f"({100 * r['13_2_no_redundancy_fraction']:.1f}%)"
    )
    print("Specificity-pocket breakdown by isoform:")
    for iso, d in r["ss20_specificity_pocket_breakdown_by_isoform"].items():
        print(f"    {iso}: {d}")

print(f"\nWrote {out_path}")
