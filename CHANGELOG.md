# Changelog

Maintained from the first commit, never retrofitted (ENG §8).

## [Unreleased]

### SCI-0 — Data Acquisition Layer (in progress)

#### SCI0-001 — Backlog refinement (Done)
- Existing refinement document at `docs/specifications/SCI0-001-refinement-data-acquisition.md`
  adopted as the authoritative decomposition of `SCI0-002`–`SCI0-014b`
- Backlog status updated to `Done`

#### SCI0-007 — Structural sources: PDB + UniProt + AlphaFold fallback (Done)
- `data/sources/structural/_isoform_map.py`: authoritative PI3K isoform↔UniProt
  map (α=P42336, β=P42338, γ=P48736, δ=O00329) with gene symbols
- `data/sources/structural/_pdb.py`: RCSB PDB REST connector; §2.1 admissibility
  rules (human, resolution ≤ 2.8 Å, bound ligand); `_assess_admissibility()`;
  `_build_construct()` → `ConstructDescriptor`; `StructureAdmissibility` enum;
  `StructureSource.EXPERIMENTAL_PDB` default
- `data/sources/structural/_alphafold.py`: AlphaFold DB fallback connector;
  Rules AF-1–AF-9 from AMENDMENT-SCI0007-ALPHAFOLD-FALLBACK.md;
  Rule AF-4 (mean pLDDT ≥ 70); Rule AF-6 (no experimental metadata fabrication);
  `GovernanceException` on accession mismatch (Rule AF-3)
- `data/sources/structural/_uniprot.py`: UniProt REST connector; sequence +
  isoform identity only; PDB cross-references
- `data/sources/structural/_structure_record.py`: `StructureRecord` (references
  ProvenanceRecord via provenance_id); `ConstructDescriptor` (frozen dataclass
  with sequence range, mutations, tags, regulatory subunit, activation-loop state,
  missing residue ranges); `ActivationLoopState` enum
- Governance: `AMENDMENT-SCI0007-ALPHAFOLD-FALLBACK.md` authorizing the
  constrained fallback with 9 deterministic rules; SCI0-001-refinement updated
- 32 new tests (24 experimental PDB + 8 AlphaFold fallback rules); 161 total

#### SCI0-006b — Literature-mining adapters: CrossRef, PubMed, PMC OA (Done)
- `data/sources/literature/_extractor.py`: `ExtractionStatus` enum
  (CANDIDATE → SPAN_VERIFIED / DISCARDED / OA_INACCESSIBLE);
  `LiteratureExtractionRecord` with full provenance; `verify_span()`
  binding-rule implementation: unanchored or unverifiable → DISCARDED,
  never retained at low confidence; `coverage_bias_report()` with
  per-year and per-journal OA fraction breakdowns
- `data/sources/literature/_crossref.py`: DOI metadata + TDM-permission
  detection from license URL; `PublicationMetadata`; CC-BY/CC0 permitted
- `data/sources/literature/_pubmed.py`: PubMed E-utilities search + fetch;
  `PubMedRecord`; identifies PMCID for OA routing
- `data/sources/literature/_pmc.py`: PMC-OA full-text fetch; extraction in
  priority order (supplementary tables → manuscript tables → assay sections
  → free text); `verify_span()` called inline — no CANDIDATE records leave
  the connector
- 18 new tests; all SCI0-006b exit criteria pass

#### SCI0-006 — Source connectors: ChEMBL, BindingDB, PubChem BioAssay (Done)
- `data/sources/_base.py`: common `SourceConnector` ABC + `RawSourceRecord`
  (single internal type returned by all three connectors); `Admissibility`
  enum: TIER1_PRIMARY / TIER2_GATED / INADMISSIBLE
- `data/sources/_tier_map.py`: authoritative target→tier map; ChEMBL IDs,
  gene symbols, UniProt ACs; all four Tier 1 and six Tier 2 PI3K targets
  covered; case-insensitive gene lookup
- `data/sources/_chembl.py`: ChEMBL REST connector; Tier assigned at
  `_parse_activity()` before any record crosses the module boundary;
  inadmissible records returned with reason code, never silently dropped
- `data/sources/_bindingdb.py`: BindingDB REST connector; UniProt-first
  tier assignment with gene-name fallback
