# Execution Plan — Repository Bootstrap through the Stage 0 Gate

**Operational document.** Sequencing only; every rule is owned elsewhere. Corrects the Phase A–E draft.

**Contingency.** Assumes `ADR-0003` Accepted and Constitution v4.7 applied. If it is not, `SCI0-004` onward change shape.

---

## Corrections applied

| # | Defect in the draft | Correction |
|---|---|---|
| 1 | BOOT-001…008 is a parallel sequence to the Foundation Protocol | Phase A **is** `FND-1`…`FND-11`. Using a different sequence would require amending the Foundation Protocol by ADR |
| 2 | Seals infrastructure absent | `FND-4` restored — `SCI0-028` has nowhere to seal thresholds without it, and a later timestamp check cannot detect a backdated seal |
| 3 | Import-graph contracts absent | `FND-9` restored, **before** Phase B imports code |
| 4 | `FND-10`, `FND-11`, lifecycle ADR absent | Restored |
| 5 | `SCI0-002` missing | Inserted before the SCI0-003 import — SCI0-003's exit gate needs `data/models.py` |
| 6 | Chemical standardization and identifier harmonization have no objective | Added as `SCI0-008b`, `SCI0-008c`; both precede deduplication |
| 7 | `SCI0-016`…`SCI0-031` missing | Restored, including all six seals and the gate procedure |
| 8 | REDESIGN permits repeating the audit after seeing it | Re-sealing required; prior-audit disclosure recorded |
| 9 | "Implemented" used as an objective status | Objectives are `Pending → Active → Done`; `Implemented` is module maturity |
| 10 | "API keys" in externalized configuration | Credentials never in config or repository; env var only, never committed |

---

## Phase A — Foundation (`FND-1` … `FND-11`)

Governed by `IMPLEMENTATION_PROTOCOL_FOUNDATION.md`. **Requires `ADR-0001` Accepted before any work begins** (Constitution §3.1 forbids infrastructure before the audit; ADR-0001 is the capped exception).

| State | Delivers |
|---|---|
| `FND-1` REPOSITORY | Canonical tree (`CLAUDE.md` §15); git init; `main` + `develop`; `.gitignore`; LICENSE; README |
| `FND-2` ENVIRONMENT | `pyproject.toml`; Python pinned to an **exact minor version**; lockfile committed; ruff, mypy, pytest, pre-commit, MkDocs as dev deps |
| `FND-3` MAKEFILE | Seven ENG §22 targets: `install test lint format typecheck docs ci-local` |
| **`FND-4` SEALS** | `sealed/MANIFEST.md` + `.sha256` convention; **seal-timestamp check**; `logs/runs/`, `logs/audit/`, empty `logs/tier2_queries.jsonl`; audit logger |
| `FND-5` CONFIG | Hydra + Pydantic `extra="forbid"`; **non-composable sealed-config loader**; no hardcoded paths, URLs, timeouts, workers. **No credentials** — env var only, never committed |
| `FND-6` TESTS | pytest, coverage, `tests/` mirrors `src/` |
| `FND-7` CI | GitHub Actions running the complete ENG §20 Phase 1 set; branch protection |
| `FND-8` DOCS | MkDocs strict; `docs/{adr,specifications,architecture,api,user_guide}`; `CHANGELOG.md` |
| **`FND-9` BOUNDARIES** | Import-graph contracts 1, 2, 4 implemented; contract 3 written inert |
| `FND-10` FIRST_MODULE | One minimal production module. **Not the provenance writer** — that is `SCI0-003`. Requires the `Process` ADR resolving the collision; suggested: run-metadata writer in a Foundation-owned location |
| `FND-11` VALIDATED | Clean-checkout verification of everything above |

**Package name is decided at `FND-1`** and substituted everywhere `<pkg>` appears. Candidates: `pi3k_cel`, `orthoselect`, `d3l`.

