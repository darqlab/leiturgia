"""
roles.py — Role-to-channel assignment manager.

Tracks which channels carry each output role (MAIN, RUNDOWN, TIMER, ANNOUNCEMENT).
Any role can be mirrored to multiple channels. Persists to data/role_assignments.json.
"""

import json
import os

_PERSIST_FILE = "data/role_assignments.json"
_VALID_ROLES    = ('main', 'rundown', 'timer', 'announcement')
_VALID_CHANNELS = ('ch1', 'ch2', 'ch3', 'ch4', 'ch5')
_DEFAULT = {
    'main':         ['ch1'],
    'rundown':      ['ch2'],
    'timer':        ['ch3'],
    'announcement': ['ch4'],
}


class RoleManager:
    def __init__(self):
        self._assignments: dict[str, list[str]] = self._load()

    # ── Public API ─────────────────────────────────────────────────────────────

    def assign(self, channels: list[str], role: str) -> dict:
        """Move each channel to role, removing it from its previous role."""
        for ch in channels:
            for r in _VALID_ROLES:
                if ch in self._assignments[r] and r != role:
                    self._assignments[r].remove(ch)
            if ch not in self._assignments[role]:
                self._assignments[role].append(ch)
        self._save()
        return self.to_dict()

    def get_channels(self, role: str) -> list[str]:
        return list(self._assignments.get(role, []))

    def get_role(self, channel: str) -> str | None:
        for role, channels in self._assignments.items():
            if channel in channels:
                return role
        return None

    def to_dict(self) -> dict:
        return {r: list(chs) for r, chs in self._assignments.items()}

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(_PERSIST_FILE), exist_ok=True)
            with open(_PERSIST_FILE, 'w') as f:
                json.dump(self._assignments, f, indent=2)
        except Exception:
            pass

    def _load(self) -> dict:
        if os.path.exists(_PERSIST_FILE):
            try:
                with open(_PERSIST_FILE) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # Ensure all roles are present
                    result = {r: list(_DEFAULT[r]) for r in _VALID_ROLES}
                    for r in _VALID_ROLES:
                        if r in data and isinstance(data[r], list):
                            result[r] = data[r]
                    return result
            except Exception:
                pass
        assignments = {r: list(chs) for r, chs in _DEFAULT.items()}
        self._assignments = assignments
        self._save()
        return assignments
