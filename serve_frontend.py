"""SKPL Agent Frontend Server with API Proxy.
Serves the built frontend and proxies API requests to the backend.

Usage: python serve_frontend.py [--port PORT] [--dist DIR] [--backend URL]
"""
import http.server
import os
import sys
import argparse
import urllib.request
import urllib.error

# API paths that should be proxied to backend.
# NOTE: /chat/ is NOT in this list because /chat/:agentId/:sessionId is an SPA
# route (ChatPage). The only API call to /chat/ is a POST, which is handled
# by the do_POST method below.
API_PREFIXES = [
    "/agent/", "/sessions/", "/credential/", "/knowledge_bases/",
    "/contexts/", "/schedule/", "/model/", "/workspace/", "/api/", "/tts-model/"
]


class SPAHandler(http.server.SimpleHTTPRequestHandler):
    """SPA handler with API proxy support."""
    
    backend_url = "http://localhost:8000"
    dist_dir = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.dist_dir, **kwargs)

    def _is_api(self):
        return any(self.path.startswith(p) for p in API_PREFIXES)

    def _proxy_to_backend(self, method):
        try:
            url = self.backend_url + self.path
            body = None
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                body = self.rfile.read(content_length)

            req = urllib.request.Request(url, data=body, method=method)
            for header in ["Authorization", "Content-Type", "X-User-ID"]:
                if header in self.headers:
                    req.add_header(header, self.headers[header])

            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for key, val in resp.getheaders():
                    if key.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")

    def do_GET(self):
        if self._is_api():
            return self._proxy_to_backend("GET")
        # SPA fallback: serve index.html for non-file paths
        file_path = os.path.join(self.dist_dir, self.path.lstrip("/"))
        if not os.path.isfile(file_path) and not self.path.startswith("/assets/"):
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        # /chat/ is the chat trigger API — always proxy POST to backend
        if self._is_api() or self.path.rstrip("/") == "/chat":
            return self._proxy_to_backend("POST")
        self.send_error(404, "Not Found")

    def do_PATCH(self):
        if self._is_api():
            return self._proxy_to_backend("PATCH")
        self.send_error(404, "Not Found")

    def do_PUT(self):
        if self._is_api():
            return self._proxy_to_backend("PUT")
        self.send_error(404, "Not Found")

    def do_DELETE(self):
        if self._is_api():
            return self._proxy_to_backend("DELETE")
        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        pass  # Suppress request logs


def main():
    parser = argparse.ArgumentParser(description="SKPL Agent Frontend Server")
    parser.add_argument("--port", type=int, default=4173, help="Frontend port (default: 4173)")
    parser.add_argument("--dist", default="frontend/dist", help="Build output directory")
    parser.add_argument("--backend", default="http://localhost:8000", help="Backend URL")
    args = parser.parse_args()

    # Resolve dist directory relative to project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(project_root, args.dist)
    if not os.path.isdir(dist_dir):
        print(f"[ERROR] Build directory not found: {dist_dir}")
        print("Run 'cd frontend && npx vite build' first.")
        sys.exit(1)

    SPAHandler.dist_dir = dist_dir
    SPAHandler.backend_url = args.backend

    server = http.server.HTTPServer(("0.0.0.0", args.port), SPAHandler)
    print(f"[SKPL Frontend] http://localhost:{args.port}")
    print(f"[SKPL Frontend] API proxy -> {args.backend}")
    print(f"[SKPL Frontend] Serving: {dist_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SKPL Frontend] Stopped.")


if __name__ == "__main__":
    main()