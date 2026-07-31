# Comparative Evidence Learning for Mechanistic Orthosteric Selectivity
## A Framework Benchmarked on Class I PI3Ks
### Project Charter, v4.6

**Supersedes:** v4.5 and all earlier versions, including the v3.x Chapter 1–14 manual.

**What changed from v4.5.**
1. **§A.4 added** — the four machine-learning counterexamples most likely to be raised (protein language models, foundation docking models, universal affinity predictors, cross-protein graph transformers) are answered individually, on the distinction that **parameter sharing is not feature correspondence**.
2. **A.1 gains a fourth requirement — stability.** Correspondence must hold across the relevant conformational ensemble. C6 now derives from this directly rather than indirectly.
3. **A.2 adopts a three-kind taxonomy** of correspondence (evolutionary, structural, physicochemical), with the project requiring only the weakest sufficient level — a deliberate weakening that makes the hypothesis harder to refute.
4. **S8c made statistically honest.** With four Tier 2 targets a rank correlation has negligible power; S8c is now a descriptive, covariate-adjusted trend report with an explicit no-significance-claimed statement, and failure requires a large unexplained *reversal* rather than any departure from monotonicity.

---

# Part A — Founding Hypothesis

## A.1 Statement

> **Founding hypothesis.** Comparative learning *with mechanistic determinant attribution* is well-posed only between binding sites possessing a **stable structural correspondence**.

For a model to learn *why* a ligand discriminates between two pockets — rather than learning two independent binding models and subtracting them — a correspondence between those pockets must exist under which:

1. a single shared feature space is definable;
2. differences within that space correspond to physical differences rather than mapping artefacts;
3. a determinant identified in one pocket has a defined **image** in the other; and
4. **the mapping is stable across the conformational ensemble relevant to ligand binding.**

Requirement (4) is not implied by (1)–(3). A mapping that holds in one conformational state and fails in another cannot support a determinant claim, because the determinant's image would exist in some states and not others. C6 (§A.6) follows directly from (4).

Where no such correspondence can be constructed, the comparison is not merely harder — it is **undefined**: there is no coordinate system in which the difference can be expressed, so any number the model emits is an artefact of the arbitrary mapping used to compute it.

> **Organizing statement.** Everything in Parts 0 through IX is either a consequence of this hypothesis or a control protecting it.

## A.2 Three kinds of correspondence, and which the project needs

Earlier versions conflated correspondence with **homology**. That was a category error: correspondence is defined by what it does, not by how it arose. Three distinguishable kinds:

| Kind | Basis | Role here |
|---|---|---|
| **Evolutionary** (homology) | Common ancestry, evidenced by sequence and fold similarity | Convenient *evidence* for the other two. Neither necessary nor sufficient. |
| **Structural** | Geometry and topology of the site and its sub-pockets; shape and volume overlap; equivalence of ligand-binding mode | **Required.** |
| **Physicochemical** | Field organization, pharmacophoric arrangement, desolvation environment, water architecture | **Required.** |

**The entailments run one way and imperfectly.** Evolutionary homology usually implies structural correspondence, which usually implies physicochemical correspondence — but homologs can diverge conformationally (a failure of A.1(4), and the reason C6 exists), and non-homologs can converge. Unrelated ATPases can present adenine-recognition environments of similar shape and electrostatics; catalytic-triad convergence between structurally unrelated proteases is a textbook case of function-preserving similarity without shared ancestry.

**The project therefore requires only the weakest sufficient level: structural and physicochemical correspondence, plus stability.** Evolutionary homology is demoted to evidence. This is a deliberate weakening — a weaker premise is a stronger position, because it is harder to refute and admits more transfer targets.

**Practical consequences.** The ordering used for S8c (§1.4.1) is a **correspondence** ordering measured on structural and physicochemical criteria, not sequence identity alone (§2.1). And a *non-homologous but structurally corresponding* ATP site becomes an admissible and stronger transfer target than a homologous paralog family (§9.6, optional extension), because it tests correspondence in the sense the hypothesis actually asserts.

## A.3 Status: hypothesis, not theorem

A.1 is **motivated, not proven.** It is offered as a working scientific premise about when comparative attribution is meaningful, and the charter applies to it the same falsifiability discipline it applies to everything else.

**What would falsify or substantially weaken it:**

- Reproducible mechanistic determinant attribution between binding sites for which no correspondence satisfying A.1(1)–(4) can be constructed, with the attributed determinants validated at evidence class E3 or E4 (§2.5). One such demonstration would show the hypothesis is too strong.
- Complete insensitivity of model performance and calibration to correspondence strength across a wide correspondence range (§A.7, S8c) — indicating that whatever the model is doing does not depend on correspondence at all.

**What would not falsify it:** any of the systems in §A.4; or a non-monotonic S8c result explained by pre-registered covariates (§1.4.1).

The project therefore **partially tests its own founding hypothesis**. S8c and S7 exist for that purpose, which makes the hypothesis stronger as a research position than an unexamined assumption would be.

## A.4 The named machine-learning counterexamples

Four classes of system will be raised as counterexamples to the word "only." None is one, and the reasons differ enough to be worth stating individually rather than dismissing collectively.

| System | What it does | Why it is not a counterexample |
|---|---|---|
| **Protein language models** | Learn sequence statistics across all known proteins; emit per-residue or per-sequence embeddings | Supply a *representation* of each site, not a frame in which two sites' differences are attributable. An embedding distance between two pockets is a scalar; it contains no determinant image in the sense of A.1(3). Representing both sites is not comparing them attributably. |
| **Foundation docking and co-folding models** | Predict a bound pose for a given protein–ligand pair | Per-complex structural output. Like affinity, requires no cross-site frame. Predicting a pose in p110α and independently in p110δ yields two poses, not an attributable account of why the ligand prefers one. |
| **Universal affinity predictors** | Predict a scalar per complex across structurally diverse proteins | Exactly the case in §A.5. Scalar prediction is well-posed without correspondence; the hypothesis does not contest it. |
| **Graph transformers trained across unrelated proteins** | Share parameters across heterogeneous inputs | **Parameter sharing is not feature correspondence.** Shared weights permit good per-input prediction; they do not license the statement "feature X in pocket A corresponds to feature Y in pocket B, and their difference explains the selectivity." The model has one function; that does not give its inputs a common frame. |

**The general form of the answer.** All four are *prediction* systems. The hypothesis is about *attribution*. It constrains what an output **means**, not what a model can **compute**: any model can compute a difference between two pockets, and the question is whether that number denotes a physical difference or an artefact of the mapping used to produce it.

A genuine counterexample would therefore need to exhibit attributable, transferable determinants between non-corresponding sites, validated at E3 or E4. None of the four supplies that, and the charter would treat such a demonstration as falsifying (§A.3).

## A.5 Scope of the claim

The hypothesis concerns **differential learning with attributable determinants**. It does not claim that no model can learn anything across non-corresponding proteins. General affinity models trained on structurally diverse complexes plainly work to a degree; they learn *binding*, a scalar property of a complex. This project learns *discrimination* and attributes it to specific structural features. Attribution requires a common frame; a scalar does not.

Stated precisely: general affinity prediction is well-posed across non-corresponding sites. **Comparative selectivity learning with determinant attribution is hypothesized not to be.**

## A.6 Corollaries

Each was presented in earlier versions as an independent design decision. All six follow from A.1.

**C1 — Comparative evidence is meaningful.** Because correspondence exists across the four Class I ATP sites, an observed difference in interaction pattern is a physical difference rather than a mapping artefact. This licenses treating comparative evidence as evidence at all (§4.1).

**C2 — A shared representation is legitimate.** One feature space across four pockets, not four unrelated encoders. Without correspondence there is no shared space to define, and "comparative representation" would name an arbitrary concatenation.

**C3 — Determinant transfer is defined.** A determinant at p110α position 859 has an image in each paralog — the residue occupying the corresponding position. This makes S1 gradeable and design rules transferable rather than isoform-anecdotal (§5.4).

**C4 — Cross-isoform reasoning is licensed, and selectivity is a property of the comparison rather than of the molecule.** This is the substantive content of "selectivity cannot be inferred from PI3Kα alone."

**C5 — Allosteric mechanisms are excluded on principled grounds.** Allosteric sites differ across the paralogs in existence, location and character; no correspondence satisfying A.1 can be constructed, so a four-isoform comparative representation of them is undefined rather than merely difficult. Tier 3 (§0.2) follows from the hypothesis, not from resourcing.

**C6 — Correspondence must be defined over conformational ensembles, not static structures.** *Direct consequence of A.1(4).* The specificity pocket between Trp780 and Met772 exists only in induced conformations; a correspondence built on apo structures is unstable across the binding-relevant ensemble and maps objects that do not contain the discriminating feature. Hence §2.1's ligand-ensemble-union pocket definition and rotamer-state representation.

## A.7 The hypothesis cuts both ways, derives the tiers, and is measurable

