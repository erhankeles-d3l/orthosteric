"""ANALYSIS / PROTOTYPE — GDR-011 Issue 1+2 empirical comparison.
Read-only. Evaluates candidate comparability units on the real A3 corpus.
NON-BINDING: no policy is selected here.
"""

import gzip
import json
import pathlib
import re
from collections import Counter, defaultdict

T1 = {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}
GENE = {
    "CHEMBL4005": "PI3Kalpha",
    "CHEMBL3145": "PI3Kbeta",
    "CHEMBL3267": "PI3Kgamma",
    "CHEMBL3130": "PI3Kdelta",
}
ATP_PAT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:u|\u03bc)M\s+ATP", re.I)
ATP_MENTION = re.compile(r"\bATP\b", re.I)

# ---- load A3 accepted records, enrich with raw assay metadata -----------------
with gzip.open("data/snapshots/activity_snapshot_A3/records.json.gz", "rt") as f:
    recs = json.load(f)
acc = [r for r in recs if not r.get("exclusion_reason")]

meta = {}
for tdir in sorted(pathlib.Path("data/raw/chembl").iterdir()):
    if not tdir.is_dir() or tdir.name not in GENE:
        continue
    for p in sorted((tdir / "IC50").glob("page_*.json")):
        for a in json.loads(p.read_text())["activities"]:
            rid = str(a.get("activity_id"))
            meta[rid] = (a.get("bao_format"), a.get("assay_type"), a.get("assay_description") or "")

for r in acc:
    bf, at, desc = meta.get(str(r.get("source_record_id")), (None, None, ""))
    r["_bao"] = bf
    r["_atype"] = at
    r["_desc"] = desc
    m = ATP_PAT.search(desc)
    r["_atp"] = float(m.group(1)) if m else None
    r["_atp_mention"] = bool(ATP_MENTION.search(desc))

print(f"A3 accepted records: {len(acc)}   metadata joined: {sum(1 for r in acc if r['_bao'])}\n")


# ---- candidate key functions -------------------------------------------------
def k_assay(r):
    return (r.get("study_id"), r.get("assay_id"))


def k_doc(r):
    return (r.get("study_id"),)


def k_proto(r):
    return (r.get("study_id"), r["_bao"], r["_atype"])


def k_proto_atp(r):
    # ATP mandatory: unknown ATP is its own non-matching bucket per record
    atp = r["_atp"] if r["_atp"] is not None else f"UNKNOWN::{r.get('assay_id')}"
    return (r.get("study_id"), r["_bao"], r["_atype"], atp)


def k_proto_atp_cov(r):
    # ATP as covariate: not in key
    return (r.get("study_id"), r["_bao"], r["_atype"])


CANDIDATES = [
    ("B  assay (study,assay) [CURRENT]", k_assay),
    ("A  document (study)", k_doc),
    ("C1 protocol (study,bao,type)", k_proto),
    ("C2 protocol+ATP mandatory", k_proto_atp),
]


