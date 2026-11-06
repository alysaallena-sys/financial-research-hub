"""Real stdio protocol acceptance against the optional official SDK."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from finance_research_hub import RISK_NOTICE
from finance_research_hub.core import Store, demo_records
from finance_research_hub.evidence import demo_datasets

HAS_MCP = importlib.util.find_spec("mcp") is not None
ROOT = Path(__file__).resolve().parents[1]
TOOLS = {"workspace_status", "list_sources", "search_records", "get_record", "get_changes",
         "build_research_pack", "export_records", "list_datasets", "get_dataset", "compare_datasets", "build_review_packet"}


@unittest.skipUnless(HAS_MCP, "Install the optional pinned MCP SDK to run actual stdio acceptance")
class StdioAcceptance(unittest.TestCase):
    def test_both_protocols_preserve_contract_and_database(self):
        from mcp import Client, StdioServerParameters

        async def check(db: Path, mode: str, record_id: str):
            parameters = StdioServerParameters(command=sys.executable,
                args=["-B", "-m", "finance_research_hub.mcp_server", "--db", str(db)],
                cwd=str(ROOT), env={"PYTHONDONTWRITEBYTECODE": "1"})
            async with Client(parameters, mode=mode, read_timeout_seconds=15) as client:
                self.assertEqual(client.protocol_version, "2026-07-28" if mode == "auto" else "2025-11-25")
                tools = (await client.list_tools()).tools
                self.assertEqual({tool.name for tool in tools}, TOOLS)
                for tool in tools:
                    self.assertTrue(tool.annotations.read_only_hint)
                    self.assertFalse(tool.annotations.open_world_hint)

                async def call(name, arguments, error=False):
                    result = await client.call_tool(name, arguments)
                    self.assertEqual(result.is_error, error, (name, result))
                    self.assertIsInstance(result.structured_content, dict, (name, arguments, result))
                    self.assertEqual(result.structured_content["risk_notice"], RISK_NOTICE)
                    self.assertTrue(result.structured_content["noncommercial"])
                    self.assertTrue(any(RISK_NOTICE in part.text for part in result.content if part.type == "text"))
                    return result.structured_content

                search = await call("search_records", {"q": "", "limit": 10})
                self.assertEqual(search["count"], 4)
                self.assertEqual((await call("workspace_status", {}))["network_enabled"], False)
                self.assertTrue((await call("list_sources", {}))["sources"])
                record = await call("get_record", {"record_id": record_id})
                self.assertIn(record_id, json.dumps(record))
                changes = await call("get_changes", {"record_id": record_id})
                self.assertTrue(all(x["item_id"] == record_id for x in changes["items"]))
                pack = await call("build_research_pack", {"symbol": "DEMO-CN", "limit": 10})
                self.assertEqual(pack["count"], 1)
                self.assertTrue(pack["chunks"])
                for chunk in pack["chunks"]:
                    self.assertIn(RISK_NOTICE, chunk["content"])
                dataset_list = await call("list_datasets", {})
                self.assertEqual(dataset_list["count"], 2)
                identifiers = [item["id"] for item in dataset_list["items"]]
                exact_dataset = await call("get_dataset", {"dataset_id": identifiers[0]})
                self.assertTrue(exact_dataset["dataset"]["rows"])
                for row in exact_dataset["dataset"]["rows"]:
                    self.assertEqual(row["risk_notice"], RISK_NOTICE)
                compared = await call("compare_datasets", {"dataset_ids": identifiers})
                self.assertEqual(len(compared["curves"]), 2)
                self.assertEqual(compared["curves"][0]["points"][0]["indexed_value"], 100)
                self.assertFalse(compared["model_calls_performed"])
                packet = await call("build_review_packet", {"record_id": record_id, "dataset_ids": identifiers})
                self.assertTrue(packet["local_only"])
                self.assertFalse(packet["model_calls_performed"])
                self.assertEqual(packet["review_status"], "not_performed")
                self.assertEqual(packet["source_access"]["paid_media_collection"], "paused")
                self.assertEqual(len(packet["review_workflow"]["reviewers"]), 2)
                for chunk in packet["chunks"]:
                    self.assertIn(RISK_NOTICE, chunk["content"])
                for fmt in ["json", "jsonl", "csv", "markdown"]:
                    exported = await call("export_records", {"format": fmt, "q": "no-such-fixture", "limit": 10})
                    self.assertIn(RISK_NOTICE, exported["content"])
                for name, arguments in [
                    ("search_records", {"limit": 0}),
                    ("search_records", {"limit": "wrong-type"}),
                    ("search_records", {"limit": 101}),
                    ("get_record", {"record_id": "missing"}),
                    ("build_research_pack", {}),
                    ("export_records", {"format": "html"}),
                    ("get_dataset", {"dataset_id": "missing"}),
                    ("compare_datasets", {"dataset_ids": identifiers[:1]}),
                    ("build_review_packet", {}),
                    ("run_shell", {"command": "unused"}),
                ]:
                    await call(name, arguments, error=True)
                resources = (await client.list_resources()).resources
                self.assertEqual({str(x.uri) for x in resources}, {"finance://policy", "finance://catalog", "finance://schema", "finance://workspace-policy"})
                templates = (await client.list_resource_templates()).resource_templates
                self.assertEqual({x.uri_template for x in templates}, {"finance://records/{record_id}", "finance://datasets/{dataset_id}"})
                for uri in ["finance://policy", "finance://catalog", "finance://schema", "finance://workspace-policy", "finance://records/" + record_id, "finance://datasets/" + identifiers[0]]:
                    resource = await client.read_resource(uri)
                    self.assertTrue(any(RISK_NOTICE in part.text for part in resource.contents if hasattr(part, "text")))
                with self.assertRaises(Exception) as raised:
                    await client.read_resource("finance://unknown")
                self.assertIn(RISK_NOTICE, str(raised.exception))
                prompt = await client.get_prompt("research_prompt", {"topic": "DEMO-CN"})
                self.assertTrue(any(RISK_NOTICE in message.content.text for message in prompt.messages))
                cross_prompt = await client.get_prompt("cross_check_prompt", {"topic": "DEMO-CN"})
                self.assertTrue(any(RISK_NOTICE in message.content.text for message in cross_prompt.messages))

        with tempfile.TemporaryDirectory(prefix="financial-hub-mcp-test-") as temporary:
            db = Path(temporary) / "synthetic.sqlite3"
            with Store(db) as store:
                store.ingest(demo_records())
                for dataset in demo_datasets():
                    store.import_dataset(dataset)
                record_id = store.query(kind="research")[0]["id"]
            before = hashlib.sha256(db.read_bytes()).hexdigest()
            for mode in ["auto", "legacy"]:
                with self.subTest(mode=mode):
                    asyncio.run(asyncio.wait_for(check(db, mode, record_id), timeout=60))
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before)
            self.assertEqual(list(Path(temporary).iterdir()), [db])

    def test_missing_database_never_creates_state_or_writes_stdout(self):
        with tempfile.TemporaryDirectory(prefix="financial-hub-mcp-missing-") as temporary:
            db = Path(temporary) / "absent.sqlite3"
            result = subprocess.run([sys.executable, "-B", "-m", "finance_research_hub.mcp_server", "--db", str(db)],
                cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn(RISK_NOTICE, result.stderr)
            self.assertFalse(db.exists())


if __name__ == "__main__":
    unittest.main()
