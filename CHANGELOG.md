# Changelog

Maintained from the first commit, never retrofitted (ENG §8).

## [Unreleased — GDR-005..GDR-009]

### Added — GDR-005 through GDR-009: SCI-2 methodological governance (2026-08-06)

Resolves GGR-003, GGR-004, GGR-005, GGR-007, GGR-008, GGR-009 from SCI2-001.
All five GDRs accepted by Project Owner (2026-08-06).

**Algorithm constants added** to `src/orthosteric/learning/_interfaces.py`:
- `AD_ALGORITHM_ID = "leverage_knn_tanimoto_95pct_v1"` (GDR-005)
- `ALPHAFOLD_TREATMENT_ID = "alphafold_include_source_indicator_v1"` (GDR-006)
- `UNCERTAINTY_METHOD_ID = "heteroscedastic_gaussian_v1"` (GDR-007)
- `UNCERTAINTY_COVERAGE = 0.95`, `UNCERTAINTY_Z_95 = 1.96` (GDR-007)
- `CENSORED_LIKELIHOOD_ID = "tobit1_censored_normal_v1"` (GDR-008)
- `LOSS_FUNCTION_ID = "tobit1_gaussian_nll_equal_weight_v1"` (GDR-009)
- `VALIDATION_PROTOCOL_ID = "scaffold_loso_cv_v1"` (GDR-009)
- `LOSS_N_OUTPUT_HEADS = 4`, `LOSS_EQUAL_WEIGHT = 1.0` (GDR-009, FROZEN)

**Decision records added**:
- `GDR-005`: per-isoform leverage k-NN AD with 95th-percentile self-calibrating threshold
- `GDR-006`: include AlphaFold features with explicit `is_alphafold` source indicator
- `GDR-007`: heteroscedastic Gaussian uncertainty; S4b interval = 2 x 1.96 x sigma_hat
- `GDR-008`: Tobit-1 censored normal; double-censored = INDETERMINATE (zero NLL contribution)
- `GDR-009`: equal-weight sum of 4 Tobit-1 Gaussian NLL heads; scaffold LOSO-CV protocol

**Tests added**: `tests/learning/test_gdr005_009_methodological_governance.py`
(19 tests, 796 total passing).

**Still CORPUS_REQUIRED**:
- GGR-002a: MMP switch set
- GGR-002b: S4b sharpness multiplier
- GGR-010: dual-inhibitor census


## [Unreleased]

### Added — SCI1-004: Protein-Ligand Interaction Fingerprints

**Files added:**
- `src/orthosteric/features/_interaction_fingerprint.py` — `InteractionType`
  (8 classes: hydrogen_bond, salt_bridge, pi_pi, cation_pi, hydrophobic,
  water_mediated, halogen_bond, metal_coordination), `InteractionStatus`
  (OBSERVED / ABSENT / UNAVAILABLE / RULE_MISSING / NOT_APPLICABLE),
  `InteractionEvidence`, `InteractionFingerprint`, `ComparativeFingerprint`,
  `FingerprintConfig`, `compute_interaction_fingerprint()`,
  `build_comparative_fingerprint()`

**Scientific rules:**
- Atom/element chemistry used to locate candidate interactions (H-bond donor/
  acceptor elements, aromatic ring atom names, hydrophobic atom identity,
  halogen/metal elements) is RULE_AVAILABLE — standard biochemistry, not a
  Constitution-governed threshold.
- All geometric classification thresholds (D...A distance, angle cutoffs,
  pi-pi centroid distance, salt-bridge cutoff, cation-pi cutoff, hydrophobic
  cutoff, halogen-bond geometry, metal coordination geometry) are
  RULE_MISSING by default — `FingerprintConfig` fields default to `None` and
  every candidate close enough to be geometrically plausible is recorded with
  raw geometry preserved and `status = RULE_MISSING`. No threshold is
  invented; each becomes configurable only once a GDR seals a value.
- Water-mediated interactions are only ever reported when an explicit `HOH`/
  `WAT` residue is present in the structure — absence of a direct contact is
  never inferred as water-mediated.
- AlphaFold fallback structures with no experimentally observed ligand pose
  produce `UNAVAILABLE` evidence for every interaction type; the
  `StructureSource` label is never relabelled as experimental.

**Comparative representation:** `ComparativeFingerprint` aligns per-isoform
`InteractionFingerprint`s by SCI1-003 canonical residue position (not raw PDB
numbering), so `canonical_comparison(pos)` returns the evidence at the same
homologous position across all supplied isoforms.

**Determinism:** all detection passes iterate protein/ligand atoms and pocket
residues in sorted order; `InteractionFingerprint.content_sha256()` /
`ComparativeFingerprint.content_sha256()` provide canonical-JSON content
hashes consistent with the SCI1-002/SCI1-003 provenance pattern.

**Tests added:** `tests/features/test_sci1004_interaction_fingerprint.py`
(32 tests, I1–I32: data model/enums, AlphaFold hierarchy, each interaction
class's RULE_MISSING/OBSERVED/ABSENT behaviour, water-mediated explicit-water
requirement, canonical-position propagation, comparative alignment,
determinism, provenance).

**Constraint:** no ML/learned interaction detection, no docking scores, no
affinity/selectivity values anywhere in this layer — pure structural
measurement only.

---

### Added — SCI1-004: Protein-Ligand Interaction Fingerprints

**Files added:**
- `src/orthosteric/features/_interaction_fingerprint.py` (820 lines)
- Updated `src/orthosteric/features/__init__.py` with all public exports
- `tests/features/test_sci1004_interaction_fingerprint.py` (32 tests, I1-I32)

