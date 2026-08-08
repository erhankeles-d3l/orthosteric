"""ANALYSIS / PROTOTYPE — bias analysis + GGR-002a/002b under each candidate policy.
Read-only, non-binding. No thresholds are selected.
"""

import gzip
import json
import pathlib
import re
import statistics
from collections import Counter, defaultdict

T1 = {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}
GENE = {
    "CHEMBL4005": "PI3Kalpha",
    "CHEMBL3145": "PI3Kbeta",
    "CHEMBL3267": "PI3Kgamma",
    "CHEMBL3130": "PI3Kdelta",
}
ATP = re.compile(r"(\d+(?:\.\d+)?)\s*(?:u|\u03bc|μ)M\s+ATP", re.I)

with gzip.open("data/snapshots/activity_snapshot_A3/records.json.gz", "rt") as f:
    recs = json.load(f)
acc = [r for r in recs if not r.get("exclusion_reason")]
meta = {}
for tdir in sorted(pathlib.Path("data/raw/chembl").iterdir()):
    if not tdir.is_dir() or tdir.name not in GENE:
        continue
    for p in sorted((tdir / "IC50").glob("page_*.json")):
        for a in json.loads(p.read_text())["activities"]:
            meta[str(a.get("activity_id"))] = (
                a.get("bao_format"),
                a.get("assay_type"),
                a.get("assay_description") or "",
            )
for r in acc:
    bf, at, d = meta.get(str(r.get("source_record_id")), (None, None, ""))
    r["_bao"], r["_atype"] = bf, at
    m = ATP.search(d)
    r["_atp"] = float(m.group(1)) if m else None


def pact(r):
    v = r.get("pchembl_value")
    try:
        return float(v) if v is not None else None
    except:
        return None


KEYS = {
    "A_document": lambda r: (r.get("study_id"),),
    "C1_protocol": lambda r: (r.get("study_id"), r["_bao"], r["_atype"]),
    "C2_protocol_ATP": lambda r: (
        r.get("study_id"),
        r["_bao"],
        r["_atype"],
        r["_atp"] if r["_atp"] is not None else f"UNK::{r.get('assay_id')}",
    ),
}


def complete_set(keyfn):
    g = defaultdict(lambda: defaultdict(set))
    for r in acc:
        ik = r.get("inchikey")
        if ik:
            g[keyfn(r)][ik].add(r.get("isoform"))
    out = set()
    for _, cm in g.items():
        for ik, iso in cm.items():
            if iso >= T1:
                out.add(ik)
    return out


print("=== POTENCY / SELECTION BIAS ===")
allp = [pact(r) for r in acc]
allp = [x for x in allp if x is not None]
print(
    f"  FULL corpus      n={len(allp):6}  median pAct={statistics.median(allp):.2f}  "
    f"IQR=[{statistics.quantiles(allp, n=4)[0]:.2f},{statistics.quantiles(allp, n=4)[2]:.2f}]  "
    f">=7.0: {100 * sum(1 for x in allp if x >= 7) / len(allp):.1f}%"
)
sets = {}
for name, kf in KEYS.items():
    s = complete_set(kf)
    sets[name] = s
    sub = [pact(r) for r in acc if r.get("inchikey") in s]
    sub = [x for x in sub if x is not None]
    if not sub:
        continue
    print(
        f"  {name:<16} n={len(sub):6}  median pAct={statistics.median(sub):.2f}  "
        f"IQR=[{statistics.quantiles(sub, n=4)[0]:.2f},{statistics.quantiles(sub, n=4)[2]:.2f}]  "
        f">=7.0: {100 * sum(1 for x in sub if x >= 7) / len(sub):.1f}%"
    )

print("\n=== STUDY CONCENTRATION (top-5 document share of complete subset) ===")
for name, s in sets.items():
    sub = [r for r in acc if r.get("inchikey") in s]
    if not sub:
        continue
    c = Counter(r.get("study_id") for r in sub)
    top5 = sum(n for _, n in c.most_common(5))
    print(f"  {name:<16} docs={len(c):4}  top5 share={100 * top5 / len(sub):5.1f}%")

print("\n=== GGR-002a — within-group MMP/selectivity-switch candidates ===")
print("  (compound pairs sharing a scaffold family, both complete, in the SAME group,")
print("   where the sign of a pairwise selectivity ratio differs -> switch candidate)")
for name, kf in KEYS.items():
    s = sets[name]
    if not s:
        print(f"  {name:<16} EMPTY")
        continue
    grp = defaultdict(lambda: defaultdict(dict))
    scaf = {}
    for r in acc:
        ik = r.get("inchikey")
        if ik in s and pact(r) is not None:
            grp[kf(r)][ik][r.get("isoform")] = pact(r)
            if r.get("scaffold_family_id"):
                scaf[ik] = r["scaffold_family_id"]
    pairs = 0
    switches = 0
    for g, cm in grp.items():
        comp = [ik for ik, d in cm.items() if set(d) >= T1]
        by_scaf = defaultdict(list)
        for ik in comp:
            if ik in scaf:
                by_scaf[scaf[ik]].append(ik)
        for fam, members in by_scaf.items():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = cm[members[i]], cm[members[j]]
                    pairs += 1
                    for x in ("PI3Kbeta", "PI3Kgamma", "PI3Kdelta"):
                        da = a["PI3Kalpha"] - a[x]
                        db = b["PI3Kalpha"] - b[x]
                        if da * db < 0 and abs(da - db) >= 1.0:
                            switches += 1
                            break
    print(f"  {name:<16} same-scaffold complete pairs={pairs:6}  sign-flip candidates={switches:5}")
print("  STATUS: CORPUS-DERIVED counts only. MMP transformation rules, the >=1.0 log")
print("          separation, and switch criteria are NOT governed -> RULE_MISSING.")

print("\n=== GGR-002b — within-group replicate noise floor ===")
for name, kf in KEYS.items():
    rg = defaultdict(list)
    for r in acc:
        v = pact(r)
        ik = r.get("inchikey")
        if v is not None and ik:
            rg[(kf(r), ik, r.get("isoform"))].append(v)
    multi = [v for v in rg.values() if len(v) >= 2]
    if not multi:
        print(f"  {name:<16} no replicate groups")
        continue
    sds = [statistics.stdev(v) for v in multi]
    print(
        f"  {name:<16} groups={len(multi):5}  obs={sum(len(v) for v in multi):6}  "
        f"median sigma={statistics.median(sds):.3f}  mean={statistics.mean(sds):.3f}  "
        f"p90={sorted(sds)[int(0.9 * len(sds)) - 1]:.3f}"
    )
    iso = Counter(k[2] for k, v in rg.items() if len(v) >= 2)
    print(f"  {'':<16} isoform coverage: {dict(iso)}")
print("  STATUS: CORPUS-DERIVED. The S4b sharpness MULTIPLIER is NOT derived here")
print("          and must not be inferred from these numbers -> GDR REQUIRED.")
