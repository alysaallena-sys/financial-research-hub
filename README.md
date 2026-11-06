# Financial Research Hub

**投资有风险，分析结果和查询结果不构成投资建议。**

Investing involves risk. Analysis and query results do not constitute investment advice.

**Noncommercial use only.** The original software and documentation use the custom [Financial Research Hub Noncommercial License 1.0](LICENSE). You may inspect the source, conduct noncommercial research, modify the project and share it under those terms. Commercial use requires separate written permission from the relevant copyright holders. This is a source-available project; it does not claim an OSI-approved open-source license.

Bring public news, TED entries, broker-report metadata and overseas analyst-rating events into one local research workspace. Preserve sources and dates, compare new and updated records, and export material with its risk notice for personal research.

The [canonical finance workspace requirements](docs/FINANCE-WORKSPACE.md) connect the source catalog, evidence rules, numerical-workbench plan and local review workflow. The packaged [workspace policy](finance_research_hub/workspace-policy.json) is the machine-readable source for those boundaries and the research-navigation catalog. A navigation entry does not activate a collector or grant data-use rights.

The bundled interface currently uses Simplified Chinese. Repository documentation is English-first. The required Chinese risk notice remains unchanged in the interface and output contract.

![The workspace running in Safari; all content shown is synthetic demo data](docs/images/demo-workspace.png)

## Features

| Information | Initial scope |
| --- | --- |
| Public news and TED | Titles, links, publication dates and short summaries from fixed public RSS/Atom sources |
| Chinese broker research | Eastmoney metadata for stock, industry, macro, strategy and broker morning reports |
| Overseas analyst ratings | Yahoo-aggregated rating events through the optional yfinance adapter |
| Change history | Local SQLite snapshots that distinguish first observation, new records, updates and unchanged records |
| Search and briefs | Filters for type, source, symbol and keywords, plus source-linked metadata briefs |
| Connected research | Exact record lookup, scoped history, provenance, coverage and retrieval chunks in one research pack |
| Typed numerical evidence | Local JSON imports, exact datasets, explicit record/topic links and compatible price/NAV comparisons |
| Local review handoff | Source-linked evidence packets and separate first-review/challenge instructions; no model calls |
| Knowledge-base exports | JSON, CSV, Markdown and retrieval chunks that retain risk notices, sources and demo labels |
| Read-only MCP | Eleven tools, policy/catalog/schema resources, exact-record/dataset templates and research/cross-check prompts over one existing local database |

Available report fields depend on the selected interface. A report-list record does not contain the report's full text. A rating event does not contain an investment bank's complete reasoning. Programs that share Eastmoney or Yahoo still share the same direct data provider.

## Quick start with synthetic data

Use Python 3.11 or later. The base application uses the Python standard library and does not require a model account or a data API key.

Clone the repository and start the demo:

```sh
git clone https://github.com/alysaallena-sys/financial-research-hub.git
cd financial-research-hub
python -m finance_research_hub --db .local/demo.sqlite3 demo
python -m finance_research_hub --db .local/demo.sqlite3 serve --demo --port 8765
```

