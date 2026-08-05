# ADR-0010 [Architectural] — Phase C: Comparative Structural Learning Platform

**Status:** Accepted
**Date:** 2026-08-05
**Reversibility:** Costly — establishes the package taxonomy and import-layer
order for Phases C through F; all subsequent architectural work builds on it.
**Review trigger:** Any proposal to add a new top-level package, change the
import-layer order, or alter Phase C's scientific pipeline.

---

## Context

Phase B (evidence engineering, `SCI0-0xx`) is complete. The project has:

- An immutable, provenanced, content-hashed evidence corpus pipeline
  (`SCI0-001` through `SCI0-014c`).
- A corpus quality assessment layer that gates the SCI-0 → SCI-1 transition
  (`ADR-0009`, `GDR-003`).
- A decision policy layer whose outputs gate molecular design (`ADR-0008`).

Phase C begins the scientific core: transforming curated structural evidence
into a *comparative structural learning platform* whose representations explain
isoform selectivity rather than merely predict it.

The previous package taxonomy (`model/`, `train/`, `explain/`) was designed
before the Phase C architecture was specified. Those names do not express the
Phase C separation of concerns cleanly. All three are empty stubs; retiring
them and introducing Phase C names now costs nothing and avoids accruing a
permanent misnaming debt.

The Phase C architecture is also richer than a flat "add one package" change.
A generative endpoint (`generation/`) and a dedicated interpretation layer
(`interpretation/`) require placement decisions across the entire layer order.

---

## 1. The Phase C scientific pipeline

```
Experimental structure   AlphaFold fallback (governed)
         |                        |
         └────────── pocket/ ─────┘
                Structural preprocessing
                Pocket extraction
                         |
                       features/
                Structural representations
                  (fingerprints, contact maps,
                   descriptors, structural graphs)
                         |
                      learning/
                Comparative representation learning
                  (compound + α + β + γ + δ → joint repr.)
                         |
                   interpretation/
                Mechanistic explanation
                  (attribution, counterfactuals, summaries)
                         |
               ┌─────────┼─────────┐
            eval/      policy/   generation/
          Criteria    Decision     Molecular
          scoring      rules       design
```

The central inversion from Phase B: the project no longer centres on
`compound → activity`. It centres on:

```
compound
 + experimental structure
 + protein environment
 + comparative evidence
        ↓
structural representation
        ↓
comparative learning
        ↓
mechanistic explanation
        ↓
decision policy
        ↓
molecular generation
```

**Selectivity is explained rather than merely predicted.** Every architectural
choice in Phase C serves this objective.

---

## 2. Package taxonomy

### 2.1 Retired packages (empty stubs, no code loss)

| Package | Reason for retirement | Superseded by |
|---|---|---|
| `model/` | Generic name; Phase C's representational learning is fundamentally comparative, not a per-compound prediction model | `learning/` |
| `train/` | Subsumed; training orchestration is an internal concern of the learning layer, not a separately-importable responsibility | `learning/` |
| `explain/` | Constitution §4.7 discrete-rule interface is a subset of `interpretation/`'s responsibility; the broader mechanistic-explanation mandate covers it | `interpretation/` |

Both source (`src/orthosteric/{model,train,explain}/`) and test
(`tests/{model,train,explain}/`) directories are removed, being empty stubs.
The `ENG §2` protocol obligation to serve Constitution §4.7 is transferred to
`interpretation/` explicitly.

### 2.2 Existing packages — responsibilities clarified or expanded

| Package | Phase C role |
|---|---|
| `data/` | Evidence layer — unchanged (SCI0-001..SCI0-014c) |
| `quality/` | Corpus quality assessment — unchanged (ADR-0009) |
| `pocket/` | Structural preprocessing + pocket extraction. **Now active**; SCI-1 begins here |
| `features/` | Structural representation construction — fingerprints, contact maps, pocket descriptors, structural graphs, MD-ready representations. **Now active** as Phase C SCI-1's output layer |
| `eval/` | Project criteria scoring — S1–S10, degeneracy battery, calibration, seal reading. Unchanged in scope; SCI-2's model outputs land here for evaluation |
| `policy/` | Scientific decision rules — ADR-0008 prediction-level policies + ADR-0009 corpus-quality gate. Unchanged |
| `runtime/` | Utilities (software provenance, timing) — unchanged |

