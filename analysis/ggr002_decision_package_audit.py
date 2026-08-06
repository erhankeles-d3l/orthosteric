"""Read-only audit for the GGR-002a/002b Project Owner Decision Package.

Traces exactly what ggr_reassessment_a4.py computes, resolves the
2,500 vs 2,992 "complete compound" discrepancy, and surfaces implementation
details (multi-record cell collapse, assay_id homogeneity inside a C1
panel, censoring/pact interaction, ATP stratification) that the current
GGR-002a/002b numbers depend on but do not make visible.

No code is changed. No governance is invented. No A4 file is modified.
"""

import gzip
import json
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "src")
from orthosteric.data.comparability import resolve_panel_key
from orthosteric.data.graph import build_graph_stats_from_records
from orthosteric.data.strata import extract_strata

A4 = pathlib.Path("data/snapshots/activity_snapshot_A4")
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)
acc = [r for r in recs if not r.get("exclusion_reason")]
T1 = {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}


def pact(r):
    v = r.get("pchembl_value")
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════
print("=" * 78, "\n1. THE 2,500 vs 2,992 DISCREPANCY\n" + "=" * 78)

# (a) GraphStats.compounds_all4_isoforms -- global, uses activity_value presence
#     (any accepted record, ANY panel, isoform in {isoforms measured at all})
gs = build_graph_stats_from_records(acc)
print(
    f"GraphStats.compounds_all4_isoforms (global, activity_value-based, "
    f"'has ANY record in each of the 4 isoforms anywhere in the corpus'): "
    f"{gs.compounds_all4_isoforms}"
)

# (b) StratumReport.total_complete_compounds -- sum over ALL C1 strata of
#     stratum_size (compounds complete WITHIN that one stratum, activity_value-based)
strata = extract_strata(acc)
c1_strata = strata.c1_primary_strata()
print(
    f"StratumReport.total_complete_compounds (SUM over {len(c1_strata)} C1 "
    f"panels of per-panel complete-compound count, activity_value-based): "
    f"{strata.total_complete_compounds}"
)

# Panel membership per compound: how many DIFFERENT C1 panels is a given
# complete compound complete in?
panel_membership = defaultdict(int)
for s in c1_strata:
    for ik in s.complete_compounds:
        panel_membership[ik] += 1

unique_complete_via_strata = len(panel_membership)
memberships = list(panel_membership.values())
print(f"\nUnique compounds complete in >=1 C1 panel (via strata):  {unique_complete_via_strata}")
print(f"Sum of per-panel memberships (= StratumReport total):     {sum(memberships)}")
print(f"Mean panels-per-complete-compound:    {statistics.mean(memberships):.3f}")
print(f"Median panels-per-complete-compound:  {statistics.median(memberships)}")
print(f"Max panels-per-complete-compound:     {max(memberships)}")
dist = Counter(memberships)
print(f"Distribution (panels : n_compounds):  {dict(sorted(dist.items()))}")

print("\nRECONCILIATION:")
print(
    f"  activity_value-based unique-compound count (via strata):     {unique_complete_via_strata}"
)
print(
    f"  activity_value-based global GraphStats count:                 {gs.compounds_all4_isoforms}"
)
print(
    f"  activity_value-based panel-SUMMED count (StratumReport):      {strata.total_complete_compounds}"
)
diff_global_vs_strata_unique = gs.compounds_all4_isoforms - unique_complete_via_strata
print(f"  global vs strata-unique difference: {diff_global_vs_strata_unique}")
print("  (Expected nonzero: GraphStats counts a compound complete if it has >=1")
print("   record in each isoform ANYWHERE across ALL panels combined -- i.e. it")
print("   does NOT require the four measurements to come from the SAME panel.")
print("   StratumReport requires all four within ONE panel. A compound measured")
print("   in alpha in panel P1 and beta/gamma/delta in panel P2 counts toward")
print("   GraphStats's 2,500 but toward NEITHER panel's StratumReport count.)")

# ══════════════════════════════════════════════════════════════════════════
print(
    "\n" + "=" * 78,
    "\n2. pact() vs activity_value -- WHICH RECORDS DOES GGR-002a/b ACTUALLY USE?\n" + "=" * 78,
)

n_has_activity = sum(1 for r in acc if r.get("activity_value") is not None)
n_has_pact = sum(1 for r in acc if pact(r) is not None)
print(f"Accepted records with activity_value populated: {n_has_activity} / {len(acc)}")
print(f"Accepted records with pchembl_value populated:   {n_has_pact} / {len(acc)}")

