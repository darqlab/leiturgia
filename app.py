# eventlet monkey-patch MUST be the very first import
import eventlet
eventlet.monkey_patch()

import logging
logging.getLogger('eventlet.wsgi.server').setLevel(logging.ERROR)

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room
import json, os, copy, re
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from generator import generate_pptx
from generator_odp import generate_odp
from scraper import fetch_hymn_lyrics, fetch_lyrics_by_title
from claude_helpers import clean_stanzas
from hymnal import search_titles, get_by_title, get_by_number
from projection import ProjectionStateManager
from media_manager import list_media
from timer import TimerManager

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024   # 200 MB upload limit
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
proj  = ProjectionStateManager()
timer = TimerManager()
DATA_FILE    = "data/program.json"
HISTORY_FILE = "data/history.json"
HISTORY_MAX  = 6
LYRICS_DIR   = "data/lyrics"


def _lyrics_key(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")


def _slugify(name: str, existing_ids: list = None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not existing_ids or slug not in existing_ids:
        return slug
    n = 2
    while f"{slug}-{n}" in existing_ids:
        n += 1
    return f"{slug}-{n}"


def _lyrics_path(key: str) -> str:
    return os.path.join(LYRICS_DIR, f"{key}.json")


def _load_lyrics(path, hint_number=None, hint_title=None):
    """Load a lyrics JSON file. Migrates old plain-array format to the new
    object format {hymn_number, title, stanzas} on first access.
    Returns the data dict (always has a 'stanzas' key)."""
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        # Old format — build metadata and re-save
        hymn_number = hint_number
        hymn_title  = hint_title
        if not hymn_number:
            key = os.path.splitext(os.path.basename(path))[0]
            if key.isdigit():
                hymn_number = int(key)
        if hymn_number and not hymn_title:
            db = get_by_number(hymn_number)
            if db:
                hymn_title = db["title"]
        data = {"stanzas": data}
        if hymn_number: data["hymn_number"] = hymn_number
        if hymn_title:  data["title"]       = hymn_title
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    return data


def _output_pptx(program_id: str) -> str:
    return f"output/{program_id}.pptx"


def _output_odp(program_id: str) -> str:
    return f"output/{program_id}.odp"


# ── Default program template ─────────────────────────────────────────────────
DEFAULT_PROGRAM = {
    "church":      "SSD GOB",
    "date":        "",
    "pianist":     "Claudine Cabañero",
    "song_leader": "Ana Marie Jaman",

    "service_programs": [
        {
            "id":          "sabbath-school",
            "name":        "Sabbath School",
            "time":        "9:00 a.m.",
            "items": [
                {"item_id": "ss-001", "type": "participant", "title": "Praise Worship",    "part": "Praise Worship",    "participant": "Congregation"},
                {"item_id": "ss-002", "type": "participant", "title": "Welcome Remarks",   "part": "Welcome Remarks",   "participant": "Dainee Rose Jabla"},
                {"item_id": "ss-003", "type": "song",    "title": "Opening Song",      "hymn_number": ""},
                {"item_id": "ss-004", "type": "participant", "title": "Opening Prayer",    "part": "Opening Prayer",    "participant": "Ailene Joy Mutsahuni"},
                {"item_id": "ss-005", "type": "participant", "title": "Special Music",     "part": "Special Music",     "participant": "Quartet"},
                {"item_id": "ss-006", "type": "participant", "title": "Mission Story",     "part": "The Church We Build Together", "participant": "Video"},
                {"item_id": "ss-007", "type": "participant", "title": "Intermission Song", "part": "Intermission Song", "participant": "Tubuan Ukerists"},
                {"item_id": "ss-008", "type": "participant", "title": "Promotional Talk",  "part": "Promotional Talk",  "participant": "Caroline Oliveira"},
                {"item_id": "ss-009", "type": "song",    "title": "Closing Song",      "hymn_number": ""},
                {"item_id": "ss-010", "type": "participant", "title": "Closing Prayer",    "part": "Closing Prayer",    "participant": "Eliezer John Jabla"},
            ],
        },
        {
            "id":          "divine-service",
            "name":        "Divine Service",
            "time":        "10:30 a.m.",
            "items": [
                {"item_id": "ds-001", "type": "participant", "title": "Praise Songs",            "part": "Praise Songs",            "participant": "Congregation"},
                {"item_id": "ds-002", "type": "participant", "title": "Call to Worship",          "part": "Call to Worship",          "participant": "Edward Rodriguez"},
                {"item_id": "ds-003", "type": "song",    "title": "Introit *",                "hymn_number": ""},
                {"item_id": "ds-004", "type": "song",    "title": "Hymn of Celebration",      "hymn_number": ""},
                {"item_id": "ds-005", "type": "participant", "title": "Invocation",               "part": "Invocation",               "participant": ""},
                {"item_id": "ds-006", "type": "song",    "title": "Hymn of Adoration",        "hymn_number": ""},
                {"item_id": "ds-007", "type": "participant", "title": "Scripture Reading",        "part": "Scripture Reading",        "participant": "Jedidiah Klyde Macaraeg"},
                {"item_id": "ds-008", "type": "song",    "title": "Prayer Hymn *",            "hymn_number": ""},
                {"item_id": "ds-009", "type": "participant", "title": "Pastoral Prayer",          "part": "Pastoral Prayer",          "participant": "Jedidiah Klyde Macaraeg"},
                {"item_id": "ds-010", "type": "song",    "title": "Hymn of Response *",       "hymn_number": ""},
                {"item_id": "ds-011", "type": "participant", "title": "Thoughts on Stewardship",  "part": "Thoughts on Stewardship",  "participant": "Exavier Jovaughn Olasiman"},
                {"item_id": "ds-012", "type": "participant", "title": "Offertory Music",          "part": "Offertory Music",          "participant": "Tubuan Ukerists"},
                {"item_id": "ds-013", "type": "song",    "title": "Hymn of Gratitude",        "hymn_number": ""},
                {"item_id": "ds-014", "type": "participant", "title": "Offertory Prayer",         "part": "Offertory Prayer",         "participant": "Exavier Jovaughn Olasiman"},
                {"item_id": "ds-015", "type": "participant", "title": "Children Homily",          "part": "Children Homily",          "participant": "Keen Spenser Gilo"},
                {"item_id": "ds-016", "type": "participant", "title": "Ministry in Song",         "part": "Ministry in Song",         "participant": "Pauleen Angeli Baloyo"},
                {"item_id": "ds-017", "type": "participant", "title": "The Spoken Word",          "part": "The Spoken Word",          "participant": "Sis. Sweetie Ritchil — Associate Treasurer, SSD"},
                {"item_id": "ds-018", "type": "song",    "title": "Hymn of Consecration",     "hymn_number": ""},
                {"item_id": "ds-019", "type": "song",    "title": "Hymn of Hope",             "hymn_number": ""},
                {"item_id": "ds-020", "type": "participant", "title": "Benediction",              "part": "Benediction",              "participant": ""},
            ],
        },
    ],

    "service_team": [
        {"role": "Presider",             "name": "Edward Rodriguez"},
        {"role": "Choristers",           "name": "Joy Olasiman & Exzser Joveil Olasiman"},
        {"role": "Pianist",              "name": "Claudine Cabañero"},
        {"role": "Deacons",              "name": "Joven Agno & Ruel Tagolgol"},
        {"role": "Program Coordinator",  "name": "Amor Maestre & Joy Olasiman"},
        {"role": "Song Leader",          "name": "Ana Marie Jaman"},
    ],
}


def _migrate_item(item, item_id=""):
    """Convert a legacy-schema item (with 'participants') to the new typed schema."""
    if "type" in item:
        return item
    parts  = item.get("participants", [])
    p_name = parts[0].get("name", "") if parts else ""
    if "hymn_number" in item:
        return {
            "item_id":     item_id,
            "type":        "song",
            "title":       item.get("title", ""),
            "hymn_number": item.get("hymn_number", ""),
            **({} if not item.get("lyrics_key") else {"lyrics_key": item["lyrics_key"]}),
        }
    return {
        "item_id":     item_id,
        "type":        "participant",
        "title":       item.get("title", ""),
        "part":        item.get("subtitle", "") or item.get("title", ""),
        "participant": p_name,
    }


def _migrate_items(items, prefix="item"):
    return [_migrate_item(it, item_id=it.get("item_id", f"{prefix}-{i+1:03d}"))
            for i, it in enumerate(items)]


def load_program():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            data = json.load(f)

        # ── Migrate old schema (sabbath_school / divine_service keys) ──────────
        if "sabbath_school" in data and "divine_service" in data:
            ss = data["sabbath_school"]
            ds = data["divine_service"]

            ss_items = ss.get("items", [])
            if ss_items and "type" not in ss_items[0]:
                ss_items = _migrate_items(ss_items, "ss")

            ds_items = []
            for sub in ds.get("subsections", []):
                items = sub.get("items", [])
                if items and "type" not in items[0]:
                    items = _migrate_items(items, "ds")
                ds_items.extend(items)

            data = {
                "church":      data.get("church", ""),
                "date":        data.get("date", ""),
                "pianist":     data.get("pianist", ""),
                "song_leader": data.get("song_leader", ""),
                "service_programs": [
                    {
                        "id":    "sabbath-school",
                        "name":  "Sabbath School",
                        "time":  ss.get("time", "9:00 a.m."),
                        "items": ss_items,
                    },
                    {
                        "id":    "divine-service",
                        "name":  "Divine Service",
                        "time":  ds.get("time", "10:30 a.m."),
                        "items": ds_items,
                    },
                ],
                "service_team": data.get("service_team", []),
            }

        # ── Migrate items within new schema if they still use legacy shape ──────
        for sp in data.get("service_programs", []):
            items = sp.get("items", [])
            if items and "type" not in items[0]:
                sp["items"] = _migrate_items(items, sp["id"][:2])
            # ── Rename old "content" participant items → "participant" ──────────
            for item in sp.get("items", []):
                if item.get("type") == "content" and "participant" in item:
                    item["type"] = "participant"

        return data
    return copy.deepcopy(DEFAULT_PROGRAM)


def save_program(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_history(program):
    """Append a snapshot of the current program to history (capped at HISTORY_MAX)."""
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        except Exception:
            history = []

    snapshot = {
        "saved_at":        datetime.now().isoformat(),
        "church":          program.get("church", ""),
        "date":            program.get("date", ""),
        "service_programs": [
            {
                "id":    sp["id"],
                "name":  sp["name"],
                "items": sp.get("items", []),
            }
            for sp in program.get("service_programs", [])
        ],
    }
    history.insert(0, snapshot)
    history = history[:HISTORY_MAX]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def _prepare_lyrics(items):
    """Load lyrics from cache for song items."""
    for item in items:
        if item.get("type") != "song":
            continue
        if item.get("lyrics_key"):
            path = _lyrics_path(item["lyrics_key"])
            if os.path.exists(path):
                data = _load_lyrics(path,
                                    hint_number=item.get("hymn_number"),
                                    hint_title=item.get("title"))
                item["lyrics"] = data["stanzas"]
        elif item.get("hymn_number") and not item.get("lyrics"):
            try:
                item["lyrics"] = fetch_hymn_lyrics(int(item["hymn_number"]))
            except Exception:
                pass


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    program = load_program()
    programs_meta = {}
    for sp in program.get("service_programs", []):
        pid  = sp["id"]
        pptx = _output_pptx(pid)
        odp  = _output_odp(pid)
        generated_at = None
        if os.path.exists(pptx):
            generated_at = datetime.fromtimestamp(
                os.path.getmtime(pptx)).strftime("%A, %d %B %Y at %H:%M")
        programs_meta[pid] = {
            "name":         sp["name"],
            "generated_at": generated_at,
            "has_pptx":     os.path.exists(pptx),
            "has_odp":      os.path.exists(odp),
        }
    return render_template("index.html", program=program, programs_meta=programs_meta)


@app.route("/api/program", methods=["GET"])
def get_program():
    return jsonify(load_program())


@app.route("/api/program", methods=["POST"])
def save_program_route():
    data = request.get_json()
    save_program(data)
    save_history(data)
    return jsonify({"status": "saved"})


@app.route("/api/generate/<section>", methods=["POST"])
def generate_section_route(section):
    try:
        program = load_program()
        sp = next((p for p in program.get("service_programs", []) if p["id"] == section), None)
        if not sp:
            return jsonify({"status": "error", "message": f"Program '{section}' not found"}), 404
        _prepare_lyrics(sp["items"])
        generate_pptx(program, sp, _output_pptx(section))
        generate_odp(program, sp, _output_odp(section))
        ts = datetime.now().strftime("%A, %d %B %Y at %H:%M")
        return jsonify({"status": "success", "generated_at": ts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/history")
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])
    try:
        with open(HISTORY_FILE) as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])


@app.route("/api/fetch-hymn/<int:number>")
def fetch_hymn(number):
    try:
        lyrics = fetch_hymn_lyrics(number)
        return jsonify({"status": "ok", "stanzas": lyrics})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/fetch-lyrics")
def fetch_lyrics_route():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"status": "error", "message": "No query provided"}), 400
    try:
        hymn_number = None
        hymn_title  = None

        if q.isdigit():
            key = q
            hymn_number = int(q)
        else:
            # Resolve title → hymn number via local DB so key is always numeric
            db_result = get_by_title(q)
            if db_result:
                key         = str(db_result["number"])
                hymn_number = db_result["number"]
                hymn_title  = db_result["title"]
            else:
                key = _lyrics_key(q)

        path = _lyrics_path(key)
        if os.path.exists(path):
            data    = _load_lyrics(path, hint_number=hymn_number, hint_title=hymn_title)
            stanzas = data["stanzas"]
            hymn_number = hymn_number or data.get("hymn_number")
            hymn_title  = hymn_title  or data.get("title")
            resp = {"status": "ok", "key": key, "count": len(stanzas), "source": "cache"}
            if hymn_number: resp["hymn_number"] = hymn_number
            if hymn_title:  resp["title"]       = hymn_title
            return jsonify(resp)

        stanzas = fetch_hymn_lyrics(hymn_number) if hymn_number else fetch_lyrics_by_title(q)
        if not stanzas:
            return jsonify({"status": "error", "message": "No lyrics found"})
        stanzas = clean_stanzas(stanzas, title=hymn_title or q)
        lyrics_data = {"stanzas": stanzas}
        if hymn_number: lyrics_data["hymn_number"] = hymn_number
        if hymn_title:  lyrics_data["title"]       = hymn_title
        with open(path, "w") as f:
            json.dump(lyrics_data, f, indent=2)
        resp = {"status": "ok", "key": key, "count": len(stanzas), "source": "web"}
        if hymn_number: resp["hymn_number"] = hymn_number
        if hymn_title:  resp["title"]       = hymn_title
        return jsonify(resp)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/lyrics/<key>")
