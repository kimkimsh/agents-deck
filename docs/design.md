# agents-deck v1 design

**Who this is for:** whoever changes agents-deck next. It describes what the
code does today and why it has this shape, so that a change can be made
without re-deriving the reasons. The history (what was tried, what was
measured, who disagreed) is in `docs/work_log/`. Section labels such as [R1]
or [A2] point at the evidence there.

**What agents-deck is.** A transparent, always-on-top desktop overlay. It
shows one animated pixel-art character for each Claude Code, Codex or
Antigravity CLI (`agy`) session running in a Warp terminal pane. The
character shows what the session is doing, including background work.
Clicking it switches Warp to that pane.

**Where it runs.** Ubuntu 24.04, GNOME Shell (mutter 46) on X11, Python
3.12, PyGObject 3.48, GTK 3.24. No root needed and no `pip` dependencies.
Wayland is out of scope for v1.

**The one rule that shapes everything else.** agents-deck only *reads*
files the agents already write. It installs no hooks, edits no agent
configuration, and connects to no agent socket. Every limitation listed
below ("not observable", "a guess") follows from this rule. Lifting it is a
user opt-in, not a code change (section 11).

---

## 1. Requirements and how v1 meets them

| # | Requirement | v1 answer |
|---|---|---|
| F1 | One icon per Claude Code / Codex / Antigravity session in Warp | Process discovery under Warp pane shells (section 4) |
| F2 | Live state, including background work | One adapter per agent; background tasks shown as a count badge and in the tooltip (section 6) |
| F3 | Transparent; only the characters visible | GTK RGBA window drawn with Cairo; an input shape lets clicks through everywhere else (section 8) |
| F4 | Pixel art, cute but refined; a dock-like feel | Original 24×24 sprites at integer scale on a translucent shelf, hover lift (section 9) |
| F5 | Move and resize by mouse | Native window-manager move from the shelf; a corner grip steps the integer scale |
| F6 | Reorder icons | Drag a tile; order saved per Warp pane id |
| F7 | Grid of rows × columns, settings button | Settings window opened from the gear |
| F8 | Click an icon → Warp switches to that session | Opens `warp://session/<pane id>` (section 7) |
| F9 | Tablet "stream deck", skeleton only | `SnapshotCodec` and `--dump-snapshot` (section 10) |

## 2. Decisions

Each decision states what it costs and what would reverse it.

### D1. GTK 3 + PyGObject + Cairo, one Python process

- **Why:** GTK provides the four window behaviours the overlay needs as
  stable API: `input_shape_combine_region` (click-through),
  `begin_move_drag` (native move), `set_accept_focus(False)` (never steals
  the keyboard) and keep-above. The bindings ship with Ubuntu, so there are
  no third-party Python dependencies. Electron was rejected: on this Ubuntu
  it only starts with `--no-sandbox`, and its click-through shape API is
  experimental [R5].
- **Costs:** a future tablet client (a browser page) cannot reuse the Cairo
  drawing. It can reuse the snapshot format and the state rules.
- **Reverse when:** the tablet becomes the main surface, or Wayland support
  is required. Both favour a web renderer.

### D2. A collector thread for all reads, the GTK main thread for the UI

- The collector thread does every file and `/proc` read. Once a second it
  builds an immutable `Snapshot` and hands it to the UI thread with
  `GLib.idle_add`. The UI thread never reads agent files. So session state
  has exactly one writer.
- **Costs:** a thread boundary. Only immutable values cross it.
- **Reverse when:** a measured poll stays under ~2 ms in the worst case;
  then it can run as a `GLib.timeout_add` on the main loop.

### D3. Passive observation only

- See "the one rule" above.
- **Costs:** Codex approval waits and Antigravity tool-confirmation waits
  are never written to a file, so they cannot be shown. Antigravity
  background work is not visible either.
- **Reverse when:** the user opts in to an integration (section 11).

### D4. Say "can't tell" instead of guessing

Every observation carries a link confidence: `exact`, `inferred` or
`unknown`, and a phase that can be `unknown`. "Could not read the state" is
never drawn as "idle": an unknown tile is faded, and its tooltip says why.
An unknown tile can still be clicked, because the Warp pane is always known.