- `data/sources/_pubchem.py`: PubChem BioAssay PUG REST connector;
  gene-symbol tier assignment; right-censored inactives detected from
  ActivityOutcome field
- 20 new tests; all SCI0-006 exit criteria pass
- `chembl_adapter.py` retained (adjudication prototype); sources layer
  is the production path

#### SCI0-004 — Activity record schema (Done)
- `data/activity.py`: `BiochemicalRecord` (IC50/Ki/Kd) and `CellularRecord`
  (EC50 only) are distinct frozen dataclasses; pooling is rejected at
  construction (Constitution §2.3(3))
- `CensoredValue`: magnitude + unit + relational operator + censoring kind;
  operator/censoring consistency validated at construction
- `RelationalOperator`: =, >, <, >=, <= as StrEnum
- Biochemical/cellular separation enforced at the Python type level — no
  function accepting `BiochemicalRecord` can silently receive EC50

#### SCI0-005 — Censored-data handling (Done)
- `is_censored()` / `censored_fraction()` — interface for censored likelihood
  downstream; right-censored inactives retained, never imputed
- 10 new tests; all SCI0-004/005 exit criteria pass

#### SCI0-003 — Provenance record schema and writer (Done)
- `data/provenance/enums.py`: closed-vocabulary enums — `SourceType`, `Tier`,
  `MeasurementType`, `MeasurementClass`, `ExtractionTier`, `LocatorType`,
  `SourceConfidence`, `LicenseType`, `Unit`
- `data/provenance/models.py`: immutable frozen dataclasses — `Quantity`
  (Decimal + Unit; no bare floats), `SpanAnchor`, `SourceMetadata`, 
  `PublicationMetadata`, `AssayMetadata`, `ExtractionMetadata`,
  `ProvenanceRecord`; `SCHEMA_VERSION = "1.0.0"`
- `data/provenance/validator.py`: structural validation; raises
  `ProvenanceValidationError` with all problems at once; literature sources
  require a verified span anchor (SCI0-006b gate)
- `data/provenance/writer.py`: deterministic JSON serialization (sorted keys,
  Decimal in canonical fixed-point, explicit UTC offset); `serialize` /
  `deserialize` / `to_json_bytes`
- `data/models.py`: extended with `ActivityRecord` — links every measurement
  to a `provenance_id` (Constitution §3.3)
- 34 provenance tests (carried from verified supplementary package, namespace
  renamed from `pi3k_cel` to `orthosteric`); 81 total tests passing

#### SCI0-002 — `data/` package scaffold (Done)
- `config.py`: externalized configuration (ENG §5); no hardcoded URLs, paths,
  timeouts, or worker counts
- `exceptions.py`: complete domain exception hierarchy (`OrthoDataError` base;
  `ProvenanceError`, `TierViolationError`, `SnapshotIntegrityError`,
  `GovernanceException`, `NormalizationError`, `ConfigurationError`)
- `models.py`: shared domain enums — `DataTier`, `SourceDB`, `MeasurementKind`,
  `CensoringKind`, `RecordStatus` (StrEnum; no descriptors, no features)
- `tier2_gate.py`: enforces the Constitution §0.4 Tier 2 information barrier
  in code at the data-layer boundary
- `data/README.md`: full Constitution section mapping (§0.1, §0.4, §2.3, §3.3)
- `__init__.py`: `__all__` declared, sorted, typed; 18 public names
- Subpackage stubs: `sources/`, `harmonization/`, `provenance/`, `snapshots/`
- 47 tests passing (19 new scaffold tests + 28 existing adjudication tests)

## [Unreleased]

### SCI-0 — Data Acquisition Layer (in progress)

#### SCI0-001 — Backlog refinement (Done)
- Existing refinement document at `docs/specifications/SCI0-001-refinement-data-acquisition.md`
  adopted as the authoritative decomposition of `SCI0-002`–`SCI0-014b`
- Backlog status updated to `Done`

#### SCI0-007 — Structural sources: PDB + UniProt + AlphaFold fallback (Done)
- `data/sources/structural/_isoform_map.py`: authoritative PI3K isoform↔UniProt
  map (α=P42336, β=P42338, γ=P48736, δ=O00329) with gene symbols
- `data/sources/structural/_pdb.py`: RCSB PDB REST connector; §2.1 admissibility
  rules (human, resolution ≤ 2.8 Å, bound ligand); `_assess_admissibility()`;
  `_build_construct()` → `ConstructDescriptor`; `StructureAdmissibility` enum;
  `StructureSource.EXPERIMENTAL_PDB` default
