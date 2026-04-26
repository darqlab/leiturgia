import asyncio
import json
import logging
import os
import threading
import time

import websockets

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
DATA_FILE = "data/program.json"

_BACKOFF = [2, 4, 8, 16, 30]
_HEARTBEAT_INTERVAL = 30
_SYNC_DEBOUNCE = 0.8  # seconds


class CloudAgent:
    """WebSocket client that maintains the Pi-to-cloud connection."""

    def __init__(self):
        self._status = "not_linked"   # not_linked | connecting | connected | reconnecting
        self._loop = None
        self._ws = None
        self._on_program_update = None  # callback(data) when cloud pushes sync:program
        self._cloud_version = 0         # last known cloud program version

        # Outbound sync state — written by Flask thread, read by asyncio loop.
        # Plain attribute assignment is GIL-safe; no asyncio.run_coroutine_threadsafe needed.
        self._notify_data = None   # latest data queued by notify_program_saved()
        self._notify_time = 0.0    # monotonic timestamp of last notify
        self._force_data = None    # set by force_push_program(); sent on next poll tick

        # Set True by _apply_program (asyncio thread); cleared by app.py pump (eventlet thread).
        self._pending_ui_notify = False

        # Restart signal — set() from Flask thread, checked by heartbeat task.
        self._restart_event = threading.Event()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def status(self):
        return self._status

    @property
    def linked(self):
        cfg = self._load_config()
        return bool(cfg.get("cloud_enabled") and cfg.get("cloud_url") and cfg.get("cloud_token"))

    def set_program_update_callback(self, cb):
        self._on_program_update = cb

    def notify_program_saved(self, data):
        """Called by Flask thread after saving program.json; debounced 800ms before push."""
        self._notify_data = data
        self._notify_time = time.monotonic()

    def force_push_program(self, data):
        """Send sync:program immediately, bypassing debounce — used by manual sync."""
        self._force_data = data

    def start(self):
        """Start the agent in a real OS thread (asyncio loop inside)."""
        cfg = self._load_config()
        if not cfg.get("cloud_enabled"):
            return
        # Use the real (unpatched) Thread so asyncio runs in an actual OS thread,
        # not an eventlet green thread.
        try:
            from eventlet.patcher import original as _orig
            _Thread = _orig("threading").Thread
        except ImportError:
            import threading as _threading
            _Thread = _threading.Thread

        t = _Thread(target=self._run_loop, daemon=True)
        t.start()

    def restart(self):
        """Reload config and reconnect — called after successful /api/cloud/link."""
        self._restart_event.set()
        self.start()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_config(self):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        finally:
            self._loop.close()
            self._loop = None
            self._status = "not_linked"

    async def _connect_loop(self):
        backoff_idx = 0
        while True:
            cfg = self._load_config()
            if not cfg.get("cloud_enabled"):
                break

            cloud_url = cfg.get("cloud_url", "").strip().rstrip("/")
            cloud_token = cfg.get("cloud_token", "").strip()
            if not cloud_url or not cloud_token:
                break

            ws_url = f"wss://{cloud_url}/ws/device"
            self._status = "connecting"

            try:
                async with websockets.connect(
                    ws_url,
                    additional_headers={"Authorization": f"Bearer {cloud_token}"},
                    ping_interval=None,  # we manage our own heartbeat
                ) as ws:
                    self._ws = ws
                    self._status = "connected"
                    backoff_idx = 0
                    await self._session(ws)
            except Exception as exc:
                logger.warning("Cloud WebSocket disconnected: %s", exc)
            finally:
                self._ws = None

            if self._restart_event.is_set():
                self._restart_event.clear()
                backoff_idx = 0
                await asyncio.sleep(0.5)
                continue

            self._status = "reconnecting"
            delay = _BACKOFF[min(backoff_idx, len(_BACKOFF) - 1)]
            backoff_idx = min(backoff_idx + 1, len(_BACKOFF) - 1)
            await asyncio.sleep(delay)

        self._status = "not_linked"

    async def _session(self, ws):
        heartbeat = asyncio.create_task(self._heartbeat(ws))
        poller = asyncio.create_task(self._sync_poller(ws))
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._handle_event(msg)
        finally:
            heartbeat.cancel()
            poller.cancel()
            for t in (heartbeat, poller):
                try:
                    await t
                except asyncio.CancelledError:
                    pass

    async def _heartbeat(self, ws):
        elapsed = 0.0
        while True:
            await asyncio.sleep(1.0)
            elapsed += 1.0
            if self._restart_event.is_set():
                await ws.close()
                return
            if elapsed >= _HEARTBEAT_INTERVAL:
                elapsed = 0.0
                try:
                    await ws.send(json.dumps({"event": "device:status"}))
                except Exception:
                    break

    async def _sync_poller(self, ws):
        """Poll for outbound sync requests every 100ms; implements debounce for notify."""
        while True:
            await asyncio.sleep(0.1)

            # Force push — send immediately
            if self._force_data is not None:
                data = self._force_data
                self._force_data = None
                self._notify_data = None  # discard any pending notify for same data
                await self._send_payload(ws, data)
                continue

            # Debounced notify push
            if self._notify_data is not None:
                if time.monotonic() - self._notify_time >= _SYNC_DEBOUNCE:
                    data = self._notify_data
                    self._notify_data = None
                    await self._send_payload(ws, data)

    async def _send_payload(self, ws, data):
        try:
            await ws.send(json.dumps({
                "event": "sync:program",
                "data": data,
                "version": self._cloud_version,
            }))
        except Exception as exc:
            logger.warning("Failed to send sync:program: %s", exc)

    async def _handle_event(self, msg):
        event = msg.get("event")
        data = msg.get("data", {})
        if event == "sync:program":
            await self._apply_program(data, msg.get("version", 0))
        elif event == "sync:media:add":
            asyncio.get_event_loop().run_in_executor(None, self._download_media, data)
        elif event == "sync:media:delete":
            self._delete_media(data)

    async def _apply_program(self, data, version: int = 0):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=2)
            self._cloud_version = version
            logger.info("sync:program applied from cloud (version %s)", version)
        except Exception as exc:
            logger.error("Failed to apply sync:program: %s", exc)
            return
        # Signal the app.py eventlet background pump instead of calling socketio.emit
        # directly — calling it from this asyncio OS thread causes greenlet cross-thread crash.
        self._pending_ui_notify = True

    # ── Media helpers (run in executor) ──────────────────────────────────────

    def _download_media(self, data):
        import urllib.request
        url = data.get("url", "")
        filename = os.path.basename(data.get("filename", ""))
        if not url or not filename:
            return
        dest_dir = os.path.join("media", "images")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, filename)
        try:
            urllib.request.urlretrieve(url, dest)
            logger.info("Downloaded media: %s", filename)
        except Exception as exc:
            logger.error("Failed to download %s: %s", filename, exc)

    def _delete_media(self, data):
        filename = os.path.basename(data.get("filename", ""))
        if not filename:
            return
        for subdir in ("images", "videos"):
            path = os.path.join("media", subdir, filename)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info("Deleted media: %s", filename)
                except Exception as exc:
                    logger.error("Failed to delete %s: %s", filename, exc)
                break


# Singleton — imported and used by app.py
agent = CloudAgent()