Open the [local workspace](http://127.0.0.1:8765). All demo entries are synthetic. They do not represent actual news, institutional opinions or current market data.

The server binds to the local loopback address. It does not publish the page to the internet. These commands keep demo records in `.local/demo.sqlite3`, separate from the default `.local/research.sqlite3`. Press `Ctrl+C` in the server's terminal to stop it.

## Search, briefs and exports

```sh
python -m finance_research_hub --db .local/demo.sqlite3 query --kind research
python -m finance_research_hub --db .local/demo.sqlite3 brief
python -m finance_research_hub --db .local/demo.sqlite3 export --format markdown
python -m finance_research_hub --db .local/demo.sqlite3 export --format csv
python -m finance_research_hub --db .local/demo.sqlite3 export --format json
python -m finance_research_hub --db .local/demo.sqlite3 export --format jsonl
```

Use `python -m finance_research_hub --help` and each subcommand's help for the current options. Omitting `--db` selects `.local/research.sqlite3`. JSON includes records and retrieval chunks with notices; JSONL emits one chunk per line. Empty JSONL and CSV exports still contain one `record_type: notice` entry. It is a notice, not a research item; importers must distinguish the types. Search and export read the local database without starting collection, model calls or PDF downloads.

To bring reviewed metadata from another permitted export into this workspace, use an explicit current-schema JSON file:

```sh
python -m finance_research_hub --db .local/research.sqlite3 import-records /absolute/path/to/reviewed-records.json
```

The input is an array of records or an object with an `items` array, bounded to 2 MiB and 1,000 records. The importer validates the batch before writing. It preserves source identity and publication dates; a missing original retrieval time remains `unknown`. It does not scan another database, map a legacy catalog or resume its collector. See the [integration contract](docs/FINANCE-WORKSPACE.md#explicit-record-interchange).

## Connected research workflow

Search saved metadata, select an exact record, inspect its own changes, and build a pack containing sources, coverage, missing information and notice-preserving retrieval chunks. Replace `RECORD_ID` below with an actual stable ID returned by the query:

```sh
python -m finance_research_hub --db .local/demo.sqlite3 query --kind research
python -m finance_research_hub --db .local/demo.sqlite3 record RECORD_ID --history-limit 20
python -m finance_research_hub --db .local/demo.sqlite3 pack --record-id RECORD_ID --limit 20 --history-limit 20
```

You can also select a pack with an exact `--symbol` or literal `--q`. Matching metadata establishes the selection rule, not a causal connection or independent corroboration. An untagged anchor stays anchor-only unless you explicitly supply a topic. See the [coverage matrix](docs/COVERAGE.md).

Research must distinguish source facts, institutional opinions and generated inference. Numerical claims need deterministic calculations with dates, units, currency, adjustment and method. Cross-checking requires two independent local review passes over the same evidence. A generated review packet or prompt does not mean either model ran; the project does not activate a cloud model or transmit private material through an external site's question URL.

In the page's research workflow, the JSON pack export retains provenance, history, coverage and retrieval chunks. The Markdown option exports a material summary containing entries and summaries; it does not contain the complete pack. Its filename is `research-summary-YYYY-MM-DD.md`, while the JSON pack uses `research-pack-YYYY-MM-DD.json`.

## Saved datasets and numerical review

The numerical extension keeps typed datasets in the same SQLite workspace, separately from news/report records. Import only a reviewed local JSON file. The command does not collect a source:

```sh
python -m finance_research_hub --db .local/research.sqlite3 import-dataset /absolute/path/to/reviewed-dataset.json
python -m finance_research_hub --db .local/demo.sqlite3 datasets
python -m finance_research_hub --db .local/demo.sqlite3 dataset DATASET_ID
python -m finance_research_hub --db .local/demo.sqlite3 compare DATASET_A DATASET_B --alignment strict
python -m finance_research_hub --db .local/demo.sqlite3 review-packet --q synthetic --dataset-id DATASET_A --dataset-id DATASET_B
```

Replace dataset placeholders with exact saved IDs. `demo` includes two synthetic daily series. Comparisons require two to five compatible saved price/NAV series and calculate an index starting at 100, observed-period return and sampled maximum drawdown. Explicit `intersection` alignment may remove dates; retain the reported method and exclusions. No FX, interpolation, dividend reinvestment or annualization occurs.

The [canonical guide](docs/FINANCE-WORKSPACE.md#typed-datasets-in-the-existing-workspace) specifies the import schema, immutable snapshot identity, row limits, preview limits, missing-value rules, comparison bases and unexecuted local-review packet. Local version 0.3.0 acceptance passed 95 tests, both actual SDK stdio modes, twelve read-only HTTP checks over imported non-demo datasets, and Safari chart/navigation checks at desktop and narrower viewports. Review-packet Blob content was inspected with the physical download suppressed. See the [acceptance scope](docs/ACCEPTANCE.md) for limits; no model execution or physical-iPad acceptance is claimed.

## Connect through MCP

The optional adapter uses the official Python SDK, pinned to `mcp==2.3.0`:

```sh
python -m pip install '.[mcp]'
python -m finance_research_hub.mcp_server --db .local/demo.sqlite3
```

The MCP host normally launches the second command. Stdio uses stdin/stdout, not an HTTP port. The database must already exist; MCP opens SQLite with `mode=ro` and cannot create tables, change records or acquire live sources. It offers saved-workspace search, exact records, scoped changes, research packs and exports, with the risk notice in both text and structured results.

Local version 0.3.0 SDK acceptance passed the eleven-tool interface in both `auto` (`2026-07-28`) and `legacy` (`2025-11-25`) modes. Both exact owned child processes exited with code 0, and the synthetic database hash remained unchanged. This does not establish acceptance in an arbitrary editor or prove that its UI displays the notice. Read the [MCP guide](docs/MCP.md), review the [host configuration example](integrations/mcp-stdio.example.json), and use the [SDK-client acceptance helper](integrations/mcp_client_acceptance.py) with a dedicated synthetic database. No global client registration is performed.

## Optional live metadata collection

Collection requires an explicit `--live` flag. Review the [source notes](docs/SOURCES.md) before choosing a source that permits your intended use. These examples show entry points. The bounded source checks described below do not establish complete or ongoing coverage:

```sh
python -m finance_research_hub collect --source bbc --live
python -m finance_research_hub collect --source guardian --live
python -m finance_research_hub collect --source ted --live
python -m finance_research_hub collect --source eastmoney --symbol 600519 --live
```

Report types are `stock`, `industry`, `strategy`, `macro` and `morning`. Use `--symbol` for a stock and `--industry` for an industry. Set `--begin` and `--end` to make the date range explicit. Bound the request with `--max-pages` and `--page-size`. The default range is the past seven days, with a hard limit of 10 pages and 100 entries per page. Results retain coverage and truncation information.

```sh
python -m finance_research_hub collect --source eastmoney --report-type macro --begin 2026-01-01 --end 2026-01-07 --max-pages 1 --page-size 20 --live
```

The fixed dates above are parameter examples. They do not establish complete data for that period.

Install the optional dependency explicitly before using the overseas ratings adapter:

```sh
python -m pip install '.[ratings]'
python -m finance_research_hub collect --source yahoo --symbol AAPL --live
```

Dependency installation connects to a package source. Live collection connects to the selected provider. Requests have timeout, pagination or quantity limits. Read the returned coverage information; a bounded page set does not establish a complete history.

If Python's CA configuration is incomplete and the system `curl` can verify the source certificate, select the system transport explicitly:

```sh
python -m finance_research_hub collect --source bbc --transport curl --live
```

This option applies only to RSS and Eastmoney adapters. It keeps HTTPS certificate validation and checks each redirect against the source allowlist. It does not disable certificate checks or change system trust settings. yfinance uses its own network implementation and rejects this override.

Bounded checks on 2026-11-06 retrieved BBC and Guardian feed metadata and one page of Eastmoney report metadata. The official TED redirect chain was checked, but the final network request failed; TED collection remains unverified. The optional overseas ratings dependency has not received runtime acceptance. See the [acceptance scope](docs/ACCEPTANCE.md).

The project does not bundle paid report databases, collect paid media, download report PDFs, execute trades, or automatically run models, notifications or scheduled jobs. Preserve a source-access failure as a failure. Do not bypass source restrictions.

The paid-media hold includes WSJ and supersedes the earlier daily three-Opinion analysis idea. Koyfin remains a market-workbench and contextual-research reference; it is not an approved data API. AKTools, efinance, Fincept and DBX retain separate candidate and acceptance states in the [integration map](docs/FINANCE-WORKSPACE.md). Their presence in the catalog does not install them or configure an account.

## Editor, agent and knowledge-base integration

**Every integration that uses this project to build a knowledge base must make the editor visibly display this exact Chinese notice with query and analysis results:**

> 投资有风险，分析结果和查询结果不构成投资建议。

Retain the same notice in every record, retrieval chunk and export. Hidden metadata, a license page alone, or a one-time dialog does not satisfy the integration conditions.

- Machine-readable contract: [integrations/editor-contract.json](integrations/editor-contract.json)
- Integration and acceptance steps: [integrations/editor-instructions.md](integrations/editor-instructions.md)
- Project agent rules: [AGENTS.md](AGENTS.md)
- Inherited finance requirements and current evidence: [docs/FINANCE-WORKSPACE.md](docs/FINANCE-WORKSPACE.md)

The bundled page, CLI and export paths implement notice retention. This repository cannot technically force an unrelated editor to follow the rules. External integrators must check the final display and must not claim compliance before that check passes.

## Data and privacy

Keep local databases, logs, credentials, live collection results and acquired original reports out of the public repository. `.gitignore` excludes common local state; still inspect the actual file list before publishing. The public repository contains code, documentation, tests and clearly labeled synthetic examples.

Distinguish the original publishing institution from the direct data provider. Retain publication time, retrieval time and coverage status. Public access does not by itself authorize bulk storage or redistribution. A software license does not replace the terms governing data, articles or research reports.

## Validation and contributions

```sh
python -B -m unittest discover -s tests -v
```

Offline tests use synthetic inputs without calling live financial interfaces, invoking models or downloading reports. GitHub Actions runs the same test entry point with read-only repository permissions. A passing workflow does not establish that a third-party interface is currently available.

The fixed version 0.3.0 functional commit [30e8d2087238bbee512f0826041eed1f2399506b](https://github.com/alysaallena-sys/financial-research-hub/commit/30e8d2087238bbee512f0826041eed1f2399506b) passed [Actions run 42263898429](https://github.com/alysaallena-sys/financial-research-hub/actions/runs/42263898429) on Python 3.11 and 3.13, including base tests, pinned SDK installation and actual stdio tests. All 42 published file blobs matched local Git hashes. This evidence applies to that functional commit; later documentation-only commits need their own CI readback. Physical iPad, external-editor display, actual local-model review and physical-download acceptance remain separate gaps.

Read the [acceptance scope](docs/ACCEPTANCE.md), [contribution rules](CONTRIBUTING.md) and [security notes](SECURITY.md). A new source needs documented coverage, rights boundaries, failure behavior and notice-retention checks.

## License and risk

[LICENSE](LICENSE) and [NOTICE](NOTICE) govern the project's original software and documentation. Third-party packages and data retain their own terms. The project does not guarantee complete, accurate or timely data, does not guarantee returns, and does not provide investment, legal or tax advice.

