"""learning package — Comparative representation learning (Phase C SCI-2).

Authority: ADR-0010 [Architectural].
Responsibility (ENG §2): comparative representation learning — always
``compound + all_isoforms -> joint_representation``, never
``compound -> activity``. Subsumes the retired ``model/`` and ``train/``
stubs.

Must NOT contain: raw structure I/O, feature construction, corpus management,
evaluation metrics (those belong in eval/).
"""
