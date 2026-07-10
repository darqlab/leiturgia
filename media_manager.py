"""
media_manager.py — Enumerate media files in media/images/ and media/videos/,
and compute storage-budget usage against them.

Public: list_media(), usage(), referenced_media(), usb_targets(),
resolve_usb_target(), videos_dir(), videos_unavailable(), resolve_export_target().
"""

import json
import logging
import os
import re
import shutil
from urllib.parse import quote as _quote, unquote as _unquote

logger = logging.getLogger('leiturgia.media')

try:
    from mutagen.mp4 import MP4 as _MP4
    _MUTAGEN_OK = True
except ImportError:
    _MUTAGEN_OK = False

MEDIA_ROOT   = "media"
IMAGES_DIR   = os.path.join(MEDIA_ROOT, "images")
VIDEOS_DIR   = os.path.join(MEDIA_ROOT, "videos")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".avi"}

CONFIG_FILE = "config.json"
DATA_FILE   = os.path.join("data", "program.json")


def videos_dir() -> str:
    """Resolve the physical video storage directory (TDD §5.6): `media_video_dir`
    from config if set, else the built-in `media/videos` path. Every video-path
    consumer (list/scan, usage, upload, yt-dlp, serve_media, export) must call
    this rather than hard-coding the videos directory."""
    cfg = _load_config()
    configured = (cfg.get('media_video_dir') or '').strip()
    return configured if configured else VIDEOS_DIR


def videos_unavailable() -> bool:
    """True only when an *externally configured* video dir (not the built-in
    default) is missing/unmounted right now — e.g. a USB drive got unplugged.
    The built-in dir simply not existing yet (fresh install, nothing uploaded)
    is normal and is NOT reported as unavailable. See TDD §5.6 'Drive-disconnected
    degradation'."""
    vdir = videos_dir()
    return vdir != VIDEOS_DIR and not os.path.isdir(vdir)


def _location_label(vdir: str) -> str:
    """Human label for where videos currently live — 'Internal' for the
    built-in dir, else the matching USB target's label, else the basename of
    the configured dir. Feeds `usage()['location_label']` (TDD §5.2)."""
    if vdir == VIDEOS_DIR:
        return "Internal"
    try:
        real = os.path.realpath(vdir)
    except (OSError, ValueError):
        real = vdir
    for entry in usb_targets():
        try:
            entry_real = os.path.realpath(entry["path"])
        except (OSError, ValueError):
            continue
        if real == entry_real or real.startswith(entry_real.rstrip('/') + '/'):
            return entry["label"]
    return os.path.basename(vdir.rstrip('/')) or vdir


def list_media() -> dict:
    """Return { "images": [...], "videos": [...], "videos_unavailable": bool }
    with filename, URL, and metadata. When the configured video dir is
    disconnected, "videos" comes back empty and "videos_unavailable" is True
    instead of raising (TDD §5.6)."""
    vdir = videos_dir()
    unavailable = videos_unavailable()
    return {
        "images":             _scan(IMAGES_DIR, IMAGE_EXTS, "images"),
        "videos":             [] if unavailable else _scan(vdir, VIDEO_EXTS, "videos"),
        "videos_unavailable": unavailable,
    }


def _fmt_size(n: int) -> str:
    for unit in ("KB", "MB", "GB"):
        n /= 1024
        if n < 1024:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} GB"


def _fmt_duration(s: float) -> str:
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def _file_meta(path: str) -> dict:
    size = os.path.getsize(path)
    duration = None
    duration_label = None
    if _MUTAGEN_OK and path.lower().endswith((".mp4", ".m4v")):
        try:
            duration = _MP4(path).info.length
            duration_label = _fmt_duration(duration)
        except Exception:
            pass
    return {
        "size":           size,
        "size_label":     _fmt_size(size),
        "duration":       duration,
        "duration_label": duration_label,
    }


def _scan(directory: str, allowed_exts: set, subdir: str) -> list:
    if not os.path.isdir(directory):
        return []
    files = []
    for name in sorted(os.listdir(directory)):
        ext = os.path.splitext(name)[1].lower()
        if ext in allowed_exts:
            full_path = os.path.join(directory, name)
            entry = {
                "name": name,
                "url":  f"/media/{subdir}/{_quote(name, safe='')}",
            }
            entry.update(_file_meta(full_path))
            files.append(entry)
    return files