**Exit:** `FND-11` satisfied → **lifecycle transition ADR** → `CLAUDE.md` header reads `Research` → Foundation Protocol terminates.

---

## Phase B — Scientific entry and code import

| Objective | Delivers |
|---|---|
| `SCI0-001` | Refinement of the SCI-0 backlog (already drafted) |
| `SCI0-002` | `data/` package scaffold: `__init__.py`, README naming Constitution sections, `config.py`, `exceptions.py`, `models.py`, subpackage stubs |
| `SCI0-003` | Import the verified provenance package; extend `data/models.py` so `ActivityRecord` references `ProvenanceRecord`; run `make test lint typecheck` **inside** the repository |

`SCI0-003` becomes **`Done`** only when its full exit gate passes — which requires `SCI0-002`, hence the ordering. Its modules reach maturity `Gate-verified` at the same point.

Branch per objective: `feature/SCI0-00N-<slug>` → merge to **`develop`**.

---

## Phase C — Data layer

| Objective | Delivers |
|---|---|
| `SCI0-004` | Activity record schema. `IC50`/`Ki`/`Kd` and `EC50` **do not share a field** (§2.3(3)); `Quantity`; `MeasurementClass` |
| `SCI0-005` | Censored measurements: exact, `>`, `<`, right- and left-censored; censored-likelihood interface. Never imputed, never discarded (§3.3) |
| `SCI0-006` | ChEMBL, BindingDB, PubChem connectors. One interface: `download search fetch metadata version`. Raw storage only. **Tier assigned at ingestion**; Tier 2 routes through the gate |
| `SCI0-006b` | Literature mining: CrossRef → PubMed → PMC. Extraction priority supplementary tables → manuscript tables → assay sections → free text. **Span verification binding**; unanchored values discarded, not down-weighted. OA coverage bias quantified |
| `SCI0-007` | PDB structures + structured construct descriptor; UniProt sequence metadata. **No AlphaFold** — predicted structures cannot satisfy §2.1(1) |
| `SCI0-008` | Activity normalization: unit conversion; **Cheng–Prusoff IC50 → Ki** where [ATP] and isoform Km known; BAO assay-ontology mapping with measured-quantity and interference-susceptibility fields |
| **`SCI0-008b`** | **Chemical standardization (RDKit)**: salt stripping, charge normalization, canonical tautomer, **stereochemistry preserved**, canonical SMILES, InChI, InChIKey. **No descriptors** — LogP, MW, rotatable bonds and ring counts are features and belong to SCI-1 |
| **`SCI0-008c`** | **Identifier harmonization**: internal ID, cross-references across ChEMBL/BindingDB/PubChem. Conflicting structures for one identifier are surfaced, never silently merged |
| `SCI0-009` | Duplicate and conflict resolution. **Different stereoisomers never merged.** Requires `SCI0-008b` — deduplication without canonical structures is unsound |
| `SCI0-010` | Confidence assignment: **additive, inspectable, deterministic. No learned model** — that would breach SI3 and make the corpus depend on a model trained on it |
| `SCI0-011` | Immutable content-hashed snapshots; manifest carries source versions **and full software provenance**: RDKit, Python, lockfile hash, git SHA, OS, pipeline version |
| `SCI0-012` | Bemis–Murcko scaffold family assignment |
| `SCI0-013` | Within-study / within-assay stratum — the evaluation ground truth under §2.3(1) |
| `SCI0-014` | Compound × isoform measurement graph: components, bridging compounds, study clusters |
| `SCI0-014b` | Dataset characterization. **Descriptive only**; may not inform split, stratum or threshold selection |

---

## Phase D — Pre-registration, then audit

**Ordering is binding.** Every seal is `Done` before `SCI0-015` begins. Running the audit first would let the kill criterion be chosen after seeing the data — Constitution §1.4, and the failure R23 describes.

