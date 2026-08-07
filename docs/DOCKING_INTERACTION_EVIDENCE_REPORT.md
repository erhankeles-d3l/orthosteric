# Atom-Residue Interaction Evidence for Cross-Docking — Session Report

**Date:** 2026-08-07
**Snapshot:** A4, `SNAP-05748f6627ea` (unmodified — verified via `git status`/`git diff`, no diff against the committed version)

## DONE (implemented, tested, executed this session)

1. **Salt-bridge chemistry fix.** Renamed `SALT_BRIDGE` → `CHARGED_CONTACT_CANDIDATE` throughout the detector, tests, and output data. The prior label overclaimed: ligand preparation in this pipeline (`RDKit MolFromSmiles` + `AddHs` + ETKDG embedding) performs **no pH-aware protonation step**, so no ligand atom in any processed compound has a verified ionization state. The geometric cutoff (4.0 Å) is **unchanged** — only the label and its documented meaning changed, so counts are identical before/after (verified: 68 `charged_contact_candidate` records, same as the prior 68 `salt_bridge` records). The protein-side classification (ARG/LYS/ASP/GLU) is untouched and reuses the same governed vocabulary SCI1-004 already uses for real PDB structures.
2. **Lint cleanup.** All `PLR2004` magic-number warnings resolved with named constants (`_MIN_RING_ATOMS`, `_MAX_COVALENT_BOND_A`, `_ZERO_VECTOR_EPSILON`, `_PDBQT_ATOM_TYPE_COL_END`). Removed an unused variable. Fixed two `__all__` sort-order issues in `_interaction_fingerprint.py` (created while exporting the shared chemistry vocabulary).
3. **Full validation suite**, all green: 996 tests, ruff clean, ruff-format clean, mypy clean, import-linter 3/3, all 5 custom governance checks pass.
4. **A4 integrity** confirmed via `git status`/`git diff` (no working-tree changes to `data/snapshots/`).

## VALIDATED (passed real-data QC and reproducibility checks)

1. **Full-pipeline reproducibility**: reran the 20-pose interaction analysis independently; all 20 `content_sha256` values identical across runs.
2. **12 Å spatial pre-filter safety**: verified numerically — the largest detector cutoff is 6.0 Å (π-π, cation-π); the pre-filter radius exceeds it by a 6 Å margin, so it cannot exclude a true candidate for any implemented interaction type.
3. **18 unit tests** with hand-computed synthetic coordinates (not just "did it run") — positive and negative cases for every implemented interaction type. Caught and fixed a real geometry bug in the process: the H-bond D-H···A angle was computed with the vertex at the wrong atom (donor heavy atom instead of the hydrogen), which would have silently produced wrong angles on every real pose.

## CORPUS-DERIVED (measured from the real 20-pose pilot, not asserted)

- 20/20 poses produced ≥1 detected interaction.
- Interaction totals across all 20 poses: 21 H-bonds, 6 cation-π, 68 charged-contact candidates, 103 hydrophobic contacts, 3 π-π.
- LY294002 shows a differential H-bond pattern: present in α/β/γ, absent in δ — a specific, testable structural hypothesis (LY294002's morpholine-carbonyl H-bond to the hinge is well documented in the medicinal chemistry literature; its apparent absence in this δ pose is worth checking against the literature, not treated as established here).
- Staurosporine-core shows 2 conserved charged-contact candidates across all four isoforms alongside isoform-differential hydrophobic-contact counts (8/8/10/12 for α/β/γ/δ).

## ENGINEERING CHOICE (implementation decisions, not scientific conclusions)

- Reused SCI1-004's governed residue-classification vocabulary directly (exported as public aliases) rather than reimplementing it — avoids a second, divergent chemistry vocabulary.
- Built a lightweight adapter for Vina/Meeko PDBQT output rather than integrating into the full `StructureRecord`/`PocketResidueSet` formal pipeline, which validates deposition metadata (resolution, deposition year, construct class) that a docking pose doesn't have.
- Geometric cutoffs (H-bond 3.5 Å/120°, charged-contact 4.0 Å, π-π/cation-π 6.0 Å, hydrophobic 4.5 Å) are literature-standard practical approximations (PLIP/Arpeggio-consistent), explicitly labeled as such, not validated physical definitions.
- 12 Å residue-level spatial pre-filter for efficiency (numerically verified safe, see above).
- Halogen bonds, metal coordination, and water-mediated interactions explicitly out of scope this session (documented reasons: no reliable sigma-hole geometry validation set, no retained metals/waters in the stripped docking receptors) — reported as absent capability, never approximated.

## GOVERNANCE REQUIRED (genuine Project Owner decisions, not made here)

None identified this session that weren't already flagged in prior sessions. The cross-isoform residue-correspondence algorithm (SCI1-003) remains the one standing gap requiring a sealed structural-alignment method before residue-identity-level comparison (rather than interaction-type-count-level comparison) is possible — unchanged from before, not newly discovered, not resolved.

## RULE_MISSING (cannot responsibly be inferred)

- Reliable ligand ionization state without a real protonation-state tool (e.g. Dimorphite-DL) wired into the pipeline. This is why `CHARGED_CONTACT_CANDIDATE` exists instead of `SALT_BRIDGE`.
- Cross-isoform residue-position correspondence (SCI1-003's alignment algorithm) — pre-existing gap, not newly discovered.

## What was NOT attempted this session (explicitly, not silently dropped)

Per the instruction's own sequencing ("after the detector is validated on the 20-pose pilot, do NOT immediately dock the entire corpus" / "do not train a large generative model yet"), the following were correctly deferred, not attempted:
- KD-tree/cell-list spatial optimization (the 12 Å pre-filter was verified sufficient for the 20-pose pilot scale; a real algorithmic upgrade is warranted before scaling to hundreds of poses, not before)
- Scaling to the 50–100 compound production pilot
- Correlating docking-derived comparative features against A4's experimental selectivity labels
- Ligand-charge protonation-state tooling integration
- Any reward/penalty weight definition

## NEXT EXECUTABLE STEP (exactly one)

**Wire a real pH-aware ligand-protonation step (e.g. Dimorphite-DL, a lightweight, already-pip-installable tool) into the ligand-preparation stage**, so that `CHARGED_CONTACT_CANDIDATE` can be legitimately re-evaluated for promotion back to a real `SALT_BRIDGE` class for the subset of ligand atoms it confirms as genuinely ionizable at pH 7.4 — this is the single blocking prerequisite named in this session's own instructions ("fix the salt-bridge chemistry before production") standing between the current pilot and the 50–100-compound production pilot, and it's a bounded, well-scoped, testable unit of work on its own.
