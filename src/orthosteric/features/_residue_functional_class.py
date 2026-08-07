"""Interaction-contextual residue functional classification.

Objective: Representation-3 mandate, sections 5-6. Derives
`residue_functional_class` from the OBSERVED interaction and its
already-resolved detector metadata (donor/acceptor role, charge sign),
never from a static per-amino-acid label. This is the residue-side
analogue of `_ligand_moiety`'s ligand-side pharmacophore classification.

Why interaction-contextual, not static: a six-class static physicochemical
grouping was explicitly rejected in review (Tyr, His, Cys each support
more than one chemically meaningful role; a static label forces an
arbitrary, information-destroying choice). Tyr participating in an
H-bond donor role and Tyr participating in a pi-pi interaction are two
different, real chemical roles for the same residue and must be able to
receive two different functional-class labels across two different
interaction records for the SAME residue -- never one fixed label
applied regardless of context.

The six-class static physicochemical grouping (aliphatic/hydrophobic,
aromatic, polar, acidic, basic, special/small) is retained ONLY as
optional secondary metadata (`static_physicochemical_class`), never as
the primary functional-role representation.

CATION_PI directionality -- confirmed limitation, not fixed here
-----------------------------------------------------------------------
Phase-0 audit of `_docking_interaction_detector.detect_cation_pi`
confirmed it resolves only ONE direction: the ligand supplies the
aromatic ring, and the PROTEIN residue supplies the cation (checked via
`rn in CATIONIC_RESIDUES` against the ligand ring centroid). It does
NOT check the reverse direction (protein residue supplies an aromatic
ring -- Trp/Tyr/Phe/His -- engaging a ligand-side cation). Per the
mandate's explicit instruction, this missing direction is NOT
implemented here (that would be new detector development, out of
scope for a representation-validation experiment) -- every CATION_PI
record from the existing detector is therefore classified
CATION_PI_CATIONIC_CAPABLE (the only resolvable direction), and
CATION_PI_AROMATIC_CAPABLE is a defined-but-currently-unreachable label,
documented so it is never silently treated as evidence of absence for
the untested direction.
"""

from __future__ import annotations

from enum import StrEnum

from orthosteric.features._docking_interaction_detector import (
    AtomResidueInteraction,
    InteractionType,
)

RESIDUE_FUNCTIONAL_CLASS_POLICY_ID = "residue_functional_class_v1_interaction_contextual"


class ResidueFunctionalClass(StrEnum):
    H_BOND_DONOR_CAPABLE = "h_bond_donor_capable"
    H_BOND_ACCEPTOR_CAPABLE = "h_bond_acceptor_capable"
    ANIONIC_CAPABLE = "anionic_capable"
    CATIONIC_CAPABLE = "cationic_capable"
    AROMATIC = "aromatic"
    HYDROPHOBIC = "hydrophobic"
    #: Residue supplies the cation in a cation-pi interaction (ligand
    #: supplies the ring) -- the only direction the current detector
    #: resolves.
    CATION_PI_CATIONIC_CAPABLE = "cation_pi_cationic_capable"
    #: Residue supplies the aromatic ring in a cation-pi interaction
    #: (ligand supplies the cation). Defined for completeness and future
    #: detector work; NEVER emitted by the current detector (see module
    #: docstring) -- its absence from real output must not be read as
    #: evidence this role is chemically absent.
    CATION_PI_AROMATIC_CAPABLE = "cation_pi_aromatic_capable"
    UNRESOLVED_FUNCTIONAL_ROLE = "unresolved_functional_role"


#: Secondary metadata only -- never the primary functional-role key.
#: Six-class static physicochemical grouping, standard in protein
#: chemistry (aliphatic-hydrophobic / aromatic / polar H-bond-capable /
#: acidic / basic / special). His is deliberately left out of a single
#: bucket here and reported as its own value, since its donor/acceptor
#: and protonation behavior is genuinely state-dependent and collapsing
#: it into "basic" or "aromatic" would assert a resolved state this
#: project has not confirmed (consistent with the existing project-wide
#: rule: do not infer protonation from identity alone).
STATIC_PHYSICOCHEMICAL_CLASS: dict[str, str] = {
    "ALA": "aliphatic_hydrophobic",
    "VAL": "aliphatic_hydrophobic",
    "LEU": "aliphatic_hydrophobic",
    "ILE": "aliphatic_hydrophobic",
    "MET": "aliphatic_hydrophobic",
    "CYS": "special_thiol",  # distinct from generic hydrophobic; real chemistry, not aliphatic
    "PHE": "aromatic",
    "TRP": "aromatic",
    "TYR": "aromatic",
    "SER": "polar_h_bond_capable",
    "THR": "polar_h_bond_capable",
    "ASN": "polar_h_bond_capable",
    "GLN": "polar_h_bond_capable",
    "ASP": "acidic",
    "GLU": "acidic",
    "LYS": "basic",
    "ARG": "basic",
    "HIS": "special_state_dependent",  # protonation/donor-acceptor state-dependent; never collapsed
    "GLY": "special_small",
    "PRO": "special_small",
}


def _hbond_class(interaction: AtomResidueInteraction) -> ResidueFunctionalClass:
    if interaction.residue_hbond_role == "donor":
        return ResidueFunctionalClass.H_BOND_DONOR_CAPABLE
    if interaction.residue_hbond_role == "acceptor":
        return ResidueFunctionalClass.H_BOND_ACCEPTOR_CAPABLE
    return ResidueFunctionalClass.UNRESOLVED_FUNCTIONAL_ROLE


def _charge_class(interaction: AtomResidueInteraction) -> ResidueFunctionalClass:
    if interaction.residue_charge_sign == "anionic":
        return ResidueFunctionalClass.ANIONIC_CAPABLE
    if interaction.residue_charge_sign == "cationic":
        return ResidueFunctionalClass.CATIONIC_CAPABLE
    return ResidueFunctionalClass.UNRESOLVED_FUNCTIONAL_ROLE


_CHARGE_CONTACT_TYPES = (InteractionType.SALT_BRIDGE, InteractionType.CHARGED_CONTACT_CANDIDATE)


def residue_functional_class(interaction: AtomResidueInteraction) -> ResidueFunctionalClass:
    """Derive the residue's functional role from the observed interaction.

    Uses only the interaction's already-resolved metadata. Never a
    static per-residue lookup.
    """
    if interaction.interaction_type == InteractionType.H_BOND:
        return _hbond_class(interaction)
    if interaction.interaction_type in _CHARGE_CONTACT_TYPES:
        return _charge_class(interaction)
    if interaction.interaction_type == InteractionType.PI_PI:
        return ResidueFunctionalClass.AROMATIC
    if interaction.interaction_type == InteractionType.HYDROPHOBIC_CONTACT:
        return ResidueFunctionalClass.HYDROPHOBIC
    if interaction.interaction_type == InteractionType.CATION_PI:
        # Only direction the current detector resolves (see module
        # docstring): residue supplies the cation.
        return ResidueFunctionalClass.CATION_PI_CATIONIC_CAPABLE
    return ResidueFunctionalClass.UNRESOLVED_FUNCTIONAL_ROLE


def static_class_for_residue(residue_name: str) -> str | None:
    """Secondary metadata only. Never used as the primary functional key."""
    return STATIC_PHYSICOCHEMICAL_CLASS.get(residue_name)
