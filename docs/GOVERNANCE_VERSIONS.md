# Governance Versions

**Single authoritative record of governance document versions.** Every protocol declares a compatibility range against this file; CI verifies the ranges are satisfied (ENG §20).

No other document restates these values.

| Document | Version | Status |
|---|---|---|
| `PROJECT_CONSTITUTION` | 4.6 | Active |
| `CLAUDE.md` | 1.0 | Active |
| `ENGINEERING_STANDARDS.md` | 1.0 | Active |
| `IMPLEMENTATION_PROTOCOL_FOUNDATION.md` | 1.0 | Active |
| `IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` | 1.2 | Active |
| `PROJECT_SPECIFICATION.md` | — | Not yet written (Constitution §7.9) |

**Operational documents** are versioned by content, not by number, and are excluded from compatibility checks: `IMPLEMENTATION_BACKLOG.md`, `SCIENTIFIC_STATE.md`, `FOUNDATION_STATE.md`.

## Compatibility declarations

Each protocol states the Constitution range it was written against. A Constitution change outside a declared range invalidates that protocol until it is revised.

| Protocol | Compatible Constitution |
|---|---|
| Foundation v1.0 | `>=4.6, <5.0` |
| Scientific v1.2 | `>=4.6, <5.0` |

**Why the major bound matters.** Constitution §A.8 requires that any amendment to Part A trigger re-derivation review of the tier architecture (§0.1), Tier 3 exclusions (§0.2), pocket definition (§2.1) and representation decision (§4.6). A major version bump therefore implies those may have changed, and every protocol state mapped to them must be re-verified rather than assumed.

## Amendment

Updating a version here requires the ADR that authorized the change (ENG §1), referenced in the row. A version recorded here without a corresponding Accepted ADR is invalid.

| Version change | Authorizing ADR |
|---|---|
| *(none yet)* | — |
