"""Fail while any unresolved <FILL marker remains (CLAUDE.md §1).

Matches the literal token, never any angle-bracket token, so the <pkg> notation does not
trip it.

Inline code spans are stripped before matching. The governance documents necessarily
*describe* this marker in prose, and a reference is not an unresolved value. Fenced code
blocks are **not** stripped, because a real placeholder inside a command block must still
be caught.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKER = "<FILL"
INLINE_CODE = re.compile(r"`[^`\n]*`")
SEARCH = ["CLAUDE.md", "docs", "configs", "src", "tests", "Makefile", "README.md"]
SKIP = {".git", "__pycache__", "site", ".mypy_cache", ".ruff_cache", ".pytest_cache"}


def _strip_inline_code(text: str) -> str:
    """Remove inline code spans, which may legitimately reference the marker."""
    return INLINE_CODE.sub("``", text)


def main() -> int:
    """Scan tracked documentation and source for unresolved markers."""
    hits: list[str] = []
    for entry in SEARCH:
        target = ROOT / entry
        if not target.exists():
            continue
        paths = [target] if target.is_file() else list(target.rglob("*"))
        for candidate in paths:
            if (
                not candidate.is_file()
                or set(candidate.parts) & SKIP
                or candidate.name == Path(__file__).name
            ):
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if MARKER in _strip_inline_code(line):
                    hits.append(f"{candidate.relative_to(ROOT).as_posix()}:{lineno}")
    for hit in sorted(set(hits)):
        print(f"no-fill-marker: unresolved {MARKER} at {hit}")
    if hits:
        return 1
    print("no-fill-marker: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