### D5. Tablet: a snapshot format now, no listener

v1 has `SnapshotCodec` and `python3 -m agents_deck --dump-snapshot`. There
is no network listener, because the transport depends on the tablet's OS
(Android can use `adb reverse`; an iPad cannot), which is undecided. The
format has no version stamp, action list or golden fixture: agents-deck is
its only writer, so `git diff` is enough coordination.

### D6. No free text leaves an adapter

Adapters keep identifiers, tool names, enum values, counts and times. They
never keep prompt text, model replies, tool arguments, command lines, file
contents, model-written task descriptions or account details. Transcript
lines are parsed one at a time and dropped after the fields above are taken
out. The only text a tile shows is the session title: the name the user
gave a Claude session, or else the folder name (cut to 24 characters,
section 5).

---

## 3. Architecture

```
          collector thread (1 poll / s)                            GTK main thread
 /proc ─► ProcessTable ─► PaneScanner ─► [PaneAgent …]
                                             │
             ┌───────────────────────────────┼──────────────────────────┐
             ▼                               ▼                          ▼
       ClaudeAdapter                   CodexAdapter                 AgyAdapter
  sessions/<pid>.json             CodexTuiRegistry              log/cli-*.log (pid)
  ClaudeSessionTracker            CodexThreadIndex (markers,    brain/<id>/…/transcript.jsonl
   └ LineTail on transcript         state_5.sqlite read-only)
                                  CodexLinkResolver
                                  CodexThreadTracker
                                   └ LineTail on rollout
             │                               │                          │
             └───────────► AgentObservation ─┴──────────────────────────┘
                                   │
                    Collector: SessionState × n ─► Snapshot (immutable)
                                   │                       │
                         SnapshotCodec (JSON)      GLib.idle_add ─► OverlayWindow
                                                                     ├ GridLayout, TileOrder
                                                                     ├ SpriteAnimator ─► DeckPainter ─► SpriteAtlas
                                                                     ├ TooltipContent ─► TooltipWindow
                                                                     └ SettingsWindow
                                                   click ─► WarpFocuser (warp:// link)
```

**Fault boundary.** `Collector.collectOnce` calls each adapter inside its
own `try`. An adapter that raises turns only its own sessions to "unknown".
`OnceLogger` logs each distinct failure once, not once per poll. If the
whole poll stops, the UI marks the deck stale after 3 silent polls
(`TimingConstants.STALE_SNAPSHOT_POLLS`).

### 3.1 Package layout

```
agents_deck/
  __main__.py          entry point: the GUI, or --dump-snapshot
  collector.py         Collector: one poll → one Snapshot
  collector_thread.py  CollectorThread: runs the poll once per interval
  constants/           named constants, one class per domain
  model/               AgentKind, Phase, WaitReason, LinkConfidence, ToolCategory,
                       ToolActivity, BackgroundKind, BackgroundTask,
                       AgentObservation, SessionState, Snapshot
  discovery/           ProcessInfo, ProcessTable, PaneAgent, PaneScanner, CodexCli
  adapters/            LineTail, TailBatch, JsonRecord, ToolClassifier, LabelSanitizer,
                       Claude*, Codex*, AgyAdapter
  diagnostics/         OnceLogger
  focus/               WarpFocuser
  settings/            Settings, SettingsStore, TileOrder, ShelfMode, ThemeChoice
  tablet/              SnapshotCodec
  ui/                  AgentsDeckApp, OverlayWindow, GridLayout, DeckPainter,
                       SpriteArt, SpritePalette, SpriteAtlas, SpriteAnimator,
                       TooltipContent, TooltipWindow, SettingsWindow, Tween, …
tests/                 unittest, synthetic data only
tools/                 render_readme_images.py (README images from demo sessions)
```

Code style follows the owner's global rules, adapted to Python: classes
`PascalCase`, methods `camelCase`, members `mValue`, locals `tValue`,
parameters without prefix, one class per file, no default parameter values,
named constants per domain, English comments that state a contract,
ownership, a constraint or a rationale.

