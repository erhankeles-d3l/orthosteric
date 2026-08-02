#!/usr/bin/env python3
"""Corpus refresh script — minimal public interface.

Usage:
    python scripts/refresh_corpus.py [--max-per-isoform N] [--dry-run]

Governance
----------
This script acquires evidence for the ADR-0003 computational adjudication
framework.  It does NOT:
  - seal thresholds;
  - modify ADR-0003 or the Constitution;
  - begin model training or evaluation.

Any GOVERNANCE_EXCEPTION in the adjudication result is written to
docs/reports/audit_reports/PEEAP_GOVERNANCE_EXCEPTIONS.json and must be
manually reviewed before the affected downstream stage may proceed.
"""

import argparse
import json
import pathlib
import subprocess
import sys
import time

# Ensure the package is importable
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from orthosteric.data.adjudication import AdjudicationStatus, run_adr0003_adjudication
from orthosteric.data.chembl_adapter import fetch_pi3k_records
from orthosteric.data.corpus import CorpusSnapshot


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-per-isoform", type=int, default=5000)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch but do not persist snapshot; still runs adjudication",
    )
    args = parser.parse_args()

    print("=== PI3K Corpus Refresh ===")
    print(f"Max per isoform : {args.max_per_isoform}")
    print(f"Dry run         : {args.dry_run}")
    sha = git_sha()
    print(f"Git SHA         : {sha}")

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"\nFetching ChEMBL records at {ts}...")
    records = fetch_pi3k_records(max_per_isoform=args.max_per_isoform, retrieval_timestamp=ts)
    print(f"Total fetched   : {len(records)}")

    snap = CorpusSnapshot.create(records, git_sha=sha, source_versions={"chembl": "current"})
    print(f"\nSnapshot ID     : {snap.manifest.snapshot_id}")
    print(f"Accepted        : {snap.manifest.accepted_count}")
    print(f"Excluded        : {snap.manifest.excluded_count}")
    print(f"SHA-256         : {snap.manifest.sha256[:16]}...")

    print("\nRunning ADR-0003 adjudication...")
    result = run_adr0003_adjudication(snap)
    print(f"Overall status  : {result.overall_status.value}")

    for label, q in [
        ("AUDITOR-1", result.auditor1),
        ("AUDITOR-2", result.auditor2),
        ("AUDITOR-3", result.auditor3),
        ("AUDITOR-4", result.auditor4),
        ("AUDITOR-5", result.auditor5),
    ]:
        if q:
            print(f"  {label}: {q.status.value}")

    if result.overall_status == AdjudicationStatus.INSUFFICIENT_EVIDENCE:
        print("\n[GOVERNANCE] INSUFFICIENT_EVIDENCE — see AUDITOR-5 Km gap.")
        print("SCI0-008 is blocked until ATP Km is resolved.")

    out_dir = pathlib.Path("docs/reports/audit_reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "PEEAP_LAST_ADJUDICATION_RESULT.json"
    out_file.write_text(json.dumps(result.to_dict(), indent=2, default=str))
    print(f"\nResult written  : {out_file}")

    if result.governance_exceptions:
        exc_file = out_dir / "PEEAP_GOVERNANCE_EXCEPTIONS.json"
        exc_file.write_text(
            json.dumps(
                {
                    "snapshot_id": snap.manifest.snapshot_id,
                    "timestamp": ts,
                    "exceptions": result.governance_exceptions,
                },
                indent=2,
            )
        )
        print(f"Exceptions      : {exc_file}")

    return 0 if result.overall_status.value in ("RESOLVED", "PROVISIONALLY_RESOLVED") else 1


if __name__ == "__main__":
    sys.exit(main())