cens_with_pact = Counter(r.get("censoring") for r in acc if pact(r) is not None)
cens_without_pact = Counter(
    r.get("censoring") for r in acc if pact(r) is None and r.get("activity_value") is not None
)
print(
    f"\nCensoring distribution AMONG records WITH a usable pact() value:    {dict(cens_with_pact)}"
)
print(
    f"Censoring distribution AMONG records WITH activity_value but NO pact(): {dict(cens_without_pact)}"
)
print("\n=> ggr_reassessment_a4.py's pact()-based analysis (GGR-002a AND GGR-002b)")
print("   silently excludes every record without a pchembl_value -- this is where")
print("   right/left-censored ChEMBL records are actually dropped, NOT via an")
print("   explicit 'exclude censored' step. This is conservative (never treats")
print("   censored as exact) but is an IMPLICIT exclusion, not a documented rule.")

# ══════════════════════════════════════════════════════════════════════════
print(
    "\n" + "=" * 78, "\n3. MULTI-RECORD PER CELL: IS THE 'LAST WRITER WINS' A PROBLEM?\n" + "=" * 78
)

cell_counts = defaultdict(list)
for r in acc:
    resolved = resolve_panel_key(r)
    if not resolved.is_scientific_evidence:
        continue
    p = pact(r)
    if p is None:
        continue
    ik = r.get("inchikey")
    if not ik:
        continue
    cell_counts[(resolved.key, ik, r.get("isoform"))].append(p)

multi_cell = {k: v for k, v in cell_counts.items() if len(v) >= 2}
print(
    f"(panel, compound, isoform) cells with >=2 pact-bearing records: {len(multi_cell)} "
    f"of {len(cell_counts)} total cells"
)
if multi_cell:
    spreads = [max(v) - min(v) for v in multi_cell.values()]
    print("  Of these, max-min spread > 0.3 pAct units (i.e. picking a different")
    print(
        f"  record would give a materially different value): "
        f"{sum(1 for s in spreads if s > 0.3)} / {len(multi_cell)}"
    )
    print(f"  This is EXACTLY the {len(multi_cell)}-cell subset of the 852 'replicate")
    print("  groups' reported by ggr_reassessment_a4.py's GGR-002a index -- but in")
    print("  ggr_reassessment_a4.py's GGR-002a pair-generation code, only ONE value")
    print("  (Python dict overwrite; last record iterated wins) is used, not a")
    print("  central-tendency aggregate. This means the 6,469 pair count and 2,578")
    print("  sign-flip count are NOT invariant to input record ORDER for these cells.")

# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 78, "\n4. DOES A C1 PANEL SPAN MULTIPLE CHEMBL assay_id VALUES?\n" + "=" * 78)

panel_assay_ids = defaultdict(set)
for r in acc:
    resolved = resolve_panel_key(r)
    if not resolved.is_scientific_evidence:
        continue
    panel_assay_ids[resolved.key].add(r.get("assay_id"))

n_single_assay = sum(1 for v in panel_assay_ids.values() if len(v) == 1)
n_multi_assay = sum(1 for v in panel_assay_ids.values() if len(v) > 1)
print(f"C1 panels backed by exactly 1 ChEMBL assay_id: {n_single_assay}")
print("C1 panels backed by >1 ChEMBL assay_id (i.e. the panel MERGES multiple")
print("  distinct ChEMBL assay records under one protocol signature -- this is")
print("  the entire point of GDR-011 Option D, but it also means a 'replicate'")
print("  within this panel may be two DIFFERENT physical assay instances, not")
print(f"  necessarily a true repeat measurement): {n_multi_assay}")

# For the 852 replicate groups specifically: how many span >1 assay_id?
rep_groups_assayid = defaultdict(set)
for r in acc:
    resolved = resolve_panel_key(r)
    if not resolved.is_scientific_evidence:
        continue
    p = pact(r)
    if p is None:
        continue
    ik = r.get("inchikey")
    if not ik:
        continue
    key = (resolved.key, ik, r.get("isoform"))
    rep_groups_assayid[key].add(r.get("assay_id"))
