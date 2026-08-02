# orthosteric.data

Public data acquisition, corpus management, and ADR-0003 adjudication layer.

## Constitution sections served

| Section | Requirement |
|---|---|
| §0.1 (tier architecture) | `models.DataTier`; `tier2_gate.assert_tier1` enforces the Tier 2 barrier |
| §0.4 (Tier 2 information barrier) | `tier2_gate.py` — raised in code, not only policy |
| §2.3 (selectivity definition) | `models.MeasurementKind` separates biochemical from cellular; never pooled |
| §3.3 (provenance) | Every record traces to a public source; right-censored inactives retained |
| ADR-0003 §2 (accepted sources) | `sources/` adapters: ChEMBL, BindingDB, PubChem BioAssay, PDB, literature |
| ADR-0003 §4 (ATP normalization) | `harmonization/cheng_prusoff.py` converts IC50 → Ki where [ATP] and Km known |
| AMENDMENT-ADR-0003 (computational adjudication) | `adjudication.py` implements the five decision procedures (v1.0) |

## Package layout

```
data/
  __init__.py          public API
  config.py            externalized configuration (ENG §5; no hardcoded values)
  exceptions.py        all domain exceptions
  models.py            shared enums and lightweight types
  tier2_gate.py        Tier 2 information-barrier guard (Constitution §0.4)
  README.md            this file
  corpus.py            evidence-record schema and snapshot system
  adjudication.py      ADR-0003 computational adjudication procedures (v1.0)
  chembl_adapter.py    ChEMBL REST adapter
  graph.py             compound x isoform evidence graph and statistics
  sources/             source-specific adapters (SCI0-006 and later)
  harmonization/       Cheng-Prusoff, deduplication, confidence scoring
  provenance/          provenance record schema and writer (SCI0-003)
  snapshots/           content-hashed immutable snapshot builder (SCI0-011)
```

## Non-goals

This package does **not** compute molecular descriptors, interaction fingerprints,
or any feature used by a learning model.  Those live in `features/` (SCI-1).
It does **not** contain model weights, training code, or evaluation logic.
AlphaFold structures are explicitly excluded: Constitution §2.1 requires experimental
structures with a bound ligand; predicted structures cannot meet this criterion.
