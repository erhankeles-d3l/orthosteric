"""ATP-concentration status extraction from free-text assay descriptions.

Objective: GDR-011 (accepted), Issue 2.
Governance: GDR-011 approves ATP concentration as a non-mandatory
covariate/stratifier, never as part of the primary comparability key
(see `_comparability.py`).  This module implements only the EXTRACTION of
an ATP status per record; it does not decide comparability policy.

ChEMBL exposes no structured ATP-concentration field (verified empirically,
GDR-011 evidence: 0 of 39,508 raw records carry one in `activity_properties`).
The only source is free text in `assay_description`.

Status semantics (binding, per GDR-011 acceptance)
----------------------------------------------------
KNOWN:
    Exactly one distinct numeric ATP concentration is extractable from the
    description.  `concentration_um` is populated.
AMBIGUOUS:
    Two or more DISTINCT numeric values are associated with "ATP" in the
    description (e.g. "20 uM PIP2, 20 uM ATP ... 400 uM" — a real corpus
    example).  GDR-011 explicitly forbids resolving this with a first-match
    rule.  `concentration_um` is None; `candidate_values_um` retains every
    candidate for future adjudication.
UNKNOWN:
    No numeric ATP concentration is extractable — including descriptions
    that mention ATP with no stated concentration (frequently a
    radiolabelled substrate reference, e.g. "[gamma-33P]ATP", not a
    condition) and descriptions that reference ATP Km without a number.
    `concentration_um` is None.

UNKNOWN != ABSENT and two UNKNOWN records must never be treated as matching
on ATP (GDR-011 acceptance, explicit instruction).  This module never
returns two UNKNOWN results as "equal" for comparability purposes — that
determination is the caller's, and the caller must not make it either.

This extraction is PROVISIONAL.  Per GDR-011 acceptance: "Regex-derived ATP
concentrations remain provisional until the multi-value extraction
ambiguity has been governed."  AMBIGUOUS records are surfaced, not resolved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

#: GDR-011 (accepted) extraction rule version.  Bump on any pattern change.
ATP_EXTRACTION_RULE_VERSION = "gdr011_atp_extract_v1"


class AtpStatus(StrEnum):
    """ATP-concentration extraction outcome for one assay description."""

    KNOWN = "known"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


# ── Patterns (PROTOTYPE-derived; see analysis/gdr011_atp_validation.py) ───────

_P_UM = re.compile(r"(\d+(?:\.\d+)?)\s*(?:u|\u03bc|\u03b7)M\s+ATP", re.IGNORECASE)
_P_MM = re.compile(r"(\d+(?:\.\d+)?)\s*mM\s+ATP", re.IGNORECASE)
_P_NM = re.compile(r"(\d+(?:\.\d+)?)\s*nM\s+ATP", re.IGNORECASE)
_P_ATP_N = re.compile(
    r"ATP\s+(?:at\s+|conc[a-z]*\s+(?:of\s+)?)?(\d+(?:\.\d+)?)\s*(u|\u03bc|m|n)M",
    re.IGNORECASE,
)
_P_KM = re.compile(r"ATP\s*Km|Km\s*(?:for|of)\s*ATP|at\s+Km", re.IGNORECASE)
_MENTION = re.compile(r"\bATP\b", re.IGNORECASE)

_UNIT_TO_UM: dict[str, float] = {"n": 1e-3, "u": 1.0, "\u03bc": 1.0, "m": 1e3}


@dataclass(frozen=True)
class AtpExtractionResult:
    """Result of ATP-status extraction for one assay description.

    Attributes:
    ----------
    status:              KNOWN / AMBIGUOUS / UNKNOWN.
    concentration_um:     Populated iff status == KNOWN.  Never populated
                          for AMBIGUOUS (GDR-011: no first-match rule).
    candidate_values_um: All distinct numeric candidates found, in µM.
                          Length 0 (UNKNOWN with no number), 1 (KNOWN), or
                          ≥2 (AMBIGUOUS).  Retained for future adjudication.
    text_span:           The matched substring, for audit (first match only;
                          for AMBIGUOUS this is diagnostic, not authoritative).
    mentions_atp:         True if "ATP" appears anywhere in the description,
                          regardless of whether a concentration was found.
    rule_version:        ATP_EXTRACTION_RULE_VERSION at extraction time.
    """

    status: AtpStatus
    concentration_um: float | None
    candidate_values_um: tuple[float, ...] = field(default_factory=tuple)
    text_span: str | None = None
    mentions_atp: bool = False
    rule_version: str = ATP_EXTRACTION_RULE_VERSION


def _all_candidates_um(description: str) -> list[float]:
    """Every distinct numeric ATP-associated concentration in the text."""
    vals: list[float] = []
    for m in _P_UM.finditer(description):
        vals.append(float(m.group(1)) * _UNIT_TO_UM["u"])
    for m in _P_MM.finditer(description):
        vals.append(float(m.group(1)) * _UNIT_TO_UM["m"])
    for m in _P_NM.finditer(description):
        vals.append(float(m.group(1)) * _UNIT_TO_UM["n"])
    for m in _P_ATP_N.finditer(description):
        unit = m.group(2).lower()
        vals.append(float(m.group(1)) * _UNIT_TO_UM.get(unit, 1.0))
    # Deduplicate while preserving encounter order (dict trick, py3.7+).
    seen: dict[float, None] = {}
    for v in vals:
        seen.setdefault(v, None)
    return list(seen)


def extract_atp_status(description: str | None) -> AtpExtractionResult:
    """Extract an ATP-concentration status from a free-text assay description.

    Never resolves ambiguity by taking the first match — GDR-011 (accepted)
    forbids that.  A description with ≥2 distinct numeric ATP-associated
    values is AMBIGUOUS, full stop, regardless of match order.
    """
    if not description:
        return AtpExtractionResult(status=AtpStatus.UNKNOWN, concentration_um=None)

    mentions = bool(_MENTION.search(description))
    if not mentions:
        return AtpExtractionResult(status=AtpStatus.UNKNOWN, concentration_um=None)

    candidates = _all_candidates_um(description)

    if len(candidates) >= 2:
        return AtpExtractionResult(
            status=AtpStatus.AMBIGUOUS,
            concentration_um=None,
            candidate_values_um=tuple(candidates),
            text_span=_first_span(description),
            mentions_atp=True,
        )
    if len(candidates) == 1:
        return AtpExtractionResult(
            status=AtpStatus.KNOWN,
            concentration_um=candidates[0],
            candidate_values_um=tuple(candidates),
            text_span=_first_span(description),
            mentions_atp=True,
        )
    # Mentions ATP, no numeric concentration (radiolabel reference, Km
    # reference, or unparseable) — UNKNOWN, not a failure.
    km_match = _P_KM.search(description)
    return AtpExtractionResult(
        status=AtpStatus.UNKNOWN,
        concentration_um=None,
        text_span=km_match.group(0) if km_match else None,
        mentions_atp=True,
    )


def _first_span(description: str) -> str | None:
    for pat in (_P_UM, _P_MM, _P_NM, _P_ATP_N):
        m = pat.search(description)
        if m:
            return m.group(0)
    return None