def get_lyrics(key):
    path = _lyrics_path(key)
    if not os.path.exists(path):
        return jsonify({"status": "error", "message": "Lyrics file not found"}), 404
    data = _load_lyrics(path)
    return jsonify({"status": "ok", "stanzas": data["stanzas"],
                    "hymn_number": data.get("hymn_number"),
                    "title": data.get("title")})


@app.route("/api/hymnal/search")
def hymnal_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    return jsonify(search_titles(q, limit=8))


@app.route("/download/<section>")
def download_pptx(section):
    path = _output_pptx(section)
    if os.path.exists(path):
        name = section.replace("-", " ").title().replace(" ", "") + ".pptx"
        return send_file(path, as_attachment=True, download_name=name)
    return "No file generated yet.", 404


@app.route("/download/<section>/odp")
def download_odp(section):
    path = _output_odp(section)
    if os.path.exists(path):
        name = section.replace("-", " ").title().replace(" ", "") + ".odp"
        return send_file(path, as_attachment=True, download_name=name)
    return "No ODP file generated yet.", 404


@app.route("/api/import-sheet", methods=["POST"])
def import_sheet():
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        return jsonify({"status": "error", "message": "GOOGLE_SHEET_ID not set in .env"}), 400
    try:
        from sheets import fetch_and_parse
        program = load_program()
        if not program.get("date"):
            return jsonify({"status": "error", "message": "Set the program date before importing"}), 400

        updates = fetch_and_parse(sheet_id, program["date"])

        count = 0
        for key, value in updates.items():
            if key == "__song_leader__":
                program["song_leader"] = value
                count += 1
            elif key == "__pianist__":
                program["pianist"] = value
                count += 1
            elif isinstance(key, tuple):
                sp_id, item_id = key
                for sp in program.get("service_programs", []):
                    if sp["id"] != sp_id:
                        continue
                    for item in sp.get("items", []):
                        if item["item_id"] == item_id and item.get("type") == "participant":
                            item["participant"] = value
                            count += 1

        save_program(program)
        save_history(program)
        return jsonify({"status": "ok", "updated": count})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/program/add", methods=["POST"])
