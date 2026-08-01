# ADR-0003 ATP Km Evidence Review (AUDITOR-5)

**Status of this document: developer evidence-gathering output — requires Independent
Scientific Auditor decision.** No ATP Km value is sealed, adopted, or proposed as final
here. Where a numeric value could not be independently verified, none is reported —
per the governing instruction, fabricating a citation or value is worse than reporting
a gap.

---

## A. What was searched, and how

Three targeted web searches were run against public literature indexes:

1. `PI3K p110alpha ATP Km kinase kinetics`
2. `"Km" ATP p110alpha p110beta p110delta p110gamma micromolar kinase assay`
3. `Walker Perisic Williams p110 structure ATP Km kinetic characterization phosphoinositide 3-kinase`

**What these searches consistently found:** biochemical PI3K inhibitor-screening papers
and patents overwhelmingly report assays run at a **fixed** ATP concentration (commonly
10 μM or 100 μM), for the purpose of IC50 determination against compounds — not a
titrated ATP concentration series from which a Km(ATP) is itself derived. This is an
important, real, and directly relevant finding: **the vast majority of the public
biochemical corpus this project would draw on for Tier 1 activity records was generated
at fixed, often-unstated-precisely `[ATP]`, which is exactly the population ADR-0003 §4
already anticipates as "unknown [ATP] → excluded from the primary target."**

## B. The one strong candidate found, and why it could not be verified

One paper explicitly states it performed a genuine kinetic characterization sufficient to
establish ATP-competitive inhibition — which requires having determined (or at minimum
titrated against) Km(ATP):

> Somoza, J.R., Koditek, D., Villaseñor, A.G., et al. "Structural, Biochemical, and
> Biophysical Characterization of Idelalisib Binding to Phosphoinositide 3-Kinase δ."
> *J. Biol. Chem.* 290(13):8439–8446 (2015). DOI: 10.1074/jbc.M114.634683. PMID: 25631052.

Two fetch attempts against this paper's full text (both `pmc.ncbi.nlm.nih.gov` and
`www.ncbi.nlm.nih.gov/pmc` mirrors) were blocked by an automated reCAPTCHA challenge
page, not by absence of the paper. This is a genuine access barrier in this session's
tooling, not evidence that the value doesn't exist or can't be found — a reviewer with
institutional full-text access, or access to a fetch tool not blocked by this challenge,
should check this paper specifically before concluding no Km(ATP) value exists in the
literature for PI3Kδ.

**No numeric Km(ATP) value from this paper, or any other source, is reported here**,
because none was independently verified against retrievable full text. This is the
central finding of this review: a plausible, specific, citable lead exists, but this
task's tooling could not close it out.

## C. What this means for the five sub-questions in ADR-0003 §4 / review package item 4

### A. Authoritative source (not resolved)
A source hierarchy can be *proposed* for Auditor consideration — primary enzymology
literature first, curated compilations second, database aggregators (BRENDA, SABIO-RK)
as a lower-confidence fallback — but this review cannot populate the top tier with a
verified value for any Class I PI3K isoform. **This is the single most important gap
for the Auditor to close**, since it blocks `SCI0-008` regardless of anything else in
this package.

### B. Isoform/construct scope
Not resolved for the reason above. Structurally, the scope should distinguish at minimum
wild-type p110α, β, γ, δ, each in its physiologically relevant regulatory-subunit
complex (p110–p85 heterodimer for α/β/δ; p110γ with p101/p87), per this project's own
`PROJECT_CONSTITUTION_v4.6.md §2.1` construct-policy language — but no verified per-
construct value can be supplied here.

### C. Version/date
Cannot be populated without part A. The *mechanism* — a sealed table with retrieval
date and content hash under `sealed/config/`, matching the pattern already used
elsewhere in this repository (`sealed/MANIFEST.md`) — is available and requires no
further evidence; only the actual source and value are missing.

### D. Conflicting values
Cannot be evaluated in the abstract without at least two independently sourced values to
compare. No policy recommendation beyond the general principle already stated in the
companion methodological document (geometric mean within a pre-specified tolerance;
otherwise treat as unresolved and non-normalizable) can be made specific to PI3K here.

### E. Sealing
Mechanically identical to every other seal in this repository — no new evidence is
needed for the *mechanism*, only for what gets sealed.

## D. Explicit statement

**No ATP Km value for any PI3K isoform is asserted, endorsed, or proposed as a sealed
value by this document.** The evidence-gathering effort found strong indirect evidence
that such measurements exist in the primary literature (assay design, and one paper
explicitly claiming a kinetic characterization) but could not verify a specific number
through the tools available in this session. This is reported as `NOT READY` for the
Km-sourcing sub-question specifically, pending either full-text access to the Somoza et
al. 2015 paper or a broader literature search than this session's tools permitted.
