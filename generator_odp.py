"""
generator_odp.py — Native LibreOffice Impress (.odp) generator.
Uses odfpy (python-odf) to write ODP files directly — no PPTX conversion.
Same slide sequence and colour scheme as generator.py.
"""
from odf.opendocument import OpenDocumentPresentation
from odf import style, draw, text

# ── Slide dimensions: 10" × 5.625" ──────────────────────────────────────────
W_IN = 10.0
H_IN = 5.625
W    = W_IN * 2.54   # cm
H    = H_IN * 2.54   # cm

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "bg":      "#0D1B3E",
    "bgCard":  "#1A2B5C",
    "bgDark":  "#091428",
    "gold":    "#D4A843",
    "goldLt":  "#F0C96A",
    "white":   "#FFFFFF",
    "offWhite":"#E8EAF0",
    "muted":   "#8C9AB5",
}

FONT_H = "Georgia"
FONT_B = "Calibri"


def _cm(v):
    return f"{v:.4f}cm"


def _i(v):
    """Inches → cm."""
    return v * 2.54


# ── Document builder ──────────────────────────────────────────────────────────
class _Doc:
    """Wraps OpenDocumentPresentation with helper drawing methods.

    odfpy requires the actual Style *object* (not just its name string)
    to be passed as `stylename` to draw elements such as Rect, Frame,
    Ellipse.  The Style object's name is used when the XML is serialised.
    """

    def __init__(self):
        self.doc = OpenDocumentPresentation()
        self._n  = 0
        self._init_layout()

    def _uid(self):
        self._n += 1
        return f"a{self._n}"

    def _init_layout(self):
        pl = style.PageLayout(name="PL1")
        self.doc.automaticstyles.addElement(pl)
        pl.addElement(style.PageLayoutProperties(
            margin="0cm",
            pagewidth=_cm(W),
            pageheight=_cm(H),
            printorientation="landscape",
        ))
        mp = style.MasterPage(name="Blank", pagelayoutname="PL1")
        self.doc.masterstyles.addElement(mp)

    # ── Style factories (return Style objects) ────────────────────────────────

    def _gs(self, fill="none", fillcolor=None, stroke="none", va=None):
        """Create, register, and return a graphic Style object."""
        s  = style.Style(name=self._uid(), family="graphic")
        kw = dict(fill=fill, stroke=stroke)
        if fillcolor:
            kw["fillcolor"] = fillcolor
        if va:
            kw["textareaverticalalign"] = va
        s.addElement(style.GraphicProperties(**kw))
        self.doc.automaticstyles.addElement(s)
        return s   # <-- Style object, not name string

    def _ps(self, align="start", fontfamily=None, fontsize=14,
            color="#FFFFFF", bold=False, italic=False):
        """Create, register, and return a paragraph Style object."""
        s  = style.Style(name=self._uid(), family="paragraph")
        ta = {"left": "start", "center": "center", "right": "end"}.get(align, "start")
        s.addElement(style.ParagraphProperties(textalign=ta))
        s.addElement(style.TextProperties(
            fontfamily=fontfamily or FONT_B,
            fontsize=f"{fontsize}pt",
            color=color,
            fontweight="bold"  if bold   else "normal",
            fontstyle="italic" if italic else "normal",
        ))
        self.doc.automaticstyles.addElement(s)
        return s   # <-- Style object

    # ── Drawing primitives ────────────────────────────────────────────────────

    def new_slide(self):
        slide = draw.Page(name=self._uid(), masterpagename="Blank")
        self.doc.presentation.addElement(slide)
        self.rect(slide, 0, 0, W_IN, H_IN, C["bg"])
        return slide

    def rect(self, slide, x, y, w, h, color):
        """Filled rectangle — coords in inches."""
        s = self._gs(fill="solid", fillcolor=color)
        r = draw.Rect(
            stylename=s,
            x=_cm(_i(x)), y=_cm(_i(y)),
            width=_cm(_i(w)), height=_cm(_i(h)),
        )
        slide.addElement(r)

    def txt(self, slide, content, x, y, w, h,
            font_size=14, color=None, bold=False, italic=False,
            align="left", font_face=None, valign="top"):
        """Text frame — coords in inches."""
        color     = color     or C["white"]
        font_face = font_face or FONT_B
        gs = self._gs(fill="none", stroke="none",
                      va="middle" if valign == "middle" else None)
        ps = self._ps(align=align, fontfamily=font_face, fontsize=font_size,
                      color=color, bold=bold, italic=italic)
        frame = draw.Frame(
            stylename=gs,
            x=_cm(_i(x)), y=_cm(_i(y)),
            width=_cm(_i(w)), height=_cm(_i(h)),
        )
        tb = draw.TextBox()
        frame.addElement(tb)
        p = text.P(stylename=ps)
        p.addText(content)
        tb.addElement(p)
        slide.addElement(frame)

    def dot(self, slide, x, y, d, color):
        """Filled circle — coords and diameter in inches."""
        s = self._gs(fill="solid", fillcolor=color)
        e = draw.Ellipse(
            stylename=s,
            x=_cm(_i(x)), y=_cm(_i(y)),
            width=_cm(_i(d)), height=_cm(_i(d)),
        )
        slide.addElement(e)

    def save(self, path):
        self.doc.save(path)


