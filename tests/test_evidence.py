"""Offline numeric-evidence contracts; no acquired data or external requests."""
import contextlib
import copy
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from finance_research_hub import RISK_NOTICE
from finance_research_hub import cli, server
from finance_research_hub.core import Store, demo_records, envelope, normalize_record
from finance_research_hub.evidence import dataset_chunks, demo_datasets, normalize_dataset
from finance_research_hub.service import ResearchWorkspace


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.raw = demo_datasets()[0]

    def test_typed_values_and_per_row_policy_survive_normalization_and_reimport(self):
        self.raw["noncommercial"] = False
        self.raw["rows"][0].update(risk_notice="removed", noncommercial=False, is_demo=False)
        value = normalize_dataset(self.raw)
        self.assertTrue(value["noncommercial"])
        self.assertEqual(value["risk_notice"], RISK_NOTICE)
        self.assertTrue(all(row["risk_notice"] == RISK_NOTICE and row["noncommercial"] and row["is_demo"] for row in value["rows"]))
        self.assertEqual(normalize_dataset(value), value)
        self.assertEqual(value["missing_fields"], [])

    def test_invalid_numeric_values_never_become_zero_or_float_silently(self):
        for bad in ("100.5", True, float("nan"), float("inf"), -float("inf")):
            raw = copy.deepcopy(self.raw)
            raw["rows"][0]["value"] = bad
            with self.subTest(value=str(bad)), self.assertRaises(ValueError):
                normalize_dataset(raw)

    def test_unknown_dimensions_and_null_values_remain_explicit(self):
        self.raw.update(market=None, currency=None, timezone=None, as_of=None, adjustment="unknown", frequency="unknown", units={})
        self.raw["provenance"]["identity_basis"] = None
        self.raw["rows"][0]["value"] = None
        value = normalize_dataset(self.raw)
        for field in ("market", "currency", "timezone", "as_of", "adjustment", "frequency", "units.value", "rows.value", "provenance.identity_basis"):
            self.assertIn(field, value["missing_fields"])
        self.assertIsNone(value["rows"][0]["value"])
        self.assertEqual(value["null_counts"]["value"], 1)

    def test_annual_macro_preserves_source_period_without_inventing_a_day(self):
        raw = {**self.raw, "kind": "macro_series", "source_id": "synthetic-annual", "as_of": "2023",
               "currency": "not_applicable", "timezone": "not_applicable", "adjustment": "not_applicable", "frequency": "annual",
               "columns": {"period": "string", "value": "number"}, "time_column": None, "value_column": "value",
               "units": {"value": "persons"}, "rows": [{"period": "2023", "value": 123}],
               "coverage": {"total_rows": 1, "truncated": False}}
        value = normalize_dataset(raw)
        self.assertEqual(value["rows"][0]["period"], "2023")
        self.assertIsNone(value["time_column"])
        self.assertNotIn("date", value["rows"][0])

    def test_schema_links_dates_and_bounds_fail_before_storage(self):
        bad_documents = [
            {**self.raw, "kind": "news"},
            {**self.raw, "kind": []},
            {**self.raw, "columns": {"value": "number"}},
            {**self.raw, "rows": [{"date": "2026-02-30", "value": 1}]},
            {**self.raw, "rows": [{"date": "2026-01-01", "value": 1, "unexpected": 5}]},
            {**self.raw, "rows": self.raw["rows"] * 334},
            {**self.raw, "topics": ["x"] * 21},
            {**self.raw, "related_record_ids": ["0" * 64] * 101},
            {**self.raw, "units": {"typo": "CNY"}},
            {**self.raw, "id": "0" * 64},
            {**self.raw, "coverage": {"total_rows": 5, "truncated": False}},
            {**self.raw, "coverage": {"total_rows": 2, "truncated": True}},
        ]
        for raw in bad_documents:
            with self.assertRaises(ValueError):
                normalize_dataset(raw)
        for url in ("http://example.com/", "javascript:alert(1)", "https://user:secret@example.com/"):
            with self.assertRaises(ValueError):
                normalize_dataset({**self.raw, "provenance": {**self.raw["provenance"], "url": url}})

    def test_chunks_keep_notice_units_gaps_and_row_window(self):
        value = normalize_dataset(self.raw)
        chunks = dataset_chunks(value, max_rows=1)
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0]["truncated"])
        self.assertEqual(chunks[0]["total_rows"], 3)
        self.assertIn(RISK_NOTICE, chunks[0]["content"])
        self.assertIn("CNY/share", chunks[0]["content"])


class EvidenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.workspace = ResearchWorkspace(":memory:", store=self.store)
        self.raw = demo_datasets()[0]

    def tearDown(self):
        self.store.close()

    def test_import_is_separate_idempotent_and_immutable(self):
        first = self.workspace.import_dataset(self.raw)
        self.assertEqual(first["status"], "new")
        identifier = first["dataset_id"]
        retrieved = self.workspace.get_dataset(identifier)["dataset"]
        summary = self.workspace.datasets()["items"][0]
        self.assertEqual(summary["content_hash"], retrieved["content_hash"])
        self.assertEqual(summary["hash_basis"], "sha256 of canonical normalized saved dataset before query metadata")
        self.assertEqual(self.workspace.get_dataset(identifier)["chunks"][0]["content_hash"], summary["content_hash"])
        self.assertEqual(self.workspace.import_dataset(retrieved)["status"], "unchanged")
        self.assertEqual(self.store.query(), [])
        changed = copy.deepcopy(self.raw)
        changed["rows"][0]["value"] = 999
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.workspace.import_dataset(changed)
        self.assertEqual(self.workspace.get_dataset(identifier)["dataset"]["rows"][0]["value"], 100)
        self.assertEqual(self.workspace.status()["dataset_count"], 1)
        self.assertEqual(self.workspace.status()["record_count"], 0)

    def test_directory_omits_full_rows_and_literal_search_excludes_numeric_values(self):
        for raw in demo_datasets():
            self.workspace.import_dataset(raw)
        result = self.workspace.datasets(symbol="DEMO-CN", limit=1)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["total_matches"], 2)
        self.assertNotIn("rows", result["items"][0])
        self.assertLessEqual(len(result["items"][0]["rows_preview"]), 5)
        self.assertFalse(result["items"][0]["rows_omitted"])
        large = copy.deepcopy(self.raw)
        large.update(source_id="long-synthetic", coverage={"truncated": False, "total_rows": 6})
        large["rows"] = [{"date": "2026-01-0" + str(i), "value": i} for i in range(1, 7)]
        large_id = self.workspace.import_dataset(large)["dataset_id"]
        self.assertTrue(next(i for i in self.workspace.datasets()["items"] if i["id"] == large_id)["rows_omitted"])
        self.assertEqual(self.workspace.datasets(q="SYNTHETIC")["count"], 3)
        self.assertEqual(self.workspace.datasets(q="102")["count"], 0)
        self.assertEqual(self.workspace.datasets(symbol="demo-cn")["count"], 0)

    def test_exact_retrieval_uses_primary_id_and_keeps_policy_rows(self):
        result = self.workspace.import_dataset(self.raw)
        trace = []
        self.store.db.set_trace_callback(trace.append)
        dataset = self.workspace.get_dataset(result["dataset_id"])
        self.assertTrue(dataset["found"])
        self.assertTrue(any("FROM datasets WHERE id=" in sql for sql in trace))
        self.assertEqual(len(dataset["dataset"]["rows"]), 3)
        self.assertTrue(all(row["risk_notice"] == RISK_NOTICE for row in dataset["dataset"]["rows"]))
        self.assertFalse(self.workspace.get_dataset("0" * 64)["found"])

    def test_dataset_only_pack_keeps_metadata_count_and_reports_numeric_evidence(self):
        self.workspace.import_dataset(self.raw)
        pack = self.workspace.research_pack(symbol="DEMO-CN")
        self.assertEqual(pack["count"], 0)
        self.assertTrue(pack["found"])
        self.assertFalse(pack["empty"])
        self.assertEqual(pack["related_datasets"]["count"], 1)
        self.assertEqual(pack["evidence_counts"], {"records": 0, "datasets": 1, "references": 0})
        self.assertEqual(pack["independent_corroboration"], "not_established")
        self.assertTrue(all(RISK_NOTICE in chunk["content"] for chunk in pack["dataset_chunks"]))

    def test_explicit_record_link_connects_anchor_without_inferred_topics(self):
        raw_record = demo_records()[0]
        self.store.ingest([raw_record])
        anchor = normalize_record(raw_record)["id"]
        self.raw["related_record_ids"] = [anchor]
        self.workspace.import_dataset(self.raw)
        pack = self.workspace.research_pack(record_id=anchor)
        self.assertEqual(pack["selection"]["basis"], "anchor_only")
        self.assertEqual(pack["related_datasets"]["items"][0]["relationship_basis"], "explicit_record_link")
        self.assertEqual(pack["count"], 1)

    def test_literal_catalogue_query_connects_dated_reference_without_fake_data(self):
        from finance_research_hub.workflow import research_catalog
        original = next(item for item in research_catalog() if item["id"] == "koyfin")
        result = self.workspace.research_pack(q="KOYFIN")
        self.assertTrue(result["found"])
        self.assertFalse(result["empty"])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["related_datasets"]["count"], 0)
        reference = result["reference_entries"]["items"][0]
        self.assertEqual(reference["id"], "koyfin")
        self.assertEqual(reference["reviewed_at"], original["reviewed_at"])
        self.assertEqual(reference["risk_notice"], RISK_NOTICE)
        self.assertTrue(reference["source_metadata_reference_only"])
        self.assertEqual(result["reference_entries"]["limit"], 20)
        self.assertEqual(self.workspace.research_pack(symbol="Koyfin")["reference_entries"]["count"], 0)

    def test_catalogue_results_are_bounded_and_literal(self):
        catalog = [{"id": str(i), "name": "Synthetic reference", "notes": "literal", "role": "manual_reference", "reviewed_at": "2026-01-01"} for i in range(25)]
        with patch("finance_research_hub.workflow.research_catalog", return_value=catalog):
            refs = self.workspace.research_pack(q="synthetic")["reference_entries"]
        self.assertEqual(refs["total_matches"], 25)
        self.assertEqual(refs["count"], 20)
        self.assertTrue(refs["truncated"])

    def test_legacy_schema_read_does_not_migrate_or_ingest(self):
        self.store.db.execute("DROP TABLE datasets")
        self.store.read_only = True
        readonly = ResearchWorkspace(":memory:", read_only=True, store=self.store)
        trace = []
        self.store.db.set_trace_callback(trace.append)
        self.assertFalse(readonly.datasets()["schema_available"])
        self.assertFalse(readonly.get_dataset("0" * 64)["schema_available"])
        self.assertEqual(readonly.status()["dataset_count"], 0)
        with self.assertRaises(PermissionError):
            readonly.import_dataset(self.raw)
        self.assertFalse(any("CREATE" in sql.upper() or "INSERT" in sql.upper() for sql in trace))

    def test_comparison_delegates_only_requested_full_datasets(self):
        identifiers = [self.workspace.import_dataset(raw)["dataset_id"] for raw in demo_datasets()]
        with patch("finance_research_hub.comparison.compare_datasets", return_value=envelope([])) as compare:
            self.workspace.compare(identifiers, alignment="intersection", start="2026-01-05", end="2026-01-07")
        self.assertEqual(len(compare.call_args.args[0]), 2)
        self.assertIn("rows", compare.call_args.args[0][0])
        self.assertEqual(compare.call_args.kwargs["alignment"], "intersection")
        with self.assertRaises(ValueError):
            self.workspace.compare([identifiers[0], identifiers[0]])
        with self.assertRaises(LookupError):
            self.workspace.compare([identifiers[0], "0" * 64])

    def test_local_cli_import_and_demo_do_not_call_sources(self):
        output = io.StringIO()
        with patch.object(cli, "Store") as factory, patch.object(cli.Path, "open", return_value=io.BytesIO(json.dumps(self.raw).encode())), contextlib.redirect_stdout(output):
            factory.return_value.__enter__.return_value = self.store
            self.assertEqual(cli.main(["import-dataset", "synthetic.json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "new")
        output = io.StringIO()
        with patch.object(cli, "Store") as factory, contextlib.redirect_stdout(output):
            factory.return_value.__enter__.return_value = self.store
            self.assertEqual(cli.main(["demo"]), 0)
        self.assertEqual(json.loads(output.getvalue())["datasets_seeded"], 2)

    def test_explicit_record_import_is_atomic_and_does_not_invent_retrieval_time(self):
        raw = demo_records()[0]
        raw.pop("retrieved_at")
        for document, expected in (({"items": [raw]}, 0), ([{**raw, "url": "http://example.com/"}], 2)):
            output, error = io.StringIO(), io.StringIO()
            before = list(self.store.db.iterdump())
            with patch.object(cli, "Store") as factory, patch.object(cli.Path, "open", return_value=io.BytesIO(json.dumps(document).encode())), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                factory.return_value.__enter__.return_value = self.store
                self.assertEqual(cli.main(["import-records", "synthetic-export.json"]), expected)
            self.assertIn(RISK_NOTICE, output.getvalue() + error.getvalue())
            if expected:
                self.assertEqual(list(self.store.db.iterdump()), before)
        self.assertEqual(self.store.query()[0]["retrieved_at"], "unknown")


class MemorySocket:
    def __init__(self, request):
        self.input, self.output = io.BytesIO(request), bytearray()
    def makefile(self, *args, **kwargs):
        return self.input
    def sendall(self, value):
        self.output.extend(value)


class DatasetHTTPTests(unittest.TestCase):
    def test_directory_exact_and_missing_routes_are_read_only(self):
        with Store(":memory:") as store:
            workspace = ResearchWorkspace(":memory:", store=store)
            identifier = workspace.import_dataset(demo_datasets()[0])["dataset_id"]
            for method, target, expected in (("GET", "/api/datasets", 200),
                                              ("GET", "/api/datasets/" + identifier, 200),
                                              ("GET", "/api/datasets/" + "0" * 64, 404),
                                              ("POST", "/api/import-dataset", 405)):
                sock = MemorySocket(f"{method} {target} HTTP/1.0\r\nHost: 127.0.0.1:8765\r\n\r\n".encode())
                with patch.object(server, "ResearchWorkspace", return_value=workspace):
                    server.make_handler(":memory:")(sock, ("127.0.0.1", 12345), SimpleNamespace(server_port=8765))
                headers, body = bytes(sock.output).split(b"\r\n\r\n", 1)
                self.assertEqual(int(headers.split(b" ", 2)[1]), expected)
                self.assertIn(RISK_NOTICE, body.decode())


if __name__ == "__main__":
    unittest.main()
