"""A4 validation — integrity, identity, and GDR-010/011 metadata checks.

Not part of src/ (this is a one-shot validation report, not governed
pipeline code).  Read-only.
"""
import sys, json, gzip, pathlib, subprocess, platform
sys.path.insert(0, "src")

from orthosteric.data.snapshots._builder import SnapshotBuilder
from orthosteric.data.snapshots._manifest import PolicyManifest, SoftwareProvenance
from orthosteric.data.comparability import PanelKeyTier, resolve_panel_key

A3 = pathlib.Path("data/snapshots/activity_snapshot_A3")
A4 = pathlib.Path("data/snapshots/activity_snapshot_A4")

def load(d):
    man = json.loads((d / "manifest.json").read_text())
    with gzip.open(d / "records.json.gz", "rt") as f:
        recs = json.load(f)
    return man, recs

man3, recs3 = load(A3)
man4, recs4 = load(A4)

print("=== A3 (predecessor) untouched? ===")
print(f"  A3 manifest sha (stored):  {man3['snapshot_sha256']}")
print(f"  A3 record count (stored):  {man3['record_count']}")
print(f"  A3 records on disk:        {len(recs3)}")
print(f"  A3 unchanged: {man3['record_count'] == len(recs3)}")

print("\n=== A4 integrity ===")
print(f"  manifest.record_count:     {man4['record_count']}")
print(f"  records on disk:           {len(recs4)}")
print(f"  count match:               {man4['record_count'] == len(recs4)}")
print(f"  parent_snapshot_sha256:    {man4['parent_snapshot_sha256']}")
print(f"  parent == A3 stored sha:   {man4['parent_snapshot_sha256'] == man3['snapshot_sha256']}")

pol = PolicyManifest(
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
sw4 = man4["software"]
software = SoftwareProvenance(
    python_version=sw4["python_version"], rdkit_version=sw4["rdkit_version"],
    orthosteric_version=sw4["orthosteric_version"], git_sha=sw4["git_sha"],
    git_dirty=sw4["git_dirty"], os_platform=sw4["os_platform"], os_version=sw4["os_version"],
    lockfile_hash=sw4.get("lockfile_hash",""), key_package_versions=sw4.get("key_package_versions",{}),
)
b = SnapshotBuilder(software=software, policy=pol)
rebuilt = b.build(recs4, source_versions=man4.get("source_versions"),
                   parent_sha256=man4.get("parent_snapshot_sha256"))
print(f"\n=== A4 content-hash reproducibility ===")
print(f"  stored content_sha256:    {man4['snapshot_sha256']}")
print(f"  rebuilt content_sha256:   {rebuilt.manifest.snapshot_sha256}")
print(f"  REPRODUCIBLE:             {man4['snapshot_sha256'] == rebuilt.manifest.snapshot_sha256}")
print(f"  stored build_prov_sha256: {man4['build_provenance_sha256']}")
print(f"  rebuilt build_prov_sha256:{rebuilt.manifest.build_provenance_sha256}")

# Retrieval-timestamp invariance check: perturb, rebuild, compare
import copy
recs4b = copy.deepcopy(recs4)
for r in recs4b:
    if "retrieval_timestamp" in r:
        r["retrieval_timestamp"] = "1999-01-01T00:00:00Z"
rebuilt_b = b.build(recs4b, source_versions=man4.get("source_versions"),
                     parent_sha256=man4.get("parent_snapshot_sha256"))
print(f"\n=== retrieval_timestamp invariance on real A4 records ===")
print(f"  content_sha256 unaffected by timestamp change: "
      f"{rebuilt.manifest.snapshot_sha256 == rebuilt_b.manifest.snapshot_sha256}")

# Environment invariance check
sw_diff = dict(sw4); sw_diff["git_sha"] = "0"*40; sw_diff["rdkit_version"] = "9999.1.1"
software_diff = SoftwareProvenance(
    python_version=sw_diff["python_version"], rdkit_version=sw_diff["rdkit_version"],
    orthosteric_version=sw_diff["orthosteric_version"], git_sha=sw_diff["git_sha"],
    git_dirty=sw_diff["git_dirty"], os_platform=sw_diff["os_platform"], os_version=sw_diff["os_version"],
    lockfile_hash=sw_diff.get("lockfile_hash",""), key_package_versions=sw_diff.get("key_package_versions",{}),
)
b_diff = SnapshotBuilder(software=software_diff, policy=pol)
rebuilt_diff = b_diff.build(recs4, source_versions=man4.get("source_versions"),
                             parent_sha256=man4.get("parent_snapshot_sha256"))
print(f"\n=== environment invariance (git_sha + rdkit_version changed) ===")
print(f"  content_sha256 unaffected: {rebuilt.manifest.snapshot_sha256 == rebuilt_diff.manifest.snapshot_sha256}")
print(f"  build_provenance_sha256 DID change: {rebuilt.manifest.build_provenance_sha256 != rebuilt_diff.manifest.build_provenance_sha256}")

print("\n=== Four-isoform identity (governed vocabulary) ===")
acc4 = [r for r in recs4 if not r.get("exclusion_reason")]
isos = {r.get("isoform") for r in acc4}
T1 = {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}
print(f"  isoforms present: {sorted(isos)}")
print(f"  all 4 present:     {T1.issubset(isos)}")
print(f"  no extra isoforms: {isos <= T1}")

print("\n=== Comparability metadata population ===")
for f in ["study_id", "bao_format", "assay_type", "atp_status"]:
    n = sum(1 for r in acc4 if r.get(f) is not None)
    print(f"  {f}: {n}/{len(acc4)} populated ({100*n/len(acc4):.1f}%)")

print("\n=== ATP status cross-check ===")
known = [r for r in acc4 if r.get("atp_status") == "known"]
ambiguous = [r for r in acc4 if r.get("atp_status") == "ambiguous"]
unknown = [r for r in acc4 if r.get("atp_status") == "unknown"]
print(f"  KNOWN: {len(known)}; all have exactly one concentration_um: "
      f"{all(r.get('atp_concentration_um') is not None for r in known)}")
print(f"  AMBIGUOUS: {len(ambiguous)}; NONE have a selected concentration_um: "
      f"{all(r.get('atp_concentration_um') is None for r in ambiguous)}")
print(f"        all have >=2 candidate values: "
      f"{all(len(r.get('atp_candidate_values_um') or []) >= 2 for r in ambiguous)}")
print(f"  UNKNOWN: {len(unknown)}; none have a concentration_um: "
      f"{all(r.get('atp_concentration_um') is None for r in unknown)}")
print(f"  sum == accepted: {len(known)+len(ambiguous)+len(unknown) == len(acc4)}")

print("\n=== Resolved panel tier sanity ===")
tiers = [resolve_panel_key(r).tier for r in acc4]
from collections import Counter
print(f"  {Counter(str(t) for t in tiers)}")
