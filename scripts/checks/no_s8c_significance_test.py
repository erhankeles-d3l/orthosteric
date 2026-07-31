"""Fail if a significance test appears in the S8c gradient reporter.

Constitution §1.4.1 and §7.6: no significance test is claimed on the correspondence
gradient at n = 4. Written before the reporter exists so it cannot be forgotten later.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "src" / "orthosteric" / "eval"
BANNED = re.compile(r"\b(spearmanr|kendalltau|pearsonr|ttest_|mannwhitneyu|p_?value)\b")


def main() -> int:
    """Scan the evaluation package for significance-test usage."""
    hits: list[str] = []
    if TARGET.exists():
        for p in TARGET.rglob("*.py"):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if BANNED.search(line) and "gradient" in p.read_text(encoding="utf-8"):
                    hits.append(f"{p.relative_to(ROOT).as_posix()}:{i}: {line.strip()}")
    for h in hits:
        print(f"s8c-no-significance-test: {h}")
    if hits:
        return 1
    print("s8c-no-significance-test: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
