# Replay JSONL Schema

Single schema shared by **human replay recordings** (provided) and **agent-emitted replays** (we produce them via `ReasoningLogger`). Agent output is a strict superset — extra optional fields inside `data`. The same data maker can render both.

## Top-level line shape

Each line of a `.recording.jsonl` is one JSON object:

```json
{
  "timestamp": "2025-11-10T17:36:18.020120+00:00",
  "data": { ... }
}
```

## `data` — fields present in both human and agent recordings

| Field | Type | Notes |
|---|---|---|
| `game_id` | string | e.g. `"sb26-0c556536"` |
| `frame` | int[1][64][64] | Outer dim is layer (always length 1). Cell values are integers **0–15** — see palette below. |
| `state` | string | `"NOT_FINISHED"`, `"WIN"`, `"GAME_OVER"` |
| `action_input` | object | `{id: int, data: object, reasoning: null}`. `id == 0` = reset/start. `id == 1..6` = ACTION1..6. `id == 7` = SPACEBAR (configure-commit games). Click games stash `{x, y}` in `data`. |
| `guid` | string | Recording UUID |
| `full_reset` | bool | Whether this step was a full game reset |
| `available_actions` | int[] | Action IDs legal at this frame |
| `levels_completed` | int | 0-indexed; increments on level-end |
| `win_levels` | int | Total levels in this game (target) |

## `data` — fields agent recordings add (all optional)

| Field | Type | Notes |
|---|---|---|
| `marker` | string | One of `start`, `decision`, `result`, `noop`, `level_change`, `win`, `loss`, `mismatch`, `stuck`. See derivation rules below. |
| `reasoning` | object | What the agent was thinking at this step. |
| `reasoning.decided_by` | string | `BFS`, `Coach`, `fallback`, `human` |
| `reasoning.play_name` | string | e.g. `direct_attack`, `sweep`, `pickup_first` (see playbook) |
| `reasoning.rationale` | string | Short text — why this action |
| `reasoning.expected_frame_hash` | string | First 8 hex of sha256(frame) — what the agent expected to see next |
| `reasoning.actual_frame_hash` | string | First 8 hex of sha256(actual next frame) — fills in after env.step |
| `scout_context` | object | Attached only on the first frame of a level. Mirrors the scouting report from `path_b_coach_swarm.md`. |
| `scout_context.action_set` | string | `keyboard \| click \| both` |
| `scout_context.player_sprite` | string | id + position |
| `scout_context.goal_hypothesis` | string | text |
| `scout_context.dangers` | string[] | |
| `scout_context.view_type` | string | `god \| agent \| mixed` |
| `scout_context.priority_actions` | int[] | Ranked action IDs |

## Marker derivation rules

For human recordings the data maker computes markers on load using these rules (in order):

| Marker | Rule |
|---|---|
| `start` | `i == 0` |
| `level_change` | `data.levels_completed > prev.levels_completed` |
| `win` | `data.state == "WIN"` |
| `loss` | `data.state == "GAME_OVER"` |
| `reset` | `data.action_input.id == 0 && i > 0` |
| `noop` | `data.action_input.id != 0` AND `frame == prev_frame` |
| `decision` | `data.action_input.id != 0` AND `frame != prev_frame` |
| `result` | fallback (rarely used for derivation; agents emit explicitly) |

Agent code emits these additional markers it has more info to detect:

| Marker | Rule |
|---|---|
| `mismatch` | `reasoning.expected_frame_hash != reasoning.actual_frame_hash` after a non-trivial decision |
| `stuck` | `noop` streak ≥ 30 consecutive frames |

## 16-color palette (canonical, from ARC-AGI-3 framework)

| Idx | Name | Hex |
|---:|---|---|
| 0 | White | `#FFFFFF` |
| 1 | Off-white | `#CCCCCC` |
| 2 | Neutral light | `#999999` |
| 3 | Neutral | `#666666` |
| 4 | Off-black | `#333333` |
| 5 | Black | `#000000` |
| 6 | Magenta | `#E53AA3` |
| 7 | Magenta light | `#FF7BCC` |
| 8 | Red | `#F93C31` |
| 9 | Blue | `#1E93FF` |
| 10 | Blue light | `#88D8F1` |
| 11 | Yellow | `#FFDC00` |
| 12 | Orange | `#FF851B` |
| 13 | Maroon | `#921231` |
| 14 | Green | `#4FCC30` |
| 15 | Purple | `#A356D6` |

Source of truth: `ARC-AGI-3-Agents/agents/templates/multimodal.py`.

## File-naming convention

- Human replays: `<game>/<guid>.recording.jsonl` (provided by competition)
- Agent replays: `replay_<game_id>.jsonl` (written by `ReasoningLogger` to `/kaggle/working`)
- Bundle at rerun end: `replays.tar.gz` containing all `replay_*.jsonl` from `/kaggle/working`

## Example minimal agent line

```json
{
  "timestamp": "2026-05-13T20:14:33.001234+00:00",
  "data": {
    "game_id": "sb26-abc123",
    "frame": [[[4, 4, ...]]],
    "state": "NOT_FINISHED",
    "action_input": {"id": 1, "data": {}, "reasoning": null},
    "guid": "agent-session-1",
    "full_reset": false,
    "available_actions": [1, 2, 3, 7],
    "levels_completed": 0,
    "win_levels": 8,
    "marker": "decision",
    "reasoning": {
      "decided_by": "Coach",
      "play_name": "configure_commit",
      "rationale": "Try blue in slot 1 to match top-left target",
      "expected_frame_hash": "8a7c2e1f",
      "actual_frame_hash": "8a7c2e1f"
    }
  }
}
```
