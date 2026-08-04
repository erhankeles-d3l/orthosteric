# SCI0-001 Refinement Output — Public Data Acquisition Layer

**What this is.** The deliverable of backlog objective `SCI0-001` (*Refine `SCI-0` backlog*), expanding `SCI0-002` … `SCI0-014b` into implementation detail, **using backlog IDs exactly**. Operational, not governance — it adds no rule and is not a new document class under SI16.

**What this is not.** Not a stage, and not a single objective. The prior draft was labelled "Stage SCI0-002"; `SCI0-002` is one objective (the package scaffold), and SI18 requires each task to map to exactly one backlog ID.

**Contingency.** Assumes `ADR-0003` Accepted and Constitution v4.7 applied. Until then this is proposed work, not authorized work.

---

## Defects corrected from the prior draft

| # | Defect | Correction |
|---|---|---|
| 1 | Sixteen objectives under one ID | Mapped to `SCI0-002`…`SCI0-014` |
| 2 | **No tier tagging at ingestion** — Tier 2 targets share queries with Class I | Tier assigned in the connector; Tier 2 lands in `data/tier2/` behind the gate from first download |
| 3 | Objective 9 computed LogP, MW, rotatable bonds, rings | Descriptors removed — they belong to `features/` at SCI-1 (Protocol §16) |
| 4 | **Cheng–Prusoff conversion absent** | Mandatory where [ATP] and isoform ATP Km are known (Amendment A5) |
| 5 | IC50/Ki/Kd/EC50 treated as one quantity | Separated; EC50 is cellular and never pooled with biochemical (§2.3(3)) |
| 6 | **Censored records absent** | Right-censored inactives retained with censored representation (§3.3) |
| 7 | AlphaFold as a structure source | Excluded — no resolution, no bound ligand, cannot support §2.1(1); R4 risk. UniProt retained for sequence metadata only |
| 8 | Missing within-study stratum and measurement-graph connectivity | Added as `SCI0-013`, `SCI0-014` — R1 depends on them |
| 9 | Cache ≠ snapshot | Content-hashed immutable snapshots added (`SCI0-011`, ENG §13) |
| 10 | `python run.py` entry point | `make` targets only (ENG §22) |
| 11 | Single end-to-end Definition of Done | Per-objective exit criteria; integration is its own objective |
| 13 | Literature sources absent — much kinase SAR is publication-only | `SCI0-006b` added, with a binding span-verification gate |
| 14 | Interaction extraction proposed inside `data/` | Deferred to `features/` at SCI-1 — interaction fingerprints are features |
| 12 | Statistics list from the superseded policy | Replaced with amended Q1 (connectivity, bridging, publication concentration, [ATP] fraction) |

## Package structure

```
src/<pkg>/data/
    __init__.py  config.py  exceptions.py  models.py
    _downloader.py  _cache.py                      # internal
    tier2_gate.py                                  # built at FND-4; consumed here
    sources/  chembl.py  bindingdb.py  pubchem.py  pdb.py  uniprot.py
              literature/  crossref.py  pubmed.py  pmc.py  extract.py  verify.py
    harmonization/  standardize.py  identifiers.py  activity.py
                    cheng_prusoff.py  deduplicate.py  confidence.py
    provenance/  record.py  writer.py
    snapshots/  builder.py  manifest.py
    graph.py  strata.py  audit.py  report.py
    README.md
```

`alphafold.py` deliberately absent (defect 7). Descriptor modules deliberately absent (defect 3).

---

## Objectives

Each is a vertical slice: implementation, its tests written first, and its docstrings. Exit criteria are per objective; `make ci-local` green is assumed throughout and not restated.

### `SCI0-002` — Package scaffold
`data/` with `__init__.py` declaring `__all__`, README naming the Constitution sections served (§2.3, §3.3, §0.4), `config.py`, `exceptions.py`. Configuration externalized — no URL, path, timeout or worker count in code (ENG §5).
**Exit:** package imports; strict typecheck clean; README states Constitution sections; no hardcoded values (lint).

### `SCI0-003` — Provenance record schema and writer
Every record carries source, study or accession, assay, [ATP], construct, date, curator, extraction version, **tier**, curation confidence (§3.3, ENG §7).
**Exit:** a record missing any field is rejected at construction, under test.

### `SCI0-004` — Activity record schema
Separate typed quantities: `IC50`, `Ki`, `Kd` (biochemical) and `EC50` (cellular). **They do not share a field.** Censoring representation: `exact | right_censored | left_censored` with the threshold and operator retained.
**Exit:** schema rejects a pooled biochemical/cellular value; a `>10 µM` record round-trips with its operator intact.

### `SCI0-005` — Censored-data handling
Right-censored inactives retained, never imputed to threshold, never discarded (§3.3). Interface for censored likelihood consumption downstream.
**Exit:** censored fraction reported; no code path drops a censored record.

### `SCI0-006` — Common source interface + ChEMBL, BindingDB, PubChem connectors
One interface: `download() · search() · fetch() · metadata() · version()`. Raw payloads stored unmodified. **No connector-specific type leaves the module.** **Every record is tier-tagged at ingestion**; Tier 2 targets route to `data/tier2/` through `tier2_gate.py`.
**Exit:** three connectors return identical internal types under test; a Tier 2 record written outside `data/tier2/` raises; database version recorded per download.


### `SCI0-006b` — Literature mining
A large share of kinase SAR never reaches ChEMBL. Accepted under ADR-0003 §2 (peer-reviewed publications and supplementary data).

**Pipeline.** CrossRef (DOI and metadata) → PubMed (records, MeSH) → PMC open-access full text and supplementary material → extraction → activity parsing → **span verification** → confidence class → standardization via `SCI0-009`.

**Extraction priority (binding order).** Medicinal chemistry SAR lives in tables; free text is the fallback.

```
1  Supplementary tables        highest yield, most structured
2  Main manuscript tables
3  Structured assay sections   methods, experimental
4  Free-text paragraphs        fallback only
```

**The extraction tier is recorded per record** and is an input to `SCI0-010` confidence. Tiers 1–2 and tier 4 have materially different error rates; treating all literature-derived records as one class discards that information.

**Verification gate (binding).** Automated or LLM-assisted extraction is **candidate-generating only**. Every extracted value carries a locatable anchor — DOI, table or figure identifier, row — and is verified against the source span before use. An unanchored or unverifiable value is discarded, never retained at low confidence: a fabricated measurement carrying a genuine DOI is worse than a missing one, because its provenance record makes it look sound (CLAUDE.md §1).

**Confidence class.** Literature-extracted records occupy a distinct class in `SCI0-013`, below database-curated records. They do not enter primary targets until span-verified. A sampled human audit is run per extraction batch and its error rate recorded in the snapshot manifest.

**Coverage bias (must be quantified, not assumed away).** PMC open access is a non-random subset by journal, year and funder. The audit reports OA versus total candidate publications per journal and year, so the resulting corpus bias is measurable rather than invisible.

**Licensing.** Restricted to open-access content and sources with explicit text-and-data-mining permission. Per-source license recorded in the provenance record.

**Exit:** every extracted value resolves to a source span under test; unanchored extractions are rejected; OA coverage fraction and audit error rate reported.

### `SCI0-007` — Structural sources: PDB, UniProt
PDB: metadata and coordinates for human structures with a bound ATP-site ligand. UniProt: sequence and isoform identity only. **AlphaFold: constrained fallback only** — experimental PDB is mandatory when an admissible human experimental structure exists; AlphaFold permitted only when no admissible experimental PDB exists, subject to the nine deterministic rules in AMENDMENT-SCI0007-ALPHAFOLD-FALLBACK.md (supersedes defect 7).
**Exit:** structures lacking resolution or a bound ligand are flagged and excluded from the §2.1 reference set; exclusion count reported.

**Construct descriptor (structured, not free text).** PDB entries differ substantially in construct design, and Constitution §2.1 states that a construct mismatch **threatens correspondence stability under A.1(4)** — so this descriptor feeds the stability assessment, not merely structure filtering.

| Field | Content |
|---|---|
| Sequence range | UniProt numbering; truncations recorded explicitly |
| Engineered mutations | position, wild-type, variant, purpose where stated |
| Fusion tags and linkers | identity and placement |
| Regulatory subunit | p85 isoform, p101, p87, or none (§2.1 construct policy) |
| Activation-loop state | modified, resolved, disordered, absent |
| Missing residues or domains | ranges; loops < 4 residues flagged, ≥ 4 excluded (§2.1) |

