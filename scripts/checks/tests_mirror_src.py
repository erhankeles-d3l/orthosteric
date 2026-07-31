"""Verify tests/ mirrors src/ exactly (ENG §3).

A source package without a test package, or the reverse, is a defect.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = "orthosteric"


def main() -> int:
    """Compare package directories under src and tests."""
    src = {p.relative_to(ROOT / "src" / PKG) for p in (ROOT / "src" / PKG).rglob("*") if p.is_dir()}
    tst = {p.relative_to(ROOT / "tests") for p in (ROOT / "tests").rglob("*") if p.is_dir()}
    src = {p for p in src if not str(p).startswith("__")}
    tst = {p for p in tst if not str(p).startswith("__")}
    missing_tests = sorted(str(p) for p in src - tst)
    orphan_tests = sorted(str(p) for p in tst - src)
    if missing_tests or orphan_tests:
        for m in missing_tests:
            print(f"tests-mirror-src: source package without tests: {m}")
        for o in orphan_tests:
            print(f"tests-mirror-src: test package without source: {o}")
        return 1
    print("tests-mirror-src: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
