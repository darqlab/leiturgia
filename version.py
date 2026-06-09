import os
import subprocess

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_cached_version = None


def get_version():
    global _cached_version
    if _cached_version is None:
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always", "--dirty"],
                cwd=_BASE_DIR,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                _cached_version = result.stdout.strip()
            else:
                _cached_version = "unknown"
        except Exception:
            _cached_version = "unknown"
    return _cached_version