def _load_config() -> dict:
    """Ad-hoc config.json read, same convention app.py uses elsewhere (no caching,
    changes apply without restart). Missing file/keys degrade to defaults."""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _dir_used_bytes(directory: str) -> int:
    if not os.path.isdir(directory):
        return 0
    return sum(
        e.stat().st_size for e in os.scandir(directory) if e.is_file()
    )


def usage() -> dict:
    """Compute video/image storage usage against the configured budgets and the
    hard filesystem reserve. See development/tdd/modules/media-storage-budget.md
    §5.2 for the full spec."""
    cfg = _load_config()

    video_budget_bytes = int(float(cfg.get('media_video_budget_gb', 2)) * 1024 ** 3)
    image_budget_bytes = int(float(cfg.get('media_image_budget_gb', 1)) * 1024 ** 3)
    reserve_bytes       = int(float(cfg.get('media_disk_reserve_gb', 1)) * 1024 ** 3)
    warn_percent        = float(cfg.get('media_warn_percent', 80))

    vdir = videos_dir()
    unavailable = videos_unavailable()
    used_bytes = 0 if unavailable else _dir_used_bytes(vdir)

    # shutil.disk_usage needs an existing path — fall back to MEDIA_ROOT, then cwd,
    # if the resolved video dir doesn't exist yet (fresh install, no media
    # uploaded, or — for an external dir — the drive is currently unplugged).
    du_path = vdir if os.path.isdir(vdir) else (
        MEDIA_ROOT if os.path.isdir(MEDIA_ROOT) else "."
    )
    fs_free_bytes = shutil.disk_usage(du_path).free

    fs_room = fs_free_bytes - reserve_bytes
    if video_budget_bytes == 0:
        remaining_bytes = fs_room
        # Unlimited budget: percent/warn track the fs-reserve term instead — the
        # "effective budget" is whatever's already used plus the room still free
        # within the reserve floor.
        percent = _safe_percent(used_bytes, used_bytes + fs_room)
        # No budget term exists to compare against — warn is driven by percent
        # (against the reserve-derived "effective budget") alone.
        fs_reserve_binding = False
    else:
        remaining_bytes = min(video_budget_bytes - used_bytes, fs_room)
        percent = _safe_percent(used_bytes, video_budget_bytes)
        # The fs-reserve term is "binding" when it's the tighter of the two candidates.
        fs_reserve_binding = fs_room < (video_budget_bytes - used_bytes)

    full = remaining_bytes <= 0
    warn = full or percent >= warn_percent or fs_reserve_binding

    images_used_bytes = _dir_used_bytes(IMAGES_DIR)
    if image_budget_bytes == 0:
        images_remaining = fs_room
    else:
        images_remaining = min(image_budget_bytes - images_used_bytes, fs_room)
    images = {
        "used_bytes":    images_used_bytes,
        "budget_bytes":  image_budget_bytes,
        "full":          images_remaining <= 0,
        "used_label":    _fmt_size(images_used_bytes),
        "budget_label":  "Unlimited" if image_budget_bytes == 0 else _fmt_size(image_budget_bytes),
    }

    return {
        "used_bytes":      used_bytes,
        "budget_bytes":    video_budget_bytes,
        "remaining_bytes": remaining_bytes,
        "percent":         percent,
        "fs_free_bytes":   fs_free_bytes,
        "reserve_bytes":   reserve_bytes,
        "warn":            warn,
        "full":            full,
        "used_label":      _fmt_size(used_bytes),
        "budget_label":    "Unlimited" if video_budget_bytes == 0 else _fmt_size(video_budget_bytes),
        "images":          images,
        "location_label":       _location_label(vdir),
        "videos_unavailable":   unavailable,
    }


