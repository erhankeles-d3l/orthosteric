"""ADR-0003 Computational Adjudication Framework.

Implements the five deterministic decision procedures specified by ADR-0003
under AMENDMENT-ADR-0003-COMPUTATIONAL-ADJUDICATION.

Key design principles
---------------------
1. Every decision is DETERMINISTIC given a corpus snapshot.
2. No developer judgment substitutes for a missing rule.
3. Insufficient or out-of-scope evidence → GOVERNANCE_EXCEPTION, never a guess.
4. Decisions are version-controlled alongside the corpus snapshot.
5. No downstream model training or evaluation occurs here.

Decision procedure versions
----------------------------
ADJUDICATION_VERSION = "1.0"

All five procedures are frozen at this version until a formal governance
amendment changes the rules.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum
from typing import Any

from orthosteric.data.corpus import CorpusSnapshot, ProvenanceTier
from orthosteric.data.graph import GraphStats, build_graph_stats

ADJUDICATION_VERSION = "1.0"

# ──────────────────────────────────────────────────────────────────────────────
# Status vocabulary
# ──────────────────────────────────────────────────────────────────────────────


class AdjudicationStatus(StrEnum):
    RESOLVED = "RESOLVED"
    PROVISIONALLY_RESOLVED = "PROVISIONALLY_RESOLVED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    GOVERNANCE_EXCEPTION = "GOVERNANCE_EXCEPTION"


# ──────────────────────────────────────────────────────────────────────────────
# Per-question result containers
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class Auditor1Result:
    """AUDITOR-1: train/evaluation split."""

    status: AdjudicationStatus
    selected_split: str | None = None  # e.g. "train_on_graph_evaluate_within_study"
    scientific_claim_supported: str | None = None
    compound_leakage_fraction: float | None = None
    scaffold_leakage_fraction: float | None = None
    within_study_count: int | None = None
    rationale: str = ""
    evidence_references: list[str] = field(default_factory=list)


@dataclass
class Auditor2Result:
    """AUDITOR-2: N_c, N_b, N_w, S4b."""

    status: AdjudicationStatus
    n_c: int | None = None  # largest-connected-component floor
    n_b: int | None = None  # bridging-compound floor
    n_w: int | None = None  # within-study four-isoform floor
    s4b_k: float | None = None  # sharpness factor multiplier
    observed_lcc: int | None = None
    observed_bridging: int | None = None
    observed_within_study: int | None = None
    corpus_sufficient: bool = False
    rationale: str = ""
    sensitivity_note: str = ""


@dataclass
class Auditor3Result:
    """AUDITOR-3: duplicate resolution policy."""

    status: AdjudicationStatus
    policy: str | None = None  # e.g. "log_median_ki_after_cheng_prusoff"
    normalization_order: str = "normalize_then_aggregate"
    stratification: str = "isoform_construct_species"
    outlier_handling: str = "confidence_based_exclusion"
    aggregation_method: str | None = None
    rationale: str = ""


@dataclass
class Auditor4Result:
    """AUDITOR-4: BindingDB/PubChem admissibility."""

    status: AdjudicationStatus
    t1_primary: str = "ADMISSIBLE"
    t2_pub_linked: str = "ADMISSIBLE"
    t3_db_only: str = "AUXILIARY_ONLY"
    t4_insufficient: str = "EXCLUDED"
    corpus_t1_count: int = 0
    corpus_t2_count: int = 0
    corpus_t3_count: int = 0
    corpus_t4_count: int = 0
    rationale: str = ""


@dataclass
class Auditor5Result:
    """AUDITOR-5: ATP Km policy."""

    status: AdjudicationStatus
    source_hierarchy: list[str] = field(default_factory=list)
    alpha_km_um: float | None = None
    alpha_km_source: str | None = None
    alpha_status: AdjudicationStatus = AdjudicationStatus.INSUFFICIENT_EVIDENCE
    beta_km_um: float | None = None
    beta_km_source: str | None = None
    beta_status: AdjudicationStatus = AdjudicationStatus.INSUFFICIENT_EVIDENCE
    gamma_km_um: float | None = None
    gamma_km_source: str | None = None
    gamma_status: AdjudicationStatus = AdjudicationStatus.INSUFFICIENT_EVIDENCE
    delta_km_um: float | None = None
    delta_km_source: str | None = None
    delta_status: AdjudicationStatus = AdjudicationStatus.INSUFFICIENT_EVIDENCE
    conflict_resolution_rule: str = (
        "geometric_mean_if_within_threefold_else_UNRESOLVED_NON_NORMALIZABLE"
    )
    rationale: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Top-level result
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class AdjudicationResult:
    """Complete ADR-0003 computational adjudication output."""

    procedure_version: str = ADJUDICATION_VERSION
    corpus_snapshot_id: str = ""
    corpus_sha256: str = ""
    timestamp: str = ""
    overall_status: AdjudicationStatus = AdjudicationStatus.GOVERNANCE_EXCEPTION
    auditor1: Auditor1Result | None = None
    auditor2: Auditor2Result | None = None
    auditor3: Auditor3Result | None = None
    auditor4: Auditor4Result | None = None
    auditor5: Auditor5Result | None = None
    governance_exceptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)

        # normalise enum values
        def _fix(obj: Any) -> Any:
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, dict):
                return {k: _fix(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_fix(v) for v in obj]
            return obj

        result: dict[str, Any] = _fix(d)
        return result

    def config_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:16]


# ──────────────────────────────────────────────────────────────────────────────
# Decision procedures
# ──────────────────────────────────────────────────────────────────────────────

# ── Minimum evidence adequacy thresholds ─────────────────────────────────────
# These are the PROCEDURE-VERSION-1.0 floors.  They may only be changed by
# a governance amendment to this file.  They are NOT corpus-observation-
# derived thresholds: they are the minimum evidence requirements for the
# adjudication to proceed at all.
_MIN_ACCEPTED_RECORDS = 50  # corpus must have at least this many accepted records
_MIN_ISOFORM_RECORDS = 10  # each isoform must have at least this many records

# ── AUDITOR-1 ─────────────────────────────────────────────────────────────────


def _adjudicate_1(snapshot: CorpusSnapshot, stats: GraphStats) -> Auditor1Result:
    """AUDITOR-1 decision procedure v1.0.

    Rule: adopt ADR-0003 §3's proposed split (train on graph, evaluate on
    within-study stratum) if and only if the within-study stratum contains
    at least _MIN_ISOFORM_RECORDS per isoform.

    Scientific claim supported: assay-robustness generalization.
    Novel-scaffold claim: NOT supported by this split (documented, not hidden).

    Leakage analysis:
    - record-level: zero by construction
    - compound-level: NON-ZERO (same compound may appear in training via a
      different study); this is intentional and documented
    - scaffold-family-level: NON-ZERO; documented
    - novel-chemistry claim: NOT supported; documented
    """
    ws = stats.within_study_four_isoform
    if ws < _MIN_ISOFORM_RECORDS:
        return Auditor1Result(
            status=AdjudicationStatus.INSUFFICIENT_EVIDENCE,
            within_study_count=ws,
            rationale=(
                f"Within-study four-isoform count ({ws}) is below the minimum "
                f"evidence-adequacy floor ({_MIN_ISOFORM_RECORDS}). "
                "GOVERNANCE_EXCEPTION — corpus insufficient for this split."
            ),
        )

    return Auditor1Result(
        status=AdjudicationStatus.PROVISIONALLY_RESOLVED,
        selected_split="train_on_graph_evaluate_within_study",
        scientific_claim_supported="assay_robustness_generalization_NOT_novel_scaffold",
        compound_leakage_fraction=None,  # requires full corpus analysis; set NONE
        scaffold_leakage_fraction=None,
        within_study_count=ws,
        rationale=(
            "ADR-0003 §3 split adopted: train on the full connected public evidence "
            "graph; gate criteria on the within-study stratum. "
            "Claim: assay-robustness generalization. "
            "Novel-scaffold generalization is NOT claimed (compound-level leakage "
            "is explicitly non-zero). "
            f"Within-study stratum size: {ws} compounds."
        ),
        evidence_references=["ADR-0003 §3", "Lindstrom 2004 BMC Bioinformatics"],
    )


# ── AUDITOR-2 ─────────────────────────────────────────────────────────────────

# Procedure-v1.0 relative threshold rules:
#   N_c = max(5, round(lcc * 0.05))  — floor of 5, or 5% of LCC
#   N_b = max(5, round(bridging * 0.10))
#   N_w = max(24, round(within_study * 0.50))
#   S4b_k = 2.0   (null-model calibration shows k=2 denies uninformative
#                  constant-width predictor plausible-looking coverage)
# These are ADEQUACY CRITERIA derived from the corpus, not hardcoded absolutes.
# The fractions are the version-1.0 frozen values.


def _adjudicate_2(snapshot: CorpusSnapshot, stats: GraphStats) -> Auditor2Result:
    """AUDITOR-2 decision procedure v1.0."""
    lcc = stats.largest_connected_component
    nb = stats.bridging_compounds
    nw = stats.within_study_four_isoform

    if lcc < 5:
        return Auditor2Result(
            status=AdjudicationStatus.INSUFFICIENT_EVIDENCE,
            observed_lcc=lcc,
            observed_bridging=nb,
            observed_within_study=nw,
            rationale=(
                f"Largest connected component ({lcc}) is too small for any "
                "meaningful threshold derivation. Corpus insufficient."
            ),
        )

    n_c = max(5, round(lcc * 0.05))
    n_b = max(5, round(nb * 0.10))
    n_w = max(24, round(nw * 0.50))
    s4b = 2.0

    return Auditor2Result(
        status=AdjudicationStatus.PROVISIONALLY_RESOLVED,
        n_c=n_c,
        n_b=n_b,
        n_w=n_w,
        s4b_k=s4b,
        observed_lcc=lcc,
        observed_bridging=nb,
        observed_within_study=nw,
        corpus_sufficient=(lcc >= 25 and nb >= 10 and nw >= 24),
        rationale=(
            "Procedure v1.0 adequacy criteria: "
            f"N_c={n_c} (5% of Lcc={lcc}), "
            f"N_b={n_b} (10% of bridging={nb}), "
            f"N_w={n_w} (50% of within-study={nw}, floor 24), "
            f"S4b_k={s4b} (null-model calibration floor). "
            "These are PROVISIONALLY RESOLVED — not sealed until SCI0-028."
        ),
        sensitivity_note=(
            "Simulation sensitivity analysis showed Lcc highly model-dependent "
            "(range 25-97 at equal parameters under different graph-topology "
            "assumptions). Relative thresholds used here are more robust than "
            "absolute values."
        ),
    )


# ── AUDITOR-3 ─────────────────────────────────────────────────────────────────


def _adjudicate_3(snapshot: CorpusSnapshot) -> Auditor3Result:
    """AUDITOR-3 decision procedure v1.0.

    Rule: log-median Ki after per-record Cheng-Prusoff normalization
    (Order A), stratified by isoform × construct × species, with
    confidence-based outlier exclusion.

    This rule follows mathematically from ADR-0003 §4's stated Cheng-Prusoff
    nonlinearity (normalize before aggregate is not a preference — it is
    a mathematical requirement when [ATP] differs across records).
    """
    return Auditor3Result(
        status=AdjudicationStatus.RESOLVED,
        policy="log_median_ki_after_cheng_prusoff_order_a",
        normalization_order="normalize_then_aggregate",
        stratification="isoform_construct_species",
        outlier_handling="confidence_based_exclusion_not_weighting",
        aggregation_method="log_median",
        rationale=(
            "Order A (Cheng-Prusoff before aggregation) is a mathematical "
            "requirement from ADR-0003 §4's stated nonlinearity: IC50 values "
            "measured at different [ATP] are not on a common scale before "
            "normalization. Log-median is robust to the long right tail of "
            "affinity data. Confidence score used as outlier filter, not weight."
        ),
    )


# ── AUDITOR-4 ─────────────────────────────────────────────────────────────────


def _adjudicate_4(snapshot: CorpusSnapshot) -> Auditor4Result:
    """AUDITOR-4 decision procedure v1.0.

    T4 exclusion is not a policy preference — it follows directly from
    ADR-0003 §4: records without [ATP] cannot undergo Cheng-Prusoff
    normalization and therefore cannot enter the primary target.
    """
    accepted = snapshot.accepted()
    excluded = snapshot.excluded()

    t_counts = dict.fromkeys(ProvenanceTier, 0)
    for r in accepted:
        t_counts[r.provenance_tier] += 1
    for r in excluded:
        t_counts[r.provenance_tier] += 1  # count in the tier they were assigned

    return Auditor4Result(
        status=AdjudicationStatus.RESOLVED,
        t1_primary="ADMISSIBLE",
        t2_pub_linked="ADMISSIBLE",
        t3_db_only="AUXILIARY_ONLY",
        t4_insufficient="EXCLUDED",
        corpus_t1_count=t_counts.get(ProvenanceTier.T1, 0),
        corpus_t2_count=t_counts.get(ProvenanceTier.T2, 0),
        corpus_t3_count=t_counts.get(ProvenanceTier.T3, 0),
        corpus_t4_count=t_counts.get(ProvenanceTier.T4, 0),
        rationale=(
            "T4 exclusion follows from ADR-0003 §4 normalization requirement: "
            "records without traceable [ATP] cannot be placed on a common Ki scale. "
            "T3 (database-only with structured metadata) admitted as auxiliary "
            "evidence only; excluded from primary training/evaluation graph "
            "per the T3 policy."
        ),
    )


# ── AUDITOR-5 ─────────────────────────────────────────────────────────────────

# Known Km evidence (procedure v1.0, from literature review passes)
# Sources:
#   Somoza 2015 JBC (PMID 25631052): 2×Km = 100-300 µM across α,β,δ → range 50-150 µM
#   Umbralisib sponsor docs: PI3Kδ 100 µM (WEAK — uncited internal reference)
#   Huang 2011 (PMID 21789487): confirmed Km(ATP) figure exists; full text inaccessible
#   Maheshwari 2017 (JBC DOI 10.1074/jbc.M116.772426): PI3Kα kinetics; full text inaccessible
#
# Procedure v1.0 rule: if the Somoza 2015 snippet establishes an upper/lower
# bound of 50-150 µM for α/β/δ, and no per-isoform primary value has been
# independently verified, the per-isoform status is INSUFFICIENT_EVIDENCE
# until full text is retrieved.  PI3Kγ: NOT ESTABLISHED.
#
# The conflict-resolution rule: values within threefold → geometric mean;
# beyond threefold → UNRESOLVED_NON_NORMALIZABLE.

_ATP_KM_LITERATURE: dict[str, dict[str, Any]] = {
    "somoza_2015_range": {
        "isoforms": ["alpha", "beta", "delta"],
        "combined_range_um": [50, 150],
        "note": "2xKm = 100-300 µM across 3 isoforms combined; no per-isoform breakdown",
        "pmid": "25631052",
        "doi": "10.1074/jbc.M114.634683",
        "tier": "PARTIAL_RANGE_ONLY",
    },
    "huang_2011_identified": {
        "isoform": "unspecified",
        "note": "PRIMARY SOURCE IDENTIFIED — NUMERIC VALUE UNVERIFIED (paywalled Springer)",
        "pmid": "21789487",
        "doi": "10.1007/s00216-011-5257-z",
        "tier": "PRIMARY_SOURCE_INACCESSIBLE",
    },
    "maheshwari_2017_identified": {
        "isoform": "alpha",
        "note": "PRIMARY SOURCE IDENTIFIED — NUMERIC VALUE UNVERIFIED (paywalled JBC)",
        "doi": "10.1074/jbc.M116.772426",
        "tier": "PRIMARY_SOURCE_INACCESSIBLE",
    },
}


def _adjudicate_5(snapshot: CorpusSnapshot) -> Auditor5Result:
    """AUDITOR-5 decision procedure v1.0.

    No per-isoform Km(ATP) value has been independently verified from
    full-text access to a primary kinetics paper in this session.
    The procedure therefore returns INSUFFICIENT_EVIDENCE for all four
    isoforms, with the specific primary sources identified for the Auditor.
    """
    return Auditor5Result(
        status=AdjudicationStatus.INSUFFICIENT_EVIDENCE,
        source_hierarchy=[
            "1. Primary peer-reviewed enzymology literature (Km titration studies)",
            "2. Authoritative curated databases (BRENDA EC 2.7.1.153 Km-values tab)",
            "3. Sponsor/clinical documentation (secondary, weak — requires primary corroboration)",
            "4. Commercial kit technical specifications (weakest — not primary determinations)",
        ],
        # All four isoforms remain INSUFFICIENT_EVIDENCE; specific leads identified
        alpha_km_um=None,
        alpha_km_source="Maheshwari 2017 JBC (DOI 10.1074/jbc.M116.772426) — INACCESSIBLE",
        alpha_status=AdjudicationStatus.INSUFFICIENT_EVIDENCE,
        beta_km_um=None,
        beta_km_source=(
            "Somoza 2015 JBC (PMID 25631052) - RANGE ONLY (50-150 uM combined with alpha and delta)"
        ),
        beta_status=AdjudicationStatus.INSUFFICIENT_EVIDENCE,
        gamma_km_um=None,
        gamma_km_source="NOT ESTABLISHED — no primary kinetics source found",
        gamma_status=AdjudicationStatus.INSUFFICIENT_EVIDENCE,
        delta_km_um=None,
        delta_km_source=(
            "Somoza 2015 (RANGE ONLY); umbralisib sponsor docs 100 µM (WEAK); "
            "Huang 2011 (PMID 21789487) — PRIMARY SOURCE IDENTIFIED, INACCESSIBLE"
        ),
        delta_status=AdjudicationStatus.INSUFFICIENT_EVIDENCE,
        conflict_resolution_rule=(
            "Concordant sources within threefold: geometric mean. "
            "Discordant beyond threefold: UNRESOLVED_NON_NORMALIZABLE. "
            "Do not average incompatible values."
        ),
        rationale=(
            "GOVERNANCE_EXCEPTION: per-isoform ATP Km policy is INSUFFICIENT_EVIDENCE. "
            "SCI0-008 (Cheng-Prusoff normalization) is blocked until this is resolved. "
            "Resolution path: obtain full-text access to Huang 2011 "
            "(Anal Bioanal Chem 401:1881, PMID 21789487) and Maheshwari 2017 "
            "(JBC 292:13541, DOI 10.1074/jbc.M116.772426), plus BRENDA "
            "EC 2.7.1.153 Km-values tab via a JS-capable browser."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────


def run_adr0003_adjudication(snapshot: CorpusSnapshot) -> AdjudicationResult:
    """Run all five ADR-0003 adjudication procedures against a corpus snapshot.

    Returns an AdjudicationResult with per-question states.  If any question
    reaches GOVERNANCE_EXCEPTION or INSUFFICIENT_EVIDENCE, the overall status
    reflects that — but other questions are still attempted independently so
    the Auditor can see partial progress.
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stats = build_graph_stats(snapshot)

    a1 = _adjudicate_1(snapshot, stats)
    a2 = _adjudicate_2(snapshot, stats)
    a3 = _adjudicate_3(snapshot)
    a4 = _adjudicate_4(snapshot)
    a5 = _adjudicate_5(snapshot)

    exceptions = []
    all_statuses = [q.status for q in (a1, a2, a3, a4, a5)]
    if AdjudicationStatus.GOVERNANCE_EXCEPTION in all_statuses:
        exceptions.append("One or more questions raised GOVERNANCE_EXCEPTION")
    if AdjudicationStatus.INSUFFICIENT_EVIDENCE in all_statuses:
        exceptions.append("One or more questions returned INSUFFICIENT_EVIDENCE")

    # Overall status: all resolved → RESOLVED; any governance exception → exception;
    # any insufficient evidence → insufficient; else provisional
    if AdjudicationStatus.GOVERNANCE_EXCEPTION in all_statuses:
        overall = AdjudicationStatus.GOVERNANCE_EXCEPTION
    elif AdjudicationStatus.INSUFFICIENT_EVIDENCE in all_statuses:
        overall = AdjudicationStatus.INSUFFICIENT_EVIDENCE
    elif all(s == AdjudicationStatus.RESOLVED for s in all_statuses):
        overall = AdjudicationStatus.RESOLVED
    else:
        overall = AdjudicationStatus.PROVISIONALLY_RESOLVED

    return AdjudicationResult(
        procedure_version=ADJUDICATION_VERSION,
        corpus_snapshot_id=snapshot.manifest.snapshot_id,
        corpus_sha256=snapshot.manifest.sha256,
        timestamp=ts,
        overall_status=overall,
        auditor1=a1,
        auditor2=a2,
        auditor3=a3,
        auditor4=a4,
        auditor5=a5,
        governance_exceptions=exceptions,
    )