## 4. Discovery: which panes run an agent

A **pane** here is one Warp terminal pane whose process tree contains an
agent. `PaneScanner` finds them once per poll.

1. `ProcessTable.refresh()` reads `/proc/<pid>/stat` for every process: pid,
   parent pid, `comm`, process group, controlling terminal, the terminal's
   foreground group, and start time. A pid together with its start time
   identifies one process. Before any process is used, `isRunning(pid,
   startTicks)` confirms that the pid was not reused.
2. Warp pane shells are the children of Warp's `terminal-server` process.
3. In each pane, the walk goes **downward** from the pane shell, starting
   with the shell itself (so `exec claude` is found). The pane's agent is the
   shallowest process whose `comm` is `claude`, `codex` or `agy` and which
   has a controlling terminal. A process in the terminal's foreground group
   wins over one that is suspended or sent to the background.
   - `comm` is used, not the executable name: Claude's executable is a
     versioned file (`…/versions/2.1.329`).
   - For `codex`, the argv decides whether it is the interactive TUI
     (`CodexCli.isTui`). Options are skipped by how many values they take, so
     `codex -C exec` is a TUI in a folder named `exec`, while `codex exec …`,
     `codex review …` and the other subcommands are not panes.
   - The walk does not descend into an agent. An agent inside an agent (for
     example `codex exec` run by a Claude Bash tool) is that pane's work,
     not another pane.
4. The pane id is `WARP_TERMINAL_SESSION_UUID`, read from the **pane
   shell's** environment, lowercased, and accepted only if it is 32 hex
   digits. The agent's own environment is not used: whatever launched the
   agent could have rewritten it, and the id ends up in a `warp://` link.
5. Because the walk only goes downward from pane shells, processes that
   merely inherited a pane id are never reached: the Codex app-server
   daemon, VS Code's Codex, helper processes.

**Not found by construction:** agents started outside Warp, agents inside
`tmux` or `screen` (their processes belong to the multiplexer's server, not
to the pane shell), and an agent that replaced the pane shell with a cleared
environment (`exec env -i claude`).

## 5. State model

```
SessionState                       one tile
  mPaneUuid     str                Warp pane id: order key and focus target
  mAgent        AgentKind          claude | codex | agy
  mPid, mStartTicks                identity of the agent process
  mTitle        str | None         user-given Claude name, else folder name (≤ 24 chars)
  mObservation  AgentObservation
  mPhaseSince   float              when the phase last changed (idle time, sleep pose)

AgentObservation
  mPhase            Phase           starting | idle | thinking | tool | waiting | error | unknown
  mWaitingFor       WaitReason|None permission | input
  mTool             ToolActivity|None   tool name + ToolCategory (prop shown)
  mBackground       tuple[BackgroundTask]
  mBackgroundKnown  bool            False = "not visible", never "none"
  mConfidence       LinkConfidence  exact | inferred | unknown
```

- `ToolCategory` picks the prop the character holds: `shell`, `edit`,
  `search`, `web`, `agent`, `other`.
- `BackgroundTask` is `(mId, mKind, mProcessName)`. `mKind` is `shell`,
  `agent`, `monitor`, `workflow`, `remote` or `process`. `mProcessName` is
  set only for `process` tasks: the kernel `comm` of a process Codex
  started, accepted only if it matches `[A-Za-z0-9._+-]{1,15}`
  (`LabelConstants.PROCESS_NAME_PATTERN`). It is shown in the local tooltip
  and never in the snapshot JSON.
- `mPhaseSince` is set by the collector when the phase changes, from the
  time the snapshot was taken.

## 6. Adapters

### 6.1 Reading growing files: `LineTail`

Every adapter reads files that agents append to. `LineTail` is the one
reader for all of them:

- It returns only newline-terminated lines. A line still being written comes
  back whole on a later poll.
- On first attach it starts at the beginning of the line that holds the
  point 8 MiB before the end (`TailConstants.INITIAL_WINDOW_BYTES`). Lines
  before that point that contain one of the owner's **prefix needles** (byte
  strings such as `"backgroundTaskId"`) come back once, with the first batch.
  That lets an adapter rebuild long-lived state, such as a background task
  launched an hour ago, without parsing the whole file.
