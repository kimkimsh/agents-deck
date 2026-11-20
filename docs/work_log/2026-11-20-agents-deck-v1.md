# 2026-11-20 — agents-deck v1: research, design, build, review

This log records how v1 was built and the evidence behind each decision.
It is written for whoever maintains agents-deck next, including the owner
coming back to it later: it should be possible to tell from this file alone
why the code is shaped the way it is, what was verified on a real machine,
and what was not. `docs/design.md` describes the resulting design; this file
holds the history and the evidence.

Machine for every measurement below: Ubuntu 24.04.5, GNOME Shell (mutter
46.2) on X11, Python 3.12.3, PyGObject 3.48.2, GTK 3.24.41, Warp
v0.2026.10.21 stable, Claude Code 2.1.329, Codex CLI 0.170.0 (its shared
app-server daemon 0.171.0), Antigravity CLI `agy` 1.0.3.

Project names and conversation ids from the owner's machine are left out or
shortened; no prompt text was read into this log.

## 1. The request

Show every Claude Code, Codex and Antigravity session running in Warp as an
animated pixel-art icon, in the spirit of the old Office assistant:
transparent background, only the characters visible, one per session, with
live state **including background work**. Mouse-drag position and size,
reorderable icons, a grid with configurable rows and columns, a settings
button, a dock-like feel. Clicking an icon switches Warp to that session.
A USB tablet "stream deck" later; only a skeleton now. Process asked for:
feasibility analysis, design, review, implementation, review, improvement;
an agent team; thorough discussion with Codex; web research.

## 2. Research (the evidence pack)

Each item was checked on this machine, by reading upstream source at the
installed version, or both. Labels R1–R6, A1 and A2 are the ones
`docs/design.md` cites.

**Warp focus (verified live).** Every Warp pane shell has
`WARP_TERMINAL_SESSION_UUID=<32 hex>` in its environment, inherited by the
agent. `gio open warp://session/<uuid>` switched the Warp window to the
other session's tab and back. In Warp's source (PR #11130,
`app/src/uri/mod.rs`) the handler finds the pane by that uuid across windows
and focuses window, tab and pane; an unknown uuid only logs a warning. The
link reaches the running Warp over D-Bus `org.freedesktop.Application.Open`.

**R1 — Claude Code 2.1.329** (binary strings + official docs).
- `~/.claude/sessions/<pid>.json` per running process: `status` ∈
  `busy | shell | idle | waiting`, `waitingFor`, `sessionId`, `name`,
  `nameSource`, `procStart` (a JSON string equal to `/proc/<pid>/stat` field
  22; verified on 6 live pids). Rewritten only when status changes; removed
  on clean exit.
- `busy` also covers delegated work after the turn ends (background agents,
  workflows); `shell` = idle with at least one background shell running.
- Background work in the transcript: `toolUseResult.backgroundTaskId` with a
  kind prefix (`b` shell, `a` agent, `t` teammate, `r` remote, `w`
  workflow, `m`/`s` monitor); async agents
  `{isAsync: true, status: "async_launched", agentId}`; completion as a
  `queue-operation` record whose content carries
  `<task-notification><task-id>…</task-id><status>…</status>`; `TaskStop`
  results carry `task_id`.
- `~/.claude/sessions/.fleetview-heartbeat` must never be touched: touching
  it turns on billed summaries.

**R2 — Codex CLI 0.170** (source at tag `rust-v0.170.0` + 1,010 local
rollouts, read-only).
- Rollouts `~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<threadId>.jsonl`:
  `task_started`, `task_complete` (with `error`), `turn_aborted`,
  `function_call`/`custom_tool_call` and their `*_output` (an unmatched call
  id is a running tool), sub-agent activity.
- Approval and input-request events are **not** persisted, so a passive
  reader cannot see an approval wait. (The owner runs Codex with
  `approval_policy = "never"`.)