**Both ways.** Correspondence is the precondition for well-posedness **and** the source of the project's central hazard. The stronger the correspondence, the smaller the discriminating differences, and the greater the risk that a model collapses into a site-agnostic binding predictor scoring well per isoform while learning nothing comparative. The four Class I ATP sites sit in the difficult middle: corresponding enough for comparison to be defined, conserved enough for it to be nearly degenerate. Hence the §4.3 degeneracy battery, and hence per-isoform accuracy is never accepted as evidence that comparative learning occurred. The tension is locatable: **the differences that make comparison meaningful are conformational and sparse rather than sequential and abundant.**

**Tiers.** Tier 2 is not held out for data hygiene. It is held out because comparison across a correspondence gap is undefined under A.1, so Tier 2 cannot be part of the learning task. It can only be a site of *evaluation*. This resolves what would otherwise contradict §4.6:

| Level | Requirement | Rationale |
|---|---|---|
| **Learning task** | Corresponding sites | A.1 — otherwise learned differences are artefacts |
| **Input interface** | Correspondence-free; accepts any ATP site | Permits evaluation on unseen and mutated pockets |

Learning happens where correspondence holds; testing happens where it weakens. A correspondence-free input interface is not a repudiation of the hypothesis but the technical means of probing its boundary.

**Measurable.** Correspondence is continuous, and the floor is unknown: A.1 asserts that well-posedness *degrades* as correspondence weakens without specifying where it fails. The Tier 2 panel spans a correspondence gradient — Class II PI3Ks nearest, then Vps34, then mTOR, then DNA-PK on the sealed ordering of §2.1 — and the sealed second family (§3.1 Q16) extends it further. Evaluating across that gradient converts the hypothesis into a measurement (S8c). Mapping where well-posedness fails is a secondary contribution, and arguably the most transferable one: a statement about comparative learning in general, not about PI3K.

## A.8 Amendment

Part A may be amended only by a gate-level Decision Record. Because Parts 0 and I derive from it, any amendment triggers mandatory re-derivation review of the tier architecture (§0.1), Tier 3 exclusions (§0.2), pocket definition (§2.1) and representation decision (§4.6). The hypothesis is not editable in passing.

## A.9 Glossary

Where wider usage is looser, this charter's definition governs.

| Term | Definition in this charter |
|---|---|
| **Well-posed** | A learning task is well-posed if its target quantity is defined independently of arbitrary implementation choices. Comparative attribution is well-posed only if the comparison does not depend on which of several possible mappings between sites was chosen. |
| **Correspondence** | A constructible mapping between two binding sites satisfying A.1(1)–(4): shared feature space, physical differences, defined determinant images, stability across the binding-relevant ensemble. Functional, not ancestral. |
| **Evolutionary correspondence (homology)** | Shared ancestry, evidenced by sequence and fold similarity. **Evidence for correspondence; neither necessary nor sufficient.** |
| **Structural correspondence** | Correspondence from geometry and topology — fold, sub-pocket architecture, shape and volume overlap, ligand-binding mode. **Required.** |
| **Physicochemical correspondence** | Correspondence from field organization, pharmacophoric arrangement, desolvation environment, water architecture. **Required.** |
| **Correspondence stability** | Invariance of the mapping across the conformational ensemble relevant to ligand binding (A.1(4)). Homologous sites may lack it; this is the C6 failure mode. |
| **Alignment** | A specific computational procedure producing a residue-to-residue mapping. One possible *implementation* of correspondence, not correspondence itself. A model may honour A.1 without performing an explicit alignment (§4.6, Path A). |
| **Representation** | The model's internal feature encoding. An implementation artefact. Distinct from correspondence: correspondence is a property of the sites, representation a property of the model. |
| **Parameter sharing** | Use of common model weights across heterogeneous inputs. **Not equivalent to correspondence** (§A.4). |
| **Determinant image** | The feature in pocket B corresponding to a determinant identified in pocket A. Required by A.1(3); what makes determinant transfer meaningful (C3). |
| **Degeneracy** | The failure mode in which a comparative model becomes effectively site-agnostic, predicting each site accurately while encoding nothing about their differences (A.7, §4.3). |
| **Candidate Determinant / Determinant / Design Rule** | Maturity states with distinct evidence requirements (§2.5, §5.4). Never used interchangeably. |

---

# Part 0 — Scope Boundary (binding)

*Every clause is a consequence of Part A, cross-referenced accordingly.*

## 0.1 Three-tier scope (from A.7)

| Tier | Contents | Role | Access |
|---|---|---|---|
| **Tier 1 — Primary learning scope** | Orthosteric ATP pockets of human p110α, p110β, p110γ, p110δ | The comparative-learning task. Correspondence constructible → A.1 satisfied. All training, model selection, feature engineering, threshold setting. | Full |
| **Tier 2 — External validation panel** | ATP sites of Class II PI3Ks (PI3KC2α/β/γ), Vps34 (PIK3C3), mTOR, DNA-PK — in decreasing correspondence per the sealed ordering (§2.1) | Held-out zero-shot generalization, broader-selectivity assessment, and **probe of the correspondence floor** (A.7). Never trained on. | Read-only, query-budgeted (§0.4) |
| **Tier 3 — Out of scope** | Everything in §0.2 | Excluded by C5 — no correspondence constructible | None |

Tiers 1 and 2 are both **orthosteric**: every target is engaged at its own ATP site.

## 0.2 Out of scope (Tier 3) — from C5

Appearance in any artifact is a scope violation under §7.6:

- Allosteric sites of any kind, including the p110/p85 nSH2 and iSH2 interfaces and the C2/helical-domain interfaces.
- Membrane-interaction and lipid-substrate binding sites.
- Protein–protein interaction modulators and autoinhibition disruptors.
- Targeted degraders, molecular glues, and mechanisms where selectivity arises from differential protein turnover rather than ATP-site recognition. *(At least one approved orthosteric agent is reported to additionally promote mutant-p110α degradation — clinically important, but not orthosteric recognition, therefore not a learning target.)*
- Covalent inhibitors engaging residues outside the ATP site.
- Regulatory-subunit-directed and isoform-expression-directed strategies.

**Note on Stage 0.5.** §3.2 characterizes long-range communication *to* the ATP site, testing whether an orthosteric-only strategy is physically available. It is not licence to design at an allosteric site. Remote network changes not manifesting at the ATP site are published separately and do not open Tier 3 (§3.2.4, cell C).

## 0.3 Orthosteric sub-regions (Tier 1, in scope)

- **Adenine region** and hinge contacts.
- **Affinity pocket** — deep sub-region behind the adenine site, bounded by the catalytic lysine and the DFG-equivalent aspartate, containing the p110α position-859 glutamine.
- **Specificity pocket** — an *induced* cleft opening between Trp780 and Met772 upon binding of propeller-shaped ligands. Absent in apo structures; the canonical instance of C6 and of correspondence instability.
- **Tryptophan shelf / Met rotamer region** governing β- and δ-selective recognition.
- Ordered and displaceable **ATP-site water networks**.

*All residue numbering is provisional and must be verified against the reference structures selected in §2.1. Do not propagate it.*

## 0.4 External panel information barrier (binding)

1. **No training use.** Tier 2 data may not enter training, pre-training, fine-tuning, hyperparameter search, model selection, early stopping, feature engineering, threshold setting, or any decision shaping the model.
2. **Query budget.** Tier 2 is evaluated **once per model generation**, at the Stage 3 and Stage 4 gates only. Each query is logged by the Independent Scientific Auditor (§1.6) with date, model hash, and pre-registered prediction. A model generation = frozen architecture + frozen training data + frozen hyperparameters.
3. **No iteration on results** within a generation. Tier 2 results may motivate a *new* generation, whose evaluation is a new query.
4. **Audit.** The query log is part of every report. A Tier 2 number without a log entry is invalid.

## 0.5 What the scope costs

- The highest-novelty modern route to therapeutic differentiation here — mutant-selective inhibition — is pursued in the field predominantly by allosteric means, and is closed by C5.
- Wild-type orthosteric α-selectivity over β/γ/δ is a **solved problem** (§1.2). No discovery novelty may be claimed on the primary axis.
- ATP-competitive binding means cellular potency is ATP-concentration dependent; biochemical selectivity does not transfer to cells (§2.3).

---

# Part I — Scientific Charter

## 1.1 Therapeutic rationale

*PIK3CA* is among the most frequently mutated oncogenes in human cancer, with hotspot activating mutations in the helical (E542K, E545A/K) and kinase (H1047R) domains. Two orthosteric, ATP-competitive, α-selective inhibitors are clinically approved (alpelisib, 2019; inavolisib, 2024).

The dose-limiting toxicity of α inhibition — hyperglycemia and insulin resistance — is **on-target**, since p110α mediates insulin signalling in normal tissue. Isoform selectivity over β/γ/δ does not resolve this; discriminating mutant from wild-type p110α would. Whether that is achievable at the orthosteric site is an open physical question (§3.2).