# ── Shared slide furniture ────────────────────────────────────────────────────

def _top_bar(doc, slide):
    doc.rect(slide, 0, 0,       W_IN, 0.06, C["gold"])

def _bottom_bar(doc, slide):
    doc.rect(slide, 0, H_IN - 0.06, W_IN, 0.06, C["gold"])

def _header(doc, slide, section_name, right_text=""):
    doc.rect(slide, 0, 0, W_IN, 0.52, C["bgDark"])
    doc.txt(slide, section_name.upper(), 0.3, 0.10, 6, 0.35,
            font_size=11, color=C["gold"], bold=True)
    if right_text:
        doc.txt(slide, right_text, 0, 0.10, 9.7, 0.35,
                font_size=11, color=C["muted"], align="right")


# ── Hymn helpers ──────────────────────────────────────────────────────────────

def _stanza_label(stanza):
    t = stanza.get("type", "verse")
    n = stanza.get("number", 1)
    if t == "verse":   return f"VERSE {n}"
    if t == "chorus":  return "CHORUS"
    if t == "refrain": return "REFRAIN"
    if t == "bridge":  return "BRIDGE"
    return f"VERSE {n}"


def _hymn_slide_sequence(stanzas):
    """v1, R, v2, R, v3, R … (refrain interleaved after each verse)."""
    verses  = [s for s in stanzas if s.get("type", "verse") == "verse"]
    chorus  = next((s for s in stanzas
                    if s.get("type") in ("chorus", "refrain")), None)
    bridges = [s for s in stanzas if s.get("type") == "bridge"]

    if not chorus:
        return stanzas

    seq = []
    for v in verses:
        seq.append(v)
        seq.append(chorus)
    seq.extend(bridges)
    return seq if seq else stanzas


# ── Slide builders ────────────────────────────────────────────────────────────

def _title_slide(doc, section_name, church, date):
    slide = doc.new_slide()
    doc.rect(slide, 0,       0,           W_IN, 0.10, C["gold"])
    doc.rect(slide, 0,       H_IN - 0.10, W_IN, 0.10, C["gold"])
    doc.rect(slide, 0,       0.10,        0.08, H_IN - 0.20, C["gold"])
    doc.rect(slide, W_IN - 0.08, 0.10,   0.08, H_IN - 0.20, C["gold"])

    doc.txt(slide, section_name, 0.4, 1.1, 9.2, 1.1,
            font_size=52, font_face=FONT_H, bold=True, align="center")
    doc.rect(slide, 3.5, 2.45, 3.0, 0.05, C["gold"])
    if date:
        doc.txt(slide, date, 0.4, 2.60, 9.2, 0.50,
                font_size=18, color=C["gold"], italic=True, align="center")
    doc.txt(slide, church, 0.4, 3.20, 9.2, 0.50,
            font_size=16, color=C["muted"], align="center")


def _overview_slide(doc, section_name, time_str, items):
    slide = doc.new_slide()
    _header(doc, slide, section_name, time_str)
    doc.txt(slide, "Programme Overview", 0.4, 0.62, 9, 0.60,
            font_size=28, font_face=FONT_H, bold=True)

    row_h = min(0.55, 4.3 / max(len(items), 1))
    for i, item in enumerate(items):
        y    = 1.35 + i * row_h
        fill = C["bgCard"] if i % 2 == 0 else C["bg"]
        doc.rect(slide, 0.4, y, 9.2, row_h - 0.04, fill)
        doc.rect(slide, 0.4, y, 0.06, row_h - 0.04, C["gold"])
        item_type = item.get("type", "participant")
        right_text = "" if item_type == "song" else item.get("participant", "")
        doc.txt(slide, item.get("title", ""), 0.55, y + 0.04, 4.5, row_h * 0.8,
                font_size=13, color=C["offWhite"])
        if right_text:
            doc.txt(slide, right_text, 5.0, y + 0.04, 4.3, row_h * 0.8,
                    font_size=12, color=C["muted"], align="right")


