"""One-use loopback handoff to the Resume Filler Firefox extension."""

import json
import secrets
import shutil
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


def open_firefox(url: str) -> None:
    executable = shutil.which("firefox")
    if executable is None:
        raise RuntimeError("Firefox was not found. Install Firefox and load the Resume Filler extension.")
    # Firefox forwards this URL to the running instance and its existing profile.
    subprocess.Popen([executable, "--new-tab", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def search_firefox(queries: list[dict[str, object]], timeout: float = 300) -> list[dict[str, object]]:
    token_path = "/assoc/" + secrets.token_urlsafe(32)
    response: dict[str, object] | None = None
    claimed = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            # Never write the one-use capability URL into HTTP logs.
            pass

        def reply(self, status: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def authorized(self) -> bool:
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self.reply(403, b'{"error":"Invalid host"}')
                return False
            if self.path not in {token_path, token_path + "/job", token_path + "/result"}:
                self.reply(404, b'{"error":"Unknown handoff"}')
                return False
            return True

        def do_GET(self) -> None:
            nonlocal claimed
            if not self.authorized():
                return
            if self.path == token_path:
                self.reply(200, (
                    '<!doctype html><html lang="en"><meta charset="utf-8">'
                    '<title>Resume Filler — Firefox association search</title>'
                    '<h1>LinkedIn search in Firefox</h1>'
                    '<p id="assoc-status">Waiting for the Resume Filler extension. '
                    'If this does not change, load or reload dist/manifest.json in '
                    'about:debugging#/runtime/this-firefox, then reload this page.</p>'
                    '<p>This search uses your existing Firefox LinkedIn session. '
                    'Results return to the assoc terminal. No password or cookies are copied.</p></html>'
                ).encode(), "text/html; charset=utf-8")
            elif self.path == token_path + "/job":
                if claimed:
                    self.reply(409, b'{"error":"Search already claimed; run assoc again"}')
                    return
                claimed = True
                self.reply(200, json.dumps({"queries": queries}).encode())
            else:
                self.reply(405, b'{"error":"Use POST"}')

        def do_POST(self) -> None:
            nonlocal response
            if not self.authorized():
                return
            if self.path != token_path + "/result" or not claimed:
                self.reply(409, b'{"error":"No claimed search"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1048576 or self.headers.get_content_type() != "application/json":
                    raise ValueError("Invalid result size or content type")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Invalid result")
                if "error" in payload:
                    if not isinstance(payload["error"], str) or not payload["error"].strip():
                        raise ValueError("Invalid error")
                else:
                    rows = payload.get("results")
                    if not isinstance(rows, list):
                        raise ValueError("Invalid profile list")
                    for row in rows:
                        if not isinstance(row, dict) or not all(
                            isinstance(row.get(key), str) for key in ("name", "url", "snippet")
                        ) or not isinstance(row.get("direct"), bool):
                            raise ValueError("Invalid profile")
                        url = urlparse(row["url"])
                        if url.scheme != "https" or url.netloc != "www.linkedin.com" or not url.path.startswith("/in/"):
                            raise ValueError("Invalid LinkedIn profile URL")
            except (ValueError, UnicodeError):
                self.reply(400, b'{"error":"Invalid search result payload"}')
                return
            self.reply(200, b'{"ok":true}')
            response = payload

    class HandoffServer(HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(5)
            return connection, address

    with HandoffServer(("127.0.0.1", 0), Handler) as server:
        server.timeout = 0.5
        print("Opening a tab in your existing Firefox. Keep the Resume Filler extension enabled.")
        print("If the handoff page stays waiting, reload dist/manifest.json in about:debugging.")
        print("Waiting for LinkedIn search results (up to five minutes); Ctrl+C cancels.")
        open_firefox(f"http://127.0.0.1:{server.server_port}{token_path}")
        deadline = time.monotonic() + timeout
        while response is None and time.monotonic() < deadline:
            server.handle_request()
    if response is None:
        raise RuntimeError(
            "Firefox did not return search results. Load/reload dist/manifest.json in "
            "about:debugging#/runtime/this-firefox, ensure LinkedIn is signed in, and run assoc again."
        )
    if "error" in response:
        raise RuntimeError(f"Firefox LinkedIn search failed: {response['error']}")
    return response["results"]
