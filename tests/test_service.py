"""Offline shared-workspace checks; no files, sockets or source requests."""
import contextlib
import csv
import io
import json
import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from finance_research_hub import RISK_NOTICE
from finance_research_hub import cli, core, server
from finance_research_hub.core import Store, demo_records, normalize_record
from finance_research_hub.service import ResearchWorkspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.store.ingest(demo_records())
        self.workspace = ResearchWorkspace(":memory:", store=self.store)
        self.anchor = normalize_record(demo_records()[2])["id"]

    def tearDown(self):
        self.store.close()

    def related(self, count=1):
        base = demo_records()[2]
        return [{**base, "id": f"related-{index}", "kind": "news", "title": f"Synthetic related topic {index}",
                 "provider": "other-demo", "published_at": f"2027-01-{(index % 28) + 1:02d}"} for index in range(count)]

    def test_exact_record_and_own_history_are_not_a_top_n_scan(self):
        # Move the anchor behind the old 1000-record search window and many global changes.
        others = [{**demo_records()[0], "id": f"later-{i}", "published_at": "2030-01-01"} for i in range(1005)]
        self.store.ingest(others)
        trace = []
        self.store.db.set_trace_callback(trace.append)
        result = self.workspace.get_record(self.anchor, history_limit=1)
        self.assertTrue(result["found"])
        self.assertEqual(result["record"]["id"], self.anchor)
        self.assertEqual(result["history"]["total_matches"], 1)
        self.assertEqual(result["history"]["items"][0]["item_id"], self.anchor)
        self.assertTrue(any("FROM items WHERE id=" in text for text in trace))
        self.assertTrue(any("FROM changes WHERE item_id IN" in text for text in trace))
        plan = self.store.db.execute("EXPLAIN QUERY PLAN SELECT * FROM items WHERE id=?", (self.anchor,)).fetchall()
        self.assertTrue(any("SEARCH" in row[3] and "INDEX" in row[3] for row in plan))

    def test_record_scoped_history_has_own_total_and_limit(self):
        raw = demo_records()[2]
        self.store.ingest([{**raw, "title": "Synthetic revision 1"}])
        self.store.ingest([{**raw, "title": "Synthetic revision 2"}])
        history = self.workspace.changes(record_id=self.anchor, limit=2)
        self.assertEqual(history["total_matches"], 3)
        self.assertTrue(history["truncated"])
        self.assertEqual(len(history["items"]), 2)
        self.assertTrue(all(item["item_id"] == self.anchor for item in history["items"]))

    def test_search_literal_casefold_count_and_bounded_top_window(self):
        self.store.ingest(self.related(12))
        result = self.workspace.search(symbol="DEMO-CN", q="TOPIC", limit=3)
        self.assertEqual(result["total_matches"], 12)
        self.assertEqual(result["count"], 3)
        self.assertTrue(result["truncated"])
        self.assertEqual([i["published_at"] for i in result["items"]], ["2027-01-12", "2027-01-11", "2027-01-10"])
        self.assertEqual(self.workspace.search(q="%_")["count"], 0)
        self.assertEqual(self.workspace.search(symbol="demo-cn")["count"], 0)

    def test_query_stream_does_not_fetch_the_full_matching_table(self):
        actual_db = self.store.db
        class Cursor:
            def __init__(self, cursor):
                self.cursor = cursor
            def __iter__(self):
                return iter(self.cursor)
            def fetchall(self):
                raise AssertionError("Search must not materialize the full cursor")
        class Connection:
            def execute(self, sql, params):
                return Cursor(actual_db.execute(sql, params))
        self.store.db = Connection()
        try:
            self.assertEqual(self.store.query_details(limit=1)["total_matches"], 4)
        finally:
            self.store.db = actual_db

    def test_pack_connects_explicit_symbol_and_preserves_gaps_and_provenance(self):
        self.store.ingest(self.related(), {"provider": "other-demo", "truncated": True, "coverage": "synthetic bounded collection"})
        result = self.workspace.research_pack(record_id=self.anchor, history_limit=1)
        self.assertEqual(result["selection"]["basis"], "exact_symbol")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["missing_kinds"], ["rating", "talk"])
        self.assertTrue(result["coverage"]["history_truncated"])
        self.assertEqual(result["independent_corroboration"], "not_established")
        self.assertFalse(result["full_report_text_included"])
        self.assertEqual(len(result["provenance"]), 2)
        self.assertTrue(all(p["source_url"].startswith("https://") for p in result["provenance"]))
        self.assertTrue(all(RISK_NOTICE in chunk["content"] for chunk in result["chunks"]))
        self.assertTrue(result["coverage"]["provider_collections"][0]["truncated"])
        self.assertIn(RISK_NOTICE, result["brief"]["text"])

    def test_pack_without_symbol_is_anchor_only_and_does_not_infer_a_topic(self):
        anchor = normalize_record(demo_records()[0])["id"]
        result = self.workspace.research_pack(record_id=anchor)
        self.assertEqual(result["selection"]["basis"], "anchor_only")
        self.assertEqual(result["selection"]["q"], "")
        self.assertEqual(result["count"], 1)

    def test_explicit_topic_query_can_broaden_beyond_anchor_symbol(self):
        result = self.workspace.research_pack(record_id=self.anchor, q="示例")
        self.assertEqual(result["count"], 4)
        self.assertEqual(result["selection"]["basis"], "literal_query")
        self.assertEqual(result["selection"]["symbol"], "")
        self.assertEqual(result["missing_kinds"], [])

    def test_pack_history_scope_can_include_anchor_outside_selected_window(self):
        self.store.ingest(self.related(100))
        result = self.workspace.research_pack(record_id=self.anchor, limit=100, history_limit=1)
        self.assertFalse(result["selection"]["anchor_in_selection"])
        self.assertEqual(result["coverage"]["history_record_count"], 101)
        self.assertFalse(result["coverage"]["history_scope_truncated"])
        self.assertEqual(result["history"]["total_matches"], 101)
        self.assertTrue(result["coverage"]["truncated"])

    def test_empty_missing_and_invalid_are_explicit(self):
        missing = self.workspace.get_record("0" * 64)
        self.assertFalse(missing["found"])
        self.assertIsNone(missing["record"])
        empty = self.workspace.research_pack(q="unmatched synthetic keyword")
        self.assertEqual(empty["count"], 0)
        self.assertTrue(empty["empty"])
        self.assertEqual(empty["missing_kinds"], sorted(core.KINDS))
        self.assertNotIn("missing_reason", empty)
        anchored = self.workspace.research_pack(record_id="0" * 64)
        self.assertEqual(anchored["selection"]["basis"], "missing_anchor")
        for action in (lambda: self.workspace.get_record("../missing"),
                       lambda: self.workspace.research_pack(),
                       lambda: self.workspace.research_pack(symbol="DEMO-CN", limit=101),
                       lambda: self.workspace.search(q="x" * 201),
                       lambda: self.workspace.search(limit=True),
                       lambda: self.workspace.changes(record_id=False),
                       lambda: self.workspace.research_pack(record_id=False, symbol="DEMO-CN"),
                       lambda: self.workspace.research_pack(record_id=self.anchor, symbol="OTHER")):
            with self.assertRaises(ValueError):
                action()

    def test_export_keeps_query_coverage_and_notice_inside_each_format(self):
        for form in ("json", "jsonl", "csv", "markdown"):
            result = self.workspace.export(form, limit=1)
            self.assertTrue(result["query"]["truncated"])
            self.assertIn(RISK_NOTICE, result["content"])
            if form == "json":
                parsed = json.loads(result["content"])
                self.assertTrue(parsed["query"]["truncated"])
                self.assertEqual(parsed["chunks"][0]["query"]["total_matches"], 4)
            if form == "csv":
                row = list(csv.DictReader(io.StringIO(result["content"])))[0]
                self.assertEqual(row["query_total_matches"], "4")

    def test_status_returns_counters_only_with_actual_demo_mode(self):
        status = self.workspace.status()
        self.assertEqual(status["items"], [])
        self.assertEqual(status["record_count"], 4)
        self.assertEqual(status["mode"], "demo")
        self.store.ingest([{**demo_records()[0], "id": "non-demo", "is_demo": False}])
        self.assertEqual(self.workspace.status()["mode"], "mixed")

    def test_read_deadline_interrupts_python_search_and_status_scan(self):
        self.store._deadline = 5
        for action in (lambda: self.store.query(limit=1), self.store.status):
            with patch.object(core.time, "monotonic", side_effect=[0, 0, 6]):
                with self.assertRaisesRegex(sqlite3.OperationalError, "deadline"):
                    action()
        self.store._deadline = None

    def test_service_reads_do_not_change_rows_or_history(self):
        before = list(self.store.db.iterdump())
        with patch("finance_research_hub.providers.request_bytes", side_effect=AssertionError("No source network")):
            self.workspace.status()
            self.workspace.sources()
            self.workspace.search()
            self.workspace.get_record(self.anchor)
            self.workspace.changes(record_id=self.anchor)
            self.workspace.brief()
            self.workspace.export()
            self.workspace.research_pack(record_id=self.anchor)
        self.assertEqual(list(self.store.db.iterdump()), before)

    def test_cli_record_pack_use_shared_service_and_keep_notice(self):
        for command, expected in ((["record", self.anchor], 0), (["pack", "--record-id", self.anchor], 0),
                                  (["record", "0" * 64], 1), (["pack", "--q", "absent"], 0)):
            output = io.StringIO()
            with patch.object(cli, "Store") as factory, contextlib.redirect_stdout(output):
                factory.return_value.__enter__.return_value = self.store
                self.assertEqual(cli.main(command), expected)
            result = json.loads(output.getvalue())
            self.assertEqual(result["risk_notice"], RISK_NOTICE)


