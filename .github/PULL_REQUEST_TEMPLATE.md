<!--
Pull request checklist, transcribed from docs/ENGINEERING_STANDARDS.md §21.
This is the human review gate — distinct from the agent's own task audit (CLAUDE.md §17).
Established by ADR-0006 (A7). Answer every item; do not delete items you find inconvenient.
-->

## Checklist (ENG §21)

1. **Why is this needed?**

2. **Which Constitution section does it serve?**

3. **Which ADR authorizes it?** Was `docs/adr/` searched for an existing decision (`CLAUDE.md` §5, §1)?

4. **What scientific capability changed?**

5. **What evidence, criteria, or tier boundary changed?** *(Expected: none. Otherwise named reviewer sign-off is required.)*

6. **Any control deleted, or threshold adjusted?** *(Expected: no. `CLAUDE.md` §3.)*

7. **New files, packages, or top-level directories** — why did reuse and extension fail (`CLAUDE.md` §6; ENG §3)?

8. **Any pinned version changed?** Linked ADR (ENG §9)?

9. **Backward compatible?** If not, which versions bump (ENG §12), and was deprecation observed (ENG §10)?

10. **Tests added or updated, written before implementation** (`CLAUDE.md` §9)?

11. **Documentation updated in the owning document only** (ENG §18)? Changelog entry?

---

*Current lifecycle stage (`CLAUDE.md` header): Research — self-review + task audit; named-reviewer sign-off begins at Publication (ENG §16). This template does not add an approval requirement beyond what the current stage already requires.*
