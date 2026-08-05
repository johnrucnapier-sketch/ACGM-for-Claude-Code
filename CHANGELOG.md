# Changelog

Plugin id: `acgm@acgm` since 0.6.0. Versions up to 0.5.1 shipped as
`agent-coding-governance-methodology@agent-coding-governance-methodology`; that
line is left as written rather than rewritten to match the present.

## [0.8.0] — 2026-08-05

### Changed — breaking

- **The four fields now ride on the command, as comment lines.** They used to be
  read from the agent's most recent message, which put the check on the wrong side
  of a race (E-027): identical calls were sometimes accepted and sometimes denied
  for missing fields, and a stale read could surface an *earlier* operation's
  fields and authorise something they were never written for (E-025).

  ```bash
  # ACGM-EVIDENCE: ls -d /Applications/Foo.app confirmed the bundle exists
  # ACGM-CURRENT-STATE: not running; no matching process
  # ACGM-VERIFY-AFTER: ls -d must report no such file
  # ACGM-ROLLBACK: reinstall from the 300110 build
  rm -rf /Applications/Foo.app
  ```

  The command is the one thing the hook always receives intact, and it is the
  thing being authorised. Fields carried on it cannot be stale, cannot go missing
  on timing, and cannot license a different call. **Nothing about approval
  changes** — an incomplete gate is still denied and the agent retries; a complete
  one still emits no decision and goes to the normal permission flow. The only
  visible difference is four comment lines above the operation.

- The shell filter skips whole-line comments, so a rollback plan that names a
  destructive command no longer makes a harmless command look destructive.
- The transcript is still read for the EVIDENCE check, which is unavoidable — it
  asks whether a read-only call happened. That check can only fail *closed* under
  the same race, costing one retry, never a false pass.

### Verified in a live session

Claimed fixed and then checked, in that order. On v0.6.1 the install of this very
release needed three attempts before its fields were seen. On v0.8.0 the gate
denied a bare `rm -rf`, printed the new format, and accepted the identical command
carrying the four fields as comments — first try, no prompt, no retry.

## [0.7.0] — 2026-08-05

### Added

- **CASES.md Case 14** — the first case from the project the methodology was built
  for, rather than from the plugin repairing itself. Around ten parallel work
  streams, catastrophic cross-stream drift, cleared by a few audit rounds; and then
  months in which the layer rarely produced anything resembling a rescue, because
  problems now die during the check-current-state step.
- **METHODOLOGY meta-observation: governance return is front-loaded, then
  invisible.** First it clears existing rot — dramatic and countable. Then it
  prevents new rot, where success looks like nothing happening. Counting saves
  measures the second phase at zero, so **a falling intervention count is the
  expected signature of success and is worthless as evidence in either direction
  without its denominator** — and equally, quietness cannot be used to argue the
  mechanism is alive.
- EVIDENCE **E-026** (the above, with the owner's untestable counterfactual marked
  as exactly that) and **E-027** (below).

### Fixed

- **`acgm_activity` counted allowed operations as misses.** A complete gate emits
  `{}` and leaves no fingerprint, so every legitimately permitted call looked
  ungated — 3 of 15 in a real project. Presence of ACGM's own PreToolUse record now
  settles whether the gate ran, whatever the record says.
- **GAPS is now labelled a candidate list, not a verdict.** Even after the fix, an
  allowed gate does not always leave a record. The one call still flagged in that
  project was checked by hand and had been denied, re-evidenced, and correctly
  allowed on retry. Reporting it as a miss would have been the overclaiming this
  project exists to prevent.

### Known defect (recorded, not fixed)

- **The gate's field check depends on a race** between the transcript flush and hook
  execution. Two calls of identical shape — fields written in the same assistant
  turn as the command — one passed, one was denied for missing fields. The visible
  direction is a false denial and is safe; the invisible direction reads a stale
  turn and surfaces an older turn's fields, which is E-025's false pass. **BINDING
  is currently the only thing standing between that race and an unauthorised
  operation.** Reading the fields from the transcript at all is the root cause.

## [0.6.1] — 2026-08-05

### Fixed

- **The four fields must name the operation they authorise.** The gate reads the
  most recent assistant text. After one gated operation succeeded, those fields
  were still the most recent text, so the *next* destructive call inherited them
  and passed. A command that should have been held was observed passing this way,
  and the pass was first misdiagnosed as the command not being destructive at all.

  A new BINDING check requires at least one operand from the command — a path, a
  plugin id, a branch name — to appear in the fields. Evidence written for one
  target no longer licenses another. Basenames count, so a field may cite a path
  in an equivalent form. Commands with no identifiable operand are not blocked on
  this ground; the check does not invent a failure it cannot substantiate.

  Two existing tests began failing when this landed, because they authorised a
  path with fields describing a plugin install. The check was right and the
  expectations were wrong. EVIDENCE E-025.

