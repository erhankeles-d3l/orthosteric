"""GDR-011 (accepted) within-study comparability-unit definition.

Governs how a "panel" / "within-study stratum" is defined, shared by
graph.py (SCI0-014) and strata.py (SCI0-013) so the two modules cannot
silently drift apart on what a comparable panel is.

Primary comparability unit (GDR-011 Option D, accepted)
-----------------------------------------------------------
    panel = (study_id, protocol)
    protocol = f"{bao_format}::{assay_type}"    when either field is present

This REPLACES the previous `(study_id, assay_id)` definition.  GDR-011
found that definition structurally incapable of ever producing a
four-isoform panel on ChEMBL data: every ChEMBL assay is defined per
(document x target x protocol), so an assay covers exactly one isoform,
always (empirically verified: 2,308 of 2,308 assays in Activity Snapshot
A3 cover exactly one isoform).  No amount of additional ChEMBL data can
change this; the previous definition was rejected, not merely under-powered.

Tiers -- LEGACY_FALLBACK is NOT scientific evidence
-------------------------------------------------------
Every panel key carries an explicit tier:

  C1_PRIMARY      -- bao_format and/or assay_type present; the GDR-011
                    Option D comparability unit.  Usable as scientific
                    evidence for GGR-002a, GGR-002b, and SCI-2 eligibility.
  LEGACY_FALLBACK -- neither field present; the key degrades to the
                    rejected `(study_id, assay_id)` form.  This exists ONLY
                    to preserve pre-existing generic-algorithm test
                    fixtures (union-find, cluster-structure mechanics) that
                    predate GDR-011 and never populated the new fields.
                    LEGACY_FALLBACK panels MUST NOT be counted as
                    C1-comparable evidence anywhere a scientific conclusion
                    is drawn.  On real ChEMBL data this tier is not
                    expected to fire: bao_format and assay_type are 100%
                    populated in Activity Snapshot A3 (GDR-011 evidence).

`panel_key()` returns the bare key for callers that only need grouping
mechanics (the generic union-find/stratum algorithms in graph.py/
strata.py).  `resolve_panel_key()` returns the key AND its tier, and is
the function any GGR-002a/GGR-002b/SCI-2-eligibility analysis MUST use --
never `panel_key()` alone -- so LEGACY_FALLBACK panels can be filtered out
before a scientific conclusion is drawn.

Secondary, ATP-confirmed stratum (flagged, per GDR-011 "hierarchical")
--------------------------------------------------------------------------
GDR-011 explicitly rejected making ATP concentration part of the PRIMARY
key (Issue 2: ATP is a non-mandatory covariate/stratifier).  A secondary,
narrower key is provided for records whose ATP status is KNOWN, for use as
a flagged/secondary stratum -- never as a replacement for the primary key.

`atp_confirmed_panel_key()` returns None for AMBIGUOUS or UNKNOWN ATP
status, and for any LEGACY_FALLBACK panel.  Returning a placeholder for
"unknown" would risk exactly the error GDR-011 forbids: treating two
UNKNOWN ATP conditions as matching.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class PanelKeyTier(StrEnum):
    """Whether a panel key is GDR-011 Option D scientific evidence."""

    C1_PRIMARY = "c1_primary"
    LEGACY_FALLBACK = "legacy_fallback"


@dataclass(frozen=True)
class PanelKeyResult:
    """A panel key together with its evidentiary tier."""

    key: tuple[str, str]
    tier: PanelKeyTier

    @property
    def is_scientific_evidence(self) -> bool:
        """True iff this key is GDR-011 Option D primary comparability
        evidence, usable in GGR-002a, GGR-002b, or SCI-2 eligibility.
        """
        return self.tier is PanelKeyTier.C1_PRIMARY


def resolve_panel_key(record: dict[str, Any]) -> PanelKeyResult:
    """Primary within-study comparability unit, WITH its evidentiary tier.

    Any code drawing a scientific conclusion (GGR-002a, GGR-002b, SCI-2
    eligibility) MUST call this -- not `panel_key()` -- and must filter to
    `result.is_scientific_evidence` before counting a panel as comparable.
    """
    study = str(record.get("study_id", record.get("assay_id", "UNKNOWN_STUDY")))
    bao = record.get("bao_format")
    atype = record.get("assay_type")
    if bao is not None or atype is not None:
        protocol = f"{bao or 'UNKNOWN_BAO'}::{atype or 'UNKNOWN_TYPE'}"
        return PanelKeyResult(key=(study, protocol), tier=PanelKeyTier.C1_PRIMARY)
    protocol = str(record.get("assay_id", "UNKNOWN_ASSAY"))
    return PanelKeyResult(key=(study, protocol), tier=PanelKeyTier.LEGACY_FALLBACK)


def panel_key(record: dict[str, Any]) -> tuple[str, str]:
    """Bare grouping key, for algorithm mechanics only (graph.py, strata.py
    union-find / stratum construction).  Does not expose the tier --
    callers needing to know whether a key is scientific evidence must use
    `resolve_panel_key()` instead.
    """
    return resolve_panel_key(record).key


def atp_confirmed_panel_key(record: dict[str, Any]) -> tuple[str, str, float] | None:
    """Secondary, flagged stratum key: primary panel + a KNOWN ATP concentration.

    Returns None whenever:
      - the panel itself is LEGACY_FALLBACK (not C1-comparable evidence);
      - `atp_status` is not `"known"` (covers AMBIGUOUS and UNKNOWN --
        GDR-011 forbids resolving AMBIGUOUS via a first-match rule);
      - the concentration value is missing.

    Callers must never substitute a placeholder for a missing value here.
    """
    resolved = resolve_panel_key(record)
    if not resolved.is_scientific_evidence:
        return None
    if record.get("atp_status") != "known":
        return None
    conc = record.get("atp_concentration_um")
    if conc is None:
        return None
    study, protocol = resolved.key
    return (study, protocol, float(conc))
