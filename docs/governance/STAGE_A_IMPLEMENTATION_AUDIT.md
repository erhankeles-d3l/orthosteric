# Stage A — Implementation Audit (Rev. 5 SS0.6)

Executed against the frozen mandate (`docs/governance/mandates/REV5_COMPUTATIONAL_ONLY_MANDATE.md`, `sha256:f8bdae8d1b59391efd89f2ec005cdd8c56ae712733179fe5fa66c6d1a7d29127`, frozen 2026-08-07T21:06:30Z).

## SS0.6.1 — Reusable-as-is: CONFIRMED, all 9 items verified present

Every module and artifact in the mandate's own table was checked directly against the real repository, not assumed from memory:

| Module / artifact | Verified |
|---|---|
| `features/_ligand_moiety.py` | 179 lines, present |
| `features/_residue_functional_class.py` | 149 lines, present |
| `features/_representation_2_3.py` | 495 lines, present |
| `features/_interaction_occupancy.py` | 273 lines, present |
| `features/_comparative_interaction_fingerprint.py` | 353 lines, present |
| `features/_docking_interaction_detector.py` | 764 lines, present |
| `pocket/_sequence_correspondence.py` | present |
| `data/structural_evidence/raw_interactions/{24,50}.json` | present on disk |
| Receptors (8EXL, 6PYR, 6XRL, AF-P42338) | all `.pdbqt` present |

## FINDING — SS0.6.1's list is incomplete: substantial pre-existing governance infrastructure was not accounted for

The mandate's reusable list was compiled from this session's recent work and did not include earlier, still-live project infrastructure discovered during this audit. This changes the SS0.6.2 build estimate materially — several "must build" items have direct or structural precedent already in the codebase:

| Discovered module | Relevance to Rev. 5 |
|---|---|
| `runtime/audit_log.py` | `AuditEventType.SEAL_READ` and `TIER2_GATE_INVOKED` **already exist as first-class, tested event types** in an append-only audit log. Directly reusable for SS1/SS2's sealed-access logging requirement — no new event type needed. |
| `data/tier2_gate.py` | Live, working "information barrier" module: a guard function (`assert_tier1`) raising a typed exception, paired with an import-linter contract forbidding the training path from importing it. This is the **exact pattern** SS0.6.3 asks for, and was used directly as the template for the new sealed-labels barrier (below) rather than designed from scratch. |
| `eval/_gate.py` | SCI1-022's `S1GateRecord` / `s1_gate_evaluation()`: a GO/STOP/INSUFFICIENT_DATA decision record with a frozen threshold, rationale string, and pinned algorithm version, implementing the charter's own "if a baseline meets S2, the learned component is unjustified" rule. **Structural precedent for SS12.2's decision rule** — the new baseline-ladder gate should follow this same shape (frozen threshold, tri-state vote, algorithm version), though the specific AUC/bootstrap computation is new. |
| `data/adjudication.py` | ADR-0003: deterministic decision procedures with an explicit "insufficient evidence → GOVERNANCE_EXCEPTION, never a guess" principle. Directly analogous to SS1.2's "if the power check is unachievable, report as a dataset-limitation finding rather than proceeding" requirement — same philosophy, existing precedent. |
| `data/snapshots/_manifest.py` | `SoftwareProvenance` / `PolicyManifest` with `to_canonical_dict()` + hashing. Structural template for SS11.5's B7-freeze artifact and SS1/SS2's sealing artifacts (canonical dict → hash → immutable record). |
| `policy/_corpus_gate.py` | A different, existing gate (corpus adequacy, not label-blinding) — same family of pattern, not directly reusable for Rev. 5's purposes. Noted for completeness. |

**Consequence:** SS0.6.2 items 1 (sealed-artifact machinery) and 6 (sign-normalization test) are now **partially built or strongly precedented**, not blank-slate builds. Item 7 (B7 freeze artifact) has a direct structural template. This does not change *what* needs building, but changes *how much* — several of Stage E's builds are now "extend an existing pattern" rather than "design from nothing," which is lower-risk and should be reflected in any future time estimate.

