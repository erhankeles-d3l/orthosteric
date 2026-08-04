"""orthosteric.data.sources.structural — structural evidence acquisition.

Objective: SCI0-007.
Constitution §2.1: experimental PDB structures with a bound ATP-site ligand.
AlphaFold excluded per SCI0-007 spec (defect 7) and Constitution §2.1(1).

Public API
----------
PDB connector      :class:`PDBConnector`
UniProt connector  :class:`UniProtConnector`
Structure record   :class:`StructureRecord`
Isoform mapping    :data:`PI3K_UNIPROT_MAP`
"""

from orthosteric.data.sources.structural._alphafold import AlphaFoldConnector
from orthosteric.data.sources.structural._isoform_map import (
    PI3K_UNIPROT_MAP,
    PI3KIsoform,
)
from orthosteric.data.sources.structural._pdb import (
    PDBConnector,
    StructureAdmissibility,
    StructureSource,
)
from orthosteric.data.sources.structural._structure_record import (
    ConstructDescriptor,
    StructureRecord,
)
from orthosteric.data.sources.structural._uniprot import (
    UniProtConnector,
    UniProtRecord,
)

__all__ = [
    "PI3K_UNIPROT_MAP",
    "AlphaFoldConnector",
    "ConstructDescriptor",
    "PDBConnector",
    "PI3KIsoform",
    "StructureAdmissibility",
    "StructureRecord",
    "StructureSource",
    "UniProtConnector",
    "UniProtRecord",
]
