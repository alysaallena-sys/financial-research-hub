"""Explicit local commands; no installation, collection or model calls on import."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import RISK_NOTICE
from .core import Store, demo_records, envelope
from .service import ResearchWorkspace
from .providers import (FEEDS, ProviderError, collect_eastmoney, collect_feed, collect_yahoo,
                        curl_request_bytes, request_bytes, source_catalog)

DEFAULT_DB = ".local/research.sqlite3"


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{RISK_NOTICE}\nerror: {message}\n")


def _filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kind", choices=["news", "talk", "research", "rating"], default="")
    parser.add_argument("--provider", default="")
    parser.add_argument("--symbol", default="")
    parser.add_argument("--q", default="", help="Literal metadata search")
    parser.add_argument("--limit", type=int, default=100)


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description="Noncommercial financial metadata workspace", epilog=RISK_NOTICE)
    parser.add_argument("--db", default=DEFAULT_DB, help="Local SQLite state (never publish this file)")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    for name in ("demo", "query", "record", "pack", "brief", "export", "sources", "changes", "collect", "serve"):
        cmd = sub.add_parser(name, epilog=RISK_NOTICE)
        cmd.add_argument("--db", default=argparse.SUPPRESS, help="Also accepted after the command")
        if name in {"query", "brief", "export"}:
            _filters(cmd)
        if name == "export":
            cmd.add_argument("--format", choices=["json", "jsonl", "csv", "markdown"], default="json")
            cmd.add_argument("--output", help="Create a new export file; existing paths are not overwritten")
        if name == "changes":
            cmd.add_argument("--limit", type=int, default=100)
            cmd.add_argument("--record-id", default="", help="Scope history to one exact record ID")
        if name == "record":
            cmd.add_argument("record_id", help="Exact 64-character record ID")
            cmd.add_argument("--history-limit", type=int, default=50)
        if name == "pack":
            cmd.add_argument("--record-id", default="", help="Optional exact anchor record ID")
            cmd.add_argument("--symbol", default="", help="Exact saved symbol; no automatic entity inference")
            cmd.add_argument("--q", default="", help="Literal metadata text, not semantic similarity")
            cmd.add_argument("--limit", type=int, default=100, help="At most 100 selected records")
            cmd.add_argument("--history-limit", type=int, default=20)
        if name == "collect":
            cmd.add_argument("--source", required=True, choices=[*FEEDS, "eastmoney", "yahoo"])
            cmd.add_argument("--live", action="store_true", help="Explicitly permit a bounded public metadata request")
            cmd.add_argument("--transport", choices=["urllib", "curl"], default="urllib",
                             help="Verified TLS transport for RSS/Eastmoney; curl is explicit and never an automatic TLS downgrade")
            cmd.add_argument("--symbol", default="")
            cmd.add_argument("--report-type", choices=["stock", "industry", "strategy", "macro", "morning"], default="stock")
            cmd.add_argument("--industry", default="")
            cmd.add_argument("--begin")
            cmd.add_argument("--end")
            cmd.add_argument("--max-pages", type=int, default=1)
            cmd.add_argument("--page-size", type=int, default=20)
        if name == "serve":
            cmd.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "localhost"])
            cmd.add_argument("--port", type=int, default=8765)
            cmd.add_argument("--demo", action="store_true", help="Seed synthetic examples before serving")
    return parser


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        # Reject accidental network commands before creating a database.
        if args.command == "collect" and not args.live:
            raise ValueError("Collection requires --live. No network request was made.")
        if args.command == "collect":
            transport = curl_request_bytes if args.transport == "curl" else request_bytes
            if args.source in FEEDS:
                records, collection = collect_feed(args.source, transport=transport)
            elif args.source == "eastmoney":
                records, collection = collect_eastmoney(report_type=args.report_type, symbol=args.symbol,
                                                      industry=args.industry, begin=args.begin, end=args.end,
                                                      max_pages=args.max_pages, page_size=args.page_size, transport=transport)
            else:
                if args.transport != "urllib":
                    raise ValueError("Yahoo uses yfinance's own transport; --transport curl applies only to RSS/Eastmoney")
                records, collection = collect_yahoo(args.symbol)
            collection["transport"] = args.transport if args.source != "yahoo" else "yfinance"
            with Store(args.db) as store:
                delta = store.ingest(records, collection)
                _print(envelope([], changes=delta, collection=collection))
            return 0
        if args.command == "serve":
            with Store(args.db) as store:
                if args.demo:
                    store.ingest(demo_records())
            from .server import serve
            serve(args.db, args.port, args.host)
            return 0
        with Store(args.db) as store:
            workspace = ResearchWorkspace(args.db, store=store)
            if args.command == "demo":
                delta = store.ingest(demo_records())
                _print(envelope(store.query(), changes=delta, note="All demo records are synthetic; no live source was called."))
            elif args.command == "sources":
                _print(workspace.sources())
            elif args.command == "changes":
                _print(workspace.changes(record_id=args.record_id, limit=args.limit))
            elif args.command == "record":
                result = workspace.get_record(args.record_id, history_limit=args.history_limit)
                _print(result)
                return 0 if result["found"] else 1
            elif args.command == "pack":
                result = workspace.research_pack(record_id=args.record_id, symbol=args.symbol, q=args.q,
                                                 limit=args.limit, history_limit=args.history_limit)
                _print(result)
                return 1 if result.get("missing_reason") else 0
            else:
                filters = {key: getattr(args, key) for key in ("kind", "provider", "symbol", "q", "limit")}
                if args.command == "query":
                    _print(workspace.search(**filters))
                elif args.command == "brief":
                    print(workspace.brief(**filters)["text"])
                else:
                    result = workspace.export(args.format, **filters)
                    text = result["content"]
                    if args.output:
                        output = Path(args.output)
                        output.parent.mkdir(parents=True, exist_ok=True)
                        with output.open("x", encoding="utf-8", newline="") as handle:
                            handle.write(text)
                        _print(envelope([], output=str(output), exported_records=result["count"], format=args.format, query=result["query"]))
                    else:
                        print(text, end="" if text.endswith("\n") else "\n")
        return 0
    except (ValueError, ProviderError, OSError, sqlite3.Error) as exc:
        print(json.dumps(envelope([], error=str(exc)), ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