def add_program():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"status": "error", "message": "Name is required"}), 400
    program = load_program()
    existing_ids = [sp["id"] for sp in program.get("service_programs", [])]
    pid = _slugify(name, existing_ids)
    program["service_programs"].append({"id": pid, "name": name, "time": "", "items": []})
    save_program(program)
    save_history(program)
    return jsonify({"status": "ok", "id": pid})


@app.route("/api/program/add-from-sheet", methods=["POST"])
def add_program_from_sheet():
    data     = request.get_json()
    name     = (data.get("name") or "").strip()
    sheet_id = (data.get("sheet_id") or "").strip()
    if not name:
        return jsonify({"status": "error", "message": "Name is required"}), 400
    if not sheet_id:
        return jsonify({"status": "error", "message": "Sheet ID or URL is required"}), 400
    # Extract sheet ID from a full Google Sheets URL if needed
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", sheet_id)
    if m:
        sheet_id = m.group(1)
    program = load_program()
    existing_ids = [sp["id"] for sp in program.get("service_programs", [])]
    pid = _slugify(name, existing_ids)
    try:
        from sheets import parse_program_sheet
        items = parse_program_sheet(sheet_id, pid)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    program["service_programs"].append({"id": pid, "name": name, "time": "", "items": items})
    save_program(program)
    save_history(program)
    return jsonify({"status": "ok", "id": pid, "item_count": len(items)})


