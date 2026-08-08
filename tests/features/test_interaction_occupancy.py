"""Tests for occupancy/recurrence aggregation
(features._interaction_occupancy) and multi-pose PDBQT parsing
(features._docking_interaction_detector.parse_pdbqt_multi_pose).

Exit criteria:
  (1) Occupancy = n_poses_with_interaction / n_poses_evaluated, exact.
  (2) Classification thresholds are deterministic and match the
      documented cutoffs (0.4 recurrent, 0.8 high-occupancy).
  (3) A single-pose evaluation is always OBSERVED_SINGLE_POSE regardless
      of its raw fraction (never miscategorized as HIGH_OCCUPANCY at n=1).
  (4) An interaction present in zero poses never appears in the output
      (no fabricated zero-occupancy record).
  (5) Distances are preserved per-pose (not just aggregated away).
  (6) Multi-pose PDBQT parsing correctly separates MODEL blocks; a
      single-model (or model-less) file returns exactly one pose.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orthosteric.features._docking_interaction_detector import (
    InteractionType,
    parse_pdbqt_multi_pose,
)
from orthosteric.features._interaction_occupancy import (
    OccupancyClass,
    aggregate_occupancy,
    classify_occupancy,
)


class _FakeInteraction:
    def __init__(
        self,
        itype: Any,
        resnum: int,
        chain: str,
        atom_name: str,
        resname: str = "GLU",
        distance: float = 3.0,
    ) -> None:
        self.interaction_type = itype
        self.residue_number = resnum
        self.chain_id = chain
        self.ligand_atom_name = atom_name
        self.residue_name = resname
        self.distance_angstrom = distance


def test_classify_occupancy_thresholds() -> None:
    assert classify_occupancy(0.2, n_poses=5) == OccupancyClass.OBSERVED_SINGLE_POSE
    assert classify_occupancy(0.4, n_poses=5) == OccupancyClass.RECURRENT
    assert classify_occupancy(0.6, n_poses=5) == OccupancyClass.RECURRENT
    assert classify_occupancy(0.8, n_poses=5) == OccupancyClass.HIGH_OCCUPANCY
    assert classify_occupancy(1.0, n_poses=5) == OccupancyClass.HIGH_OCCUPANCY


def test_single_pose_never_high_occupancy_even_at_fraction_1() -> None:
    """A single-pose evaluation reporting occupancy=1.0 must still be
    OBSERVED_SINGLE_POSE, not HIGH_OCCUPANCY -- n=1 carries no recurrence
    evidence regardless of the raw fraction."""
    assert classify_occupancy(1.0, n_poses=1) == OccupancyClass.OBSERVED_SINGLE_POSE


def test_aggregate_occupancy_exact_fraction() -> None:
    it = InteractionType.H_BOND
    poses = [
        [_FakeInteraction(it, 852, "A", "O1", distance=2.8)],
        [_FakeInteraction(it, 852, "A", "O1", distance=2.9)],
        [],  # absent in this pose
        [_FakeInteraction(it, 852, "A", "O1", distance=2.7)],
        [],  # absent in this pose
    ]
    results = aggregate_occupancy(poses)
    assert len(results) == 1
    r = results[0]
    assert r.n_poses_evaluated == 5
    assert r.n_poses_with_interaction == 3
    assert r.occupancy == 3 / 5
    assert r.occupancy_class == OccupancyClass.RECURRENT


def test_zero_occupancy_interaction_never_fabricated() -> None:
    """An interaction that never occurs in any pose must not appear as a
    zero-occupancy record -- there is nothing to report."""
    poses: list[list[Any]] = [[], [], []]
    results = aggregate_occupancy(poses)
    assert results == []


def test_distances_preserved_per_pose_not_just_averaged() -> None:
    it = InteractionType.HYDROPHOBIC_CONTACT
    poses = [
        [_FakeInteraction(it, 100, "A", "C1", distance=4.0)],
        [_FakeInteraction(it, 100, "A", "C1", distance=4.4)],
    ]
    results = aggregate_occupancy(poses)
    assert results[0].distances == (4.0, 4.4)
    assert results[0].mean_distance == pytest.approx(4.2)
    assert results[0].median_distance == pytest.approx(4.2)


def test_different_residues_tracked_independently() -> None:
    it = InteractionType.H_BOND
    poses = [
        [_FakeInteraction(it, 852, "A", "O1"), _FakeInteraction(it, 900, "A", "O1")],
        [_FakeInteraction(it, 852, "A", "O1")],
    ]
    results = aggregate_occupancy(poses)
    by_res = {r.residue_number: r for r in results}
    assert by_res[852].occupancy == 1.0
    assert by_res[900].occupancy == 0.5


# ── Multi-pose PDBQT parsing ──────────────────────────────────────────────────

_MULTI_MODEL_PDBQT = """MODEL 1
ATOM      1  C1  UNL     1      1.000   2.000   3.000  1.00  0.00     0.000 C
ATOM      2  O1  UNL     1      2.000   2.000   3.000  1.00  0.00     0.000 OA
ENDMDL
MODEL 2
ATOM      1  C1  UNL     1      1.500   2.500   3.500  1.00  0.00     0.000 C
ATOM      2  O1  UNL     1      2.500   2.500   3.500  1.00  0.00     0.000 OA
ENDMDL
MODEL 3
ATOM      1  C1  UNL     1      1.100   2.100   3.100  1.00  0.00     0.000 C
ATOM      2  O1  UNL     1      2.100   2.100   3.100  1.00  0.00     0.000 OA
ENDMDL
"""

_SINGLE_MODEL_PDBQT = """ATOM      1  C1  UNL     1      1.000   2.000   3.000  1.00  0.00     0.000 C
ATOM      2  O1  UNL     1      2.000   2.000   3.000  1.00  0.00     0.000 OA
"""  # noqa: E501


def test_multi_pose_parsing_separates_models(tmp_path: Path) -> None:
    p = tmp_path / "multi.pdbqt"
    p.write_text(_MULTI_MODEL_PDBQT)
    poses = parse_pdbqt_multi_pose(p, is_ligand=True)
    assert len(poses) == 3
    assert all(len(pose) == 2 for pose in poses)
    # coordinates differ per pose -- confirms no cross-contamination
    assert poses[0][0].x == 1.000
    assert poses[1][0].x == 1.500
    assert poses[2][0].x == 1.100


def test_single_model_file_returns_one_pose(tmp_path: Path) -> None:
    p = tmp_path / "single.pdbqt"
    p.write_text(_SINGLE_MODEL_PDBQT)
    poses = parse_pdbqt_multi_pose(p, is_ligand=True)
    assert len(poses) == 1
    assert len(poses[0]) == 2


def test_multi_pose_atom_indices_reset_per_pose(tmp_path: Path) -> None:
    """Each pose's atom .index must start at 0 -- never a running count
    across pose boundaries (a real bug this module's design avoids)."""
    p = tmp_path / "multi.pdbqt"
    p.write_text(_MULTI_MODEL_PDBQT)
    poses = parse_pdbqt_multi_pose(p, is_ligand=True)
    for pose in poses:
        assert pose[0].index == 0
        assert pose[1].index == 1
