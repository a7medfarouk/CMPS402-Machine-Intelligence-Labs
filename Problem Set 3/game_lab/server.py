"""Serve the game interface on loopback and dispatch to the local runner."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import webbrowser

from .worker import call


WEB = Path(__file__).with_name("web")
FILES = {
    "/": ("index.html", "text/html"),
    "/style.css": ("style.css", "text/css"),
    "/play.js": ("play.js", "text/javascript"),
    "/instructions": ("../../Instructions.html", "text/html"),
    "/instructions.pdf": ("../../Instructions.pdf", "application/pdf"),
}


class Handler(BaseHTTPRequestHandler):
    def deliver(self, code, payload, mime):
        self.send_response(code)
        self.send_header("Content-Type", mime if mime == "application/pdf" else f"{mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path not in FILES:
            self.send_error(404)
            return
        filename, mime = FILES[self.path]
        self.deliver(200, (WEB / filename).read_bytes(), mime)

    def do_POST(self):
        host = f"127.0.0.1:{self.server.server_port}"
        if (self.path != "/api/game" or self.headers.get("Host") != host
                or self.headers.get("Origin") not in (None, f"http://{host}")
                or self.headers.get_content_type() != "application/json"):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError("Invalid request size.")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict) or request.get("action") not in ("inspect", "reply", "compare"):
                raise ValueError("Unknown game request.")
            response = call(request)
        except (ValueError, UnicodeError) as error:
            response = {"status": "INVALID REQUEST", "detail": str(error)}
        self.deliver(200, json.dumps(response).encode("utf-8"), "application/json")

    def log_message(self, format, *args):
        pass


def serve(port=0, open_browser=True):
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        address = f"http://127.0.0.1:{server.server_port}"
        print(f"Games are open at {address}. Press Ctrl+C to stop.", flush=True)
        if open_browser:
            webbrowser.open(address)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
