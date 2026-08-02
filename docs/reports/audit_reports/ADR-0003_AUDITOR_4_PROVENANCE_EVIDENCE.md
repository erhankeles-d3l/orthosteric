# AUDITOR-4 Provenance Evidence: BindingDB/PubChem Admissibility

**Status:** Evidence prepared | CANDIDATE POLICY — requires Auditor approval

---

## 1. Provenance architecture of the three databases

### BindingDB
- Primary design: links measurements to publications; PMID/DOI available for the large majority of records
- Assay metadata: target name, organism, construct often recorded; [ATP] not systematically reported in the core record fields
- Source: mostly literature curation plus some direct depositions
- Without-publication records: exist; represent deposited screening data without an associated published paper

### PubChem BioAssay (PubChem BioAssay database)
- Primary design: structured deposition format; each assay (AID) has provenance including depositing organization
- Publication link: some AIDs are linked to a journal article (has_related_pubmed_id); many are not — particularly HTS depositions from industry
- Assay metadata: varies widely; [ATP] may or may not appear in assay description fields; construct/species often present
- Without-publication class: numerically large (many industry deposits); some have complete structured provenance, others minimal

### ChEMBL (methodological comparator)
- Primary design: manually curated from peer-reviewed publications; every record linked to a primary source
- Policy: ChEMBL excludes records that cannot be traced to a publication; this is its core quality guarantee
- Assay metadata: document assay type, target confidence score (1-9), assay format, organism systematically recorded
- ATP concentration: not systematically extracted; present as free text in assay description when reported

**EVIDENCE SYNTHESIS:** ChEMBL's strict publication-linking policy is the primary reason it is the standard training source for bioactivity prediction benchmarks. Its policy implicitly resolves AUDITOR-4 for a ChEMBL-only corpus — but ADR-0003 §2 explicitly accepts BindingDB and PubChem BioAssay as additional sources.

---

## 2. Proposed four-tier evidence classification

| Tier | Definition | Cheng-Prusoff viable? | Suggested treatment |
|---|---|---|---|
| T1 | Publication-linked + assay metadata sufficient to reconstruct [ATP] and construct | Yes | Primary training/evaluation evidence |
| T2 | Publication-linked + [ATP] not reported but assay format implies standard conditions | Partial — needs declared assumption | Primary evidence with assay-condition flag |
| T3 | Database-only (no primary publication) + complete structured metadata ([ATP], construct, organism traceable) | Yes, if metadata complete | Auxiliary evidence; training use conditional on cross-validation |
| T4 | Database-only + insufficient metadata (no [ATP], no construct) | No — cannot undergo normalization | Excluded from primary and auxiliary training |

**CANDIDATE POLICY — requires Auditor approval:**
> T1: primary evidence. T2: primary evidence with declared normalization assumption. T3: auxiliary evidence only; excluded from evaluation stratum. T4: excluded entirely.

---

## 3. Corpus size impact (qualitative only — no real corpus accessed)

**CANDIDATE RANGE — requires Auditor approval:**

If T4 records are excluded, the expected impact depends on what fraction of the BindingDB and PubChem data lacks both a publication and [ATP] metadata. Based on general knowledge of these databases:
- The ChEMBL-sourced fraction of BindingDB (the majority of its PI3K entries) would likely meet T1 or T2 criteria.
- Direct PubChem depositions without publication links (common in HTS datasets) would often fall to T3 or T4.
- Excluding T4 likely has a small effect on the PI3K-specific corpus because the most cited PI3K biochemical papers are heavily curated in ChEMBL/BindingDB; the "long tail" of unpublished screening data is less likely to be PI3K-specific.

This is an inference, not a calculation. The Auditor should request a quantitative Stage 0 Q8 audit that stratifies corpus records by this four-tier scheme.

---

## 4. Interaction with AUDITOR-5 (ATP Km)

**EVIDENCE SYNTHESIS:** T4 records (no [ATP]) cannot undergo Cheng–Prusoff normalization. If they are admitted to training, they contribute IC50 values that cannot be placed on a common Ki scale, making them systematically incomparable with normalized records. This is not merely a quality concern — it is a category error. T4 exclusion follows from the normalization requirement in ADR-0003 §4, not from a separate policy decision.

---

## 5. What remains the Auditor's decision

- Adopt or modify the four-tier classification;
- Set the threshold for cross-validation requirement for T3 records;
- Decide whether T3 records may enter training when no primary-publication records exist for a given compound (i.e., T3 as fallback vs. as excluded);
- Request the quantitative Stage 0 Q8 tier breakdown.

**Independent Auditor decision still required: YES.**