def _item_slide(doc, item, index, total, section_name):
    slide = doc.new_slide()

    # Resolve type
    item_type = item.get("type", "participant")

    # ── Content item: free-form text body, no participant row ─────────────────
    if item_type == "content":
        _header(doc, slide, section_name, f"{index + 1} of {total}")
        content_text = item.get("content", "")
        doc.txt(slide, item.get("title", ""), 0.4, 0.65, 9.2, 0.85,
                font_size=38, font_face=FONT_H, bold=True, color=C["goldLt"])
        doc.rect(slide, 0.4, 1.65, 4.0, 0.04, C["gold"])
        # Render content lines as separate paragraphs
        lines = content_text.split("\n") if content_text else [""]
        gs = doc._gs(fill="none", stroke="none")
        frame = __import__("odf.draw", fromlist=["Frame"]).Frame(
            stylename=gs,
            x=doc._cm(doc._i(1.0)), y=doc._cm(doc._i(1.80)),
            width=doc._cm(doc._i(8.0)), height=doc._cm(doc._i(2.50)),
        )
        from odf import draw as _draw, text as _text
        tb = _draw.TextBox()
        for line in lines:
            ps = doc._ps(align="center", fontfamily=FONT_B, fontsize=18,
                         color=C["offWhite"])
            p = _text.P(stylename=ps)
            p.addText(line)
            tb.addElement(p)
        frame.addElement(tb)
        slide.addElement(frame)
        _bottom_bar(doc, slide)
        return

    _header(doc, slide, section_name, f"{index + 1} of {total}")

    # Resolve fields from new typed schema (or legacy schema)
    if item_type == "song":
        subtitle = f"Hymn #{item['hymn_number']}" if item.get("hymn_number") else ""
        p_name   = ""
        p_role   = ""
    elif "participants" in item and not item.get("type"):
        subtitle = item.get("subtitle", "")
        parts    = item.get("participants", [])
        p_name   = parts[0].get("name", "") if parts else ""
        p_role   = parts[0].get("role", "") if parts else ""
    else:
        # Participant item
        subtitle = item.get("part", "")
        p_name   = item.get("participant", "")
        p_role   = item.get("part", "")

    doc.txt(slide, item.get("title", ""), 0.4, 0.65, 9.2, 0.85,
            font_size=38, font_face=FONT_H, bold=True)
    if subtitle:
        doc.txt(slide, subtitle, 0.4, 1.55, 9.2, 0.45,
                font_size=18, color=C["goldLt"], italic=True)

    doc.rect(slide, 0.4, 2.10, 4.0, 0.04, C["gold"])

    if p_name:
        doc.txt(slide, p_role.upper() if p_role else "", 0.4, 2.22, 2.8, 0.32,
                font_size=10, color=C["muted"], bold=True)
        doc.txt(slide, p_name, 3.3, 2.22, 6.3, 0.32,
                font_size=16, color=C["white"])

    _bottom_bar(doc, slide)


def _hymn_slides(doc, stanzas):
    sequence = _hymn_slide_sequence(stanzas)
    total    = len(sequence)

    CONTENT_TOP = 0.68
    CONTENT_BOT = 5.28
    AVAILABLE   = CONTENT_BOT - CONTENT_TOP

    for idx, stanza in enumerate(sequence):
        slide = doc.new_slide()

        label      = _stanza_label(stanza)
        is_chorus  = stanza.get("type") in ("chorus", "refrain")
        lcolor     = C["goldLt"] if is_chorus else C["gold"]

        doc.rect(slide, 3.8, 0.14, 2.4, 0.46, C["bgDark"])
        doc.rect(slide, 3.8, 0.14, 0.06, 0.46, lcolor)
        doc.txt(slide, label, 3.86, 0.14, 2.34, 0.46,
                font_size=16, color=lcolor, bold=True, align="center")

        if idx < total - 1:
            next_label = _stanza_label(sequence[idx + 1])
            doc.txt(slide, f"Next \u203a {next_label}", 7.2, 5.18, 2.6, 0.30,
                    font_size=9, color=C["muted"], align="right")

        lines = stanza["lines"]
        n     = len(lines)
        if   n <= 4: LINE_H, LINE_GAP, FONT_S = 0.80, 0.20, 26
        elif n == 5: LINE_H, LINE_GAP, FONT_S = 0.68, 0.14, 22
        elif n == 6: LINE_H, LINE_GAP, FONT_S = 0.58, 0.10, 19
        elif n == 7: LINE_H, LINE_GAP, FONT_S = 0.50, 0.08, 17
        else:        LINE_H, LINE_GAP, FONT_S = 0.44, 0.06, 15

        block_h = LINE_H * n + LINE_GAP * (n - 1)
        start_y = CONTENT_TOP + (AVAILABLE - block_h) / 2

        for i, line in enumerate(lines):
            y = start_y + i * (LINE_H + LINE_GAP)
            doc.txt(slide, line, 0.3, y, 9.4, LINE_H,
                    font_size=FONT_S, font_face=FONT_H, align="center",
                    color=C["white"], valign="middle")

        dot_w   = 0.14
        dot_gap = 0.09
        total_w = dot_w * total + dot_gap * (total - 1)
        start_x = (W_IN - total_w) / 2
        for di in range(total):
            x = start_x + di * (dot_w + dot_gap)
            is_cd = sequence[di].get("type") in ("chorus", "refrain")
            if di == idx:      dc = C["gold"]
            elif is_cd:        dc = C["goldLt"]
            else:              dc = C["muted"]
            doc.dot(slide, x, 5.35, dot_w, dc)



