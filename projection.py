"""
projection.py — In-memory per-channel projection state manager.

State schema per channel:
  {
    "type": "text" | "image" | "video" | "announcement" | "timer" | "blank",
    "data": { ... },
    "theme_id": "default"
  }

Phase 7 will add JSON persistence here.
"""


_BLANK_STATE = {"type": "blank", "data": {}, "theme_id": "default"}


class ProjectionStateManager:
    def __init__(self):
        self._state: dict[str, dict] = {}

    def get_state(self, channel: str) -> dict:
        return self._state.get(channel, dict(_BLANK_STATE))

    def set_state(self, channel: str, state: dict) -> None:
        self._state[channel] = state

    def clear_state(self, channel: str) -> None:
        self._state[channel] = dict(_BLANK_STATE)
