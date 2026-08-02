"""orthosteric.data.sources — source connectors for public bioactivity databases.

Objective: SCI0-006.
Constitution §0.1 / §0.4: every record is tier-tagged at ingestion;
Tier 2 records are routed through the information barrier immediately.
ADR-0003 §2: ChEMBL, BindingDB, PubChem BioAssay are approved sources.

Public API
----------
Common interface    :class:`SourceConnector` (ABC)
ChEMBL              :class:`ChEMBLConnector`
BindingDB           :class:`BindingDBConnector`
PubChem BioAssay    :class:`PubChemConnector`
Ingested record     :class:`RawSourceRecord`
"""

from orthosteric.data.sources._base import RawSourceRecord, SourceConnector
from orthosteric.data.sources._bindingdb import BindingDBConnector
from orthosteric.data.sources._chembl import ChEMBLConnector
from orthosteric.data.sources._pubchem import PubChemConnector

__all__ = [
    "BindingDBConnector",
    "ChEMBLConnector",
    "PubChemConnector",
    "RawSourceRecord",
    "SourceConnector",
]
