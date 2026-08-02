"""orthosteric.data.sources.literature — literature-mining adapters.

Objective: SCI0-006b.
ADR-0003 §2: peer-reviewed publications are an approved source.

Pipeline:
  CrossRef (DOI + metadata) → PubMed (records, MeSH) → PMC OA full text
  → extraction → span verification → confidence class

Exit criteria:
  * Every extracted value resolves to a source span.
  * Unanchored extractions are rejected (not retained at low confidence).
  * OA coverage fraction and extraction audit error rate reported.
"""

from orthosteric.data.sources.literature._crossref import CrossRefConnector
from orthosteric.data.sources.literature._extractor import (
    ExtractionStatus,
    LiteratureExtractionRecord,
    OACoverageBias,
    SpanVerificationResult,
    coverage_bias_report,
    verify_span,
)
from orthosteric.data.sources.literature._pmc import PMCConnector
from orthosteric.data.sources.literature._pubmed import PubMedConnector

__all__ = [
    "CrossRefConnector",
    "ExtractionStatus",
    "LiteratureExtractionRecord",
    "OACoverageBias",
    "PMCConnector",
    "PubMedConnector",
    "SpanVerificationResult",
    "coverage_bias_report",
    "verify_span",
]