### 2.3 New packages (introduced by this ADR)

| Package | Phase C role | Constitution sections |
|---|---|---|
| `learning/` | Comparative representation learning (SCI-2). Subsumes `model/` + `train/`. Never `compound → activity`; always `compound + all isoforms → joint representation`. | §4.1–§4.7, §1.3 Option A |
| `interpretation/` | Mechanistic explanation (SCI-3). Subsumes `explain/`. Interaction attribution, residue importance, counterfactual interactions, comparative fingerprints, mechanistic summaries. | §4.7, §2.5, §5.4 |
| `generation/` | Molecular design (SCI-4). Deferred until SCI-3 is complete. Consumes comparative representations, mechanistic explanations, and Decision Policy outputs. | §1.3, §5.4, §6.2 |

---

## 3. Import-layer order

Highest layer may import from all layers below it; no layer may import from
above. This is mechanically enforced by `import-linter` and probe-verified on
merge.

```
generation/          SCI-4 — highest; consumes policy, interpretation, learning
policy/              ADR-0008 — consumes predictions, quality assessments
eval/                Criteria scoring — consumes learning + interpretation outputs
interpretation/      SCI-3 — consumes learning outputs
learning/            SCI-2 — consumes features + pocket + data
features/            SCI-1 (output) — consumes pocket + data
pocket/              SCI-1 (input) — consumes quality + data
quality/             ADR-0009 — consumes data.snapshots
data/                Evidence layer
runtime/             Utilities
```

Formal `.importlinter` order (top of layers list = highest):

```
generation, policy, eval, interpretation, learning, features, pocket, quality,
data, runtime
```

### 3.1 Placement rationale for each new package

**`generation/` at the top.** Generation consumes policy decisions (which
compounds to optimise for), interpretation outputs (mechanistic rationale to
respect), and representation outputs (seeds for design). No layer should
import generation's outputs; it is a terminal consumer. Placing it at the top
ensures the generative layer cannot be depended on by anything upstream.

**`learning/` below `eval/` and `interpretation/`.**  `eval/` needs to import
from `learning/` to score model outputs against the S-criteria. `interpretation/`
needs to import from `learning/` to attribute and explain what the model
learned. Both correctly sit above `learning/`.

**`features/` below `learning/`.** Learning consumes features; features must
not depend on learning (no feedback from representation into feature
construction — the feature layer must remain a pure structural measurement).

**`pocket/` below `features/`.** Feature construction consumes pocket
representations; pocket preprocessing must not depend on features (no
circular dependency between structure extraction and feature generation).

**`quality/` below `pocket/`.** Corpus quality assessment is a post-hoc
profile interpretation that must not influence the raw structural pipeline.

---

## 4. What each new package must NOT contain

These are mechanically enforceable via the import-layer contracts above and are
binding on all Phase C implementation.

| Package | Must NOT contain |
|---|---|
| `learning/` | Raw structure I/O; feature construction; corpus management; evaluation metrics (belong in `eval/`) |
| `interpretation/` | Model training; feature construction; corpus management; policy decisions |
| `generation/` | Training loops; structure featurization; corpus management; criteria evaluation (those belong in `eval/`) |
| `pocket/` | Feature selection; prediction; model training; interpretation |
| `features/` | Structure I/O; training loops; prediction; policy decisions |

---

## 5. Scientific invariants for Phase C (binding on all implementations)

These are derived from the Phase C Authorization and the Constitution. They
are not engineering preferences; they are architectural requirements.

1. **Experimental evidence always overrides predicted evidence.** Within
   `pocket/`, when both an experimental PDB structure and an AlphaFold fallback
   exist for the same isoform/construct, the experimental structure is
   preferred for all downstream representations. The fallback is used only when
   no admissible experimental structure exists (SCI0-007 rule, unchanged).
2. **Provenance is preserved at every stage.** Every feature vector, pocket
   representation, interaction fingerprint, contact map, and learned
   representation must carry a traceable reference back to: structure
   identifier, structure source, construct descriptor, software versions. This
   is enforced at the type level — every object produced by `pocket/` and
   `features/` carries a `StructureProvenance` or equivalent frozen dataclass.