- The same defect has a benign twin: the gate sometimes denies fields that *were*
  written, because the text block has not reached the transcript when the hook
  reads it. That direction is a false denial and is safe; it is recorded rather
  than fixed, since restating the fields resolves it.

### Changed

- **Descriptions spell ACGM out.** The plugin, marketplace and repository
  descriptions said "governance for long-horizon Claude Code development" without
  once expanding the acronym they are named after: **Agent Coding Governance
  Methodology**.
- The "why Claude Code only" section no longer says Codex support "was removed".
  That was true of the old repository and is now misleading, since `ACGM-for-Codex`
  exists as a separate adapter. The split is stated as one of repository and
  evidence: nothing measured here validates that adapter.
- README credits its authors, including the model that co-wrote the v0.4–v0.6
  rebuild, and states plainly that most defects fixed in those versions were
  introduced during that rebuild and caught by reading evidence.

## [0.6.0] — 2026-08-05

### Changed

- **Renamed.** The plugin and marketplace are now `acgm`, so the id is
  `acgm@acgm` and skills are invoked as `/acgm:truth-first`. The previous id was
  71 characters and had to be typed to install anything.
- The repository is `ACGM-for-Claude-Code`, a sibling of `ACGM-for-Codex` rather
  than a standalone phrase. "Methodology" in a repository name reads as a
  document; people looking for a plugin scroll past it.

### Notes

- Renaming changes the id, so an existing install is not upgraded in place: the
  old id must be uninstalled and `acgm@acgm` installed. Because plugins are
  user-scope, that is one uninstall and one install for the whole machine, not
  one per project.
- Discovery is carried by the description and topics far more than by the name.
  The rename is for the person typing the install command.


## [0.5.1] — 2026-08-05

### Fixed

- **Marketplace inspection is not marketplace mutation.** The whitelist matched
  the bare noun `claude plugin marketplace`, so `marketplace list` — and even
  `marketplace --help` — were gated. The patterns now name the mutating
  subcommands (`add`, `remove`, `update`, `refresh`).

  Deliberately not fixed by exempting read-only subcommands: the filter matches
  substrings, so an exemption for `list` would have let
  `claude plugin uninstall x && claude plugin list` through on the `list`.
  Narrowing the positive pattern has no such hole.

  Third false positive of the same family in one day — `2>/dev/null`, then
  `--help`, then this. All three share a cause: matching a fragment of an
  invocation instead of the operation it performs. Precision debt is only
  visible once a gate denies (EVIDENCE E-024).

## [0.5.0] — 2026-08-05

### Added

- **`scripts/acgm_activity.py` — activation you can check after the fact.**
  Doctor honestly refuses to report runtime activation, because a subprocess
  cannot observe the session that started it. That left a real question
  unanswered: *did the plugin actually do anything over in that other project?*
  This reads it out of each session's recorded hook output.

  Three properties it is built around, each one a mistake already made in this
  repository:

  - **Attribution reads the mechanism's own output, keyed by tool call.** Never a
    text search — a transcript is full of the gate's own wording that the agent
    quoted, printed or `cat`-ed. Counting those is CASES Case 11.
  - **Counts come with their denominator.** "The gate never fired" and "the gate
    is not installed" are indistinguishable until you know how many destructive
    commands it had the chance to catch.
  - **The finding worth acting on is the gap** — a destructive call with no gate
    decision against its id. Reported separately from `INACTIVE`, which means no
    hook output at all: the second is broader, and calling it a gap would
    understate it.

  It also distinguishes hook versions by their wording, so a session running
  stale hooks is visible, and it announces truncation rather than silently
  showing the first few.

### Changed

- Doctor's activation note now points at the activity report instead of ending
  at "not provable from here".

### Notes

- The reporter re-implements the shell filter's classification in Python.
  `tests/test_activity.py` sends one corpus through both and fails on any
  disagreement — the duplication is not prevented, it is made loud.
- The first draft of the reporter found every `ask` and no `deny`, minutes after
  a deny had been watched happening. A denied call is recorded as an error
  `tool_result`, an asked one as a hook attachment. Both are read now, and both
  shapes are covered by tests.

## [0.4.2] — 2026-08-05

### Fixed

- **Discarding output is not writing.** The first real command after the gate
  started denying was a read-only inspection of `~/.claude` — `ls`, `du`, `test`
  — and it was blocked. The agent-config rule treats any `>` as a write, and
  `2>/dev/null` contains one. Redirects to `/dev/null` and `2>&1` are now
  stripped from the string used for matching, never from the command itself; a
  write to a real path under the directory still carries its own `>` and is
  still caught.

  Worth stating plainly: this false positive appeared within one command of the
  gate gaining real teeth. A gate that only *asks* can carry sloppy patterns
  indefinitely, because nothing downstream depends on them being right. Denying
  is what made the imprecision cost something.