rep_multi_only = {k: v for k, v in rep_groups_assayid.items() if len(cell_counts.get(k, [])) >= 2}
single_assay_replicates = sum(1 for v in rep_multi_only.values() if len(v) == 1)
multi_assay_replicates = sum(1 for v in rep_multi_only.values() if len(v) > 1)
print(f"\nOf the {len(rep_multi_only)} replicate groups (n>=2 pact obs):")
print(
    f"  backed by a SINGLE ChEMBL assay_id (true repeat measurement):   {single_assay_replicates}"
)
print("  backed by MULTIPLE ChEMBL assay_ids (cross-assay agreement, NOT")
print(f"    the same thing as measurement replicate noise):               {multi_assay_replicates}")


# Recompute sigma separately for each subset
def sigma_stats(keys_subset, cell_counts):
    sds = [statistics.stdev(cell_counts[k]) for k in keys_subset if len(cell_counts[k]) >= 2]
    return sds


single_keys = [k for k, v in rep_multi_only.items() if len(v) == 1]
multi_keys = [k for k, v in rep_multi_only.items() if len(v) > 1]
sds_single = sigma_stats(single_keys, cell_counts)
sds_multi = sigma_stats(multi_keys, cell_counts)
if sds_single:
    print(
        f"\n  median sigma, SINGLE-assay_id replicate groups (n={len(sds_single)}): "
        f"{statistics.median(sds_single):.3f}"
    )
if sds_multi:
    print(
        f"  median sigma, MULTI-assay_id  replicate groups (n={len(sds_multi)}): "
        f"{statistics.median(sds_multi):.3f}"
    )

# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 78, "\n5. PER-ISOFORM SIGMA (is a global pooled sigma defensible?)\n" + "=" * 78)

by_iso_sds = defaultdict(list)
for k, v in cell_counts.items():
    if len(v) >= 2:
        by_iso_sds[k[2]].append(statistics.stdev(v))
for iso in sorted(by_iso_sds):
    sds = by_iso_sds[iso]
    print(
        f"  {iso:<12} n_groups={len(sds):4}  median={statistics.median(sds):.3f}  "
        f"mean={statistics.mean(sds):.3f}"
    )

# ══════════════════════════════════════════════════════════════════════════
print(
    "\n" + "=" * 78,
    "\n6. SIGN-FLIP MAGNITUDE DISTRIBUTION (is there a natural separation from noise?)\n"
    + "=" * 78,
)

panel_cmpd_iso_val = defaultdict(lambda: defaultdict(dict))
panel_cmpd_scaf = defaultdict(dict)
for r in acc:
    resolved = resolve_panel_key(r)
    if not resolved.is_scientific_evidence:
        continue
    key = resolved.key
    ik = r.get("inchikey")
    if not ik:
        continue
    p = pact(r)
    if p is not None:
        panel_cmpd_iso_val[key][ik][r.get("isoform")] = p
    fam = r.get("scaffold_family_id")
    if fam:
        panel_cmpd_scaf[key][ik] = fam

all_deltas = []  # |da - db| for flip candidates
all_deltas_noflip = []  # |da - db| for non-flip pairs, for comparison
for key, cm in panel_cmpd_iso_val.items():
    complete_iks = [ik for ik, isod in cm.items() if T1.issubset(isod)]
    by_scaf = defaultdict(list)
    for ik in complete_iks:
        fam = panel_cmpd_scaf.get(key, {}).get(ik)
        if fam:
            by_scaf[fam].append(ik)
    for fam, members in by_scaf.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = cm[members[i]], cm[members[j]]
                for x in ("PI3Kbeta", "PI3Kgamma", "PI3Kdelta"):
                    da = a["PI3Kalpha"] - a[x]
                    db = b["PI3Kalpha"] - b[x]
                    if da * db < 0:
                        all_deltas.append(abs(da - db))
                    else:
                        all_deltas_noflip.append(abs(da - db))

if all_deltas:
    qs = statistics.quantiles(all_deltas, n=10)
    print(f"Sign-flip |Δselectivity| distribution (n={len(all_deltas)}):")
    print(f"  deciles: {[round(q, 3) for q in qs]}")
    print(
        f"  median within-noise-floor (2x median C1 sigma = "
        f"{2 * statistics.median([statistics.stdev(v) for v in cell_counts.values() if len(v) >= 2]):.3f}):"
        f" {sum(1 for d in all_deltas if d < 2 * statistics.median([statistics.stdev(v) for v in cell_counts.values() if len(v) >= 2]))}"
        f" / {len(all_deltas)} sign-flips have magnitude below 2x the replicate noise floor"
    )
if all_deltas_noflip:
    print(
        f"Non-flip |Δselectivity| median: {statistics.median(all_deltas_noflip):.3f} (n={len(all_deltas_noflip)})"
    )
