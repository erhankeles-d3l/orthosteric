"""Build SCI1 SelectivityTarget objects from a frozen Activity Snapshot.

Objective: closes the gap between eval/_metrics.py's SelectivityTarget
(abstract) and Activity Snapshot A4 (concrete, governed). No prior module
connected these -- s1_gate_evaluation() (SCI1-022) had implementing code
but had never been executed against real data.

Governance basis
-----------------
- Panel definition: orthosteric.data.comparability.resolve_panel_key()
  (GDR-011, Option D). Only C1_PRIMARY panels contribute.
- Per-cell exact value: orthosteric.data.replicate_aggregation
  (GDR-013). Deterministic median, never last-write-wins.
- Selectivity differences (pAct_alpha - pAct_X) are computed WITHIN one
  panel only, per Constitution SS2.3(1) -- never as (value from panel A)
  minus (value from panel B). This is unchanged from GDR-013/012's own
  candidate-generation policy in mmp_candidates.py.
- Cross-panel aggregation: a compound complete in >1 C1_PRIMARY panel
  contributes one within-panel difference PER panel; the SelectivityTarget
  emitted for that compound takes the MEDIAN of those per-panel
  differences. This is a bounded, reversible, documented engineering
  choice (never mixes isoform values ACROSS panels; only aggregates
  already-valid within-panel differences), consistent with the
  replicate-median precedent (GDR-001, GDR-013).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

from orthosteric.data._comparative_example import ComparativeExample
from orthosteric.data.replicate_aggregation import aggregate_records_by_cell
from orthosteric.eval._metrics import SelectivityTarget

#: Policy identifier for this glue layer.
POLICY_ID = "sci1_target_construction_from_a4_v1"

_TIER1_ISOFORMS = ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")


def build_selectivity_targets(records: list[dict[str, Any]]) -> list[SelectivityTarget]:
    """Construct one SelectivityTarget per compound with >=1 complete
    C1_PRIMARY panel (all four isoforms, each with an exact aggregated
    value). Compounds without such a panel are excluded -- never imputed.

    Returns targets sorted by compound_id for determinism.
    """
    accepted = [r for r in records if not r.get("exclusion_reason")]
    cells = aggregate_records_by_cell(accepted)

    # panel -> compound -> isoform -> AggregatedCell
    panel_cmpd_iso: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for (panel, ik, iso), cell in cells.items():
        panel_cmpd_iso[panel][ik][iso] = cell

    # compound -> canonical_smiles (first seen, deterministic via sorted source id)
    smiles_of: dict[str, str] = {}
    for r in sorted(accepted, key=lambda r: str(r.get("source_record_id", ""))):
        ik_lookup = r.get("inchikey")
        smi = r.get("canonical_smiles")
        if ik_lookup and smi and ik_lookup not in smiles_of:
            smiles_of[ik_lookup] = str(smi)

    # compound -> list of per-panel (pac_alpha, diff_beta, diff_gamma, diff_delta, atp_mm)
    per_compound_panels: dict[str, list[tuple[float, float, float, float]]] = defaultdict(list)

    for _panel, cmpd_map in panel_cmpd_iso.items():
        for ik, iso_map in cmpd_map.items():
            if not all(
                iso in iso_map and iso_map[iso].value is not None for iso in _TIER1_ISOFORMS
            ):
                continue
            a = iso_map["PI3Kalpha"].value
            b = iso_map["PI3Kbeta"].value
            g = iso_map["PI3Kgamma"].value
            d = iso_map["PI3Kdelta"].value
            per_compound_panels[ik].append((a, a - b, a - g, a - d))

    targets: list[SelectivityTarget] = []
    for ik in sorted(per_compound_panels):
        panels = per_compound_panels[ik]
        pac_alpha = statistics.median(p[0] for p in panels)
        lr_beta = statistics.median(p[1] for p in panels)
        lr_gamma = statistics.median(p[2] for p in panels)
        lr_delta = statistics.median(p[3] for p in panels)
        smi = smiles_of.get(ik)
        if smi is None:
            continue  # cannot fit ligand-based baselines without structure
        targets.append(
            SelectivityTarget(
                pac_alpha=pac_alpha,
                lr_vs_beta=lr_beta,
                lr_vs_gamma=lr_gamma,
                lr_vs_delta=lr_delta,
                ci_half=None,  # RULE_MISSING upstream; not fabricated here
                compound_id=ik,
                smiles=smi,
                assay_atp_mm=None,  # ATP is a covariate (GDR-011), not folded in here
                within_study=True,  # every contributing panel is C1_PRIMARY by construction
            )
        )
    return targets


def compounds_for_split(targets: list[SelectivityTarget]) -> list[tuple[str, str]]:
    """(compound_id, smiles) pairs for orthosteric.eval.scaffold_split()."""
    return [(t.compound_id, t.smiles) for t in targets if t.smiles]


def to_comparative_example(target: SelectivityTarget) -> ComparativeExample:
    """Convert an eval-layer SelectivityTarget to the layer-neutral
    ComparativeExample (SI17: orthosteric.learning may not import
    orthosteric.eval; see orthosteric.data._comparative_example).
    """
    return ComparativeExample(
        pac_alpha=target.pac_alpha,
        lr_vs_beta=target.lr_vs_beta,
        lr_vs_gamma=target.lr_vs_gamma,
        lr_vs_delta=target.lr_vs_delta,
        compound_id=target.compound_id,
        smiles=target.smiles,
        within_study=target.within_study,
    )


def build_comparative_examples(records: list[dict[str, Any]]) -> list[ComparativeExample]:
    """Same construction as build_selectivity_targets(), returned as the
    layer-neutral ComparativeExample for orthosteric.learning consumers.
    """
    return [to_comparative_example(t) for t in build_selectivity_targets(records)]
