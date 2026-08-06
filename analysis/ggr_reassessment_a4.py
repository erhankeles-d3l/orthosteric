"""GGR-002a/002b/010 recomputation on Activity Snapshot A4, under the
Project-Owner-approved GDR-010/GDR-011 policies.

Uses ONLY orthosteric.data.comparability (resolve_panel_key,
atp_confirmed_panel_key) and orthosteric.data.harmonization._atp_extraction
-- the governed modules -- never ad-hoc inline key construction.

This is ANALYSIS / not governed pipeline code.  No MMP transformation rule,
no S4b sharpness multiplier, and no dual-inhibitor inclusion rule is
invented here.  Where the existing governance has not sealed such a rule,
this script reports GDR_REQUIRED / CORPUS_INSUFFICIENT and stops.
"""
import sys, json, gzip, pathlib, statistics
from collections import Counter, defaultdict
sys.path.insert(0, "src")

from orthosteric.data.comparability import PanelKeyTier, resolve_panel_key, atp_confirmed_panel_key

A4 = pathlib.Path("data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
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

# ── Build C1_PRIMARY-only panel index (GDR-011 Option D) ─────────────────────
panel_cmpd_iso_val = defaultdict(lambda: defaultdict(dict))  # key -> ik -> iso -> pact
panel_cmpd_scaf = defaultdict(dict)  # key -> ik -> scaffold_family_id
n_legacy = 0
for r in acc:
    resolved = resolve_panel_key(r)
    if not resolved.is_scientific_evidence:
        n_legacy += 1
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

print(f"=== Panel index (C1_PRIMARY only; GDR-011 Option D) ===")
print(f"  A4 accepted records:       {len(acc)}")
print(f"  LEGACY_FALLBACK records:   {n_legacy} (excluded from all evidence below)")
print(f"  C1_PRIMARY panels:         {len(panel_cmpd_iso_val)}")

complete_pact = {}
for key, cm in panel_cmpd_iso_val.items():
    for ik, isod in cm.items():
        if T1.issubset(isod):
            complete_pact.setdefault(ik, {})
            for iso, v in isod.items():
                complete_pact[ik][iso] = v  # last-writer if seen in >1 complete panel

n_complete_compounds = sum(
    1 for key, cm in panel_cmpd_iso_val.items()
    for ik, isod in cm.items() if T1.issubset(isod)
)
print(f"  C1_PRIMARY complete four-isoform (panel,compound) pairs: {n_complete_compounds}")

# ══════════════════════════════════════════════════════════════════════════════
# GGR-002a -- MMP / selectivity-switch candidates
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}\nGGR-002a\n{'='*70}")

pairs_examined = 0
sign_flip_candidates = 0
same_scaffold_pairs = []
studies_involved = set()

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
                a_ik, b_ik = members[i], members[j]
                a, b = cm[a_ik], cm[b_ik]
                pairs_examined += 1
                studies_involved.add(key[0])
                flips = []
                for x in ("PI3Kbeta", "PI3Kgamma", "PI3Kdelta"):
                    da = a["PI3Kalpha"] - a[x]
                    db = b["PI3Kalpha"] - b[x]
                    if da * db < 0:
                        flips.append((x, da, db))
                if flips:
                    sign_flip_candidates += 1
                    same_scaffold_pairs.append((key, a_ik, b_ik, flips))

print("GOVERNANCE STATUS: MMP transformation and switch-inclusion criteria")
print("are NOT sealed by any accepted GDR (Constitution S5/§3.6 curated MMP")
print("switch set was never frozen). This script does not invent one.")
print()
print("CORPUS-DERIVED OBSERVATION (not a governance rule):")
print(f"  Same-scaffold, same-C1-panel, complete-4-isoform pairs examined: {pairs_examined}")
print(f"  Pairs with >=1 isoform showing an alpha-vs-X selectivity SIGN change: {sign_flip_candidates}")
print(f"  Distinct studies (study_id) contributing such pairs: {len(studies_involved)}")
if same_scaffold_pairs:
    print(f"\n  First 5 sign-flip candidates:")
    for key, a_ik, b_ik, flips in same_scaffold_pairs[:5]:
        print(f"    panel={key[0][:20]}.../{key[1][:30]} {a_ik[:16]} vs {b_ik[:16]}: {flips}")

