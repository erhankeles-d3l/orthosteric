#!/usr/bin/env python3
"""Stage 0 — Robust acquisition with long pauses, target-by-target.
Run with: python3 scripts/stage0_acquire.py [target_id]
Or without arguments to run all in sequence.
"""

import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

API = "https://www.ebi.ac.uk/chembl/api/data"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "chembl"
RAW_DIR.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 200
CURL_TIMEOUT = 30
INTER_PAGE_SLEEP = 1.0
INTER_TARGET_SLEEP = 15.0
MAX_RETRIES = 5

TARGETS = {
    # PIK3CA: PENDING_API_VERIFICATION (ADR-0011) — not included
    "CHEMBL3145": {"gene": "PIK3CB", "tier": "tier1", "types": ["IC50"]},  # confirmed ChEMBL 37
    "CHEMBL3267": {"gene": "PIK3CG", "tier": "tier1", "types": ["IC50"]},  # confirmed ChEMBL 37
    # PIK3CD: PENDING_API_VERIFICATION (ADR-0011) — not included
    # MTOR CHEMBL2842: tier2; ID unverified in ChEMBL 37 — not included until ADR-0011 follow-up
}


def curl_json(url: str) -> dict | None:
    """Fetch JSON via curl. Returns None on failure."""
    for attempt in range(MAX_RETRIES):
        r = subprocess.run(
            ["curl", "-s", "--max-time", str(CURL_TIMEOUT),
             "--retry", "0",          # we handle retries ourselves
             "-A", "orthosteric-research-pipeline/1.0 (contact: research@example.org)",
             "-H", "Accept: application/json",
             url],
            capture_output=True, text=True, timeout=CURL_TIMEOUT + 5, check=False,
        )
        text = r.stdout.strip()
        if r.returncode == 0 and text and text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        wait = 5 * (attempt + 1)
        print(f"    attempt {attempt+1}/{MAX_RETRIES} failed (rc={r.returncode}), "
              f"sleeping {wait}s", flush=True)
        time.sleep(wait)
    return None


def download_one_target(chembl_id: str, meta: dict) -> dict:
    gene = meta["gene"]
    tier = meta["tier"]
    types = meta["types"]

    target_dir = RAW_DIR / chembl_id
    target_dir.mkdir(exist_ok=True)

    summary: dict = {"chembl_id": chembl_id, "gene": gene, "tier": tier,
                     "types": {}, "total_records": 0, "errors": []}

    for st in types:
        type_dir = target_dir / st
        type_dir.mkdir(exist_ok=True)

        count_file = type_dir / "_count.json"
        if count_file.exists():
            existing = json.loads(count_file.read_text())
            t = existing["total"]
            print(f"  {chembl_id}/{st}: already complete ({t} records)", flush=True)
            summary["types"][st] = t
            summary["total_records"] += t
            continue

        # Probe
        params = urllib.parse.urlencode({
            "target_chembl_id": chembl_id,
            "standard_type": st,
            "limit": 1,
            "format": "json",
        })
        probe = curl_json(f"{API}/activity/?{params}")
        if probe is None:
            msg = f"{chembl_id}/{st}: probe failed"
            print(f"  {msg}", flush=True)
            summary["errors"].append(msg)
            summary["types"][st] = None
            continue

        total = probe.get("page_meta", {}).get("total_count", 0)
        print(f"  {chembl_id}/{st}: {total} records", flush=True)

        if total == 0:
            count_file.write_text(json.dumps({"total": 0, "pages": 0}))
            summary["types"][st] = 0
            continue

        # Download pages
        offset = 0
        page = 0
        failed = False
        while offset < total:
            page_file = type_dir / f"page_{page:04d}.json"
            if not page_file.exists():
                params = urllib.parse.urlencode({
                    "target_chembl_id": chembl_id,
                    "standard_type": st,
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "format": "json",
                })
                data = curl_json(f"{API}/activity/?{params}")
                if data is None:
                    msg = f"{chembl_id}/{st}: page {page} failed"
                    print(f"  {msg}", flush=True)
                    summary["errors"].append(msg)
                    failed = True
                    break
                page_file.write_text(json.dumps(data, separators=(",", ":")))
                n = len(data.get("activities", []))
                print(f"    page {page}: {n} records (offset={offset}/{total})", flush=True)
                time.sleep(INTER_PAGE_SLEEP)
            offset += PAGE_SIZE
            page += 1

        if not failed:
            count_file.write_text(json.dumps({"total": total, "pages": page}))
            summary["types"][st] = total
            summary["total_records"] += total
        else:
            # Record partial progress
            partial = sum(
                len(json.loads(f.read_text()).get("activities", []))
                for f in sorted(type_dir.glob("page_*.json"))
            )
            summary["types"][st] = f"PARTIAL:{partial}/{total}"
            summary["errors"].append(f"{chembl_id}/{st}: partial ({partial}/{total})")

    return summary


def write_manifest(summaries: list[dict], version: str = "ChEMBL_37") -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest = {
        "source": "ChEMBL",
        "source_version": version,
        "retrieval_timestamp_utc": ts,
        "targets": summaries,
        "total_complete_records": sum(
            s.get("total_records", 0) for s in summaries
        ),
    }
    path = RAW_DIR / "acquisition_manifest.json"
    path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest: {path}", flush=True)
    print(f"Total records (complete only): {manifest['total_complete_records']}", flush=True)


def main():
    # Optionally run only specific target(s)
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(TARGETS.keys())
    unknown = [t for t in requested if t not in TARGETS]
    if unknown:
        print(f"Unknown targets: {unknown}")
        sys.exit(1)

    print("=== Stage 0 Acquisition ===", flush=True)
    print(f"Targets: {requested}", flush=True)
    print(f"Raw dir: {RAW_DIR}", flush=True)
    print(flush=True)

    summaries = []
    for i, chembl_id in enumerate(requested):
        if i > 0:
            print(f"Sleeping {INTER_TARGET_SLEEP}s between targets...", flush=True)
            time.sleep(INTER_TARGET_SLEEP)
        meta = TARGETS[chembl_id]
        print(f"--- {chembl_id} ({meta['gene']}) ---", flush=True)
        s = download_one_target(chembl_id, meta)
        summaries.append(s)
        print(f"  => {s['total_records']} records, "
              f"{len(s['errors'])} errors: {s['errors']}", flush=True)

    write_manifest(summaries)


if __name__ == "__main__":
    main()