## [0.4.1] — 2026-08-05

### Fixed

- **The gate denies instead of asking.** v0.4.0 returned `permissionDecision:
  "ask"` for an incomplete gate. Against a real destructive command the hook
  fired — the transcript records it against that exact `toolUseID` — and the
  command ran anyway, with no prompt: an `ask` is routed through the session's
  permission mode, and an auto-accepting mode turns it into a no-op. An
  incomplete gate now returns `deny`; supplying the four fields lifts the block,
  and a complete gate emits no decision so the human is reached through the
  normal flow. See EVIDENCE E-023.

  The version is bumped rather than patched in place because Claude Code keys its
  plugin cache on the version string — reusing it would leave an installed copy
  on the old code. That lesson comes from the 0.3.0-rc notes, and it was right.

## [0.4.0] — 2026-08-05

Rebuilt from the v0.1 skeleton. The 0.3.0-rc line is not an ancestor of this
release: its wording improvements were carried over deliberately, its Python
runtime and installer were not. That line is preserved at tag `v0.3.0-rc.4` in the
archived predecessor repository, `johnrucnapier-sketch/Agent-Coding-Governance-Methodology`,
along with the v0.1 history that CASES Case 10 cites as its evidence. It is not
carried into this repository, and it is not deleted either.

### Fixed

- **The plugin can be installed.** `plugin.json` declared `"skills": "skills/"`
  and `"hooks": "hooks/hooks.json"`. Declared paths must start with `./`, and
  `hooks/hooks.json` is auto-loaded, so declaring it fails as a duplicate. v0.1
  could not load from a clean install by anyone; it appeared to work on the
  author's machine only because a directory-source cache had captured an
  uncommitted variant of the manifest. See CASES.md Case 10.
- **The PostToolUse hook no longer edits files.** It appended a marker comment
  into the governance document it had just flagged — on a false positive — while
  the skill text promised it did not. It now returns an advisory and touches
  nothing, and `ACGM-REVIEWED` silences it on a reviewed document.

### Changed

- **The destructive-operation gate checks structure, not prose.** v0.1 grepped
  for the literal markers `(a)`–`(d)`; four characters satisfied it. The gate now
  requires: four named fields carrying real content (templates, `TBD`, `n/a`,
  `待定` rejected); the operation isolated in its own tool call, with no `;`,
  `&&`, `||`, pipe, redirection, subshell, or command-substituted target; and a
  read-only tool call already present in the session. All three are decided from
  the tool call and the transcript, so none can be produced by writing text.
  A complete gate still returns `ask` — evidence is never authorization.
- **The destructive whitelist covers agent-owned state.** v0.1 gated an `rm -rf`
  against a non-existent directory and let `claude plugin uninstall` through
  silently. Added: plugin management, global package installs, writes into
  `~/.claude`, `curl | sh`, and the remaining history-rewriting Git commands.
- **Skills adopt the 0.3.0-rc wording** for the four fields, the three-call
  separation, and the four-state distinction (source verified / configuration
  verified / runtime activated / project governed) — without its surface
  enumeration or installation content.
- **SessionStart declares its own limit.** The injected message now states that
  it proves only that SessionStart ran, and points at doctor for the rest.

### Added

- `acgm-doctor.sh` — manifest shape, official validation, hook wiring, skill
  discovery, registration, and cache-versus-source drift. It reports runtime
  activation as **not provable from here**, because doctor is a subprocess and
  cannot observe the session that invoked it.
- `SessionEnd` hook — reports `ACGM-VERIFY-AFTER` promises the session is ending
  without room to have kept. Appends to `.governance/OPEN_OBLIGATIONS.md` only
  where that directory already exists; it never creates governance files in a
  project that has none.
- **CI that asks whether Claude Code accepts the package** — official validation,
  then a real install from the checkout, then asserting `enabled`. The 0.3.0-rc
  line shipped ~4400 lines of tests, an 8-check release contract and a 3-OS
  matrix without ever running the validator or attempting an install.
- Contract and behaviour tests, hermetic by construction. The suite runs with
  `CLAUDECODE` both set and unset, because the 0.3.0-rc suite read the process
  environment inside the code under test and passed only where CI never runs
  inside Claude Code.
- CASES.md 10–13 — all four observed on 2026-08-05 in this repository.

### Boundaries

- Runtime activation is never claimed from configuration evidence.
- ACGM does not require, extend or delegate to any other skill system.
- No installer. Installation is `claude plugin marketplace add` plus
  `claude plugin install`; a correct manifest is what makes that work.