@app.route("/api/programs/<program_id>", methods=["DELETE"])
def delete_program(program_id):
    program = load_program()
    programs = program.get("service_programs", [])
    if len(programs) <= 1:
        return jsonify({"error": "cannot delete last program"}), 400
    program["service_programs"] = [p for p in programs if p["id"] != program_id]
    save_program(program)
    return jsonify({"ok": True, "selected": program["service_programs"][0]["id"]})


@app.route("/api/reset", methods=["POST"])
def reset():
    save_program(copy.deepcopy(DEFAULT_PROGRAM))
    return jsonify({"status": "reset"})


# ── Projection routes ────────────────────────────────────────────────────────
@app.route("/ch<int:n>")
def projection_channel(n):
    channel = f"ch{n}"
    return render_template("projection.html", channel=channel)


# ── Static theme files ───────────────────────────────────────────────────────
from flask import send_from_directory

_THEMES = [
    {"id": "default",  "name": "Default (Navy/Gold)"},
    {"id": "midnight", "name": "Midnight"},
    {"id": "dawn",     "name": "Dawn"},
    {"id": "forest",   "name": "Forest"},
    {"id": "slate",    "name": "Slate"},
    {"id": "ivory",    "name": "Ivory (Light)"},
    {"id": "ocean",    "name": "Ocean"},
    {"id": "ember",    "name": "Ember"},
    {"id": "pearl",    "name": "Pearl"},
    {"id": "royal",    "name": "Royal"},
]