**New public API:**
  `InteractionType` (8 values), `InteractionStatus` (5 values),
  `FingerprintConfig`, `InteractionEvidence`, `InteractionFingerprint`,
  `ComparativeFingerprint`, `compute_interaction_fingerprint()`,
  `build_comparative_fingerprint()`

**Eight interaction classes implemented:**

| Class | Detection | Threshold |
|---|---|---|
| Hydrogen bond | N/O donor/acceptor pairs, D...A distance | RULE_MISSING |
| Salt bridge | ARG/LYS/HIS vs ASP/GLU N/O pairs | RULE_MISSING |
| pi-pi | Ring centroid (RDKit SMILES) + residue ring tables | RULE_MISSING |
| Cation-pi | Protein ring vs ligand N; ligand ring vs protein cation | RULE_MISSING |
| Hydrophobic | Nonpolar C/S atoms by residue type | RULE_MISSING |
| Water-mediated | Explicit HOH only, never inferred | RULE_MISSING |
| Halogen bond | CL/BR/I elements; C-X...A angle approximated | RULE_MISSING |
| Metal coordination | Explicit metal elements (MG/ZN/CA/MN/FE/CU/NI/CO) | RULE_MISSING |

**Scientific governance:**
All classification thresholds in `FingerprintConfig` default to `None`
(RULE_MISSING). Raw geometry (distances, angles, dihedrals) is always
preserved. When a Governance Decision Record seals a threshold, the status
automatically classifies as OBSERVED/ABSENT without code changes.

**Comparative architecture:**
`ComparativeFingerprint.canonical_comparison(pos)` returns interaction
evidence at a given canonical residue position (from SCI1-003) across all
four isoforms simultaneously. This is the joint structural representation
required by Constitution §4.2.

**AlphaFold hierarchy enforced:**
If a structure's `StructureSource` is `ALPHAFOLD_GOVERNED_FALLBACK` and the
ligand is absent, all evidence records carry `UNAVAILABLE` status. The module
never fabricates interaction geometry.

**Five status values kept strictly distinct:**
`OBSERVED`, `ABSENT`, `UNAVAILABLE`, `RULE_MISSING`, `NOT_APPLICABLE` are
never collapsed.

---

### Added — SCI1-003: Cross-Isoform Residue Correspondence Data Model

**Files added:**
- `src/orthosteric/pocket/_residue_mapping.py` — `ResidueCorrespondenceTable`,
  `CorrespondenceAssignment`, `CorrespondenceStatus`, `AnchorPosition`,
  `TIER1_ISOFORMS`, `build_correspondence_table()`, `make_anchor_assignments()`,
  `annotate_pocket_residue_set()`

**Scientific rules:**
- `AnchorPosition.ALPHA_859 / TRP780 / MET772` — three Constitution §0.3/§2.1
  named positions (RULE_AVAILABLE — explicitly stated in the charter)
- Reference isoform always PI3Kalpha (RULE_AVAILABLE — §2.1 numbering convention)
- Structural alignment algorithm: `RULE_MISSING/GOVERNANCE_DECISION_REQUIRED` —
  `alignment_algorithm = "RULE_MISSING"` by default; `alignment_governance_note`
  is non-empty until a GDR seals the algorithm
- `CorrespondenceStatus`: MAPPED / PROVISIONAL / MANUALLY_VERIFIED / UNMAPPED / ANCHOR
  (RULE_AVAILABLE — vocabulary derived from Constitution §2.1's "manually verified"
  requirement)

**Tests added:** `tests/pocket/test_sci1003_residue_mapping.py` (19 tests, M1–M14)

**Constraint:** `annotate_pocket_residue_set()` does NOT mutate the frozen
`PocketResidueSet`; it returns a list of `(residue_id, canonical_position,
status)` triples. The alignment computation itself is deferred — no structural
superimposition algorithm is executed without a sealed GDR.

---

### Added — SCI1-002: Pocket Geometry, Rotamer State, and Solvent Accessibility

**Files added:**
- `src/orthosteric/pocket/_pocket_geometry.py` — `PocketGeometry`, `AtomCoordinate`, `GeometryConfig`, `compute_pocket_geometry()`
- `src/orthosteric/pocket/_rotamer_state.py` — `PocketRotamerStates`, `ResidueRotamerState`, `ChiAngle`, `RotamerAvailability`, `compute_pocket_rotamer_states()`
- `src/orthosteric/pocket/_solvent_accessibility.py` — `PocketSASA`, `ResidueSASA`, `SASAConfig`, `SASAAvailability`, `compute_pocket_sasa()`

**Files modified:**
- `src/orthosteric/pocket/__init__.py` — exports all SCI1-002 symbols
- `pyproject.toml` — added `biopython>=1.84`, per-file mypy/ruff overrides for untyped BioPython

**Dependency added:** `biopython>=1.84` (SCI1-002 structural preprocessing)

**Tests added:** `tests/pocket/test_sci1002_structural_geometry.py` (26 tests, exit criteria G1–G9, R1–R8, S1–S8)

**Scientific rules:**
- `GOVERNED_PROBE_RADIUS_ANGSTROM = 1.4` — Lee & Richards 1971 (RULE_AVAILABLE)
- `TIEN_2013_MAX_ASA` — Tien et al. 2013 relative SASA normalization (RULE_AVAILABLE)
- `CHI_ATOM_NAMES` — Dunbrack 1993 chi-angle atom definitions (RULE_AVAILABLE)
- Pocket volume: `RULE_MISSING/GOVERNANCE_DECISION_REQUIRED` — `volume_angstrom3` always `None`
- Rotamer classification: `RULE_MISSING/GOVERNANCE_DECISION_REQUIRED` — `rotamer_label` always `None`

