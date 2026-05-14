# Data Maker

Single-page browser app to view ARC-AGI-3 human replay recordings, label them, and produce the `arc_play_by_play.jsonl` consumed by Path B notebooks.

## Run

From the repo root (`C:\Users\lucyl\Desktop\agi-3`):

```powershell
python -m http.server 8080
```

Then open: <http://localhost:8080/agi3_v3/data_maker/>

The server must be started from `agi-3/` (not from `data_maker/`) so the relative path `../../agi3_v1/data/...` resolves to the recordings.

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
