import csv
import io
import requests
from datetime import datetime

EXPORT_URL = "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}

_SS = "sabbath-school"
_DS = "divine-service"

# Columns that map directly to a (service_program_id, item_id) target
COLUMN_MAP = {
    # Sabbath School
    2:  (_SS, "ss-002"),   # Welcome Remarks
    5:  (_SS, "ss-004"),   # Opening Prayer
    6:  (_SS, "ss-005"),   # Special Music
    11: (_SS, "ss-007"),   # Intermission Song
    12: (_SS, "ss-008"),   # Promotional Talk
    14: (_SS, "ss-010"),   # Closing Prayer
    # Program-level
    3:  "__song_leader__",
    4:  "__pianist__",
    # Divine Service
    17: (_DS, "ds-002"),   # Presider / Call to Worship
    20: (_DS, "ds-016"),   # Ministry in Song
    21: (_DS, "ds-011"),   # Thoughts on Stewardship
    22: (_DS, "ds-007"),   # Scripture Reading
    24: (_DS, "ds-012"),   # Offertory Music
    25: (_DS, "ds-015"),   # Children Homily
    27: (_DS, "ds-017"),   # The Spoken Word (Speaker)
}

# First non-empty of these columns → Mission Story participant
MISSION_STORY_COLS = [7, 8, 9, 10]
MISSION_STORY_TARGET = (_SS, "ss-006")


def parse_program_sheet(sheet_id: str, program_id: str) -> list:
    """
    Fetch a flat Google Sheet and return a list of typed program items.

    Expected sheet format — row 1 is a header (skipped); each subsequent
    non-empty row is one program item:

      Col A  — Title
      Col B  — Type ("song" | "participant"; defaults to "participant" if blank)
      Col C  — Part / Role (defaults to Title if blank)
      Col D  — Participant name  (for participant items)
               Hymn number       (for song items, cast to int)

    item_id is auto-generated as "{program_id}-{index:03d}".
    """
    url = EXPORT_URL.format(sheet_id=sheet_id)
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()

    rows = list(csv.reader(io.StringIO(r.text)))
    data_rows = rows[1:]  # skip header row

    items = []
    for row in data_rows:
        # Pad to at least 4 columns
        row = list(row) + [""] * (4 - len(row))
        title = row[0].strip()
        if not title:
            continue

        item_type = row[1].strip().lower() or "participant"
        part      = row[2].strip() or title
        col_d     = row[3].strip()
        item_id   = f"{program_id}-{len(items) + 1:03d}"

        if item_type == "song":
            hymn_number = ""
            try:
                hymn_number = int(col_d)
            except (ValueError, TypeError):
                pass
            items.append({
                "item_id":     item_id,
                "type":        "song",
                "title":       title,
                "hymn_number": hymn_number,
            })
        else:
            items.append({
                "item_id":     item_id,
                "type":        "participant",
                "title":       title,
                "part":        part,
                "participant": col_d,
            })

    return items


def fetch_and_parse(sheet_id: str, date_str: str) -> dict:
    """
    Fetch the sheet CSV and return a flat updates dict:
      { (sp_id, item_id): name, "__song_leader__": name, "__pianist__": name }

    Raises ValueError if the date row is not found.
    Raises requests.RequestException on network error.
    """
    url = EXPORT_URL.format(sheet_id=sheet_id)
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()

    rows = list(csv.reader(io.StringIO(r.text)))
    # rows[0..2] = merged header rows; data starts at row index 3
    data_rows = rows[3:]

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    target_month = dt.strftime("%B")   # e.g. "March"
    target_day   = str(dt.day)         # e.g. "7"  (no leading zero)

    current_month = ""
    data_row = None
    for row in data_rows:
        if not row:
            continue
        if row[0].strip():
            current_month = row[0].strip()
        day_cell = row[1].strip() if len(row) > 1 else ""
        if (current_month.lower() == target_month.lower()
                and day_cell == target_day):
            data_row = row
            break

    if data_row is None:
        raise ValueError(f"No sheet row found for {target_month} {target_day}")

    def col(idx):
        return data_row[idx].strip() if idx < len(data_row) else ""

    updates = {}

    for idx, target in COLUMN_MAP.items():
        val = col(idx)
        if val:
            updates[target] = val

    # Mission Story: use first non-empty class column
    for idx in MISSION_STORY_COLS:
        val = col(idx)
        if val:
            updates[MISSION_STORY_TARGET] = val
            break

    return updates
