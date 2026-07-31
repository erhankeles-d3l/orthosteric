# Sealed Artefact Manifest

Every sealed artefact is listed here with its SHA-256 companion and the commit that
sealed it. A seal whose commit postdates the first commit touching
`src/orthosteric/train/` is invalid and CI fails (`scripts/checks/seal_timestamp.py`).

**Nothing is sealed yet.** Seals are produced by `SCI0-023` … `SCI0-029`, all of which
are `Scientific` category and require the Independent Scientific Auditor
(Constitution §7.7, ENG §1).

| Artefact | SHA-256 file | Sealing commit | Objective | Date |
|---|---|---|---|---|
| *(none)* | — | — | — | — |

## Expected artefacts

| Objective | Artefact |
|---|---|
| `SCI0-023` | Correspondence ordering, weighting, S8c covariate list |
| `SCI0-024` | S9 reference rule set |
| `SCI0-026` | S10 mutation and null-control sites |
| `SCI0-027` | Second-family selection |
| `SCI0-028` | `N_c`, `N_b`, `N_w`, S4b sharpness factor, duplicate-resolution policy, per-isoform ATP Km source |
| `SCI0-029` | Pre-registered thresholds for all criteria (`sealed/config/`) |