---


### SCI-0 — Data Acquisition Layer (in progress)

#### ADR-0010 / SCI1-000..SCI1-001 — Phase C: Comparative Structural Learning Platform Architecture + SCI-1 Milestone 2 (Done)

**Architecture (ADR-0010, SCI1-000)**
- Phase C Authorization implemented: project transitions from evidence
  engineering to structural representation learning
- New package taxonomy with import-layer enforcement:
  `generation/` > `policy/` > `eval/` > `interpretation/` > `learning/` >
  `features/` > `pocket/` > `quality/` > `data/` > `runtime/`
- Retired empty stubs `model/`, `train/`, `explain/` (superseded by
  `learning/`, `learning/`, `interpretation/` respectively) — zero code lost
- Created stub packages: `learning/`, `interpretation/`, `generation/`
  (src + tests), with documented responsibilities and ENG §2 entries
- Updated `.importlinter` Contract 3 (Tier 2 protection) from `train/` to
  `learning/`
- Updated ENG §2 package table, `IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` §16
  (dataflow + state machine + package ownership), `IMPLEMENTATION_BACKLOG.md`
  (Phase C + SCI-1..SCI-4 sections)
- ADR-0010 documents: Phase C pipeline, package taxonomy, layer order
  rationale, 6 scientific invariants (no apo pocket, no learned pocket
  detection, provenance mandatory, determinism, comparative learning
  principle, measurement/interpretation separation), 7-milestone SCI-1 roadmap

**SCI-1 Milestone 2: `pocket/` data models (SCI1-001)**
- `pocket/_structure_record.py`: typed frozen data models with zero external
  dependencies — `StructureRecord`, `StructureProvenance`,
  `ConstructDescriptor`, `LigandRecord`, `ChainRecord`, `ResidueRecord`,
  `StructureSource`, `ConstructClass`, `ConformationalState`,
  `LigandShapeClass`, `DataTier`, `make_record_id()`
  - Experimental-priority invariant encoded in `StructureSource` — code
    cannot silently treat AlphaFold as experimental (validated in constructor)
  - `LIGAND_BOUND` state with no ATP-site ligands is a type-level error
    (Constitution §2.1 apo prohibition, §A.6 C6 corollary)
  - `has_propeller_ligand`: distinguishes propeller-shaped (induced
    specificity pocket) from flat ligands (Constitution §0.3, S6)
  - `content_sha256()`: deterministic content hash; `make_record_id()`
    stable against mutation-tuple ordering
  - `ConstructDescriptor.construct_class` records regulatory-subunit
    composition — Constitution §2.1 construct policy (mixed constructs must
    be flagged, never silently pooled)

- `pocket/_pocket_definition.py`: governed pocket definition with all 4
  Constitution §2.1 rules — `PocketDefinitionPolicy`, `PocketResidueSet`,
  `PocketResidue`, `SubRegion`
  - `GOVERNED_DISTANCE_CUTOFF_ANGSTROM = 5.0` (Constitution §2.1) — a
    named constant modifiable only via GDR, never via an undocumented kwarg
  - `default_pocket_definition_policy()` enforces apo prohibition,
    propeller-coverage requirement, governed cutoff and stability threshold
  - `SubRegion` enum: all Constitution §0.3 sub-regions (adenine hinge,
    affinity pocket, **specificity pocket**, tryptophan shelf, water network)
  - `PocketResidue.present_with_propeller_ligand`: records which residues
    are part of the induced specificity pocket (C6 corollary — cannot be
    seen in apo/flat-ligand structures)
  - `PocketDefinitionPolicy.validate_input_structure()`: checks apo
    prohibition and AlphaFold provenance flagging without raising (caller
    decides whether to exclude or flag)

- 38 new tests (22 structure-record + 16 pocket-definition); 503 total passing

#### ADR-0009 / GDR-003 / CQA-001 — Corpus Quality Assessment Layer (`quality/`) (Done)
- New architectural layer `src/orthosteric/quality/`, authorized by `ADR-0009`
  [Architectural]. Interposes between the descriptive `CorpusProfile`
  (`GDR-002`) and the Decision Policy Layer (`policy/`, `ADR-0008`) — three
  distinct responsibilities, none merged:
  `CorpusProfile` (descriptive) → `CorpusQualityAssessment` (interpretive,
  `quality/`) → `CorpusQualityGatePolicy` (decision, `policy/`) →
  `PROCEED`/`WARNING`/`REDESIGN`/`STOP`
- **Firewall mechanically verified by probe, both directions:** making
  `data/` import `quality/`, or `quality/` import `policy/`, breaks the
  `.importlinter` layers contract and fails CI. `quality/` sits directly
  above `data/` (so `data/` cannot import it — a profile cannot depend on
  its own interpretation) and below `policy/` (so `policy/` can consume it)
- `GDR-003` [Scientific]: every dimension rule is one of exactly two kinds —
  a **structural/definitional fact** (true or false by the quantity's own
  definition, e.g. "does at least one four-isoform-complete compound exist")
  or an **already-governed magnitude cited by reference** (the one instance:
  R1's "< 8 scaffold families," fixed at the Constitution's original
  authorship, not invented here). No new magnitude threshold is introduced
  anywhere in this change
