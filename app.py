from flask import Flask, render_template, request, jsonify, send_file
import json, os, copy
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from generator import generate_pptx
from generator_odp import generate_odp
from scraper import fetch_hymn_lyrics, fetch_lyrics_by_title
from claude_helpers import clean_stanzas
from hymnal import search_titles

app = Flask(__name__)
DATA_FILE    = "data/program.json"
HISTORY_FILE = "data/history.json"
HISTORY_MAX  = 6
LYRICS_DIR   = "data/lyrics"


def _lyrics_key(query: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")


def _lyrics_path(key: str) -> str:
    return os.path.join(LYRICS_DIR, f"{key}.json")


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
                with open(path) as f:
                    item["lyrics"] = json.load(f)
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
        key  = _lyrics_key(q)
        path = _lyrics_path(key)
        if os.path.exists(path):
            with open(path) as f:
                stanzas = json.load(f)
            return jsonify({"status": "ok", "key": key, "count": len(stanzas), "source": "cache"})
        stanzas = fetch_hymn_lyrics(int(q)) if q.isdigit() else fetch_lyrics_by_title(q)
        if not stanzas:
            return jsonify({"status": "error", "message": "No lyrics found"})
        stanzas = clean_stanzas(stanzas, title=q)
        with open(path, "w") as f:
            json.dump(stanzas, f, indent=2)
        return jsonify({"status": "ok", "key": key, "count": len(stanzas), "source": "web"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/lyrics/<key>")
def get_lyrics(key):
    path = _lyrics_path(key)
    if not os.path.exists(path):
        return jsonify({"status": "error", "message": "Lyrics file not found"}), 404
    with open(path) as f:
        stanzas = json.load(f)
    return jsonify({"status": "ok", "stanzas": stanzas})


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


@app.route("/api/reset", methods=["POST"])
def reset():
    save_program(copy.deepcopy(DEFAULT_PROGRAM))
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    os.makedirs("data",     exist_ok=True)
    os.makedirs(LYRICS_DIR, exist_ok=True)
    os.makedirs("output",   exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=False)
