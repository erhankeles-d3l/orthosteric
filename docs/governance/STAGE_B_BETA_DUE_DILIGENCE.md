# Stage B, Part 1 — β Receptor Due Diligence (SS3)

## Search methodology

Four independent, differently-worded searches were run, not one:
1. General: `PIK3CB / p110beta human crystal structure PDB ATP site inhibitor`
2. Human-specific: `"Homo sapiens" PIK3CB p110beta crystal structure PDB human ATP binding site`
3. Recency-focused: `human PI3K beta p110beta crystal structure 2023 2024 2025 new PDB`
4. Cryo-EM-specific: `PIK3CB cryo-EM structure p110beta p85 complex`

## Candidates found and disqualified

| PDB ID | Description | Organism | Disposition |
|---|---|---|---|
| 2Y3A | p110β/p85β icSH2 complex + GDC-0941 | ***Mus musculus*** | Disqualified -- not human |
| 4BFR | p110β + pyrimidone indoline amide, ATP-site bound, 2.80 Å | ***Mus musculus*** | Disqualified -- not human (confirmed directly on the RCSB structure page: "Organism(s): Mus musculus") |

No other PIK3CB/p110β entries surfaced across any of the four searches. All other results returned were PIK3CA (alpha) or PIK3CG (gamma) structures, confirming the searches were reaching the right structural-biology literature and not simply missing relevant terms.

## Finding

**No adequate human PIK3CB experimental ATP-site structure was located.** This is consistent with the documented structural-biology history of this isoform: human p110β has long resisted crystallization in a form suitable for ATP-site ligand-bound structures, while the mouse ortholog (2Y3A, 4BFR, and related Sanofi/Williams-lab structures) has been tractable — which is presumably why this project used an AlphaFold model (AF-P42338) for beta in the first place, rather than an experimental structure, unlike the other three isoforms.

Per SS3's own due-diligence standard (REMARK 465/480 completeness check, not resolution alone), this question is moot here: there is no human candidate structure to run that check against at all, mouse structures being disqualified on species grounds before completeness is even assessed.

## Consequence (SS3.1, binding)

> **The four-isoform confirmatory endpoint is INVALIDATED.**

Per the mandate's own explicit rule, this is not silently converted into a three-isoform confirmatory study. The reason is a label/signal mismatch: the frozen endpoint's "other-selective" class is defined by four-isoform experimental labels, and a compound labelled other-selective *because it is β-selective* has no structural basis for that label without a β receptor.

**SS1's power check must NOT be run against the four-isoform endpoint.** Per SS3.1's explicit binding dependency, this was checked *before* attempting SS1, which is why SS1 has not been executed this session.

## What remains available

Per SS3.1's permitted response: *"Any three-isoform (α vs γ/δ) analysis is exploratory only, requires its own separately pre-registered endpoint and its own power check, and cannot inherit the confirmatory status of the frozen endpoint."*

This is a substantial design task — a new endpoint definition, a new power simulation, and explicit re-registration — not something to improvise as a side effect of this finding. It is noted here as the available path forward, not executed.

## What is unaffected by this finding

The remainder of Stage B (the 6XRL production-path bridge and smoke test, SS0.6.4) does not depend on beta and proceeds regardless of which endpoint (four-isoform or a future three-isoform design) is ultimately pursued — gamma-via-6XRL is needed either way.

## Governance cross-reference — a real tension, flagged not silently resolved

Re-running this search surfaced that an **earlier** project governance decision already formally adjudicated the beta receptor question, via a different mechanism than Rev. 5's own §3:

> Per `analysis/run_docking_pilot_four_isoform.py`'s docstring: *"No human PIK3CB (P42338) PDB structure exists (verified, unchanged from prior sessions). Per SCI0-007's AlphaFold admissibility rules (mean pLDDT >= 70; source confirmed by UniProt accession match; only when no admissible PDB exists) and GDR-006 (AlphaFold features included with an explicit is_alphafold indicator), fetched the real AlphaFold model for P42338 (AF-P42338-F1-model_v6, global mean pLDDT = 86.38 -- admissible)."*

This means the "no human PIK3CB structure exists" finding is not new — it was already established and **formally resolved** by an accepted governance procedure (SCI0-007 / GDR-006), which treats AlphaFold as an *admissible* receptor tier (tier D2, disclosed) rather than a disqualifying failure.

**Rev. 5's own §3/§3.1 text sets a stricter, different standard for this specific study**: *"If β cannot be given an adequate receptor (no passing experimental structure...) → The four-isoform confirmatory endpoint is INVALIDATED."* Read literally, Rev. 5 treats the absence of an experimental structure itself as sufficient grounds for invalidation — a higher bar than GDR-006's general admissibility rule, for a specific, stated reason: this study's position-filtered S/H features (§9) need precise pocket geometry at specific anchor residues, which an AlphaFold model has not been experimentally validated to provide at that level of precision, even though GDR-006 judged it adequate for coarser prior comparative work.

**This is a real tension between two governance layers, not a contradiction to paper over.** Rev. 5 is the most recent, most specific, explicitly frozen document governing this particular study, and its text on this point is unambiguous even where it diverges from the earlier, more general decision. Per that specificity and recency, **Rev. 5's own rule is applied** (four-isoform endpoint invalidated, as recorded above) — but this cross-reference is recorded so the divergence from GDR-006 is visible and correctable by the project owner, not quietly resolved in either direction without comment.
