"""GATE 0 — Verify residue correspondence against known biological anchors.

Mandatory, blocking, per the execution mandate. Uses real literature-known
anchor residues (checked via web search this session, citations in the
final report) to test whether pocket._sequence_correspondence's
Biopython BLOSUM62 global alignment places biologically equivalent
residues in correspondence with each other -- BEFORE that table is
trusted for any Gate 1-5 comparative interpretation.

Known anchors (numbering as deposited in the actual crystal structures
used by this project, verified against the real PDB files, not assumed):
  - Specificity-pocket Trp/Met pair: alpha Trp780/Met772 (project's own
    Charter + confirmed in structural-biology literature this session);
    delta Trp760/Met752 (confirmed this session via literature search).
  - Hinge valine (near-universal PI3K inhibitor H-bond anchor): delta
    Val828, gamma Val882 (both confirmed this session via literature
    search). Alpha's hinge valine number is NOT hard-coded here --
    it is determined empirically by querying the correspondence table
    itself (alpha is the reference isoform) and independently verified
    by checking the residue identity at the mapped position in the real
    8EXL sequence.

A4 is not touched. No new docking. Read-only analysis of already-built
infrastructure and already-downloaded receptor structures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

from orthosteric.pocket._sequence_correspondence import (
    build_correspondence_table,
    extract_sequence_from_pdb,
)

RECEPTOR_DIR = Path("/home/ubuntu/docking_pilot/receptors")
RECEPTOR_PDB_PATHS = {
    "PI3Kalpha": RECEPTOR_DIR / "8EXL.pdb",
    "PI3Kbeta": RECEPTOR_DIR / "AF-P42338.pdb",
    "PI3Kgamma": RECEPTOR_DIR / "6AUD.pdb",
    "PI3Kdelta": RECEPTOR_DIR / "6PYR.pdb",
}

print("=== GATE 0: Residue correspondence validation against known anchors ===\n")

print("--- Chain/sequence extraction sanity check ---")
sequences = {}
for iso, path in RECEPTOR_PDB_PATHS.items():
    seq = extract_sequence_from_pdb(path)
    sequences[iso] = seq
    first_resnum, first_chain, _ = seq[0]
    last_resnum, last_chain, _ = seq[-1]
    print(f"  {iso}: {len(seq)} residues extracted, chain {first_chain}, "
          f"range {first_resnum}-{last_resnum}")

print("\n--- Rebuilding correspondence table fresh ---")
table = build_correspondence_table(RECEPTOR_PDB_PATHS, reference_isoform="PI3Kalpha")
fresh_hash = table.content_sha256()
print(f"  Fresh content_sha256: {fresh_hash}")

committed_path = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/residue_correspondence_table.json")
committed = {}
if committed_path.exists():
    committed = json.loads(committed_path.read_text())
    committed_hash = committed.get("content_sha256")
    print(f"  Committed content_sha256: {committed_hash}")
    print(f"  MATCH (table is reproducible, not silently drifted): {fresh_hash == committed_hash}")
else:
    print("  No committed table found to compare against.")


def residue_at(isoform: str, resnum: int) -> str | None:
    for num, _chain, aa in sequences[isoform]:
        if num == resnum:
            return aa
    return None


_ONE_TO_THREE = {
    "W": "TRP", "M": "MET", "V": "VAL", "F": "PHE", "Y": "TYR",
    "L": "LEU", "I": "ILE",
}


def describe(aa: str | None) -> str:
    if aa is None:
        return "NOT IN CRYSTALLIZED RANGE"
    return f"{_ONE_TO_THREE.get(aa, aa)} ({aa})"


print("\n--- Anchor verification ---")
results = []

alpha_trp780 = residue_at("PI3Kalpha", 780)
delta_via_table = table.lookup("PI3Kdelta", 780)
delta_actual_at_mapped = residue_at("PI3Kdelta", delta_via_table) if delta_via_table else None
delta_known_anchor = residue_at("PI3Kdelta", 760)
print("\nAnchor 1 -- specificity-pocket Trp (alpha Trp780 vs delta Trp760):")
print(f"  alpha[780] = {describe(alpha_trp780)} (expect TRP)")
print(f"  table maps alpha[780] -> delta[{delta_via_table}] = {describe(delta_actual_at_mapped)}")
print(f"  delta's independently known anchor delta[760] = {describe(delta_known_anchor)} (expect TRP)")
plausible_1 = (
    alpha_trp780 == "W" and delta_actual_at_mapped == "W" and delta_via_table == 760
)
print(f"  Exact match to known anchor (760) AND residue identity TRP->TRP: {plausible_1}")
results.append(("alpha Trp780", "delta (mapped)", "sequence_alignment_v1_provisional",
                 alpha_trp780 == "W" and delta_actual_at_mapped == "W", plausible_1))

alpha_met772 = residue_at("PI3Kalpha", 772)
delta_via_table_2 = table.lookup("PI3Kdelta", 772)
delta_actual_at_mapped_2 = residue_at("PI3Kdelta", delta_via_table_2) if delta_via_table_2 else None
delta_known_anchor_2 = residue_at("PI3Kdelta", 752)
print("\nAnchor 2 -- specificity-pocket Met (alpha Met772 vs delta Met752):")
print(f"  alpha[772] = {describe(alpha_met772)} (expect MET)")
print(f"  table maps alpha[772] -> delta[{delta_via_table_2}] = {describe(delta_actual_at_mapped_2)}")
print(f"  delta's independently known anchor delta[752] = {describe(delta_known_anchor_2)} (expect MET)")
plausible_2 = (
    alpha_met772 == "M" and delta_actual_at_mapped_2 == "M" and delta_via_table_2 == 752
)
print(f"  Exact match to known anchor (752) AND residue identity MET->MET: {plausible_2}")
results.append(("alpha Met772", "delta (mapped)", "sequence_alignment_v1_provisional",
                 alpha_met772 == "M" and delta_actual_at_mapped_2 == "M", plausible_2))

print("\nAnchor 3 -- hinge valine (delta Val828 / gamma Val882, alpha number NOT assumed):")
delta_828 = residue_at("PI3Kdelta", 828)
gamma_882 = residue_at("PI3Kgamma", 882)
print(f"  delta[828] = {describe(delta_828)} (expect VAL, independently known)")
print(f"  gamma[882] = {describe(gamma_882)} (expect VAL, independently known)")

alpha_hinge_candidate = None
for alpha_resnum, _, aa in sequences["PI3Kalpha"]:
    if table.lookup("PI3Kdelta", alpha_resnum) == 828:
        alpha_hinge_candidate = alpha_resnum
        break
print(f"  table inversion: alpha position mapping to delta[828] = "
      f"alpha[{alpha_hinge_candidate}] = "
      f"{describe(residue_at('PI3Kalpha', alpha_hinge_candidate) if alpha_hinge_candidate else None)}")
if alpha_hinge_candidate:
    gamma_via_alpha = table.lookup("PI3Kgamma", alpha_hinge_candidate)
    print(f"  same alpha position via table -> gamma[{gamma_via_alpha}] = "
          f"{describe(residue_at('PI3Kgamma', gamma_via_alpha) if gamma_via_alpha else None)} "
          f"(expect this to BE or be near gamma's known 882)")
    plausible_3 = (
        delta_828 == "V" and gamma_882 == "V"
        and residue_at("PI3Kalpha", alpha_hinge_candidate) == "V"
        and gamma_via_alpha == 882
    )
else:
    plausible_3 = False
    gamma_via_alpha = None
print(f"  Three-way consistent VAL identity AND gamma position matches known 882: {plausible_3}")
results.append(("delta Val828", f"alpha[{alpha_hinge_candidate}] / gamma (mapped)",
                 "sequence_alignment_v1_provisional", delta_828 == "V", plausible_3))

print("\n--- Summary table ---")
print(f"{'Reference/residue':<20} {'Target':<28} {'Method':<32} {'Plausible?':<12} {'Verified?'}")
for ref, tgt, method, plausible, verified in results:
    print(f"{ref:<20} {tgt:<28} {method:<32} {str(plausible):<12} {verified}")

n_verified = sum(1 for r in results if r[4])
print(f"\n{n_verified}/{len(results)} anchors fully verified.")

out = {
    "fresh_content_sha256": fresh_hash,
    "committed_content_sha256": committed.get("content_sha256"),
    "table_reproducible": fresh_hash == committed.get("content_sha256"),
    "anchors": [
        {"reference": r, "target": t, "method": m, "residue_identity_plausible": p, "fully_verified": v}
        for r, t, m, p, v in results
    ],
    "n_verified": n_verified,
    "n_total": len(results),
    "gate_0_result": "PASS" if n_verified == len(results) else ("PARTIAL" if n_verified > 0 else "FAIL"),
}
out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/GATE0_CORRESPONDENCE_VALIDATION.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nGATE 0 RESULT: {out['gate_0_result']}")
print(f"Wrote {out_path}")
