"""Scaffold-aware and series-aware data splitting.

Authority: SCI1-017. Constitution §3.4.

Constitution §3.4 mandate:
  "Scaffold- or series-aware at minimum; time-aware where chronology exists.
  Held-out set contains entire series absent from training.
  Model-selection folds respect the same series boundaries as the final split."

The critical requirement: if compound X is in the training set, ALL compounds
sharing its Bemis-Murcko scaffold must also be in the training set. The test
set must contain only scaffolds completely unseen during training.

This prevents the model from exploiting similarity between training and test
compounds -- a form of data leakage that inflates measured performance.

Scientific rule classification
  RULE_AVAILABLE:  Bemis-Murcko scaffold definition (Bemis & Murcko 1996,
    J. Med. Chem.). This is a widely accepted and computationally reproducible
    scaffold definition using the RDKit MurckoDecomposer.
  RULE_AVAILABLE:  The constraint that entire series must be held out together.
    This is explicitly stated in Constitution §3.4.
  RULE_MISSING:    The specific split fractions. Constitution §3.4 does not
    specify these; they are seal-at-Stage-0 parameters.
  RULE_MISSING:    Whether to use scaffold-aware or series-aware splitting
    when both are possible. Default: scaffold-aware (more conservative).
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

__all__ = [
    "SPLITTING_ALGORITHM_VERSION",
    "ScaffoldSplit",
    "scaffold_split",
]

SPLITTING_ALGORITHM_VERSION = "scaffold_split_v1_sci1017"


@dataclass(frozen=True, slots=True)
class ScaffoldSplit:
    """Result of a scaffold-aware train/val/test split.

    Attributes:
        train_ids:      Compound IDs in training partition.
        val_ids:        Compound IDs in validation partition.
        test_ids:       Compound IDs in test partition.
        n_train_scaffolds: Distinct scaffolds in training.
        n_val_scaffolds:   Distinct scaffolds in validation.
        n_test_scaffolds:  Distinct scaffolds in test.
        test_fraction:  Achieved test fraction (may differ slightly from target).
        val_fraction:   Achieved val fraction.
        scaffold_overlap: Always 0 for a valid split.
        algorithm_version: Pinned version.
    """

    train_ids: tuple[str, ...]
    val_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    n_train_scaffolds: int
    n_val_scaffolds: int
    n_test_scaffolds: int
    test_fraction: float
    val_fraction: float
    scaffold_overlap: int
    algorithm_version: str

    def __post_init__(self) -> None:
        if self.scaffold_overlap != 0:
            raise ValueError(
                f"Invalid split: scaffold_overlap = {self.scaffold_overlap} "
                "-- scaffolds must be exclusive across partitions"
            )

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "test_ids": sorted(self.test_ids),
                "train_ids": sorted(self.train_ids),
                "val_ids": sorted(self.val_ids),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def _murcko_scaffold(smiles: str) -> str | None:
    try:
        mol = Chem.MolFromSmiles(smiles)
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)  # type: ignore[no-untyped-call]
        smi = Chem.MolToSmiles(scaffold, canonical=True)
        return smi if smi else "NO_SCAFFOLD"
    except Exception:
        return None


def scaffold_split(
    compounds: list[tuple[str, str]],  # (compound_id, smiles)
    test_fraction: float = 0.2,
    val_fraction: float = 0.1,
    random_seed: int = 42,
) -> ScaffoldSplit:
    """Scaffold-aware train/val/test split (Constitution §3.4).

    Parameters
    ----------
    compounds:      List of (compound_id, smiles) pairs.
    test_fraction:  Target fraction for test set (scaffolds, not compounds).
    val_fraction:   Target fraction for validation set.
    random_seed:    Seed for deterministic scaffold ordering.

    Returns:
    -------
    `ScaffoldSplit` where no scaffold appears in more than one partition.
    """
    if not compounds:
        return ScaffoldSplit(
            train_ids=(),
            val_ids=(),
            test_ids=(),
            n_train_scaffolds=0,
            n_val_scaffolds=0,
            n_test_scaffolds=0,
            test_fraction=0.0,
            val_fraction=0.0,
            scaffold_overlap=0,
            algorithm_version=SPLITTING_ALGORITHM_VERSION,
        )

    # Assign scaffolds
    scaffold_to_ids: dict[str, list[str]] = defaultdict(list)
    for cid, smi in compounds:
        scaffold = _murcko_scaffold(smi) or "INVALID"
        scaffold_to_ids[scaffold].append(cid)

    # Sort scaffolds deterministically (by scaffold SMILES for reproducibility)
    sorted_scaffolds = sorted(scaffold_to_ids.keys())
    # Deterministic shuffle using seed
    rng_state = random_seed
    indices = list(range(len(sorted_scaffolds)))
    for i in range(len(indices) - 1, 0, -1):
        rng_state = (rng_state * 1664525 + 1013904223) & 0xFFFFFFFF
        j = rng_state % (i + 1)
        indices[i], indices[j] = indices[j], indices[i]
    shuffled = [sorted_scaffolds[i] for i in indices]

    # Assign scaffolds to partitions
    n_total = len(shuffled)
    n_test = max(1, int(n_total * test_fraction))
    n_val = max(1, int(n_total * val_fraction))
    test_scaffolds = set(shuffled[:n_test])
    val_scaffolds = set(shuffled[n_test : n_test + n_val])

    train_ids: list[str] = []
    val_ids: list[str] = []
    test_ids: list[str] = []
    for scaffold, ids in scaffold_to_ids.items():
        if scaffold in test_scaffolds:
            test_ids.extend(ids)
        elif scaffold in val_scaffolds:
            val_ids.extend(ids)
        else:
            train_ids.extend(ids)

    # Verify no overlap (guaranteed by construction, but check)
    train_set = set(train_ids)
    val_set = set(val_ids)
    test_set = set(test_ids)
    overlap = len(train_set & test_set) + len(train_set & val_set) + len(val_set & test_set)

    n_total_compounds = len(train_ids) + len(val_ids) + len(test_ids)
    achieved_test = len(test_ids) / n_total_compounds if n_total_compounds > 0 else 0.0
    achieved_val = len(val_ids) / n_total_compounds if n_total_compounds > 0 else 0.0

    return ScaffoldSplit(
        train_ids=tuple(sorted(train_ids)),
        val_ids=tuple(sorted(val_ids)),
        test_ids=tuple(sorted(test_ids)),
        n_train_scaffolds=len(shuffled) - n_test - n_val,
        n_val_scaffolds=n_val,
        n_test_scaffolds=n_test,
        test_fraction=round(achieved_test, 4),
        val_fraction=round(achieved_val, 4),
        scaffold_overlap=overlap,
        algorithm_version=SPLITTING_ALGORITHM_VERSION,
    )