- One call reads at most 16 MiB (`MAX_READ_BYTES_PER_POLL`). A single line
  longer than that is skipped through its newline, over as many polls as it
  takes, so one huge record cannot stall the file.
- Each call works from one open file descriptor. The cursor moves only after
  the whole read succeeded. A smaller file or a new inode means the file was
  replaced: the next batch is marked `mWasReset` and the owner discards what
  it derived from the old file.
- `JsonRecord.parse` turns a line into a dict, or `None` for anything that is
  not a JSON object.

### 6.2 Claude Code: exact [R1]

**Link.** `~/.claude/sessions/<pid>.json` belongs to the pane's process when
its `procStart` equals the process start time in `/proc/<pid>/stat`. This is
exact.

**Phase**, from the registry `status`, refined by the transcript
`~/.claude/projects/*/<sessionId>.jsonl`:

| registry `status` | transcript | phase |
|---|---|---|
| `waiting` | — | `waiting`; `waitingFor` names a permission reason or is missing → permission, otherwise → input |
| `busy` | a `tool_use` with no `tool_result` yet | `tool` (name → category) |
| `busy` | the turn has ended | `idle` (only delegated work is running, e.g. async agents) |
| `busy` | otherwise | `thinking` |
| `shell` | — | `idle`, with at least one background shell |
| `idle` | the newest assistant record of the turn is an API error | `error` |
| `idle` | otherwise | `idle` |
| registry missing, or `procStart` differs | — | `starting` |
| anything else | — | `unknown` |

**Background tasks**, from the transcript:

- opened by a tool result with `backgroundTaskId` (its first letter gives the
  kind: `b` shell, `a` agent, `t` teammate, `r` remote, `w` workflow, `m`/`s`
  monitor) or by an async agent launch (`status: "async_launched"`, always
  kind `agent`);
- closed by a `<task-notification>` with a terminal status, or by the result
  of a `TaskStop` tool call. Only a result of a tool named `TaskStop` closes
  a task; another tool's result that happens to carry `task_id` does not;
- if the registry says `shell` and no shell task is known, one unnamed shell
  task is added so the badge is not zero.

If the transcript cannot be read this poll, nothing derived from it is shown
(no tool, no background, `mBackgroundKnown = False`). Showing state from an
older poll or an older session would be a guess. A `/clear` starts a new
session id and a new transcript; `ClaudeSessionTracker` drops the old state
when that happens.

**Never touched:** the registry fields `tempo/state/detail/needs` and
`~/.claude/sessions/.fleetview-heartbeat`. Touching the heartbeat turns on
billed summaries.

### 6.3 Codex: inferred at best [R2, A1, A2]

**Why the link is a guess.** Codex 0.170+ runs its TUI as a thin client of
a shared `codex app-server` daemon. The TUI process holds no file, lock or
log row for its thread [A1]. The only TUI-side signal is the attach marker:
the empty file `~/.codex/tui-thread-reference-capabilities/<threadId>`,
whose mtime is written when a TUI process first learns of a thread: at start
(about 10 s after launch), on `codex resume` and on `/new` [A2]. In the
Codex source, the same marker is also written for threads a dynamic tool
starts without the TUI showing them, and never again for a thread that
process already wrote. So the newest marker credited to a TUI is a strong
hint, not proof. Every Codex link is `inferred` or `unknown`, and the
tooltip says "Thread matched by start time and folder; may be wrong".

**`CodexLinkResolver`** decides each marker change once, when it is first
seen, in time order, and keeps the decision:

1. The candidates are the TUIs alive at the marker's mtime
   (`CodexTuiRegistry` remembers exited TUIs for 10 minutes so they still
   count). Subagent threads are dropped first.
2. If exactly one candidate is inside its own start-up window (30 s after
   start, `CODEX_ATTACH_WINDOW_SECONDS`) and has not taken a marker yet, it
   takes this one. A fresh TUI writes its first marker within seconds.
3. Otherwise, if exactly one candidate's working folder equals the thread's
   folder (from `state_5.sqlite`, opened read-only), it takes it.
