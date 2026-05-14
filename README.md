# agi3-viewer

A browser-based replay viewer + replay-log writer for [ARC-AGI-3](https://arcprize.org/). View human recordings, view agent runs you produce locally, scrub through frames, see reasoning logs and markers like the [official ARC replay viewer](https://arcprize.org/replay/).

## What's in here

| Path | Purpose |
|---|---|
| `data_maker/` | Single-page HTML viewer. Open in a local browser, drag in any `.recording.jsonl` (human or agent), scrub frames, filter by marker, read reasoning subtitles. |
| `schemas/replay_schema.md` | Wire-format spec. Human recordings + agent-emitted replays share this format. The viewer reads either. |
| `agent/reasoning_logger.py` | Python helper an agent imports to write replays during play. Emits a strict superset of the human recording schema (adds `marker`, `reasoning`, `scout_context` fields). |

## Quick start — view a recording

```powershell
# from the repo root
python -m http.server 8080
# open http://localhost:8080/data_maker/
```

The viewer loads `data_maker/manifest.json` for known game/recording listings. To view your own files:

- **Drag-and-drop** any `.recording.jsonl` directly onto the canvas area, OR
- Click the **📁 Load file** button in the top bar.

This works for human replays from the competition dataset and for agent replays written by `reasoning_logger.py`.

## Quick start — write an agent replay

In a Kaggle notebook or local agent loop:

```python
from agi3_v3.agent.reasoning_logger import ReasoningLogger

rl = ReasoningLogger(game_id='sb26-abc', out_dir='/kaggle/working')

rl.log_scout({
    'action_set': 'keyboard', 'player_sprite': 'blue 3x3',
    'goal_hypothesis': 'yellow square', 'view_type': 'god',
    'priority_actions': [3, 4, 1, 2],
})

rl.log_decision(
    action_id=3, decided_by='Coach', play_name='direct_attack',
    rationale='goal is up; wall blocks right; need UP first',
    expected_frame=predicted_next_frame,
)
env_response = env.step(3)
rl.log_result(env_response)
# ... loop ...

rl.close()
```

Outputs `/kaggle/working/replay_<game_id>.jsonl`. Drag that file into the viewer to see what your agent did.

## Viewer features

- ARC-AGI-3 official 16-color palette with subtle graph-paper grid lines
- Playback controls (play/pause, speed 2–20 fps, scrubber, step ±1/±10, Home/End)
- Event timeline (right panel) — every frame as a clickable entry, color-coded marker badges
- **Filter by category**: all / actions / reactions / decisions / results / no-ops / surprises
- **Reasoning log** (subtitle-style) — current frame's `rationale` in large text with previous lines faded above
- Session summary panel: game_id, recording, level reached, totals (decisions, no-ops, level-changes, wins, mismatches)
- Keyboard shortcuts: `←` `→` step · `Shift+←/→` ±10 · `Home`/`End` start/end · `[` `]` filter prev/next · `Space` play/pause
- Out-of-palette frame values render as magenta as a visible warning
- All DOM access is defensive — missing elements log a console error rather than crashing the page

## Markers (auto-derived for human recordings, emitted by the logger for agent recordings)

| Marker | Meaning |
|---|---|
| `start` | First frame of recording |
| `decision` | Action was taken AND frame changed |
| `noop` | Action was taken AND frame did not change |
| `level_change` | `levels_completed` incremented |
| `win` / `loss` | Game state is WIN or GAME_OVER |
| `reset` | Action 0 (start/reset) after the first frame |
| `mismatch` | Agent's `expected_frame_hash` ≠ actual (agent recordings only) |
| `stuck` | Sustained 30-frame no-op streak |

Filter categories combine these — `decisions only` shows just `decision` markers; `results` shows level_change + win + loss; etc.

## Regenerating manifest.json

The provided `manifest.json` was built against a specific local recording layout. To regenerate against your own copy of the public recordings:

```python
import os, json
base = '/path/to/public_games-dataset'   # change to your path
m = {}
for g in sorted(os.listdir(base)):
    gpath = os.path.join(base, g)
    if os.path.isdir(gpath):
        m[g] = sorted([f for f in os.listdir(gpath) if f.endswith('.recording.jsonl')])
json.dump(m, open('data_maker/manifest.json', 'w'), indent=2)
```

Then edit the `BASE` constant near the top of `data_maker/index.html` to point at your recordings directory (relative to wherever you serve from).

## Recording data

The public human recordings live in the ARC-AGI-3 competition dataset on Kaggle: <https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3>. They are NOT included in this repo.

## License

MIT.
