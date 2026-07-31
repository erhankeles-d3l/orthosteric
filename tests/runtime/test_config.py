"""Tests for configuration and the sealed loader (FND-5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orthosteric.runtime.config import (
    ConfigurationError,
    SealedConfigError,
    load_sealed_thresholds,
    resolved_config_hash,
)


@pytest.fixture
def sealed_file(tmp_path: Path) -> Path:
    """A sealed threshold file under a sealed/ path."""
    sealed = tmp_path / "sealed" / "config"
    sealed.mkdir(parents=True)
    target = sealed / "thresholds.json"
    target.write_text(json.dumps({"s2_rmse_margin": "0.3", "s4a_ece": "0.10"}), encoding="utf-8")
    return target


def test_loads_and_hashes(sealed_file: Path) -> None:
    """Sealed thresholds load and produce a stable content hash."""
    a = load_sealed_thresholds(sealed_file)
    b = load_sealed_thresholds(sealed_file)
    assert a.values["s2_rmse_margin"] == "0.3"
    assert a.content_hash == b.content_hash
    assert len(a.content_hash) == 64


def test_override_is_refused(sealed_file: Path) -> None:
    """An attempted override raises rather than being silently ignored.

    A CLI override leaves no git trace, so an overridable threshold would make
    Constitution §1.4 unenforceable.
    """
    with pytest.raises(SealedConfigError, match="not overridable"):
        load_sealed_thresholds(sealed_file, overrides={"s2_rmse_margin": "0.1"})


def test_path_outside_sealed_refused(tmp_path: Path) -> None:
    """A threshold file outside sealed/ is refused."""
    stray = tmp_path / "thresholds.json"
    stray.write_text(json.dumps({"a": "1"}), encoding="utf-8")
    with pytest.raises(SealedConfigError, match="must live under sealed/"):
        load_sealed_thresholds(stray)


def test_non_string_values_refused(tmp_path: Path) -> None:
    """Numeric literals are refused so that no float enters a hash."""
    sealed = tmp_path / "sealed" / "config"
    sealed.mkdir(parents=True)
    target = sealed / "t.json"
    target.write_text(json.dumps({"a": 0.3}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="string to string"):
        load_sealed_thresholds(target)


def test_resolved_config_hash_is_order_independent() -> None:
    """The hash covers content, not key insertion order."""
    assert resolved_config_hash({"a": 1, "b": 2}) == resolved_config_hash({"b": 2, "a": 1})