**Interaction extraction is not here.** Hydrogen bonds, hydrophobic contacts, water bridges, electrostatics, contact maps and interaction fingerprints are **features**, and `data/` never contains features (Protocol §16). They are derived in `features/` at SCI-1, from the structures this objective acquires. Placing them in `data/` would breach package ownership P8 and put model inputs inside the acquisition layer.

### `SCI0-008` — Caching layer
Content-hash validation, timestamps, source version tracking, explicit invalidation. Nothing downloaded twice.
**Exit:** repeated build issues no network call; a corrupted cache entry is detected by hash, not by size or date.

### `SCI0-009` — Chemical standardization (RDKit)
Salt stripping, charge normalization, canonical tautomer, **stereochemistry preserved**, canonical SMILES, InChI, InChIKey, sanitization. **No descriptors** — no LogP, MW, rotatable bonds, ring counts, fingerprints or graph features.
**Exit:** stereoisomers remain distinct through the pipeline; no descriptor column exists; deterministic across runs.

### `SCI0-010` — Identifier harmonization
Internal ID, canonical SMILES, InChI, InChIKey, cross-references to ChEMBL / BindingDB / PubChem.
**Exit:** the same compound from three sources resolves to one internal ID; conflicting structures for one identifier are surfaced, not silently merged.

### `SCI0-008` — Activity normalization and Cheng–Prusoff
Unit conversion across M/mM/µM/nM/pM. **Where assay [ATP] and the isoform ATP Km are known, IC50 → Ki via `Ki = IC50 / (1 + [ATP]/Km_ATP)`.** Where [ATP] is unknown the record is flagged non-normalizable, excluded from primary targets, retained as low-reliability auxiliary evidence (§2.3(2) as amended). Original value, unit, assay description and conditions preserved. **No averaging.**
**Assay ontology normalization.** Free-text assay descriptions map to a controlled vocabulary — **reuse BioAssay Ontology (BAO) terms and ChEMBL assay-format annotations rather than inventing a vocabulary** (CLAUDE.md §6). Covered formats include radiometric, ADP-Glo and other coupled-luminescence, HTRF, TR-FRET, fluorescence polarization, mobility shift, and ELISA.

Each format carries two fields beyond its identity:

| Field | Why |
|---|---|
| **Measured quantity** | These formats do not measure the same thing — coupled luminescence detects ADP production, radiometric detects direct phosphate transfer, FP and TR-FRET are proximity or displacement readouts. Pooling them without recording which is a hidden heterogeneity |
| **Interference susceptibility** | Fluorescent, quenching and aggregating compounds produce format-specific artefacts. This flag is what makes the ontology usable for bias analysis and confidence weighting, not just bookkeeping |

**Exit:** normalized and raw values both present; non-normalizable fraction reported; per-isoform Km_ATP source cited, not assumed; every record carries a BAO-mapped format or an explicit `unmapped` marker with its free text retained.

### `SCI0-009` — Duplicate detection and conflict resolution
Identical compounds merged; **different stereoisomers never merged**; all constituent measurements and their provenance retained.
**Exit:** a stereoisomer pair survives deduplication; a merged record lists every source measurement.

### `SCI0-010` — Confidence scoring
Interpretable, **additive and inspectable** score over: assay quality (including BAO format and interference susceptibility), publication quality, duplicate agreement, measurement consistency, metadata completeness, and literature extraction tier where applicable. Deterministic; its version enters the snapshot hash, since changing it changes the corpus.

**No learned confidence model at SCI-0.** Two reasons, and the second is decisive. A neural confidence estimator is not auditable — a reviewer cannot ask why a record scored 0.4. And it would be a learned component built before the `SCI-1` baseline gate, breaching **SI3**, while making the corpus depend on a model trained on that corpus. Circular, not merely opaque.
**Exit:** score decomposition is inspectable per record; rerun reproduces identical scores.