class ReadOnlyStoreTests(unittest.TestCase):
    def test_uri_is_read_only_and_schema_ddl_and_ingest_are_not_allowed(self):
        connection = Mock()
        with patch.object(Path, "is_file", return_value=True), patch.object(core.sqlite3, "connect", return_value=connection) as connect:
            store = Store("/synthetic directory/workspace.sqlite3", read_only=True)
        self.assertEqual(connect.call_args.args[0], "file:///synthetic%20directory/workspace.sqlite3?mode=ro")
        self.assertTrue(connect.call_args.kwargs["uri"])
        connection.executescript.assert_not_called()
        connection.commit.assert_not_called()
        connection.set_progress_handler.assert_called_once()
        with self.assertRaises(PermissionError):
            store.ingest(demo_records())
        store.close()

    def test_missing_read_only_database_never_creates_state(self):
        with patch.object(Path, "is_file", return_value=False), patch.object(Path, "mkdir") as mkdir, patch.object(core.sqlite3, "connect") as connect:
            with self.assertRaises(FileNotFoundError):
                ResearchWorkspace("/synthetic/missing.sqlite3", read_only=True).search()
        mkdir.assert_not_called()
        connect.assert_not_called()
        with self.assertRaises(ValueError):
            Store(":memory:", read_only=True)


