"""
rundown.py — Rundown display state for CH2 (participants holding area).

Derives the display list from the loaded program + active item reference.
Does not persist — regenerated on every item change or timer tick.
"""


_DEFAULT_MINUTES: dict[str, int] = {
    "song":        4,
    "prayer":      3,
    "content":     5,
    "participant": 5,
    "media":       5,
    "image":       5,
    "video":       5,
}

# Row color per (status, timer_state) — matches Channel Output doc §5 table
_ROW_COLOR = {
    ("done",     "normal"):   "dimmed",
    ("done",     "warning"):  "dimmed",
    ("done",     "overtime"): "dimmed",
    ("active",   "normal"):   "white",
    ("active",   "warning"):  "yellow",
    ("active",   "overtime"): "red",
    ("next",     "normal"):   "none",
    ("next",     "warning"):  "yellow",
    ("next",     "overtime"): "red",
    ("upcoming", "normal"):   "none",
    ("upcoming", "warning"):  "none",
    ("upcoming", "overtime"): "none",
}


class RundownManager:
    def __init__(self):
        self._active_program_id: str | None = None
        self._active_item_id:    str | None = None

    def set_active(self, program_id: str, item_id: str) -> None:
        self._active_program_id = program_id
        self._active_item_id    = item_id

    def get_display(self, program: dict, timer_state: str = "normal") -> dict:
        """
        Returns the rundown display payload for CH2.

        program:     the full program dict loaded from program.json
        timer_state: 'normal' | 'warning' | 'overtime'
        """
        service = self._find_program(program)
        if service is None:
            return self._empty(program)

        items     = service.get("items", [])
        active_id = self._active_item_id
        found_active = False
        display_items = []

        found_next = False
        for item in items:
            item_id = item.get("item_id", "")

            if active_id is None:
                status = "upcoming"
            elif item_id == active_id:
                status = "active"
                found_active = True
            elif not found_active:
                status = "done"
            elif not found_next:
                status = "next"
                found_next = True
            else:
                status = "upcoming"

            is_timed  = item.get("timed", True)
            row_color = _ROW_COLOR.get((status, timer_state), "none")
            allotted  = self._allotted_seconds(item) if is_timed else 0

            display_items.append({
                "item_id":          item_id,
                "title":            item.get("title", item.get("name", "—")),
                "participant":      item.get("participant", ""),
                "status":           status,
                "allotted_seconds": allotted,
                "row_color":        row_color,
                "timed":            is_timed,
            })

        return {
            "active_item_id": active_id,
            "program_name":   service.get("name", ""),
            "date":           program.get("date", ""),
            "items":          display_items,
            "timer_state":    timer_state,
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _find_program(self, program: dict) -> dict | None:
        for sp in program.get("service_programs", []):
            if sp.get("id") == self._active_program_id:
                return sp
        # Fall back to first program if none matched
        progs = program.get("service_programs", [])
        return progs[0] if progs else None

    def _allotted_seconds(self, item: dict) -> int:
        if "allotted_minutes" in item:
            return int(item["allotted_minutes"]) * 60
        itype = item.get("type", "participant")
        return _DEFAULT_MINUTES.get(itype, 10) * 60

    def _empty(self, program: dict) -> dict:
        return {
            "active_item_id": None,
            "program_name":   "",
            "date":           program.get("date", ""),
            "items":          [],
            "timer_state":    "normal",
        }