3. **Determinism.** Every transformation in `pocket/` and `features/` must be
   deterministic: identical inputs with identical software produce
   identical outputs. Random seeds are forbidden unless explicitly governed.
   Determinism is verified by tests that run the same transformation twice and
   check byte-equality of outputs.
4. **Comparative learning principle.** `learning/` must never train a
   `compound → activity` model. Every training example must include all
   available isoforms. Per-isoform ablations and degeneracy tests (§4.3) verify
   this is not violated in practice.
5. **Measurement is separate from interpretation.** `pocket/` and `features/`
   produce measurements. `learning/` produces representations. `interpretation/`
   produces explanations. No module may do two of these things.
6. **No learned pocket detection.** Pocket definition is governed (Constitution
   §2.1, §A.6, §0.3); it must not be inferred by a model. The pocket boundary
   is the deterministic ligand-ensemble union, computed in `pocket/`.

---

## 6. SCI-1 implementation roadmap

SCI-1 populates `pocket/` and `features/`. It is the Phase C milestone that
produces the representation layer for SCI-2.

### 6.1 `pocket/` modules (structural preprocessing → pocket extraction)

| Module | Description | Depends on |
|---|---|---|
| `_structure_record.py` | Typed, frozen data models: `StructureRecord`, `StructureProvenance`, `ChainRecord`, `LigandRecord`, `ConstructDescriptor`, `ConformationalState` | Pure (dataclasses, stdlib only) |
| `_pocket_definition.py` | Governed pocket definition: `PocketDefinitionPolicy`, `PocketResidueSet`, `LigandEnsembleUnion`. Implements Constitution §2.1 ligand-ensemble-union rule. No apo allowed | `_structure_record` |
| `_residue_mapping.py` | Structure-based cross-isoform residue correspondence. Implements Constitution §2.1 "structure-based alignment, not sequence-only". Records Trp780/Met772/position-859 equivalences | `_structure_record`, `_pocket_definition` |
| `_rotamer_state.py` | Rotamer state representation for selectivity-relevant residues (Constitution §2.1: "rotamer states are part of the pocket, not noise") | `_structure_record` |
| `_pocket_geometry.py` | Volume, depth, enclosure, shape descriptors from pocket residue coordinates | `_pocket_definition` |
| `_solvent_accessibility.py` | Per-residue solvent-accessible surface area; ordered/displaceable water annotation | `_structure_record`, `_pocket_definition` |

### 6.2 `features/` modules (structural representations → ML-ready)

| Module | Description | Depends on |
|---|---|---|
| `_interaction_fingerprint.py` | Protein–ligand interaction fingerprints (PLIF): HB, salt bridge, π–π, cation–π, hydrophobic, water-mediated, halogen, metal. Each interaction carries residue + ligand atom + type + geometric params + provenance | `pocket/` |
| `_contact_map.py` | Residue–residue and ligand–residue contact maps; distance matrices; graph representations. Configurable distance cutoffs (no hard-coded biological definition) | `pocket/` |
| `_pocket_descriptor.py` | Pocket-level descriptors: volume, depth, enclosure, polarity, hydrophobicity, charge distribution, residue composition, flexibility indicators | `pocket/` |
| `_structural_graph.py` | Heterogeneous graph: residue nodes, ligand-atom nodes, water nodes; covalent/spatial/HB/electrostatic edges. Deterministic adjacency construction | `pocket/`, `_contact_map` |
| `_comparative_feature.py` | Multi-isoform feature set: one feature vector per (compound, α, β, γ, δ) tuple. Conserved-interaction flags, differential-interaction flags, missing-interaction indicators | All above |
| `_md_interface.py` | Placeholder interfaces for MD-ready representations: interaction-persistence placeholders, conformational-state labels, ensemble identifiers, trajectory metadata, state provenance | `pocket/` |

### 6.3 Governed configuration

SCI-1 introduces a `features/` configuration layer: `FeatureConfig` (a frozen
dataclass, versioned). All cutoffs, atom-typing rules, and interaction
definitions are governed configuration — never hard-coded constants — and are
recorded in every feature vector's provenance.

### 6.4 Milestone structure