def analyse(name, keyfn):
    grp_iso = defaultdict(set)
    grp_cmpd_iso = defaultdict(lambda: defaultdict(set))
    for r in acc:
        ik = r.get("inchikey")
        if not ik:
            continue
        g = keyfn(r)
        iso = r.get("isoform")
        grp_iso[g].add(iso)
        grp_cmpd_iso[g][ik].add(iso)

    complete_cmpds, pair_panels = set(), 0
    n_iso_hist = Counter()
    complete_groups = 0
    for g, cm in grp_cmpd_iso.items():
        has4 = False
        for ik, isos in cm.items():
            n_iso_hist[len(isos & T1)] += 1
            if isos >= T1:
                complete_cmpds.add(ik)
                has4 = True
            k = len(isos & T1)
            pair_panels += k * (k - 1) // 2
        if has4:
            complete_groups += 1

    # bias descriptors on the complete subset
    comp_recs = [r for r in acc if r.get("inchikey") in complete_cmpds]
    scaf = {r.get("scaffold_family_id") for r in comp_recs if r.get("scaffold_family_id")}
    docs = {r.get("study_id") for r in comp_recs}
    cens = Counter(r.get("censoring") for r in comp_recs)
    iso_bal = Counter(r.get("isoform") for r in comp_recs)
    atp_known = sum(1 for r in comp_recs if r["_atp"] is not None)
    return dict(
        name=name,
        groups=len(grp_iso),
        complete_groups=complete_groups,
        complete_cmpds=len(complete_cmpds),
        pair_panels=pair_panels,
        hist={k: n_iso_hist[k] for k in (1, 2, 3, 4)},
        scaffolds=len(scaf),
        docs=len(docs),
        cens=dict(cens),
        iso_bal=dict(iso_bal),
        comp_recs=len(comp_recs),
        atp_known_pct=(100 * atp_known / len(comp_recs) if comp_recs else 0.0),
        cmpd_set=complete_cmpds,
    )


res = [analyse(n, f) for n, f in CANDIDATES]

print("=== Candidate comparability units — A3 corpus ===")
hdr = f"{'definition':<36}{'groups':>8}{'4-iso grps':>12}{'complete cmpds':>16}{'pairwise':>10}{'scaffolds':>11}{'docs':>7}"
print(hdr)
print("-" * len(hdr))
for r in res:
    print(
        f"{r['name']:<36}{r['groups']:>8}{r['complete_groups']:>12}{r['complete_cmpds']:>16}{r['pair_panels']:>10}{r['scaffolds']:>11}{r['docs']:>7}"
    )

print("\n=== Isoform-count histogram per (compound x group) ===")
print(f"{'definition':<36}{'1/4':>9}{'2/4':>9}{'3/4':>9}{'4/4':>9}")
for r in res:
    h = r["hist"]
    print(f"{r['name']:<36}{h[1]:>9}{h[2]:>9}{h[3]:>9}{h[4]:>9}")

print("\n=== Complete-subset composition (bias descriptors) ===")
for r in res:
    if r["complete_cmpds"] == 0:
        print(f"  {r['name']}: EMPTY")
        continue
    print(f"  {r['name']}")
    print(
        f"      records={r['comp_recs']}  scaffolds={r['scaffolds']}  docs={r['docs']}  ATP-known={r['atp_known_pct']:.1f}%"
    )
    print(f"      isoform balance: {r['iso_bal']}")
    print(f"      censoring: {r['cens']}")

# nesting check
print("\n=== Nesting of complete-compound sets ===")
by = {r["name"]: r["cmpd_set"] for r in res}
names = [r["name"] for r in res]
for i in range(len(names)):
    for j in range(len(names)):
        if i < j:
            a, b = by[names[i]], by[names[j]]
            if a or b:
                print(
                    f"  |{names[i][:22]}|={len(a):5}  |{names[j][:22]}|={len(b):5}  shared={len(a & b):5}  A-only={len(a - b):5}  B-only={len(b - a):5}"
                )

# ---- whole-corpus baseline for bias comparison ------------------------------
all_scaf = {r.get("scaffold_family_id") for r in acc if r.get("scaffold_family_id")}
all_iso = Counter(r.get("isoform") for r in acc)
all_cens = Counter(r.get("censoring") for r in acc)
all_atp = 100 * sum(1 for r in acc if r["_atp"] is not None) / len(acc)
print("\n=== FULL corpus baseline (for bias comparison) ===")
print(
    f"  records={len(acc)} compounds={len({r.get('inchikey') for r in acc if r.get('inchikey')})} scaffolds={len(all_scaf)} docs={len({r.get('study_id') for r in acc})}"
)
print(f"  isoform balance: {dict(all_iso)}")
print(f"  censoring: {dict(all_cens)}   ATP-known={all_atp:.1f}%")