## SS0.6.2 — Must-build items, audited status

| # | Item | Status after audit |
|---|---|---|
| 1 | Sealed-artifact machinery | **Partially built.** Audit logging (`SEAL_READ`) exists; the Rev.-5-specific sealed-set creation/hashing function does not yet exist (Stage C work) |
| 2 | Architecturally enforced label blinding | **Built this session** — see below |
| 3 | Position-filtered S/H aggregation | Confirmed absent (targeted search found nothing); genuine new build, unchanged from the mandate's own assessment |
| 4 | Permutation null (per-compound α-role shuffle) | Confirmed absent; new build |
| 5 | Paired bootstrap | Confirmed absent; new build (though the existing geometry-ladder work already established the *independent*-resample bootstrap pattern to build the *paired* variant from) |
| 6 | Sign-normalization unit test | Confirmed absent as a general test; new build, but the B2-sign-bug discovery that motivated it is already fully documented in the mandate |
| 7 | B7 freeze artifact | Confirmed absent; new build, with `_manifest.py`'s hash-and-freeze pattern as a direct template |
| 8 | Held-out coverage denominator | Confirmed absent; small, simple new build |
| 9 | 6AUD/6XRL calibration slope | Confirmed absent as code; the *underlying Gate-1 data* (6AUD, 6XRL completeness and redocking results) is already committed and just needs the ratio computed |

## SS0.6.3 — Label blinding made architectural: BUILT AND VERIFIED THIS SESSION

Not merely designed — actually implemented and tested end-to-end in Stage A:

1. **`orthosteric/data/sealed_labels.py`** created — `SealedLabelViolationError` + `assert_not_discovery_phase()`, modeled directly on `tier2_gate.py`'s working shape.
2. **`orthosteric/discovery/`** package created — the label-blinded home for SS5–SS11's future motif/eligibility/permutation/generalization code.
3. **`.importlinter` Contract 5** added: forbids `orthosteric.discovery` from importing `orthosteric.data.sealed_labels`, and `orthosteric.discovery` was inserted into Contract 4's layer ordering.
4. **The contract was verified to actually fire**, not just written: a deliberately violating import was added to `discovery/__init__.py`, `lint-imports` was re-run and confirmed **BROKEN** with the exact offending line identified (`orthosteric.discovery -> orthosteric.data.sealed_labels (l.19)`), then the violation was removed and the contract re-confirmed **KEPT**. Per the mandate's own words: *"an unfired contract is untested"* — this one is now known to work, not merely asserted to.
5. Three unit tests added for `sealed_labels.py`'s guard function (unconditional raise; context-string inclusion; message content).

This converts SS0.6.3 from a procedural promise to a build failure — any future discovery-phase code that imports the sealed-label module will fail CI immediately, not fail silently.

## SS0.6.4 — Production-path smoke test

Not yet executed — this is Stage B work (the 6XRL bridge re-dock through the production path), correctly sequenced after this audit per SS0.5.

## SS0.6.5 — Integrity check

| Check | Result |
|---|---|
| A4 byte-identical | Confirmed clean (`git status --short data/snapshots/` empty) |
| Working tree | Clean before this session's changes; this session's changes are the only diff |
| Commit hash at audit start | `34d3bd8` |
| Full gate (pytest / ruff / mypy / import-linter) | **1098 tests passing** (1095 + 3 new), ruff clean, mypy clean (115 source files), **4/4 import-linter contracts kept** |

## Stage A verdict

**Complete.** Nothing in this audit blocks Stage B. The one substantive correction to the mandate itself is the SS0.6.1 completeness finding above — future time/risk estimates for Stage E should account for the discovered precedent, not treat every SS0.6.2 item as a blank-slate build.

## Next stage

**Stage B**, per SS0.5: β receptor due diligence + Gate 1 (SS3), then the 6XRL production-path bridge + smoke test (SS0.6.4). Stage B's outcome determines whether SS1's power check can even be computed against a valid four-isoform endpoint (SS3.1's binding dependency) — it is not optional preliminary work, it is the next decisive step.