@app.route("/static/themes/<path:filename>")
def serve_theme(filename):
    themes_dir = os.path.join(app.root_path, "templates", "themes")
    return send_from_directory(themes_dir, filename)

@app.route("/api/themes")
def api_themes():
    return jsonify(_THEMES)


# ── SocketIO event handlers ──────────────────────────────────────────────────
@socketio.on('join')
def on_join(data):
    channel = data.get('channel', 'ch1')
    join_room(channel)

@socketio.on('state:restore')
def on_state_restore(data):
    channel = data.get('channel', 'ch1')
    state   = proj.get_state(channel)
    # Don't restore blank — display stays in "Waiting for content…" mode
    if state.get('type') != 'blank':
        emit('slide:show', state)

@socketio.on('slide:show')
def on_slide_show(data):
    channel = data.get('channel', 'ch1')
    state   = {'type': 'text', 'data': data, 'theme_id': data.get('theme_id', 'default')}
    proj.set_state(channel, state)
    emit('slide:show', data, to=channel)

@socketio.on('slide:blank')
def on_slide_blank(data):
    channel = data.get('channel', 'ch1')
    state   = {'type': 'blank', 'data': {}, 'theme_id': 'default'}
    proj.set_state(channel, state)
    emit('slide:blank', state, to=channel)

