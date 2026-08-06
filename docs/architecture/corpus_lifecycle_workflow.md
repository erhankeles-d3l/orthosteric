# Corpus Lifecycle Workflow

**Authority:** `data.corpus_lifecycle`; `policy._lifecycle_pipeline`; ADR-0003; GDR-004.  
**Audience:** Graduate students, new contributors, anyone running a training experiment.

---

## The fundamental rule

> **The corpus may evolve. A snapshot may not. A model generation must always
> identify exactly which snapshot produced it.**

---

## Overview

```
External sources (ChEMBL, BindingDB, PubChem, PDB)
        |
        v
  Acquisition / Harmonization / Curation
        |
        v
  CURRENT CORPUS  (mutable, updateable)
  data.corpus_lifecycle.CurrentCorpus
        |
  .freeze(builder, parent_snapshot_sha256=...)
        |
        v
  IMMUTABLE SNAPSHOT  (CorpusSnapshotV2)
  content-hashed SHA-256 identity
  parent lineage preserved
        |
  CorpusSnapshotRegistry.register(snapshot, data_mode)
        |
        v
  CorpusProfile  (corpus-derived engineering parameters)
  data.snapshots._profile.freeze_corpus_profile()
        |
        v
  CorpusQualityAssessment
  quality.CorpusQualityAssessor.assess(profile)
        |
        v
  GateDecision  (PROCEED / WARNING / REDESIGN / STOP)
  policy.CorpusQualityGatePolicy.evaluate(assessment)
        |
        v
  LifecyclePipelineResult
  policy.CorpusLifecyclePipeline.run(snapshot, data_mode, profile)
  .eligible_for_training: bool
  .result_sha256: str (deterministic)
        |
  if eligible:
  pipeline.register_model_generation(result, snapshot, mg_id, ...)
        |
        v
  ModelGenerationRecord
  .training_snapshot_sha  <- bound to exactly one snapshot
  .loss_function_id, .uncertainty_method_id, ...  (GDR-governed)
        |
        v
  [Training]  -- not yet implemented; awaits SCI2-002
        |
        v
  [Evaluation]  -- eval/ gates S2, S3, S4a, S6
        |
        v
  [Gate Report]  -- identifies model generation + snapshot SHA
```

---

## Step-by-step (once the training implementation is complete)

### Step 1 — Acquire or update the corpus

```python
from orthosteric.data.corpus_lifecycle import CorpusDataMode, CurrentCorpus

cc = CurrentCorpus(data_mode=CorpusDataMode.SCIENTIFIC_CORPUS)

# Add records from governed sources (ChEMBL, BindingDB, ...)
cc.add_records(records_from_chembl)
cc.update_source_version("chembl", "34")
cc.update_source_version("bindingdb", "2025-01")
```

### Step 2 — Freeze to an immutable snapshot

```python
from orthosteric.data.snapshots._builder import SnapshotBuilder
from orthosteric.data.snapshots._manifest import PolicyManifest, SoftwareProvenance

builder = SnapshotBuilder(
    software=SoftwareProvenance.collect(),
    policy=PolicyManifest.current(),
)

# First snapshot: parent_snapshot_sha256=None
# Subsequent updates: pass SHA of the previous snapshot for lineage
snap = cc.freeze(builder, parent_snapshot_sha256=None)
print(f"Snapshot: {snap.manifest.snapshot_id}")
print(f"SHA: {snap.manifest.snapshot_sha256}")
```

### Step 3 — Register and check lineage

```python
from orthosteric.data.snapshots._registry import CorpusSnapshotRegistry

registry = CorpusSnapshotRegistry()
registry.register(snap, CorpusDataMode.SCIENTIFIC_CORPUS)
```

### Step 4 — Compute corpus profile

```python
from orthosteric.data.graph import build_graph_stats_from_records
from orthosteric.data.audit import characterize
from orthosteric.data.strata import extract_strata
from orthosteric.data.snapshots._profile import freeze_corpus_profile

gs = build_graph_stats_from_records(accepted_records)
char = characterize(accepted_records, snapshot_sha256=snap.manifest.snapshot_sha256)
strata = extract_strata(accepted_records)
profile = freeze_corpus_profile(
    snapshot_sha256=snap.manifest.snapshot_sha256,
    graph_stats=gs,
    characterization=char,
    software=SoftwareProvenance.collect(),
    policy=PolicyManifest.current(),
    strata_report=strata,
)
```

### Step 5 — Run quality assessment and gate

