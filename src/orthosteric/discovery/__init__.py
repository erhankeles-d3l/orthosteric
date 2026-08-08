"""Label-blinded discovery-phase package (Rev. 5 mandate SS5-SS11).

Corpus assembly, motif enumeration, eligibility, permutation nulls, and
scaffold-held-out generalization. Every module in this package is
architecturally forbidden (`.importlinter` Contract 5) from importing
`orthosteric.data.sealed_labels` -- discovery-phase code must never see
sealed retrospective labels before the one-time SS12 unblinding event.

Contract 5 was verified to actually fire (Stage A audit, this commit):
a deliberate violating import was added, confirmed BROKEN by
import-linter with the exact offending line identified, then removed.
An unfired contract is untested; this one is now known to work.

Empty pending Stage E execution. Created now (Stage A) so the import
barrier protects this package from its first real module onward,
rather than being added reactively after discovery code already exists.
"""

from __future__ import annotations
