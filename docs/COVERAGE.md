# Information and workflow coverage

**投资有风险，分析结果和查询结果不构成投资建议。**

Investing involves risk. Analysis and query results do not constitute investment advice.

This matrix separates acquisition, local research and MCP access. A connector's presence is not evidence of complete coverage, current availability or data-use rights. The [canonical workspace requirements](FINANCE-WORKSPACE.md) define inherited scope. See [source notes](SOURCES.md) and the versioned [acceptance record](ACCEPTANCE.md).

## Information sources

| Information | Explicit acquisition path | Saved scope | Live evidence recorded on 2026-11-06 |
| --- | --- | --- | --- |
| BBC Business | `collect --source bbc --live` | Feed metadata and short feed summaries | One bounded system-curl request returned 54 records |
| Guardian Business | `collect --source guardian --live` | Feed metadata and short feed summaries | One bounded system-curl request returned 20 records |
| TED | `collect --source ted --live` | Talk feed metadata, not video or transcript text | Official redirects checked; final request failed, so availability remains unverified |
| Eastmoney stock reports | `collect --source eastmoney --report-type stock --symbol ... --live` | Report-list metadata and source links | One historical company page returned five records; five total pages were reported and `truncated=true` |
| Eastmoney industry reports | `collect --source eastmoney --report-type industry --industry ... --live` | Bounded report-list metadata | Synthetic parsing and parameter tests only |
| Eastmoney macro, strategy and morning reports | Explicit `collect --source eastmoney --live` with report type `macro`, `strategy` or `morning` | Bounded report-list metadata | Synthetic parsing and parameter tests only |
| Yahoo rating events | `collect --source yahoo --symbol ... --live` with the ratings extra | Yahoo-aggregated rating history | Optional dependency and live call remain unverified |
| Synthetic demo | `demo` with a dedicated database | Clearly labeled examples for each information type | Local test and Safari evidence is recorded separately from live-source evidence |

The source counts above describe those requests. They do not promise a stable feed size, complete history or continuous updates. Default Python CA validation failed in the tested environment; explicit system curl retained certificate validation without changing system trust. The optional curl transport applies only to RSS and Eastmoney, not yfinance.

## Workflow surfaces

| Operation | CLI | Local page | MCP |
| --- | --- | --- | --- |
| Acquire public metadata | Explicit `collect --live` | No | No |
| Search saved metadata | Yes | Yes | `search_records` |
| Read an exact record | `record RECORD_ID` | Record details | `get_record` and `finance://records/{record_id}` |
| Read scoped change history | Research workspace | Changes view | `get_changes` |
| Inspect source and coverage status | `sources` | Sources view | `list_sources` and catalog resource |
| Build a source-linked research pack | `pack --record-id ...`, `--symbol ...` or `--q ...` | Research workflow | `build_research_pack` |
| Export selected material | JSON, JSONL, CSV and Markdown | Export controls | `export_records` returns content; it does not select an arbitrary output file |
| Read policy/schema | Project documentation | Risk and source information | `finance://policy` and `finance://schema` |
| Obtain research instructions | Documentation | Workflow guidance | `research_prompt(topic)` |
| Import reviewed current-schema metadata | `import-records FILE` only | No | No |
| Import a reviewed typed local dataset | `import-dataset FILE` only | No | No |
| List/read saved datasets | `datasets` and `dataset DATASET_ID` | Numerical workbench extension | `list_datasets`, `get_dataset` and exact-dataset resource template |
| Compare compatible price/NAV series | `compare DATASET_A DATASET_B ...` | Numerical workbench extension | `compare_datasets` |
| Prepare a local two-reviewer packet | `review-packet` | Numerical workbench extension | `build_review_packet` and `cross_check_prompt(topic)` |
| Read inherited finance policy and navigation catalog | Packaged workspace policy | Research navigation extension | `finance://workspace-policy` |

The page's research-workflow JSON export retains the complete pack, including provenance, history, coverage and chunks. Its Markdown export contains entries and summaries only and uses a `research-summary-YYYY-MM-DD.md` filename. Treat that file as a summary rather than a complete research-pack export. Ordinary record exports through the CLI or MCP remain separate operations.

MCP is a read-only view over one existing, launch-selected local workspace. SQLite uses `mode=ro`; MCP does not create tables, change records or create a missing database. It has no arbitrary filesystem, URL, shell, model or trading tool. Its record limit is at most 100 per request, even if an underlying local service supports a larger query. An external host's own model or other tools remain outside this server's guarantees.

The broader local search/export service supports windows up to 1,000 records. Research-pack selection is capped at 100. A pack can additionally retain one exact anchor outside the selected window, giving its scoped history up to 101 record IDs. History has its own result limit and truncation marker. These limits refer to selected records and history independently.

Typed datasets use a separate SQLite table and do not inflate metadata-record counts. Local imports are bounded to 2 MiB, 1,000 rows and 32 columns. Directory/related-pack previews contain at most five rows; exact retrieval returns saved rows. Research packs link up to 20 dataset summaries. Comparison accepts two to five compatible price/NAV series. Reviewer packets cap metadata at 20 records, datasets at five and each dataset chunk at 20 rows. Omitted-row, missing-field, alignment and source-coverage markers remain visible. See the [schema and numerical methods](FINANCE-WORKSPACE.md#typed-datasets-in-the-existing-workspace).

Local version 0.3.0 acceptance passed 95 tests, the actual eleven-tool SDK interface in both protocol modes, and twelve read-only HTTP checks over imported non-demo datasets with no database-hash change. Actual Safari at 1440×896 and 834×904 passed chart/navigation, dated-reference and visible-layout checks. Review-packet Blob content was inspected while the test suppressed a physical download. See [ACCEPTANCE.md](ACCEPTANCE.md) for the precise scope. A reviewer packet explicitly reports that no models ran; only a host that actually executes two local reviewers can claim completed cross-review. A physical iPad, external-editor notice display, actual two-model execution and physical browser download remain unverified; current-version remote CI remains pending.

## Evidence boundaries

- A new observation is not necessarily a newly published report. Keep publication time and first observation separate.
- A metadata update is not proof that the original report's thesis changed. Read permitted source text before making that claim.
- Eastmoney-backed libraries share the same direct provider. Multiple libraries do not create independent corroboration.
- Research packs organize available records and their citations. They do not supply a licensed full-report corpus or guarantee a conclusion.
- JSONL and CSV empty exports contain a notice-only entry. It preserves the warning and must not be counted as a report, article or chunk of source evidence.
- Record, chunk and result notices survive export. The editor must also visibly render the notice; hidden metadata alone is insufficient.
- SDK-client acceptance, the local page and a named external editor are separate acceptance layers.
- A navigation catalog entry does not activate an account, connector, paid subscription or collector.
- Imported provenance and coverage are caller declarations. Schema validation and an immutable local snapshot do not verify the original provider's accuracy.
- Deterministic indexed curves, period returns and drawdowns describe saved aligned observations. They do not add dividends, fees, FX or annualization, and sampled drawdowns can miss between-observation extremes.

## Outside the current combination

The project does not bundle or acquire paywalled media, subscription investment-bank reports, report PDFs, private account data or an unrestricted web corpus. It does not execute trades, send notifications or run a model automatically. ReportGem, efinance and Fincept are not bundled dependencies; their recorded limitations remain in [source notes](SOURCES.md).