```python
from orthosteric.policy._lifecycle_pipeline import CorpusLifecyclePipeline, LifecycleEligibility
from orthosteric.policy._corpus_gate import CorpusQualityGatePolicy
from orthosteric.quality._assessment import CorpusQualityAssessor
from orthosteric.quality._dimensions import (
    ConnectivityEvaluator, CoverageEvaluator, MissingnessEvaluator,
    PublicationConcentrationEvaluator, ScaffoldDiversityEvaluator,
    StructuralCoverageEvaluator, ConfidenceEvaluator,
)

pipeline = CorpusLifecyclePipeline(
    assessor=CorpusQualityAssessor([
        ConnectivityEvaluator(), CoverageEvaluator(), MissingnessEvaluator(),
        PublicationConcentrationEvaluator(), ScaffoldDiversityEvaluator(),
        StructuralCoverageEvaluator(), ConfidenceEvaluator(),
    ]),
    gate_policy=CorpusQualityGatePolicy(),
    registry=registry,
)

result = pipeline.run(snap, CorpusDataMode.SCIENTIFIC_CORPUS, profile)

print(f"Eligibility: {result.eligibility.value}")
print(f"Gate: {result.gate_decision.status.value}")
print(f"Eligible for training: {result.eligible_for_training}")
```

### Step 6 — Register a model generation (if eligible)

```python
if result.eligible_for_training:
    mg = pipeline.register_model_generation(
        pipeline_result=result,
        snapshot=snap,
        model_generation_id="MG-001",
        architecture_description="graph_transformer_v1",
        feature_config_version="v0.1-rule_missing",
        training_split_id="SPLIT-001",
    )
    print(f"Model generation: {mg.generation_id}")
    print(f"Bound to snapshot: {mg.training_snapshot_sha}")
else:
    print(f"Not eligible: {result.ineligibility_reason}")
```

### Step 7 — Train (SCI2-002, not yet implemented)

```python
# When SCI2-002 is implemented, training will look approximately like:
# trainer = ComparativeModelTrainer(model_generation=mg)
# trainer.train(snapshot=snap)   # snapshot SHA binds the training data
```

---

## Snapshot updates and lineage

When the corpus is refreshed with new data:

```python
# Previous snapshot SHA
sha_v1 = snap_v1.manifest.snapshot_sha256

# New records arrive
cc_v2 = CurrentCorpus(data_mode=CorpusDataMode.SCIENTIFIC_CORPUS)
cc_v2.add_records(all_records_including_new)
snap_v2 = cc_v2.freeze(builder, parent_snapshot_sha256=sha_v1)

# Diff between versions
from orthosteric.data.snapshots._diff import compute_snapshot_diff
diff = compute_snapshot_diff(snap_v1, snap_v2)
print(f"Added: {diff.records_added}, Removed: {diff.records_removed}")
print(f"Parent lineage valid: {diff.parent_lineage_valid}")
```

A new snapshot does NOT automatically retrain the model. Training remains an
explicit model-generation event (Step 6 above).

---

## Data mode rules

| Mode | Purpose | Eligible for training? |
|---|---|---|
| `SYNTHETIC_FIXTURE` | Unit tests, edge cases only | NEVER |
| `DEVELOPMENT_REAL` | Integration testing with small real sample | No (pipeline rejects) |
| `SCIENTIFIC_CORPUS` | Full production corpus from governed sources | Yes, after gate PROCEED/WARNING |

**SYNTHETIC_FIXTURE data must never enter the scientific training corpus.** The
pipeline enforces this at `LifecyclePipeline.run()` and at
`register_model_generation()`. `CurrentCorpus.validate_data_mode()` may also
be called explicitly.

---

## Corpus-dependent items still pending (CORPUS_REQUIRED)

These require real corpus evidence and are not resolved by this infrastructure:

| Item | What is needed |
|---|---|
| GGR-002a MMP switch set | Real within-study MMP pairs from ChEMBL/BindingDB |
| GGR-002b S4b sharpness multiplier | Within-study noise floor from actual corpus |
| GGR-010 Dual-inhibitor census | ChEMBL/BindingDB search for dual PI3K/mTOR agents |

---

## Machine infrastructure status

| Component | Status |
|---|---|
| Acquisition interfaces (sources/) | Architecture complete; real queries need corpus access |
| Harmonization (harmonization/) | Complete |
| Snapshot (snapshots/_builder.py) | Complete |
| Snapshot diff (snapshots/_diff.py) | Complete |
| Snapshot registry (snapshots/_registry.py) | Complete |
| Corpus profile (snapshots/_profile.py) | Complete |
| Quality assessment (quality/) | Complete |
| Gate policy (policy/_corpus_gate.py) | Complete |
| Lifecycle pipeline (policy/_lifecycle_pipeline.py) | Complete |
| Model generation record (learning/_interfaces.py) | Schema complete; training not implemented |
| Training (SCI2-002) | NOT YET AUTHORIZED — awaiting corpus prerequisites |
