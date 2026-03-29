"""
timer.py — Server-side countdown timer state per channel.

TimerManager tracks a countdown for each channel independently.
The actual tick happens client-side (projection.html); the server
stores the last-known state so state:restore can replay it.

Phase 6 adds start/pause/reset/jump controls.
"""

import time


class TimerState:
    def __init__(self):
        self.seconds: int   = 0
        self.label:   str   = ""
        self.running: bool  = False
        self._started_at: float | None = None
        self._started_secs: int        = 0

    def start(self, seconds: int | None = None, label: str | None = None):
        if seconds is not None:
            self.seconds = seconds
        if label is not None:
            self.label = label
        self.running      = True
        self._started_at  = time.monotonic()
        self._started_secs = self.seconds

    def pause(self):
        if self.running and self._started_at is not None:
            elapsed = int(time.monotonic() - self._started_at)
            self.seconds = max(0, self._started_secs - elapsed)
        self.running     = False
        self._started_at = None

    def reset(self, seconds: int | None = None):
        self.running      = False
        self._started_at  = None
        if seconds is not None:
            self.seconds = seconds

    def current_seconds(self) -> int:
        """Return the live second count, accounting for elapsed time if running."""
        if self.running and self._started_at is not None:
            elapsed = int(time.monotonic() - self._started_at)
            return max(0, self._started_secs - elapsed)
        return self.seconds

    def to_dict(self) -> dict:
        return {
            "seconds": self.current_seconds(),
            "label":   self.label,
            "running": self.running,
        }


class TimerManager:
    def __init__(self):
        self._timers: dict[str, TimerState] = {}

    def _get(self, channel: str) -> TimerState:
        if channel not in self._timers:
            self._timers[channel] = TimerState()
        return self._timers[channel]

    def show(self, channel: str, seconds: int, label: str) -> dict:
        t = self._get(channel)
        t.reset(seconds)
        t.label = label
        return t.to_dict()

    def start(self, channel: str, seconds: int | None = None, label: str | None = None) -> dict:
        t = self._get(channel)
        t.start(seconds, label)
        return t.to_dict()

    def pause(self, channel: str) -> dict:
        t = self._get(channel)
        t.pause()
        return t.to_dict()

    def reset(self, channel: str, seconds: int | None = None) -> dict:
        t = self._get(channel)
        t.reset(seconds)
        return t.to_dict()

    def get(self, channel: str) -> dict:
        return self._get(channel).to_dict()
