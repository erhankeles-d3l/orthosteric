"""Tests for GDR-011 (accepted) Option D comparability-unit definitions.

Exit criteria:
  (1) panel_key/resolve_panel_key use (study_id, bao_format, assay_type)
      when available.
  (2) resolve_panel_key falls back to (study_id, assay_id) -- tagged
      LEGACY_FALLBACK -- when bao_format/assay_type are both absent.
  (3) Two records differing only in ChEMBL assay_id but sharing
      (study_id, bao_format, assay_type) are the SAME panel -- this is the
      entire point of Option D (assay_id alone was rejected).
  (4) LEGACY_FALLBACK panels are explicitly NOT scientific evidence
      (is_scientific_evidence is False) and must not silently look like
      C1_PRIMARY evidence.
  (5) atp_confirmed_panel_key returns None for AMBIGUOUS/UNKNOWN ATP status
      and for LEGACY_FALLBACK panels, and never fabricates a match between
      two such records.
"""

from __future__ import annotations

from orthosteric.data.comparability import (
    PanelKeyTier,
    atp_confirmed_panel_key,
    panel_key,
    resolve_panel_key,
)

# ── panel_key: primary comparability unit ────────────────────────────────────


def test_panel_key_uses_bao_and_assay_type_when_present() -> None:
    r = {"study_id": "S1", "assay_id": "A1", "bao_format": "BAO_0000357", "assay_type": "B"}
    study, protocol = panel_key(r)
    assert study == "S1"
    assert protocol == "BAO_0000357::B"


def test_panel_key_falls_back_to_assay_id_when_no_protocol_fields() -> None:
    """Backward compatibility: pre-GDR-011 generic algorithm test fixtures
    that only set study_id/assay_id must be unaffected."""
    r = {"study_id": "S1", "assay_id": "A1"}
    assert panel_key(r) == ("S1", "A1")


def test_two_different_assays_same_protocol_are_one_panel() -> None:
    """The entire point of Option D: two ChEMBL assays in the same
    document, sharing bao_format+assay_type, are one comparable panel even
    though (study_id, assay_id) [rejected] would have separated them."""
    r1 = {"study_id": "S1", "assay_id": "CHEMBL_ASSAY_A", "bao_format": "BAO_1", "assay_type": "B"}
    r2 = {"study_id": "S1", "assay_id": "CHEMBL_ASSAY_B", "bao_format": "BAO_1", "assay_type": "B"}
    assert panel_key(r1) == panel_key(r2)


def test_different_bao_format_different_panel() -> None:
    r1 = {"study_id": "S1", "assay_id": "A1", "bao_format": "BAO_1", "assay_type": "B"}
    r2 = {"study_id": "S1", "assay_id": "A2", "bao_format": "BAO_2", "assay_type": "B"}
    assert panel_key(r1) != panel_key(r2)


def test_different_assay_type_different_panel() -> None:
    r1 = {"study_id": "S1", "assay_id": "A1", "bao_format": "BAO_1", "assay_type": "B"}
    r2 = {"study_id": "S1", "assay_id": "A2", "bao_format": "BAO_1", "assay_type": "F"}
    assert panel_key(r1) != panel_key(r2)


def test_different_study_different_panel_even_with_same_protocol() -> None:
    r1 = {"study_id": "S1", "assay_id": "A1", "bao_format": "BAO_1", "assay_type": "B"}
    r2 = {"study_id": "S2", "assay_id": "A2", "bao_format": "BAO_1", "assay_type": "B"}
    assert panel_key(r1) != panel_key(r2)


def test_partial_protocol_field_still_uses_protocol_form() -> None:
    """Even if only one of bao_format/assay_type is present, use the
    protocol form (with an explicit UNKNOWN_* placeholder) rather than
    silently falling back to assay_id."""
    r = {"study_id": "S1", "assay_id": "A1", "bao_format": "BAO_1"}
    _study, protocol = panel_key(r)
    assert protocol == "BAO_1::UNKNOWN_TYPE"


# ── resolve_panel_key: tier machinery ────────────────────────────────────────


def test_resolve_panel_key_tags_c1_primary_when_protocol_present() -> None:
    r = {"study_id": "S1", "assay_id": "A1", "bao_format": "BAO_1", "assay_type": "B"}
    result = resolve_panel_key(r)
    assert result.tier is PanelKeyTier.C1_PRIMARY
    assert result.is_scientific_evidence is True


