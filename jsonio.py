import json
import os
import tempfile


def atomic_write_json(path, data, *, indent=2):
    """Write JSON to `path` atomically: temp file in the same dir, fsync, then replace.

    Guarantees a concurrent reader sees either the old complete file or the new
    complete file — never a partially-written one.
    """
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
