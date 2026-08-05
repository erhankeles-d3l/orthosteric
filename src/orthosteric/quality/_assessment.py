"""Corpus quality assessment engine and result type.

Authority: `ADR-0009`; `GDR-003`.

`CorpusQualityAssessor` mirrors `ADR-0008`'s `PolicyEngine` exactly: it holds
a list of registered `QualityDimensionEvaluator` instances and runs all of
them, in order, over one `CorpusProfile`. Adding a dimension means passing
another evaluator instance to the constructor; nothing here changes.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from orthosteric.data.snapshots import CorpusProfile
from orthosteric.quality._dimensions import DimensionAssessment, QualityDimensionEvaluator

__all__ = [
    "ASSESSMENT_ALGORITHM_VERSION",
    "QUALITY_ASSESSMENT_SCHEMA_VERSION",
    "CorpusQualityAssessment",
    "CorpusQualityAssessor",
]

QUALITY_ASSESSMENT_SCHEMA_VERSION = "corpus_quality_assessment_v1_adr0009"
ASSESSMENT_ALGORITHM_VERSION = "corpus_quality_rules_v1_gdr003"
"""Version of the *rule set* GDR-003 §2 defines. Bump this if a dimension's
rule changes, independent of the schema_version bump for structural changes
to the assessment object itself."""


def _canonical_default(obj: object) -> object:
    if hasattr(obj, "value"):  # StrEnum
        return obj.value
    return str(obj)


def _stable_json(obj: object) -> str:
    return json.dumps(
        obj, sort_keys=True, default=_canonical_default, separators=(",", ":"), ensure_ascii=True
    )


@dataclass(frozen=True, slots=True)
class CorpusQualityAssessment:
    """Immutable, content-hashed interpretation of one `CorpusProfile`.

    Derived exclusively from an already-frozen `CorpusProfile` — no raw
    record is read anywhere upstream of this type (`ADR-0009` §2).

    Attributes:
        schema_version: Assessment schema version.
        assessment_algorithm_version: Version of the *rule set* (`GDR-003`
            §2) applied. Bump this if a dimension's rule changes, even if no
            evaluator's code otherwise does — mirrors `PROFILE_ALGORITHM_
            VERSION`'s role for `CorpusProfile`.
        profile_sha256: The `CorpusProfile` this assessment was computed
            from — a foreign-key reference, giving full backward
            traceability to the snapshot and, transitively, to raw evidence.
        dimensions: One `DimensionAssessment` per registered evaluator, in
            evaluation order.
        assessed_at_utc: When the assessment was computed. Provenance
            metadata only — excluded from `assessment_content_sha256`.
        assessment_content_sha256: Content hash over every field above
            except `assessed_at_utc`.
    """

    schema_version: str
    assessment_algorithm_version: str
    profile_sha256: str
    dimensions: tuple[DimensionAssessment, ...]
    assessed_at_utc: str
    assessment_content_sha256: str

    def dimension(self, name: str) -> DimensionAssessment | None:
        for d in self.dimensions:
            if d.dimension == name:
                return d
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessed_at_utc": self.assessed_at_utc,
            "assessment_algorithm_version": self.assessment_algorithm_version,
            "assessment_content_sha256": self.assessment_content_sha256,
            "dimensions": [d.to_canonical_dict() for d in self.dimensions],
            "profile_sha256": self.profile_sha256,
            "schema_version": self.schema_version,
        }


class CorpusQualityAssessor:
    """Runs registered dimension evaluators over a `CorpusProfile`.

    Never reads raw records; never reads anything but the `CorpusProfile`
    passed to `assess()`. Determinism: identical profile and evaluator set
    yield an identical `assessment_content_sha256` regardless of when
    `assess()` is called.
    """

    def __init__(self, evaluators: Sequence[QualityDimensionEvaluator]) -> None:
        if not evaluators:
            raise ValueError("CorpusQualityAssessor requires at least one evaluator")
        names = [e.dimension_name for e in evaluators]
        if len(set(names)) != len(names):
            raise ValueError(f"Duplicate dimension_name values registered: {names}")
        self._evaluators = tuple(evaluators)

    @property
    def registered_dimensions(self) -> tuple[str, ...]:
        return tuple(e.dimension_name for e in self._evaluators)

    def assess(self, profile: CorpusProfile) -> CorpusQualityAssessment:
        dimensions = tuple(e.evaluate(profile) for e in self._evaluators)

        payload = _stable_json(
            {
                "dimensions": [d.to_canonical_dict() for d in dimensions],
                "profile_sha256": profile.profile_sha256,
                "schema_version": QUALITY_ASSESSMENT_SCHEMA_VERSION,
                "assessment_algorithm_version": ASSESSMENT_ALGORITHM_VERSION,
            }
        )
        content_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        return CorpusQualityAssessment(
            schema_version=QUALITY_ASSESSMENT_SCHEMA_VERSION,
            assessment_algorithm_version=ASSESSMENT_ALGORITHM_VERSION,
            profile_sha256=profile.profile_sha256,
            dimensions=dimensions,
            assessed_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            assessment_content_sha256=content_sha,
        )
