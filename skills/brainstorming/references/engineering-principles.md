# Engineering Principles for This Library

These apply when *editing* a skill in this repo, not just when using one — load this file only
for that rare branch, not for ordinary routing.

- **Labeling discipline** — `spec`/`design`/`review` (SDS mode) tag every non-trivial claim
  (`[REQUIRED]`/`[CONFIRMED]`/`[ASSUMPTION]`/`[OPEN QUESTION]`/`[DECISION]`). Never let a produced
  document carry an untagged guess.
- **Stack-detection over hardcoding** — `skills/` (the generic family) must keep auto-detecting
  the target project's stack from its own manifest files, never assume a language/framework.
  Project-specific hardcoding belongs in a dedicated example folder (e.g.
  `examples/finx-script5/`), not in a generic skill.
- **Gates are not suggestions** — a skill that finds the previous phase's gate `BLOCKED` stops
  and reports, it does not proceed "since it's probably fine."
- **Evidence before assertions** — no skill in this chain should claim "done," "tested," or
  "ready" without having actually run the check that proves it (see `test`'s HARD-GATE,
  `superpowers:verification-before-completion`).
- **One numbered `docs/` sequence for every skill that persists output** —
  `00-context` (pre-existing, human-authored) → `01-discovery` → `03-srs` (`spec`, both MODE A and
  MODE B..L) → `04-sds` (`design`, both MODE A and MODE B..L) → `02-architecture` (`architecture`,
  all modes) → `05-knowledge` (`insights`). A skill's own output path must match this sequence, not
  invent its own number or a bare word-named folder. This was renumbered from an earlier
  inconsistent scheme (MODE A used to sit at `01-srs`/`02-sds`, one number behind MODE B..L) — a
  target project that already has folders from before this renumbering needs to rename them by
  hand, since skills only Glob-discover paths and never migrate existing content.
