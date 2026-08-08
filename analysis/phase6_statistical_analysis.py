"""Phase 6 -- Statistical analysis (SS17, SS18, SS23).

Computes the net comparative score (alpha-favored minus other-favored
Rep2/Rep3 bins per compound) by experimental stratum, with compound-level
bootstrap confidence intervals -- the same statistical unit discipline
already established in this project (never pose-level pseudoreplication).

For Rep2/Rep3, "alpha-favored" / "other-favored" is defined analogously
to the existing residue-level pattern classification (SS9 in the prior
Gate-3 module): among isoforms with data, does alpha's occupancy exceed
the best non-alpha isoform's occupancy by >= 0.4 (the SAME threshold
already used and documented in
features._comparative_interaction_fingerprint, not a new number invented
for this analysis), or vice versa. Applied per Rep2/Rep3 bin, then
averaged per compound, then bootstrapped per stratum -- mirroring
exactly the procedure already used for Representation 1 in commit
2f26c5c/7b3fe61, so the four representations are genuinely comparable
side by side (SS23).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

DATA_DIR = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence")
GOV_DIR = Path("/home/ubuntu/Documents/orthosteric/docs/governance")

_FAVORED_OCCUPANCY_DELTA = 0.4  # same threshold as _comparative_interaction_fingerprint.py
_N_BOOTSTRAP = 10_000
_RNG_SEED = 42  # deterministic, disclosed
_SMALL_N_APPROXIMATE_COVERAGE_THRESHOLD = 8  # matches SS17's stated n<8 caveat


def load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text())


def net_score_per_compound(rep_records_by_iso: dict[str, list[dict]]) -> float:
    """Mean(alpha_favored_bins) - mean(other_favored_bins) for one
    compound, given its per-isoform Rep2/Rep3 bin lists. A bin is
    alpha-favored/other-favored using the SAME occupancy-delta rule
    already established for Representation 1."""
    # Union of keys across isoforms (moiety, functional_class, itype[, gbin]).
    key_fields = ("ligand_pharmacophore_class", "residue_functional_class", "interaction_type")
    if any("geometry_bin" in r for recs in rep_records_by_iso.values() for r in recs):
        key_fields = key_fields + ("geometry_bin",)

    occ_by_key: dict[tuple, dict[str, float]] = {}
    for iso, recs in rep_records_by_iso.items():
        for r in recs:
            key = tuple(r[f] for f in key_fields)
            occ_by_key.setdefault(key, {})[iso] = r["occupancy"]

    n_alpha_favored, n_other_favored = 0, 0
    for key, occ_by_iso in occ_by_key.items():
        alpha_occ = occ_by_iso.get("PI3Kalpha", 0.0)
        others = [occ for iso, occ in occ_by_iso.items() if iso != "PI3Kalpha"]
        if not others:
            continue
        if alpha_occ - max(others) >= _FAVORED_OCCUPANCY_DELTA:
            n_alpha_favored += 1
        elif max(others) - alpha_occ >= _FAVORED_OCCUPANCY_DELTA:
            n_other_favored += 1
    return float(n_alpha_favored - n_other_favored)


def bootstrap_ci(values: list[float], n_boot: int, seed: int) -> tuple[float, float, float]:
    """Percentile bootstrap over the COMPOUND-level values (never poses).
    Returns (mean, ci_low, ci_high). n<8 is flagged by the caller as an
    approximate-coverage regime (SS17's mandatory small-n caveat)."""
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return (0.0, 0.0, 0.0)
    boot_means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()
    lo = boot_means[int(0.025 * n_boot)]
    hi = boot_means[int(0.975 * n_boot)]
    return (sum(values) / n, lo, hi)


def net_score_from_pattern_records(records: list[dict]) -> float:
    """For Representation 0 (atom-level) and Representation 1
    (residue-level), the pattern classification is ALREADY computed per
    record (from the existing, unchanged _comparative_interaction_fingerprint
    module) -- this just counts alpha_favored minus other_favored,
    exactly mirroring net_score_per_compound's Rep2/Rep3 logic so all
    four representations are scored by the identical rule.
    """
    n_alpha = sum(1 for r in records if r["pattern"] == "alpha_favored")
    n_other = sum(1 for r in records if r["pattern"] == "other_favored")
    return float(n_alpha - n_other)


def analyze(
    label: str,
    rep2_file: str,
    rep3_file: str,
    selection_file: str,
    atom_level_file: str,
    residue_level_file: str,
) -> dict:
    rep2 = load(rep2_file)
    rep3 = load(rep3_file)
    atom_level = load(atom_level_file)
    residue_level = load(residue_level_file)
    compounds = json.loads((DATA_DIR / selection_file).read_text())
    stratum_by_id = {c["compound_id"]: c["stratum"] for c in compounds}

    out: dict[str, dict] = {}

    for rep_name, rep_records_by_compound in (
        ("representation_0_atom_level", atom_level),
        ("representation_1_residue_level", residue_level),
    ):
        score_by_stratum: dict[str, list[float]] = {}
        for cid, records in rep_records_by_compound.items():
            stratum = stratum_by_id.get(cid, "unknown")
            score = net_score_from_pattern_records(records)
            score_by_stratum.setdefault(stratum, []).append(score)
        stratum_results = {}
        for stratum, values in score_by_stratum.items():
            mean, lo, hi = bootstrap_ci(values, _N_BOOTSTRAP, _RNG_SEED)
            stratum_results[stratum] = {
                "n_compounds": len(values),
                "mean_net_score": round(mean, 4),
                "bootstrap_95ci_low": round(lo, 4),
                "bootstrap_95ci_high": round(hi, 4),
                "approximate_coverage_only": len(values) < _SMALL_N_APPROXIMATE_COVERAGE_THRESHOLD,
                "raw_values": values,
            }
        out[rep_name] = stratum_results

    for rep_name, rep_data in (
        ("representation_2_role_aware", rep2),
        ("representation_3_role_aware_geometry", rep3),
    ):
        score_by_stratum: dict[str, list[float]] = {}
        for cid, by_iso in rep_data.items():
            stratum = stratum_by_id.get(cid, "unknown")
            score = net_score_per_compound(by_iso)
            score_by_stratum.setdefault(stratum, []).append(score)

        stratum_results = {}
        for stratum, values in score_by_stratum.items():
            mean, lo, hi = bootstrap_ci(values, _N_BOOTSTRAP, _RNG_SEED)
            stratum_results[stratum] = {
                "n_compounds": len(values),
                "mean_net_score": round(mean, 4),
                "bootstrap_95ci_low": round(lo, 4),
                "bootstrap_95ci_high": round(hi, 4),
                "approximate_coverage_only": len(values) < _SMALL_N_APPROXIMATE_COVERAGE_THRESHOLD,
                "raw_values": values,
            }
        out[rep_name] = stratum_results
    return out


results_24 = analyze(
    "24-compound",
    "representation2_24.json",
    "representation3_24.json",
    "production_pilot_compound_selection.json",
    "comparative_interaction_fingerprints.json",
    "residue_level_comparative_24_rebuilt.json",
)
results_50 = analyze(
    "50-compound",
    "representation2_50.json",
    "representation3_50.json",
    "expanded_pilot_compound_selection.json",
    "expanded_comparative_interaction_fingerprints.json",
    "residue_level_comparative_50_rebuilt.json",
)

out_path = GOV_DIR / "PHASE6_STATISTICAL_ANALYSIS.json"
out_path.write_text(
    json.dumps(
        {
            "n_bootstrap_replicates": _N_BOOTSTRAP,
            "rng_seed": _RNG_SEED,
            "resampling_unit": "compound (never pose)",
            "small_n_caveat": (
                "Strata with n<8 compounds have approximate, not guaranteed "
                "nominal, percentile-bootstrap coverage (SS17). Flagged per "
                "stratum via approximate_coverage_only."
            ),
            "24_compound": results_24,
            "50_compound": results_50,
        },
        indent=2,
    )
)

for label, results in (("24-compound", results_24), ("50-compound", results_50)):
    print(f"\n=== {label} ===")
    for rep_name, stratum_results in results.items():
        print(f"  -- {rep_name} --")
        for stratum, r in sorted(stratum_results.items()):
            approx = " [APPROX COVERAGE, n<8]" if r["approximate_coverage_only"] else ""
            print(
                f"    {stratum} (n={r['n_compounds']}): mean={r['mean_net_score']:+.3f} "
                f"95% CI [{r['bootstrap_95ci_low']:+.3f}, {r['bootstrap_95ci_high']:+.3f}]{approx}"
            )

print(f"\nWrote {out_path}")