def _safe_percent(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(part / whole * 100, 1)


def referenced_media() -> dict:
    """Scan data/program.json for items whose url points at a media/{videos,images}
    file, mapping basename -> [{program, item}, ...]. Read-only informational scan —
    a plain json.load is fine here (no migration/retry logic needed).
    See development/tdd/modules/media-storage-budget.md §5.3a."""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        logger.warning("referenced_media: could not read %s", DATA_FILE, exc_info=True)
        return {}

    refs: dict = {}
    for sp in data.get("service_programs", []):
        program_label = sp.get("name", sp.get("id", ""))
        for item in sp.get("items", []):
            t = item.get('type', 'participant')
            is_video = (t == 'video') or (t == 'media' and item.get('media_type') == 'video')
            is_image = (t == 'image') or (t == 'media' and item.get('media_type') != 'video')
            if not (is_video or is_image):
                continue
            url = item.get('url', '')
            if not url:
                continue
            basename = _unquote(os.path.basename(url))
            item_label = item.get("title", item.get("part", ""))
            refs.setdefault(basename, []).append({
                "program": program_label,
                "item":    item_label,
            })
    return refs


# ── USB export targets (TDD §5.4 / §5.7 "USB export") ─────────────────────

USB_MOUNT_ROOTS = ("/media/", "/mnt/", "/run/media/")

_MOUNT_OCTAL_RE = re.compile(r'\\([0-7]{3})')


def _unescape_mount_field(s: str) -> str:
    """/proc/mounts octal-escapes spaces/tabs/newlines/backslashes in paths
    (e.g. a space becomes \\040) — undo that so mount points compare/display
    correctly."""
    return _MOUNT_OCTAL_RE.sub(lambda m: chr(int(m.group(1), 8)), s)


def usb_targets() -> list:
    """List writable removable-looking mounts for USB export, per TDD §5.4:
    parse /proc/mounts, keep mount points under the allowlisted roots, require
    os.access(W_OK). Returns [{path, label, free_bytes, free_label, fs_type,
    fat32}, ...]. Linux-only (/proc/mounts); returns [] elsewhere."""
    targets = []
    try:
        with open('/proc/mounts') as f:
            lines = f.readlines()
    except OSError:
        return targets

    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        mount_point = _unescape_mount_field(parts[1])
        fs_type     = parts[2]
        if not any(mount_point.startswith(root) for root in USB_MOUNT_ROOTS):
            continue
        if not os.path.isdir(mount_point) or not os.access(mount_point, os.W_OK):
            continue
        try:
            free_bytes = shutil.disk_usage(mount_point).free
        except OSError:
            continue
        label = os.path.basename(mount_point.rstrip('/')) or mount_point
        targets.append({
            "path":       mount_point,
            "label":      label,
            "free_bytes": free_bytes,
            "free_label": _fmt_size(free_bytes),
            "fs_type":    fs_type,
            "fat32":      fs_type.lower() in ("vfat", "fat32", "fat", "msdos"),
        })
    return targets


def resolve_usb_target(target: str) -> str:
    """Validate a client-supplied export target against a *fresh* rescan of
    /proc/mounts (never trust a stale client-supplied path) — the target must
    resolve (realpath) to a mount point currently listed by usb_targets().
    Returns the canonical mount path, or None if invalid/not currently
    mounted/writable. See TDD §5.4 "Export security"."""
    if not target:
        return None
    try:
        real = os.path.realpath(target)
    except (OSError, ValueError):
        return None
    for entry in usb_targets():
        if os.path.realpath(entry["path"]) == real:
            return entry["path"]
    return None


def resolve_export_target(target: str) -> str:
    """Broader sibling of resolve_usb_target(): validates a client-supplied
    path against a *fresh* /proc/mounts rescan, accepting the path if its
    realpath sits AT or BELOW a currently-mounted, writable, allowlisted root
    — not just equal to it. Used by the configurable video storage location
    (TDD §5.6), whose target is typically `<mount>/leiturgia-videos`, a
    subdirectory of the mount root rather than the root itself. Returns the
    resolved absolute path, or None if invalid/not currently mounted/writable.
    See TDD §5.6 "Validation (server, on POST)"."""
    if not target or not os.path.isabs(target):
        return None
    try:
        real = os.path.realpath(target)
    except (OSError, ValueError):
        return None
    for entry in usb_targets():
        try:
            entry_real = os.path.realpath(entry["path"])
        except (OSError, ValueError):
            continue
        if real == entry_real or real.startswith(entry_real.rstrip('/') + '/'):
            return real
    return None