Within Tier 2, **mTOR is the highest-priority safety axis** — above PI3Kγ — because dual PI3K/mTOR pharmacology substantially alters toxicity. Every selectivity objective must trace to a toxicity or efficacy consequence.

## 1.2 Prior art, stated honestly

Orthosteric PI3Kα selectivity over β/γ/δ is a solved medicinal chemistry problem with a characterized structural basis:

- The **affinity-pocket glutamine at p110α position 859** (non-conserved across paralogs) is the principal α-selectivity handle, engaged by alpelisib-class compounds.
- The **induced specificity pocket** between Trp780 and Met772 is exploited by propeller-shaped β/δ-selective compounds (PIK-39, idelalisib class).
- Canonical references: Knight *et al.*, *Cell* 2006; Berndt *et al.*, *Nat Chem Biol* 2010; Furet *et al.* 2013 (BYL-719).

**Consequence for novelty.** A model that "discovers" the 859 determinant recovers 2010 knowledge densely represented in its training data. That is method validation, not discovery — hence "benchmarked on" in the title.

**Methodological prior art to cite and beat.** Learning across multiple related targets with target descriptors is **proteochemometrics**, established since the mid-2000s and standard in kinome-wide selectivity modelling; multi-task kinase-panel learning, uncertainty quantification, applicability domains and active learning are all published. The systems in §A.4 must also be cited and distinguished, not ignored. The defensible delta is: the explicit and testable founding hypothesis (Part A), comparative-evidence discipline, per-isoform calibration, induced-pocket and rotamer-aware representation, held-out generalization with a **measured correspondence floor** (A.7), auditable unsupervised rule extraction (S9), counterfactual explanation testing (S10), cross-family transfer (S7), and provenance.

## 1.3 Central question

**Option A — Method validation (primary).**
> Can a comparative evidence-learning framework, trained exclusively on the orthosteric ATP pockets of the four human Class I PI3K isoforms, (i) recover *de novo* the known structural determinants and medicinal-chemistry rules of orthosteric isoform selectivity without supervision from selectivity labels or rule annotations, (ii) produce explanations that are causally load-bearing under counterfactual perturbation, (iii) behave across a correspondence gradient in a manner consistent with the founding hypothesis, and (iv) transfer without retuning to a second, pre-registered family of corresponding ATP sites?

**Option B — Orthosteric mutant discrimination (conditional, high risk).**
> Does activation-hotspot mutation in *PIK3CA* (H1047R, E542K, E545K) propagate a measurable change **to the orthosteric ATP pocket** — in geometry, electrostatics, or site dynamics — sufficient to support ATP-competitive discrimination between mutant and wild-type p110α?

None of the hotspot residues lines the ATP pocket: H1047R sits in the kinase domain near the membrane-binding region; E542K/E545K at the helical-domain interface with p85 nSH2. Any orthosteric discrimination must be indirect and propagated. Option B is **blocked** pending §3.2.

Option B is the *limiting case* of A.1: wild-type and mutant p110α correspond almost perfectly, differing at one residue remote from the site. Well-posedness is trivially satisfied; discriminability is minimal. Option B therefore probes the opposite end of the A.7 tension from Tier 2.

**Election rule.** Execute Option A. Do not describe the project in Option B terms unless §3.2 returns outcome A or B (§3.2.4).

## 1.4 Falsifiable success criteria

Provisional; fixed before any model is trained; not revisable after results are seen.

### Predictive competence

| # | Criterion | Scope | Threshold |
|---|---|---|---|
| S2 | Comparative discrimination | Tier 1 | Beats a **ligand-only** baseline on log-selectivity-ratio prediction by ≥ 0.3 log RMSE on held-out *series* |
| S3 | Degeneracy control | Tier 1 | Performance degrades ≥ 0.3 log RMSE under pocket-feature shuffling (§4.3) |
| S4 | Per-target calibration | Tier 1 | ECE ≤ 0.10 for each of α, β, γ, δ **separately** |
| S5 | MMP selectivity switching | Tier 1 | ≥ 60% correct direction on held-out matched pairs known to flip selectivity |
| S6 | Induced-pocket sensitivity (tests C6) | Tier 1 | Correctly ranks propeller-shaped compounds as β/δ-preferring — impossible from apo-pocket features alone |
| S8a | Zero-shot external accuracy | Tier 2 | On mTOR, beats a ligand-only baseline trained on the same Tier 1 data, on dual-inhibitor-stratified evaluation (§3.5) |
| S8b | Calibration under shift | Tier 2 | Predicted uncertainty increases and AD flags fire on Tier 2 relative to Tier 1. Equal confidence on Vps34 and PI3Kβ = failure, regardless of accuracy |
| S8c | **Correspondence-gradient behaviour** (tests A.1 / A.7) | Tier 2 (+ second family) | See §1.4.1 |
| S7 | **Cross-family transfer** | Second family, sealed at Stage 0 | S1–S4 met on the pre-registered second family with no framework retuning. Required for any methods-generality claim (§9.6) |

### 1.4.1 S8c, stated without overconstraint

Strict monotonicity is the wrong test, for two reasons that pull in opposite directions:

- **Upward departure.** A target whose chemotypes happen to be abundant and well-learned in Tier 1 training data may outperform a nominally closer target purely on chemistry. mTOR is the likely case, given dual-inhibitor prevalence (§3.5).
- **Downward departure.** A closer target with sparse or poorly resolved structures — Class II PI3Ks are the likely case — may underperform despite higher correspondence, for reasons of data quality rather than well-posedness.

Both are compatible with the founding hypothesis. Treating either as failure would reject reasonable behaviour.

**Statistical honesty (binding).** With four Tier 2 targets, a rank correlation has negligible statistical power: a non-significant result would be uninformative and a significant one fragile. **No significance test is claimed on n = 4.** S8c is a descriptive, effect-size report, and must be presented as such.

**S8c-1 — Primary report.** Covariate-adjusted predictive quality and predicted uncertainty per target, with confidence intervals, plotted against sealed correspondence rank (§2.1). Adjustment uses covariates pre-registered at Stage 0:

- number of evaluable compounds per target;
- chemotype overlap with Tier 1 training series (§3.5);
- structural data quantity and resolution per target (§2.1);
- assay heterogeneity per target;
- construct heterogeneity per target.

**Adjusted performance is the primary figure; raw performance is reported alongside it, never instead of it.**

**S8c-2 — Expected behaviour.** A negative trend in adjusted performance and a positive trend in adjusted uncertainty with decreasing correspondence. Direction and effect size are reported. **Wobble among adjacent ranks is expected and is not a departure.**

**S8c-3 — Departure investigation.** A material departure triggers mandatory investigation against the pre-registered covariates, plus the possibility that the **sealed correspondence ordering was itself wrong** — a scientifically interesting outcome, reportable as such, and an admissible explanation.

**S8c-4 — Failure condition.** S8c fails only on a large **reversal**: the least-corresponding target outperforming the most-corresponding by more than their confidence intervals overlap, where the reversal (a) survives covariate adjustment, (b) is unexplained by any pre-registered covariate, and (c) is not attributable to a documented ordering error. Under those three conditions the model's behaviour is indifferent to correspondence, and the founding hypothesis is either false or not honoured by the implementation — both requiring diagnosis before any determinant claim.

**Power improves with S7.** The sealed second family's targets extend the correspondence gradient, so S7 and S8c are the same experiment measured at more points. Where S7 is executed, S8c is reported over the combined gradient.

### Knowledge extraction

| # | Criterion | Threshold |
|---|---|---|
| S1 | **Determinant recovery** (tests C3) | Top-ranked α-selectivity determinant is the affinity-pocket 859 position, recovered without selectivity-label supervision, in ≥ 4 of 5 held-out scaffold families |
| S9a | **Rule recall** | Recovers ≥ 50% of the **locked reference rule set** (§3.6), unsupervised, in operationally testable form |
| S9b | **Rule precision** | ≥ the floor calibrated empirically at Stage 0 against extraction from a deliberately uninformative baseline (§3.6.5); provisionally 30% |
| S9c | **Scrambled-label negative control** | Identical extraction on a model trained on **permuted selectivity labels** must yield chance-level recall. Otherwise the extraction procedure is generating narrative, and S9a/S9b are void |

### Causal robustness

| # | Criterion | Threshold |
|---|---|---|
| S10a | **Determinant knockout** | In-silico mutation of a model-claimed determinant (e.g. p110α position 859 → the paralog residue) abolishes or significantly attenuates the predicted α-preference and its attributed explanation, in the direction consistent with medicinal-chemistry expectation |
| S10b | **Null-mutation control** | In-silico mutation of a conserved, distal, non-determinant residue produces **no** significant change. Required — without it a model merely sensitive to any perturbation passes S10a trivially |

**Interpretive limit on S10, binding.** S10 tests whether an explanation is causally load-bearing **within the model**. It is not evidence about the enzyme. Passing S10 does not promote a Candidate Determinant to a Determinant; that requires evidence class E3 or E4 (§2.5, §5.4). Describing S10 as causal validation of a biological mechanism is a §7.6 violation.

