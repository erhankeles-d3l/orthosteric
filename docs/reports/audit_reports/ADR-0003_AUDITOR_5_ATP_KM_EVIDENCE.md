# AUDITOR-5 ATP Km Evidence (corrected)

**Status:** Evidence prepared, substantially weaker than a prior draft claimed | UNRESOLVED — no isoform-specific value can be established from currently retrievable sources

**Correction note:** an earlier draft of this document over-interpreted the Somoza et al.
2015 methods sentence as implying per-isoform values, and over-weighted the umbralisib
clinical-protocol "100 µM" figure as independent corroboration. Both errors are corrected
below. See `ADR-0003_INTERNAL_EVIDENCE_TABLE.md` for full source-by-source traceability.

**Searches performed:** as previously logged, plus a fifth search tracing the umbralisib
"Km = 100 µM" citation to its underlying reference.

---

## 1. Somoza et al. 2015 (JBC) — FACT / INFERENCE / NOT ESTABLISHED

**Citation:** Somoza JR, Koditek D, Villaseñor AG, et al. J Biol Chem. 2015;290(13):8439–
8446. DOI: 10.1074/jbc.M114.634683. PMID: 25631052.

**FACT — verified from search snippet, quoted verbatim:**
> "PI3K isoforms were assayed under initial rate conditions in the presence of 25 mm
> HEPES (pH 7.4), and 2 × Km ATP (100–300 μm), 10 μm PIP2 [...] at the following
> concentrations for each isoform: PI3Kα, β, δ at 25–50 pm and PI3Kγ at 2 nm."

**INFERENCE — what can mathematically be derived from the FACT above:**
- The three isoforms explicitly grouped together (α, β, δ) were assayed at "2 × Km ATP,"
  and the combined range across whatever concentrations were actually used for each is
  stated as 100–300 µM.
- This means the sum of individual "2 × Km" values used spans that range, so the
  underlying per-isoform Km values are each somewhere in the 50–150 µM interval.
- **This is the only mathematically defensible inference.** It is a bound on a range, not
  three (or four) separate numbers.

**NOT ESTABLISHED — explicitly, per the correction to this document:**
- PI3Kα Km(ATP) = any specific value
- PI3Kβ Km(ATP) = any specific value
- PI3Kδ Km(ATP) = any specific value from this source
- PI3Kγ Km(ATP) — no numeric ATP concentration for γ is given at all in the retrieved
  snippet (only the enzyme concentration, 2 nM, is stated)
- Any one-to-one mapping between a specific isoform and a specific point within the
  100–300 µM range

**A per-isoform Km table cannot be constructed from this source with the material
retrieved in this session.** The paper's own Table 2 (not retrieved — reCAPTCHA-blocked
in this session, as before) may resolve this. This remains the single most consequential
gap, and it is now reported without the earlier overreach.

---

## 2. The umbralisib/TGR-1202 "100 µM" figure — reclassified

**What was previously claimed (incorrect):** that this figure "corroborated" the Somoza
range and represented a second independent primary source for PI3Kδ.

**What is actually established, after tracing the citation:**

The statement "ATP at its Km value (100 µM)" appears verbatim, or near-verbatim, across
at least six independent NCT clinical trial protocol documents (NCT02867618, NCT02742090,
NCT03178201, NCT02612311, NCT03364231, NCT02268851, NCT03828448). **Every one of these
cites the same internal reference** — variously rendered as "(11)," "(10)," or "Prasanna
R, 2011" — which is not a peer-reviewed publication retrievable through this session's
tools. It appears to be an internal Rhizen Pharmaceuticals / TG Therapeutics study report
or conference abstract, not a publicly verifiable primary kinetic determination.

**Reclassification:**
- Source type: **(c) sponsor/clinical documentation**, per the categories specified for
  this correction — not primary kinetic evidence, and not a database.
- Independence: **NOT independently corroborating.** Six documents citing the same
  uncited internal reference is one data point repeated six times, not six data points.
- Confidence: downgraded from the prior draft's "MODERATE" to **WEAK**, on the same basis
  as the Millipore kit value (a stated Km without a traceable primary determination).

