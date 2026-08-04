"""Authoritative PI3K isoform-to-UniProt mapping.

Objective: SCI0-007.
Constitution §2.1: human Tier 1 targets only.

This is the single source of truth for isoform identity in the structural
layer.  Every structural record is anchored to one of these four isoforms.
"""

from __future__ import annotations

from enum import StrEnum


class PI3KIsoform(StrEnum):
    """Human Class I PI3K isoforms (Tier 1 scope, Constitution §0.1)."""

    ALPHA = "PI3Kalpha"  # PIK3CA
    BETA = "PI3Kbeta"  # PIK3CB
    GAMMA = "PI3Kgamma"  # PIK3CG
    DELTA = "PI3Kdelta"  # PIK3CD


#: Canonical human UniProt accessions for each Tier 1 isoform.
PI3K_UNIPROT_MAP: dict[PI3KIsoform, str] = {
    PI3KIsoform.ALPHA: "P42336",  # PIK3CA_HUMAN
    PI3KIsoform.BETA: "P42338",  # PIK3CB_HUMAN
    PI3KIsoform.GAMMA: "P48736",  # PIK3CG_HUMAN
    PI3KIsoform.DELTA: "O00329",  # PIK3CD_HUMAN
}

#: Gene symbols for each isoform.
PI3K_GENE_MAP: dict[PI3KIsoform, str] = {
    PI3KIsoform.ALPHA: "PIK3CA",
    PI3KIsoform.BETA: "PIK3CB",
    PI3KIsoform.GAMMA: "PIK3CG",
    PI3KIsoform.DELTA: "PIK3CD",
}


def isoform_from_uniprot(uniprot_ac: str) -> PI3KIsoform | None:
    """Return the isoform for a UniProt accession, or None if not a Tier 1 target."""
    ac = uniprot_ac.strip().upper()
    for iso, uid in PI3K_UNIPROT_MAP.items():
        if uid.upper() == ac:
            return iso
    return None
