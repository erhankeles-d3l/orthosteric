import sys, json, gzip, pathlib, subprocess, platform
sys.path.insert(0, "src")
from orthosteric.data.corpus_lifecycle import CorpusDataMode
from orthosteric.data.snapshots._builder import SnapshotManifestV2, CorpusSnapshotV2
from orthosteric.data.snapshots._manifest import PolicyManifest, SoftwareProvenance
from orthosteric.data.graph import build_graph_stats_from_records
from orthosteric.data.audit import characterize
from orthosteric.data.strata import extract_strata
from orthosteric.data.snapshots._profile import freeze_corpus_profile
from orthosteric.policy._lifecycle_pipeline import CorpusLifecyclePipeline
from orthosteric.policy._corpus_gate import CorpusQualityGatePolicy
from orthosteric.quality._assessment import CorpusQualityAssessor
from orthosteric.quality._dimensions import (
    ConnectivityEvaluator, CoverageEvaluator, MissingnessEvaluator,
    PublicationConcentrationEvaluator, ScaffoldDiversityEvaluator,
    StructuralCoverageEvaluator, ConfidenceEvaluator)

A4 = pathlib.Path("data/snapshots/activity_snapshot_A4")
manifest = json.loads((A4/"manifest.json").read_text())
with gzip.open(A4/"records.json.gz","rt") as f: records = json.load(f)
sha = manifest["snapshot_sha256"]
accepted = [r for r in records if not r.get("exclusion_reason")]

policy = PolicyManifest(
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
    confidence_lit_tier_rule="RULE_MISSING")
d = manifest["software"]
sw = SoftwareProvenance(python_version=d["python_version"], rdkit_version=d["rdkit_version"],
    orthosteric_version=d["orthosteric_version"], git_sha=d["git_sha"], git_dirty=d["git_dirty"],
    os_platform=d["os_platform"], os_version=d["os_version"],
    lockfile_hash=d.get("lockfile_hash",""), key_package_versions=d.get("key_package_versions",{}))

gs = build_graph_stats_from_records(accepted)
print("=== Graph Stats -- A4 (GDR-011 Option D panel definition) ===")
print(f"  total_compounds:           {gs.total_compounds}")
print(f"  per_isoform:               {gs.per_isoform_compounds}")
print(f"  compounds >=2 isoforms:    {gs.compounds_ge2_isoforms}")
print(f"  compounds ALL 4 isoforms:  {gs.compounds_all4_isoforms}")
print(f"  largest_connected_comp:    {gs.largest_connected_component}")
print(f"  n_connected_components:    {gs.n_connected_components}")
print(f"  bridging_compounds:        {gs.bridging_compounds}")
print(f"  within_study_four_isoform: {gs.within_study_four_isoform}")
print(f"  n_four_isoform_clusters:   {gs.n_four_isoform_clusters}")
print(f"  scaffold_families:         {gs.scaffold_families}")
print(f"  legacy_fallback_records:   {gs.legacy_fallback_records}")

char = characterize(accepted, snapshot_sha256=sha)
strata = extract_strata(accepted)
print(f"\n=== StratumReport -- A4 ===")
print(f"  total_strata:              {strata.total_strata}")
print(f"  usable_strata:             {strata.usable_strata}")
print(f"  total_complete_compounds:  {strata.total_complete_compounds}")
print(f"  C1_PRIMARY strata:         {len(strata.c1_primary_strata())}")
c1_complete = sum(s.stratum_size for s in strata.c1_primary_strata())
print(f"  C1_PRIMARY complete compounds (sum over strata): {c1_complete}")

profile = freeze_corpus_profile(snapshot_sha256=sha, graph_stats=gs, characterization=char,
    software=sw, policy=policy, strata_report=strata)
ep = profile.engineering_parameters
print(f"\n=== Engineering Parameters -- A4 ===")
for f in ["n_c","n_b","n_w","n_complete_compounds","n_complete_strata",
          "n_connected_components","scaffold_families_in_largest_component"]:
    print(f"  {f}: {getattr(ep,f)}")

mo = SnapshotManifestV2(schema_version=manifest["schema_version"], snapshot_sha256=sha,
    build_provenance_sha256=manifest["build_provenance_sha256"],
    snapshot_id=manifest["snapshot_id"], parent_snapshot_sha256=manifest.get("parent_snapshot_sha256"),
    created_at_utc=manifest["created_at_utc"], record_count=manifest["record_count"],
    accepted_count=manifest["accepted_count"], excluded_count=manifest["excluded_count"],
    censored_count=manifest["censored_count"], unresolved_count=0, conflict_count=0,
    rule_missing_count=0, governance_exception_count=0, structural_records_total=0,
    structural_experimental_pdb=0, structural_alphafold_fallback=0, structural_inadmissible=0,
    source_versions=manifest["source_versions"], policy=policy, software=sw)
snap = CorpusSnapshotV2(manifest=mo, records=tuple(records))

pipeline = CorpusLifecyclePipeline(
    assessor=CorpusQualityAssessor([ConnectivityEvaluator(), CoverageEvaluator(),
        MissingnessEvaluator(), PublicationConcentrationEvaluator(), ScaffoldDiversityEvaluator(),
        StructuralCoverageEvaluator(), ConfidenceEvaluator()]),
    gate_policy=CorpusQualityGatePolicy())
res = pipeline.run(snap, CorpusDataMode.SCIENTIFIC_CORPUS, profile)

print(f"\n=== STAGE 0 GATE -- A4 ===")
print(f"  Gate:                  {res.gate_decision.status.value}")
print(f"  Eligible for training: {res.eligible_for_training}")
print(f"  Rationale:             {res.gate_decision.rationale}")
print(f"  Dimensions:")
for k,v in sorted(res.gate_decision.dimension_summary.items()): print(f"    {k}: {v}")

out = {"snapshot_sha256":res.snapshot_sha,"eligibility":res.eligibility.value,
  "gate_status":res.gate_decision.status.value,"gate_rationale":res.gate_decision.rationale,
  "eligible_for_training":res.eligible_for_training,"lifecycle_stage":res.lifecycle_stage.value,
  "dimension_summary":res.gate_decision.dimension_summary,"result_sha256":res.result_sha256,
  "engineering_params":{f:getattr(ep,f) for f in ["n_c","n_b","n_w","n_complete_compounds","n_complete_strata"]},
  "graph_stats":{"total_compounds":gs.total_compounds,"per_isoform":gs.per_isoform_compounds,
    "compounds_all4":gs.compounds_all4_isoforms,"within_study_four_isoform":gs.within_study_four_isoform,
    "largest_cc":gs.largest_connected_component,"n_components":gs.n_connected_components,
    "legacy_fallback_records":gs.legacy_fallback_records}}
(A4/"lifecycle_result.json").write_text(json.dumps(out, indent=2))
print(f"\nWrote lifecycle_result.json")