- 7 dimension evaluators: `ConnectivityEvaluator`, `CoverageEvaluator`,
  `ScaffoldDiversityEvaluator`, `PublicationConcentrationEvaluator`,
  `ConfidenceEvaluator`, `MissingnessEvaluator`, `StructuralCoverageEvaluator`
  (extension-point stub, always `NOT_YET_AVAILABLE` until `SCI0-018` exists)
- `CorpusQualityAssessor` mirrors `ADR-0008`'s `PolicyEngine` extensibility
  pattern exactly: register an evaluator, no existing code changes
  (test-verified with a demonstration dimension)
- `policy/`'s new `CorpusQualityGatePolicy`: consumes only a
  `CorpusQualityAssessment`, never raw statistics; applies `GDR-003` §4's
  categorical aggregation rule (`STOP` if any dimension `STRUCTURALLY_
  DEGENERATE`; else `REDESIGN` if any `GOVERNED_THRESHOLD_NOT_MET`; else
  `WARNING` if any `WARNING`/`INSUFFICIENT_DATA`/`NOT_YET_AVAILABLE`; else
  `PROCEED`) — no weighted score anywhere. Does not implement the `Policy`
  ABC (`ADR-0008`): the input/output shape is genuinely different from a
  per-compound prediction decision, and forcing one interface onto both
  would hide that difference rather than express it
- **A defect discovered and fixed during implementation:** `GraphStats.
  within_study_four_isoform` (`SCI0-014`, already merged) counts compounds
  in a panel where all four isoforms are collectively represented
  *somewhere*, not compounds *individually* measured across all four — a
  materially weaker quantity than the Constitution's actual `N_w`.
  `CorpusProfile.engineering_parameters` gains a corrected field,
  `n_complete_compounds` (`StratumReport.total_complete_compounds`, verified
  correct by direct construction). `quality/`'s `CoverageEvaluator` uses the
  corrected field; `n_w` is retained for continuity, now documented with the
  discovered gap. `graph.py` itself is not modified — flagged for a future
  pass, out of scope here
- **Closes the remaining R1 threshold dependency `GDR-002` left open:** every
  rule touching `N_c`/`N_b`/`N_w` is a structural zero/non-zero check, never
  a magnitude comparison. No fixed-threshold dependency on those three
  quantities remains anywhere in the interpretation pipeline
- `CorpusProfile` extended (additive, backward-compatible): reserved
  `structural_coverage: StructuralCoverageStats | None` field (`None` by
  default; no PDB or AlphaFold record read anywhere in this change);
  `PROFILE_ALGORITHM_VERSION`/`CORPUS_PROFILE_SCHEMA_VERSION` bumped
  (`_gdr002` → `_adr0009`, v1 → v3) since the profile's shape changed twice
  (structural-coverage field, then the `n_complete_compounds` fix)
- `assessment_content_sha256` and `GateDecision` both exclude their
  respective timestamps from the content hash, per the `SCI0-011` precedent;
  full traceability chain verified test-side: Decision → Assessment →
  Profile → Snapshot
- `.importlinter`: 10th layer (`quality/`, between `pocket/` and `data/`);
  ENG §2 package table + layer-order note; `IMPLEMENTATION_PROTOCOL_
  SCIENTIFIC.md` §16 dataflow diagram extended; backlog: new "Corpus Quality
  Assessment Layer" section (`CQA-001`, `Done`), no `SCI-N` stage created or
  renumbered
- 50 new tests (22 profile incl. 4 regression, 18 dimension, 14 assessment,
  11 gate-policy — note: some overlap across files); 465 total passing

#### GDR-002 — `N_c`, `N_b`, `N_w` reclassified as corpus-derived engineering parameters (Done)
- `docs/governance/decision-records/GDR-002-corpus-derived-engineering-parameters.md`:
  `N_c` (largest connected component), `N_b` (bridging compounds), `N_w`
  (within-study four-isoform compounds) are corpus-derived engineering
  parameters, not literature-derived scientific thresholds — computed
  deterministically from an already-frozen `SCI0-011` snapshot; never
  optimized during model development, never fitted to model performance,
  never estimated from the literature
- **Two governance categories made explicit:** corpus-derived engineering
  parameters (`N_c`, `N_b`, `N_w`, corpus/graph/scaffold/publication
  statistics) vs. scientific parameters (ATP Km, Cheng–Prusoff, biochemical
  conversion rules) — the latter explicitly **not** touched by this record;
  AUDITOR-5 unchanged
- `data/snapshots/_profile.py`: `freeze_corpus_profile()` — pure function over
  already-computed `GraphStats` (SCI0-014) and `CharacterizationReport`
  (SCI0-014b); no raw-record parameter exists on the function, so it cannot
  be run against partially curated data by construction
- `CorpusProfile` — frozen, content-hashed (`profile_sha256`), references the
  `SCI0-011` snapshot by SHA-256 (foreign key; `SnapshotManifestV2` itself not
  reopened). Embeds `SoftwareProvenance` and `PolicyManifest` reused from
  `SCI0-011` (not redefined), plus `profile_algorithm_version` (versions the
  *computation method* independent of upstream policy versions)
- Freeze timestamp excluded from `profile_sha256`, per the `SCI0-011`
  precedent — identical inputs yield an identical hash regardless of when
  frozen