4. Otherwise, if there is exactly one candidate, it takes it.
5. Otherwise every candidate becomes `unknown` until its next marker.

Keeping each decision matters. An earlier version re-derived all links on
every poll. When a TUI exited and was forgotten, its old markers were
handed to a surviving TUI. The regression test
`testForgettingAnExitedTuiDoesNotHandItsMarkerToASurvivor` pins this.
Markers written before agents-deck started are trusted only inside a TUI's
start-up window or by folder, because TUIs that exited before then are
invisible.

**Phase**, from the thread's rollout
`~/.codex/sessions/YYYY/MM/DD/rollout-*-<threadId>.jsonl`, tailed with
needles for turn boundaries, calls and subagent events:

| rollout | phase |
|---|---|
| a turn is open and a `request_user_input` call has no output yet | `waiting` (input) |
| a turn is open and another call has no output yet | `tool` |
| a turn is open | `thinking` |
| the last turn ended in `turn_aborted` with an error, or `task_complete` with an error | `error` |
| otherwise | `idle` |
| the thread has no row and no rollout yet (no turn persisted) | `idle` |
| the thread has a row but its rollout cannot be read, or the format is not recognised | `unknown` |

`request_user_input` waits for the answer in every collaboration mode, not
only when Codex marks it blocking, so an open call is shown as waiting in
any mode. Codex approval waits are not persisted, so they are not shown.

**Background tasks:**

- subagents, from `sub_agent_activity` events and `SubAgentActivity` items
  (kind `agent`);
- processes whose environment has `CODEX_THREAD_ID == <threadId>` (children
  of the daemon or of the TUI), kind `process`, labelled by their checked
  `comm`. A process whose `CODEX_TOOL_CALL_ID` is a call still open is the
  running tool, not background work.

### 6.4 Antigravity CLI `agy`: exact link, coarse state [R3]

**Link.** Each `agy` process writes
`~/.gemini/antigravity-cli/log/cli-<start time>.log`, with its pid in every
log line header. The log is chosen by the pid and by a name time within 2 s
before to 30 s after the process start. The log also contains prompt text
and the account email. So it is read line by line, and only a line that
matches the whole regular expression `AgyConstants.CONVERSATION_LINE` (a log
header from this pid, then `Created conversation <uuid>` or `Streaming
conversation <uuid>`) yields anything: the conversation id. A prompt that
quotes such a message sits behind a different header and does not match.

**Phase**, from the newest step in
`brain/<conversation>/.system_generated/logs/transcript.jsonl`:

| newest step | phase |
|---|---|
| status `ERROR`, or type `ERROR_MESSAGE` | `error` |
| `PLANNER_RESPONSE` that calls a tool | `tool` |
| `PLANNER_RESPONSE` without a tool call | `idle` |
| anything else (the user spoke, a tool finished) | `thinking` |
| no conversation named yet | `idle` |
| log or transcript unreadable | `unknown` |

The transcript is append-only and each step is written once, with the
status it had then. A command that went to the background stays `RUNNING`
in that file forever. So Antigravity background work is reported as **not
visible** (`mBackgroundKnown = False`), never as "none". Tool-confirmation
waits are not observable either.

## 7. Focus

`WarpFocuser.focus(paneId)` opens `warp://session/<pane id>` with
`Gio.AppInfo.launch_default_for_uri`. That is the same path as `gio open`,
which was verified live to switch Warp's window, tab and pane [R4].

Before the launch, the overlay re-checks that the session's process is
still the same one (`isRunning(pid, startTicks)`). If it is gone, the tile
shakes and its tooltip says "Session ended".

The launch is asynchronous. A launch that fails (for example, no handler for
`warp://`) is only logged, as "Warp focus request failed". Warp itself only
logs a warning when it cannot find the pane, so a successful launch does not
prove the pane was focused. Warp
raises its own window with `_NET_ACTIVE_WINDOW`; mutter honours that except
across workspaces. A Wnck-based raise is not built until a raise failure is
reproduced.

## 8. Overlay window and interaction

