"""Stage C, Step 2 -- Build the candidate pool and apply exclusions, in
the exact frozen order, before anything is inspected.

seal literature compounds + scaffolds (already done, Step 1)
  -> build candidate pool from A4
  -> exclude 24/50 compounds + scaffolds
  -> exclude literature compounds + scaffolds
  -> freeze validation structures + labels as two separate artifacts
  -> hash both
  -> ONLY NOW inspect class/scaffold composition (done in a SEPARATE
     script, deliberately, so this script cannot see composition while
     still capable of excluding anything).

Two physically separate artifacts, per the frozen revision:
  sealed_validation_structures.json -- compound_id, SMILES, isoform
    panel identifiers. Freely readable by discovery-phase code (it
    needs structures to dock).
  sealed_validation_labels.json -- compound_id, selectivity label.
    Reachable ONLY through the orthosteric.data.sealed_labels guard
    (architectural barrier, Contract 5) -- discovery-phase code must
    never import the module this lives behind.

Within-study, within-assay four-isoform panel, per charter SS2.3: a
compound qualifies if there exists a single study_id under which it has
ACCEPTED records (conflict_status == "ok", exclusion_reason is None)
covering all four isoforms.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence")
SNAPSHOT_PATH = Path("/home/ubuntu/Documents/orthosteric/data/snapshots/activity_snapshot_A4/records.json.gz")
SEALED_LABELS_DIR = Path("/home/ubuntu/Documents/orthosteric/data/sealed")
SEALED_LABELS_DIR.mkdir(exist_ok=True)

REQUIRED_ISOFORMS = {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}

print("=== Stage C Step 2: candidate pool + exclusions (frozen order) ===\n")

# --- Step: literature compounds + scaffolds (already sealed, Step 1) ---
lit_panel = json.loads((DATA_DIR / "sealed_literature_panel.json").read_text())
excluded_lit_inchikeys = set(lit_panel["excluded_compound_inchikeys"])
excluded_lit_scaffolds = set(lit_panel["excluded_scaffold_inchikeys"])
print(f"Literature panel: {len(excluded_lit_inchikeys)} compounds, {len(excluded_lit_scaffolds)} scaffolds")

# --- Step: build candidate pool from A4 ---
print(f"\nLoading A4 from {SNAPSHOT_PATH} ...")
with gzip.open(SNAPSHOT_PATH) as f:
    records = json.load(f)
print(f"A4 total records: {len(records)}")

accepted = [r for r in records if r.get("conflict_status") == "ok" and r.get("exclusion_reason") is None]
print(f"Accepted records (conflict_status=ok, no exclusion_reason): {len(accepted)}")

# Group by (compound inchikey, study_id) -> set of isoforms present
by_compound_study: dict[tuple[str, str], set[str]] = defaultdict(set)
compound_smiles: dict[str, str] = {}
compound_scaffold: dict[str, str] = {}
for r in accepted:
    key = (r["inchikey"], r["study_id"])
    by_compound_study[key].add(r["isoform"])
    compound_smiles[r["inchikey"]] = r["canonical_smiles"]
    compound_scaffold[r["inchikey"]] = r["scaffold_family_id"]

qualifying_compounds: set[str] = set()
for (inchikey, study_id), isoforms in by_compound_study.items():
    if REQUIRED_ISOFORMS.issubset(isoforms):
        qualifying_compounds.add(inchikey)

print(f"Compounds with a within-study four-isoform panel (candidate pool): {len(qualifying_compounds)}")

# --- Step: exclude 24/50 compounds + scaffolds ---
corpus_24 = json.loads((DATA_DIR / "production_pilot_compound_selection.json").read_text())
corpus_50 = json.loads((DATA_DIR / "expanded_pilot_compound_selection.json").read_text())
excluded_corpus_inchikeys = {c["compound_id"] for c in corpus_24} | {c["compound_id"] for c in corpus_50}
excluded_corpus_scaffolds = {c["scaffold_family_id"] for c in corpus_24} | {c["scaffold_family_id"] for c in corpus_50}
print(f"\n24/50 corpora: {len(excluded_corpus_inchikeys)} compounds, {len(excluded_corpus_scaffolds)} scaffolds to exclude")

after_corpus_exclusion = {
    ik
    for ik in qualifying_compounds
    if ik not in excluded_corpus_inchikeys and compound_scaffold.get(ik) not in excluded_corpus_scaffolds
}
print(f"After excluding 24/50 compounds+scaffolds: {len(after_corpus_exclusion)} remain")

# --- Step: exclude literature compounds + scaffolds ---
final_sealed_set = {
    ik
    for ik in after_corpus_exclusion
    if ik not in excluded_lit_inchikeys and compound_scaffold.get(ik) not in excluded_lit_scaffolds
}
print(f"After excluding literature-panel compounds+scaffolds: {len(final_sealed_set)} remain")
print("\n>>> No step after this point may add or remove a compound. <<<")

# --- Step: freeze validation structures + labels as TWO SEPARATE artifacts ---
# Need per-compound isoform panel data (pAct per isoform) for the labels
# artifact, and the label class itself. Compute pAct_alpha and log-ratio
# vs other isoforms per compound, from the SAME accepted records, exactly
# analogous to the 24/50 corpora's own stratum fields -- but this is
# LABEL information and goes in the labels artifact only.
def isoform_pact(records_for_compound: list[dict], isoform: str) -> float | None:
    vals = [
        float(r["pchembl_value"])
        for r in records_for_compound
        if r["isoform"] == isoform and r.get("pchembl_value") not in (None, "")
    ]
    return sum(vals) / len(vals) if vals else None


by_compound_all: dict[str, list[dict]] = defaultdict(list)
for r in accepted:
    if r["inchikey"] in final_sealed_set:
        by_compound_all[r["inchikey"]].append(r)

structures = []
labels = []
for ik in sorted(final_sealed_set):
    recs = by_compound_all[ik]
    structures.append(
        {
            "compound_id": ik,
            "smiles": compound_smiles[ik],
            "scaffold_family_id": compound_scaffold[ik],
            "isoforms_present": sorted({r["isoform"] for r in recs}),
        }
    )
    pact = {iso: isoform_pact(recs, iso) for iso in REQUIRED_ISOFORMS}
    if pact["PI3Kalpha"] is None or any(v is None for v in pact.values()):
        stratum = "indeterminate_missing_pact"
    else:
        others = [pact[i] for i in REQUIRED_ISOFORMS if i != "PI3Kalpha"]
        min_other = min(others)
        max_other = max(others)
        if pact["PI3Kalpha"] - max_other >= 1.0:
            stratum = "alpha_selective"
        elif min_other - pact["PI3Kalpha"] >= 1.0:
            stratum = "other_selective"
        elif max(pact.values()) - min(pact.values()) <= 0.5:
            stratum = "non_selective"
        else:
            stratum = "intermediate"
    labels.append({"compound_id": ik, "pact_by_isoform": pact, "stratum": stratum})

timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

structures_artifact = {
    "artifact": "sealed_validation_structures",
    "sealed_timestamp_utc": timestamp,
    "n_compounds": len(structures),
    "a4_snapshot_id": "SNAP-05748f6627ea",
    "exclusions_applied_in_order": [
        "literature_panel_compounds_and_scaffolds",
        "candidate_pool_built_from_a4",
        "corpus_24_50_compounds_and_scaffolds",
        "literature_panel_compounds_and_scaffolds_reapplied",
    ],
    "structures": structures,
}
labels_artifact = {
    "artifact": "sealed_validation_labels",
    "sealed_timestamp_utc": timestamp,
    "n_compounds": len(labels),
    "a4_snapshot_id": "SNAP-05748f6627ea",
    "stratum_definition": (
        "alpha_selective: pAct_alpha - max(others) >= 1.0 log unit. "
        "other_selective: min(others) - pAct_alpha >= 1.0. "
        "non_selective: max-min across all four <= 0.5. intermediate: otherwise."
    ),
    "labels": labels,
}

structures_hash = hashlib.sha256(json.dumps(structures_artifact, sort_keys=True).encode()).hexdigest()
labels_hash = hashlib.sha256(json.dumps(labels_artifact, sort_keys=True).encode()).hexdigest()
structures_artifact["content_sha256"] = structures_hash
labels_artifact["content_sha256"] = labels_hash

structures_path = DATA_DIR / "sealed_validation_structures.json"
labels_path = SEALED_LABELS_DIR / "sealed_validation_labels.json"
structures_path.write_text(json.dumps(structures_artifact, indent=2))
labels_path.write_text(json.dumps(labels_artifact, indent=2))

print(f"\nWrote {structures_path} (sha256: {structures_hash})")
print(f"Wrote {labels_path} (sha256: {labels_hash})")
print(f"\nFinal sealed set size: {len(final_sealed_set)}")
print("Composition NOT yet inspected in this script -- that is a deliberately separate step.")
