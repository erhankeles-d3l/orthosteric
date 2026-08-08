#!/usr/bin/env python3
"""Stage B+C — harmonize raw ChEMBL records and freeze Activity Snapshot A4.

Reads raw JSON pages from data/raw/chembl/, runs the existing harmonization
pipeline, and produces an immutable Activity Snapshot using the SCI0-011
SnapshotBuilder.

Governance notes
----------------
- Activity-first sampling: records come from the acquisition defined in
  stage0_acquire.py and ADR-0011. No structural selection bias is introduced.
- All four Class I isoforms present: PIK3CA (CHEMBL4005), PIK3CB (CHEMBL3145),
  PIK3CG (CHEMBL3267), PIK3CD (CHEMBL3130).
- Lineage: A0 VOID (ADR-0013) -> A1 -> A2 -> A3 -> A4 (this snapshot).
  parent_snapshot_sha256 = A3's content_sha256.  A3's records, manifest,
  characterization and lifecycle_result are NOT modified by this script.
- Snapshot identity: GDR-010 (accepted, Option A).  snapshot_sha256 is now
  content_sha256 (records minus retrieval_timestamp, + policy); it is
  invariant to software/environment.  build_provenance_sha256 is recorded
  separately and is NOT identity-defining.
- Comparability unit: GDR-011 (accepted, Option D).  Records carry
  bao_format and assay_type so graph.py/strata.py resolve panels via
  orthosteric.data.comparability.resolve_panel_key() to the C1_PRIMARY
  tier, not the rejected (study_id, assay_id) LEGACY_FALLBACK.
- ATP status: GDR-011 (accepted, Issue 2).  Every record carries
  atp_status in {known, ambiguous, unknown} via
  orthosteric.data.harmonization._atp_extraction, PROVISIONAL pending
  governance of the multi-value extraction ambiguity.  ATP is a covariate,
  never part of the primary comparability key.
- Data mode: SCIENTIFIC_CORPUS throughout.
- Snapshot is immutable after freeze(); subsequent acquisitions produce a new
  snapshot with parent_sha pointing to this one.

Outputs
-------
data/snapshots/activity_snapshot_A4/
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

from orthosteric.data.comparability import PanelKeyTier, resolve_panel_key
from orthosteric.data.corpus_lifecycle import CorpusDataMode, CurrentCorpus
from orthosteric.data.harmonization._atp_extraction import extract_atp_status
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
SNAP_DIR = pathlib.Path("data/snapshots/activity_snapshot_A4")
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
            # bao_format: raw ChEMBL field, not parsed by _chembl.py's
            # RawSourceRecord.  Required, with assay_type, for the GDR-011
            # (accepted, Option D) comparability unit (study_id, bao_format,
            # assay_type).  Read directly from the raw payload -- never
            # invented if absent.
            "bao_format": act.get("bao_format"),
            "record_type": "activity",  # SnapshotBuilder sort key
            # study_id: the within-study grouping unit.  A ChEMBL *document*
            # is the study: within-document assay panels share protocol and
            # ATP concentration, which is what Constitution 2.3 requires for
            # a comparable selectivity ratio.
            "study_id": act.get("document_chembl_id"),
            "document_chembl_id": act.get("document_chembl_id"),
            "document_year": act.get("document_year"),
            "organism": raw.organism,
            "publication_id": raw.publication_id,
            # governance fields
            "conflict_status": "ok",
            "censoring": "exact",
            "exclusion_reason": None,
        }

        # 1b. ATP-status extraction (GDR-011, accepted, Issue 2).
        # PROVISIONAL: from free-text assay_description; KNOWN/AMBIGUOUS/
        # UNKNOWN per orthosteric.data.harmonization._atp_extraction.  Never
        # first-match-resolved; AMBIGUOUS retains its candidates, never a
        # selected concentration.  Applied regardless of admissibility so
        # the field is present and auditable on every record.
        atp = extract_atp_status(act.get("assay_description"))
        base["atp_status"] = str(atp.status)
        base["atp_concentration_um"] = atp.concentration_um
        base["atp_candidate_values_um"] = list(atp.candidate_values_um)

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
    """Produce a characterization summary for governance assessment.

    Comparability metrics use `orthosteric.data.comparability.
    resolve_panel_key()` (GDR-011, accepted, Option D) — panels are
    (study_id, bao_format, assay_type), NOT the rejected document-only or
    (study_id, assay_id) definitions.  LEGACY_FALLBACK panels are counted
    separately and excluded from every "C1" / "complete" figure.
    """
    accepted = [r for r in records if not r.get("exclusion_reason")]
    t1 = {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}

    # Per-isoform
    per_gene = Counter(r.get("isoform") for r in accepted)

    # ── Comparability (GDR-011, Option D) ────────────────────────────────
    panel_iso: dict[tuple, set] = defaultdict(set)
    panel_tier: dict[tuple, str] = {}
    panel_cmpd_iso: dict[tuple, dict] = defaultdict(lambda: defaultdict(set))
    legacy_fallback_records = 0
    for r in accepted:
        resolved = resolve_panel_key(r)
        key = resolved.key
        panel_iso[key].add(r.get("isoform"))
        panel_tier[key] = str(resolved.tier)
        if not resolved.is_scientific_evidence:
            legacy_fallback_records += 1
        ik = r.get("inchikey")
        if ik:
            panel_cmpd_iso[key][ik].add(r.get("isoform"))

    c1_panels = [k for k, t in panel_tier.items() if t == str(PanelKeyTier.C1_PRIMARY)]
    c1_four_iso_panels = [k for k in c1_panels if t1.issubset(panel_iso[k])]
    c1_complete_compounds: set = set()
    for k in c1_four_iso_panels:
        for ik, isos in panel_cmpd_iso[k].items():
            if t1.issubset(isos):
                c1_complete_compounds.add(ik)

    # ── ATP status (GDR-011, Issue 2 — covariate, never mandatory) ──────
    atp_status_counts = Counter(r.get("atp_status", "unknown") for r in accepted)

    # ── Scaffold families ────────────────────────────────────────────────
    scaffold_families = {
        r.get("scaffold_family_id") for r in accepted if r.get("scaffold_family_id")
    }

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

    n = len(accepted) or 1
    return {
        "total_records": len(records),
        "accepted_records": len(accepted),
        "excluded_records": len(records) - len(accepted),
        "per_isoform": dict(per_gene),
        "unique_inchikeys": len(compounds),
        "unique_documents": len(docs),
        "unique_scaffold_families": len(scaffold_families),
        # GDR-011 Option D comparability (replaces prior document-only metric)
        "c1_panels": len(c1_panels),
        "c1_four_isoform_panels": len(c1_four_iso_panels),
        "c1_complete_compounds": len(c1_complete_compounds),
        "legacy_fallback_records": legacy_fallback_records,
        "legacy_fallback_pct": round(100 * legacy_fallback_records / n, 3),
        # GDR-011 Issue 2 ATP status (covariate; not mandatory)
        "atp_status_counts": dict(atp_status_counts),
        "atp_status_pct": {k: round(100 * v / n, 2) for k, v in atp_status_counts.items()},
        "replicate_groups": rep_group_count,
        "censoring_distribution": dict(censoring),
        "top_10_documents_by_records": docs.most_common(10),
    }


# ── Main ────────────────────────────────────────────────────────────────────────


def main() -> None:
    print("=== Stage B+C: Activity Snapshot A4 ===\n")

    # Load
    raw = load_raw_records()

    # Harmonize
    print("\nHarmonizing...")
    records = harmonize_records(raw)

    # Characterize (before freeze — for reporting)
    print("\nCharacterizing...")
    char = characterize(records)

    # Freeze
    print("\nFreezing Activity Snapshot A4...")
    cc = CurrentCorpus(data_mode=CorpusDataMode.SCIENTIFIC_CORPUS)
    cc.add_records(records)
    cc.update_source_version("chembl", CHEMBL_VERSION)
    cc.update_source_version("chembl_targets", "_".join(sorted(TARGETS)))

    # Lineage: A4 descends from A3.  A3 is NOT mutated — correction proceeds
    # by re-freeze, per ADR-0013.  A4 implements the Project-Owner-approved
    # GDR-010 (content/build-provenance hash split) and GDR-011 (Option D
    # comparability unit; ATP as covariate) decisions on top of A3's
    # already-correct isoform vocabulary and scaffold assignment.
    # parent_sha is A3's SNAPSHOT_SHA256 AS RECORDED IN A3'S OWN MANIFEST —
    # i.e. computed under the hashing scheme in effect when A3 was frozen
    # (pre-GDR-010).  This is deliberate: lineage records history as it
    # actually happened, not as it would look under the current scheme.
    parent_sha = "5e5e54cb5590da829aaccbd7e121d4197d38f1de9923799b8eec8a0296b171da"  # A3

    builder = SnapshotBuilder(software=_software(), policy=_policy())
    snapshot = cc.freeze(builder, parent_snapshot_sha256=parent_sha)

    sha = snapshot.manifest.snapshot_sha256
    build_sha = snapshot.manifest.build_provenance_sha256
    print(f"\nSnapshot content_sha256 (scientific identity): {sha}")
    print(f"Snapshot build_provenance_sha256 (NOT identity): {build_sha}")
    print(f"Snapshot ID:     {snapshot.manifest.snapshot_id}")
    print(f"Parent SHA:      {snapshot.manifest.parent_snapshot_sha256}")
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
    char["build_provenance_sha256"] = build_sha
    char["parent_snapshot_sha256"] = snapshot.manifest.parent_snapshot_sha256
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

    print("\n=== Snapshot A4 frozen ===")
    print(f"Output directory: {SNAP_DIR.resolve()}")
    print(f"content_sha256: {sha}")


if __name__ == "__main__":
    main()