- `data/sources/structural/_alphafold.py`: AlphaFold DB fallback connector;
  Rules AF-1–AF-9 from AMENDMENT-SCI0007-ALPHAFOLD-FALLBACK.md;
  Rule AF-4 (mean pLDDT ≥ 70); Rule AF-6 (no experimental metadata fabrication);
  `GovernanceException` on accession mismatch (Rule AF-3)
- `data/sources/structural/_uniprot.py`: UniProt REST connector; sequence +
  isoform identity only; PDB cross-references
- `data/sources/structural/_structure_record.py`: `StructureRecord` (references
  ProvenanceRecord via provenance_id); `ConstructDescriptor` (frozen dataclass
  with sequence range, mutations, tags, regulatory subunit, activation-loop state,
  missing residue ranges); `ActivationLoopState` enum
- Governance: `AMENDMENT-SCI0007-ALPHAFOLD-FALLBACK.md` authorizing the
  constrained fallback with 9 deterministic rules; SCI0-001-refinement updated
- 32 new tests (24 experimental PDB + 8 AlphaFold fallback rules); 161 total

#### SCI0-006b — Literature-mining adapters: CrossRef, PubMed, PMC OA (Done)
- `data/sources/literature/_extractor.py`: `ExtractionStatus` enum
  (CANDIDATE → SPAN_VERIFIED / DISCARDED / OA_INACCESSIBLE);
  `LiteratureExtractionRecord` with full provenance; `verify_span()`
  binding-rule implementation: unanchored or unverifiable → DISCARDED,
  never retained at low confidence; `coverage_bias_report()` with
  per-year and per-journal OA fraction breakdowns
- `data/sources/literature/_crossref.py`: DOI metadata + TDM-permission
  detection from license URL; `PublicationMetadata`; CC-BY/CC0 permitted
- `data/sources/literature/_pubmed.py`: PubMed E-utilities search + fetch;
  `PubMedRecord`; identifies PMCID for OA routing
- `data/sources/literature/_pmc.py`: PMC-OA full-text fetch; extraction in
  priority order (supplementary tables → manuscript tables → assay sections
  → free text); `verify_span()` called inline — no CANDIDATE records leave
  the connector
- 18 new tests; all SCI0-006b exit criteria pass

#### SCI0-006 — Source connectors: ChEMBL, BindingDB, PubChem BioAssay (Done)
- `data/sources/_base.py`: common `SourceConnector` ABC + `RawSourceRecord`
  (single internal type returned by all three connectors); `Admissibility`
  enum: TIER1_PRIMARY / TIER2_GATED / INADMISSIBLE
- `data/sources/_tier_map.py`: authoritative target→tier map; ChEMBL IDs,
  gene symbols, UniProt ACs; all four Tier 1 and six Tier 2 PI3K targets
  covered; case-insensitive gene lookup
- `data/sources/_chembl.py`: ChEMBL REST connector; Tier assigned at
  `_parse_activity()` before any record crosses the module boundary;
  inadmissible records returned with reason code, never silently dropped
- `data/sources/_bindingdb.py`: BindingDB REST connector; UniProt-first
  tier assignment with gene-name fallback
- `data/sources/_pubchem.py`: PubChem BioAssay PUG REST connector;
  gene-symbol tier assignment; right-censored inactives detected from
  ActivityOutcome field
- 20 new tests; all SCI0-006 exit criteria pass
- `chembl_adapter.py` retained (adjudication prototype); sources layer
  is the production path

#### SCI0-004 — Activity record schema (Done)
- `data/activity.py`: `BiochemicalRecord` (IC50/Ki/Kd) and `CellularRecord`
  (EC50 only) are distinct frozen dataclasses; pooling is rejected at
  construction (Constitution §2.3(3))
- `CensoredValue`: magnitude + unit + relational operator + censoring kind;
  operator/censoring consistency validated at construction
- `RelationalOperator`: =, >, <, >=, <= as StrEnum
- Biochemical/cellular separation enforced at the Python type level — no
  function accepting `BiochemicalRecord` can silently receive EC50

