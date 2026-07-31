# ADR-0007 [Architectural] — Package and Repository Name: `orthosteric`

**Status:** Accepted
**Date:** 2026-07-31
**Supersedes:** `ADR-0005` (package name `orthocel`)
**Reversibility:** costly — decided before publication, when it is still one commit

## Decision

The repository and the distribution/import package are both named **`orthosteric`**.

`ADR-0005` selected `orthocel`. That decision is superseded rather than edited: ADRs are
immutable except for the Status line (ENG §1), so the reasoning behind the original choice
remains readable.

## Alternatives

| Candidate | Status |
|---|---|
| `orthosteric` | **Adopted** |
| `orthocel` | Superseded. Named the method (*ortho*steric *c*omparative *e*vidence *l*earning) but reads as an invented contraction |
| `pi3k_selectivity` | Rejected in `ADR-0005` — locks the name to the benchmark, which Constitution §9.6 anticipates transferring away from |
| `orthoselect` | Rejected in `ADR-0005` — "select" implies discovery, which Constitution §1.5 disclaims and §7.6 guards against |

## Evidence

**Collision check.** `pypi.org/pypi/orthosteric/json` returns HTTP 404 — the name is
unclaimed on PyPI. This was `ADR-0005`'s stated review trigger, and it is satisfied.

**Rename cost.** Nothing has been published: no remote, no consumers, one commit. The
rename touched the package directory, every import, `pyproject.toml`, the import contracts,
the five CI check scripts, the `Makefile`, `mkdocs.yml`, the API documentation stub, and the
governance documents. All verification passed afterwards — ruff, `mypy --strict`, 16 tests,
94% coverage, three import contracts kept, four custom checks green.

## Consideration recorded, not resolved

`orthosteric` names the **binding-site class** rather than the method. `ADR-0005` argued the
name should follow the framework, since Constitution §9.6 anticipates transfer beyond PI3K
and the title is deliberately *"benchmarked on Class I PI3Ks"*. By that reasoning
`orthosteric` is one step closer to naming the subject than the contribution.

Against that: it is a real word rather than a contraction, carries no discovery
connotation, is not target-locked, and is unclaimed. The naming decision is the project
owner's, and this trade-off is recorded so a future reader sees it was considered rather
than overlooked.

## Note on repository versus package name

These are deliberately identical here, but need not be — `scikit-learn` publishes `sklearn`.
If the package should carry the method name while the repository carries the site name, that
is a further ADR; it was not requested.

## Review trigger

A collision appearing on a package index, or a decision to publish the package under a
different name from the repository.