- **Milestone 1** (this ADR's PR): Architecture, governance, package stubs.
  No feature-extraction code. Establishes the framework everything else builds
  on.
- **Milestone 2**: `pocket/` data models — `StructureRecord`,
  `StructureProvenance`, `PocketDefinitionPolicy`, `PocketResidueSet`
  (pure-Python, no external deps, fully tested).
- **Milestone 3**: `pocket/` geometric + rotamer — `_pocket_geometry`,
  `_rotamer_state`, `_solvent_accessibility` (introduces BioPython/numpy).
- **Milestone 4**: `pocket/` residue mapping — `_residue_mapping`
  (cross-isoform correspondence, Constitution §2.1).
- **Milestone 5**: `features/` interaction fingerprints — `_interaction_fingerprint`.
- **Milestone 6**: `features/` contact maps and graph — `_contact_map`,
  `_structural_graph`.
- **Milestone 7**: `features/` descriptors + comparative set —
  `_pocket_descriptor`, `_comparative_feature`.
- **Milestone 8**: `features/` MD interface stubs — `_md_interface`.

Each milestone is a PR that: passes all checks, adds tests, updates provenance,
and carries a CHANGELOG entry.

---

## 7. Constitution sections served by Phase C packages

| Package | Constitution sections |
|---|---|
| `pocket/` | §2.1 (pocket definition, C6, ligand-ensemble union, rotamer states), §0.3 (orthosteric sub-regions), §A.6 (C6 corollary) |
| `features/` | §4.2 (comparative feature requirements), §4.6 (Path A: correspondence-free input interface) |
| `learning/` | §4.1–§4.7 (full learning contract), §4.3 (degeneracy battery), §1.3 Option A |
| `interpretation/` | §4.7 (explanation interface), §2.5 (evidence classes), §5.3–§5.4 (knowledge extraction + promotion rules) |
| `eval/` | §1.4 (all S-criteria), §4.3 (degeneracy battery), §6.1 (rigor levels) |
| `policy/` | §2.3 (selectivity definition), §2.4 (uncertainty), §2.3(6) (potency floor) — unchanged |
| `generation/` | §1.3, §5.4, §6.2 (molecules as hypotheses), §9.5 |

---

## 8. Alternatives considered

| Alternative | Why not |
|---|---|
| Keep `model/`, `train/`, `explain/` | They are empty stubs. Their names do not express Phase C's science. `model/` suggests a scalar predictor; `learning/` expresses comparative representation. Renaming now costs nothing; renaming after real code exists costs considerably more |
| Put `interpret­ation/` above `generation/` | Generation must be able to consume interpretation outputs, so generation sits above interpretation in the import order. Swapping would prevent this |
| Put `learning/` above `eval/` | Evaluation needs to import learning outputs to score them; `eval/` must be above `learning/`. The reverse breaks the §1.4 criterion-scoring responsibilities |
| Fold `pocket/` into `features/` | ENG §2 requires mutually exclusive responsibilities. "Structural preprocessing + pocket extraction" (measurement of structure) is categorically distinct from "feature construction" (computing representations for ML). The pocket layer produces residue coordinates and annotations; the features layer consumes those to produce ML-ready tensors |
| Defer `generation/` package introduction | The layer order must be fixed now to avoid retroactive changes. `generation/` is introduced as an empty stub precisely so the import order is sealed and the architectural intent is recorded before SCI-2 begins |

---

## 9. Consequences

- `src/orthosteric/model/`, `src/orthosteric/train/`, `src/orthosteric/explain/`
  and their test counterparts are removed (empty stubs only).
- `src/orthosteric/learning/`, `src/orthosteric/interpretation/`,
  `src/orthosteric/generation/` and their test counterparts are created as
  documented stubs.
- `src/orthosteric/pocket/` and `src/orthosteric/features/` receive proper
  `README.md` and `__init__.py`; their test packages are extended. Real SCI-1
  code begins in Milestone 2.
- `.importlinter` layer order is updated (10 layers, same count, different
  composition: `generation`, `policy`, `eval`, `interpretation`, `learning`,
  `features`, `pocket`, `quality`, `data`, `runtime`).
- `ENGINEERING_STANDARDS.md` §2 package table is updated.
- `IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` §16 package ownership and dataflow
  diagram are updated.
- `IMPLEMENTATION_BACKLOG.md` gains Phase C sections.
- 465 existing tests are unaffected. No code is deleted that has tests against it.