- Processes Codex starts carry `CODEX_THREAD_ID` and `CODEX_TOOL_CALL_ID`.
- The catch: an interactive TUI connects to a shared `codex app-server`
  daemon when one is running. The rollout, the writer lock and the child
  processes then belong to the daemon, not to the TUI in the Warp pane.

**A1 — live Codex TUI probe.** Three throwaway TUIs in a pty: the TUI holds
no thread-specific file, lock or log row; `logs_2.sqlite` rows for TUI pids
have `thread_id` NULL; thread writer locks survive the TUI's exit. So "lock
held" does not mean "pane alive", and logs cannot link a pane to a thread.

**A2 — the Codex attach marker.** `~/.codex/tui-thread-reference-capabilities/<threadId>`
is an empty file whose mtime is rewritten whenever a TUI attaches to that
thread: on a fresh start (about 10 s after process start, before any
prompt), on `codex resume <id>` (+2 s), and on `/new` inside a running TUI
(+1.6 s). In-app `/resume` was not verified. This is the only TUI-side
signal found, and it is what agents-deck links Codex panes with.

**R3 — Antigravity `agy` 1.0.3** (binary and log inspection + docs).
- Per-process glog `~/.gemini/antigravity-cli/log/cli-<ts>.log`: records
  the pid, and `Created conversation <id>` / `Streaming conversation <id>`.
  The same log contains prompt text and the account email, so only those
  structural lines may be parsed.
- `brain/<id>/.system_generated/logs/transcript.jsonl` steps, append-only:
  a step is written once, with the status it had then. A background command
  stays `RUNNING` forever in that file; its end is recorded elsewhere.
- Full state (tool-confirmation waits, task counts) needs the opt-in status
  line command, which edits the user's `agy` settings. Not done in v1.

**R4 — Warp source.** Window raise uses `_NET_ACTIVE_WINDOW`; mutter 46
honours it except across workspaces. Warp also writes OSC 777 notifications
to `warp.log`, but that log contains prompt and reply text, so it is never
read.

**R5 — overlay technology (live tests).** Electron 45.2.3 renders
transparency here, but on Ubuntu 24.04
(`kernel.apparmor_restrict_unprivileged_userns = 1`) it aborts without
`--no-sandbox`, and its `setShape` click-through is experimental. GTK 3
offers `input_shape_combine_region`, `begin_move_drag`,
`set_accept_focus(False)` and keep-above as stable API, and needs no new
dependency. Tauri cannot be built here (no Rust, no WebKit headers, no
sudo).

**R6 — prior art and conventions (web).** Prior tools (notch apps, Electron
desk pets, tmux dashboards, Stream Deck plugins) mostly rely on hooks; their
reported failure is a "running tool" state that sticks after a denied or
interrupted call. Pixel-art conventions adopted: palette-indexed sprites in
code, integer scaling, 2–4 idle frames, a key frame under reduced motion,
state never shown by colour alone, and only the "needs you" states pulse.
No vendor mascot is copied.

## 3. Decisions and the pair rounds behind them

Each decision ran as a Claude + Codex pair. The two halves worked
independently, and disagreements went to a Codex judge round.

| Decision | Outcome | Why |
|---|---|---|
| Framework | GTK 3 + PyGObject + Cairo, one Python process | R5. The two halves diverged (Electron vs GTK); the judge round chose GTK. Electron's forced `--no-sandbox` and experimental shape API decided it. Zero third-party Python dependencies. |
| Codex pane ↔ thread link | Attach markers (A2), credited to the one TUI alive at that moment; ambiguity shown as "unknown"; never better than "inferred" (section 6) | The first design inferred the link from working folder and creation time. Codex's plan review called that indefensible, because a second TUI in the same folder can create the newest thread and exit between polls. The marker is the only signal tied to a TUI attaching. |
| Tablet | `SnapshotCodec` + `--dump-snapshot` only; no version stamp, no action list, no golden fixture | The judge round proposed a versioned contract. The engineering review and the owner's own rules (no coordination machinery without two concurrent writers) won: one writer, so `git diff` is the coordination. |
| Antigravity background | Reported as "not visible" (`backgroundKnown = False`) | R3: the transcript never records the end of a background command. |
| Privacy of labels | No model-written text is kept or shown (decided in section 6) | |