**Kill criteria.** Failure of S2 or S3: comparative learning did not occur; no selectivity claim publishable regardless of aggregate accuracy. Failure of S6: pocket representation is apo-degenerate (C6 violated); rebuild. Failure of S8b: applicability domain non-functional; no prospective prediction may issue. Failure of S8c-4: diagnose before any determinant claim. Failure of S9c: rule-extraction contribution withdrawn. Failure of S10b: explanation module non-specific; outputs may not be reported as determinants. Absence of S7: the deliverable is a PI3K case study and must be described as one (§9.6). If Stage 0 yields fewer than 300 four-isoform panel compounds across fewer than 8 scaffold families, the project stops and is redesigned as a physics-only orthosteric study.

## 1.5 Explicit non-goals

Clinical candidate nomination; beating any published virtual-screening benchmark; a general-purpose discovery platform; novel ML architecture development; any biological claim from computation alone; anything in §0.2; any model trained on Tier 2; any determinant claim resting on S10 alone; any comparative claim across a correspondence gap (A.1); any generality claim without S7; **any presentation of the founding hypothesis as proven**.

## 1.6 Resource declaration (mandatory, complete before Part III)

| Resource | Committed |
|---|---|
| People (FTE, roles) | |
| GPU-hours / month | |
| Wall-clock horizon to first gate | |
| Experimental partner (synthesis) | |
| Experimental partner (assay) | |
| Budget for external assays | |
| Named decision-maker at each gate | |
| **Independent Scientific Auditor** | |
| **Stage 0 pre-registration time, ring-fenced** | |
| **Phase commitment (§9.0): Core only / Core + Extension / Full** | |

**Independent Scientific Auditor** — one named person, **not the model developer**, owning: the Tier 2 query log (§0.4), curation and sealing of the S9 reference rule set (§3.6), design of the S10 null-mutation control, the sealed correspondence ordering, weighting and S8c covariate list (§2.1, §1.4.1), the sealed second-family selection (§3.1 Q16), and blinded adjudication of candidate novel rules. This role exists because all of these controls fail the same way — the person who built the model marks its homework.

If no experimental partner can be named, record it and downgrade every knowledge claim from "determinant" to "computational hypothesis."

---

# Part II — Provisional Operating Definitions

**Bootstrap rule.** Every definition is **provisional v0.1** — usable immediately, versioned, cited as provisional, reviewed at gates, not revised mid-stage. This breaks the v3.x deadlock in which nothing could be implemented until definitions were operational and no definition could be calibrated without implementation.

## 2.1 Orthosteric pocket (provisional) — the operational form of C6

**Reference structures.** Per Tier 1 isoform, enumerate all human experimental structures with resolution ≤ 2.8 Å and a bound ATP-site ligand. Record PDB ID, resolution, construct (p110 alone / p110–p85 heterodimer / p110γ), mutations, ligand, ligand shape class (flat vs. propeller). Repeat for Tier 2, recording that coverage is **uneven and generally poorer** — mTOR and Vps34 reasonably represented, DNA-PK sparser, Class II sparsest. Per §1.4.1 this asymmetry is a pre-registered S8c covariate, not a nuisance.

**Construct policy.** p110α/β/δ occur as p110–p85 heterodimers; p110γ pairs with p101/p87. Regulatory-subunit presence alters ATP-site conformation. Mixed-construct comparisons are flagged, never silently pooled — a construct mismatch threatens correspondence stability under A.1(4).

**Tier 1 data asymmetry.** p110γ is the most extensively characterized (historically a family surrogate); p110β the sparsest. Record per-isoform structure counts and resolutions as covariates in all evaluations.

**Pocket definition — both rules follow from A.1(4) via C6:**

1. **Ligand-ensemble union, never apo.** The pocket is the union, across the reference ensemble per target, of residues with any heavy atom within 5.0 Å of any heavy atom of a bound ATP-site ligand. **Apo-derived definitions are prohibited**: the induced specificity pocket is absent in apo structures, so an apo correspondence is unstable across the binding-relevant ensemble and empty of the discriminating feature.
2. **Rotamer states are part of the pocket, not noise.** Selectivity here derives substantially from side-chain conformational accessibility rather than sequence identity. The pocket is represented as an ensemble of rotamer states; sequence-only or backbone-only representations are non-compliant, establishing a correspondence that omits the differences the model must learn (A.7).

**Residue correspondence within Tier 1.** Structure-based alignment, not sequence-only. The α-859-equivalent and Trp780/Met772-equivalent positions must be explicitly recorded and manually verified.

**Correspondence ordering for Tier 2 (required for S8c).** The Auditor records, before any Tier 2 query, a quantitative **correspondence** ordering of Tier 2 targets relative to Tier 1. Per A.2, measured on structural and physicochemical criteria — not sequence identity alone:

- ATP-site residue identity and similarity;
- fold-level structural similarity of the pocket region;
- ATP-site shape and volume overlap;
- pharmacophoric field similarity across the adenine and affinity sub-regions;
- equivalence of ligand-binding mode;
- an assessment of correspondence **stability** across each target's available conformational states (A.1(4)).

The composite ordering, its weighting, and the S8c covariate list are sealed together with the S9 rule set. S8c is scored against the sealed ordering, never one chosen after results are seen. The ordering is itself falsifiable: a documented error in it is an admissible explanation for a departure (§1.4.1, S8c-3).

**In-silico mutation support (for S10).** The pocket pipeline must accept a point-mutated input structure and re-derive the pocket without manual intervention, including re-equilibration of rotamer states and waters.

**Protonation.** pH 7.4, single dominant tautomer; tool and version recorded. Ordered ATP-site waters retained and flagged.

**Missing residues.** Loops < 4 residues modelled and flagged; ≥ 4 residues excluded.

## 2.2 Productive binding (provisional)

| Class | Criteria (all must hold) |
|---|---|
| **Productive** | Pose reproduced in ≥ 3 of 5 independent docking runs (RMSD ≤ 2.0 Å); required hinge and affinity-pocket contacts present; no heavy-atom clash < 2.2 Å; ligand RMSD ≤ 3.0 Å from starting pose across 3 × 100 ns MD replicates |
| **Non-productive** | Positive evidence of failure: reproducible steric clash, reproducible loss of a required contact, or ligand egress in ≥ 2 of 3 MD replicates |
| **Indeterminate** | Neither criterion set satisfied, or replicates disagree |

Positive criteria for all three classes — v3.x defined Non-Productive as the negation of Productive and then forbade treating it as the negation, which is incoherent. Indeterminate is **not** weak evidence of sparing and contributes zero to selectivity claims. A model unable to output Indeterminate per target is non-compliant.

## 2.3 Selectivity (provisional)

All targets in Tiers 1 and 2 are engaged ATP-competitively and differ in ATP Km. IC50 depends on assay ATP concentration; biochemical ratios do not transfer to cells.

