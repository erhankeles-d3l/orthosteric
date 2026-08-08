"""ANALYSIS / PROTOTYPE — GDR-011 Issue 2: ATP extraction feasibility + validation.
Read-only. Extraction is EXPERIMENTAL and non-binding; no value is written to any record.
"""

import json
import pathlib
import random
import re
from collections import Counter, defaultdict

GENE = {
    "CHEMBL4005": "PI3Kalpha",
    "CHEMBL3145": "PI3Kbeta",
    "CHEMBL3267": "PI3Kgamma",
    "CHEMBL3130": "PI3Kdelta",
}
MENTION = re.compile(r"\bATP\b", re.I)
# Candidate patterns (PROTOTYPE — not governed)
P_UM = re.compile(r"(\d+(?:\.\d+)?)\s*(?:u|\u03bc|μ)M\s+ATP", re.I)
P_MM = re.compile(r"(\d+(?:\.\d+)?)\s*mM\s+ATP", re.I)
P_NM = re.compile(r"(\d+(?:\.\d+)?)\s*nM\s+ATP", re.I)
P_ATP_N = re.compile(
    r"ATP\s+(?:at\s+|conc[a-z]*\s+(?:of\s+)?)?(\d+(?:\.\d+)?)\s*(u|\u03bc|μ|m|n)M", re.I
)
P_KM = re.compile(r"ATP\s*Km|Km\s*(?:for|of)\s*ATP|at\s+Km", re.I)

rows = []
for tdir in sorted(pathlib.Path("data/raw/chembl").iterdir()):
    if not tdir.is_dir() or tdir.name not in GENE:
        continue
    for p in sorted((tdir / "IC50").glob("page_*.json")):
        for a in json.loads(p.read_text())["activities"]:
            rows.append(
                {
                    "id": str(a.get("activity_id")),
                    "iso": GENE[tdir.name],
                    "doc": a.get("document_chembl_id"),
                    "assay": a.get("assay_chembl_id"),
                    "desc": a.get("assay_description") or "",
                    "props": a.get("activity_properties") or [],
                }
            )

n = len(rows)
print(f"=== ATP evidence census (n={n} raw records) ===")

# 1. structured fields
struct = 0
struct_ex = []
for r in rows:
    for pr in r["props"]:
        blob = json.dumps(pr)
        if MENTION.search(blob):
            struct += 1
            if len(struct_ex) < 3:
                struct_ex.append(pr)
            break
print(f"  structured (activity_properties mentions ATP): {struct} ({100 * struct / n:.2f}%)")
for e in struct_ex:
    print(f"      e.g. {json.dumps(e)[:150]}")

# 2. free text
ment = [r for r in rows if MENTION.search(r["desc"])]
print(f"  assay_description mentions ATP              : {len(ment)} ({100 * len(ment) / n:.1f}%)")


def extract(desc):
    """Return (value_uM, unit_seen, span, rule) or (None, ..., reason)."""
    m = P_UM.search(desc)
    if m:
        return float(m.group(1)), "uM", m.group(0), "P_UM"
    m = P_MM.search(desc)
    if m:
        return float(m.group(1)) * 1000, "mM", m.group(0), "P_MM"
    m = P_NM.search(desc)
    if m:
        return float(m.group(1)) / 1000, "nM", m.group(0), "P_NM"
    m = P_ATP_N.search(desc)
    if m:
        v = float(m.group(1))
        u = m.group(2).lower()
        v = v * 1000 if u == "m" else (v / 1000 if u == "n" else v)
        return v, u + "M", m.group(0), "P_ATP_N"
    if P_KM.search(desc):
        return None, None, P_KM.search(desc).group(0), "KM_REFERENCED"
    return None, None, None, "NO_MATCH"


res = Counter()
vals = Counter()
km = []
nomatch = []
extracted = {}
for r in ment:
    v, u, span, rule = extract(r["desc"])
    res[rule] += 1
    if v is not None:
        vals[v] += 1
        extracted[r["id"]] = (v, u, span, rule, r["desc"])
    elif rule == "KM_REFERENCED" and len(km) < 5:
        km.append(r["desc"][:130])
    elif rule == "NO_MATCH" and len(nomatch) < 8:
        nomatch.append(r["desc"][:130])

print(f"\n=== Extraction outcome on the {len(ment)} ATP-mentioning records ===")
for k, c in res.most_common():
    print(f"  {k:<16}{c:>7}  ({100 * c / len(ment):5.1f}%)")
print(
    f"  numeric value obtained: {sum(v for k, v in res.items() if k.startswith('P_'))} "
    f"({100 * sum(v for k, v in res.items() if k.startswith('P_')) / n:.1f}% of all records)"
)

print("\n=== Extracted concentrations (uM) ===")
for v, c in sorted(vals.items()):
    print(f"  {v:>10} uM : {c}")

print(f"\n=== FAILURE MODE 1: Km-referenced (no numeric conc) — {res['KM_REFERENCED']} records ===")
for s in km:
    print(f"  ...{s}")
print(f"\n=== FAILURE MODE 2: mentions ATP, no extractable conc — {res['NO_MATCH']} records ===")
for s in nomatch:
    print(f"  ...{s}")

# 3. conflicting: same assay, >1 distinct extracted value
assay_vals = defaultdict(set)
for r in ment:
    v, _, _, rule = extract(r["desc"])
    if v is not None:
        assay_vals[r["assay"]].add(v)
conflict = {a: v for a, v in assay_vals.items() if len(v) > 1}
print(f"\n=== FAILURE MODE 3: same assay_id, conflicting values: {len(conflict)} assays ===")
for a, v in list(conflict.items())[:5]:
    print(f"  {a}: {sorted(v)}")

# 4. ambiguity: description contains >1 numeric ATP-like match
amb = 0
amb_ex = []
for r in ment:
    hits = P_UM.findall(r["desc"]) + P_MM.findall(r["desc"])
    if len(hits) > 1:
        amb += 1
        if len(amb_ex) < 4:
            amb_ex.append((hits, r["desc"][:130]))
print(f"\n=== FAILURE MODE 4: multiple ATP concentrations in one description: {amb} records ===")
for h, s in amb_ex:
    print(f"  {h} <- ...{s}")

# 5. BOUNDED MANUAL REVIEW SET — deterministic sample for owner inspection
random.seed(20260806)
pool = sorted(extracted.items())
sample = random.sample(pool, min(30, len(pool)))
out = [
    {
        "activity_id": k,
        "extracted_uM": v[0],
        "unit_seen": v[1],
        "text_span": v[2],
        "rule": v[3],
        "assay_description": v[4],
    }
    for k, v in sample
]
pathlib.Path("analysis/atp_manual_review_set.json").write_text(json.dumps(out, indent=2))
print("\n=== BOUNDED MANUAL REVIEW SET ===")
print(f"  Sampling: random.seed(20260806), 30 of {len(pool)} successfully-extracted records")
print("  Written to analysis/atp_manual_review_set.json for Project Owner adjudication")
print("  NOTE: no precision estimate is claimed — this set has NOT been manually reviewed.")
for o in out[:5]:
    print(f"    {o['activity_id']}: {o['extracted_uM']} uM  span='{o['text_span']}'")
