"""
media_manager.py — Enumerate media files in media/images/ and media/videos/.

Only list_media() is public.
"""

import os

MEDIA_ROOT   = "media"
IMAGES_DIR   = os.path.join(MEDIA_ROOT, "images")
VIDEOS_DIR   = os.path.join(MEDIA_ROOT, "videos")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".avi"}


def list_media() -> dict:
    """Return { "images": [...], "videos": [...] } with filename and URL path."""
    return {
        "images": _scan(IMAGES_DIR, IMAGE_EXTS, "images"),
        "videos": _scan(VIDEOS_DIR, VIDEO_EXTS, "videos"),
    }


def _scan(directory: str, allowed_exts: set, subdir: str) -> list:
    if not os.path.isdir(directory):
        return []
    files = []
    for name in sorted(os.listdir(directory)):
        ext = os.path.splitext(name)[1].lower()
        if ext in allowed_exts:
            files.append({
                "name": name,
                "url":  f"/media/{subdir}/{name}",
            })
    return files
