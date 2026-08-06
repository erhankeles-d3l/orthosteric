"""SCI1-017 through SCI1-022: splitting, stratum, baselines, gate."""

from __future__ import annotations

import pytest

from orthosteric.eval import (
    BASELINES_ALGORITHM_VERSION,
    GATE_ALGORITHM_VERSION,
    SPLITTING_ALGORITHM_VERSION,
    STRATUM_ALGORITHM_VERSION,
    ActivityRecord,
    BaselinePredictor,
    LigandOnlyBaseline,
    NearestNeighborBaseline,
    ProteochemometricBaseline,
    S1GateVote,
    SelectivityTarget,
    load_within_study_stratum,
    s1_gate_evaluation,
    scaffold_split,
)

# ── Shared test data ────────────────────────────────────────────────────────

_ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
_PHENOL = "Oc1ccccc1"
_ANILINE = "Nc1ccccc1"
_NAPHTHALENE = "c1ccc2ccccc2c1"
_ANTHRACENE = "c1ccc2cc3ccccc3cc2c1"

_CPS = [
    ("C1", _ASPIRIN),
    ("C2", _ASPIRIN),
    ("C3", _PHENOL),
    ("C4", _ANILINE),
    ("C5", _NAPHTHALENE),
    ("C6", _ANTHRACENE),
]


def _target(
    cid: str, b: float = 1.0, g: float = 1.0, d: float = 1.0, smiles: str | None = None
) -> SelectivityTarget:
    return SelectivityTarget(
        pac_alpha=8.0,
        lr_vs_beta=b,
        lr_vs_gamma=g,
        lr_vs_delta=d,
        ci_half=0.3,
        compound_id=cid,
        smiles=smiles,
        assay_atp_mm=1.0,
        within_study=True,
    )


def _arec(cid: str, iso: str, study: str = "S1", atp: float | None = 1.0) -> ActivityRecord:
    return ActivityRecord(
        compound_id=cid,
        isoform=iso,
        pac_value=8.0,
        is_censored=False,
        study_id=study,
        assay_atp_mm=atp,
        smiles=_ASPIRIN,
    )


# ── SCI1-017: Scaffold-aware splitting ──────────────────────────────────────


def test_scaffold_split_no_overlap() -> None:
    result = scaffold_split(_CPS, test_fraction=0.25, val_fraction=0.1)
    train_s = set(result.train_ids)
    val_s = set(result.val_ids)
    test_s = set(result.test_ids)
    assert len(train_s & test_s) == 0
    assert len(train_s & val_s) == 0
    assert len(val_s & test_s) == 0
    assert result.scaffold_overlap == 0


def test_scaffold_split_all_compounds_present() -> None:
    result = scaffold_split(_CPS)
    total = len(result.train_ids) + len(result.val_ids) + len(result.test_ids)
    assert total == len(_CPS)


def test_scaffold_split_is_frozen() -> None:
    result = scaffold_split(_CPS)
    with pytest.raises((AttributeError, TypeError)):
        result.train_ids = ()  # type: ignore[misc]


def test_scaffold_split_empty_input() -> None:
    result = scaffold_split([])
    assert result.train_ids == ()
    assert result.test_ids == ()


def test_scaffold_split_algorithm_version() -> None:
    assert SPLITTING_ALGORITHM_VERSION == "scaffold_split_v1_sci1017"


def test_scaffold_split_deterministic() -> None:
    r1 = scaffold_split(_CPS, random_seed=42)
    r2 = scaffold_split(_CPS, random_seed=42)
    assert r1.train_ids == r2.train_ids


def test_scaffold_split_different_seed_may_differ() -> None:
    r1 = scaffold_split(_CPS, random_seed=42)
    r2 = scaffold_split(_CPS, random_seed=99)
    # With >4 distinct scaffolds, different seeds should differ
    assert r1.content_sha256() != r2.content_sha256()


# ── SCI1-017b: Within-study stratum ─────────────────────────────────────────


def _four_isoform_records(
    cid: str, study: str = "S1", atp: float | None = 1.0
) -> list[ActivityRecord]:
    return [
        _arec(cid, iso, study, atp) for iso in ["PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"]
    ]


def test_stratum_within_study_qualification() -> None:
    records = _four_isoform_records("C1") + _four_isoform_records("C2")
    r = load_within_study_stratum(records)
    assert "C1" in r.within_study_ids
    assert "C2" in r.within_study_ids


def test_stratum_cross_study_excluded_from_within() -> None:
    recs = [
        _arec("C3", "PI3Kalpha", "S1"),
        _arec("C3", "PI3Kbeta", "S2"),
        _arec("C3", "PI3Kgamma", "S1"),
        _arec("C3", "PI3Kdelta", "S1"),
    ]
    r = load_within_study_stratum(recs)
    assert "C3" in r.cross_study_ids
    assert "C3" not in r.within_study_ids