def _service_team_slide(doc, service_team, church):
    slide = doc.new_slide()
    _header(doc, slide, "Divine Service", church)

    doc.txt(slide, "Service Team", 0.4, 0.62, 9, 0.65,
            font_size=34, font_face=FONT_H, bold=True)

    row_h = min(0.62, 3.8 / max(len(service_team), 1))
    for i, member in enumerate(service_team):
        y    = 1.40 + i * row_h
        fill = C["bgCard"] if i % 2 == 0 else C["bg"]
        doc.rect(slide, 0.4, y, 9.2, row_h - 0.04, fill)
        doc.rect(slide, 0.4, y, 0.06, row_h - 0.04, C["gold"])
        doc.txt(slide, member.get("role", "").upper(), 0.6, y + 0.04, 3.2, row_h * 0.38,
                font_size=10, color=C["gold"], bold=True)
        doc.txt(slide, member.get("name", ""), 0.6, y + row_h * 0.42, 8.5, row_h * 0.52,
                font_size=16, color=C["offWhite"])

    _bottom_bar(doc, slide)


def _closing_slide(doc, section_name, church, next_service=None):
    slide = doc.new_slide()
    doc.rect(slide, 0,          0,           W_IN, 0.12, C["gold"])
    doc.rect(slide, 0,          H_IN - 0.12, W_IN, 0.12, C["gold"])
    doc.rect(slide, 0,          0.12, 0.08,  H_IN - 0.24, C["gold"])
    doc.rect(slide, W_IN - 0.08, 0.12, 0.08, H_IN - 0.24, C["gold"])

    doc.txt(slide, section_name, 0.4, 1.3, 9.2, 1.1,
            font_size=56, font_face=FONT_H, bold=True, align="center")
    doc.rect(slide, 3.5, 2.55, 3.0, 0.05, C["gold"])
    ending = next_service if next_service else "Ends Here"
    doc.txt(slide, ending, 0.4, 2.75, 9.2, 0.55,
            font_size=20, color=C["gold"], italic=True, align="center")
    doc.txt(slide, f"{church}  \u00b7  Sabbath Worship", 0.4, 5.0, 9.2, 0.35,
            font_size=13, color=C["muted"], align="center")


def _section_divider_slide(doc, title):
    slide = doc.new_slide()
    doc.rect(slide, 0, 0,           W_IN, 0.06, C["gold"])
    doc.rect(slide, 0, H_IN - 0.06, W_IN, 0.06, C["gold"])
    doc.txt(slide, title, 0.4, 1.8, 9.2, 1.2,
            font_size=42, font_face=FONT_H, bold=True, align="center")
    doc.rect(slide, 3.5, 3.15, 3.0, 0.05, C["gold"])


def _ds_overview_slide(doc, ds):
    all_items = [item for sub in ds.get("subsections", [])
                 for item in sub.get("items", [])]
    _overview_slide(doc, "Divine Service", ds.get("time", ""), all_items)


# ── Public entry point ────────────────────────────────────────────────────────

def generate_odp(program: dict, section: dict, output_path: str):
    """Generate an ODP for any service program.

    Args:
        program: full program dict (church, date, service_team, …)
        section: one entry from program["service_programs"]
        output_path: where to save the .odp
    """
    doc    = _Doc()
    church = program["church"]
    date   = program.get("date", "")
    name   = section.get("name", "")
    time   = section.get("time", "")
    items  = section.get("items", [])

    # Determine closing message based on next program in list
    programs = program.get("service_programs", [])
    idx      = next((i for i, sp in enumerate(programs) if sp["id"] == section["id"]), -1)
    next_sp  = programs[idx + 1] if 0 <= idx < len(programs) - 1 else None
    closing_next = f"Ends Here \u00b7 {next_sp['name']} Follows" if next_sp else None

    _title_slide(doc, name, church, date)
    _overview_slide(doc, name, time, items)

    for i, item in enumerate(items):
        _item_slide(doc, item, i, len(items), name)
        if item.get("lyrics"):
            _hymn_slides(doc, item["lyrics"])

    if program.get("service_team"):
        _service_team_slide(doc, program["service_team"], church)

    _closing_slide(doc, name, church, closing_next)

    doc.save(output_path)
    print(f"\u2705 Generated ODP: {output_path}")
