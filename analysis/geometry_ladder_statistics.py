"""Geometry-sensitivity ladder: full statistical analysis (Actions 2, 3,
4, 6). Covers Rep 0 (atom) / Rep 1 (residue) / Rep 2 (role-aware, no
geometry) / Rep 3-coarse / Rep 3-intermediate / Rep 3-fine, uniformly.

Action 2 -- normalized net score: raw net score is a COUNT, and adding
geometry to the key roughly multiplies the number of possible bins,
which mechanically inflates the raw score's magnitude independent of
any real chemistry. The normalized score
  (N_alpha_favored - N_other_favored) / N_occupied_bins
is computed PER COMPOUND first, then averaged by stratum -- this is the
metric actually judged for ladder stability, not the raw score (which
is retained alongside it for continuity with the already-committed
result only).

Action 3 -- bootstrap the difference directly, not CI-overlap-as-a-proxy:
for each pairwise stratum contrast, each stratum is resampled
INDEPENDENTLY (never jointly -- they are different compounds), and
Delta = mean(A) - mean(B) is computed per replicate; the percentile CI
of that Delta distribution is the actual test of "is this pairwise
difference distinguishable from zero," which CI-overlap only
conservatively approximates.

Action 4 -- multiplicity is stated explicitly rather than reading any
single CI-excludes-zero result as confirmatory: 3 pairwise contrasts x
6 representation rungs x 2 datasets = 36 individual difference-CIs
computed below (more than the 24 the mandate anticipated, since Rep 0/1
are included for completeness) -- every one is reported, and the
write-up treats all of them as exploratory, not as independent
confirmatory tests.

Action 6 -- complexity diagnostics (occupied bins, mean bins/compound)
reported at every rung, specifically to make bin-count inflation
visible rather than hidden inside the raw score.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

DATA_DIR = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence")
GOV_DIR = Path("/home/ubuntu/Documents/orthosteric/docs/governance")

_FAVORED_OCCUPANCY_DELTA = 0.4
_N_BOOTSTRAP = 10_000
_RNG_SEED = 42
_SMALL_N_APPROXIMATE_COVERAGE_THRESHOLD = 8

_STRATA_CONTRASTS = (
    ("alpha_selective", "non_selective"),
    ("alpha_selective", "intermediate"),
    ("alpha_selective", "other_selective"),
)


def load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text())


def per_compound_scores_rep23(rep_records_by_iso: dict[str, list[dict]]) -> tuple[float, float, int]:
    """Returns (raw_net_score, normalized_net_score, n_occupied_bins) for
    ONE compound, given its per-isoform Rep2/Rep3-style bin lists.
    n_occupied_bins is the count of distinct comparative keys observed
    across all isoforms -- the denominator Action 2 requires.
    """
    key_fields = ("ligand_pharmacophore_class", "residue_functional_class", "interaction_type")
    if any("geometry_bin" in r for recs in rep_records_by_iso.values() for r in recs):
        key_fields = key_fields + ("geometry_bin",)

    occ_by_key: dict[tuple, dict[str, float]] = {}
    for iso, recs in rep_records_by_iso.items():
        for r in recs:
            key = tuple(r[f] for f in key_fields)
            occ_by_key.setdefault(key, {})[iso] = r["occupancy"]

    n_alpha_favored, n_other_favored = 0, 0
    for occ_by_iso in occ_by_key.values():
        alpha_occ = occ_by_iso.get("PI3Kalpha", 0.0)
        others = [occ for iso, occ in occ_by_iso.items() if iso != "PI3Kalpha"]
        if not others:
            continue
        if alpha_occ - max(others) >= _FAVORED_OCCUPANCY_DELTA:
            n_alpha_favored += 1
        elif max(others) - alpha_occ >= _FAVORED_OCCUPANCY_DELTA:
            n_other_favored += 1

    n_occupied = len(occ_by_key)
    raw = float(n_alpha_favored - n_other_favored)
    normalized = raw / n_occupied if n_occupied > 0 else 0.0
    return raw, normalized, n_occupied


def per_compound_scores_from_pattern(records: list[dict]) -> tuple[float, float, int]:
    """Rep 0/Rep 1 counterpart: pattern already classified per record."""
    n_alpha = sum(1 for r in records if r["pattern"] == "alpha_favored")
    n_other = sum(1 for r in records if r["pattern"] == "other_favored")
    n_occupied = len(records)
    raw = float(n_alpha - n_other)
    normalized = raw / n_occupied if n_occupied > 0 else 0.0
    return raw, normalized, n_occupied


def bootstrap_ci(values: list[float], seed: int) -> tuple[float, float, float]:
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return (0.0, 0.0, 0.0)
    boot_means = []
    for _ in range(_N_BOOTSTRAP):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()
    lo = boot_means[int(0.025 * _N_BOOTSTRAP)]
    hi = boot_means[int(0.975 * _N_BOOTSTRAP)]
    return (sum(values) / n, lo, hi)


def bootstrap_difference_ci(values_a: list[float], values_b: list[float], seed: int) -> dict:
    """Action 3: resample A and B INDEPENDENTLY, compute Delta = mean(A)
    - mean(B) per replicate, return the percentile CI of Delta directly
    -- the actual test of whether the pairwise difference is
    distinguishable from zero, not a CI-overlap proxy for it."""
    rng = random.Random(seed)
    n_a, n_b = len(values_a), len(values_b)
    if n_a == 0 or n_b == 0:
        return {"mean_delta": 0.0, "ci_low": 0.0, "ci_high": 0.0, "excludes_zero": False}
    deltas = []
    for _ in range(_N_BOOTSTRAP):
        sample_a = [values_a[rng.randrange(n_a)] for _ in range(n_a)]
        sample_b = [values_b[rng.randrange(n_b)] for _ in range(n_b)]
        deltas.append(sum(sample_a) / n_a - sum(sample_b) / n_b)
    deltas.sort()
    lo = deltas[int(0.025 * _N_BOOTSTRAP)]
    hi = deltas[int(0.975 * _N_BOOTSTRAP)]
    mean_delta = sum(values_a) / n_a - sum(values_b) / n_b
    return {
        "mean_delta": round(mean_delta, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "excludes_zero": bool(lo > 0 or hi < 0),
        "approximate_coverage_only": min(n_a, n_b) < _SMALL_N_APPROXIMATE_COVERAGE_THRESHOLD,
    }


def build_stratum_data(
    dataset_label: str, rep_name: str, rep_records_by_compound: dict, stratum_by_id: dict, is_pattern_style: bool
) -> dict:
    """Per-stratum: raw values, normalized values, occupied-bin counts."""
    raw_by_stratum: dict[str, list[float]] = {}
    norm_by_stratum: dict[str, list[float]] = {}
    n_occupied_by_stratum: dict[str, list[int]] = {}

    for cid, data in rep_records_by_compound.items():
        stratum = stratum_by_id.get(cid, "unknown")
        if is_pattern_style:
            raw, norm, n_occ = per_compound_scores_from_pattern(data)
        else:
            raw, norm, n_occ = per_compound_scores_rep23(data)
        raw_by_stratum.setdefault(stratum, []).append(raw)
        norm_by_stratum.setdefault(stratum, []).append(norm)
        n_occupied_by_stratum.setdefault(stratum, []).append(n_occ)

    per_stratum = {}
    for stratum in raw_by_stratum:
        raw_vals = raw_by_stratum[stratum]
        norm_vals = norm_by_stratum[stratum]
        n_occ_vals = n_occupied_by_stratum[stratum]
        raw_mean, raw_lo, raw_hi = bootstrap_ci(raw_vals, _RNG_SEED)
        norm_mean, norm_lo, norm_hi = bootstrap_ci(norm_vals, _RNG_SEED)
        per_stratum[stratum] = {
            "n_compounds": len(raw_vals),
            "raw_net_score_mean": round(raw_mean, 4),
            "raw_net_score_95ci": [round(raw_lo, 4), round(raw_hi, 4)],
            "normalized_net_score_mean": round(norm_mean, 4),
            "normalized_net_score_95ci": [round(norm_lo, 4), round(norm_hi, 4)],
            "mean_occupied_bins_per_compound": round(sum(n_occ_vals) / len(n_occ_vals), 2),
            "approximate_coverage_only": len(raw_vals) < _SMALL_N_APPROXIMATE_COVERAGE_THRESHOLD,
            "_raw_normalized_values": norm_vals,  # kept for the difference-bootstrap step below
        }

    contrasts = {}
    for stratum_a, stratum_b in _STRATA_CONTRASTS:
        if stratum_a not in per_stratum or stratum_b not in per_stratum:
            continue
        vals_a = per_stratum[stratum_a]["_raw_normalized_values"]
        vals_b = per_stratum[stratum_b]["_raw_normalized_values"]
        contrasts[f"{stratum_a}_vs_{stratum_b}"] = bootstrap_difference_ci(vals_a, vals_b, _RNG_SEED)

    for s in per_stratum.values():
        del s["_raw_normalized_values"]

    return {"per_stratum": per_stratum, "pairwise_normalized_score_contrasts": contrasts}


def run_dataset(dataset_label: str, selection_file: str, file_map: dict[str, tuple[str, bool]]) -> dict:
    compounds = json.loads((DATA_DIR / selection_file).read_text())
    stratum_by_id = {c["compound_id"]: c["stratum"] for c in compounds}
    out = {}
    for rep_name, (filename, is_pattern_style) in file_map.items():
        data = load(filename)
        out[rep_name] = build_stratum_data(dataset_label, rep_name, data, stratum_by_id, is_pattern_style)
    return out


FILE_MAP_24 = {
    "rep0_atom_level": ("comparative_interaction_fingerprints.json", True),
    "rep1_residue_level": ("residue_level_comparative_24_rebuilt.json", True),
    "rep2_no_geometry": ("representation2_24.json", False),
    "rep3a_coarse": ("representation3_24.json", False),
    "rep3b_intermediate": ("representation3_intermediate_24.json", False),
    "rep3c_fine": ("representation3_fine_24.json", False),
}
FILE_MAP_50 = {
    "rep0_atom_level": ("expanded_comparative_interaction_fingerprints.json", True),
    "rep1_residue_level": ("residue_level_comparative_50_rebuilt.json", True),
    "rep2_no_geometry": ("representation2_50.json", False),
    "rep3a_coarse": ("representation3_50.json", False),
    "rep3b_intermediate": ("representation3_intermediate_50.json", False),
    "rep3c_fine": ("representation3_fine_50.json", False),
}

results_24 = run_dataset("24-compound", "production_pilot_compound_selection.json", FILE_MAP_24)
results_50 = run_dataset("50-compound", "expanded_pilot_compound_selection.json", FILE_MAP_50)

n_ladder_rungs = 6
n_contrasts = len(_STRATA_CONTRASTS)
n_datasets = 2
total_comparisons = n_ladder_rungs * n_contrasts * n_datasets

out_path = GOV_DIR / "GEOMETRY_LADDER_STATISTICS.json"
out_path.write_text(
    json.dumps(
        {
            "action_4_multiplicity_disclosure": {
                "n_ladder_rungs": n_ladder_rungs,
                "n_pairwise_contrasts": n_contrasts,
                "n_datasets": n_datasets,
                "total_individual_difference_cis_computed": total_comparisons,
                "statement": (
                    f"{total_comparisons} individual pairwise-difference bootstrap CIs "
                    "are computed and reported below. No multiple-comparisons correction "
                    "is pre-specified. Every result is reported, and any single "
                    "CI-excludes-zero finding among these must be read as exploratory, "
                    "not as an independent confirmatory test -- consistent with this "
                    "project's existing small-n statistical discipline elsewhere."
                ),
            },
            "n_bootstrap_replicates": _N_BOOTSTRAP,
            "rng_seed": _RNG_SEED,
            "resampling_unit": "compound (never pose); each stratum resampled independently for difference CIs",
            "24_compound": results_24,
            "50_compound": results_50,
        },
        indent=2,
    )
)
print(f"Wrote {out_path}\n")

for label, results in (("24-compound", results_24), ("50-compound", results_50)):
    print(f"=== {label} ===")
    for rep_name, rep_data in results.items():
        print(f"  -- {rep_name} --")
        for stratum, s in sorted(rep_data["per_stratum"].items()):
            approx = " [approx]" if s["approximate_coverage_only"] else ""
            print(
                f"    {stratum} (n={s['n_compounds']}): raw={s['raw_net_score_mean']:+.3f} "
                f"norm={s['normalized_net_score_mean']:+.3f} "
                f"bins/cpd={s['mean_occupied_bins_per_compound']:.1f}{approx}"
            )
        for contrast, c in rep_data["pairwise_normalized_score_contrasts"].items():
            flag = " *** excludes zero ***" if c["excludes_zero"] else ""
            print(f"    Delta({contrast}) [normalized] = {c['mean_delta']:+.3f} "
                  f"CI[{c['ci_low']:+.3f},{c['ci_high']:+.3f}]{flag}")
    print()
