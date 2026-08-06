"""ANALYSIS — validate every activity snapshot for internal self-consistency."""
import sys, json, gzip, pathlib
sys.path.insert(0,"src")
from orthosteric.data.snapshots._builder import SnapshotBuilder
from orthosteric.data.snapshots._manifest import PolicyManifest, SoftwareProvenance

POL=dict(chemical_standardization_policy="sci0008b_rdkit_canonical_v1",
    identifier_harmonization_policy="sci0008c_inchikey_v1",deduplication_policy="sci0009_log_median_v1",
    confidence_scoring_policy="sci0010_v1",adr0003_adjudication_procedure="adr0003_procedure_v1.0",
    alphafold_fallback_policy="sci0007_af_fallback_v1.0",auditor5_status="INSUFFICIENT_EVIDENCE_frozen",
    cheng_prusoff_status="BLOCKED/AUDITOR-5",within_group_conflict_threshold="RULE_MISSING/SCI0-016_required",
    confidence_assay_quality_rule="RULE_MISSING",confidence_lit_tier_rule="RULE_MISSING")
T1={"PI3Kalpha","PI3Kbeta","PI3Kgamma","PI3Kdelta"}

print(f"{'snapshot':<10}{'id':<20}{'recs':>7}{'cnt=man':>9}{'sha repro':>11}{'4 iso':>7}{'parent':<16} verdict")
print("-"*100)
for d in sorted(pathlib.Path("data/snapshots").iterdir()):
    if not d.is_dir(): continue
    mp,rp = d/"manifest.json", d/"records.json.gz"
    if not (mp.exists() and rp.exists()):
        print(f"{d.name:<10}INCOMPLETE"); continue
    man=json.loads(mp.read_text())
    with gzip.open(rp,"rt") as f: recs=json.load(f)
    cnt_ok = man["record_count"]==len(recs)
    sw=man["software"]
    b=SnapshotBuilder(software=SoftwareProvenance(
        python_version=sw["python_version"],rdkit_version=sw["rdkit_version"],
        orthosteric_version=sw["orthosteric_version"],git_sha=sw["git_sha"],git_dirty=sw["git_dirty"],
        os_platform=sw["os_platform"],os_version=sw["os_version"],
        lockfile_hash=sw.get("lockfile_hash",""),key_package_versions=sw.get("key_package_versions",{})),
        policy=PolicyManifest(**POL))
    try:
        re_sha=b.build(recs,source_versions=man.get("source_versions")).manifest.snapshot_sha256
        repro = re_sha==man["snapshot_sha256"]
    except Exception as e:
        repro=f"ERR"
    acc=[r for r in recs if not r.get("exclusion_reason")]
    isos={r.get("isoform") for r in acc}
    four = isos>=T1
    par=(man.get("parent_snapshot_sha256") or "none")[:12]
    verdict = "VALID" if (cnt_ok and repro is True) else "INVALID"
    if d.name.endswith("A0"): verdict += " (VOID per ADR-0013)"
    print(f"{d.name.replace('activity_snapshot_',''):<10}{man['snapshot_id']:<20}{len(recs):>7}"
          f"{str(cnt_ok):>9}{str(repro):>11}{str(four):>7} {par:<15} {verdict}")