#### SCI0-005 — Censored-data handling (Done)
- `is_censored()` / `censored_fraction()` — interface for censored likelihood
  downstream; right-censored inactives retained, never imputed
- 10 new tests; all SCI0-004/005 exit criteria pass

#### SCI0-003 — Provenance record schema and writer (Done)
- `data/provenance/enums.py`: closed-vocabulary enums — `SourceType`, `Tier`,
  `MeasurementType`, `MeasurementClass`, `ExtractionTier`, `LocatorType`,
  `SourceConfidence`, `LicenseType`, `Unit`
- `data/provenance/models.py`: immutable frozen dataclasses — `Quantity`
  (Decimal + Unit; no bare floats), `SpanAnchor`, `SourceMetadata`, 
  `PublicationMetadata`, `AssayMetadata`, `ExtractionMetadata`,
  `ProvenanceRecord`; `SCHEMA_VERSION = "1.0.0"`
- `data/provenance/validator.py`: structural validation; raises
  `ProvenanceValidationError` with all problems at once; literature sources
  require a verified span anchor (SCI0-006b gate)
- `data/provenance/writer.py`: deterministic JSON serialization (sorted keys,
  Decimal in canonical fixed-point, explicit UTC offset); `serialize` /
  `deserialize` / `to_json_bytes`
- `data/models.py`: extended with `ActivityRecord` — links every measurement
  to a `provenance_id` (Constitution §3.3)
- 34 provenance tests (carried from verified supplementary package, namespace
  renamed from `pi3k_cel` to `orthosteric`); 81 total tests passing

#### SCI0-002 — `data/` package scaffold (Done)
- `config.py`: externalized configuration (ENG §5); no hardcoded URLs, paths,
  timeouts, or worker counts
- `exceptions.py`: complete domain exception hierarchy (`OrthoDataError` base;
  `ProvenanceError`, `TierViolationError`, `SnapshotIntegrityError`,
  `GovernanceException`, `NormalizationError`, `ConfigurationError`)
- `models.py`: shared domain enums — `DataTier`, `SourceDB`, `MeasurementKind`,
  `CensoringKind`, `RecordStatus` (StrEnum; no descriptors, no features)
- `tier2_gate.py`: enforces the Constitution §0.4 Tier 2 information barrier
  in code at the data-layer boundary
- `data/README.md`: full Constitution section mapping (§0.1, §0.4, §2.3, §3.3)
- `__init__.py`: `__all__` declared, sorted, typed; 18 public names
- Subpackage stubs: `sources/`, `harmonization/`, `provenance/`, `snapshots/`
- 47 tests passing (19 new scaffold tests + 28 existing adjudication tests)

## [0.1.0] — 2026-07-31

### Foundation (`FND-1` … `FND-11`)

Authorized by `ADR-0001` as a capped exception to Constitution §3.1.

- `FND-1` Canonical repository tree; `main` and `develop`; `.gitignore`; LICENSE; README
- `FND-2` `pyproject.toml`; Python pinned to `==3.12.*`; ruff, mypy, pytest, coverage
- `FND-3` `Makefile` with the seven ENG §22 target contracts
- `FND-4` `sealed/MANIFEST.md`; seal-timestamp check; `logs/{runs,audit}`; empty
  `logs/tier2_queries.jsonl`; scientific audit logger
- `FND-5` Configuration schema; **non-composable sealed threshold loader**
- `FND-6` pytest, coverage, `tests/` mirroring `src/`
- `FND-7` GitHub Actions running the complete ENG §20 Phase 1 set
- `FND-8` MkDocs strict; documentation tree; this changelog
- `FND-9` Import-graph contracts 1, 2 and 4 enforced; contract 3 written inert
- `FND-10` Run-metadata writer in `runtime/` (per `ADR-0004`)
- `FND-11` Clean-checkout validation

### Decisions

- `ADR-0001` Foundation authorization
- `ADR-0002` Governance closure — authority ordering; `PROJECT_SPECIFICATION` v0.1
- `ADR-0003` Public knowledge-only training policy (**Proposed**, awaiting Auditor)
- `ADR-0004` `FND-10` first module is the run-metadata writer, not the provenance writer
- `ADR-0005` Package name `orthosteric`

### Not implemented

No scientific capability. `data/`, `pocket/`, `features/`, `model/`, `train/`, `eval/`,
`explain/` and `kg/` are scaffolds owned by later objectives.