1. Selectivity computed **only from within-study, within-assay panels.** Cross-study ratios excluded from primary targets; admissible only as low-reliability auxiliary evidence.
2. Every record carries assay ATP concentration, format, substrate, construct. Records lacking ATP concentration are flagged and excluded from primary targets.
3. Biochemical and cellular selectivity are **separate targets**, never pooled.
4. **Primary target (Tier 1):** `S₁ = (pAct_α, pAct_α − pAct_β, pAct_α − pAct_γ, pAct_α − pAct_δ) ± CI`
5. **External target (Tier 2), evaluated never trained:** per-target log ratios reported in **sealed correspondence order** for S8c, never aggregated into a single off-target score — data density differs by an order of magnitude across them.
6. **Potency floor.** Selectivity is undefined below `pAct_α ≥ 7.0`. Objective: maximize selectivity **subject to** the floor. (Replaces v3.x's "selectivity before affinity," a lexicographic error.)

## 2.4 Uncertainty composition

A selectivity claim is a **conjunction** (α productive AND the rest spared), so joint confidence composes as a product over correlated events and is *lower* than the weakest component, not equal to it. (v3.x's min-rule was wrong.)

- Report per-target confidence and uncertainty separately, always.
- Report joint confidence as an explicit conjunction with a stated correlation assumption; Tier 1 and Tier 2 conjunctions separately.
- Distinguish epistemic from aleatoric uncertainty. Assay uncertainty is estimable from replicate and inter-lab variance, typically ≥ 0.3 log units. No model may claim precision below the noise floor of its labels.

## 2.5 Evidence classes for mechanistic claims

| Class | Evidence | Sufficient for |
|---|---|---|
| **E1 — Associational** | Model attribution, feature importance, attention | **Candidate Determinant** only |
| **E2 — Model-counterfactual** | S10a/S10b in-silico mutation of model inputs | Candidate Determinant with *internal consistency* noted |
| **E3 — Physics-counterfactual** | Alchemical residue mutation, free-energy perturbation | **Determinant** |
| **E4 — Experimental** | Site-directed mutagenesis, structural, biochemical | **Determinant** (highest reliability); required for **Design Rule** |

E1 and E2 together do **not** reach E3. This is the promotion rule referenced by §5.4.

---

# Part III — Data and Physical Feasibility

## 3.1 Stage 0 — Feasibility and pre-registration (blocking)

No modelling, architecture or infrastructure work begins until complete and reviewed.

**Tier 1**
1. Compounds with **all four** Class I isoforms measured **within a single study and assay**, by Bemis–Murcko scaffold family.
2. Distinct scaffold families; propeller-shaped vs. flat counts. *(Both required for S6.)*
3. Fraction of right-censored records; handling for each.
4. Inter-lab reproducibility for compounds in ≥ 3 independent studies — sets the label noise floor and the ceiling on reportable accuracy.
5. Per-isoform ATP-site structure counts, resolutions, constructs, and how many contain an **open specificity pocket**.
6. Curated **MMP selectivity-switch set** for S5.
7. Estimated evaluation-set size after scaffold-aware splitting.

**Tier 2**
8. Per external target, compounds measured **alongside a full Tier 1 panel**. Expect mTOR plentiful, DNA-PK marginal, Vps34 and Class II sparse.
9. Declare per-target evaluation mode: **quantitative** (sufficient for S8a) or **qualitative**. Do not compute an ECE on eleven data points.
10. Tier 2 structural data availability and quality.
11. **Sealed correspondence ordering**, weighting, and **sealed S8c covariate list** (§1.4.1, §2.1).
12. **Dual-inhibitor census** (§3.5).

**Knowledge extraction**
13. **Locked reference rule set** (§3.6), sealed by the Auditor.
14. Pre-specified S10a mutation sites and S10b null-control sites.
15. **Empirical calibration of the S9b precision floor** (§3.6.5).

**Transfer**
16. **Sealed second-family selection** for S7. The family must be named, justified against the A.2 correspondence criteria, its data availability audited, and sealed **before** Tier 1 modelling begins. Candidates include the JAK paralogs (JAK1/2/3/TYK2 — four ATP-competitive targets with a deep isoform-selectivity literature and clinically validated selective agents) and AKT1/2/3. Post hoc selection is prohibited: a family chosen after Tier 1 results are known will be chosen to be easy, and S7 would demonstrate nothing.

**Gate:** if Q1 yields < 300 compounds across < 8 families, invoke the kill criterion. If Q2 yields no propeller-shaped series, S6 is untestable and the induced-pocket contribution is dropped. If Q8 yields no quantitative Tier 2 target, S8a is dropped and S8b/S8c become the sole external criteria. If Q9 yields fewer than three quantitative targets, S8c is reported qualitatively with the limitation stated. If Q13 yields fewer than 8 operationally testable reference rules, S9 thresholds are recalibrated before modelling or S9 is withdrawn. If Q16 finds no second family with adequate data, S7 is struck and §9.6 applies.

**Warning.** Stage 0 is the largest single stage, and its pre-registration deliverables (sealed rule set, sealed correspondence ordering and covariates, sealed second family, MMP switch set, mutation-site pre-specification, dual-inhibitor census) are the first casualties of schedule pressure. Ring-fence the time in §1.6 or the falsifiability architecture of Part I becomes decorative.

## 3.2 Stage 0.5 — Orthosteric mutation-propagation test (blocking for Option B only)

Because the hotspot residues do not line the ATP pocket, Option B rests on an unverified physical premise. H1047R in particular is expected to act through altered membrane engagement and conformational communication rather than local ATP-site geometry — so a geometry-only test would likely return a false negative.

### 3.2.1 System setup

Matched apo and holo ensembles of wild-type p110α, H1047R, E542K and E545K in **equivalent constructs** (heterodimeric where available). Identical force field, water model, ionization, box and equilibration across conditions. Minimum **5 independent replicates per condition** — three is insufficient for the null in §3.2.3.

### 3.2.2 Measurements

**Local, at the orthosteric pocket:** pocket volume distribution; rotamer state populations (Trp/Met shelf, affinity-pocket residues); affinity-pocket geometry and hinge distances; ordered water occupancy and residence times; electrostatic potential at the adenine and affinity sub-sites.

**Dynamic and network-level:** dynamic cross-correlation (DCCM) mutant vs. wild-type; residue interaction network construction and comparison (contact-based and/or energy-weighted); community structure analysis, including whether the ATP site changes community membership; communication path analysis from mutation site to ATP-site residues (shortest and suboptimal paths, betweenness); transfer entropy or equivalent directed-information measure (optional, reportable only with the §3.2.3 null satisfied).

### 3.2.3 Statistical controls (mandatory)

Any two MD ensembles differ in cross-correlation; with thousands of residue pairs and few replicates, "significant" network differences are near-guaranteed.

1. **Replicate-level null** built from *within-condition* replicate pairs (WT vs. WT, mutant vs. mutant). Between-condition differences count only if they exceed it.
2. **Effect size, not p-value**, standardized against the within-condition distribution.
3. **Multiple-comparison correction** across residue pairs and network measures.
4. **Convergence reporting** (block averaging or equivalent); unconverged metrics are inconclusive, not null.
5. **Timescale caveat, binding.** Allosteric communication changes may require microsecond sampling. At 100-ns-scale replicates a negative is **inconclusive rather than a true negative.** Either commit to enhanced sampling, or record "not detected at accessible timescale" and refrain from concluding no propagation exists.

### 3.2.4 Outcome matrix

| Cell | Finding | Option B | Publication |
|---|---|---|---|
| **A** | Mutation-dependent difference in ATP-site **geometry or electrostatics** exceeding the null | **Live.** Directly exploitable by an ATP-competitive ligand | Structural finding |
| **B** | Geometry null, but ATP-site **own dynamics** differ — flexibility, rotamer kinetics, water residence | **Conditionally live.** Exploitable via conformational selection; requires a modified design hypothesis and a Decision Record | Dynamics finding |
| **C** | Geometry and site dynamics null; only **remote** network changes | **Retired.** An ATP-competitive ligand cannot read a difference not manifesting at the site it occupies | Allostery finding, separate paper; does **not** open Tier 3 |

Cell C is worth publishing — it would explain from first principles why the field pursues mutant selectivity allosterically — but is not a rescue of Option B and must not be reported as one.

## 3.3 Data policies

- **Censored data are data.** Right-censored inactives retained and modelled with a censored likelihood — never discarded, never imputed to the threshold.
- **Negative-evidence scarcity is a known bias.** Inactives are systematically under-reported, distorting the symmetric treatment required by §4.2. Quantify in Stage 0; report with every result.
- **Provenance mandatory** per record: source, study, assay, ATP concentration, construct, date, curator, extraction version, tier.

## 3.4 Splitting (binding immediately)

- Scaffold- or series-aware at minimum; time-aware where chronology exists.
- Held-out set contains **entire series absent from training**.
- Model-selection folds respect the same series boundaries as the final split.
- Stratify so evaluation is not dominated by data-rich isoforms.
- Report a **nearest-neighbour Tanimoto baseline** with every result.
- Tier 2 sits outside the partition entirely (§0.4).

## 3.5 Dual-inhibitor contamination control

Dual PI3K/mTOR inhibitors are abundant; flat morpholino-triazine chemotypes engage both. Tier 1 training data therefore contains many compounds *designed* to hit mTOR — **chemotype leakage**, which inflates apparent Tier 2 generalization and is the most likely cause of an upward S8c departure at mTOR. This is why chemotype overlap is a pre-registered S8c covariate (§1.4.1).

1. Stage 0 dual-inhibitor census (§3.1 Q12).
2. Tier 2 evaluation **stratified** into (a) series containing known dual agents and (b) series not. S8a and S8c assessed on stratum (b) as primary, (a) as secondary.
3. If stratum (b) is too small, S8a is **inconclusive**, not passed. Passing on (a) alone demonstrates chemotype recall, not generalization.

## 3.6 The locked reference rule set (required for S9)

**3.6.1 Construction.** The Auditor curates known transferable orthosteric selectivity rules for Class I PI3K from the medicinal chemistry literature. Illustrative form: occupancy of the induced specificity pocket by a propeller-shaped ligand → β/δ preference; hydrogen bonding to the affinity-pocket residue at p110α position 859 → α preference; hinge-binding motifs common to all four isoforms → selectivity-neutral.

**3.6.2 Requirements.** Each rule must be **operationally testable** — stated so a matched molecular pair could contradict it. Vague statements are excluded. Each carries its citation and supporting evidence class.

**3.6.3 Locking.** Sealed with timestamp and hash **before any model is trained**, invisible to the model developer. No post-sealing modification; modification voids S9.

**3.6.4 Blinded adjudication.** Model-emitted rules outside the reference set are adjudicated *plausible-and-novel*, *implausible*, or *trivial*, blind to generation, with scrambled-label outputs mixed into the same batch.

**3.6.5 Empirical precision floor.** The provisional S9b threshold of 30% is arbitrary. At Stage 0, run the full extraction procedure on a deliberately uninformative baseline (ligand-only or randomly initialized) and measure its precision. Set the S9b floor above that value, making the threshold calibrated rather than invented.

---

# Part IV — Learning Contract

## 4.1 What is learned

Target: `S₁` (§2.3.4) with per-isoform Productive / Non-Productive / Indeterminate classification, each carrying confidence, uncertainty, and links to supporting evidence. Model outputs are **evidence**, never conclusions (C1). Tier 2 ratios are predicted but never trained on (A.7).

## 4.2 Binding requirements on any implementation

1. **Comparison must be represented.** Four accurate independent per-isoform predictors do not satisfy this. Predict the log ratio directly and compare against the difference of independent predictions. Note §A.4: parameter sharing alone does not satisfy this requirement.
2. **Symmetric evidence.** Productive α binding and β/γ/δ sparing enter the objective with equal weight — not as an affinity model with a penalty bolted on.
3. **Pocket conformational states are inputs**, not averaged away (C6, §2.1).
4. **Per-target applicability domain.** A single molecule-level AD is non-compliant.
5. **"I don't know" must be expressible** per target.
6. **Evidence independence.** Repeated observations from one method are one observation.
7. **A ligand-only baseline is mandatory** in every report, and on Tier 2 for S8a/S8c.
8. **The model must accept an arbitrary ATP site as input** (§4.6).
9. **The model must accept a mutated input structure** and re-predict without retraining (§2.1, for S10).
10. **The explanation interface must emit discrete, operationally testable statements** (§4.7), or S9 cannot be scored.

## 4.3 The degeneracy problem and its tests (the operational form of A.7)

| Test | Procedure | Pass condition |
|---|---|---|
| Pocket shuffle | Permute isoform pocket features at evaluation | Performance drops ≥ 0.3 log RMSE |
| Ligand-only ablation | Train with no protein features | Full model beats it by ≥ 0.3 log RMSE |
| Δ-prediction | Direct log-ratio vs. difference of independent predictions | Direct is better calibrated |
| MMP switch set | Held-out pairs known to flip selectivity | ≥ 60% correct direction |
| Scaffold-family holdout | Whole families withheld | Determinant recovered in ≥ 4 of 5 |
| Apo-ablation | Remove induced-pocket / rotamer features | Propeller ranking collapses (confirms C6 is doing work) |
| Tier 2 zero-shot | Unseen ATP sites, once, logged | S8a, S8b |
| Correspondence gradient | Covariate-adjusted per-target performance against sealed ordering | S8c (descriptive; §1.4.1) |
| Scrambled-label | Retrain on permuted labels; run full explanation pipeline | Chance-level rule recall (S9c) |
| In-silico mutation | Determinant knockout + null control | S10a, S10b |
| Cross-family transfer | Sealed second family, no retuning | S7 |

## 4.4 Evaluation

Aggregate accuracy or AUC is never sufficient. Required: comparative discrimination, per-target calibration, the full §4.3 battery, determinant reproducibility across independent series, Tier 2 zero-shot with query log and covariate-adjusted gradient analysis, S9 rule extraction with scrambled control, S10 counterfactual tests with null control, cross-family transfer, and prospective performance where obtainable.

## 4.5 Monitored failure modes

Named owner and monitoring method each: Tier 1 evidence imbalance; confounding by structure quality or assay format; negative-evidence scarcity; hypothesis lock-in; distribution shift with unenforced per-target AD; comparative degeneracy; label-noise ceiling violation; apo-pocket degeneracy; dual-inhibitor chemotype leakage; Tier 2 budget erosion; correspondence-indifference (S8c-4); narrative generation in rule extraction; non-specific explanation sensitivity; scope drift.

## 4.6 Representation — Path A adopted (from A.7)

**Path A is adopted as the project default.** The representation shall be **correspondence-free at the input interface**: geometric, field-based, or otherwise invariant to residue indexing, accepting any ATP site — including Tier 2 targets, second-family targets and mutated Tier 1 structures — without alignment to Class I positions.

This is not in tension with A.1. Correspondence is required for the **learning task**; correspondence-freedom is a property of the **input interface** (A.7). Per the glossary, *alignment* is one implementation of correspondence, not correspondence itself, so a model may honour A.1 without performing an explicit alignment. Equally, per §A.4, accepting arbitrary inputs does not by itself establish correspondence — the input interface is permissive; the scientific claim is not.

Rationale for rejecting the alternative: a representation indexed by aligned Class I residue positions cannot accept mTOR (no Trp/Met cleft analogue), cannot accept the second family, and cannot cleanly accept a point-mutated structure. It would forfeit **S7, S8a, S8b, S8c and S10** — every generalization and causal test — for sample efficiency on four pockets.

**Path B (correspondence-indexed) requires a gate-level Decision Record** documenting that Path A was implemented and evaluated, the specific sample-efficiency threshold it failed, and formal amendment of §1.4 to strike S7, S8a, S8b, S8c and S10, with the loss recorded in the risk register. Path B is not selectable for convenience, and choosing it forfeits every generality claim (§9.6).

## 4.7 Explanation interface requirement

S9 is unscoreable against a continuous attribution map. The model must expose an interface producing **discrete candidate rules**:

> *structural feature or ligand property* → *predicted selectivity direction* → *supporting evidence set* → *confidence*

each expressed so a matched molecular pair could contradict it. Derivation method (attribution clustering, symbolic distillation, surrogate rule induction, contrastive MMP analysis) is an implementation choice recorded by Decision Record. That the interface exists and emits falsifiable statements is a charter requirement.

---

# Part V — Scientific Knowledge Layer

*Reintroduced from v3.x in minimal form. v3.x devoted several chapters to ontology while possessing no data and no implemented component; v4.0–4.2 removed it entirely, reducing the project to a predictive pipeline. This is the smallest version that does real work.*

## 5.1 Justification test (binding)

A knowledge graph is warranted only if it answers queries a relational table cannot. Three such queries justify it; all are traversal-shaped:

1. **Contradiction since promotion.** *Which promoted Design Rules are contradicted by evidence added after their promotion date?*
2. **Unsupported claims.** *Which Determinant claims rest on evidence class E1 or E2 only, with no E3 or E4 support?*
3. **Provenance chains.** *For this candidate, trace every evidence record, model generation, pocket definition version and reference structure contributing to its prediction.*

**Any proposed schema extension must name a fourth such query.** If it cannot, the information belongs in a table.

## 5.2 Minimal schema

**Nodes (8, capped):** Molecule · Chemical Series · ATP-Site Pocket Version · Interaction Evidence Record · Selectivity Prediction · Candidate Determinant · Determinant · Design Rule

**Edges (6, capped):** `supports` · `contradicts` · `derived_from` · `supersedes` · `belongs_to` · `perturbationally_tested_by`

Adding a type requires a Decision Record naming its justifying query and a retirement; the caps do not rise.

## 5.3 Integration points

| Source | Enters as |
|---|---|
| Docking, MM/GBSA, MD, FEP | Interaction Evidence Record, with method, version, replicate count, reliability |
| Model prediction | Selectivity Prediction, linked to model generation hash |
| Model explanation (§4.7) | Candidate Determinant, class E1 |
| S10 in-silico mutation | `perturbationally_tested_by` edge, class E2 |
| Alchemical mutation / FEP | `perturbationally_tested_by` edge, class E3 |
| Matched molecular pair result | `supports` or `contradicts` edge |
| Experimental assay or mutagenesis | Interaction Evidence Record, class E4 |
| Literature rule (§3.6) | Design Rule, flagged as sealed reference-set member |

## 5.4 Promotion and contradiction rules

- **Candidate Determinant → Determinant** requires a `perturbationally_tested_by` edge of class **E3 or E4**. E1 and E2 combined are insufficient. This is where S10 connects to the knowledge layer — and where it stops.
- **Determinant → Design Rule** requires reproducibility across ≥ 2 independent chemical series and at least one E4 edge.
- **Contradiction is retained, never deleted.** A contradicted rule is marked, not removed; both edges persist. Query 1 depends on this.
- **Demotion is first-class** and recorded with the evidence that caused it.
- **Everything is versioned.** Pocket definitions, model generations and rule statements carry versions; predictions reference the versions that produced them.

## 5.5 Size budget

Knowledge-layer documentation ≤ **3 pages**; schema within §5.2's caps.

---

# Part VI — Validation and Decision Contract

## 6.1 Levels of computational rigor

("Levels" are rigor tiers, distinct from the Tier 1/2/3 scope tiers of §0.1.)

| Level | Method | Cost / compound | Compounds | Advance if |
|---|---|---|---|---|
| L1 | Docking + counter-docking, 4 Class I ATP sites | | | pre-registered |
| L2 | Interaction fingerprint + MM/GBSA | | | pre-registered |
| L3 | MD, replicated, 4 isoforms | | | pre-registered |
| L4 | Alchemical / FEP — ligand pairs **and** residue mutations (class E3) | | | pre-registered |
| L5 | Synthesis + assay, ATP-matched Class I panel + mTOR | | | — |

Thresholds set before results are seen. Post-hoc adjustment invalidates the level. L4 carries a second function: alchemical **residue** mutation is the cheapest route to E3 evidence and therefore to legitimate Determinant promotion (§5.4).

## 6.2 Molecules as hypotheses — operationalized

Each proposed molecule carries, **before** evaluation: the Design Rule or Candidate Determinant it tests; a quantitative prediction with CI; the observation that would **falsify** the rule; and the level at which falsification is decided. Without all four it is a suggestion, not a hypothesis, and is excluded from knowledge-layer updates.

## 6.3 Experimental arm

Either name synthesis and assay partners and the compound budget in §1.6, or formally record the project as computation-only and downgrade all outputs to computational hypotheses with no Determinant or Design Rule claims. Under §5.4 a computation-only project can reach Determinant status via L4 alchemical mutation (E3) but **cannot reach Design Rule status**, which requires E4.

---

# Part VII — Governance (minimal)

**7.1 One record type.** A dated Decision Record: *Decision · Date · Alternatives · Evidence · Reversibility · Review trigger.* Only irreversible or costly decisions get one.

**7.2 One status vocabulary.** `Provisional` → `Validated` → `Retired`. Concepts only, never document sections.

**7.3 One ontology, one owner.** Objects defined in exactly one place (§5.2); additions require a Decision Record and a retirement. Terms defined once in §A.9.

**7.4 Provisional definitions permitted.** Work proceeds on provisional definitions, cited as provisional, reviewed at gates.

**7.5 Documentation budget.** Governance documentation ≤ 20% of project artifacts by page count. (v3.x: ~100%.) **Note:** this charter is itself the principal governance artifact, and separating implementation detail into the specification of §7.9 is part of how the ratio is kept. If the charter grows further without implementation artifacts accumulating, §7.5 is being violated by this document.

**7.6 Scope-drift and overclaim guard.** Every artifact declares its **tier**. Tier 3 references require removal or a gate-level scope-amendment Decision Record. Overclaim violations: describing S10 as biological causal validation; reporting a Candidate Determinant as a Determinant; reporting Stage 0.5 outcome C as support for Option B; reporting a Tier 2 number without a log entry; asserting a comparative determinant across a correspondence gap (A.1); **presenting the founding hypothesis as proven, or stating it without the "with mechanistic determinant attribution" qualifier**; making a generality claim without S7 (§9.6); **claiming a significance test on the S8c gradient at n = 4**.

**7.7 Independent audit.** The Auditor (§1.6) owns the Tier 2 query log, sealed rule set, sealed correspondence ordering and covariate list, sealed second-family selection, S10 null-control design, and blinded rule adjudication. Any of these produced or modified by the model developer is invalid. Barrier violations are recorded, not quietly corrected.

**7.8 Hypothesis amendment.** Per A.8.

**7.9 Companion Implementation Specification (mandatory).** The charter states **what must be true**; a separate Implementation Specification states **how**. It shall contain: a requirement-to-module traceability matrix covering every binding requirement in Parts 0–VI; software module boundaries and APIs; data schemas; the knowledge-layer storage and query implementation; compute and storage estimates per rigor level; and milestone definitions matched to the phases of §9.0.

Relationship rules:
- The specification may not weaken, reinterpret or silently omit a charter requirement. Conflicts resolve in the charter's favour.
- The specification versions independently and is expected to churn; the charter is expected to be stable.
- Every charter requirement must map to at least one specification item or be explicitly marked deferred with a phase (§9.0).
- The specification is the appropriate home for everything this charter deliberately refuses to prescribe: architectures, loss functions, optimizers, tooling, schedules.

---

# Part VIII — Risk Register

| # | Risk | Severity | Mitigation | Kill trigger |
|---|---|---|---|---|
| R1 | Insufficient four-isoform panel data | Fatal | Stage 0 | < 300 cmpds / < 8 families |
| R2 | Central question already answered | Fatal to novelty | Option A framing; title; §1.2 | Uncited prior art at review |
| R3 | Comparative degeneracy (A.7) | Fatal to claims | §4.3 battery | S2 or S3 fails |
| R4 | Apo-pocket definition deletes induced specificity pocket (C6) | Fatal to determinant claims | §2.1(1); apo-ablation | S6 fails |
| R26 | Founding hypothesis presented as proven; reviewer produces a counterexample | Fatal to framing | A.3 status and falsification conditions; **§A.4 named counterexamples answered**; §7.6 | Any artifact asserting A.1 as established |
| R27 | Correspondence conflated with homology; framework appears narrower than it is | High | **A.2 three-kind taxonomy**; §A.9 glossary; correspondence ordering in §2.1 | Sequence-identity-only ordering used for S8c |
| R28 | S8c overconstrained — chemistry- or data-quality-driven departure read as failure | High | **§1.4.1 covariate-adjusted descriptive report; two-sided departure handling; reversal-only failure condition** | S8c-4 conditions all met |
| **R32** | **S8c reported as a significance test despite n = 4** | **Moderate** | **§1.4.1 statistical-honesty clause; §7.6** | **Any p-value claimed on the gradient** |
| **R33** | **Correspondence assumed stable when it is not (A.1(4)) — e.g. homologous sites with divergent conformational behaviour** | **High** | **A.1(4); C6; stability assessment in the §2.1 ordering; apo-ablation test** | **S6 fails, or ordering omits stability** |
| R29 | No cross-family transfer → framework appears PI3K-specific | High | S7 as gate; sealed second family; §9.6 honesty clause | S7 absent → case-study framing mandatory |
| R30 | Second family selected post hoc and chosen to be easy | High | §3.1 Q16 sealing before Tier 1 modelling | Selection dated after modelling start |
| R31 | Scope collapse under implementation load | High | §9.0 phase partition; §7.9 specification; phase commitment | No phase committed by end of Stage 0 |
| R18 | Rule extraction produces plausible narrative from noise | Fatal to S9 | §3.6 sealed set; S9c; blinded adjudication | S9c fails |
| R19 | Stage 0.5 dynamic metrics return near-guaranteed false positives | High | §3.2.3 null, effect sizes, correction | Effects within within-condition null |
| R20 | Stage 0.5 negative is a sampling artefact | High | §3.2.3(5) timescale caveat | — |
| R21 | S10 overinterpreted as biological causality | High | §1.4 limit; §2.5; §7.6 | Overclaim in any artifact |
| R22 | Explanation module non-specific | High | S10b null control | S10b fails |
| R5 | ATP-concentration / assay heterogeneity dominates signal | High | §2.3 within-study-only | Assay covariates explain > 50% of variance |
| R6 | Hotspot mutations do not reach the ATP site | High (Option B) | §3.2 outcome matrix | Outcome C |
| R7 | No experimental arm → Design Rules unreachable | High | §6.3 forced election | — |
| R14 | Tier 2 barrier erosion | High | §0.4 budget; §7.7 | Two unlogged queries |
| R15 | Dual-inhibitor chemotype leakage inflates S8a/S8c | High | §3.5 census + stratification; S8c covariate | Stratum (b) too small |
| R16 | Path B chosen → S7, S8, S10 all lost | High | §4.6 Path A default | Path B without documented Path A failure |
| R23 | Stage 0 pre-registration abandoned under schedule pressure | High | §3.1 warning; ring-fenced time | Any sealed artefact created after modelling began |
| R24 | Knowledge layer regrows into the v3.x ontology cathedral | Moderate | §5.1 query test; caps; budget | Schema exceeds caps without retirement |
| R9 | Structure-quality asymmetry (β sparsest; Tier 2 uneven) | Moderate | Covariate in all evaluations; S8c covariate | β uncalibrated at any sample size |
| R10 | Label-noise ceiling exceeded | Moderate | Stage 0 Q4 | Reported RMSE < inter-lab σ |
| R11 | Scope drift toward Tier 3 | Moderate | §7.6 | Two unamended violations |
| R12 | Hypothesis lock-in | Moderate | Adversarial review each gate | — |
| R17 | Tier 2 too sparse for quantitative evaluation | Moderate | §3.1 Q9 | < 3 quantitative targets → S8c qualitative |
| R13 | Governance overgrowth, including by this charter | Low | §7.5 note; §7.9 separation | Ratio > 20% |

---

# Part IX — Phasing and Staged Plan

## 9.0 Phase partition and the minimum defensible deliverable

The charter specifies comparative learning, uncertainty estimation, explanation, rule extraction, counterfactual testing, a knowledge layer, MD, alchemical mutation, cross-family transfer, provenance and governance. Each is individually justified; collectively they constitute a multi-year platform. Attempting all of it at once produces ten half-finished workstreams.

The project therefore commits to a phase at Stage 0 (§1.6). Each phase is independently publishable.

| Phase | Contents | Criteria | Deliverable |
|---|---|---|---|
| **Phase 1 — Core** | Tier 1 comparative model; per-isoform calibration; full degeneracy battery; determinant recovery | S1, S2, S3, S4, S5, S6 | **A defensible methods result on its own** — comparative selectivity learning on Class I PI3K with degeneracy controls most published work lacks. Requires no Tier 2, no knowledge layer, no rule extraction, no MD-scale resources, no experimental arm |
| **Phase 2 — Extension** | Explanation interface; rule extraction with scrambled control; in-silico counterfactual testing; Tier 2 evaluation with correspondence-gradient analysis | S8a, S8b, S8c, S9a–c, S10a–b | Knowledge-extraction and correspondence-floor claims become available |
| **Phase 3 — Full** | Knowledge layer; Stage 0.5 dynamics; L4 alchemical mutation to E3; cross-family transfer; prospective experimental test | S7, E3/E4 promotion, Option B election | Design Rule claims, generality claims, therapeutic framing |

**Descoping rule.** Under resource pressure, phases are dropped from the top, never partially executed across all three. A Phase 1 result honestly described is worth more than three phases attempted and none completed. Dropping a phase requires only a Decision Record, not a charter amendment.

**Claim ceiling by phase.** Phase 1 supports no determinant claim (no perturbational evidence) and no generality claim. Phase 2 supports Candidate Determinant claims and a correspondence-floor finding. Only Phase 3 supports Design Rules and generality.

## 9.1 Stage 0 — Feasibility and pre-registration (blocking, largest stage)

Tier 1 and Tier 2 data audits; ATP-site reference structure enumeration with specificity-pocket status and verified residue numbering; **sealed correspondence ordering, weighting, stability assessment and S8c covariates**; MMP switch-set curation; dual-inhibitor census; **sealed S9 reference rule set**; empirical S9b floor calibration; pre-specified S10 mutation and null-control sites; **sealed second-family selection**; resource declaration including the Auditor, ring-fenced pre-registration time, and **phase commitment**. *Gate: proceed / redesign / stop; Tier 2 modes fixed; S8c quantitative or qualitative; S9 thresholds fixed or withdrawn; S7 live or struck.*

## 9.2 Stage 0.5 — Mutation-propagation test (Phase 3; blocking for Option B only)

§3.2 with full statistical controls. *Gate: outcome A, B or C recorded.*

## 9.3 Stage 1 — Baselines and representation (Phase 1)

Ligand-only, nearest-neighbour and proteochemometric baselines on Tier 1. Implement **Path A**; implement the §4.7 explanation interface if Phase 2 is committed. Fix all thresholds. *Gate: if a baseline already meets S2, the learned component is unjustified.*

## 9.4 Stage 2 — Comparative model (Phase 1)

Part IV. Full §4.3 battery excluding Tier 2 and transfer; including scrambled-label and S10 tests if Phase 2 is committed. *Gate: S2, S3, S4, S6 (+ S9c, S10a, S10b if Phase 2).*

## 9.5 Stage 3 — Knowledge extraction and first Tier 2 query (Phase 2)

S1 across held-out families; S9a/S9b against the sealed rule set with blinded adjudication; **one logged Tier 2 evaluation** including covariate-adjusted correspondence-gradient analysis. *Gate: S1, S5, S9a, S9b, S8a, S8b, S8c.*

## 9.6 Stage 4 — Cross-family transfer (Phase 3; a gate, not an option)

Evaluate the **sealed second family** (§3.1 Q16) with no framework retuning; second logged Tier 2 query on the next model generation. L4 alchemical residue mutation to convert leading Candidate Determinants to E3. Report S8c over the combined correspondence gradient (§1.4.1).

**Optional stronger extension.** Per A.2, a *non-homologous but structurally corresponding* ATP site is a harder and more informative transfer target than a homologous paralog family, because it tests correspondence in the sense the hypothesis actually asserts rather than in the ancestral sense. If data permit, add such a target and report it separately.

**Honesty clause (binding).** Because Stage 4 carries the entire generality claim, its absence changes what the project is. Without S7, the deliverable is **a case study on Class I PI3K**, and the title, abstract and conclusions must say so — no general framework claim, no transferability claim, no "applicable to other protein families." Breach is a §7.6 overclaim violation.

## 9.7 Stage 5 — Prospective test (Phase 3)

Molecules with pre-registered predictions (§6.2), synthesized and assayed against the Class I panel and mTOR. Required for any Design Rule claim (§5.4). Requires §6.3.

---

# Appendix A — Retained principles

Correct in v3.x and carried forward: selectivity is comparative and cannot be inferred from α alone (now derived as C4); negative and positive evidence carry equal weight; independent evidence outweighs repeated evidence; Indeterminate is distinct and never counts as sparing; every prediction carries confidence and uncertainty; prefer mature validated methods absent clear advantage; computational predictions are never presented as experimental facts; understanding outranks predictive performance; series-aware evaluation is mandatory; contradiction is retained rather than deleted; agreement never outranks scientific accuracy.

# Appendix B — Defects corrected

| Origin | Defect | Fix |
|---|---|---|
| v4.5 A.3 | ML counterexamples answered only in general terms; named systems (PLMs, foundation docking, universal affinity predictors, cross-protein graph transformers) unaddressed | **§A.4** answers each individually on the **parameter-sharing ≠ correspondence** distinction; §1.2 requires citing them |
| v4.5 A.1 | Correspondence stability not required; a mapping valid in one conformational state but not another would satisfy A.1 | **A.1(4)** stability requirement; C6 now derives from it directly; stability assessment added to the §2.1 ordering; R33 |
| v4.5 A.2 | Two-kind (structural/functional) split coarser than needed | **Three-kind taxonomy** (evolutionary / structural / physicochemical) with one-way imperfect entailments and an explicit weakest-sufficient-level argument |
| v4.5 §1.4.1 | S8c framed as a partial rank correlation, which has negligible power at n = 4 | **Descriptive covariate-adjusted report**; explicit no-significance-claimed clause; two-sided departure handling; **reversal-only** failure condition; power note on S7; R32 |
| v4.4 A.1 | Founding statement presented as an established mathematical premise | Founding hypothesis; A.3 status and falsification conditions; "foundational" replaces "mathematical"; §7.6 |
| v4.4 | Stage 4 optional despite carrying the generality claim; second family unsealed | S7 elevated to gate; §3.1 Q16; §9.6 honesty clause |
| v4.4 | Implementation load unbounded; no descoping path | §9.0 phase partition; §7.9 specification; phase commitment |
| v4.3 §0.5 | Central premise appeared as a subordinate scope justification | Part A promoted to front; corollaries explicit |
| v4.2 §1.4 | All criteria prediction-oriented; no knowledge-extraction benchmark | S9a/S9b/S9c; §3.6; §4.7 |
| v4.2 §1.4 | No causal-robustness test | S10a/S10b; §2.5 evidence classes |
| v4.2 §3.2 | Stage 0.5 geometry-only; would likely false-negative on H1047R | §3.2.2 dynamics; §3.2.3 controls; §3.2.4 outcome matrix |
| v4.2 §4.6 | Representation fork left open | Path A adopted |
| v4.0–4.2 | Knowledge graph removed entirely | Part V, minimal and query-justified |
| v4.2 title | Named the target, not the contribution | Retitled with "benchmarked on" |
| v4.1 §2.3(6) | Wider ATP-site panel folded into the primary task | §0.1 three-tier scope, derived from A.7 |
| v4.1 | No information barrier for external targets | §0.4; §7.7 |
| v4.1 | Dual PI3K/mTOR chemotype leakage unaddressed | §3.5; S8c covariate |
| v4.0 | Allosteric agents cited as frontier; Option B permitted allosteric route | §0.2, derived from C5 |
| v3.x §1.4 | Central question already answered | §1.3 Option A; title |
| v3.x §1.7 P2 | "Selectivity before affinity" lexicographic error | §2.3(6) potency floor |
| v3.x §2.3, §2.5 | Governance deadlock | §7.4 |
| v3.x §2.6 | Non-Productive defined as negation then forbidden from being negation | §2.2 positive criteria for all three |
| v3.x §2.10, §4.8 | Status contradictions | §7.2; Part IX |
| v3.x Ch. 5, Ch. 11 | Ontology objects added outside the ontology; duplicated concepts | §5.2 capped schema; §7.3 |
| v3.x Ch. 6 / Ch. 11 | Duplicate chapters, identical title | Merged into Part IV |
| v3.x §6.13 | Degeneracy risk named, no test | §4.3; derived from A.7 |
| v3.x §7.11 vs §2.3 | Four readiness states vs. three | §7.2 |
| v3.x §11.10 | Min-rule for uncertainty | §2.4 conjunction |
| v3.x §11.12 | Novelty table a straw man; proteochemometrics uncited | §1.2 |
| v3.x Ch. 14 | Third restatement of the learning framework | Deleted |
| v3.x throughout | No data audit; no resource model; no experimental arm | Part III; §1.6; §6.3 |
| v3.x throughout | No PI3K structural biology, constructs, or assay physics | §0.3; §1.2; §2.1; §2.3 |
| v3.x throughout | Two project titles, six version numbers | Single title, single version |