- **Window:** a `Gtk.Window` toplevel with an RGBA visual, app-paintable,
  undecorated, keep-above, sticky (all workspaces), `accept_focus=False`,
  `focus_on_map=False`, skip taskbar and pager, type hint `UTILITY`.
- **Input shape:** while the shelf is shown, the whole plate takes input.
  While it is hidden, only the tile rectangles do, and everything else
  passes clicks to the window below.
- **Shelf:** a rounded translucent plate behind the tiles (alpha 0.94),
  dark or light by theme. Shown on hover (default) or always. On the first
  run it stays visible for 4 s.
- **Move:** press on the shelf outside a tile → `begin_move_drag`, the
  window manager's own move.
- **Resize:** the grip changes the integer sprite scale, 2× to 6×. Pixel art
  is drawn only at integer scales.
- **Reorder:** press a tile and move it more than 6 px. The tile follows the
  pointer and the others make room. Release on the shelf drops it; release
  outside the shelf, or `Esc`, cancels and the tile slides back. A press
  without movement is a click.
- **Grabs:** a press on a tile or the grip grabs the pointer, so motion and
  the release still arrive when the pointer leaves the window. Only a tile
  drag also grabs the keyboard, because only a drag can be cancelled with
  `Esc`; at any other time `Esc` belongs to the focused terminal. If the
  keyboard grab is refused, the pointer is grabbed alone. A broken grab (a
  window-manager shortcut, a screen lock) or an unmapped window cancels the
  press. After every press the overlay asks the pointer where it is, because
  crossing events were ignored while the press lasted.
- **Grid:** `columns × rows` from the settings, filled row by row in the
  saved order. More sessions than cells add rows; nothing is hidden. The
  gear and the grip sit in a fixed column on the right, so they stay
  reachable with zero sessions.
- **Hover:** after 400 ms a tooltip window (no focus) shows the agent, what
  it is doing, idle time, and the background summary. Once a tooltip has
  been shown, the next hover within 300 ms shows its tooltip at once. The
  hovered tile lifts over 120 ms.
- **Stale:** when snapshots stop arriving, tiles fade and the tooltip says
  "Status paused".

### Settings

`~/.config/agents-deck/settings.json`: columns and rows (1 to 8), scale (2
to 6), shelf mode, show names, theme (system, light, dark), tile order,
position, first-run flag.

- Saving writes a temporary file in the same folder (`mkstemp`, mode 0600),
  then `os.replace`s it. A failed save removes the temporary file.
- Each field is checked on load. A value that is the wrong type or out of
  range falls back to its default; a position outside the X11 coordinate
  range (−32768 to 32767) is dropped. A file that is not readable JSON
  gives all defaults, plus a note in the log and in the gear's tooltip.
- The position is saved only after the user has placed the deck (moved it
  or used the grip). Until then the default placement, bottom centre of the
  primary monitor, follows monitor changes.
- **Tile order** (`TileOrder`) is a list of pane ids. A pane that is gone
  keeps its place, because Warp keeps pane ids across its own restarts. The
  list is capped at 64: the absent panes seen least recently are forgotten
  first, and a live pane is never forgotten.

## 9. Visual design

Design read: a desktop status widget for one developer. Dock-like, pixel
art, cute but restrained. Motion carries state; nothing moves for
decoration.

- **Characters** (original, no vendor mascots): *Ember* (Claude, an orange
  blob with a flame tuft), *Cubit* (Codex, a blue boxy robot with a visor),
  *Floaty* (Antigravity, a mint-green orb that hovers over its shadow).
  24×24 sprites drawn from palette-indexed rows in `SpriteArt`, one shared
  dark outline, three-tone shading.
- **Rim:** an always-on cream outline (`#fbf7efe6`, all 8 neighbours) around
  each character. What lies behind the deck does not follow the system
  theme, so a theme-dependent rim was illegible on some backdrops.
- **State → pose, prop and motion** (`SpriteAnimator`):

