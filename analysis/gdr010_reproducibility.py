"""ANALYSIS / PROTOTYPE — GDR-010 snapshot identity reproducibility experiment.

Read-only. Does NOT modify hashing. Demonstrates which fields enter identity.
"""

import copy
import gzip
import json
import pathlib
import sys

sys.path.insert(0, "src")
from orthosteric.data.snapshots._builder import SnapshotBuilder
from orthosteric.data.snapshots._manifest import PolicyManifest, SoftwareProvenance

SNAP = pathlib.Path("data/snapshots/activity_snapshot_A3")
man = json.loads((SNAP / "manifest.json").read_text())
with gzip.open(SNAP / "records.json.gz", "rt") as f:
    records = json.load(f)

POLICY = PolicyManifest(
    chemical_standardization_policy="sci0008b_rdkit_canonical_v1",
    identifier_harmonization_policy="sci0008c_inchikey_v1",
    deduplication_policy="sci0009_log_median_v1",
    confidence_scoring_policy="sci0010_v1",
    adr0003_adjudication_procedure="adr0003_procedure_v1.0",
    alphafold_fallback_policy="sci0007_af_fallback_v1.0",
    auditor5_status="INSUFFICIENT_EVIDENCE_frozen",
    cheng_prusoff_status="BLOCKED/AUDITOR-5",
    within_group_conflict_threshold="RULE_MISSING/SCI0-016_required",
    confidence_assay_quality_rule="RULE_MISSING",
    confidence_lit_tier_rule="RULE_MISSING",
)
d = man["software"]
BASE_SW = dict(
    python_version=d["python_version"],
    rdkit_version=d["rdkit_version"],
    orthosteric_version=d["orthosteric_version"],
    git_sha=d["git_sha"],
    git_dirty=d["git_dirty"],
    os_platform=d["os_platform"],
    os_version=d["os_version"],
    lockfile_hash=d.get("lockfile_hash", ""),
    key_package_versions=d.get("key_package_versions", {}),
)


def build(sw_over=None, rec_over=None, policy=POLICY):
    sw = dict(BASE_SW)
    sw.update(sw_over or {})
    recs = rec_over if rec_over is not None else records
    b = SnapshotBuilder(software=SoftwareProvenance(**sw), policy=policy)
    return b.build(recs, source_versions=man.get("source_versions")).manifest.snapshot_sha256


baseline = build()
print(f"Stored A3 SHA : {man['snapshot_sha256']}")
print(f"Rebuilt SHA   : {baseline}")
print(f"MATCH         : {baseline == man['snapshot_sha256']}\n")

print("=== Perturbation experiment (records byte-identical throughout) ===")
print(f"{'perturbation':<46}{'identity changes?':<20}{'sha[:12]'}")
print("-" * 82)

cases = [
    ("BASELINE (no change)", {}, None),
    ("git_sha -> different commit", {"git_sha": "0" * 40}, None),
    ("git_dirty True -> False", {"git_dirty": not BASE_SW["git_dirty"]}, None),
    ("python_version 3.12.3 -> 3.12.4", {"python_version": "3.12.4"}, None),
    ("os_platform Linux -> Darwin", {"os_platform": "Darwin"}, None),
    ("os_version -> different kernel", {"os_version": "6.99.0-generic"}, None),
    ("rdkit_version -> 2025.09.1", {"rdkit_version": "2025.09.1"}, None),
    ("orthosteric_version -> 0.2.0", {"orthosteric_version": "0.2.0"}, None),
    ("lockfile_hash -> set", {"lockfile_hash": "abc123"}, None),
]
for label, sw_over, rec_over in cases:
    sha = build(sw_over, rec_over)
    changed = "YES  <-- " if sha != baseline else "no"
    print(f"{label:<46}{changed:<20}{sha[:12]}")

# Record-level perturbation: genuinely scientific change
recs2 = copy.deepcopy(records)
for r in recs2:
    if not r.get("exclusion_reason"):
        r["activity_value"] = r.get("activity_value") or 0
        break
recs3 = copy.deepcopy(records)
changed_one = False
for r in recs3:
    if not r.get("exclusion_reason") and r.get("activity_value") is not None:
        r["activity_value"] = float(r["activity_value"]) + 1.0
        changed_one = True
        break
sha_sci = build({}, recs3)
print(
    f"{'ONE activity_value +1.0 (scientific change)':<46}{'YES  <-- ' if sha_sci != baseline else 'no':<20}{sha_sci[:12]}"
)

# Policy perturbation
pol2 = PolicyManifest(
    **{
        **{k: getattr(POLICY, k) for k in POLICY.__dataclass_fields__},
        "deduplication_policy": "sci0009_log_mean_v2",
    }
)
sha_pol = build({}, None, pol2)
print(
    f"{'deduplication_policy changed (scientific)':<46}{'YES  <-- ' if sha_pol != baseline else 'no':<20}{sha_pol[:12]}"
)

# Retrieval timestamp inside records
recs4 = copy.deepcopy(records)
for r in recs4:
    r["retrieval_timestamp"] = "2099-01-01T00:00:00Z"
sha_ts = build({}, recs4)
print(
    f"{'retrieval_timestamp in records changed':<46}{'YES  <-- ' if sha_ts != baseline else 'no':<20}{sha_ts[:12]}"
)

# Option A prototype: content hash over records+policy only
from orthosteric.data.snapshots._builder import _hash_payload, _stable_json


def content_sha(recs, policy):
    def key(r):
        return (
            str(r.get("record_type", "activity")),
            str(r.get("source_db", "")),
            str(r.get("source_record_id", r.get("pdb_id", ""))),
        )

    return _hash_payload(
        _stable_json(sorted(recs, key=key)) + "\n" + _stable_json(policy.to_canonical_dict())
    )


def build_prov_sha(sw):
    return _hash_payload(_stable_json(SoftwareProvenance(**sw).to_canonical_dict()))


print("\n=== Option A prototype (content_sha256 = records + policy only) ===")
c_base = content_sha(records, POLICY)
print(f"  content_sha256 baseline                : {c_base[:16]}")
print(
    f"  content_sha256 after git_sha change    : {content_sha(records, POLICY)[:16]}  (unchanged by construction)"
)
print(
    f"  content_sha256 after activity change   : {content_sha(recs3, POLICY)[:16]}  CHANGED={content_sha(recs3, POLICY) != c_base}"
)
print(
    f"  content_sha256 after policy change     : {content_sha(records, pol2)[:16]}  CHANGED={content_sha(records, pol2) != c_base}"
)
sw_a = dict(BASE_SW)
sw_b = dict(BASE_SW)
sw_b["git_sha"] = "0" * 40
print(f"  build_provenance_sha256 (env A)        : {build_prov_sha(sw_a)[:16]}")
print(
    f"  build_provenance_sha256 (env B)        : {build_prov_sha(sw_b)[:16]}  DIFFERS={build_prov_sha(sw_a) != build_prov_sha(sw_b)}"
)