@socketio.on('slide:edit')
def on_slide_edit(data):
    channel = data.get('channel', 'ch1')
    state   = {'type': 'text', 'data': data, 'theme_id': data.get('theme_id', 'default')}
    proj.set_state(channel, state)
    emit('slide:edit', data, to=channel)

@socketio.on('media:image')
def on_media_image(data):
    channel = data.get('channel', 'ch1')
    state   = {'type': 'image', 'data': data, 'theme_id': 'default'}
    proj.set_state(channel, state)
    emit('media:image', data, to=channel)

@socketio.on('media:video')
def on_media_video(data):
    channel = data.get('channel', 'ch1')
    state   = {'type': 'video', 'data': data, 'theme_id': 'default'}
    proj.set_state(channel, state)
    emit('media:video', data, to=channel)

@socketio.on('media:status')
def on_media_status(data):
    channel = data.get('channel', 'ch1')
    emit('media:status', data, to=channel)

@socketio.on('announcement')
def on_announcement(data):
    channel = data.get('channel', 'ch1')
    state   = {'type': 'announcement', 'data': data, 'theme_id': 'default'}
    proj.set_state(channel, state)
    emit('announcement', data, to=channel)

@socketio.on('timer:show')
def on_timer_show(data):
    channel = data.get('channel', 'ch1')
    state_d = timer.show(channel, int(data.get('seconds', 0)), data.get('label', ''))
    state_d.update({'channel': channel, 'type': 'timer'})
    proj.set_state(channel, {'type': 'timer', 'data': state_d, 'theme_id': 'default'})
    emit('timer:show', state_d, to=channel)

@socketio.on('timer:start')
def on_timer_start(data):
    channel = data.get('channel', 'ch1')
    secs    = data.get('seconds')
    label   = data.get('label')
    state_d = timer.start(channel, int(secs) if secs is not None else None, label)
    state_d.update({'channel': channel, 'type': 'timer'})
    proj.set_state(channel, {'type': 'timer', 'data': state_d, 'theme_id': 'default'})
    emit('timer:start', state_d, to=channel)

@socketio.on('timer:pause')
def on_timer_pause(data):
    channel = data.get('channel', 'ch1')
    state_d = timer.pause(channel)
    state_d.update({'channel': channel})
    emit('timer:pause', state_d, to=channel)

@socketio.on('timer:reset')
def on_timer_reset(data):
    channel = data.get('channel', 'ch1')
    secs    = data.get('seconds')
    state_d = timer.reset(channel, int(secs) if secs is not None else None)
    state_d.update({'channel': channel, 'type': 'timer'})
    proj.set_state(channel, {'type': 'timer', 'data': state_d, 'theme_id': 'default'})
    emit('timer:reset', state_d, to=channel)


# ── Media routes ─────────────────────────────────────────────────────────────
_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
_VIDEO_EXTS = {'.mp4', '.webm', '.mov'}

@app.route("/api/media")
def api_media():
    return jsonify(list_media())