| phase | pose | prop / overlay | motion |
|---|---|---|---|
| idle | idle | — | blink every 5–8 s |
| idle ≥ 10 min | sleep | `zzz` | 1 frame/s |
| thinking | think | thought bubble, dots 1-2-3 | body 500 ms, dots 333 ms |
| tool | work | prop by category: terminal, pencil, magnifier, globe, mini-bot, wrench | 250 ms |
| waiting | raise | `!` bubble (permission) or `?` bubble (input) | 400 ms |
| error | error | smoke puff, red eyes | 300 ms, for the first 3 s only |
| unknown | idle | — | still, opacity 0.55 |
| starting | idle | — | still |

- **Background badge:** a cream pill at the top left with the number of
  background tasks, `9+` above nine. Hidden when zero, and also hidden when
  background work is not visible (an Antigravity session never shows "0").
- **Reduced motion:** when GTK animations are off, each state shows its key
  frame; poses still differ by state.

## 10. Tablet skeleton

`SnapshotCodec.encode(snapshot, order)` produces the JSON a tablet would
receive, in tile order:

```json
{
  "generatedAt": 1795180000.0,
  "warpRunning": true,
  "sessions": [
    {
      "pane": "<32 hex digits>",
      "agent": "claude",
      "phase": "tool",
      "phaseSince": 1795179990.0,
      "waitingFor": null,
      "toolCategory": "shell",
      "background": {"known": true, "count": 2, "kinds": ["agent", "shell"]},
      "confidence": "exact"
    }
  ]
}
```

It is narrower than the local overlay. It carries no title, no tool name
(MCP tool names contain server names), no process name and no path. When
background work is not visible, `background` is
`{"known": false, "count": null, "kinds": null}`, never a count of 0.

Not built: the transport. The likely shape is HTTP + WebSocket bound to
127.0.0.1 with a random token and a Host/Origin check, and on Android an
`adb reverse tcp:P tcp:P` that is re-applied on reconnect.

## 11. Not built in v1, on purpose

Each of these needs the user to opt in, because it edits an agent's
configuration or connects to an agent:

- Codex `PermissionRequest` hook (would show approval waits);
- Antigravity status-line command (would show confirmation waits and
  background tasks);
- a Codex app-server client (`thread/read`) for an exact pane ↔ thread link;
- Claude Code hooks.

Also not built: the tablet listener, a Wnck raise fallback, Wayland,
several machines, and anything that reads or summarises conversation
content.

## 12. When something looks wrong

| Symptom | Where to look |
|---|---|
| An agent has no tile | Section 4. Run `python3 -m agents_deck --dump-snapshot`. Check that the agent's process sits under a Warp pane shell (`ps -o pid,ppid,comm`) and that the shell has `WARP_TERMINAL_SESSION_UUID`. |
| A Codex tile is faded | Section 6.3. Two TUIs were candidates for one marker. Typing `/new` in that pane while no other Codex pane is starting writes a fresh marker. |
| A Codex tile shows another pane's thread | Section 6.3, step 3 or 4: a folder match or a single candidate can be wrong after an in-app `/resume`. A resolver test reproducing the case is the place to start. |
| A tile is stuck in `tool` or `thinking` | The adapter's state class (`ClaudeTranscriptState`, `CodexRolloutState`) and the record that should have closed the call. Agents change undocumented formats on upgrade. |
| Every tile is faded, "Status paused" | The collector thread stopped. Its first failure is in the log of the terminal agents-deck was started from. |
| "no boot time in /proc/stat" in the log | `ProcessTable` could not read `btime`. Codex and Antigravity tiles stay unknown, because their links need process start times. |

The formats read here are not official APIs. When one changes, the intended
failure is "unknown", never a wrong state. Each adapter has unit tests that
pin the shapes it parses, built from synthetic records.

## 13. Verification

- **Unit tests:** `python3 -m unittest discover tests`. Synthetic data only:
  fake process tables, temporary files, hand-written records.
- **Type check:** `pyright`, run from the repository root (a `.venv` with
  type stubs is gitignored).
- **Live run:** `--dump-snapshot` against the real sessions on the machine,
  and the overlay with `XDG_CONFIG_HOME` pointed at a scratch folder so the
  real settings are not written.
- **Not automated:** a physical mouse (synthetic GDK events were used), focus
  across workspaces and of a minimised Warp, multi-monitor moves.
