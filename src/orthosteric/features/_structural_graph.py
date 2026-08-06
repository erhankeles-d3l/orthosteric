"""Heterogeneous structural graph for orthosteric pocket evidence.

Authority: ADR-0010 [Architectural]; SCI1-005 (part 2 of 2).
Constitution sections served: §2.1, §4.2, §4.6.

Nodes: residue, ligand_atom, water.
Edges: spatial proximity (RULE_MISSING threshold), plus optional annotation
  from SCI1-004 interaction evidence.

Scientific rule classification
  RULE_AVAILABLE:  node type vocabulary (residue/ligand_atom/water).
  RULE_AVAILABLE:  edge source (spatial proximity; interaction from SCI1-004).
  RULE_MISSING:    spatial edge distance cutoff. Not governed. Defaults to None.
  RULE_MISSING:    edge type assignment beyond "spatial". Interaction-type
    edges are available only when an InteractionFingerprint is supplied.

Design: nodes and edges are immutable and sorted deterministically. The graph
supports downstream ML (graph neural networks) via adjacency tuple.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np

from orthosteric.features._interaction_fingerprint import (
    InteractionFingerprint,
    InteractionStatus,
    InteractionType,
)
from orthosteric.pocket._pocket_definition import PocketResidueSet
from orthosteric.pocket._residue_mapping import ResidueCorrespondenceTable
from orthosteric.pocket._structure_record import LigandRecord, StructureRecord

__all__ = [
    "STRUCTURAL_GRAPH_ALGORITHM_VERSION",
    "EdgeType",
    "GraphEdge",
    "GraphNode",
    "NodeType",
    "PocketGraph",
    "StructuralGraphConfig",
    "compute_structural_graph",
]

STRUCTURAL_GRAPH_ALGORITHM_VERSION = "structural_graph_v1_sci1005"

_SPATIAL_RULE_MISSING = "RULE_MISSING: spatial edge cutoff not governed. Raw distance preserved."
_SPATIAL_SEARCH_A: float = 8.0  # implementation; not a scientific threshold


class NodeType(StrEnum):
    """Node types in the heterogeneous pocket graph."""

    RESIDUE = "residue"
    LIGAND_ATOM = "ligand_atom"
    WATER = "water"


class EdgeType(StrEnum):
    """Edge types in the pocket graph.

    SPATIAL:              within candidate search radius (RULE_MISSING threshold).
    HYDROGEN_BOND:        from SCI1-004 InteractionFingerprint evidence.
    SALT_BRIDGE:          from SCI1-004.
    PI_PI:                from SCI1-004.
    CATION_PI:            from SCI1-004.
    HYDROPHOBIC:          from SCI1-004.
    WATER_MEDIATED:       from SCI1-004 (three-node motif: lig-water-prot).
    HALOGEN_BOND:         from SCI1-004.
    METAL_COORDINATION:   from SCI1-004.
    """

    SPATIAL = "spatial"
    HYDROGEN_BOND = "hydrogen_bond"
    SALT_BRIDGE = "salt_bridge"
    PI_PI = "pi_pi"
    CATION_PI = "cation_pi"
    HYDROPHOBIC = "hydrophobic"
    WATER_MEDIATED = "water_mediated"
    HALOGEN_BOND = "halogen_bond"
    METAL_COORDINATION = "metal_coordination"


# Mapping from InteractionType to EdgeType
_ITYPE_TO_ETYPE: dict[str, str] = {
    InteractionType.HYDROGEN_BOND.value: EdgeType.HYDROGEN_BOND.value,
    InteractionType.SALT_BRIDGE.value: EdgeType.SALT_BRIDGE.value,
    InteractionType.PI_PI.value: EdgeType.PI_PI.value,
    InteractionType.CATION_PI.value: EdgeType.CATION_PI.value,
    InteractionType.HYDROPHOBIC.value: EdgeType.HYDROPHOBIC.value,
    InteractionType.WATER_MEDIATED.value: EdgeType.WATER_MEDIATED.value,
    InteractionType.HALOGEN_BOND.value: EdgeType.HALOGEN_BOND.value,
    InteractionType.METAL_COORDINATION.value: EdgeType.METAL_COORDINATION.value,
}


@dataclass(frozen=True, slots=True)
class StructuralGraphConfig:
    """Graph construction parameters. Defaults to None (RULE_MISSING)."""

    spatial_cutoff_angstrom: float | None = None

    def to_canonical_dict(self) -> dict[str, float | None]:
        return {"spatial_cutoff_angstrom": self.spatial_cutoff_angstrom}


@dataclass(frozen=True, slots=True)
class GraphNode:
    """One node in the structural graph.

    Attributes:
        node_id:           Unique string identifier.
        node_type:         RESIDUE / LIGAND_ATOM / WATER.
        residue_id:        `ResidueRecord.residue_id()` for residue nodes;
                           formatted water/metal id otherwise.
        residue_name:      3-letter PDB residue name.
        atom_name:         Atom name (for ligand_atom/water nodes); empty for
                           residue-level nodes.
        element:           Element symbol (for atom-level nodes).
        canonical_position: From SCI1-003; None if unmapped or not a residue node.
        x: y: z:           Centroid or single-atom coordinates.
    """

    node_id: str
    node_type: NodeType
    residue_id: str
    residue_name: str
    atom_name: str
    element: str
    canonical_position: int | None
    x: float
    y: float
    z: float

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "atom_name": self.atom_name,
            "canonical_position": self.canonical_position,
            "element": self.element,
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "residue_id": self.residue_id,
            "residue_name": self.residue_name,
            "x": self.x,
            "y": self.y,
            "z": self.z,
        }


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """One edge in the structural graph.

    Edges are undirected and stored with node_id_a < node_id_b for determinism.
    The `distance_angstrom` field is always the atom-level distance used to
    establish the edge (centroid-centroid for ring-based, heavy-atom otherwise).

    Attributes:
        node_id_a:          Lower node_id (deterministic).
        node_id_b:          Higher node_id.
        edge_type:          EdgeType value.
        distance_angstrom:  Raw geometry preserved regardless of classification.
        status:             "contact", "noncontact", "rule_missing", "unavailable".
        governance_note:    RULE_MISSING note or empty.
    """

    node_id_a: str
    node_id_b: str
    edge_type: str
    distance_angstrom: float
    status: str
    governance_note: str

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "distance_angstrom": self.distance_angstrom,
            "edge_type": self.edge_type,
            "governance_note": self.governance_note,
            "node_id_a": self.node_id_a,
            "node_id_b": self.node_id_b,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class PocketGraph:
    """Heterogeneous structural graph for one orthosteric pocket.

    Attributes:
        nodes:                  Sorted by node_id for determinism.
        edges:                  Sorted by (node_id_a, node_id_b, edge_type).
        structure_record_id:    Source structure.
        isoform:                Target isoform.
        algorithm_version:      Pinned version string.
        config:                 Construction config.
        n_residue_nodes:        Count of RESIDUE nodes.
        n_ligand_atom_nodes:    Count of LIGAND_ATOM nodes.
        n_water_nodes:          Count of WATER nodes.
        n_spatial_edges:        Count of SPATIAL edges.
        n_interaction_edges:    Count of interaction-typed edges (from SCI1-004).
    """

    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    structure_record_id: str
    isoform: str
    algorithm_version: str
    config: StructuralGraphConfig
    n_residue_nodes: int
    n_ligand_atom_nodes: int
    n_water_nodes: int
    n_spatial_edges: int
    n_interaction_edges: int

    def get_nodes_by_type(self, node_type: NodeType) -> tuple[GraphNode, ...]:
        return tuple(n for n in self.nodes if n.node_type == node_type)

    def get_edges_by_type(self, edge_type: EdgeType) -> tuple[GraphEdge, ...]:
        return tuple(e for e in self.edges if e.edge_type == edge_type.value)

    def adjacency(self) -> tuple[tuple[str, str, str, float], ...]:
        """Adjacency as (node_id_a, node_id_b, edge_type, distance) tuples."""
        return tuple(
            (e.node_id_a, e.node_id_b, e.edge_type, e.distance_angstrom) for e in self.edges
        )

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "config": self.config.to_canonical_dict(),
                "edges": [e.to_canonical_dict() for e in self.edges],
                "isoform": self.isoform,
                "nodes": [n.to_canonical_dict() for n in self.nodes],
                "structure_record_id": self.structure_record_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _atom_element(atom: Any) -> str:
    el = (atom.element or "").strip().upper()
    return el if el else (atom.get_name().strip().upper()[:1] if atom.get_name().strip() else "")


def _heavy(res: Any) -> list[Any]:
    return [a for a in res.get_atoms() if _atom_element(a) not in ("H", "D", "")]


def _centroid_coords(atoms: list[Any]) -> tuple[float, float, float]:
    if not atoms:
        return (0.0, 0.0, 0.0)
    vecs = np.array([a.get_vector().get_array() for a in atoms], dtype=np.float64)
    c = np.mean(vecs, axis=0)
    return (round(float(c[0]), 4), round(float(c[1]), 4), round(float(c[2]), 4))


def _classify_spatial(dist: float, cutoff: float | None) -> tuple[str, str]:
    if cutoff is None:
        return "rule_missing", _SPATIAL_RULE_MISSING
    return ("contact" if dist <= cutoff else "noncontact"), ""


def _canon_pos(res_id: str, table: ResidueCorrespondenceTable | None) -> int | None:
    if table is None:
        return None
    a = table.get_canonical_position(res_id)
    return a.canonical_position if a is not None else None


def _node_id_for_res(res_id: str) -> str:
    return f"res:{res_id}"


def _node_id_for_lig(lig_rname: str, atom_name: str) -> str:
    return f"lig:{lig_rname}:{atom_name}"


def _node_id_for_water(water_id: str) -> str:
    return f"wat:{water_id}"


def _ordered_edge(
    id_a: str,
    id_b: str,
    etype: str,
    dist: float,
    status: str,
    note: str,
) -> GraphEdge:
    a, b = (id_a, id_b) if id_a <= id_b else (id_b, id_a)
    return GraphEdge(
        node_id_a=a,
        node_id_b=b,
        edge_type=etype,
        distance_angstrom=round(dist, 4),
        status=status,
        governance_note=note,
    )


# ── Main public API ───────────────────────────────────────────────────────────


def compute_structural_graph(  # noqa: PLR0912,PLR0915
    bio_structure: Any,
    structure_record: StructureRecord,
    pocket_residue_set: PocketResidueSet,
    ligand_record: LigandRecord | None = None,
    isoform: str = "",
    correspondence_table: ResidueCorrespondenceTable | None = None,
    config: StructuralGraphConfig | None = None,
    interaction_fingerprint: InteractionFingerprint | None = None,
) -> PocketGraph:
    """Build a heterogeneous structural graph for one orthosteric pocket.

    Nodes: one per pocket residue (centroid), one per ligand heavy atom,
      one per bridging water in the structure.
    Edges: spatial (within search radius, RULE_MISSING classification) and
      interaction-typed (from `interaction_fingerprint` when provided).

    Parameters
    ----------
    interaction_fingerprint:
        When provided, interaction evidence from SCI1-004 is used to add
        typed edges (HYDROGEN_BOND, HYDROPHOBIC, etc.) in addition to the
        spatial edges derived from coordinates.
    """
    if config is None:
        config = StructuralGraphConfig()
    bio_model = next(iter(bio_structure.get_models()))
    rec_id = structure_record.record_id

    # ── Residue nodes ────────────────────────────────────────────────────────
    sorted_prs = sorted(
        pocket_residue_set.residues,
        key=lambda pr: (pr.residue.chain_id, pr.residue.residue_seq),
    )
    res_nodes: list[GraphNode] = []
    bio_residues: list[Any | None] = []
    for pr in sorted_prs:
        rr = pr.residue
        bio_res = None
        with contextlib.suppress(KeyError, AttributeError):
            bio_res = bio_model[rr.chain_id][(" ", rr.residue_seq, rr.insertion_code)]
        bio_residues.append(bio_res)
        heavy = _heavy(bio_res) if bio_res is not None else []
        cx, cy, cz = _centroid_coords(heavy) if heavy else (0.0, 0.0, 0.0)
        rid = rr.residue_id()
        res_nodes.append(
            GraphNode(
                node_id=_node_id_for_res(rid),
                node_type=NodeType.RESIDUE,
                residue_id=rid,
                residue_name=rr.residue_name,
                atom_name="",
                element="",
                canonical_position=_canon_pos(rid, correspondence_table),
                x=cx,
                y=cy,
                z=cz,
            )
        )

    # ── Ligand atom nodes ────────────────────────────────────────────────────
    lig_nodes: list[GraphNode] = []
    lig_heavy_map: dict[str, tuple[float, float, float]] = {}
    lig_rname = ""
    if ligand_record is not None:
        lig_rname = ligand_record.residue_name
        lig_bio_res = None
        try:
            bc = bio_model[ligand_record.chain_id]
            for het in (f"H_{lig_rname}", " "):
                lig_key = (het, ligand_record.residue_seq, ligand_record.insertion_code)
                if lig_key in bc:
                    lig_bio_res = bc[lig_key]
                    break
        except (KeyError, AttributeError):
            pass
        if lig_bio_res is not None:
            for la in sorted(_heavy(lig_bio_res), key=lambda a: a.get_name().strip()):
                aname = la.get_name().strip()
                v = la.get_vector().get_array()
                x, y, z = float(round(v[0], 4)), float(round(v[1], 4)), float(round(v[2], 4))
                nid = _node_id_for_lig(lig_rname, aname)
                lig_heavy_map[aname] = (x, y, z)
                lig_nodes.append(
                    GraphNode(
                        node_id=nid,
                        node_type=NodeType.LIGAND_ATOM,
                        residue_id=f"{ligand_record.chain_id}_{ligand_record.residue_seq}",
                        residue_name=lig_rname,
                        atom_name=aname,
                        element=_atom_element(la),
                        canonical_position=None,
                        x=x,
                        y=y,
                        z=z,
                    )
                )

    # ── Water nodes ──────────────────────────────────────────────────────────
    water_nodes: list[GraphNode] = []
    water_positions: dict[str, tuple[float, float, float]] = {}
    for chain in bio_model:
        for res in chain:
            if res.get_resname().strip() not in ("HOH", "WAT"):
                continue
            if "O" not in res:
                continue
            wo = res["O"]
            wid = f"{chain.id}_{res.get_id()[1]}_{res.get_id()[2]!s}"
            v = wo.get_vector().get_array()
            x, y, z = float(round(v[0], 4)), float(round(v[1], 4)), float(round(v[2], 4))
            water_positions[wid] = (x, y, z)
            water_nodes.append(
                GraphNode(
                    node_id=_node_id_for_water(wid),
                    node_type=NodeType.WATER,
                    residue_id=wid,
                    residue_name="HOH",
                    atom_name="O",
                    element="O",
                    canonical_position=None,
                    x=x,
                    y=y,
                    z=z,
                )
            )

    all_nodes = sorted(res_nodes + lig_nodes + water_nodes, key=lambda n: n.node_id)

    # ── Spatial edges ─────────────────────────────────────────────────────────
    edges: list[GraphEdge] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def _maybe_add(a_id: str, b_id: str, dist: float) -> None:
        k = (min(a_id, b_id), max(a_id, b_id), EdgeType.SPATIAL.value)
        if k in seen_edges or dist > _SPATIAL_SEARCH_A:
            return
        seen_edges.add(k)
        st, note = _classify_spatial(dist, config.spatial_cutoff_angstrom)
        edges.append(_ordered_edge(a_id, b_id, EdgeType.SPATIAL.value, dist, st, note))

    # Residue-residue spatial edges
    for i, (rn_i, br_i) in enumerate(zip(res_nodes, bio_residues, strict=False)):
        for j, (rn_j, br_j) in enumerate(zip(res_nodes, bio_residues, strict=False)):
            if j <= i:
                continue
            if br_i is None or br_j is None:
                continue
            ha = _heavy(br_i)
            hb = _heavy(br_j)
            if not ha or not hb:
                continue
            va = np.array([a.get_vector().get_array() for a in ha], dtype=np.float64)
            vb = np.array([a.get_vector().get_array() for a in hb], dtype=np.float64)
            d = float(
                round(float(np.min(np.linalg.norm(va[:, None, :] - vb[None, :, :], axis=2))), 4)
            )
            _maybe_add(rn_i.node_id, rn_j.node_id, d)

    # Ligand-residue spatial edges
    for ln in lig_nodes:
        lv = np.array([ln.x, ln.y, ln.z], dtype=np.float64)
        for rn, br in zip(res_nodes, bio_residues, strict=False):
            if br is None:
                continue
            ha = _heavy(br)
            if not ha:
                continue
            va = np.array([a.get_vector().get_array() for a in ha], dtype=np.float64)
            d = float(round(float(np.min(np.linalg.norm(va - lv, axis=1))), 4))
            _maybe_add(ln.node_id, rn.node_id, d)

    # Water edges (water-residue and water-ligand)
    for wn in water_nodes:
        wv = np.array([wn.x, wn.y, wn.z], dtype=np.float64)
        for rn, br in zip(res_nodes, bio_residues, strict=False):
            if br is None:
                continue
            ha = _heavy(br)
            if not ha:
                continue
            va = np.array([a.get_vector().get_array() for a in ha], dtype=np.float64)
            d = float(round(float(np.min(np.linalg.norm(va - wv, axis=1))), 4))
            _maybe_add(wn.node_id, rn.node_id, d)
        for ln in lig_nodes:
            lv = np.array([ln.x, ln.y, ln.z], dtype=np.float64)
            d = float(round(float(np.linalg.norm(wv - lv)), 4))
            _maybe_add(wn.node_id, ln.node_id, d)

    # ── Interaction edges from SCI1-004 fingerprint ──────────────────────────
    n_interaction_edges = 0
    if interaction_fingerprint is not None:
        for ev in interaction_fingerprint.evidence:
            if ev.status not in (
                InteractionStatus.OBSERVED,
                InteractionStatus.RULE_MISSING,
            ):
                continue
            etype = _ITYPE_TO_ETYPE.get(ev.interaction_type.value)
            if etype is None:
                continue
            if ev.primary_distance_angstrom is None:
                continue
            # Determine node IDs from evidence
            prot_nid = _node_id_for_res(ev.protein_residue_id)
            if lig_rname and ev.ligand_atom_name and ev.ligand_atom_name != "<ring_centroid>":
                lig_nid = _node_id_for_lig(lig_rname, ev.ligand_atom_name)
            elif ev.water_residue_id is not None:
                lig_nid = _node_id_for_water(ev.water_residue_id)
            else:
                continue
            id_lo = prot_nid if prot_nid <= lig_nid else lig_nid
            id_hi = lig_nid if prot_nid <= lig_nid else prot_nid
            k: tuple[str, str, str] = (id_lo, id_hi, etype)
            if k in seen_edges:
                continue
            seen_edges.add(k)
            edges.append(
                _ordered_edge(
                    prot_nid,
                    lig_nid,
                    etype,
                    ev.primary_distance_angstrom,
                    ev.status.value,
                    ev.governance_note,
                )
            )
            n_interaction_edges += 1

    sorted_edges = tuple(sorted(edges, key=lambda e: (e.node_id_a, e.node_id_b, e.edge_type)))
    n_spatial = sum(1 for e in sorted_edges if e.edge_type == EdgeType.SPATIAL.value)

    return PocketGraph(
        nodes=tuple(all_nodes),
        edges=sorted_edges,
        structure_record_id=rec_id,
        isoform=isoform,
        algorithm_version=STRUCTURAL_GRAPH_ALGORITHM_VERSION,
        config=config,
        n_residue_nodes=len(res_nodes),
        n_ligand_atom_nodes=len(lig_nodes),
        n_water_nodes=len(water_nodes),
        n_spatial_edges=n_spatial,
        n_interaction_edges=n_interaction_edges,
    )
