# ADR-0005 [Architectural] — Package Name

**Status:** Superseded by ADR-0007
**Date:** 2026-07-31
**Reversibility:** reversible now, costly after `FND-11`

## Decision

The distribution and import package name is **`orthosteric`** — *ortho*steric *c*omparative
*e*vidence *l*earning.

## Alternatives

| Candidate | Rejected because |
|---|---|
| `pi3k_selectivity` | Locks the name to the benchmark target. Constitution §9.6 anticipates transfer to a second family; a PI3K-specific name would misdescribe the framework if S7 succeeds |
| `orthoselect` | "select" implies selection or discovery. Constitution §1.5 lists a general-purpose discovery platform as an explicit non-goal, and §7.6 guards against discovery framing |
| `d3l` | Opaque; carries no relation to the Constitution title |
| `cel` | Too generic for a distribution name; high collision risk |

## Evidence

The Constitution title is *Comparative Evidence Learning for Mechanistic Orthosteric
Selectivity: A Framework Benchmarked on Class I PI3Ks*. The name follows the framework,
not the benchmark, which is the same discipline that produced the "benchmarked on"
phrasing.

## Review trigger

Rename is cheap before `FND-11` and expensive afterwards, since it touches every import,
the import contracts, CI check scripts and the documentation build. Revisit only if a
naming collision is discovered on a package index.