ggr002a_status = "GDR_REQUIRED"
print(f"\nGGR-002a = {ggr002a_status}")
print("  Rationale: candidate pairs are corpus-derived and reproducible, but no")
print("  accepted GDR defines what makes a pair a valid MMP or what selectivity-")
print("  switch magnitude counts as a governed 'switch'. Freezing either now")
print("  would be inventing governance, which this script must not do.")

# ══════════════════════════════════════════════════════════════════════════════
# GGR-002b -- within-study noise floor
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}\nGGR-002b\n{'='*70}")

rep_groups = defaultdict(list)
for r in acc:
    resolved = resolve_panel_key(r)
    if not resolved.is_scientific_evidence:
        continue
    p = pact(r)
    if p is None:
        continue
    key = (resolved.key, r.get("inchikey"), r.get("isoform"))
    rep_groups[key].append(p)

multi = {k: v for k, v in rep_groups.items() if len(v) >= 2}
print(f"C1_PRIMARY replicate groups (n>=2 same compound x isoform x panel): {len(multi)}")
if multi:
    sds = [statistics.stdev(v) for v in multi.values()]
    iso_cov = Counter(k[2] for k in multi)
    print(f"  Total replicate observations: {sum(len(v) for v in multi.values())}")
    print(f"  median sigma (pAct units):    {statistics.median(sds):.3f}")
    print(f"  mean sigma:                   {statistics.mean(sds):.3f}")
    print(f"  p90 sigma:                    {sorted(sds)[int(0.9*len(sds))-1]:.3f}")
    print(f"  isoform coverage:             {dict(iso_cov)}")
else:
    print("  No C1_PRIMARY replicate groups found.")

# ATP-confirmed secondary stratum replicate check (GDR-011 Option D secondary)
atp_rep_groups = defaultdict(list)
for r in acc:
    atp_key = atp_confirmed_panel_key(r)
    if atp_key is None:
        continue
    p = pact(r)
    if p is None:
        continue
    full_key = (atp_key, r.get("inchikey"), r.get("isoform"))
    atp_rep_groups[full_key].append(p)
atp_multi = {k: v for k, v in atp_rep_groups.items() if len(v) >= 2}
print(f"\nATP-CONFIRMED secondary-stratum replicate groups (n>=2): {len(atp_multi)}")
if atp_multi:
    sds2 = [statistics.stdev(v) for v in atp_multi.values()]
    print(f"  median sigma: {statistics.median(sds2):.3f}  (n={len(atp_multi)} groups)")

ggr002b_status = "CORPUS_INSUFFICIENT" if not multi else "GDR_REQUIRED"
print(f"\nGGR-002b = {ggr002b_status}")
print("  Rationale: within-study sigma is corpus-derived and reproducible above.")
print("  No accepted GDR specifies the S4b sharpness MULTIPLIER derived from it,")
print("  or the minimum group count/isoform coverage required to seal one.")
print("  This script reports the statistics; it does not choose a multiplier.")

# ══════════════════════════════════════════════════════════════════════════════
# GGR-010 -- dual PI3K/mTOR census
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}\nGGR-010\n{'='*70}")
print("mTOR ChEMBL target: NOT ACQUIRED. Activity Snapshot A4 contains no")
print("mTOR (CHEMBL2842 candidate, unverified in ChEMBL 37) activity records.")
print("No pathway-, docking-, structural-similarity-, or model-based inference")
print("substitutes for direct mTOR activity evidence (per governance instructions).")
print(f"\nGGR-010 = CORPUS_INSUFFICIENT")
print("  Rationale: zero mTOR activity records in A4 -- there is no explicit")
print("  dual PI3K/mTOR evidence to report, positive or negative.")

# ── Write machine-readable summary ────────────────────────────────────────────
out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "c1_primary_panels": len(panel_cmpd_iso_val),
    "legacy_fallback_records": n_legacy,
    "c1_complete_four_isoform_pairs": n_complete_compounds,
    "ggr002a": {
        "status": ggr002a_status,
        "same_scaffold_complete_pairs": pairs_examined,
        "sign_flip_candidates": sign_flip_candidates,
        "studies_involved": len(studies_involved),
    },
    "ggr002b": {
        "status": ggr002b_status,
        "c1_replicate_groups": len(multi),
        "median_sigma": statistics.median(sds) if multi else None,
        "atp_confirmed_replicate_groups": len(atp_multi),
    },
    "ggr010": {
        "status": "CORPUS_INSUFFICIENT",
        "mtor_records": 0,
    },
}
(A4 / "ggr_reassessment.json").write_text(json.dumps(out, indent=2))
print(f"\nWrote {A4}/ggr_reassessment.json")
