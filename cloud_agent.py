import asyncio
import json
import logging
import os

import websockets

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
DATA_FILE = "data/program.json"

_BACKOFF = [2, 4, 8, 16, 30]
_HEARTBEAT_INTERVAL = 30


class CloudAgent:
    """WebSocket client that maintains the Pi-to-cloud connection."""

    def __init__(self):
        self._status = "not_linked"   # not_linked | connecting | connected | reconnecting
        self._loop = None
        self._ws = None
        self._pending_sync = None     # asyncio.Task for debounced program sync
        self._on_program_update = None  # callback(data) when cloud pushes sync:program

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
        """App calls this after saving program.json locally (debounced 800ms)."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._schedule_sync(data), self._loop)

    def force_push_program(self, data):
        """Send sync:program immediately, bypassing the debounce — used by manual sync."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._send_program(data), self._loop)
        else:
            logger.warning("force_push_program: agent not running, sync skipped")

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
            import threading
            _Thread = threading.Thread

        t = _Thread(target=self._run_loop, daemon=True)
        t.start()

    def restart(self):
        """Reload config and reconnect — called after successful /api/cloud/link."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._stop_ws(), self._loop)
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

    async def _stop_ws(self):
        if self._ws:
            await self._ws.close()

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

            self._status = "reconnecting"
            delay = _BACKOFF[min(backoff_idx, len(_BACKOFF) - 1)]
            backoff_idx = min(backoff_idx + 1, len(_BACKOFF) - 1)
            await asyncio.sleep(delay)

        self._status = "not_linked"

    async def _session(self, ws):
        heartbeat = asyncio.create_task(self._heartbeat(ws))
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._handle_event(msg)
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass

    async def _heartbeat(self, ws):
        while True:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            try:
                await ws.send(json.dumps({"event": "device:status"}))
            except Exception:
                break

    async def _handle_event(self, msg):
        event = msg.get("event")
        data = msg.get("data", {})
        if event == "sync:program":
            await self._apply_program(data)
        elif event == "sync:media:add":
            asyncio.get_event_loop().run_in_executor(None, self._download_media, data)
        elif event == "sync:media:delete":
            self._delete_media(data)

    async def _apply_program(self, data):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=2)
            if self._on_program_update:
                self._on_program_update(data)
            logger.info("sync:program applied from cloud")
        except Exception as exc:
            logger.error("Failed to apply sync:program: %s", exc)

    # ── Outbound sync ────────────────────────────────────────────────────────

    async def _send_program(self, data):
        if self._ws:
            try:
                await self._ws.send(json.dumps({"event": "sync:program", "data": data}))
            except Exception as exc:
                logger.warning("Failed to force-send sync:program: %s", exc)
        else:
            logger.warning("force_push_program: no WebSocket connection")

    # ── Debounced outbound sync ───────────────────────────────────────────────

    async def _schedule_sync(self, data):
        if self._pending_sync and not self._pending_sync.done():
            self._pending_sync.cancel()
        self._pending_sync = asyncio.create_task(self._delayed_sync(data))

    async def _delayed_sync(self, data):
        await asyncio.sleep(0.8)
        if self._ws:
            try:
                await self._ws.send(json.dumps({"event": "sync:program", "data": data}))
            except Exception as exc:
                logger.warning("Failed to send sync:program: %s", exc)

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