def test_resolve_panel_key_tags_legacy_fallback_when_no_protocol_fields() -> None:
    r = {"study_id": "S1", "assay_id": "A1"}
    result = resolve_panel_key(r)
    assert result.tier is PanelKeyTier.LEGACY_FALLBACK
    assert result.is_scientific_evidence is False


def test_resolve_panel_key_matches_panel_key_bare_value() -> None:
    """panel_key() must be exactly resolve_panel_key().key -- no drift
    between the tier-aware and tier-blind accessors."""
    r = {"study_id": "S1", "assay_id": "A1", "bao_format": "BAO_1", "assay_type": "B"}
    assert panel_key(r) == resolve_panel_key(r).key


def test_legacy_fallback_key_can_collide_with_a_c1_primary_key_by_coincidence() -> None:
    """Demonstrates why tier tracking is necessary: a LEGACY_FALLBACK key
    built from assay_id could coincidentally match a C1_PRIMARY protocol
    string.  Only the tier -- never the key alone -- tells a caller whether
    the match is scientific evidence."""
    legacy = {"study_id": "S1", "assay_id": "BAO_1::B"}  # no protocol fields
    primary = {"study_id": "S1", "assay_id": "X9", "bao_format": "BAO_1", "assay_type": "B"}
    assert panel_key(legacy) == panel_key(primary)  # same bare key
    assert resolve_panel_key(legacy).tier is PanelKeyTier.LEGACY_FALLBACK
    assert resolve_panel_key(primary).tier is PanelKeyTier.C1_PRIMARY
    assert resolve_panel_key(legacy).is_scientific_evidence is False
    assert resolve_panel_key(primary).is_scientific_evidence is True


# ── atp_confirmed_panel_key: secondary, flagged stratum ──────────────────────


def test_atp_confirmed_key_present_when_known_and_c1_primary() -> None:
    r = {
        "study_id": "S1",
        "bao_format": "BAO_1",
        "assay_type": "B",
        "atp_status": "known",
        "atp_concentration_um": 10.0,
    }
    key = atp_confirmed_panel_key(r)
    assert key == ("S1", "BAO_1::B", 10.0)


def test_atp_confirmed_key_none_when_unknown() -> None:
    r = {"study_id": "S1", "bao_format": "BAO_1", "assay_type": "B", "atp_status": "unknown"}
    assert atp_confirmed_panel_key(r) is None


def test_atp_confirmed_key_none_when_ambiguous() -> None:
    """GDR-011 (accepted): AMBIGUOUS must never be silently resolved into a
    confirmed stratum membership."""
    r = {
        "study_id": "S1",
        "bao_format": "BAO_1",
        "assay_type": "B",
        "atp_status": "ambiguous",
        "atp_concentration_um": None,
    }
    assert atp_confirmed_panel_key(r) is None


def test_atp_confirmed_key_none_when_panel_is_legacy_fallback() -> None:
    """Even a record with a KNOWN ATP value cannot enter the ATP-confirmed
    secondary stratum if its underlying panel is LEGACY_FALLBACK -- the
    secondary stratum is strictly narrower than C1_PRIMARY, never broader."""
    r = {
        "study_id": "S1",
        "assay_id": "A1",
        "atp_status": "known",
        "atp_concentration_um": 10.0,
    }
    assert resolve_panel_key(r).tier is PanelKeyTier.LEGACY_FALLBACK
    assert atp_confirmed_panel_key(r) is None


def test_two_unknown_atp_records_never_produce_matching_confirmed_keys() -> None:
    """The core GDR-011 guard: two records that are both ATP-UNKNOWN must
    never be treated as sharing an ATP-confirmed stratum."""
    r1 = {"study_id": "S1", "bao_format": "BAO_1", "assay_type": "B", "atp_status": "unknown"}
    r2 = {"study_id": "S1", "bao_format": "BAO_1", "assay_type": "B", "atp_status": "unknown"}
    assert atp_confirmed_panel_key(r1) is None
    assert atp_confirmed_panel_key(r2) is None
    # Both being None is not a match -- callers must not compare them as equal
    # keys; the API returning None (not a shared sentinel tuple) enforces this.


def test_atp_confirmed_key_none_when_status_known_but_no_value() -> None:
    r = {"study_id": "S1", "bao_format": "BAO_1", "assay_type": "B", "atp_status": "known"}
    assert atp_confirmed_panel_key(r) is None