def test_stratum_excluded_when_atp_missing() -> None:
    recs = _four_isoform_records("C4", atp=None)
    r = load_within_study_stratum(recs)
    assert "C4" in r.excluded_ids
    assert "C4" not in r.within_study_ids


def test_stratum_missing_isoform_goes_to_cross() -> None:
    recs = [_arec("C5", "PI3Kalpha"), _arec("C5", "PI3Kbeta"), _arec("C5", "PI3Kgamma")]
    r = load_within_study_stratum(recs)
    assert "C5" in r.cross_study_ids


def test_stratum_algorithm_version() -> None:
    assert STRATUM_ALGORITHM_VERSION == "stratum_v1_sci1017b"


def test_stratum_result_is_frozen() -> None:
    r = load_within_study_stratum([])
    with pytest.raises((AttributeError, TypeError)):
        r.within_study_ids = ()  # type: ignore[misc]


# ── SCI1-018/019/020: Baselines ──────────────────────────────────────────────


def test_ligand_only_baseline_predicts_mean() -> None:
    b = LigandOnlyBaseline()
    targets = [_target("C1", b=1.0), _target("C2", b=3.0), _target("C3", b=5.0)]
    b.fit(targets)
    pred = b.predict_lr_vs_beta("anything")
    assert pred == pytest.approx(3.0)


def test_ligand_only_ignores_smiles() -> None:
    b = LigandOnlyBaseline()
    b.fit([_target("C1", b=2.0)])
    assert b.predict_lr_vs_beta(_ASPIRIN) == b.predict_lr_vs_beta(_ANILINE)


def test_ligand_only_zero_before_fit() -> None:
    b = LigandOnlyBaseline()
    assert b.predict_lr_vs_beta(_ASPIRIN) == pytest.approx(0.0)


def test_nn_baseline_returns_finite_value() -> None:
    b = NearestNeighborBaseline()
    st = _target("C1", b=2.5, smiles=_ASPIRIN)
    b.fit([st])
    val = b.predict_lr_vs_beta(_PHENOL)
    assert isinstance(val, float)


def test_pcm_baseline_fits_and_predicts() -> None:
    b = ProteochemometricBaseline()
    targets = [
        SelectivityTarget(
            pac_alpha=8.0,
            lr_vs_beta=float(i),
            lr_vs_gamma=float(i),
            lr_vs_delta=float(i),
            ci_half=None,
            compound_id=f"C{i}",
            smiles=smi,
            assay_atp_mm=1.0,
            within_study=True,
        )
        for i, smi in enumerate([_ASPIRIN, _PHENOL, _NAPHTHALENE])
    ]
    b.fit(targets)
    pred = b.predict_lr_vs_beta(_ANILINE)
    assert isinstance(pred, float)


def test_baselines_algorithm_version() -> None:
    assert BASELINES_ALGORITHM_VERSION == "baselines_v1_sci1018_019_020"


def test_baseline_predictor_protocol() -> None:
    b = LigandOnlyBaseline()
    assert isinstance(b, BaselinePredictor)


# ── SCI1-021 / SCI1-022: Gate evaluation ─────────────────────────────────────


def test_gate_go_when_baseline_rmse_above_threshold() -> None:
    r = s1_gate_evaluation(
        baseline_1_rmse={"alpha_vs_beta": 1.5, "alpha_vs_gamma": 1.2},
        baseline_2_rmse={"alpha_vs_beta": 1.1},
        baseline_3_rmse=None,
        n_within_study=100,
    )
    assert r.vote == S1GateVote.GO
    assert r.any_baseline_meets_s2 is False


def test_gate_stop_when_ligand_only_too_good() -> None:
    r = s1_gate_evaluation(
        baseline_1_rmse={"alpha_vs_beta": 0.1},  # <= 0.3 threshold
        baseline_2_rmse=None,
        baseline_3_rmse=None,
        n_within_study=100,
    )
    assert r.vote == S1GateVote.STOP
    assert r.any_baseline_meets_s2 is True


def test_gate_insufficient_data_below_minimum() -> None:
    r = s1_gate_evaluation(
        baseline_1_rmse={"alpha_vs_beta": 2.0},
        baseline_2_rmse=None,
        baseline_3_rmse=None,
        n_within_study=10,  # below default minimum of 50
    )
    assert r.vote == S1GateVote.INSUFFICIENT_DATA


def test_gate_record_is_frozen() -> None:
    r = s1_gate_evaluation({"alpha_vs_beta": 1.0}, None, None, 100)
    with pytest.raises((AttributeError, TypeError)):
        r.vote = S1GateVote.STOP  # type: ignore[misc]


def test_gate_rationale_non_empty() -> None:
    r = s1_gate_evaluation({"alpha_vs_beta": 1.0}, None, None, 100)
    assert len(r.rationale) > 20


def test_gate_algorithm_version() -> None:
    assert GATE_ALGORITHM_VERSION == "gate_v1_sci1022"
