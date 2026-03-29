"""
projection.py — Per-channel projection state manager with disk persistence.

State schema per channel:
  {
    "type": "text" | "image" | "video" | "announcement" | "timer" | "blank",
    "data": { ... },
    "theme_id": "default"
  }

State is persisted to data/projection_state.json on every set_state() call
so that a server restart + state:restore can replay the last known state.
"""

import json
import os

_BLANK_STATE      = {"type": "blank", "data": {}, "theme_id": "default"}
_STATE_FILE       = "data/projection_state.json"


class ProjectionStateManager:
    def __init__(self):
        self._state: dict[str, dict] = self._load()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_state(self, channel: str) -> dict:
        return self._state.get(channel, dict(_BLANK_STATE))

    def set_state(self, channel: str, state: dict) -> None:
        self._state[channel] = state
        self._save()

    def clear_state(self, channel: str) -> None:
        self._state[channel] = dict(_BLANK_STATE)
        self._save()

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
            with open(_STATE_FILE, "w") as f:
                json.dump(self._state, f, indent=2)
        except Exception:
            pass  # Persistence is best-effort; never crash the server

    def _load(self) -> dict:
        if not os.path.exists(_STATE_FILE):
            return {}
        try:
            with open(_STATE_FILE) as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}