@app.route("/api/media/upload", methods=["POST"])
def upload_media():
    from werkzeug.utils import secure_filename
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({"status": "error", "message": "Empty filename"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext in _IMAGE_EXTS:
        media_type = "image"
        subdir     = "images"
    elif ext in _VIDEO_EXTS:
        media_type = "video"
        subdir     = "videos"
    else:
        return jsonify({"status": "error", "message": f"Unsupported file type: {ext}"}), 400

    filename  = secure_filename(f.filename)
    save_dir  = os.path.join(app.root_path, "media", subdir)
    os.makedirs(save_dir, exist_ok=True)
    f.save(os.path.join(save_dir, filename))

    url = f"/media/{subdir}/{filename}"
    return jsonify({"status": "ok", "url": url, "media_type": media_type})

@app.route("/media/<subdir>/<path:filename>")
def serve_media(subdir, filename):
    if subdir not in ("images", "videos"):
        return "Not found", 404
    media_dir = os.path.join(app.root_path, "media", subdir)
    return send_from_directory(media_dir, filename)


# ── YouTube / platform download ───────────────────────────────────────────────
import shutil as _shutil
_FFMPEG = _shutil.which('ffmpeg')

# When ffmpeg is available: download best video+audio streams and merge.
# When ffmpeg is absent: fall back to pre-merged progressive streams (≤720p on YouTube).
_QUALITY_MERGE = {
    'best':  'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
    '720p':  'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
    '480p':  'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]',
    '360p':  'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]',
    'audio': 'bestaudio[ext=m4a]/bestaudio',
}
_QUALITY_NOFFMPEG = {
    'best':  'best[ext=mp4]/best',
    '1080p': 'best[height<=1080][ext=mp4]/best[height<=1080]',
    '720p':  'best[height<=720][ext=mp4]/best[height<=720]',
    '480p':  'best[height<=480][ext=mp4]/best[height<=480]',
    '360p':  'best[height<=360][ext=mp4]/best[height<=360]',
    'audio': 'bestaudio[ext=m4a]/bestaudio',
}

def _get_format(quality):
    table = _QUALITY_MERGE if _FFMPEG else _QUALITY_NOFFMPEG
    return table.get(quality, table['best'])

def _yt_progress_hook(d, item_id, sid):
    status = d.get('status')
    if status == 'downloading':
        raw = d.get('_percent_str', '0%').strip()
        try:
            percent = float(raw.replace('%', ''))
        except ValueError:
            percent = 0.0
        socketio.emit('yt:progress', {
            'item_id': item_id,
            'status':  'downloading',
            'percent': percent,
            'speed':   d.get('_speed_str', '').strip(),
            'eta':     d.get('eta', 0),
        }, room=sid)
    elif status == 'finished':
        socketio.emit('yt:progress', {
            'item_id': item_id,
            'status':  'processing',
            'percent': 100.0,
            'speed':   '',
            'eta':     0,
        }, room=sid)

def _yt_download_task(url, quality, item_id, sid):
    import yt_dlp
    videos_dir = os.path.join(app.root_path, 'media', 'videos')
    os.makedirs(videos_dir, exist_ok=True)
    ydl_opts = {
        'format':         _get_format(quality),
        'outtmpl':        os.path.join(videos_dir, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: _yt_progress_hook(d, item_id, sid)],
        'quiet':          True,
        'no_warnings':    True,
    }
    if _FFMPEG:
        ydl_opts['merge_output_format'] = 'mp4'
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info     = ydl.extract_info(url, download=True)
            raw_name = os.path.basename(ydl.prepare_filename(info))
            # If ffmpeg merged to mp4, the extension will be .mp4 regardless of raw_name
            if _FFMPEG:
                final = os.path.splitext(raw_name)[0] + '.mp4'
            else:
                # Find the actual downloaded file (extension may vary)
                base  = os.path.splitext(raw_name)[0]
                found = next(
                    (f for f in os.listdir(videos_dir) if f.startswith(base)),
                    raw_name
                )
                final = found
            final_url = f'/media/videos/{final}'
        socketio.emit('yt:done', {
            'item_id':  item_id,
            'url':      final_url,
            'filename': final,
        }, room=sid)
    except Exception as exc:
        socketio.emit('yt:error', {
            'item_id': item_id,
            'message': str(exc),
        }, room=sid)

@socketio.on('yt:download:start')
def on_yt_download_start(data):
    from flask_socketio import disconnect
    url     = (data.get('url') or '').strip()
    quality = data.get('quality', 'best')
    item_id = data.get('item_id', '')
    sid     = request.sid

    if not url.startswith(('http://', 'https://')):
        emit('yt:error', {'item_id': item_id, 'message': 'Invalid URL — must start with http:// or https://'})
        return

    socketio.start_background_task(_yt_download_task, url, quality, item_id, sid)


if __name__ == "__main__":
    os.makedirs("data",        exist_ok=True)
    os.makedirs(LYRICS_DIR,    exist_ok=True)
    os.makedirs("output",      exist_ok=True)
    os.makedirs("media/images", exist_ok=True)
    os.makedirs("media/videos", exist_ok=True)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
