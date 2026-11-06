"""Exercise both protocol eras against an existing synthetic stdio workspace.

This helper does not install packages, register a host, collect sources, scan
processes or kill a process. It uses one private process-factory hook from the
exact pinned SDK solely to observe the owned child's shutdown. The public
Client API does not expose a process handle. Keep this instrumentation out of
ordinary host integrations.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import sys
from typing import Any
from unittest.mock import patch


RISK_NOTICE = "投资有风险，分析结果和查询结果不构成投资建议。"
SDK_VERSION = "2.3.0"
SDK_COMMIT = "2118f14f8a19bc158d8a1cf90af58d85d187f849"
TOOLS = {
    "workspace_status", "list_sources", "search_records", "get_record",
    "get_changes", "build_research_pack", "export_records",
    "list_datasets", "get_dataset", "compare_datasets", "build_review_packet",
}
RESOURCES = {"finance://policy", "finance://catalog", "finance://schema", "finance://workspace-policy"}
TEMPLATES = {"finance://records/{record_id}", "finance://datasets/{dataset_id}"}
PROMPTS = {"research_prompt", "cross_check_prompt"}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def tool_payload(result: Any, *, error: bool = False) -> dict[str, Any]:
    data = result.structured_content
    text = "\n".join(block.text for block in result.content if block.type == "text")
    check(isinstance(data, dict), "Expected an object in structured_content")
    check(data.get("risk_notice") == RISK_NOTICE, "Structured risk notice is missing")
    check(data.get("noncommercial") is True, "Noncommercial flag is missing")
    check(RISK_NOTICE in text, "Model-readable text risk notice is missing")
    check(bool(result.is_error) is error, "Unexpected tool error status")
    return data


async def expect_error(call: Any) -> None:
    try:
        result = await call
    except Exception as exc:
        check(RISK_NOTICE in str(exc), "Protocol error omitted the risk notice")
    else:
        tool_payload(result, error=True)


async def exercise(mode: str, python: str, repo: Path, database: Path) -> dict[str, Any]:
    from mcp import Client, StdioServerParameters

    stdio = importlib.import_module("mcp.client.stdio")
    spawn = stdio._create_platform_compatible_process
    owned = []
    receipt: dict[str, Any] = {"mode": mode, "checks": [], "errors": []}

    async def capture_owned_process(*args: Any, **kwargs: Any) -> Any:
        process = await spawn(*args, **kwargs)
        owned.append(process)
        return process

    launch = StdioServerParameters(
        command=python,
        args=["-B", "-m", "finance_research_hub.mcp_server", "--db", str(database)],
        cwd=str(repo),
    )

    try:
        with patch.object(stdio, "_create_platform_compatible_process", capture_owned_process):
            async with Client(launch, mode=mode, read_timeout_seconds=10) as client:
                expected = "2026-07-28" if mode == "auto" else "2025-11-25"
                check(client.protocol_version == expected, "Unexpected negotiated protocol version")
                receipt["protocol_version"] = client.protocol_version
                receipt["checks"].append("actual_stdio_protocol_negotiation")

                tools = (await client.list_tools()).tools
                check({tool.name for tool in tools} == TOOLS, "Unexpected tool surface")
                for tool in tools:
                    check(tool.annotations is not None and tool.annotations.read_only_hint is True,
                          f"{tool.name} lacks a read-only annotation")
                    check(tool.annotations.open_world_hint is False,
                          f"{tool.name} lacks a closed-world annotation")
                receipt["checks"].append("eleven_read_only_tools")

                status = tool_payload(await client.call_tool("workspace_status", {}))
                check(status.get("record_count", 0) > 0 and
                      status.get("record_count") == status.get("demo_record_count"),
                      "Acceptance requires a dedicated database containing only synthetic records")
                check(status.get("dataset_count", 0) >= 2 and
                      status.get("dataset_count") == status.get("demo_dataset_count"),
                      "Seed a dedicated synthetic database with the current demo command; two demo datasets are required")
                tool_payload(await client.call_tool("list_sources", {}))

                search = tool_payload(await client.call_tool("search_records", {"limit": 100}))
                records = search.get("items", [])
                check(bool(records), "Seed an existing synthetic demo database before running acceptance")
                check(all(item.get("is_demo") is True for item in records),
                      "Acceptance only permits synthetic search results")
                for item in records:
                    check(item.get("risk_notice") == RISK_NOTICE, "Record notice is missing")
                record_id = records[0]["id"]
                receipt["synthetic_records_returned"] = len(records)
                receipt["checks"].append("structured_text_and_record_notices")

                exact = tool_payload(await client.call_tool("get_record", {"record_id": record_id}))
                check(any(item.get("id") == record_id for item in exact.get("items", [])),
                      "Exact-record lookup did not return the selected record")
                history = tool_payload(await client.call_tool("get_changes", {"record_id": record_id}))
                check(all(item.get("item_id") == record_id for item in history.get("items", [])),
                      "Scoped change history returned another record")
                pack = tool_payload(await client.call_tool("build_research_pack", {"record_id": record_id}))
                for chunk in pack.get("chunks", []):
                    check(chunk.get("risk_notice") == RISK_NOTICE and RISK_NOTICE in chunk.get("content", ""),
                          "Research-pack chunk omitted the notice")
                tool_payload(await client.call_tool("export_records", {"format": "jsonl"}))
                receipt["checks"].append("exact_record_scoped_history_pack_and_export")

                directory = tool_payload(await client.call_tool("list_datasets", {"limit": 100}))
                datasets = directory.get("items", [])
                check(len(datasets) >= 2 and all(item.get("is_demo") is True for item in datasets),
                      "Run the current demo command in a dedicated synthetic database before acceptance")
                identifiers = [item["id"] for item in datasets[:2]]
                for item in datasets:
                    check(item.get("risk_notice") == RISK_NOTICE, "Dataset directory notice is missing")
                    check(len(item.get("rows_preview", [])) <= 5, "Dataset preview exceeded its row limit")
                for identifier in identifiers:
                    result = tool_payload(await client.call_tool("get_dataset", {"dataset_id": identifier}))
                    dataset = result.get("dataset")
                    check(isinstance(dataset, dict) and dataset.get("id") == identifier,
                          "Exact dataset lookup returned another dataset")
                    check(dataset.get("is_demo") is True and bool(dataset.get("rows")),
                          "Acceptance requires nonempty synthetic saved datasets")
                    fingerprint = dataset.get("content_hash", "")
                    check(isinstance(fingerprint, str) and len(fingerprint) == 64 and
                          all(character in "0123456789abcdef" for character in fingerprint),
                          "Exact dataset omitted its saved payload fingerprint")
                    check(bool(dataset.get("hash_basis")), "Dataset fingerprint basis is missing")
                    for row in dataset["rows"]:
                        check(row.get("risk_notice") == RISK_NOTICE and row.get("noncommercial") is True,
                              "Saved dataset row omitted a policy field")
                    for chunk in result.get("chunks", []):
                        check(chunk.get("risk_notice") == RISK_NOTICE and RISK_NOTICE in chunk.get("content", ""),
                              "Exact dataset chunk omitted its notice")
                compared = tool_payload(await client.call_tool("compare_datasets", {"dataset_ids": identifiers}))
                check(len(compared.get("curves", [])) == 2, "Comparison did not return both saved series")
                check(compared.get("model_calls_performed") is False, "Comparison claimed a model call")
                for curve in compared["curves"]:
                    check(curve.get("points", [{}])[0].get("indexed_value") == 100,
                          "Indexed curve did not start at 100")
                    for point in curve.get("points", []):
                        check(point.get("risk_notice") == RISK_NOTICE,
                              "Comparison point omitted its notice")
                packet = tool_payload(await client.call_tool("build_review_packet", {
                    "record_id": record_id, "dataset_ids": identifiers,
                    "question": "What does the saved synthetic evidence support?",
                }))
                check(packet.get("local_only") is True and packet.get("model_calls_performed") is False,
                      "Review packet did not preserve the unexecuted local-only state")
                check(packet.get("review_status") == "not_performed", "Packet claimed a completed review")
                check(packet.get("source_access", {}).get("paid_media_collection") == "paused",
                      "Packet did not preserve the paid-media hold")
                reviewers = packet.get("review_workflow", {}).get("reviewers", [])
                check(len(reviewers) == 2 and all(item.get("model_id") is None and
                      item.get("status") == "not_started" for item in reviewers),
                      "Packet did not preserve two unselected, unstarted reviewers")
                for chunk in packet.get("chunks", []):
                    check(chunk.get("risk_notice") == RISK_NOTICE and RISK_NOTICE in chunk.get("content", ""),
                          "Review packet chunk omitted its notice")
                receipt["synthetic_datasets_returned"] = len(datasets)
                receipt["checks"].append("exact_datasets_hashes_rows_comparison_and_unexecuted_review_packet")

                resources = (await client.list_resources()).resources
                check({str(resource.uri) for resource in resources} == RESOURCES,
                      "Unexpected fixed resource surface")
                templates = (await client.list_resource_templates()).resource_templates
                check({str(item.uri_template) for item in templates} == TEMPLATES,
                      "Unexpected exact-record/dataset resource template surface")
                for uri in sorted(RESOURCES) + [f"finance://records/{record_id}", f"finance://datasets/{identifiers[0]}"]:
                    result = await client.read_resource(uri)
                    text = "\n".join(item.text for item in result.contents if hasattr(item, "text"))
                    check(RISK_NOTICE in text, "Resource text omitted the notice")
                    if uri == "finance://workspace-policy":
                        policies = [json.loads(item.text) for item in result.contents if hasattr(item, "text")]
                        check(any(item.get("policy", {}).get("paid_media_collection") == "paused" and
                                  item.get("policy", {}).get("review_workflow", {}).get("local_only") is True
                                  for item in policies), "Workspace policy resource omitted inherited boundaries")
                prompts = (await client.list_prompts()).prompts
                check({item.name for item in prompts} == PROMPTS, "Unexpected prompt surface")
                for name in sorted(PROMPTS):
                    prompt = await client.get_prompt(name, {"topic": "synthetic research workflow"})
                    text = "\n".join(message.content.text for message in prompt.messages
                                     if message.content.type == "text")
                    check(RISK_NOTICE in text, "Research/cross-check prompt omitted the notice")
                receipt["checks"].append("four_fixed_resources_two_templates_two_prompts_and_policy")

                for name, arguments in (
                    ("unknown_tool", {}),
                    ("search_records", {"limit": 101}),
                    ("search_records", {"limit": "invalid integer"}),
                    ("get_record", {"record_id": "not-a-saved-record"}),
                    ("get_dataset", {"dataset_id": "not-a-saved-dataset"}),
                    ("compare_datasets", {"dataset_ids": identifiers[:1]}),
                    ("build_review_packet", {}),
                ):
                    await expect_error(client.call_tool(name, arguments))
                await expect_error(client.read_resource("finance://unknown"))
                receipt["checks"].append("noticed_error_paths")
    except Exception as exc:
        receipt["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        receipt["process_observation"] = {
            "method": "private process-factory instrumentation in the exact pinned SDK",
            "scope": "only process objects created by this Client context; no scan or explicit kill",
            "children": [{"pid": process.pid, "returncode": process.returncode} for process in owned],
        }
        if len(owned) != 1 or any(process.returncode is None for process in owned):
            receipt["errors"].append("The exact owned child's exit was not confirmed")
        elif any(process.returncode != 0 for process in owned):
            receipt["errors"].append("The exact owned child exited with a nonzero return code")
        else:
            receipt["checks"].append("exact_owned_child_exit_observed")
    receipt["passed"] = not receipt["errors"]
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, epilog=RISK_NOTICE)
    parser.add_argument("--db", required=True, help="Existing dedicated synthetic database; no directory is created")
    parser.add_argument("--python", default=sys.executable, help="Interpreter containing the pinned MCP extra")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    try:
        check(version("mcp") == SDK_VERSION, "Install the exact project MCP extra before running this helper")
        database = Path(args.db).expanduser().resolve(strict=True)
        repo = Path(args.repo).expanduser().resolve(strict=True)
        check(database.is_file(), "An existing database file is required")
        before = hashlib.sha256(database.read_bytes()).hexdigest()

        async def both() -> list[dict[str, Any]]:
            return [await exercise(mode, args.python, repo, database) for mode in ("auto", "legacy")]

        receipts = asyncio.run(both())
        after = hashlib.sha256(database.read_bytes()).hexdigest()
        passed = all(item["passed"] for item in receipts) and before == after
        print(json.dumps({
            "risk_notice": RISK_NOTICE, "noncommercial": True,
            "sdk_version": SDK_VERSION, "sdk_commit": SDK_COMMIT,
            "receipts": receipts, "database_sha256_unchanged": before == after,
            "global_registration": False, "live_acquisition": False, "passed": passed,
        }, ensure_ascii=False, indent=2))
        return 0 if passed else 1
    except (AssertionError, PackageNotFoundError, OSError, ValueError) as exc:
        print(json.dumps({"risk_notice": RISK_NOTICE, "noncommercial": True,
                          "passed": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

