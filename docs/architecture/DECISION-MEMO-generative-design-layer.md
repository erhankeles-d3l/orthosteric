# Decision Memo — Proposed Generative Design Layer

**Status:** input to a decision, not a decision. Not a governance document (SI16); ADR input under ENG §1.
**Requires:** Independent Scientific Auditor, per Constitution §7.7 — the proposal is `Scientific` category.

---

## The proposal

Add a de novo generative layer consuming the comparative model, pockets, interaction fingerprints and chemical priors; emit molecules; filter through PAINS, Brenk, NIH, Lipinski, Veber, Ghose, Egan, REOS, synthetic accessibility, QED, Fsp3, ring and toxicophore alerts, reaction feasibility, patent similarity, novelty, docking, MM/GBSA and MD; rank; deliver "novel PI3Kα-selective molecules" as the terminal output.

## Why it cannot proceed under the current Constitution

| Barrier | Text |
|---|---|
| §1.5 Explicit non-goals | Lists **"a general-purpose discovery platform"** among things the project is not |
| §1.3 Election rule | Option A (method validation) is elected: recover known determinants, produce causally load-bearing explanations, behave across a correspondence gradient, transfer to a second family. Molecule design is not among the four |
| Part IX | Six stages, none generative |
| §9.0 | Three phases; Phase 3 is knowledge layer, Stage 0.5, L4 alchemical, transfer, prospective test. No generative workstream |
| Protocol §16 | Package ownership table has no generative package, and P8 permits none to appear without a state that owns it |
| §7.6 | Overclaim guard — a deliverable framed as novel selective molecules is a discovery claim |

**These are not oversights.** §1.2 records that orthosteric α-selectivity over β/γ/δ is a **solved medicinal chemistry problem** with a characterized structural basis, and R2 — *"central question already answered, fatal to novelty"* — is a Fatal-severity risk in Part VIII. The title carries "benchmarked on" precisely to prevent the discovery framing. A terminal deliverable of novel α-selective molecules reinstates what that framing was constructed to avoid, on an axis the field solved in 2010 and shipped twice (alpelisib 2019, inavolisib 2024).

**It also conflicts with the governance freeze.** Adopting it requires simultaneous amendment of §1.3, §1.5, §9.0 and Part IX, plus new protocol states, backlog sections and package ownership rows — the "major restructuring" excluded at v1.0.

## What is already authorized

**Constitution §6.2 — molecules as hypotheses.** Each proposed molecule carries, before evaluation: the Design Rule or Candidate Determinant it tests; a quantitative prediction with CI; the observation that would **falsify** the rule; and the rigor level at which falsification is decided. Without all four it is a suggestion, not a hypothesis.

**Constitution §6.1 — the validation ladder already exists.** L1 docking and counter-docking · L2 interaction fingerprint and MM/GBSA · L3 replicated MD · L4 alchemical/FEP · L5 synthesis and assay. Most of the proposed filter cascade is this ladder under other names. What is genuinely new is only the **generation** step.

So molecule proposal is in scope when each molecule is a falsifiable test of a learned rule, evaluated at a pre-registered rigor level, at Stage 5 (§9.7) with the §6.3 experimental arm. That is a narrow, hypothesis-driven generator — not a discovery platform.

## Three paths

| | Path | Cost | Consequence |
|---|---|---|---|
| **A** | Amend the Constitution to admit generative design | Gate-level ADR; Auditor sign-off; amendments to §1.3, §1.5, §9.0, Part IX; new protocol states and packages | **Reopens R2 deliberately.** The project must then defend novelty on a solved axis, or re-elect toward mutant-selective discrimination — which §3.2 shows is not established as orthosterically available |
| **B** | Separate downstream project consuming frozen outputs | No amendment. New repository; this platform's snapshots, model generations and knowledge layer are its inputs | Clean separation. Generative model replaceable (diffusion, autoregressive, RL) without touching the scientific pipeline — which is the maintainability argument the proposal itself makes |
| **C** | Use §6.2 as it stands | None. Already authorized | Molecules are generated only as falsifiable hypotheses, at Stage 5, requiring the experimental arm. Narrow but immediately legitimate |

## Recommendation

**B, with C in the interim.** Path B delivers the separation the proposal argues for — swapping the generative model without disturbing the learning pipeline — and it is the only path requiring no amendment, no R2 exposure and no reopening of the frozen governance. Path C is available today and needs no new decision at all.

Path A is defensible only if the project deliberately re-elects its central question. That is a legitimate choice, but it is a different project, and it should be made as one rather than arrived at by accretion.

## For the Auditor

1. Is the project re-electing away from Option A method validation? If not, A is closed.
2. If B: what constitutes the frozen interface — snapshot hash, model generation, knowledge-layer export?
3. If C: is the §6.3 experimental arm nameable? Without it, Stage 5 is not entered and no molecule reaches E4 regardless of path.
