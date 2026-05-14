"""ReasoningLogger — emits replay JSONL compatible with human recordings.

Output is a strict superset of the human recording schema (see
agi3_v3/schemas/replay_schema.md). The data maker can render both.

Designed to live next to the agent's env loop:

    rl = ReasoningLogger(game_id, out_dir='/kaggle/working')
    rl.log_scout(scout_dict)                              # at level-start
    rl.log_decision(action_id, decided_by='BFS', ...)     # before env.step()
    env_response = env.step(action_id)
    rl.log_result(env_response)                           # after env.step()
    ...
    rl.close()                                            # at episode end
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone

# Without this, our log calls are silently swallowed inside Kaggle. See
# feedback_qwen_injection_imports memory and v10 post-mortem.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s | %(message)s',
    force=True,
)
logger = logging.getLogger('reasoning_logger')


def _hash_frame(frame):
    """Cheap stable hash of a frame (handles both [1,64,64] and [64,64])."""
    if frame is None:
        return None
    if isinstance(frame[0], list) and frame and isinstance(frame[0][0], list):
        flat = bytes(v for row in frame[0] for v in row)
    else:
        flat = bytes(v for row in frame for v in row)
    return hashlib.sha256(flat).hexdigest()[:8]


def _frames_equal(a, b):
    if a is None or b is None:
        return False
    return _hash_frame(a) == _hash_frame(b)


class ReasoningLogger:
    """Wraps the env loop and emits replay JSONL.

    Lifecycle:
        - Construct once per game (game_id is the unique key).
        - Call log_scout(scout_dict) at each level start to attach context to
          the next line.
        - Call log_decision(...) BEFORE env.step() with the action + reasoning.
        - Call log_result(env_response) AFTER env.step() with the full env
          response dict (must have keys matching the human-recording schema:
          frame, state, action_input, available_actions, levels_completed,
          win_levels — plus any others present, all are passed through).
        - close() flushes and closes the file.

    The marker for each line is computed from (state, levels_completed,
    frame-equality with prev, and decision metadata).
    """

    NOOP_THRESHOLD = 30  # consecutive identical frames -> 'stuck'

    def __init__(self, game_id: str, out_dir: str = '/kaggle/working'):
        self.game_id = game_id
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        safe_game = game_id.replace('/', '_').replace(' ', '_')
        self.path = out / f'replay_{safe_game}.jsonl'
        self.fh = open(self.path, 'a', buffering=1)  # line-buffered
        self.prev_frame = None
        self.prev_levels = 0
        self.pending_decision = None
        self.scout_context = None
        self.noop_streak = 0
        self.lines_written = 0
        logger.info(f'started game_id={game_id} path={self.path}')

    def log_scout(self, scout: dict):
        """Attach scout report to the next result line. Wipes after one use."""
        self.scout_context = dict(scout) if scout else None

    def log_decision(self, action_id: int, decided_by: str,
                     play_name: str = None, rationale: str = '',
                     expected_frame=None):
        """Stash decision metadata to attach to the next log_result() call."""
        self.pending_decision = {
            'action_id': int(action_id),
            'decided_by': decided_by,
            'play_name': play_name,
            'rationale': (rationale or '')[:500],
            'expected_frame_hash': _hash_frame(expected_frame),
        }

    def log_result(self, env_response: dict):
        """Write one line covering the env response after env.step()."""
        frame = env_response.get('frame')
        state = env_response.get('state', 'NOT_FINISHED')
        levels = env_response.get('levels_completed', 0)
        action_obj = env_response.get('action_input', {}) or {}
        aid = action_obj.get('id', 0)

        # Compute marker (most-specific-wins ordering)
        marker = 'result'
        is_noop = _frames_equal(frame, self.prev_frame)
        if levels > self.prev_levels:
            marker = 'level_change'
            self.noop_streak = 0
        elif state == 'WIN':
            marker = 'win'
        elif state == 'GAME_OVER':
            marker = 'loss'
        elif aid == 0:
            marker = 'reset'
            self.noop_streak = 0
        elif is_noop:
            self.noop_streak += 1
            marker = 'stuck' if self.noop_streak >= self.NOOP_THRESHOLD else 'noop'
        else:
            marker = 'decision'
            self.noop_streak = 0

        # Mismatch detection on a real decision
        reasoning = None
        if self.pending_decision is not None:
            reasoning = dict(self.pending_decision)
            reasoning['actual_frame_hash'] = _hash_frame(frame)
            exp = reasoning.get('expected_frame_hash')
            if exp and exp != reasoning['actual_frame_hash'] and marker == 'decision':
                marker = 'mismatch'

        # Build data block — pass through env_response, add our fields
        data = dict(env_response)
        data['marker'] = marker
        if reasoning is not None:
            data['reasoning'] = reasoning
        if self.scout_context is not None:
            data['scout_context'] = self.scout_context
            self.scout_context = None

        line = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data,
        }
        self.fh.write(json.dumps(line, default=str) + '\n')
        self.lines_written += 1

        # Roll state
        self.prev_frame = frame
        self.prev_levels = levels
        self.pending_decision = None

        # Surface interesting markers to stdout for live debugging
        if marker in ('level_change', 'win', 'loss', 'stuck', 'mismatch'):
            logger.info(
                f'[{self.game_id}] marker={marker} aid={aid} '
                f'lvl={levels}/{env_response.get("win_levels", "?")} state={state}'
            )

    def close(self):
        if self.fh and not self.fh.closed:
            self.fh.close()
            logger.info(f'closed game_id={self.game_id} lines={self.lines_written} path={self.path}')

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


if __name__ == '__main__':
    # Self-test: emit a tiny synthetic replay to /tmp.
    import tempfile
    import random
    tmp = tempfile.mkdtemp()
    rl = ReasoningLogger('selftest-abc', out_dir=tmp)
    rl.log_scout({
        'action_set': 'keyboard', 'player_sprite': 'blue 3x3',
        'goal_hypothesis': 'yellow square', 'view_type': 'god',
        'priority_actions': [3, 4, 1, 2]
    })
    frame_a = [[[random.randint(0, 15) for _ in range(64)] for _ in range(64)]]
    frame_b = [[[random.randint(0, 15) for _ in range(64)] for _ in range(64)]]
    rl.log_decision(action_id=3, decided_by='Coach', play_name='direct_attack',
                    rationale='goal is up', expected_frame=frame_b)
    rl.log_result({
        'game_id': 'selftest-abc', 'frame': frame_a, 'state': 'NOT_FINISHED',
        'action_input': {'id': 3, 'data': {}, 'reasoning': None},
        'guid': 's1', 'full_reset': False, 'available_actions': [1, 2, 3, 4],
        'levels_completed': 0, 'win_levels': 3,
    })
    rl.log_result({
        'game_id': 'selftest-abc', 'frame': frame_b, 'state': 'WIN',
        'action_input': {'id': 7, 'data': {}, 'reasoning': None},
        'guid': 's1', 'full_reset': False, 'available_actions': [],
        'levels_completed': 1, 'win_levels': 3,
    })
    rl.close()
    print(f'wrote: {rl.path}')
    with open(rl.path) as f:
        for line in f:
            d = json.loads(line)['data']
            print(f'  marker={d["marker"]} aid={d["action_input"]["id"]} lvl={d["levels_completed"]}')
