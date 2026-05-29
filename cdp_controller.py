import asyncio
import json
import sys

import websockets

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    import requests

    def _http_get_json(url: str) -> list[dict]:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()

except ImportError:
    import urllib.request

    def _http_get_json(url: str) -> list[dict]:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())


class CDPController:
    def __init__(self, port: int = 9222):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self._targets: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def discover_video_targets(self) -> list[dict]:
        """Find all page-type targets that contain a <video> element."""
        all_targets = self._list_targets()
        video_targets = []
        for t in all_targets:
            if t.get("type") in ("page", "webview"):
                ws_url = t.get("webSocketDebuggerUrl", "")
                if ws_url and self._has_video(ws_url):
                    video_targets.append(t)
        self._targets = video_targets
        return video_targets

    def set_speed(self, speed: float) -> int:
        """Set playbackRate on all videos in all known targets. Returns count."""
        if not self._targets:
            self.discover_video_targets()
        total = 0
        stale = []
        for t in self._targets:
            ws_url = t.get("webSocketDebuggerUrl", "")
            if not ws_url:
                continue
            try:
                count = self._set_speed_on_target(ws_url, speed)
                if count >= 0:
                    total += count
                else:
                    stale.append(t)
            except Exception:
                stale.append(t)
        for t in stale:
            self._targets.remove(t)
        # Retry discovery if all targets went stale
        if not self._targets and total == 0:
            self.discover_video_targets()
            for t in self._targets:
                ws_url = t.get("webSocketDebuggerUrl", "")
                if ws_url:
                    try:
                        total += self._set_speed_on_target(ws_url, speed)
                    except Exception:
                        pass
        return total

    def get_current_speed(self) -> float | None:
        """Read playbackRate from the first video in the first target."""
        if not self._targets:
            self.discover_video_targets()
        for t in self._targets:
            ws_url = t.get("webSocketDebuggerUrl", "")
            if not ws_url:
                continue
            try:
                val = self._execute_js(
                    ws_url,
                    "(function(){var v=document.querySelector('video');return v?v.playbackRate:null;})()",
                )
                if val is not None:
                    return float(val)
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # Internal: HTTP target discovery
    # ------------------------------------------------------------------

    def _list_targets(self) -> list[dict]:
        return _http_get_json(f"{self.base_url}/json")

    # ------------------------------------------------------------------
    # Internal: WebSocket JS execution
    # ------------------------------------------------------------------

    def _has_video(self, ws_url: str) -> bool:
        result = self._execute_js(ws_url, "!!document.querySelector('video')")
        return result is True

    def _set_speed_on_target(self, ws_url: str, speed: float) -> int:
        expr = (
            f"(function(){{"
            f"var vs=document.querySelectorAll('video');"
            f"vs.forEach(function(v){{v.playbackRate={speed}}});"
            f"return vs.length;"
            f"}})()"
        )
        result = self._execute_js(ws_url, expr)
        return result if isinstance(result, (int, float)) else -1

    def _execute_js(self, ws_url: str, expression: str):
        """Execute JavaScript in a target via CDP Runtime.evaluate."""
        return asyncio.run(self._async_execute_js(ws_url, expression))

    async def _async_execute_js(self, ws_url: str, expression: str):
        async with websockets.connect(
            ws_url, max_size=2**23, open_timeout=5, close_timeout=3
        ) as ws:
            cmd = json.dumps(
                {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expression,
                        "returnByValue": True,
                        "awaitPromise": False,
                    },
                }
            )
            await ws.send(cmd)
            while True:
                resp_text = await asyncio.wait_for(ws.recv(), timeout=5)
                resp = json.loads(resp_text)
                if resp.get("id") == 1:
                    result = resp.get("result", {})
                    if "exceptionDetails" in result:
                        return None
                    return result.get("result", {}).get("value")
