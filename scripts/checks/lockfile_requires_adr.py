"""Fail on a dependency-lock change without a linked ADR (ENG §9).

Spontaneous dependency upgrades are the failure mode this prevents.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKS = ("uv.lock", "poetry.lock", "requirements.lock")
ADR = re.compile(r"ADR-\d{4}")


def main() -> int:
    """Check the working commit for a lock change and an ADR reference."""
    changed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    if not any(Path(c).name in LOCKS for c in changed):
        print("lockfile-requires-adr: OK (no lock change)")
        return 0
    msg = subprocess.run(
        ["git", "log", "-1", "--format=%B"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    if ADR.search(msg):
        print("lockfile-requires-adr: OK (ADR referenced)")
        return 0
    print("lockfile-requires-adr: lock changed without a linked ADR in the commit body")
    return 1


if __name__ == "__main__":
    sys.exit(main())
