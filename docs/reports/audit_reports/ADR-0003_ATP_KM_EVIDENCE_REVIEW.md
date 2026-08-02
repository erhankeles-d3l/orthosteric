# ADR-0003 ATP Km Evidence Review (AUDITOR-5)

**Status of this document: developer evidence-gathering output — requires Independent
Scientific Auditor decision.** No ATP Km value is sealed, adopted, or proposed as final
here. This revision replaces the prior version of this document, whose earlier attempt
to fetch the paper below was blocked; a subsequent fetch attempt succeeded and is
reported here in full, with its own limitations disclosed explicitly (§E).

---

## A. Source retrieved and verified

> Somoza, J.R., Koditek, D., Villaseñor, A.G., Novikov, N., Wu, M.X., Villasenor, A.G.
> (Gilead Sciences, Inc.), *et al.* "Structural, Biochemical, and Biophysical
> Characterization of Idelalisib Binding to Phosphoinositide 3-Kinase δ."
> *J. Biol. Chem.* 290(13):8439–8446. Published online 2015-01-28.
> DOI: `10.1074/jbc.M114.634683`. PMID: `25631052`. PMCID: `PMC4375495`.

**Retrieval:** full text fetched from `https://pmc.ncbi.nlm.nih.gov/articles/PMC4375495/`
via three separate tool calls on 2026-08-01 (retrieval date), each targeting a
different, narrower extraction question to cross-check internal consistency.

## B. What was extracted, verbatim, from the paper

### Table 1 — Time-resolved FRET (HTRF) ATP Km, all four Class I isoforms

| Isoform | Km(ATP), TR-FRET (μM) | IC50 of idelalisib at 2×Km ATP (nM) | Fold selectivity vs. PI3Kδ |
|---|---:|---:|---:|
| PI3Kα | 48 | 8600 | 453 |
| PI3Kβ | 279 | 4000 | 210 |
| PI3Kγ | 37 | 2100 | 110 |
| PI3Kδ | **118** | 19 | 1 |

*(Reproduced from the tool's quoted extraction of Table 1; no error/uncertainty was
reported in the table for any isoform.)*

### Constructs and species used for the Table 1 measurements (Experimental Procedures)

Quoted: *"The full-length protein used for the PI3Kα, γ, and δ measurements is described
above. The PI3Kβ consisted of a complex of N-terminal His6-tagged recombinant full-length
human p110β and untagged, full-length, human p85α (Millipore)."*

| Isoform | Construct | Species | Regulatory subunit |
|---|---|---|---|
| PI3Kα | full-length p110α | human | p85α |
| PI3Kβ | full-length p110β, His6-tagged | human | full-length human p85α (Millipore) |
| PI3Kγ | full-length p110γ | human | none (γ has no p85-type regulatory subunit) |
| PI3Kδ | full-length p110δ | **murine** | p85α |

**Note the species mismatch:** three of four isoform measurements used human protein;
the PI3Kδ measurement used *murine* p110δ. This is directly relevant to construct-scope
questions the Auditor must decide (§C below) and is stated here as fact, not glossed over.

### Second, independent PI3Kδ measurement — ATP-competition global fit

Quoted (Results, "Idelalisib Is an ATP-competitive Inhibitor"): *"The ability of idelalisib
to compete with ATP binding to PI3Kδ was tested in enzymatic assays. The activity of
PI3Kδ was measured at various concentrations of ATP and idelalisib, and the data were fit
globally to the competition expression described under 'Experimental Procedures.' ...
The global fit yielded the following kinetic parameters: **Km = 37 ± 3 μM** and
Ki = 1.5 ± 0.1 nM."*

The paper's own reconciliation, quoted in full: *"The measured Km value of 37 μm from the
competition data was slightly lower than the value reported in Table 1, but this
difference did not significantly affect the data analysis."*

## C. The reconciliation question — not collapsed to one number

Two values for the same target (PI3Kδ), from the same paper:

| | Table 1 (TR-FRET/HTRF) | Competition assay (Fig. 2, global fit) |
|---|---:|---:|
| Km(ATP) | 118 μM | 37 ± 3 μM |
| Method | Millipore HTRF kinase-activity kit, single-point/standard-curve TR-FRET readout | Direct ATP-titration series, competition-binding model, globally fit jointly with Ki |
| Purpose in the paper | Screening-panel selectivity comparison across all four isoforms (Table 1) | Mechanistic confirmation that idelalisib is ATP-competitive (Fig. 2) |
| Construct | Murine p110δ + human p85α | Not restated in the extracted passage — presumed same construct as used throughout the paper's PI3Kδ work, but this was **not independently confirmed** in this pass |

**What this is, precisely:** two different assay formats measuring (nominally) the same
kinetic parameter for the same enzyme, yielding a >3-fold discrepancy, which the paper
itself notes but does not explain beyond "slightly lower... did not significantly affect
the data analysis." This is not evidence of two different biological constructs or
conditions — the paper does not offer that as the explanation — but the *possibility*
that assay-format-dependent artefacts (e.g., HTRF assay Km being an apparent/operational
Km at a fixed detection format vs. a directly fit kinetic Km) explains the gap **was not
confirmed or ruled out** by anything retrieved in this pass. This is reported as an open
question, not resolved here.

A search for PI3Kδ ATP Km in the wider public literature, independent of this paper,
did **not** surface a second, separately citable primary source with its own numeric
value within this task's search scope (§F). The >3-fold intra-paper discrepancy is
therefore currently uncorroborated in either direction by any second source found.

## D. All four isoforms — summary for AUDITOR-5

| Isoform | Species | Construct | Regulatory complex | Km(ATP) | Uncertainty | Assay | Source | DOI | Location | Comparability to project's intended assay context | Status |
|---|---|---|---|---:|---:|---|---|---|---|---|---|
| PI3Kα | Human | Full-length p110α | p85α | 48 μM | Not reported | TR-FRET (HTRF) | Somoza et al. 2015 | 10.1074/jbc.M114.634683 | Table 1 | Single-source, single-assay-format only | Verified (single source) |
| PI3Kβ | Human | Full-length p110β (His6) | Full-length human p85α | 279 μM | Not reported | TR-FRET (HTRF) | Somoza et al. 2015 | 10.1074/jbc.M114.634683 | Table 1 | Single-source, single-assay-format only | Verified (single source) |
| PI3Kγ | Human | Full-length p110γ | None | 37 μM | Not reported | TR-FRET (HTRF) | Somoza et al. 2015 | 10.1074/jbc.M114.634683 | Table 1 | Single-source, single-assay-format only | Verified (single source) |
| PI3Kδ | **Murine** | Full-length p110δ | p85α | 118 μM | Not reported | TR-FRET (HTRF) | Somoza et al. 2015 | 10.1074/jbc.M114.634683 | Table 1 | Single-source; species mismatch vs. the other three (human) | Verified (single source), **internally conflicting** |
| PI3Kδ | (not restated in the extracted passage) | (not restated) | (not restated) | 37 ± 3 μM | ± 3 μM | ATP-competition, global fit with Ki | Somoza et al. 2015 | 10.1074/jbc.M114.634683 | Fig. 2 / Results text | Same paper, different assay format from the row above | Verified (single source), **internally conflicting** |

Every cell above is either a direct quotation/transcription from the retrieved text or
explicitly marked "Not reported" — none is inferred or filled from memory.

**No second, independently authored source was verified for any of the four isoforms.**
All values in this table trace to one 2015 paper. This is disclosed as a real limitation
of the current evidence base, not minimized.

## E. Retrieval-method limitation — disclosed explicitly

The full text was retrieved through a web-fetch tool that internally uses a
summarization/extraction model to answer a targeted question about the fetched page,
rather than returning raw HTML/PDF text for direct line-by-line reading by this task.
Three separate, increasingly specific extraction queries were run against the same URL
specifically to cross-check internal consistency (e.g., confirming the isoform identity
of the competition-assay value independently of the Table 1 quote), and all three were
consistent with each other. This substantially reduces, but does not eliminate, the risk
of extraction error inherent to any tool-mediated text retrieval.

