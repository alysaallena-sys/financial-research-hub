# MCP integration

**投资有风险，分析结果和查询结果不构成投资建议。**

Investing involves risk. Analysis and query results do not constitute investment advice.

The MCP adapter gives a compatible host read-only access to this workspace's saved metadata. It shares the research workflow with the CLI and local page. It does not collect live information, download reports, run a model, send notifications or execute trades.

The project's [noncommercial license](../LICENSE) and [editor contract](../integrations/editor-contract.json) apply. A host must visibly display the Chinese risk notice with query and analysis results. Returning the notice over MCP does not technically force an unrelated host to render it.

## Install the optional adapter

Use a dedicated Python environment. The base application remains usable without the MCP dependency.

```sh
python -m pip install '.[mcp]'
```

The optional extra pins the official Python SDK to `mcp==2.3.0`. The SDK's `cli` extra and the Node-based Inspector are not required for a stdio connection.

The audited release is [v2.3.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0), published on 2026-10-02. Its tag resolves to [`2118f14f8a19bc158d8a1cf90af58d85d187f849`](https://github.com/modelcontextprotocol/python-sdk/tree/2118f14f8a19bc158d8a1cf90af58d85d187f849). The SDK uses MIT; this project's original code keeps its own noncommercial license.

## Start a local stdio server

Prepare a separate synthetic workspace first:

```sh
python -m finance_research_hub --db .local/demo.sqlite3 demo
python -m finance_research_hub.mcp_server --db .local/demo.sqlite3
```

The second command waits for an MCP host on stdin. It does not start an HTTP listener. A host normally launches this command itself; do not run a second copy and expect the host to attach to it.

Use an absolute database path in a host configuration. The database must already exist. MCP opens SQLite in read-only `mode=ro`; it does not create the database, run DDL or change records. The launch configuration selects the database; model-supplied tool arguments cannot select an arbitrary file or database. Keep the database private and outside the public Git file set.

Stdout is the JSON-RPC transport. Do not add a startup banner or import-time print. Diagnostics belong on stderr. The required risk notice belongs in result content and structured data, not only in a log or hidden `_meta` field.

## Read-only interface

| Tool | Purpose |
| --- | --- |
| `workspace_status` | Read saved-workspace counts, mode and limits |
| `list_sources` | Inspect source adapters and saved coverage information |
| `search_records` | Filter saved records by metadata, with a maximum of 100 returned records |
| `get_record` | Read one exact saved record by its stable ID |
| `get_changes` | Read saved changes, including history scoped to a record |
| `build_research_pack` | Assemble a source-linked research pack from saved metadata |
| `export_records` | Return an export payload without writing an arbitrary output file |

Search and export windows are bounded to 100 records through MCP. A research pack selects at most 100 records and may also retain one separate exact anchor when the selected filter excludes it. Its history scope can therefore contain up to 101 record IDs; the history result has its own bounded limit. Counts and truncation markers describe each window, not a guarantee about the full source universe.

The interface has no acquisition, shell, arbitrary URL, arbitrary file, PDF, model, notification or trading tool. `read_only_hint` annotations describe this behavior; annotations alone are not an access-control mechanism.

SQLite opens the existing database with `mode=ro`. The adapter skips schema changes and rejects ingestion. Search streams candidates through a bounded top-N heap rather than loading the full result table. Read-only database work has a cooperative five-second deadline through SQLite progress callbacks and Python scan checks. This is a database-read limit, not a hard bound on host rendering or total response serialization time.

Resources provide application-selected context:

- `finance://policy`: risk, noncommercial and use boundaries.
- `finance://catalog`: available information types and source metadata.
- `finance://schema`: record and output contracts.
- `finance://records/{record_id}`: a resource template for an exact saved record.

The `research_prompt(topic)` prompt supplies a user-selected research workflow. It must retain the risk notice and distinguish published facts, institutional opinions and generated inference. It does not call a model or acquire source content.

## What a host can read

The adapter returns selected saved metadata: titles, links, providers, institutions, publication and retrieval times, summaries, changes, coverage markers and explicitly labeled synthetic examples. Source-dependent fields remain source-dependent. It does not grant access to the rest of the filesystem, browser sessions, credentials or other knowledge bases.

All tool results retain the risk notice in model-readable text and in the structured object. Record and retrieval-chunk notices remain intact. Source failure, missing fields, bounded results and demo labels must survive a handoff to the host.

A report-list record is not full report text. A rating change is not the institution's full reasoning. A research pack organizes the available evidence; it does not establish that a prediction is correct or provide an investment recommendation.

Live acquisition remains a separate, explicit CLI action using `collect --live`. Read [source coverage](COVERAGE.md) and [source terms](SOURCES.md) before collecting. Source credentials, paid databases and client registrations are not configured by the MCP adapter.

## Host configuration template

Copy values from [the stdio example](../integrations/mcp-stdio.example.json) into the configuration mechanism your chosen host supports. Replace the placeholder interpreter and database paths with reviewed local paths. The interpreter must belong to the environment where the project and its MCP extra are installed.

The example uses the common `mcpServers` container. Host products use different configuration schemas, paths and approval flows. It is a template, not proof of acceptance in every product. This project does not write global host configuration or register a client automatically.

## Protocol compatibility

The pinned SDK's [version registry](https://github.com/modelcontextprotocol/python-sdk/blob/2118f14f8a19bc158d8a1cf90af58d85d187f849/src/mcp-types/mcp_types/version.py) lists both protocol eras:

| SDK client mode | Negotiation | Expected version with this server |
| --- | --- | --- |
| `auto` | Probe `server/discover`; fall back to the legacy handshake for an older server | `2026-07-28` |
| `legacy` | Use `initialize` and `notifications/initialized` | `2025-11-25` |

The 2026 protocol carries version and capability metadata with each request. It removes the legacy initialization handshake. The SDK handles both paths; application code should not implement a second JSON-RPC stack.

Keep result objects compatible with both eras. In particular, return a JSON object for structured content. The 2026 specification permits broader JSON values, while earlier structured-output contracts are more restrictive. Python uses the property name `structured_content`; the wire uses `structuredContent`.

Do not use `mode="2026-07-28"` as a negotiation test. A version pin adopts that version without probing, and it does not discover server identity. The [official negotiation guide](https://github.com/modelcontextprotocol/python-sdk/blob/2118f14f8a19bc158d8a1cf90af58d85d187f849/docs/protocol-versions.md) explains this distinction.

## Repeatable SDK-client acceptance

Run the example against a dedicated database containing synthetic demo records:

```sh
python -m finance_research_hub --db .local/demo.sqlite3 demo
python integrations/mcp_client_acceptance.py --db .local/demo.sqlite3
```

The script launches the actual stdio server separately for `auto` and `legacy`. It checks discovery, tools, structured and text notices, resources, a record resource, a prompt and handled error paths. It rejects non-demo search results and compares the chosen database's hash before and after both runs. It does not create a directory, collect live data, register a host or modify a global client configuration.

The SDK's public `Client` API does not expose a process handle. This acceptance helper therefore wraps one private process-factory function from the exact pinned SDK solely to retain the owned child process object and observe its return code after context exit. It performs no process scan and does not kill a process itself. This is version-pinned test instrumentation, not a host-integration API.

An SDK stdio pass demonstrates that transport and interface under the tested SDK. It does not prove that an external editor installed the server, approved it, selected the same database or displayed the required notice. Check those actions in the target host separately. Record actual results in [acceptance scope](ACCEPTANCE.md).

The local MCP-specific unittest run on 2026-11-06 passed two cases covering actual child stdio connections in both protocol modes. It checked text and structured notices, error paths, database hash preservation and missing-database refusal. The complete suite, the standalone helper and any external-editor display require their own recorded results.

## Official implementation references

- [Pinned `MCPServer` constructor and serving API](https://github.com/modelcontextprotocol/python-sdk/blob/2118f14f8a19bc158d8a1cf90af58d85d187f849/src/mcp/server/mcpserver/server.py)
- [Pinned stdio client example](https://github.com/modelcontextprotocol/python-sdk/blob/2118f14f8a19bc158d8a1cf90af58d85d187f849/docs_src/client_transports/tutorial004.py)
- [Pinned tool annotations](https://github.com/modelcontextprotocol/python-sdk/blob/2118f14f8a19bc158d8a1cf90af58d85d187f849/docs_src/tools/tutorial005.py)
- [Pinned output conversion](https://github.com/modelcontextprotocol/python-sdk/blob/2118f14f8a19bc158d8a1cf90af58d85d187f849/src/mcp/server/mcpserver/utilities/func_metadata.py#L186-L226)
- [2026-07-28 protocol changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [2025-11-25 specification](https://modelcontextprotocol.io/specification/2025-11-25)

