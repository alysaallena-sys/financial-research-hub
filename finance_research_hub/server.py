"""Local, read-only HTTP presentation. No collection or execution endpoint."""
from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from .core import Store, brief, envelope, export_items
from .providers import source_catalog

STATIC = Path(__file__).parent / "static"


def make_handler(db_path: str, static_dir: Path = STATIC) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "FinancialResearchHub/0.1"

        def log_message(self, *_: Any) -> None:
            # Do not log search queries or acquired-source contents by default.
            pass

        def send_body(self, data: str | bytes, content_type: str, status: int = 200) -> None:
            encoded = data.encode("utf-8") if isinstance(data, str) else data
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(encoded)

        def send_json(self, data: dict[str, Any], status: int = 200) -> None:
            self.send_body(json.dumps(data, ensure_ascii=False, allow_nan=False), "application/json; charset=utf-8", status)

        def allowed_origin(self) -> bool:
            # Loopback bind alone does not prevent DNS-rebinding reads.
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if host not in allowed:
                return False
            origin = self.headers.get("Origin")
            return origin is None or origin in {"http://" + item for item in allowed}

        def do_GET(self) -> None:
            if not self.allowed_origin():
                self.send_json(envelope([], error="Only the matching loopback origin is allowed"), 403)
                return
            parsed = urlsplit(self.path)
            args = parse_qs(parsed.query, keep_blank_values=True)
            try:
                if parsed.path.startswith("/api/"):
                    self.api(parsed.path, args)
                    return
                path = unquote(parsed.path)
                relative = "index.html" if path == "/" else path.lstrip("/")
                root = static_dir.resolve()
                target = (root / relative).resolve()
                if not target.is_relative_to(root) or target.suffix not in {".html", ".js", ".css", ".svg", ".png", ".ico"} or not target.is_file():
                    self.send_json(envelope([], error="Not found"), 404)
                    return
                self.send_body(target.read_bytes(), (mimetypes.guess_type(target.name)[0] or "application/octet-stream") + ("; charset=utf-8" if target.suffix in {".html", ".js", ".css", ".svg"} else ""))
            except (ValueError, TypeError) as exc:
                self.send_json(envelope([], error=str(exc)), 400)
            except Exception:
                self.send_json(envelope([], error="Local request failed. Check the local database and project configuration."), 500)

        def api(self, path: str, args: dict[str, list[str]]) -> None:
            one = lambda key, default="": args.get(key, [default])[0]
            limit = int(one("limit", "100"))
            filters = {key: one(key) for key in ("kind", "provider", "symbol", "q")}
            filters["limit"] = limit
            with Store(db_path) as store:
                if path == "/api/items":
                    items = store.query(**filters)
                    self.send_json(envelope(items, limit=limit, returned=len(items), completeness="query limited to requested maximum"))
                elif path == "/api/status":
                    self.send_json(store.status())
                elif path == "/api/changes":
                    self.send_json(envelope(store.changes(limit), limit=limit))
                elif path == "/api/sources":
                    collections = store.collections()
                    self.send_json(envelope([], sources=source_catalog(collections), collections=collections,
                                            network_enabled=False, note="Adapter availability is not live-source acceptance."))
                elif path == "/api/brief":
                    self.send_json(brief(store.query(**filters)))
                elif path == "/api/export":
                    data, content_type = export_items(store.query(**filters), one("format", "json"))
                    self.send_body(data, content_type)
                else:
                    self.send_json(envelope([], error="Not found"), 404)

        def do_POST(self) -> None:
            self.send_json(envelope([], error="Read-only server; use the explicit local CLI for collection"), 405)

        do_PUT = do_POST
        do_DELETE = do_POST
        do_PATCH = do_POST

    return Handler


def create_server(db_path: str, port: int = 8765, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Only loopback binding is supported")
    if not 0 <= port <= 65535:
        raise ValueError("Invalid port")
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(db_path))


def serve(db_path: str, port: int = 8765, host: str = "127.0.0.1") -> None:
    server = create_server(db_path, port, host)
    from . import RISK_NOTICE
    print(RISK_NOTICE, flush=True)
    print(f"Local read-only workspace: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

