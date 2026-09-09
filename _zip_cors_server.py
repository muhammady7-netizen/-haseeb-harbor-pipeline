"""Serve Downloads QC zips with CORS so the trainer page can fetch them."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class CorsHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args), flush=True)


def main() -> None:
    ap = argparse.ArgumentHandler() if False else argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--dir", default=str(Path.home() / "Downloads"))
    args = ap.parse_args()
    root = Path(args.dir).resolve()
    handler = partial(CorsHandler, directory=str(root))
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Serving {root} on http://127.0.0.1:{args.port}/", flush=True)
    # sanity list of QC zips
    for name in (
        "UPLOAD-THIS-TO-QC-gen-g1205.zip",
        "UPLOAD-THIS-TO-QC-fin-f39.zip",
        "UPLOAD-THIS-TO-QC-the-thread-hands-back-its-own-opener.zip",
    ):
        p = root / name
        print(f"  {name}: {'OK '+str(p.stat().st_size) if p.exists() else 'MISSING'}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
