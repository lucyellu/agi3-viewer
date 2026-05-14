"""Scan all known recording directories and emit manifest.json + status_index.json.

Run from the repo root:
    cd C:/Users/lucyl/Desktop/agi-3/agi3_v3/data_maker
    python build_index.py

Outputs:
    manifest.json       {"sources": {<source_id>: {"base_url": str, "games": {game: [filename, ...]}}}, "generated_at": ts}
    status_index.json   {<source_id>: {<game>: {<filename>: {status, levels_completed, win_levels, total_actions, final_state}}}}
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent              # .../agi3_v3/data_maker
DESKTOP_AGI3 = REPO_ROOT.parent.parent                   # .../agi-3

# Source registry: id -> (base_url relative to data_maker/, filesystem path)
# base_url is what the browser fetches against; filesystem path is what this script reads.
SOURCES: list[dict[str, Any]] = [
    {
        "id": "human",
        "label": "Human (public demo)",
        "base_url": "../../agi3_v1/data/arc_agi_3_public_demo_human_testing/public_games-dataset",
        "fs_path": DESKTOP_AGI3 / "agi3_v1" / "data" / "arc_agi_3_public_demo_human_testing" / "public_games-dataset",
        "layout": "game_dir",  # files are at <root>/<game>/<file>
    },
    {
        "id": "agent-clickgames-v6",
        "label": "Agent: clickgames v6",
        "base_url": "../../agi3_v1/clickgames/results/v6-logs/recordings",
        "fs_path": DESKTOP_AGI3 / "agi3_v1" / "clickgames" / "results" / "v6-logs" / "recordings",
        "layout": "flat_prefixed",  # files are at <root>/<game>.myagent.<uuid>.recording.jsonl
    },
    {
        "id": "agent-clickgames-v7",
        "label": "Agent: clickgames v7",
        "base_url": "../../agi3_v1/clickgames/results/v7-logs/recordings",
        "fs_path": DESKTOP_AGI3 / "agi3_v1" / "clickgames" / "results" / "v7-logs" / "recordings",
        "layout": "flat_prefixed",
    },
    {
        "id": "agent-clickgames-v8",
        "label": "Agent: clickgames v8",
        "base_url": "../../agi3_v1/clickgames/results/v8-logs/recordings",
        "fs_path": DESKTOP_AGI3 / "agi3_v1" / "clickgames" / "results" / "v8-logs" / "recordings",
        "layout": "flat_prefixed",
    },
]

# Add sim_solver versions automatically
for sv in ["v9", "v11", "v14", "v15", "v16", "v17"]:
    p = DESKTOP_AGI3 / "agi3_v1" / "sim_solver" / "results" / sv / "recordings"
    SOURCES.append({
        "id": f"agent-sim-{sv}",
        "label": f"Agent: sim_solver {sv}",
        "base_url": f"../../agi3_v1/sim_solver/results/{sv}/recordings",
        "fs_path": p,
        "layout": "flat_prefixed",
    })


def parse_recording_status(path: Path) -> dict[str, Any] | None:
    """Read first + last line of a recording to extract status fields.

    First line gives us win_levels (total levels in this game).
    Last line of human/agent recordings is usually a summary row with `cards`.
    Falls back to scanning the last data row if no summary present.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return None
    if not lines:
        return None

    def parse(line: str) -> dict[str, Any] | None:
        line = line.strip()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    first = parse(lines[0]) or {}
    last = parse(lines[-1]) or {}

    first_data = first.get("data") or first
    win_levels = first_data.get("win_levels")
    game_id = first_data.get("game_id")

    last_data = last.get("data") or last
    levels_completed = last_data.get("levels_completed")
    final_state = last_data.get("state")
    total_actions = last_data.get("total_actions")

    # Summary-row case: `cards` dict present
    cards = last_data.get("cards") or {}
    if cards and game_id and game_id in cards:
        card = cards[game_id]
        states = card.get("states") or []
        if states:
            final_state = states[-1]
        lvls = card.get("levels_completed") or []
        if lvls:
            levels_completed = max(lvls)
        if total_actions is None:
            ta = card.get("total_actions")
            if ta is not None:
                total_actions = ta

    # Final fallback: rescan if final_state is still None
    if final_state is None:
        for raw in reversed(lines):
            d = parse(raw)
            if not d:
                continue
            dd = d.get("data") or d
            if dd.get("state"):
                final_state = dd.get("state")
                if levels_completed is None:
                    levels_completed = dd.get("levels_completed")
                break

    won = bool(final_state == "WIN")
    fully_finished = (
        win_levels is not None
        and levels_completed is not None
        and levels_completed >= win_levels
    )
    if won and fully_finished:
        status = "won"
    elif won:
        status = "won_partial"  # state=WIN but didn't reach all levels (rare/edge)
    elif final_state == "GAME_OVER":
        status = "lost"
    elif levels_completed and levels_completed > 0:
        status = "partial"     # made progress, didn't finish
    else:
        status = "no_progress"

    return {
        "status": status,
        "levels_completed": int(levels_completed or 0),
        "win_levels": int(win_levels or 0),
        "total_actions": int(total_actions) if isinstance(total_actions, int | float) else None,
        "final_state": final_state,
    }


