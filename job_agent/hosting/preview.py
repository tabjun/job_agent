"""Serve an exported public bundle with its real stateless API for local QA."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from job_agent.hosting.handler import handler


class PreviewHandler(SimpleHTTPRequestHandler):
    respond = handler.respond
    do_POST = handler.do_POST

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.respond(404, {"error": "Not found"})
        else:
            super().do_GET()


def server(bundle, port=8790):
    public = Path(bundle).resolve() / "public"
    if not (public / "index.html").is_file():
        raise ValueError("A built public bundle is required")
    return ThreadingHTTPServer(
        ("127.0.0.1", port), partial(PreviewHandler, directory=str(public))
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview the exported public website")
    parser.add_argument("bundle")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args(argv)
    with server(args.bundle, args.port) as app:
        print(f"Public build preview: http://127.0.0.1:{app.server_port}", flush=True)
        app.serve_forever()


if __name__ == "__main__":
    main()
