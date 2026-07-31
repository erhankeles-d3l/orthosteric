"""Verify no seal postdates the first training-code commit (CLAUDE.md §7).

A seal created after modelling began is not a pre-registration. This check is written
while src/orthosteric/train/ contains no implementation, so it is correct for every seal
that follows.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAIN = "src/orthosteric/train"
SEALED = ROOT / "sealed"


def _first_commit_epoch(path: str) -> int | None:
    out = subprocess.run(  # noqa: S603
        ["git", "log", "--reverse", "--format=%ct", "--", path],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
    return int(lines[0]) if lines else None


def main() -> int:
    """Compare seal commit times against the first training commit."""
    train_epoch = _first_commit_epoch(TRAIN)
    if train_epoch is None:
        print("seal-timestamp: OK (no training code committed yet)")
        return 0
    failures: list[str] = []
    for seal in sorted(SEALED.rglob("*")):
        if not seal.is_file() or seal.name == "MANIFEST.md":
            continue
        rel = seal.relative_to(ROOT).as_posix()
        epoch = _first_commit_epoch(rel)
        if epoch is not None and epoch > train_epoch:
            failures.append(rel)
    for f in failures:
        print(f"seal-timestamp: seal postdates first training commit: {f}")
    if failures:
        return 1
    print("seal-timestamp: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
