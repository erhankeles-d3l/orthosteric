"""orthosteric.data configuration.

Objective: SCI0-002.
ENG §5: every configurable value originates here; no URL, path, timeout or
worker count is hardcoded in any other module in this package.

All values are read from environment variables.  Defaults are provided only
where absence is safe; otherwise ``ConfigurationError`` is raised.

No Hydra dependency at this layer — this module is imported before the
training stack and must be importable in isolation.  Full Hydra composition
is added at SCI-1 when the training stack is introduced.
"""

from __future__ import annotations

import os

from orthosteric.data.exceptions import ConfigurationError


def _env(key: str, default: str | None = None) -> str:
    """Read an environment variable; raise ConfigurationError if required and absent."""
    value = os.environ.get(key, default)
    if value is None:
        raise ConfigurationError(
            f"Required environment variable {key!r} is not set. "
            "Set it in the shell environment or in a .env file (never committed)."
        )
    return value


def _env_int(key: str, default: int | None = None) -> int:
    raw = _env(key, str(default) if default is not None else None)
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"Environment variable {key!r} must be an integer, got {raw!r}."
        ) from exc


def _env_bool(key: str, default: bool = False) -> bool:
    raw = _env(key, str(default)).lower()
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    raise ConfigurationError(
        f"Environment variable {key!r} must be a boolean (true/false/1/0), got {raw!r}."
    )


# ──────────────────────────────────────────────────────────────────────────────
# ChEMBL adapter
# ──────────────────────────────────────────────────────────────────────────────


def chembl_api_base() -> str:
    """Base URL for the ChEMBL REST API."""
    return _env("CHEMBL_API_BASE", "https://www.ebi.ac.uk/chembl/api/data")


def chembl_page_size() -> int:
    """Number of records per ChEMBL API request page."""
    return _env_int("CHEMBL_PAGE_SIZE", 100)


def chembl_max_per_isoform() -> int:
    """Safety ceiling on records fetched per isoform per refresh."""
    return _env_int("CHEMBL_MAX_PER_ISOFORM", 5000)


def chembl_request_timeout_s() -> int:
    """HTTP request timeout in seconds."""
    return _env_int("CHEMBL_REQUEST_TIMEOUT_S", 30)


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot storage
# ──────────────────────────────────────────────────────────────────────────────


def snapshot_dir() -> str:
    """Directory where corpus snapshots are written."""
    return _env("ORTHOSTERIC_SNAPSHOT_DIR", "data/snapshots")


# ──────────────────────────────────────────────────────────────────────────────
# Adjudication
# ──────────────────────────────────────────────────────────────────────────────


def adjudication_procedure_version() -> str:
    """Version of the ADR-0003 adjudication procedure in use (frozen at v1.0)."""
    return "1.0"  # not env-configurable; procedure version is governance-controlled