**Recommendation to the Auditor:** independently confirm Table 1 and the Fig. 2 /
competition-assay paragraph directly against the primary PDF or HTML
(`https://www.jbc.org/article/S0021-9258(20)63985-0/fulltext`,
`https://pmc.ncbi.nlm.nih.gov/articles/PMC4375495/`) before relying on the transcription
above for any sealed value.

## F. Search hierarchy applied, and what was and was not found

1. **Primary peer-reviewed kinetic literature** — Somoza et al. 2015 located and verified
   (§A–D above). This is the only primary source with numeric Km(ATP) values for all
   four Class I isoforms found within this task's search scope.
2. **Independent peer-reviewed enzymology literature** — searched specifically for a
   second, independent PI3Kδ ATP-Km determination. No second primary source with its own
   numeric value was found; search results returned general PI3Kδ structural/biological
   review material and inhibitor-characterization papers that describe assay *conditions*
   (e.g., "2×Km ATP, 100–300 μM") without independently re-deriving Km itself.
3. **Curated databases (secondary corroboration)** — not queried in this pass. Not ruled
   out as unhelpful; simply out of this pass's scope. Flagged as a next step for whoever
   continues this evidence-gathering, not treated as equivalent to a completed search.
4. **Aggregators (BRENDA, SABIO-RK)** — not queried in this pass, for the same reason.
   If used later, per the source-hierarchy principle already stated in this project's
   companion methodological document, any aggregator value must be traced back to its
   own underlying primary publication before being treated as corroborating evidence,
   never accepted at face value.

## G. What this means for the five sub-questions in ADR-0003 §4 / review package item 4

### Authoritative source
**Partially advanced, not resolved.** One primary source now exists with verified,
quotable values for all four isoforms — a substantive improvement over the prior version
of this document, which had zero verified numbers. It is not sufficient by itself to
declare an "authoritative source" for two reasons: (a) it is a single source, with no
independent corroboration found for any isoform; (b) for PI3Kδ specifically, the source
is **internally conflicting** (118 μM vs. 37 ± 3 μM) and does not explain why.

### Construct/isoform scope
**Now has real, source-grounded evidence**, and reveals a scope question the prior
version of this document could not: three isoforms were measured with **human** protein,
PI3Kδ with **murine** protein. Whether a species-crossed PI3Kδ Km is admissible for this
project's Cheng–Prusoff normalization, or whether only a human-construct value should be
sought as a replacement, is squarely an Auditor decision — this review surfaces the fact,
not the resolution.

### Version/date
The mechanism (sealed table, retrieval date, content hash under `sealed/config/`) remains
unchanged from the prior version of this document — no new evidence was needed for the
mechanism, only for the values, which are now available for the Auditor to consider
sealing (or not).

### Conflicting values
**No longer purely hypothetical** — an actual, in-hand conflict now exists (PI3Kδ: 118 μM
vs. 37 ± 3 μM), from the same paper, unexplained by the paper itself beyond "slightly
lower." This is exactly the kind of case the general conflict-resolution principle in the
companion methodological document (geometric mean within a pre-specified tolerance;
otherwise treat as unresolved) was written to anticipate — but applying it here, even
provisionally, would be a decision this document does not make.

### Sealing
Unchanged: mechanically identical to every other seal in this repository. No further
evidence is needed for the *mechanism*.

## H. Explicit statement

**No ATP Km value for any PI3K isoform is asserted, endorsed, sealed, or proposed as
final by this document.** A single primary source (Somoza et al. 2015) has now been
retrieved and its relevant values verified and transcribed in full, including an
unresolved internal conflict for PI3Kδ (118 μM vs. 37 ± 3 μM) and a species mismatch
(murine PI3Kδ vs. human for the other three isoforms) that the source itself does not
address. No independent second source was found within this task's search scope. This
remains `NOT READY` for the Km-sourcing sub-question — the evidence base is now
substantially better documented, but the Auditor must still: (a) decide whether a single,
internally conflicting, species-mixed source is an adequate foundation, or whether
further literature search / a database cross-check is required first; (b) resolve the
118 μM vs. 37 μM conflict for PI3Kδ; and (c) decide the construct/species-scope policy.
