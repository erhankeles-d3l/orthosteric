# Stage C, Step 2 — Candidate Pool and Exclusions: Summary

## Frozen exclusion order (executed exactly as specified, verified by the script's own print trace)

1. Literature panel compounds + scaffolds sealed (Step 1): 5 compounds, 5 scaffolds.
2. Candidate pool built from A4 (`SNAP-05748f6627ea`): 39,508 total records → 39,002 accepted (`conflict_status == "ok"`, no `exclusion_reason`) → **2,481 compounds** with a within-study four-isoform panel (charter §2.3: same `study_id`, all four isoforms present among accepted records).
3. 24/50 corpora excluded (compounds **and** scaffolds): 51 compounds, 50 scaffolds → 2,481 → **2,083** remain.
4. Literature panel excluded again (compounds **and** scaffolds, per the revised plan's extension beyond compound-only exclusion): 2,083 → **2,069** remain.
5. **Frozen and hashed at this point.** No step after hashing added or removed a compound.
6. Composition inspected only now (legitimate per the frozen order).

## The composition finding that drives the Stage C decision

The sealed set is **2,069 compounds** — but the frozen primary confirmatory contrast (alpha_selective vs other_selective) only draws on compounds where **all four isoforms** have a usable numeric pAct value (not just presence in a four-isoform panel, which was Step 2's coarser qualifying criterion — Step 2 required isoform *presence*, not a complete *pAct value* per isoform).

| Stratum | n |
|---|---:|
| indeterminate (missing pAct for ≥1 isoform) | 1,114 |
| intermediate | 744 |
| non_selective | 167 |
| **alpha_selective** | **31** |
| **other_selective** | **13** |

**Primary contrast n = 44.** This is the number that determines whether Stage C's decisive gate exists — not the 2,069 headline figure, which would have been a materially misleading number to report as "the sealed set size" for power purposes.

## The two frozen artifacts

- `data/structural_evidence/sealed_validation_structures.json` — 2,069 compounds, SMILES + scaffold_family_id + isoforms_present. Freely readable by discovery-phase code (Contract 5 does not block this path).
- `data/sealed/sealed_validation_labels.json` — 2,069 compounds, pAct per isoform + stratum. Reachable only through `orthosteric.data.sealed_labels.load_sealed_labels_for_unblinding()`, itself reachable only by code Contract 5 does not forbid from importing `orthosteric.data.sealed_labels` (i.e., never from `orthosteric.discovery`).

## Stratum definition (frozen, stated in the labels artifact itself)

- `alpha_selective`: pAct_alpha − max(others) ≥ 1.0 log unit.
- `other_selective`: min(others) − pAct_alpha ≥ 1.0 log unit.
- `non_selective`: max−min across all four ≤ 0.5 log unit.
- `intermediate`: none of the above.
- `indeterminate_missing_pact`: at least one isoform's pAct could not be computed (no accepted record with a numeric `pchembl_value` for that isoform within the qualifying study).