class MemorySocket:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = bytearray()
    def makefile(self, *args, **kwargs):
        return self.input
    def sendall(self, data):
        self.output.extend(data)


class WorkspaceHTTPTests(unittest.TestCase):
    def test_exact_record_pack_and_query_bounds_through_http(self):
        with Store(":memory:") as store:
            store.ingest(demo_records())
            anchor = normalize_record(demo_records()[2])["id"]
            workspace = ResearchWorkspace(":memory:", store=store)
            checks = [(f"/api/records/{anchor}", 200), ("/api/records/" + "0" * 64, 404),
                      (f"/api/pack?record_id={anchor}", 200), ("/api/pack?q=absent", 200),
                      ("/api/pack", 400), ("/api/pack?symbol=DEMO-CN&limit=101", 400),
                      ("/api/items?q=" + "x" * 201, 400)]
            for target, expected in checks:
                request = f"GET {target} HTTP/1.0\r\nHost: 127.0.0.1:8765\r\n\r\n".encode()
                sock = MemorySocket(request)
                with patch.object(server, "ResearchWorkspace", return_value=workspace):
                    server.make_handler(":memory:")(sock, ("127.0.0.1", 12345), SimpleNamespace(server_port=8765))
                headers, body = bytes(sock.output).split(b"\r\n\r\n", 1)
                self.assertEqual(int(headers.split(b" ", 2)[1]), expected)
                self.assertIn(RISK_NOTICE, body.decode())


if __name__ == "__main__":
    unittest.main()