The judge, the Codex plan review and the engineering review all said no
model-written free text should be displayed. The first build still showed
sanitized Claude descriptions (Bash and Agent `description`, 40 characters)
in the local tooltip. The code review judge ruled that a blocker, and both
description paths were removed (section 6, R22).

## 4. Implementation notes

- **Collector thread → UI thread.** The collector polls once a second on a
  worker thread and hands an immutable `Snapshot` to GTK through
  `GLib.idle_add`. Only the UI thread touches widgets. A UI-side check
  marks the deck stale after 3 silent polls.
- **Fault boundary.** One adapter raising an exception blanks only its own
  sessions to "unknown", logged once per distinct failure (`OnceLogger`).
- **Measured costs** (engineering review): full `/proc` scan of 785
  processes, median 4.9 ms; `--dump-snapshot` end to end 0.497 s; Codex
  rollout parse 2–9 ms per file; first attach to a Claude transcript of
  66,772 lines 336–388 ms, later polls 26–65 ms.
- **Live link check.** A Codex TUI started in a pty (pid 38922) was linked
  to its new thread 2 s after its attach marker appeared. The build then
  labelled that link `EXACT`. After the code review (section 6, R01 and
  judge Part D #2) every Codex link is `INFERRED` at best, so the same check
  would now report `INFERRED`.

### Probe side effects on the owner's machine

The Codex probes touched real Codex state; nothing was deleted:

- thread `01a1bee3…` had its `updated_at` bumped by a `codex resume` probe;
- an empty thread `01a1f8e9-abe3…` was created by the live link test;
- throwaway TUIs from A1 left empty threads and markers.

## 5. Design QA on the running deck

The deck was run against the live sessions with the settings directory
pointed at the scratchpad (`XDG_CONFIG_HOME`), so the owner's real
`~/.config/agents-deck` was never written. Screenshots were cropped to the
deck. Findings and fixes:

| Seen | Cause | Fix |
|---|---|---|
| First-run shelf never appeared | `OverlayWindow.__init__` set the first-run deadline but never called `_updateShelf()`; the shelf only retargets on events | Call it at the end of `__init__` |
| Badge digit read as "H" | Badge height had no vertical padding; digit strokes touched the outline and read as a negative | Padded, rounded pill (`BADGE_PAD_Y = 1`) |
| Badge drawn at the tile origin | Painter ignored `BADGE_LEFT`/`BADGE_TOP` | Use them |
| `!`/`?` glyphs touched their bubble outline | Same negative-glyph effect | A fill row above and below each glyph |
| Characters illegible over dark windows with the light system theme | The rim was drawn only in dark theme, but what lies behind the deck does not follow the theme (the owner's system theme is light while Warp is dark) | An always-on cream rim (`#fbf7efe6`, 8-neighbour); only the shelf controls follow the theme |
| Text in windows behind showed through the shelf | Shelf alpha 0.86; GTK 3 cannot blur what is behind a window | Alpha 0.94 |

The always-on rim departs from the design review's B1 (rim on dark theme
only). It was compared against a translucent lavender rim and a
4-neighbour cream rim on four backdrops; the 8-neighbour cream rim was the
only one legible on all four.

Synthetic-event interaction run: 18 of 18 checks passed (click focuses;
jitter is not a drag; drag past 6 px reorders and saves; Esc cancels; drop
outside the shelf cancels; grip resizes 3→5 and clamps at 2; gear opens
settings; settings change columns and keep the order; reset order works).
These were synthetic GDK events, not a physical mouse.

`WarpFocuser` rejected malformed ids, and a real focus request to one of
the owner's panes completed.

## 6. Code review: Claude + Codex pair, then a Codex judge

**How it ran.** Both halves got the same brief and the same source tree,
and each formed its findings without seeing the other's. The Claude half
was a subagent; the Codex half was `codex exec` at `xhigh` effort, with the
model from `~/.codex/config.toml`. Every finding had to cite `file:line` or
a reproduction. The two sets diverged, so a Codex judge round received both
positions with their evidence. It first listed every disagreement and the
evidence that decides it, then gave verdicts, then added what both had
missed (its "Part D").

### 6.1 The two halves side by side

| | Claude half | Codex half |
|---|---|---|
| Headline | One blocker: Codex links re-derived every poll hand an exited TUI's marker to a survivor (B1). Privacy of the 40-character descriptions judged acceptable. | Blockers: wrong Codex pane after a TUI expires (R01), a >16 MiB record stalls a file (R02), raw tool names in the tablet JSON (R21), clipped descriptions still carry prompt text (R22). |
| Findings | B1; S1–S6 (should-fix); N1–N13 (nits); 9 unverified | R01–R26; an unverified list |
| Found by both | B1 ≈ R01 · S3 ≈ R02 · N1 ≈ R04 · S1/S2/N13 ≈ R16 · N9 ≈ R20 · N11 ≈ R21 · N5 ≈ R25 · N7 ≈ R26 | |
| Only this half | S4 (a new TUI with no thread row turns both panes unknown), S5 (agy reads the whole log, and a quoted line can spoof the conversation), S6 (any `task_id` + `task_type` result closed a running task), N2, N3, N4, N10, N12 | R03, R05–R15, R17–R19, R22–R24 |

**Convergence:** the sets diverged. The sharpest split was privacy: the
Claude half signed off on the clipped descriptions; the Codex half called
them a blocker.

### 6.2 Judge verdicts

- **Blockers:** R01/B1, R02/S3, R21, R22, R23, S5, and two items from Part
  D (below).
- **Should-fix:** most of the rest, including R03–R20, R24, S1, S2, S4, S6,
  N2, N3, N10.
- **Nits:** R25, R26, N4, N5, N7, N9, N12. **Report only:** N6 (dead code),
  N8 (inline literals).
- **Part D, missed by both:**
  1. raw transcript payloads enter memory before filtering (blocker);
  2. a Codex marker can be wrong even with one TUI, because Codex also
     writes it for threads a dynamic tool starts, and never rewrites it for
     a thread the process already knows (blocker);
  3. an unresolvable Codex rollout was shown as idle (should-fix);
  4. `turn_aborted` with an error was shown as idle (should-fix);
  5. Antigravity background work is never visible (coverage gap).

### 6.3 What changed

| Finding | Cause | Fix | Regression test |
|---|---|---|---|
| R01, B1, Part D #2 | Links re-derived every poll from markers; exited TUIs forgotten; markers are not proof | `CodexLinkResolver` decides each marker change once and keeps it; a TUI in its start-up window takes its first marker; every Codex link is `INFERRED` at best | `testForgettingAnExitedTuiDoesNotHandItsMarkerToASurvivor` (fails against stateless re-derivation), `testAStartedTuiDoesNotTakeASecondMarkerInItsWindow`, `testUnchangedMarkerIsNotDecidedAgain` |
| S4 | A fresh TUI has no thread row yet, so no folder match | Start-up window credit (same change) | `testNewTuiTakesItsStartupMarkerWithoutARow` |
| R02, S3, R03, R04, N1 | `JsonlTail` stalled on a long record, could attach mid-record, lost a reset after a failed open | Replaced by `LineTail`: one descriptor per read, cursor committed after success, discard mode through the next newline, attach at the start of an unfinished record | `test_line_tail.py` (11 tests; the R02 and R03 cases fail on the old logic) |
| R05 | One unreadable argv ended a live TUI | A known TUI is kept without re-reading argv | `testAMissedArgvReadDoesNotEndALiveTui` |
| R06 | Oldest-first walk preferred a suspended agent | Foreground process group wins | `testForegroundAgentWinsOverASuspendedOne` |
| R07 | Metadata read after a pid could be reused | `isRunning(pid, startTicks)` after each read; one environ read per process | `testAgentWhosePidWasReusedDuringTheScanIsNotAPane` |
| R08 | Codex mode guessed from any argv word | `CodexCli.isTui` skips option values by arity | `test_codex_cli.py` |
| R09 | Waiting keyed on the async question tool | An open `request_user_input` call → waiting (input) | `testOpenCallsAreQueryableByName` |
| R10 | Legacy `sub_agent_activity` events ignored | Both forms feed one handler; both are prefix needles | `testSubagentLifecycleAcrossBothEventForms` |
| R11 | Calls opened before the attach window were cleared | Call records are prefix needles; no prefix reset | `testCallOpenedBeforeTheAttachWindowStaysOpen` |
| R12 | Unreadable Claude transcript still drove state | Transcript-derived fields used only when read this poll | `testUnreadableTranscriptDropsEarlierTranscriptState` |
| R13, R14, S5 | agy used `rfind` over the whole log; read failure shown as idle | Incremental `LineTail`; whole-line regex with this pid; unreadable → unknown; log name time bounded on both sides | `testOnlyTheExactGlogLineFromThisPidNamesTheConversation`, `testUnreadableLogIsUnknownNotIdle`, `testConversationIdMustBeAUuid` |
| R15 | Clamp could push the gear above the screen | `max(min(…))`: the top-left stays visible | not automated |
| R16, S1, S2, N13 | `Esc` went to Warp; no grab-loss cleanup; stale "pointer inside" | Keyboard grab only for a tile drag (pointer-only fallback); one cleanup path for release, `Esc`, grab-broken and unmap; real pointer queried afterwards | not automated |
| R17 | A destroyed overlay stayed an update target | Overlay `destroy` quits the app; timers and appearance signals removed | not automated |
| R18 | A relayout move was not saved | Position saved from the confirmed configure event, once the user has placed the deck | not automated |
| R19, R20, N9 | Order cap hid live panes; caches grew forever | Cap forgets only absent panes and their timestamps; hover and shake state pruned to live panes; badge art cached by shown value; Codex index caches bounded to current markers | `testCapNeverHidesALivePane`, `testForgottenPanesLeaveNoTimestampBehind` |
| R21 | Tablet JSON carried tool names | `toolCategory` only; no background count when not visible | `test_snapshot_codec.py` |
| R22 | Clipped descriptions keep copied prompt text | Both description paths removed; `BackgroundTask` has no label | `testBackgroundShellOpensWithoutItsDescription` |
| R23 | Agent environment could set the pane id | Pane id from the pane shell only, validated at discovery | `testPaneIdComesFromTheShellNotTheAgent`, `testMalformedPaneIdIsNotAPane`, `testExecReplacedShellIsThePanesAgent` |
| R24 | Pre-existing temp file kept mode 0644 | `mkstemp` in the same folder, unlink on failure | `testFailedSaveLeavesNoTemporaryFile` |
| R25, N5 | Duplicated facts | One MCP prefix (`ToolClassifier.MCP_PREFIX`); `TILE = SpriteConstants.CANVAS`; one pane-id pattern; one app name | — |
| R26, N7 | Lambda sort key | Named `_PaneRank` key | — |
| S6 | Any task-shaped result closed a task | Only a `TaskStop` result closes one | `testTaskShapedResultOfAnotherToolDoesNotCloseTask` |
| N2, N3, N4 | Non-string title crashed; huge position overflowed GTK; async agent kind guessed from id | Type check; X11 range check; async launch is always `agent` | `test_label_sanitizer.py`, `testPositionOutsideTheScreenCoordinateRangeIsDropped` |
| N10 | Missing boot time became 0 | Boot time optional; warned once; Codex and agy stay unknown | — |
| N12, N6 | Wrong docstring; dead code | Docstring fixed; dead code written in this build removed | — |
| Part D #3, #4 | Unresolvable rollout → idle; abort error dropped | Row without rollout → unknown; abort error → error | `testPersistedThreadWithoutARolloutIsUnknown`, `testAbortWithAnErrorIsAnError` |

The new tests for B1, S4, R02, R03, R05, R07, R11, S6, R13 and Part D #3
were also run against the old behaviour patched back in (files copied aside
and restored afterwards); each failed, so they test the fix and not only the
new code.

### 6.4 Where the result departs from the judge

- **Part D #1, raw payloads in memory: not adopted as worded.** The
  constraint "no raw transcript payload in memory" came from my brief to the
  judge, not from the owner. Passive observation (decision D3) cannot work
  without parsing the lines the agents write. What was adopted: lines are
  parsed one at a time and dropped; only ids, tool names, enum values,
  counts and times are kept (design D6); prefix lines are pre-filtered by
  byte needles; the agy log yields only lines that match the whole glog
  header pattern. Codex argv is likewise read transiently, and only a
  yes/no "is the TUI" survives.
- **S5, adopted in part.** The judge preferred a producer-side metadata
  source or "unavailable". No such source exists without an opt-in
  (section 11 of the design), so the log is read incrementally with a strict
  whole-line match instead.
- **R09, evidence instead of a blocking-mode check.** The judge wanted
  evidence of blocking mode before showing an open `request_user_input` as
  waiting. The Codex source (`request_user_input.rs`) sets
  `is_blocking: mode == ModeKind::Plan` but awaits
  `session.request_user_input(...)` in every mode. So an open call is a
  wait in any mode, and no mode check is needed.
- **R02, no gap signal.** The judge asked that a skipped oversized record be
  reported to the owner "until state is recoverable". `LineTail` skips the
  record and continues, but tells nobody. A record that is skipped (over
  16 MiB on one line) and that would have closed a tool call leaves that
  tile in `tool` until the next turn starts. Not done because no agent was
  seen writing a record that large; a `mSkipped` flag on `TailBatch` is the
  place to add it.
- **R20, Claude's closed-task set kept unbounded, as the judge ruled.** It
  stops a later record that mentions a finished task from reopening it, and
  it lives only as long as one transcript.

### 6.5 Still open after the review

- Antigravity background work stays "not visible" (Part D #5). It needs the
  opt-in status-line source.
- An in-app `/resume` inside a running Codex TUI may leave no new marker,
  so the tile can keep showing the previous thread. The tooltip says the
  link is a guess.
- N8 (inline literals) was report-only and is unchanged.

## 7. Verification

Commands run at the end, from the repository root:

| Check | Command | Result |
|---|---|---|
| Unit tests (full suite; the final check spans most targets) | `python3 -m unittest discover tests` | 107 tests, OK |
| Regression tests added after that run (R05, R07, the `exec` case, Part D #3) | `python3 -m unittest tests.test_pane_scanner tests.test_codex_tui_registry tests.test_codex_adapter` | 13 tests, OK; no production file changed since the full run |
| Type check | `pyright` (stubs from the gitignored `.venv`) | 0 errors, 0 warnings |
| Live snapshot | `XDG_CONFIG_HOME=<scratch> python3 -m agents_deck --dump-snapshot` | 0.49 s; 3 Claude panes (thinking, idle, tool/shell), all `exact`; JSON keys exactly `pane, agent, phase, phaseSince, waitingFor, toolCategory, background, confidence` |
| GUI smoke run | overlay for 6 s with a scratch `XDG_CONFIG_HOME`, then `SIGTERM` | clean exit, empty stderr; settings saved with 3 panes in the order and no position (default placement is not pinned) |
| README images | `.venv/bin/python -m tools.render_readme_images docs/images` | byte-identical to the previous render |

**Not verified:**

- No Codex or Antigravity session was running during the final live
  checks, so their adapters were exercised only by unit tests in this
  round. The Codex link was last checked live before the review fixes
  (section 4).
- A physical mouse and `Esc` with the new keyboard grab under mutter, a
  grab broken by a shortcut or screen lock, the R15 clamp with a deck larger
  than the screen, multi-monitor moves, and Warp focus across workspaces.
- Whether the docs read clearly to someone new to the project: they were
  checked against the code, not tested on a reader.

## 8. Packaging: one executable, an icon, a launcher

Asked for: build agents-deck into a program that starts from a double-click
on its icon, give it a good icon, and add a Makefile so anyone can do the
same.

| Decision | Why |
|---|---|
| A zipapp (`python3 -m zipapp`), not PyInstaller | The app needs the system GTK bindings anyway. A zipapp is one 88 KB file, needs only the standard library to build, and runs on `/usr/bin/python3`. PyInstaller would bundle Python and GTK typelibs, which is large and breaks easily. |
| The package's own `__main__.py` is the zipapp's entry | `zipapp --main` generates an entry that drops the exit status of `main()`. Reusing the file keeps one entry point and keeps the status. |
| Desktop entry named after the app id (`dev.agentsdeck.AgentsDeck.desktop`) | GNOME Shell matches a window to its app through `_GTK_APPLICATION_ID`; with the same name the running deck gets the new icon. |
| Makefile reads the app id and name from `AppConstants` | One definition of each; the desktop-entry template gets them by substitution. |
| Desktop launcher marked trusted with `gio set … metadata::trusted true` | The desktop icons extension (`ding`) runs a launcher only when it is executable and trusted. If `gio` fails, the user is told to choose Allow Launching. |
| No `gtk-update-icon-cache` | The user icon folder had no cache; creating one would hide icons other apps add later without updating it. `make install` touches the folder instead, so GTK distrusts a cache older than the new icon. |
| Icon drawn by `tools/render_app_icon.py` from the real sprites | The icon cannot drift from the characters. A smooth squircle plate in the sprites' ink colours, a warm glow taken from the Claude body colour, characters at a whole-number scale per size: the idle hero up to 48 px, the hero with its thought bubble at 64 and 96 px, the three-character lineup from 128 px. No 16 px icon, because the hero cannot be drawn below one screen pixel per sprite pixel. |

Verification, run here:

| Check | Result |
|---|---|
| `make` | builds `build/agents-deck` (zipapp, `#!/usr/bin/python3`), 8 icon sizes, the desktop entry; `desktop-file-validate` silent |
| `build/agents-deck --dump-snapshot`, run from `/tmp` | 3 live sessions, 0.60 s |
| `tests/test_app_icon.py` | 2 tests OK; fails with a 16 px size (scale 0) and with a 97 % fill (content wider than the plate) |
| `make install` | 4 files plus 8 PNGs, all under `$HOME`; launcher `metadata::trusted: true` |
| `gio launch ~/Desktop/agents-deck.desktop` (what a double-click does) | process `agents-deck` on `/usr/bin/python3.12`; window `_GTK_APPLICATION_ID = dev.agentsdeck.AgentsDeck`, `WM_CLASS = agents-deck`; no output on stderr |
| Second launch through the app menu entry (`gtk-launch`) | still one process; the running deck is brought forward |
| SIGTERM | clean exit |
| `pyright` | 0 errors |

Not verified: a physical double-click on the desktop icon (the `gio launch`
path is the same launcher code, but the click itself was not made), and
how the icon looks in the dock and app grid.
