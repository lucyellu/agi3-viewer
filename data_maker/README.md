# Data Maker / agi3-viewer

Single-page browser app to view ARC-AGI-3 replay recordings — human plays from the public-25 dataset *and* agent recordings from prior solver runs (`clickgames`, `sim_solver`). Filter by source (human / agent version), by win/loss status, and by per-frame marker.

## Build the index

The viewer reads `manifest.json` and `status_index.json`. Regenerate them whenever recordings are added or moved:

```powershell
cd C:/Users/lucyl/Desktop/agi-3/agi3_v3/data_maker
python build_index.py
```

This scans:
- `agi3_v1/data/arc_agi_3_public_demo_human_testing/public_games-dataset/` — 340 human recordings
- `agi3_v1/clickgames/results/{v6,v7,v8}-logs/recordings/` — agent recordings
- `agi3_v1/sim_solver/results/{v9,v11,v14,v15,v16,v17}/recordings/` — agent recordings (v17 = highest local score)

…and extracts win/levels-completed/total-actions per recording into `status_index.json`. ~505 recordings total at last scan.

## Run

From the repo root (`C:\Users\lucyl\Desktop\agi-3`):

```powershell
python -m http.server 8080
```

The server must be started from `agi-3/` so the relative paths (`../../agi3_v1/...`) resolve.

## Three viewers

All three read the same manifest/status_index and load the same recordings — they differ only in UI:

| File | Public URL | Purpose |
|------|------------|---------|
| `index.html` | <https://agi3-viewer.netlify.app/> | **Annotation tool** — view_type / signature / commentary labelling, JSONL export. Use this when curating few-shot examples. |
| `index_controls.html` | <https://agi3-viewer.netlify.app/index_controls.html> | **Controls viewer** — D-pad + click-cursor showing which input produced each frame; per-level breakdown with destiny labels (`level_completed` / `level_failed` etc.); recording-status topbar badge. |
| `index_workspace.html` | <https://agi3-viewer.netlify.app/index_workspace.html> | **Workspace viewer** — same panels as Controls, but as a 3-lane docked layout with drag-to-resize splitters. Named workspace layouts persist to localStorage; built-ins: Compact, Wide, Equal. Autofit button equalizes everything. |

Local: open at `http://localhost:8080/agi3_v3/data_maker/<filename>` (or use the `launch-data-maker.bat` desktop shortcut, which currently opens the Workspace viewer with a cache-bust query string).

**Action-data caveat:** Agent recordings (clickgames v6–v8, sim_solver v9–v17) have `action_input.id = 0` on every frame because the framework's recorder doesn't capture the agent's chosen action. Human recordings work fully; agent replays show frame transitions but the Controls buttons can't light up until the notebook-side fix lands.

## Filters

The topbar exposes three filters:

1. **source** — which recording set to browse (Human, Agent: clickgames v6/v7/v8, Agent: sim_solver v9/v11/v14/v15/v16/v17).
2. **status** — `won` (beat all levels) · `won or partial` · `partial only` · `lost` (GAME_OVER) · `no progress`.
3. **recording** — actual file selector, prefixed with a status badge (`[WON]`, `[PART]`, `[LOST]`, `[----]`) and levels-reached (e.g. `5/8`).

## What you do here

1. Pick a game (top-left dropdown). 25 games, 340 total recordings.
2. Pick a recording. Step through frames with ←/→ (Shift for +10), or jump to level-change frames with `L`.
3. Set **view_type** and **signature** per game — these stick across recordings of the same game.
4. On any interesting frame, write **commentary**, pick a **label** (`level_start`, `level_end_win`, etc.), and press `S` to save the row.
5. When you've curated ~30 examples across the games, click **Download JSONL** to get `arc_play_by_play_<ts>.jsonl`. That file is what Path B notebook #2 retrieves few-shot examples from.

State persists in `localStorage` between sessions, so you can close the tab and come back.

## What good annotations look like

- One `level_start` and one `level_end_win` per winning level you want to teach from.
- Commentary in present tense, mechanism-focused: "player is one cell from yellow goal; wall blocks right; need UP".
- View_type labeled once per game (god / agent / mixed).
- Signature is your call: `keyboard_short_uniform`, `click_escalating`, `pure_keyboard_spatial`, etc. Match the game-type taxonomy in `path_b_coach_swarm.md`.

## What to skip

- Frames where nothing changed (consecutive identical frames).
- Long exploration runs where the human was clearly fumbling.
- Anything that requires more than one sentence of commentary to describe — those are too complex to be useful exemplars.