**RECOMMENDATION — not a governance decision:** this figure should not be treated as
corroboration for any Somoza-derived inference. If the Auditor wishes to pursue it
further, tracing "Prasanna R, 2011" would require access to conference-abstract archives
(e.g., AACR abstract books from 2011) not searched in this session.

---

## 3. The Millipore kit value (10–20 µM) — reclassified, not averaged

**FACT — directly supported by patent text (USPTO 9388189):**
> "[ATP] was used at 15 μM for all isoforms for technical reasons (Km values varied
> between 10 and 20 μM depending on the isoform)"

**Source type: commercial kit manufacturer's technical specification, cited in a patent
— not a primary kinetic paper.** No original determination is cited or traceable from
this snippet.

**This value is NOT averaged with the Somoza-derived 50–150 µM range.** Per the explicit
instruction governing this correction, the scientific question is not "what single number
should we pick" but "under what experimental context is each number valid." Candidate,
unconfirmed explanations for the discrepancy (all UNRESOLVED, none preferred over another
without further evidence):

- **Apparent vs. intrinsic Km:** lipid kinases assayed against membrane-embedded
  substrate may not follow simple Michaelis-Menten kinetics; a kit-reported "Km" and a
  paper's rigorously fit Km could reflect different operational definitions.
- **Different recombinant constructs:** insect-cell-expressed kit isoforms vs. Somoza's
  specific expression constructs may differ in ways that shift apparent Km.
- **Different lipid substrate / vesicle composition:** Km(ATP) for a lipid kinase is not
  independent of substrate presentation; different PIP2 formulations across assay
  platforms are a plausible driver.
- **Marketing/rounding in the kit's technical documentation:** a manufacturer's
  simplified technical note is not held to the same rigor as a peer-reviewed
  determination.

**No preferred explanation is asserted.** This is presented as a genuine, unresolved
discrepancy requiring either full-text access to a true primary kinetic paper, or direct
experimental determination, to resolve.

---

## 4. Corrected per-isoform evidence summary

| Isoform | What is actually established | Confidence | Source(s) |
|---|---|---|---|
| PI3Kα | Assayed at "2 × Km," where Km falls somewhere in an unallocated 50–150 µM range shared with β and δ. No isoform-specific value. | **WEAK — range only, not isoform-specific** | Somoza 2015 (partial) |
| PI3Kβ | Same as α | **WEAK — range only, not isoform-specific** | Somoza 2015 (partial) |
| PI3Kδ | Same range-only inference from Somoza; separately, a "100 µM" figure appears in six sponsor documents tracing to one uncited internal reference | **WEAK on both counts** | Somoza 2015 (partial); umbralisib sponsor docs (uncorroborated) |
| PI3Kγ | No ATP concentration given in retrieved snippet at all (only enzyme concentration, 2 nM) | **NOT ESTABLISHED** | Somoza 2015 (partial) |

**This table is materially weaker than the version in the prior draft of this document,
which incorrectly implied isoform-specific values could be read off the same source.**

---

## 5. Construct and WT/mutant scope

Unchanged from the prior draft: all retrievable Km-related evidence concerns wild-type
recombinant isoforms; no mutant-specific Km data was found in any source reviewed. This
finding is not affected by the corrections above.

---

## 6. What remains the Auditor's decision

- Obtain Somoza et al. 2015 JBC Table 2 (or an equivalent primary source) to establish
  actual per-isoform numeric values — **this evidence review cannot supply them.**
- Decide whether the umbralisib sponsor-document "100 µM" figure is worth pursuing
  further (e.g., via AACR 2011 abstract archives) or should be disregarded as
  unverifiable.
- Decide how to treat the Millipore kit's 10–20 µM figure — as a competing candidate
  value, as inadmissible (no traceable primary source), or as grounds to commission a
  fresh kinetic determination.
- Decide whether any Km policy can be sealed at all without a verified primary source,
  or whether `SCI0-008` should be blocked until one is obtained.

**Independent Auditor decision still required: YES.**

**UNRESOLVED — evidence insufficient to establish any single per-isoform Km(ATP) value
with confidence sufficient for sealing.** This is the honest conclusion of this evidence
review, stated plainly rather than papered over with an inferred table.
