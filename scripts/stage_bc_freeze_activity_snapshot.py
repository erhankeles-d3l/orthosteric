#!/usr/bin/env python3
"""Stage B+C — harmonize raw ChEMBL records and freeze Activity Snapshot A1.

Reads raw JSON pages from data/raw/chembl/, runs the existing harmonization
pipeline, and produces an immutable Activity Snapshot using the SCI0-011
SnapshotBuilder.

Governance notes
----------------
- Activity-first sampling: records come from the acquisition defined in
  stage0_acquire.py and ADR-0011. No structural selection bias is introduced.
- All four Class I isoforms present: PIK3CA (CHEMBL4005), PIK3CB (CHEMBL3145),
  PIK3CG (CHEMBL3267), PIK3CD (CHEMBL3130).
- Lineage: parent_snapshot_sha256 = None. Snapshot A0 was VOIDED by ADR-0013
  (in-place mutation of a frozen snapshot); the lineage does not begin at A0.
- Snapshot identity is environment-dependent pending GDR-010 (DRAFT).
- Data mode: SCIENTIFIC_CORPUS throughout.
- Snapshot is immutable after freeze(); subsequent acquisitions produce a new
  snapshot with parent_sha pointing to this one.

Outputs
-------
data/snapshots/activity_snapshot_A1/
    manifest.json          — SnapshotManifestV2 (content-hashed)
    records.json.gz        — all records (accepted + excluded)
    characterization.json  — per-target/study/compound summary
"""

from __future__ import annotations

import gzip
import json
import pathlib
import platform
import subprocess
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from rdkit import __version__ as rdkit_ver

from orthosteric.data.corpus_lifecycle import CorpusDataMode, CurrentCorpus
from orthosteric.data.harmonization._chem_standardizer import (
    ChemicalStandardizer,
    StandardizationStatus,
)
from orthosteric.data.harmonization._scaffold import ScaffoldAssigner
from orthosteric.data.snapshots._builder import SnapshotBuilder
from orthosteric.data.snapshots._manifest import PolicyManifest, SoftwareProvenance
from orthosteric.data.sources._base import Admissibility
from orthosteric.data.sources._chembl import _parse_activity
from orthosteric.data.sources.structural._isoform_map import PI3K_GENE_MAP

#: Authoritative gene-symbol -> canonical isoform designation, derived from
#: PI3K_GENE_MAP (SCI0-007) so this script cannot drift from the single source
#: of truth.  The `isoform` field MUST carry the canonical designation
#: ("PI3Kalpha"), not the gene symbol ("PIK3CA"), because graph.py, strata.py
#: and _residue_mapping.py all key on it.
GENE_TO_ISOFORM: dict[str, str] = {gene: iso.value for iso, gene in PI3K_GENE_MAP.items()}

RAW_DIR = pathlib.Path("data/raw/chembl")
SNAP_DIR = pathlib.Path("data/snapshots/activity_snapshot_A3")
SNAP_DIR.mkdir(parents=True, exist_ok=True)

# ── Provenance ─────────────────────────────────────────────────────────────────

CHEMBL_VERSION = "ChEMBL_37"
RETRIEVAL_TS = "2026-08-06T12:00:00Z"  # approximate; actual timestamps in raw pages

TARGETS = {
    "CHEMBL4005": "PIK3CA",  # confirmed ChEMBL 37 (ADR-0012)
    "CHEMBL3145": "PIK3CB",  # confirmed ChEMBL 37 (ADR-0011)
    "CHEMBL3267": "PIK3CG",  # confirmed ChEMBL 37 (ADR-0011)
    "CHEMBL3130": "PIK3CD",  # confirmed ChEMBL 37 (ADR-0012)
}


def _software() -> SoftwareProvenance:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except Exception:
        sha, dirty = "unknown", False

    return SoftwareProvenance(
        python_version=sys.version.split()[0],
        rdkit_version=rdkit_ver,
        orthosteric_version="0.1.0",
        git_sha=sha,
        git_dirty=dirty,
        os_platform=platform.system(),
        os_version=platform.release(),
        lockfile_hash="",
        key_package_versions={"rdkit": rdkit_ver},
    )


