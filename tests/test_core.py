import csv
import io
import json
import unittest

from finance_research_hub import RISK_NOTICE
from finance_research_hub.core import Store, brief, demo_records, envelope, export_items, normalize_record
from finance_research_hub.server import create_server


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.raw = demo_records()[2]

    def tearDown(self):
        self.store.close()

    def test_first_seen_is_not_publication_time_and_replay_is_unchanged(self):
        self.assertEqual(self.store.ingest([self.raw]), {"new": 1, "updated": 0, "unchanged": 0})
        first = self.store.query()[0]
        self.assertNotEqual(first["first_seen_at"], first["published_at"])
        replay = {**self.raw, "retrieved_at": "2030-01-01T00:00:00+00:00"}
        self.assertEqual(self.store.ingest([replay])["unchanged"], 1)
        self.assertEqual(len(self.store.changes()), 1)
        # Exported, already-normalized items keep their upstream identity on reimport.
        self.assertEqual(self.store.ingest([first])["unchanged"], 1)
        self.assertEqual(len(self.store.query()), 1)

    def test_update_records_previous_version_and_updates_query_index(self):
        self.store.ingest([self.raw])
        changed = {**self.raw, "symbol": "DEMO-NEW", "title": "新的合成标题"}
        self.assertEqual(self.store.ingest([changed])["updated"], 1)
        self.assertEqual(self.store.query(symbol="DEMO-CN"), [])
        self.assertEqual(len(self.store.query(symbol="DEMO-NEW")), 1)
        change = self.store.changes()[0]
        self.assertEqual(change["before"]["title"], self.raw["title"])
        self.assertEqual(change["after"]["title"], changed["title"])
        self.assertEqual(change["item"], change["after"])

    def test_provider_and_kind_are_part_of_identity(self):
        self.store.ingest([self.raw, {**self.raw, "provider": "independent-demo"}])
        self.assertEqual(len(self.store.query()), 2)
        self.assertEqual(len(self.store.query(provider="demo")), 1)
        self.assertEqual(len(self.store.query(q="新的%标题")), 0)

    def test_batch_validation_precedes_write(self):
        with self.assertRaises(ValueError):
            self.store.ingest([self.raw, {**self.raw, "url": "javascript:alert(1)"}])
        self.assertEqual(self.store.query(), [])
        with self.assertRaises(ValueError):
            self.store.ingest([{**self.raw, "url": "https://example.com/\n[x]"}])

    def test_notice_cannot_be_replaced_by_source_or_extra_fields(self):
        item = normalize_record({**self.raw, "risk_notice": "", "noncommercial": False})
        self.assertEqual(item["risk_notice"], RISK_NOTICE)
        self.assertTrue(item["noncommercial"])
        output = envelope([item], risk_notice="gone", noncommercial=False)
        self.assertEqual(output["risk_notice"], RISK_NOTICE)
        self.assertTrue(output["noncommercial"])

    def test_per_record_and_empty_export_notice_retention(self):
        self.store.ingest(demo_records())
        items = self.store.query()
        obj = json.loads(export_items(items, "json")[0])
        self.assertTrue(all(i["risk_notice"] == RISK_NOTICE for i in obj["items"]))
        self.assertTrue(all(RISK_NOTICE in c["content"] for c in obj["chunks"]))
        for form in ("json", "jsonl", "csv", "markdown"):
            for batch in (items, []):
                text, _ = export_items(batch, form)
                self.assertIn(RISK_NOTICE, text)
        jsonl = [json.loads(line) for line in export_items(items, "jsonl")[0].splitlines()]
        self.assertTrue(all(RISK_NOTICE in row["content"] for row in jsonl))
        empty = json.loads(export_items([], "jsonl")[0])
        self.assertEqual(empty["record_type"], "notice")
        rows = list(csv.DictReader(io.StringIO(export_items(items, "csv")[0])))
        self.assertTrue(all(r["risk_notice"] == RISK_NOTICE for r in rows))
        empty_rows = list(csv.DictReader(io.StringIO(export_items([], "csv")[0])))
        self.assertEqual(empty_rows[0]["record_type"], "notice")

    def test_untrusted_markdown_and_csv_text_is_not_active_markup(self):
        self.store.ingest([{**self.raw, "title": '=HYPERLINK("bad")', "summary": '<script>bad()</script> [bad](javascript:bad)'}])
        items = self.store.query()
        csv_row = list(csv.DictReader(io.StringIO(export_items(items, "csv")[0])))[0]
        self.assertTrue(csv_row["title"].startswith("'="))
        md = export_items(items, "markdown")[0]
        self.assertNotIn("<script>", md)
        self.assertNotIn("[bad](javascript:bad)", md)
        self.assertIn(RISK_NOTICE, brief(items)["text"])

    def test_remote_binding_rejected_without_opening_socket(self):
        with self.assertRaises(ValueError):
            create_server(":memory:", host="0.0.0.0")


if __name__ == "__main__":
    unittest.main()