### `SCI0-011` — Snapshot builder
Content-hashed, immutable snapshot. The manifest records source versions, download dates, harmonization version and confidence version — **plus full software provenance**: RDKit version, Python version, dependency lock hash, git commit, OS and pipeline version (ENG §13, §6).

**Why the toolchain is part of corpus identity.** RDKit tautomer canonicalization changes between releases, so the same input SMILES can yield a different InChIKey under a different version. A snapshot is therefore not reproducible from source database versions alone; the standardization toolchain enters the hash.
**Exit:** two builds from the same cache yield the same hash; a snapshot cannot be modified in place (SI9).

### `SCI0-012` / `SCI0-013` — Scaffold assignment; comparative assembly and within-study stratum
Per compound, per isoform: individual measurements, explicit missingness, multiple measurements retained, publication links. **No imputation.** Plus **within-study / within-assay stratum extraction** (`strata.py`) — the evaluation ground truth under §2.3(1) as amended.
**Exit:** missing ≠ inactive anywhere in the schema; the within-study stratum is separable and its size reported.

### `SCI0-014` — Measurement-graph construction
Bipartite compound × isoform graph (`graph.py`): connected components, bridging compounds, study-cluster structure. This is the substrate the amended R1 is evaluated against.
**Exit:** largest component, bridging count and cluster structure computed and reproducible.


### `SCI0-014b` — Dataset characterization
**Describes the snapshot; never modifies it.** Descriptive analysis only, so it remains inside SCI-0 responsibilities and touches no learned component (SI1, SI3).

Outputs, per frozen snapshot and attached to its hash: activity distributions per isoform and quantity type · assay-format distributions (BAO-mapped) · publication distributions and per-publication concentration · scaffold distributions · confidence distributions, decomposed by contributing term · connectivity statistics · missingness heat maps · isoform overlap matrices · temporal trends by publication year.

**Guard (binding).** Characterization runs **before** modelling and its outputs may not be used to select the evaluation stratum, tune splits, or choose thresholds after inspecting distributions. Thresholds are sealed at `SCI0-028` before the audit runs; characterization informs *description*, never *selection*. Using a distribution plot to pick a split is choosing the test after seeing the data.

**Exit:** report regenerates identically from the snapshot hash alone; no characterization output feeds a split, threshold or stratum decision; artefacts carry snapshot hash and full software provenance.

---

## Ordering constraint (binding)

**Threshold sealing precedes the audit.** `SCI0-028` — sealing `N_c`, `N_b`, `N_w`, the S4b sharpness factor and the duplicate-resolution policy — must be `Done` before the audit objective runs. Running connectivity analysis first would allow the kill criterion to be chosen after seeing the data: a Constitution §1.4 violation and precisely the failure R23 describes.

The audit itself (`SCI0-015`) and report generation follow, and are specified against amended Q1: total compounds and records per isoform; coverage and pairwise overlap; **connectivity, bridging compounds, study clusters**; within-study four-isoform count; scaffold diversity in the connected component; publication diversity and concentration; assay-type diversity, [ATP]-recorded fraction, Ki-normalizable fraction; duplicate and conflict rates; confidence distribution.

## Definition of done

Per-objective exit criteria above, plus one integration objective:

```
make dataset          # build from cache, or download then build
make dataset-report   # emit reports/ artefacts
```

Both are `Makefile` targets with contracts under ENG §22 — no `python run.py` (ENG §22, CLAUDE.md §16). Reports carry full provenance (ENG §7): source versions, download dates, snapshot hash, harmonization and confidence versions, record counts, quality metrics, coverage, limitations.

The stage demonstrates that a comparative PI3K corpus can be assembled reproducibly from public sources alone, with tier separation intact and every record traceable to a publication or accession.

## Out of scope

No model, training, inference, embeddings, fingerprints, graph features, descriptors, feature selection, docking, MD, ADMET, knowledge graph, or mechanism inference. These belong to `SCI-1` and later and are barred here by SI1, SI3 and Protocol §16 package ownership.

## Reusability

The source interface, harmonization layer and snapshot builder are target-agnostic; only the target identifiers and the isoform ATP Km table are PI3K-specific. This is a precondition for `S7` cross-family transfer at `SCI-4`, where the sealed second family must be ingested without framework retuning.