def _policy() -> PolicyManifest:
    return PolicyManifest(
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


# ── Load raw pages ─────────────────────────────────────────────────────────────


def load_raw_records() -> list[dict]:
    """Load all raw activity records from downloaded JSON pages."""
    all_recs = []
    for tid, gene in TARGETS.items():
        pages = sorted((RAW_DIR / tid / "IC50").glob("page_*.json"))
        for p in pages:
            d = json.loads(p.read_text())
            for act in d.get("activities", []):
                act["_source_chembl_target_id"] = tid
                act["_gene"] = gene
                all_recs.append(act)
    print(f"Loaded {len(all_recs)} raw records from {len(TARGETS)} targets")
    return all_recs


# ── Parse + harmonize ─────────────────────────────────────────────────────────


def harmonize_records(raw_activities: list[dict]) -> list[dict]:
    """Parse raw ChEMBL activities into harmonized snapshot dicts.

    Returns a list of dicts suitable for SnapshotBuilder.build().
    Each dict retains full provenance and is not filtered — exclusions are
    marked with exclusion_reason, not discarded.
    """
    cs = ChemicalStandardizer()
    sa = ScaffoldAssigner()  # SCI0-012 Bemis-Murcko
    records = []
    stats = Counter()

    for act in raw_activities:
        tid = act["_source_chembl_target_id"]
        gene = act["_gene"]
        ts = act.get("_retrieval_ts", RETRIEVAL_TS)

        # 1. Parse to RawSourceRecord
        raw = _parse_activity(act, tid, CHEMBL_VERSION, ts)

        base = {
            "source_db": raw.source_db,
            "source_record_id": raw.source_record_id,
            "source_version": raw.source_version,
            "retrieval_timestamp": raw.retrieval_timestamp,
            "target_chembl_id": tid,
            "gene": gene,
            "isoform": GENE_TO_ISOFORM[gene],  # canonical designation (SCI0-007)
            "compound_id": raw.compound_id,  # molecule_chembl_id
            "parent_molecule_chembl_id": act.get("parent_molecule_chembl_id"),
            "smiles_raw": raw.smiles,
            "activity_type": raw.activity_type,
            "activity_value": raw.activity_value,
            "activity_units": raw.activity_units,
            "activity_relation": raw.activity_relation,
            "pchembl_value": act.get("pchembl_value"),
            "assay_id": raw.assay_id,
            "assay_type": raw.assay_type,
            "record_type": "activity",  # SnapshotBuilder sort key
            # study_id: the within-study grouping unit.  A ChEMBL *document*
            # is the study: within-document assay panels share protocol and
            # ATP concentration, which is what Constitution 2.3 requires for
            # a comparable selectivity ratio.
            "study_id": act.get("document_chembl_id"),
            "document_chembl_id": act.get("document_chembl_id"),
            "document_year": act.get("document_year"),
            "atp_concentration_um": raw.atp_concentration_um,
            "organism": raw.organism,
            "publication_id": raw.publication_id,
            # governance fields
            "conflict_status": "ok",
            "censoring": "exact",
            "exclusion_reason": None,
        }

        # 2. Handle inadmissible raw records
        if raw.admissibility == Admissibility.INADMISSIBLE:
            base["exclusion_reason"] = raw.inadmissibility_reason or "INADMISSIBLE"
            stats["inadmissible"] += 1
            records.append(base)
            continue

        # 3. Chemical standardization
        if raw.smiles:
            std = cs.standardize(raw.smiles)
            if std.status == StandardizationStatus.OK:
                base["canonical_smiles"] = std.canonical_smiles
                base["inchikey"] = std.inchikey
                stats["standardized_ok"] += 1
                # SCI0-012 Bemis-Murcko scaffold family (required by graph.py,
                # audit.py; drives scaffold-aware splitting per GDR-009).
                sc = sa.assign(std.inchikey, std.canonical_smiles)
                base["scaffold_family_id"] = sc.scaffold_family_id
                base["scaffold_status"] = str(sc.status)
                base["scaffold_smiles"] = sc.scaffold_smiles
                stats[f"scaffold_{sc.status}"] += 1
            else:
                base["canonical_smiles"] = None
                base["inchikey"] = None
                base["scaffold_family_id"] = None
                base["scaffold_status"] = None
                base["scaffold_smiles"] = None
                base["exclusion_reason"] = f"STANDARDIZATION_FAILED:{std.status}"
                stats["standardization_failed"] += 1
        else:
            base["canonical_smiles"] = None
            base["inchikey"] = None
            base["scaffold_family_id"] = None
            base["scaffold_status"] = None
            base["scaffold_smiles"] = None
            base["exclusion_reason"] = "NO_STRUCTURE"
            stats["no_structure"] += 1

        # 4. Censoring classification
        relation = (raw.activity_relation or "=").strip()
        if relation in {">", ">="}:
            base["censoring"] = "right"  # inactive / right-censored
        elif relation in {"<", "<="}:
            base["censoring"] = "left"  # very potent / left-censored
        else:
            base["censoring"] = "exact"

        stats["accepted" if not base["exclusion_reason"] else "excluded"] += 1
        records.append(base)

    print(f"\nHarmonization stats: {dict(stats)}")
    return records


# ── Characterization ───────────────────────────────────────────────────────────


def characterize(records: list[dict]) -> dict:
    """Produce a characterization summary for governance assessment."""
    accepted = [r for r in records if not r.get("exclusion_reason")]

    # Per-isoform
    per_gene = Counter(r.get("isoform") for r in accepted)

    # Within-study (same document_chembl_id, same compound, two isoforms)
    # Group accepted by (document_chembl_id, compound_id)
    doc_compound = defaultdict(set)
    for r in accepted:
        doc = r.get("document_chembl_id", "")
        cmpd = r.get("compound_id", "")
        iso = r.get("isoform", "")
        if doc and cmpd and iso:
            doc_compound[(doc, cmpd)].add(iso)

    n_iso_hist = Counter(len(genes) for genes in doc_compound.values())
    within_study_all4 = n_iso_hist.get(4, 0)
    within_study_ge2 = sum(v for k, v in n_iso_hist.items() if k >= 2)

    # Replicates: same compound_id x assay_id, multiple records in same doc
    replicate_groups = defaultdict(list)
    for r in accepted:
        key = (
            r.get("document_chembl_id", ""),
            r.get("compound_id", ""),
            r.get("assay_id", ""),
            r.get("isoform", ""),
        )
        replicate_groups[key].append(r.get("activity_value"))
    rep_group_count = sum(1 for v in replicate_groups.values() if len(v) > 1)

    # Documents
    docs = Counter(r.get("document_chembl_id", "") for r in accepted if r.get("document_chembl_id"))

    # Compounds
    compounds = Counter(r.get("inchikey", "") for r in accepted if r.get("inchikey"))

    # Censoring
    censoring = Counter(r.get("censoring", "exact") for r in accepted)

    return {
        "total_records": len(records),
        "accepted_records": len(accepted),
        "excluded_records": len(records) - len(accepted),
        "per_isoform": dict(per_gene),
        "unique_inchikeys": len(compounds),
        "unique_documents": len(docs),
        "within_study_all4_isoforms": within_study_all4,
        "within_study_ge2_isoforms": within_study_ge2,
        "within_study_isoform_count_histogram": dict(sorted(n_iso_hist.items())),
        "replicate_groups": rep_group_count,
        "censoring_distribution": dict(censoring),
        "top_10_documents_by_records": docs.most_common(10),
    }


# ── Main ────────────────────────────────────────────────────────────────────────


def main() -> None:
    print("=== Stage B+C: Activity Snapshot A3 ===\n")

    # Load
    raw = load_raw_records()

    # Harmonize
    print("\nHarmonizing...")
    records = harmonize_records(raw)

    # Characterize (before freeze — for reporting)
    print("\nCharacterizing...")
    char = characterize(records)

    # Freeze
    print("\nFreezing Activity Snapshot A3...")
    cc = CurrentCorpus(data_mode=CorpusDataMode.SCIENTIFIC_CORPUS)
    cc.add_records(records)
    cc.update_source_version("chembl", CHEMBL_VERSION)
    cc.update_source_version("chembl_targets", "_".join(sorted(TARGETS)))

    # Lineage: A2 descends from A1.  A1's `isoform` field carried gene symbols
    # ("PIK3CA") rather than the canonical designation ("PI3Kalpha") required by
    # graph.py / strata.py / _residue_mapping.py, which produced
    # compounds_all4_isoforms = 0.  A2 corrects the vocabulary.
    # A1 is NOT mutated — correction proceeds by re-freeze, per ADR-0013.
    parent_sha = "e6acd7a37a40f7d167ce11220cb2661deafab380cda95aef7c2e59e55d673583"

    builder = SnapshotBuilder(software=_software(), policy=_policy())
    snapshot = cc.freeze(builder, parent_snapshot_sha256=parent_sha)

    sha = snapshot.manifest.snapshot_sha256
    print(f"\nSnapshot SHA-256: {sha}")
    print(f"Snapshot ID:     {snapshot.manifest.snapshot_id}")
    print(f"Record count:    {snapshot.manifest.record_count}")
    print(f"Accepted:        {snapshot.manifest.accepted_count}")
    print(f"Excluded:        {snapshot.manifest.excluded_count}")
    print(f"Censored:        {snapshot.manifest.censored_count}")

    # Write manifest
    manifest_dict = snapshot.manifest.to_dict()
    manifest_dict["data_mode"] = CorpusDataMode.SCIENTIFIC_CORPUS.value
    (SNAP_DIR / "manifest.json").write_text(json.dumps(manifest_dict, indent=2))

    # Write records (gzip for size)
    with gzip.open(SNAP_DIR / "records.json.gz", "wt", encoding="utf-8") as f:
        json.dump(list(snapshot.records), f, separators=(",", ":"))
    print(f"\nWrote records to {SNAP_DIR / 'records.json.gz'}")

    # Write characterization
    char["snapshot_sha256"] = sha
    char["snapshot_id"] = snapshot.manifest.snapshot_id
    char["chembl_version"] = CHEMBL_VERSION
    char["targets_acquired"] = list(TARGETS.keys())
    char["voided_predecessor"] = "SNAP-2b8f5ce6f236 (A0) - VOID per ADR-0013"
    (SNAP_DIR / "characterization.json").write_text(json.dumps(char, indent=2))

    print("\n=== Characterization ===")
    print(
        json.dumps({k: v for k, v in char.items() if k != "top_10_documents_by_records"}, indent=2)
    )
    print("\nTop 10 documents by record count:")
    for doc, cnt in char.get("top_10_documents_by_records", []):
        print(f"  {doc}: {cnt}")

    print("\n=== Snapshot A1 frozen ===")
    print(f"Output directory: {SNAP_DIR.resolve()}")
    print(f"SHA-256: {sha}")


if __name__ == "__main__":
    main()
