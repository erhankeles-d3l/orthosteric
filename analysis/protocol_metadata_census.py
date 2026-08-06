"""ANALYSIS — what assay metadata is actually available for a protocol signature?"""

import json
import pathlib
import re
from collections import Counter, defaultdict

GENE = {
    "CHEMBL4005": "PI3Kalpha",
    "CHEMBL3145": "PI3Kbeta",
    "CHEMBL3267": "PI3Kgamma",
    "CHEMBL3130": "PI3Kdelta",
}
fields = [
    "assay_type",
    "bao_format",
    "bao_label",
    "assay_description",
    "assay_variant_mutation",
    "target_organism",
    "standard_units",
    "standard_type",
    "data_validity_comment",
    "activity_properties",
]
present = Counter()
total = 0
vals = defaultdict(Counter)
assay_meta = {}  # assay_id -> metadata tuple

for tdir in sorted(pathlib.Path("data/raw/chembl").iterdir()):
    if not tdir.is_dir() or tdir.name not in GENE:
        continue
    iso = GENE[tdir.name]
    for p in sorted((tdir / "IC50").glob("page_*.json")):
        for a in json.loads(p.read_text())["activities"]:
            total += 1
            for f in fields:
                v = a.get(f)
                if v not in (None, "", [], {}):
                    present[f] += 1
                    if f in (
                        "assay_type",
                        "bao_format",
                        "bao_label",
                        "standard_units",
                        "target_organism",
                    ):
                        vals[f][str(v)] += 1
            aid = a.get("assay_chembl_id")
            if aid and aid not in assay_meta:
                assay_meta[aid] = {
                    "iso": iso,
                    "doc": a.get("document_chembl_id"),
                    "assay_type": a.get("assay_type"),
                    "bao_format": a.get("bao_format"),
                    "bao_label": a.get("bao_label"),
                    "desc": a.get("assay_description") or "",
                    "organism": a.get("target_organism"),
                }

print(f"=== Field availability (n={total} raw records) ===")
for f in fields:
    print(f"  {f:<26}{present[f]:>7}  ({100 * present[f] / total:5.1f}%)")

print("\n=== Value distributions ===")
for f in ["assay_type", "bao_format", "bao_label", "standard_units", "target_organism"]:
    print(f"  {f}: {vals[f].most_common(5)}")

print(f"\n=== Assay-level metadata (n={len(assay_meta)} distinct assays) ===")
bao_by_assay = Counter(m["bao_format"] for m in assay_meta.values())
print(f"  bao_format across assays: {bao_by_assay.most_common(6)}")
type_by_assay = Counter(m["assay_type"] for m in assay_meta.values())
print(f"  assay_type across assays: {type_by_assay.most_common(6)}")

# Within a 4-isoform document, do the 4 assays share bao_format/assay_type?
doc_assays = defaultdict(list)
for aid, m in assay_meta.items():
    if m["doc"]:
        doc_assays[m["doc"]].append(m)
four_docs = {d for d, ms in doc_assays.items() if len({m["iso"] for m in ms}) == 4}
print(f"\n=== Protocol homogeneity within 4-isoform documents (n={len(four_docs)}) ===")
same_type = same_bao = same_both = 0
for d in four_docs:
    ms = doc_assays[d]
    st = len({m["assay_type"] for m in ms}) == 1
    sb = len({m["bao_format"] for m in ms}) == 1
    same_type += st
    same_bao += sb
    same_both += st and sb
print(
    f"  all assays share assay_type : {same_type}/{len(four_docs)} ({100 * same_type / len(four_docs):.1f}%)"
)
print(
    f"  all assays share bao_format : {same_bao}/{len(four_docs)} ({100 * same_bao / len(four_docs):.1f}%)"
)
print(
    f"  share both                  : {same_both}/{len(four_docs)} ({100 * same_both / len(four_docs):.1f}%)"
)

# ATP within document: do the 4 assays state the SAME ATP concentration?
pat = re.compile(r"(\d+(?:\.\d+)?)\s*(?:u|\u03bc)M\s+ATP", re.I)


def atp_of(desc):
    m = pat.search(desc or "")
    return float(m.group(1)) if m else None


allknown = conflict = partial = none_known = 0
for d in four_docs:
    ms = doc_assays[d]
    atps = [atp_of(m["desc"]) for m in ms]
    known = [a for a in atps if a is not None]
    if not known:
        none_known += 1
    elif len(known) < len(atps):
        partial += 1
    elif len(set(known)) == 1:
        allknown += 1
    else:
        conflict += 1
print("\n=== ATP consistency within 4-isoform documents ===")
print(
    f"  all 4 assays state SAME ATP conc : {allknown}/{len(four_docs)} ({100 * allknown / len(four_docs):.1f}%)"
)
print(
    f"  all 4 state ATP but CONFLICTING  : {conflict}/{len(four_docs)} ({100 * conflict / len(four_docs):.1f}%)"
)
print(
    f"  only SOME assays state ATP       : {partial}/{len(four_docs)} ({100 * partial / len(four_docs):.1f}%)"
)
print(
    f"  no assay states ATP              : {none_known}/{len(four_docs)} ({100 * none_known / len(four_docs):.1f}%)"
)
