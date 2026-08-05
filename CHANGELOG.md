# Changelog

Plugin id: `agent-coding-governance-methodology@agent-coding-governance-methodology`.

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
runtime and installer were not. Those remain available at tag `v0.3.0-rc.4`.

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
