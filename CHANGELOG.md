# Changelog

Maintained from the first commit, never retrofitted (ENG §8).

## [Unreleased]

### SCI-0 — Data Acquisition Layer (in progress)

#### SCI0-001 — Backlog refinement (Done)
- Existing refinement document at `docs/specifications/SCI0-001-refinement-data-acquisition.md`
  adopted as the authoritative decomposition of `SCI0-002`–`SCI0-014b`
- Backlog status updated to `Done`

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
