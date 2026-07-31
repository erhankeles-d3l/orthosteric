"""Configuration schema and the non-composable sealed loader.

Objective: FND-5.
Owner: ENG §5.

Scientific rationale:
    Hydra composition and CLI overrides can silently defeat a seal, and a CLI override
    leaves no git trace. Pre-registered thresholds (Constitution §1.4) therefore load
    through a path that refuses override keys entirely, and the resolved values are
    hashed so an evaluation can verify them against ``sealed/`` at use time.

    Building this at FND-5 rather than when thresholds first exist matters: deferred, the
    first pre-registered thresholds would be read through an overridable path and §1.4
    would be unenforceable for exactly the seals that decide whether the project proceeds.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "ConfigurationError",
    "SealedConfigError",
    "SealedThresholds",
    "load_sealed_thresholds",
    "resolved_config_hash",
]


class ConfigurationError(ValueError):
    """Raised on a malformed or unknown configuration key."""


class SealedConfigError(ConfigurationError):
    """Raised when a sealed configuration is loaded through an overridable path."""


@dataclass(frozen=True, slots=True)
class SealedThresholds:
    """Pre-registered thresholds, loaded without composition.

    Attributes:
        values: Threshold name to value, as strings so that no float enters a hash.
        content_hash: SHA-256 over the canonical rendering, for verification against
            ``sealed/*.sha256`` at evaluation time.
    """

    values: dict[str, str]
    content_hash: str


def resolved_config_hash(resolved: dict[str, Any]) -> str:
    """Hash a fully resolved configuration.

    Args:
        resolved: The resolved configuration mapping, not a template.

    Returns:
        Hex SHA-256 over canonical JSON.
    """
    canonical = json.dumps(resolved, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_sealed_thresholds(
    path: Path, *, overrides: dict[str, str] | None = None
) -> SealedThresholds:
    """Load sealed thresholds, refusing any override.

    Args:
        path: JSON file under ``sealed/config/``.
        overrides: Must be empty or ``None``. Present in the signature so that an
            attempted override fails loudly rather than being silently ignored.

    Returns:
        The loaded thresholds and their content hash.

    Raises:
        SealedConfigError: If overrides are supplied, or the file is not under ``sealed/``.
        ConfigurationError: If the payload is not a flat string mapping.
    """
    if overrides:
        msg = (
            "sealed thresholds are not overridable: a CLI or composition override leaves "
            "no git trace and would make Constitution §1.4 unenforceable"
        )
        raise SealedConfigError(msg)
    if "sealed" not in path.parts:
        msg = f"sealed thresholds must live under sealed/: {path}"
        raise SealedConfigError(msg)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or any(not isinstance(v, str) for v in raw.values()):
        msg = "sealed threshold file must be a flat mapping of string to string"
        raise ConfigurationError(msg)
    values = {str(k): str(v) for k, v in sorted(raw.items())}
    canonical = json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return SealedThresholds(
        values=values,
        content_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )
