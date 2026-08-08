"""Authoritative target-to-tier mapping for PI3K superfamily targets.

Objective: SCI0-006.
Constitution §0.1 / §0.4.
Authority: ADR-0003 §2; ADR-0011 (ChEMBL 37 target-ID correction).

This module is the single source of truth for tier assignment at ingestion.
Every connector calls ``admissibility_for_target()`` before emitting a record.

Tier 1 — Class I PI3K isoforms (primary learning scope)
Tier 2 — External validation panel (read-only; information barrier)
Tier 3 / everything else — out of scope; records are INADMISSIBLE

Source identifiers covered
--------------------------
ChEMBL   — IDs verified against ChEMBL 37 by UniProt-accession lookup (ADR-0011).
            Previous ChEMBL 34 IDs were WRONG in ChEMBL 37 and have been removed.
            PIK3CA (p110α) = CHEMBL4005 — confirmed ChEMBL 37: UniProt P42336 lookup.
            PIK3CD (p110δ) = CHEMBL3130 — confirmed ChEMBL 37: UniProt O00329 lookup.
            Verification date: 2026-08-06. See ADR-0011.
Gene     — canonical gene symbol; used for BindingDB and PubChem matching.
UniProt  — used where source returns UniProt ACs.  Version-independent.

Any target not in this map is INADMISSIBLE.  The map may only be extended
through a governance amendment (Constitution §0.1 / ADR-0003 §2).
"""

from __future__ import annotations

from orthosteric.data.sources._base import Admissibility

# ── Tier 1: Class I PI3K ─────────────────────────────────────────────────────

_TIER1_CHEMBL: frozenset[str] = frozenset(
    {
        "CHEMBL4005",  # PIK3CA (p110α) — confirmed ChEMBL 37: UniProt P42336 lookup (2026-08-06)
        "CHEMBL3145",  # PIK3CB (p110β)  — confirmed ChEMBL 37: UniProt P42338 lookup (ADR-0011)
        "CHEMBL3267",  # PIK3CG (p110γ)  — confirmed ChEMBL 37: UniProt P48736 lookup (ADR-0011)
        "CHEMBL3130",  # PIK3CD (p110δ) — confirmed ChEMBL 37: UniProt O00329 lookup (2026-08-06)
    }
)

_TIER1_GENE: frozenset[str] = frozenset(
    {
        "PIK3CA",
        "PIK3CB",
        "PIK3CG",
        "PIK3CD",
        # alternate names that appear in BindingDB / PubChem
        "p110alpha",
        "p110beta",
        "p110gamma",
        "p110delta",
        "PI3K alpha",
        "PI3K beta",
        "PI3K gamma",
        "PI3K delta",
        "PI3-kinase p110-alpha",
        "PI3-kinase p110-beta",
        "PI3-kinase p110-gamma",
        "PI3-kinase p110-delta",
        "Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit alpha",
        "Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit beta",
        "Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit gamma",
        "Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit delta",
    }
)

_TIER1_UNIPROT: frozenset[str] = frozenset(
    {
        "P42336",  # PIK3CA human
        "P42338",  # PIK3CB human
        "P48736",  # PIK3CG human
        "O00329",  # PIK3CD human
    }
)

# ── Tier 2: External validation panel ────────────────────────────────────────

_TIER2_CHEMBL: frozenset[str] = frozenset(
    {
        "CHEMBL2842",  # MTOR  (mTOR)
        "CHEMBL3194",  # PIK3C3 / VPS34
        "CHEMBL4680",  # PRKDC  (DNA-PK)
        "CHEMBL2695",  # PIK3C2A (Class II)
        "CHEMBL2898",  # PIK3C2B (Class II)
        "CHEMBL3717",  # PIK3C2G (Class II)
    }
)

_TIER2_GENE: frozenset[str] = frozenset(
    {
        "MTOR",
        "mTOR",
        "FRAP1",
        "PIK3C3",
        "VPS34",
        "Vps34",
        "PRKDC",
        "DNA-PK",
        "DNA-PKcs",
        "PIK3C2A",
        "PIK3C2B",
        "PIK3C2G",
        "PI3K-C2α",
        "PI3K-C2β",
        "PI3K-C2γ",
    }
)

_TIER2_UNIPROT: frozenset[str] = frozenset(
    {
        "P42345",  # MTOR human
        "O00750",  # PIK3C3 / VPS34 human
        "P78527",  # PRKDC human
        "O00443",  # PIK3C2A human
        "O15155",  # PIK3C2B human
        "O75747",  # PIK3C2G human
    }
)


def admissibility_for_chembl_target(chembl_target_id: str) -> Admissibility:
    """Return admissibility for a ChEMBL target ID."""
    cid = chembl_target_id.upper().strip()
    if cid in _TIER1_CHEMBL:
        return Admissibility.TIER1_PRIMARY
    if cid in _TIER2_CHEMBL:
        return Admissibility.TIER2_GATED
    return Admissibility.INADMISSIBLE


def admissibility_for_gene(gene_name: str) -> Admissibility:
    """Return admissibility for a gene symbol or target name.

    Case-insensitive lookup across canonical names and common aliases.
    """
    name = gene_name.strip()
    # Exact match first
    if name in _TIER1_GENE:
        return Admissibility.TIER1_PRIMARY
    if name in _TIER2_GENE:
        return Admissibility.TIER2_GATED
    # Case-insensitive fallback
    name_up = name.upper()
    if any(n.upper() == name_up for n in _TIER1_GENE):
        return Admissibility.TIER1_PRIMARY
    if any(n.upper() == name_up for n in _TIER2_GENE):
        return Admissibility.TIER2_GATED
    return Admissibility.INADMISSIBLE


def admissibility_for_uniprot(uniprot_ac: str) -> Admissibility:
    """Return admissibility for a UniProt accession."""
    ac = uniprot_ac.strip().upper()
    if ac in {u.upper() for u in _TIER1_UNIPROT}:
        return Admissibility.TIER1_PRIMARY
    if ac in {u.upper() for u in _TIER2_UNIPROT}:
        return Admissibility.TIER2_GATED
    return Admissibility.INADMISSIBLE