| Objective | Delivers |
|---|---|
| `SCI0-023` | Seal: correspondence ordering, weighting, S8c covariate list |
| `SCI0-024` | Seal: S9 reference rule set |
| `SCI0-025` | Empirical S9b precision floor calibration |
| `SCI0-026` | Seal: S10 mutation and null-control sites |
| `SCI0-027` | Seal: second-family selection |
| **`SCI0-028`** | **Seal: `N_c`, `N_b`, `N_w`, S4b sharpness factor, duplicate-resolution policy, per-isoform ATP Km source** |
| `SCI0-029` | Seal: pre-registered thresholds for all criteria, into `sealed/config/` |

Seals `SCI0-023`…`SCI0-029` are `Scientific` category and require the Auditor (ENG §1; Constitution §7.7).

| Objective | Delivers |
|---|---|
| `SCI0-015` | **Public comparative evidence audit** — amended Q1, all nine sub-questions. **R1 evaluated here** |
| `SCI0-016` | Q4 — **both** noise floors, within-study and cross-study |
| `SCI0-017` | Q3 — right-censored fraction and handling |
| `SCI0-018` | Q5 — ATP-site structure inventory |
| `SCI0-019` | Q6 — MMP switch set, **within-study pairs only** |
| `SCI0-020` | Q7 — evaluation-set size after scaffold-aware splitting |
| `SCI0-021` | Q8–Q10 — Tier 2 census, per-target evaluation mode, structural quality |
| `SCI0-022` | Q12 — dual-inhibitor census |
| `SCI0-030` | Phase commitment recorded in the `CLAUDE.md` header (Constitution §1.6) |

**Audit outputs** carry full ENG §7 provenance and are attached to the snapshot hash: `Stage0_Audit.json`, `Stage0_Audit_Report.md` (PDF rendered from it), `Stage0_Snapshot_Manifest.json`.

---

## Phase E — Stage 0 gate (`SCI0-031`)

`[procedure]` — Scientific Protocol §15.4. Not an implementation objective; it produces a recorded outcome, evaluated **once**.

| Outcome | Condition | Action |
|---|---|---|
| **GO** | All Stage 0 criteria satisfied against the sealed thresholds | Proceed to `SCI-1` |
| **REDESIGN** | Deficiencies recoverable within the Constitution | See below |
| **STOP** | R1 thresholds failed — connected component, bridging compounds, within-study stratum, or scaffold diversity below seal | Terminate comparative learning; **write up the negative result**. Constitution §1.4: redesign as a physics-only orthosteric study |

**REDESIGN is not "audit again."** Any redesign that changes what is audited requires:

1. an ADR recording the redesign **and disclosing that a prior audit was observed**;
2. **re-sealed thresholds** under `SCI0-028`, since the originals were chosen for a different design;
3. a new snapshot and a new audit run against the new seals.

Without those, REDESIGN degenerates into repeating the audit until it passes, which makes the kill criterion negotiable and R1 decorative.

**A STOP outcome is a result, not a failure.** It would establish that the public evidence base cannot support comparative selectivity learning at the Class I ATP site — a finding worth publishing, and one no amount of further engineering changes.

---

## Flow

```
ADR-0002 governance closure  →  ADR-0001 Foundation authorization
  →  Process ADR (FND-10 / SCI0-002 collision)
  →  FND-1 … FND-11  →  lifecycle ADR  →  Research
  →  SCI0-001 → 002 → 003
  →  004 → 005 → 006 → 006b → 007 → 008 → 008b → 008c → 009 → 010
  →  011 → 012 → 013 → 014 → 014b
  →  SEALS 023 … 029                          ← before the audit, always
  →  015 audit → 016 → 017 → 018 → 019 → 020 → 021 → 022 → 030
  →  SCI0-031 gate  →  GO | REDESIGN | STOP
```

One branch and one merge per objective; `main` tagged at phase boundaries (`v0.1.0-foundation`, `v0.2.0-stage0`).

The first genuinely scientific decision is `SCI0-031`, and it is decided by the evidence graph — not by further planning.