- **Two definitional gaps flagged, not silently resolved:** (1) `N_w`
  compound-count (Constitution's original unit, `GraphStats.
  within_study_four_isoform`) vs. strata-count (Project Owner's phrasing,
  `StratumReport.usable_strata`) — both frozen under distinct names
  (`n_w`, `n_complete_strata`); (2) scaffold-family diversity *within the
  largest connected component* — not computed by any existing module;
  recorded as `None`, never substituted with `SCI0-014b`'s corpus-global count
- **R1 (Constitution Part VIII, Amendment A10) consequence stated explicitly:**
  a condition of "measured value < measured value" is vacuous, so R1's
  kill-switch function for `N_c`/`N_b`/`N_w` cannot survive. Replaced by an
  informed human decision at the existing `SCI0-031` gate ("proceed / redesign
  / stop"), informed by the frozen `CorpusProfile`. The "< 8 scaffold
  families" disjunct is **unchanged** — fixed at the Constitution's original
  authorship, not one of the outstanding placeholders
- **S4b relocated, not reclassified:** remains a methodological/model-design
  parameter per the Project Owner's explicit instruction; moves to the
  Decision Policy Layer (`ADR-0008`, `policy/`), versioned, fixed per
  experiment, revisable only via a future Governance Decision Record. Not
  implemented as a policy class yet — no `SCI0-016` noise floor exists for it
  to operate against
- `CONSTITUTION_AMENDMENT_SET_v4.7.md` Amendments A1 (S4b) and A10 (R1):
  dated revision notes appended beneath the original "Was/Becomes" text
  (preserved verbatim, not rewritten)
- `docs/IMPLEMENTATION_BACKLOG.md`: `SCI0-028` scope revised to verification
  (determinism/reproducibility) rather than sealing; ordering constraint
  against `SCI0-015` revised — no longer applies to `N_c`/`N_b`/`N_w`;
  new `SCI0-014c` row for corpus-profile freezing
- `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md`: third-pass addendum;
  historical classification tables preserved, not deleted
- `sealed/MANIFEST.md`: `SCI0-028`'s expected-artefacts row revised — ATP Km
  source is now the only remaining item
- **`SCI0-015` no longer blocked by `SCI0-028`** (the specific reason for that
  ordering constraint no longer applies). Real corpus acquisition remains
  separately unauthorized
- 18 new tests; 415 total passing

#### ADR-0008 / DPL-001 — Decision Policy Layer (`policy/`) (Done)
- New architectural layer `src/orthosteric/policy/`, authorized by `ADR-0008`
  [Architectural]. Operates exclusively on model outputs; never modifies
  evidence, harmonized data, features, or learned models
- **Two governance conflicts found during review and resolved in the ADR, not
  papered over:**
  1. The request labelled this `SCI-4`, but `SCI-4` is already *Cross-family
     transfer* — Constitution §9.6, criterion **S7**, which carries the
     project's entire generality claim under §9.6's binding honesty clause.
     Implemented as an **unnumbered architectural layer** instead (consistent
     with `data/`, `features/`, `model/`, `eval/`, `explain/`), so no stage is
     renumbered and S7 is untouched. `SCI-3` is likewise *Knowledge extraction*,
     not "prediction"
  2. ENG §2's package-responsibility table is authoritative and exhaustive;
     adding `policy/` required amending it, which per ENG §1 required an
     Accepted ADR first
- **Criterion firewall (Constitution §1.4):** `policy/` is the *highest* layer
  in `.importlinter`, so no lower layer may import it — a prioritization
  threshold mechanically cannot reach evidence, features, training, prediction,
  or criterion evaluation. Every `PolicyOutcome`/`DecisionRecord` carries
  `criterion_eligible = False`. Policy thresholds are **not** sealed artefacts
  and are not added to `sealed/MANIFEST.md`
- Configurable `SelectivityTierTable` — defaults 10× / 30× / 100× / 300× /
  1000× as *configuration*, not implementation constants; validated for strictly
  ascending order and unique names
- Selectivity computed in log space per Constitution §2.3(4)
  (`Δ = pAct_ref − pAct_x`), with fold-change `10 ** Δ` exposed as a derived
  view — mathematically identical to `Activity_x / Activity_ref`. Full
  `SelectivityVector` retained (per-isoform Δ, folds, and limiting isoform), so
  nothing is lost to the scalar `Smin`
- **Governed gates applied before any tier is assigned**, all sourced from the
  Constitution rather than invented: §2.3(6) potency floor → `UNDEFINED_POTENCY_
  FLOOR` (undefined, *not* a low tier); §2.2 Indeterminate → `UNDEFINED_
  INDETERMINATE` (never read as sparing); §2.3(3) mixed biochemical/cellular →
  `UNDEFINED_MIXED_CLASS`; missing point estimate → `UNDEFINED_MISSING_
  PREDICTION` (missing ≠ inactive)
- `ConfidencePolicy` composes joint confidence as a **product** per §2.4, never
  `min` — §2.4 states the min-rule is wrong; the correlation assumption is
  recorded in `detail` as §2.4 requires
- `UncertaintyPolicy` **abstains** when no label-noise floor is configured
  rather than defaulting to §2.4's "typically ≥ 0.3 log units", which is a
  general observation, not this project's measured floor (an `SCI0-016` output)
- **AUDITOR-5 interaction surfaced, not worked around:** there is no
  cross-isoform-harmonized potency metric — Cheng–Prusoff is blocked. Every
  `PredictionInput` carries a required `NormalizationStatus`; tiers computed
  from `NOT_NORMALIZED` inputs still compute but carry `AUDITOR5_ADVISORY` into
  the `DecisionRecord`, marked as not comparable across differing `[ATP]`. No
  ATP Km inferred
- Provenance per decision: policy id + version, full embedded threshold
  configuration, software provenance (reusing `SCI0-011`'s `SoftwareProvenance`),
  model version, evidence snapshot SHA-256, prediction id, timestamp.
  `decision_content_sha256` **excludes the timestamp**, per the `SCI0-011`
  precedent, so identical inputs yield an identical hash
- Extensibility: `Policy` ABC + engine registration; a new policy requires no
  change to any existing module (test-verified). `ADMETPolicy` /
  `DevelopabilityPolicy` deliberately not implemented — no supporting evidence
  layer exists and any threshold would be invented
- Updated: `.importlinter` (9th layer), ENG §2 package table + layer order,
  `IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` §16 (dataflow diagram + stage-vs-layer
  distinction + package-ownership row), backlog, `policy/README.md`
- 78 new tests; 397 total passing

#### GDR-001 — Duplicate-resolution policy resolved via literature review (Done)
- `docs/governance/decision-records/GDR-001-duplicate-resolution-policy.md`:
  resolves AUDITOR-3 (SCI0-028 item 5/6). Under Project Owner authorization
  (2026-08-05) to resolve scientific-methodology questions via comprehensive
  literature review where a single, well-supported choice exists
- **Decision:** within a fully-specified evidence-identity group (compound ×
  isoform × construct × organism × measurement type × measurement class ×
  assay × source), ≥2 distinct exact values are combined by **median**
- Cited evidence: Kramer et al. *JMC* 2012; Landrum & Riniker *JCIM* 2024
  ("Combining IC50 or Ki Values From Different Sources Is a Source of
  Significant Noise"); Schiebroek/Landrum/Riniker *JCIM* 2025; Huber, *Robust
  Statistics*; three independent bioactivity-curation pipelines using median
  for this exact operation (Rep3Net, an RL/chemical-LM study, Bioactivity-
  explorer)
- **Scope, explicit:** literal replicates only (same source + assay); does
  NOT authorize cross-study/cross-source combination (unaffected: Constitution
  §2.3(1), SCI0-013's within-study stratum); does NOT resolve AUDITOR-5
  (ATP Km / Cheng-Prusoff, remains `INSUFFICIENT_EVIDENCE`)
- **Alternatives considered and rejected:** mean (not robust to documented
  outlier pattern), most-recent (no literature support; Ki/IC50 is a
  physical constant, not time-varying), highest-confidence-only (discards
  corroborating replicate information; confidence's role is cross-group, per
  SCI0-010, not intra-group)
- **Accompanying correctness fix:** `_deduplicator.py`'s identity key
  extended with `construct` and `organism` (fields the schema already
  carried but the key omitted) — prevents wild-type/mutant or cross-species
  blending; strictly narrows existing groups
- `GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN` introduced;
  `Deduplicator.POLICY_ID` bumped to
  `sci0009_identity_grouping_median_replicates_v2_gdr001` (propagates a new
  SCI0-011 snapshot hash for any corpus rebuilt after this change)
- `_confidence.py`'s `duplicate_agreement` component updated: the
  disagreement signal still fires for `RESOLVED_REPLICATE_MEDIAN` groups —
  resolving how to combine differing values doesn't mean they stopped differing
- `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md` revised: item 5/6
  marked `RESOLVED`; N_c/N_b counting-basis clarified as unique-compound
  (InChIKey) identity, non-numeric, per Amendment A10's own text
  distinguishing "compounds" from "scaffold families"; additional ATP Km
  literature search performed (negative result — located a PI3Kα/β Km for
  the PI lipid substrate, not ATP; explicitly not usable, recorded to
  prevent future confusion)
- N_c, N_b, N_w, S4b sharpness factor, and ATP Km source remain
  `RULE_MISSING`. `SCI0-015` remains not authorized
- 5 new/updated tests (construct/organism stratification, median resolution,
  median-vs-censoring contradiction checks); 319 total passing

#### SCI0-028 — Governance gap review (Blocked; report only, no code)
- `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md`: reviewed all six required
  seals (`N_c`, `N_b`, `N_w`, S4b sharpness factor, duplicate-resolution policy,
  per-isoform ATP Km source) against Constitution, ADR-0003, the AUDITOR-2/3/5
  evidence documents, and `sealed/MANIFEST.md`
- **Result: 0/6 items RULE_AVAILABLE.** All six classified RULE_MISSING; no
  numeric threshold, similarity measure, or scientific policy invented
- Flagged an internal documentation inconsistency: `adjudication.py` marks
  AUDITOR-3 (duplicate-resolution) `RESOLVED`, while `_deduplicator.py`'s
  docstring and the AUDITOR brief's own checklist mark it open — recorded as
  requiring a Governance Decision Record to reconcile, not resolved here
- `SCI0-015` remains **not authorized to begin** (backlog ordering constraint
  unsatisfied)
- Terminology: this report and future authored documents use "Governance
  Decision Record" / "Governance Amendment" in place of "Independent
  Scientific Auditor sign-off," per Project Owner direction (2026-08-05).
  Historical documents are quoted verbatim and not retroactively edited
- Backlog corrected: `SCI0-014` row was missing its `Done` marker (oversight
  from the SCI0-014 merge); corrected in this pass

#### SCI0-014b — Dataset characterization (Done)
- `data/audit.py`: `characterize(records, snapshot_sha256)` — pure descriptive
  analysis; never modifies records; output attached to snapshot SHA-256
- `IsoformStats`, `ScaffoldStats`, `ConnectivityStats` (delegated to SCI0-014),
  `ConfidenceStats`, `PublicationStats`, `MissingnessMatrix`, temporal counts,
  assay-format and quantity-type distributions
- Binding invariant: output is read-only; may NOT inform split/stratum/threshold
  decisions
- 13 new tests

#### SCI0-014 — Measurement-graph construction (Done)
- `data/graph.py`: `build_graph_stats_from_records()` — primary SCI0-014 API;
  union-find connected components over compound co-assay graph
- `largest_connected_component` (N_c candidate), `bridging_compounds`
  (N_b candidate), `within_study_four_isoform` (N_w candidate), `StudyCluster`
  structure per `(study_id, assay_id)`
- Legacy `build_graph_stats()` wrapper retained for `corpus.py` compatibility
- All statistics reproducible given the same input
- 22 new tests

#### SCI0-001 — Backlog refinement (Done)
- Existing refinement document at `docs/specifications/SCI0-001-refinement-data-acquisition.md`
  adopted as the authoritative decomposition of `SCI0-002`–`SCI0-014b`
- Backlog status updated to `Done`

#### SCI0-008c — Identifier harmonization (Done)
- `data/harmonization/_identifier_harmonizer.py`: `IdentifierHarmonizer`
  assigns deterministic internal IDs (InChIKey from SCI0-008b output) and
  cross-references compounds across source databases
- Internal ID = InChIKey: source-agnostic, deterministic, 27-char, stereo-
  preserving; follows directly from SCI0-008b guarantee + spec requirement
- Cross-reference accumulation: `cross_refs: dict[source_db, [source_ids]]`
  — multiple source IDs for the same InChIKey merged without conflict
- Conflict detection: same `source_compound_id` → different InChIKey → 
  `ConflictStatus.CONFLICT` + `StructureConflict` record; never silently merged
- Fail-closed: invalid SMILES / no SMILES → `ConflictStatus.UNRESOLVED`;
  all records returned, none dropped
- Stereoisomers preserved: enantiomers and E/Z isomers get distinct InChIKeys
  (inherits SCI0-008b guarantee, verified by exit-criterion tests)
- RDKit version propagated to `HarmonizedCompound.rdkit_version` (SCI0-011)
- 15 new tests; 194 total passing

#### SCI0-008b — Chemical standardization (RDKit) (Done)
- `data/harmonization/_chem_standardizer.py`: `ChemicalStandardizer` with
  deterministic 9-step pipeline: parse → metal disconnect → salt strip →
  normalize → uncharge → canonical tautomer → sanitize → canonical SMILES
  → InChI/InChIKey
- `SetRemoveSp3Stereo(False)` + `SetReassignStereo(True)` on tautomer
  enumerator — stereoisomers remain distinct (exit criterion 1)
- `StandardizedStructure` frozen dataclass: canonical_smiles, inchi, inchikey,
  rdkit_version, content_hash, salt_stripped, steps_applied — no descriptor
  fields (exit criterion 2)
- Output is deterministic given same SMILES + RDKit version (exit criterion 3)
- RDKit version recorded in every output (`rdkit_version` field) per SCI0-011:
  RDKit version affects InChIKey so toolchain is part of corpus identity
- Failed records returned with status + reason, never silently dropped
- rdkit>=2024.3 added to project dependencies
- 18 new tests; 179 total passing

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

#### GDR-001 — Duplicate-resolution policy resolved via literature review (Done)
- `docs/governance/decision-records/GDR-001-duplicate-resolution-policy.md`:
  resolves AUDITOR-3 (SCI0-028 item 5/6). Under Project Owner authorization
  (2026-08-05) to resolve scientific-methodology questions via comprehensive
  literature review where a single, well-supported choice exists
- **Decision:** within a fully-specified evidence-identity group (compound ×
  isoform × construct × organism × measurement type × measurement class ×
  assay × source), ≥2 distinct exact values are combined by **median**
- Cited evidence: Kramer et al. *JMC* 2012; Landrum & Riniker *JCIM* 2024
  ("Combining IC50 or Ki Values From Different Sources Is a Source of
  Significant Noise"); Schiebroek/Landrum/Riniker *JCIM* 2025; Huber, *Robust
  Statistics*; three independent bioactivity-curation pipelines using median
  for this exact operation (Rep3Net, an RL/chemical-LM study, Bioactivity-
  explorer)
- **Scope, explicit:** literal replicates only (same source + assay); does
  NOT authorize cross-study/cross-source combination (unaffected: Constitution
  §2.3(1), SCI0-013's within-study stratum); does NOT resolve AUDITOR-5
  (ATP Km / Cheng-Prusoff, remains `INSUFFICIENT_EVIDENCE`)
- **Alternatives considered and rejected:** mean (not robust to documented
  outlier pattern), most-recent (no literature support; Ki/IC50 is a
  physical constant, not time-varying), highest-confidence-only (discards
  corroborating replicate information; confidence's role is cross-group, per
  SCI0-010, not intra-group)
- **Accompanying correctness fix:** `_deduplicator.py`'s identity key
  extended with `construct` and `organism` (fields the schema already
  carried but the key omitted) — prevents wild-type/mutant or cross-species
  blending; strictly narrows existing groups
- `GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN` introduced;
  `Deduplicator.POLICY_ID` bumped to
  `sci0009_identity_grouping_median_replicates_v2_gdr001` (propagates a new
  SCI0-011 snapshot hash for any corpus rebuilt after this change)
- `_confidence.py`'s `duplicate_agreement` component updated: the
  disagreement signal still fires for `RESOLVED_REPLICATE_MEDIAN` groups —
  resolving how to combine differing values doesn't mean they stopped differing
- `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md` revised: item 5/6
  marked `RESOLVED`; N_c/N_b counting-basis clarified as unique-compound
  (InChIKey) identity, non-numeric, per Amendment A10's own text
  distinguishing "compounds" from "scaffold families"; additional ATP Km
  literature search performed (negative result — located a PI3Kα/β Km for
  the PI lipid substrate, not ATP; explicitly not usable, recorded to
  prevent future confusion)
- N_c, N_b, N_w, S4b sharpness factor, and ATP Km source remain
  `RULE_MISSING`. `SCI0-015` remains not authorized
- 5 new/updated tests (construct/organism stratification, median resolution,
  median-vs-censoring contradiction checks); 319 total passing

#### SCI0-028 — Governance gap review (Blocked; report only, no code)
- `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md`: reviewed all six required
  seals (`N_c`, `N_b`, `N_w`, S4b sharpness factor, duplicate-resolution policy,
  per-isoform ATP Km source) against Constitution, ADR-0003, the AUDITOR-2/3/5
  evidence documents, and `sealed/MANIFEST.md`
- **Result: 0/6 items RULE_AVAILABLE.** All six classified RULE_MISSING; no
  numeric threshold, similarity measure, or scientific policy invented
- Flagged an internal documentation inconsistency: `adjudication.py` marks
  AUDITOR-3 (duplicate-resolution) `RESOLVED`, while `_deduplicator.py`'s
  docstring and the AUDITOR brief's own checklist mark it open — recorded as
  requiring a Governance Decision Record to reconcile, not resolved here
- `SCI0-015` remains **not authorized to begin** (backlog ordering constraint
  unsatisfied)
- Terminology: this report and future authored documents use "Governance
  Decision Record" / "Governance Amendment" in place of "Independent
  Scientific Auditor sign-off," per Project Owner direction (2026-08-05).
  Historical documents are quoted verbatim and not retroactively edited
- Backlog corrected: `SCI0-014` row was missing its `Done` marker (oversight
  from the SCI0-014 merge); corrected in this pass

#### SCI0-014b — Dataset characterization (Done)
- `data/audit.py`: `characterize(records, snapshot_sha256)` — pure descriptive
  analysis; never modifies records; output attached to snapshot SHA-256
- `IsoformStats`, `ScaffoldStats`, `ConnectivityStats` (delegated to SCI0-014),
  `ConfidenceStats`, `PublicationStats`, `MissingnessMatrix`, temporal counts,
  assay-format and quantity-type distributions
- Binding invariant: output is read-only; may NOT inform split/stratum/threshold
  decisions
- 13 new tests

#### SCI0-014 — Measurement-graph construction (Done)
- `data/graph.py`: `build_graph_stats_from_records()` — primary SCI0-014 API;
  union-find connected components over compound co-assay graph
- `largest_connected_component` (N_c candidate), `bridging_compounds`
  (N_b candidate), `within_study_four_isoform` (N_w candidate), `StudyCluster`
  structure per `(study_id, assay_id)`
- Legacy `build_graph_stats()` wrapper retained for `corpus.py` compatibility
- All statistics reproducible given the same input
- 22 new tests

#### SCI0-001 — Backlog refinement (Done)
- Existing refinement document at `docs/specifications/SCI0-001-refinement-data-acquisition.md`
  adopted as the authoritative decomposition of `SCI0-002`–`SCI0-014b`
- Backlog status updated to `Done`

#### SCI0-008c — Identifier harmonization (Done)
- `data/harmonization/_identifier_harmonizer.py`: `IdentifierHarmonizer`
  assigns deterministic internal IDs (InChIKey from SCI0-008b output) and
  cross-references compounds across source databases
- Internal ID = InChIKey: source-agnostic, deterministic, 27-char, stereo-
  preserving; follows directly from SCI0-008b guarantee + spec requirement
- Cross-reference accumulation: `cross_refs: dict[source_db, [source_ids]]`
  — multiple source IDs for the same InChIKey merged without conflict
- Conflict detection: same `source_compound_id` → different InChIKey → 
  `ConflictStatus.CONFLICT` + `StructureConflict` record; never silently merged
- Fail-closed: invalid SMILES / no SMILES → `ConflictStatus.UNRESOLVED`;
  all records returned, none dropped
- Stereoisomers preserved: enantiomers and E/Z isomers get distinct InChIKeys
  (inherits SCI0-008b guarantee, verified by exit-criterion tests)
- RDKit version propagated to `HarmonizedCompound.rdkit_version` (SCI0-011)
- 15 new tests; 194 total passing

#### SCI0-008b — Chemical standardization (RDKit) (Done)
- `data/harmonization/_chem_standardizer.py`: `ChemicalStandardizer` with
  deterministic 9-step pipeline: parse → metal disconnect → salt strip →
  normalize → uncharge → canonical tautomer → sanitize → canonical SMILES
  → InChI/InChIKey
- `SetRemoveSp3Stereo(False)` + `SetReassignStereo(True)` on tautomer
  enumerator — stereoisomers remain distinct (exit criterion 1)
- `StandardizedStructure` frozen dataclass: canonical_smiles, inchi, inchikey,
  rdkit_version, content_hash, salt_stripped, steps_applied — no descriptor
  fields (exit criterion 2)
- Output is deterministic given same SMILES + RDKit version (exit criterion 3)
- RDKit version recorded in every output (`rdkit_version` field) per SCI0-011:
  RDKit version affects InChIKey so toolchain is part of corpus identity
- Failed records returned with status + reason, never silently dropped
- rdkit>=2024.3 added to project dependencies
- 18 new tests; 179 total passing

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
