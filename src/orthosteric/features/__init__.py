"""features package -- Structural representation construction (Phase C SCI-1).

Authority: ADR-0010 [Architectural].
Responsibility (ENG §2): feature construction -- interaction fingerprints,
residue-residue and ligand-residue contact maps, pocket descriptors,
structural graphs, comparative multi-isoform feature sets, MD-ready
representation interfaces. Consumes pocket/ representations; produces
ML-ready tensors.

Must NOT contain: structure I/O, training loops, prediction, policy decisions.
"""

from orthosteric.features._interaction_fingerprint import (
    FINGERPRINT_ALGORITHM_VERSION,
    ComparativeFingerprint,
    FingerprintConfig,
    InteractionEvidence,
    InteractionFingerprint,
    InteractionStatus,
    InteractionType,
    build_comparative_fingerprint,
    compute_interaction_fingerprint,
)

__all__ = [
    "FINGERPRINT_ALGORITHM_VERSION",
    "ComparativeFingerprint",
    "FingerprintConfig",
    "InteractionEvidence",
    "InteractionFingerprint",
    "InteractionStatus",
    "InteractionType",
    "build_comparative_fingerprint",
    "compute_interaction_fingerprint",
]
