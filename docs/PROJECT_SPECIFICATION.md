# Project Specification

**Version 0.1 — partial.** Created under explicit instruction, which is the SI16 exception required for a governance-adjacent document.

**Mandate.** Constitution §7.9 requires a companion Implementation Specification containing a requirement-to-module traceability matrix covering **every** binding requirement in Parts 0–VI, plus module boundaries and APIs, data schemas, knowledge-layer storage and query implementation, compute and storage estimates per rigor level, and milestone definitions matched to §9.0.

**This version discharges §1 only.** All other sections are structurally present and explicitly deferred with a phase, which §7.9 permits: *"Every charter requirement must map to at least one specification item or be explicitly marked deferred with a phase."* Marking them deferred is compliance; leaving them unmentioned would not be.

| Field | Value |
|---|---|
| **Owns** | Functional requirements; requirement-to-module traceability |
| **Authority** | Lowest governance layer; may not weaken, reinterpret or omit a Constitution requirement (§7.9) |
| **Data policy source** | `ADR-0003` — this section has no force until that ADR is Accepted |

---

## 1. Data sources and exclusions

Authoritative implementation of `ADR-0003` and Constitution §3.3 as amended (Amendment A9).

### 1.1 Accepted — training and evaluation

| Source | Content | Record requirements |
|---|---|---|
| **ChEMBL** | Curated bioactivity from primary literature | ChEMBL ID; primary publication; assay ID; confidence score |
| **BindingDB** | Measured binding affinities | BindingDB ID; primary publication or patent; assay description |
| **PubChem BioAssay** | Deposited assay results | AID; depositor; assay protocol |
| **RCSB PDB** | Experimental structures | PDB ID; resolution; construct; ligand; deposition date |
| **Peer-reviewed publications** | Records extracted from primary literature and supplementary data | DOI; extraction date; curator; extraction version |

Every accepted record carries the full provenance set of Constitution §3.3: source, study, assay, ATP concentration, construct, date, curator, extraction version, tier.

### 1.2 Rejected — training and evaluation

| Excluded | Reason |
|---|---|
| User-run assays | Not independently reproducible from the public record |
| Laboratory notebooks | Not published; no citable provenance |
| Unpublished screening decks | Same |
| Proprietary or licensed corporate datasets | A third party cannot reconstruct the corpus |
| Continual or online learning from deployment | Incompatible with model-generation immutability (Constitution §0.4) |

### 1.3 Accepted — prospective validation and E4 evidence only

Newly generated experiment under Constitution §6.3, and independent external benchmarks.

**These never enter a training or evaluation corpus.** The separation is what preserves Design Rule reachability: §5.4 requires an E4 edge, Stage 5 (§9.7) generates it, and a blanket exclusion of non-public data would make Design Rules unobtainable. The policy prohibits *retraining* on new experiment, not its existence.

### 1.4 Corpus lifecycle

```
Public snapshot (content-hashed, immutable)
  → training → frozen model generation → predictions
  → new public snapshot → next model generation
```

There is no `prediction → user experiment → retraining` path. A model generation is frozen architecture + training data + hyperparameters (§0.4); new evidence produces a new generation, never a modified one.

### 1.5 Normalization and admissibility

- Where assay [ATP] **and** the isoform ATP Km are known, IC50 → Ki by Cheng–Prusoff before use. A normalization, not a learned covariate.
- Where [ATP] is unknown, the record cannot be normalized: flagged, excluded from primary targets, admissible only as low-reliability auxiliary evidence.
- Assay type, endpoint, organism, construct, publication and curation confidence are metadata, usable as covariates or stratification variables.
- **Training** uses the connected public evidence graph. **Evaluation of S2, S4a, S4b and S5** uses the within-study, within-assay stratum only. The two are reported separately and never pooled (Constitution §2.3(1) as amended).

### 1.6 Traceability — §1 requirements to modules

| Requirement | Module | Backlog objective |
|---|---|---|
| Source ingestion, five sources | `data/chembl|bindingdb|pubchem|pdb|literature` | `SCI0-006`, `SCI0-007` |
| Provenance capture | `data/provenance` | `SCI0-003` |
| Assay metadata schema | `data/` record schema | `SCI0-004` |
| Cheng–Prusoff normalization | `data/harmonization` | `SCI0-008` |
| Duplicate and conflict resolution | `data/harmonization` | `SCI0-009` |
| Curation confidence | `data/harmonization` | `SCI0-010` |
| Content-hashed snapshots | `data/snapshots` | `SCI0-011` |
| Within-study stratum extraction | `data/` | `SCI0-013` |
| Measurement-graph connectivity | `data/` | `SCI0-014`, `SCI0-015` |
| Exclusion enforcement (§1.2) | `data/` ingestion guard | `SCI0-006`, `SCI0-007` |

---

## 2–8. Deferred sections

Each is required by Constitution §7.9 and is deferred with a phase, per that section's own provision.

| § | Content | Deferred to |
|---|---|---|
| 2 | Requirement-to-module traceability, Constitution Parts 0–II | `SCI0-001` |
| 3 | Requirement-to-module traceability, Parts III–IV | `SCI1-001` |
| 4 | Module boundaries and public APIs | `SCI1-001`, extended per state |
| 5 | Data schemas beyond §1 | `SCI0-004` |
| 6 | Knowledge-layer storage and query implementation | `SCI4-001` (Phase 3) |
| 7 | Compute and storage estimates per rigor level L1–L5 | Constitution §1.6 resource declaration |
| 8 | Milestone definitions matched to §9.0 phases | at phase commitment, `SCI0-030` |

**Nothing here is unmapped-and-unmentioned**, which is the failure mode §7.9 exists to prevent. Sections 2–8 become obligations of the named objectives; §5 of ENG's PR checklist will surface any binding requirement that reaches implementation without a specification entry.