def game_from_filename(fname: str, layout: str) -> str | None:
    if layout == "flat_prefixed":
        # <game>.myagent.<uuid>.recording.jsonl OR <game>.<uuid>.recording.jsonl
        parts = fname.split(".")
        if len(parts) >= 2:
            return parts[0]
    return None


def scan_source(src: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, dict[str, Any]]]:
    """Return (games_to_files, statuses_per_file_per_game)."""
    games: dict[str, list[str]] = {}
    statuses: dict[str, dict[str, Any]] = {}
    fs_path: Path = src["fs_path"]
    if not fs_path.exists():
        print(f"  skip {src['id']}: path missing {fs_path}")
        return games, statuses

    if src["layout"] == "game_dir":
        for game_dir in sorted(fs_path.iterdir()):
            if not game_dir.is_dir():
                continue
            game = game_dir.name
            files = sorted(p.name for p in game_dir.glob("*.recording.jsonl"))
            if not files:
                continue
            games[game] = files
            statuses[game] = {}
            for f in files:
                info = parse_recording_status(game_dir / f)
                if info:
                    statuses[game][f] = info
    elif src["layout"] == "flat_prefixed":
        for path in sorted(fs_path.glob("*.recording.jsonl")):
            game = game_from_filename(path.name, "flat_prefixed")
            if not game:
                continue
            games.setdefault(game, []).append(path.name)
            statuses.setdefault(game, {})
            info = parse_recording_status(path)
            if info:
                statuses[game][path.name] = info

    return games, statuses


def main() -> None:
    manifest: dict[str, Any] = {
        "generated_at": int(time.time()),
        "sources": {},
    }
    status_index: dict[str, Any] = {}

    for src in SOURCES:
        print(f"scanning {src['id']} <- {src['fs_path']}")
        games, statuses = scan_source(src)
        if not games:
            continue
        manifest["sources"][src["id"]] = {
            "label": src["label"],
            "base_url": src["base_url"],
            "layout": src["layout"],
            "games": games,
        }
        status_index[src["id"]] = statuses
        total = sum(len(v) for v in games.values())
        print(f"  {src['id']}: {total} recordings across {len(games)} games")

    (REPO_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (REPO_ROOT / "status_index.json").write_text(
        json.dumps(status_index, indent=2), encoding="utf-8"
    )
    total_recs = sum(
        len(files)
        for src in manifest["sources"].values()
        for files in src["games"].values()
    )
    print(f"\nwrote manifest.json + status_index.json ({total_recs} recordings total)")


if __name__ == "__main__":
    main()
