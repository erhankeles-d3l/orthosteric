# Scientific State

Per `docs/IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` SI3: baseline results
recorded here before the first `model/`/`train/` commit.

## SCI1-021/SCI1-022 — Baseline evaluation and gate (executed 2026-08-06)

See `docs/governance/decision-records/ADR-0015-sci1022-gate-executed-go.md`
and `docs/governance/SCI1022_GATE_RECORD_A4.json` for full detail.

**Gate: GO.** Ligand-only baseline RMSE (0.817–1.174 log units) exceeds the
Constitution §1.4 S2 threshold (0.3 log units); a learned comparative model
is not automatically unjustified. SI3 satisfied on Activity Snapshot A4
(`SNAP-05748f6627ea`).

| Baseline | alpha_vs_beta | alpha_vs_gamma | alpha_vs_delta |
|---|---:|---:|---:|
| ligand_only_mean | 1.174 | 0.817 | 1.106 |
| nearest_neighbor_tanimoto | 0.560 | 0.707 | 0.570 |
| proteochemometric_linear | 0.675 | 0.760 | 0.714 |

Scaffold split (seed=42): train 822 / val 191 / test 254 compounds;
407/57/115 scaffolds; overlap 0.

## Model Generation 1 — Baseline comparison (see below, this session)

See `docs/MODEL_GENERATION_1_BASELINE_REPORT.md`.
