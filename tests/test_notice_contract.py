"""Independent notice/integration contract checks using synthetic memory-only inputs."""
from __future__ import annotations

import contextlib
import csv
import io
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from finance_research_hub import LICENSE_ID, RISK_NOTICE
from finance_research_hub import cli, server
from finance_research_hub.core import Store, brief, demo_records, envelope, export_items, normalize_record
from finance_research_hub.providers import ProviderError, collect_eastmoney, validate_request_url


ROOT = Path(__file__).resolve().parents[1]


class NoticeContractTests(unittest.TestCase):
    def records(self):
        with Store(":memory:") as store:
            store.ingest(demo_records())
            return store.query()

    def test_license_and_machine_contract_share_required_notice(self):
        contract = json.loads((ROOT / "integrations/editor-contract.json").read_text())
        self.assertEqual(contract["risk_notice"], RISK_NOTICE)
        self.assertEqual(contract["license_id"], LICENSE_ID)
        self.assertTrue(contract["visible_required"])
        self.assertTrue(contract["noncommercial"])
        self.assertIn("retrieval_chunk", contract["preserve_on"])
        self.assertIn(LICENSE_ID, (ROOT / "LICENSE").read_text())
        self.assertIn(RISK_NOTICE, (ROOT / "NOTICE").read_text())

    def test_imported_material_cannot_remove_notice_or_noncommercial_flag(self):
        raw = demo_records()[0]
        raw.update(risk_notice="", noncommercial=False)
        result = normalize_record(raw)
        self.assertEqual(result["risk_notice"], RISK_NOTICE)
        self.assertIs(result["noncommercial"], True)

    def test_envelope_cannot_override_mandatory_contract(self):
        result = envelope([], risk_notice="removed", noncommercial=False, license="MIT",
                          editor_notice_required=False)
        self.assertEqual(result["risk_notice"], RISK_NOTICE)
        self.assertIs(result["noncommercial"], True)
        self.assertEqual(result["license"], LICENSE_ID)
        self.assertIs(result["editor_notice_required"], True)

    def test_query_and_deterministic_brief_keep_notice_and_demo_markers(self):
        records = self.records()
        result = brief(records)
        self.assertIn(RISK_NOTICE, result["text"])
        self.assertIn("合成演示", result["text"])
        for item in result["items"]:
            self.assertEqual(item["risk_notice"], RISK_NOTICE)
            self.assertIs(item["noncommercial"], True)
            self.assertIs(item["is_demo"], True)

    def test_all_export_records_and_chunks_keep_notice(self):
        records = self.records()
        text, _ = export_items(records, "json")
        result = json.loads(text)
        self.assertEqual(result["risk_notice"], RISK_NOTICE)
        self.assertEqual(result["license"], LICENSE_ID)
        self.assertEqual(len(result["items"]), len(records))
        for item in result["items"]:
            self.assertEqual(item["risk_notice"], RISK_NOTICE)
        for chunk in result["chunks"]:
            self.assertEqual(chunk["risk_notice"], RISK_NOTICE)
            self.assertIn(RISK_NOTICE, chunk["content"])
            self.assertIs(chunk["is_demo"], True)

        text, _ = export_items(records, "jsonl")
        chunks = [json.loads(line) for line in text.splitlines()]
        self.assertEqual(len(chunks), len(records))
        for chunk in chunks:
            self.assertEqual(chunk["risk_notice"], RISK_NOTICE)
            self.assertIn(RISK_NOTICE, chunk["content"])

        text, _ = export_items(records, "csv")
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(len(rows), len(records))
        for row in rows:
            self.assertEqual(row["risk_notice"], RISK_NOTICE)
            self.assertEqual(row["noncommercial"], "True")

        text, _ = export_items(records, "markdown")
        sections = text.split("\n\n---\n\n")
        self.assertEqual(len(sections), len(records) + 1)
        for section in sections:
            self.assertIn(RISK_NOTICE, section)

    def test_empty_exports_have_parseable_notice_not_fake_data(self):
        for name in ("json", "jsonl", "csv", "markdown"):
            with self.subTest(format=name):
                text, _ = export_items([], name)
                self.assertIn(RISK_NOTICE, text)
                if name == "json":
                    result = json.loads(text)
                    self.assertEqual(result["count"], 0)
                    self.assertEqual(result["items"], [])
                elif name == "jsonl":
                    rows = [json.loads(line) for line in text.splitlines()]
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["record_type"], "notice")
                    self.assertEqual(rows[0]["count"], 0)
                elif name == "csv":
                    rows = list(csv.DictReader(io.StringIO(text)))
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["record_type"], "notice")
                    self.assertFalse(rows[0].get("id"))

    def run_cli(self, argv):
        out, error = io.StringIO(), io.StringIO()
        with patch.object(cli, "Store", side_effect=lambda _: Store(":memory:")):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(error):
                code = cli.main(argv)
        return code, out.getvalue(), error.getvalue()

    def test_empty_cli_query_brief_and_each_export_keep_notice(self):
        commands = [["query"], ["brief"]] + [
            ["export", "--format", name] for name in ("json", "jsonl", "csv", "markdown")
        ]
        for argv in commands:
            with self.subTest(command=argv):
                code, out, error = self.run_cli(argv)
                self.assertEqual(code, 0)
                self.assertIn(RISK_NOTICE, out)
                self.assertEqual(error, "")

    def test_cli_collection_without_live_refuses_before_any_network_or_store(self):
        error = io.StringIO()
        with patch.object(cli, "collect_feed") as collect, patch.object(cli, "Store") as store:
            with contextlib.redirect_stderr(error):
                code = cli.main(["collect", "--source", "bbc"])
        self.assertEqual(code, 2)
        self.assertIn(RISK_NOTICE, error.getvalue())
        collect.assert_not_called()
        store.assert_not_called()

    def test_cli_argument_error_contains_notice(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            with self.assertRaises(SystemExit) as caught:
                cli.main(["query", "--kind", "unsupported"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn(RISK_NOTICE, error.getvalue())

    def test_cli_database_failure_is_a_noticed_error_result(self):
        error = io.StringIO()
        with patch.object(cli, "Store", side_effect=sqlite3.OperationalError("synthetic invalid database")):
            with contextlib.redirect_stderr(error):
                code = cli.main(["query"])
        self.assertEqual(code, 2)
        result = json.loads(error.getvalue())
        self.assertEqual(result["risk_notice"], RISK_NOTICE)
        self.assertIs(result["noncommercial"], True)
        self.assertIn("error", result)


class MemorySocket:
    """One HTTP exchange without opening a socket, file or server process."""

    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = bytearray()

    def makefile(self, *args, **kwargs):
        return self.input

    def sendall(self, data):
        self.output.extend(data)


class PresentationBoundaryTests(unittest.TestCase):
    def exchange(self, target, method="GET", host="127.0.0.1:8765", origin=None):
        extra = f"Origin: {origin}\r\n" if origin else ""
        request = f"{method} {target} HTTP/1.0\r\nHost: {host}\r\n{extra}\r\n".encode()
        sock = MemorySocket(request)
        handler = server.make_handler(":memory:")
        with patch.object(server, "Store", side_effect=lambda _: Store(":memory:")):
            handler(sock, ("127.0.0.1", 12345), SimpleNamespace(server_port=8765))
        head, body = bytes(sock.output).split(b"\r\n\r\n", 1)
        return int(head.split(b" ", 2)[1]), body.decode()

    def test_empty_api_and_errors_keep_notice_in_payload(self):
        checks = [
            ("/api/items", "GET", 200),
            ("/api/brief", "GET", 200),
            ("/api/export?format=jsonl", "GET", 200),
            ("/api/items?limit=0", "GET", 400),
            ("/api/unknown", "GET", 404),
            ("/api/items", "POST", 405),
            ("/api/collect?url=https://example.com/report.pdf", "GET", 404),
        ]
        for target, method, expected in checks:
            with self.subTest(target=target, method=method):
                status, body = self.exchange(target, method)
                self.assertEqual(status, expected)
                self.assertIn(RISK_NOTICE, body)

    def test_nonloopback_host_and_foreign_origin_are_noticed_rejections(self):
        for options in ({"host": "outside.example:8765"}, {"origin": "https://outside.example"}):
            with self.subTest(options=options):
                status, body = self.exchange("/api/items", **options)
                self.assertEqual(status, 403)
                self.assertIn(RISK_NOTICE, body)

    def test_public_bind_rejected_before_server_construction(self):
        with patch.object(server, "ThreadingHTTPServer") as create:
            with self.assertRaises(ValueError):
                server.create_server(":memory:", host="0.0.0.0")
            create.assert_not_called()

    def test_source_allowlist_excludes_arbitrary_targets_and_pdf_downloads(self):
        for url in ("http://reportapi.eastmoney.com/report/list", "https://example.com/report.pdf",
                    "https://127.0.0.1/api", "https://www.ted.com.evil.example/",
                    "https://user:password@www.ted.com/feed"):
            with self.subTest(url=url):
                with self.assertRaises(ProviderError):
                    validate_request_url(url)

        calls = []

        def transport(url, payload=None):
            calls.append((url, payload))
            return json.dumps({"TotalPage": 1, "data": [{"title": "合成研报", "infoCode": "demo-id",
                                "publishDate": "2026-01-01", "orgSName": "合成机构"}]}).encode()

        records, coverage = collect_eastmoney(report_type="stock", symbol="600519",
                                              begin="2026-01-01", end="2026-01-02", transport=transport)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][0].startswith("https://reportapi.eastmoney.com/report/"))
        self.assertNotIn(".pdf", calls[0][0])
        self.assertEqual(len(records), 1)
        self.assertIn("metadata", coverage["coverage"])


if __name__ == "__main__":
    unittest.main()

