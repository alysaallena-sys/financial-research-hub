# Finance workspace: requirements and integration map

**投资有风险，分析结果和查询结果不构成投资建议。**

Investing involves risk. Analysis and query results do not constitute investment advice.

This document consolidates the project's finance requirements. Use it before extending a source, workflow or integration. It contains approved product requirements and source findings. It does not reproduce private conversations, account details or acquired financial content.

The original project uses the custom [noncommercial source-available license](../LICENSE). That license does not grant rights to third-party data. Preserve [NOTICE](../NOTICE) and the [editor display contract](../integrations/editor-contract.json).

## Product goal

Use one local workspace to follow public information, inspect broker-report metadata, compare permitted financial observations and assemble source-linked research material. Connect records, topics, datasets, calculations and outputs. Reuse the same services through the CLI, local page and optional MCP adapter.

The workspace supports personal research. It does not execute trades or produce personalized investment recommendations. A source-linked research pack is evidence organization. It does not establish the accuracy of a forecast.

## Inherited requirements

| Requirement | Implementation rule |
| --- | --- |
| Combine financial information | Keep public news, TED entries, broker-report metadata, rating events and permitted typed datasets in one research workflow. Identify each information type explicitly. |
| Preserve source evidence | Retain the original publisher, direct provider, original URL, publication or observation time, retrieval time and coverage. Record a missing field as missing. |
| Make changes inspectable | Distinguish first observation, newly saved records, metadata updates and unchanged records. A changed metadata field does not prove a changed investment thesis. |
| Connect research material | Link exact records, literal topics, exact symbols, dataset provenance and scoped history. State the selection rule. A matching keyword does not prove a causal connection. |
| Use calculations for numerical claims | Calculate comparisons in deterministic code. Keep units, currencies, price adjustments, date alignment and method visible. Do not ask a model to invent missing observations. |
| Support cross-checking | Prepare the same cited evidence for two independent review passes. Separate each review, disagreements and unresolved evidence. A packet or prompt does not prove that two models ran. |
| Improve the research interface | Use a coherent market and research workbench. Koyfin is an interaction reference. Do not copy proprietary assets or claim access to its data API. |
| Preserve editor risk notices | Show the exact Chinese notice with every query and analysis result. Retain it in records, chunks and exports. Hidden metadata alone is insufficient. |
| Remain noncommercial and local by default | Keep acquired data, private configuration and credentials outside public Git. Use synthetic public fixtures. Keep models, notifications, trading and global client registration disabled by default. |
| Keep paid media on hold | Do not acquire WSJ, Seeking Alpha or other paid content. The earlier idea of selecting and analyzing three daily WSJ Opinion articles remains held under the later paid-media exclusion. |

The requirement for public-news and TED collection remains active. A source failure remains a failure. Do not substitute a claimed successful collection or bypass a restriction.

The dormant WSJ request selected three representative Opinion articles and required title, author, publication date and a selection rationale. Its six analysis sections were core claim; argument chain and evidence; implicit assumptions; strongest counterargument; evidence gaps; and implications and follow-up observations. A cross-article comparison followed those sections. The accepted fallback used the nearest verified publication day within seven days and displayed the actual date. This preserves the requested format only; the later paid-media hold prevents acquisition or automatic execution. The earlier local dual-review attempt failed twice and was disabled. This project does not silently resume it.

Screenshots and other products can illustrate watchlists, charts, fund data, convertible bonds, macro data or annotations. They do not create a fixed seven-module delivery checklist. Select an implementation from the actual user request, source rights and verified interfaces.

## Current integrated baseline

The baseline joins saved records, exact lookup, source-linked briefs, scoped history, research packs and notice-preserving exports. The CLI, local HTTP page and optional read-only MCP adapter share the same research service. The MCP adapter reads one existing, launch-selected SQLite database and does not acquire data.

| Area | Current evidence and limits |
| --- | --- |
| Public news | BBC and Guardian feed metadata passed bounded live checks on 2026-11-06. This is not full-article collection or continuous availability. |
| TED | The official redirect chain was checked. The final network request failed during the recorded check; runtime collection remains unverified. No video or transcript acquisition is claimed. |
| Broker research | Eastmoney stock-report metadata passed one bounded historical-page check. Industry, macro, strategy and morning-report categories have synthetic parser tests, not complete live acceptance. No report-PDF or full-report corpus is included. |
| Overseas rating events | The optional yfinance adapter represents Yahoo-aggregated institutional events. Its live dependency and source call remain unverified. It does not provide all investment-bank research. |
| Local research | Exact record lookup, query-scoped briefs, history and research packs have synthetic service and page acceptance. JSON packs preserve provenance, coverage, history and chunks. Markdown page exports contain a material summary. |
| MCP | Actual official SDK stdio acceptance passed the version 0.3.0 eleven-tool interface in `auto` and `legacy` modes, with both owned children exiting 0 and the synthetic database hash unchanged. External-editor installation and visible notice display remain separate acceptance work. |
| Numerical workbench extension | Version 0.3.0 passed 95 tests, twelve read-only HTTP checks over four imported non-demo dataset kinds, and actual Safari chart/navigation checks at 1440×896 and 834×904. Review-packet Blob inspection passed with physical download suppressed. No model ran. Physical iPad, external-editor display, two-model execution and physical download retain their separate pending scopes. |

The [coverage matrix](COVERAGE.md) contains surface and source limits. The [acceptance record](ACCEPTANCE.md) distinguishes fixed historical versions from later changes. Test totals and public CI status belong to the version that actually ran them.

The fixed functional commit [30e8d2087238bbee512f0826041eed1f2399506b](https://github.com/alysaallena-sys/financial-research-hub/commit/30e8d2087238bbee512f0826041eed1f2399506b) passed [Actions run 42263898429](https://github.com/alysaallena-sys/financial-research-hub/actions/runs/42263898429) on Python 3.11 and 3.13, including base tests, pinned SDK installation and actual stdio tests. All 42 published file blobs matched local Git hashes. Later documentation-only commits require a separate CI readback.

## Source and adaptation roles

| Layer | Candidate or reference | Reuse and boundary |
| --- | --- | --- |
| Public information acquisition | Fixed BBC, Guardian and TED feeds | Save permitted feed metadata and short summaries. Do not infer full-text or media rights. |
| Broker-report metadata | Eastmoney; AKShare and report-cli interface references | Keep five report categories, dates, institutions, ratings and source links where available. A PDF URL is metadata, not permission to fetch the PDF. |
| Observation and change methods | a-share-research-monitor and report index references | Reuse stable IDs, snapshots, differences and reading organization in the existing workspace. Do not inherit remote models, automatic notifications or unrelated defaults. |
| Overseas ratings | yfinance / Yahoo | Optional event source with source-dependent coverage. Multiple wrappers around Yahoo do not create independent sources. |
| Typed financial-data candidates | efinance; discovery-first AKShare/AKTools | Review an exact interface, its source rights, units, adjustment and network behavior before integration. See the isolated-test limits below. |
| Macro-data candidate | Fincept's World Bank connector; FRED official interfaces | Use original provider metadata and revision dates. One World Bank connector sample does not establish all Fincept connectors. FRED MCP is documented, not registered. |
| Market navigation and presentation | Koyfin, Finviz, Stock Analysis, ETFdb, CompaniesMarketCap, MacroMicro | Preserve original research links. Navigation and visual references do not authorize automated acquisition. |
| Local database maintenance | DBX | Candidate for manual SQLite inspection. It does not replace the existing store or authorize access to another database. |
| Paid or private research | WSJ, Seeking Alpha, ReportGem and subscription reports | Hold acquisition and account integration. Do not create a public corpus or activate a paid remote connector. |
| Community and AI dashboards | Reddit and AnalysisSite | Treat as research leads. Confirm facts with original sources. AnalysisSite was paused in the dated review; no product acceptance is claimed. |

The [source register](SOURCES.md) records fixed code references and dated official documentation. Recheck time-sensitive rights, interfaces and prices before a new connection. A software license and a data license are separate questions.

## Candidate evidence, without integration claims

### efinance

The fixed source is `c8fd370a3109b2d14a121e3a32a86e9c8354b01b`. The source review found disabled certificate checks and HTTP paths, plus a README noncommercial statement alongside MIT license text. The project does not resolve that conflict or adopt insecure network defaults.

On 2026-11-06, a bounded isolated test of the matching 0.5.9 package used explicit security-only transport changes. Three paths returned nonempty results with the expected schemas: stock daily history, fund NAV history and one convertible-bond base record. The test retained TLS verification, used a fixed request boundary and did not add an efinance dependency to this project.

This evidence establishes only those patched, bounded paths. It does not establish unmodified upstream safety, a production adapter, US-market identifiers, all instruments, all interfaces or redistribution rights. Fund NAV, estimated changes and disclosed holdings must remain distinct information types.

### FinceptTerminal

The fixed source is `7716ee8613249fb44c4d14036c5bc16ed6f34e97`. The reviewed license documents conflict. Generic workbench ideas and source-interface organization remain references; this project does not copy Fincept code, UI or assets.

On 2026-11-06, a bounded isolated test exercised the original World Bank connector's parsing path for one public indicator request. Python's request timed out; one explicitly approved request to the same URL through system curl succeeded. This establishes one connector/source path and response parsing. It does not establish native desktop installation, Qt startup, all connectors, model features, trading features or independent verification of the published observation.

### AKShare and AKTools

The AKTools review dated 2026-11-02 fixed version 0.1.4 at `b22c979fa1b018b1dba7353df12ca281b5fe3835`. Its discovery sequence is `search_interfaces` → `describe_interface` → `get_data`. Use an approved interface list and examine the schema before a data request. Do not expose an unreviewed catalog as implicit permission to collect every endpoint.

That review did not install the package, connect a client or obtain live data. Interface discovery does not prove token savings, source accuracy or data-use rights. Candidate interfaces included A-share history, ETF market-price history and China CPI; ETF prices and fund NAV are different datasets.

### Market navigation and maintenance

The official-site review dated 2026-11-02 documented Finviz map embeds and FRED's official MCP. Neither was connected locally. It recorded Koyfin as a manual research and UI reference, with no data API offered in its official FAQ. Stock Analysis, ETFdb, CompaniesMarketCap and MacroMicro remained research-navigation references with source-specific access and reuse limits.

The DBX review dated 2026-11-02 identified stable `v0.6.64` at `c107fa773905994a726bbba19cfaaa42a4ecd678` and a different main commit, `51f31ef6aa9aeb7a128639121b29202e87e979ec`. It did not download, install or run DBX, open this project's database, test locking or configure a model. A release name shared with main does not establish identical code.

The earlier public-information selection included NPR, DW, France 24, Al Jazeera, PBS, Guardian World and TED Talks Daily. These remain dated candidates in the catalog. Their historical records do not establish current collection in this repository, and this work does not resume another production collector.

## Explicit record interchange

```sh
python -m finance_research_hub --db .local/research.sqlite3 import-records /absolute/path/to/reviewed-records.json
```

This local CLI bridge accepts a current-schema record array or an object with an `items` array. The limit is 2 MiB and 1,000 records. It validates the batch before writing and preserves source identities, publication dates, notices and demo labels. A missing original retrieval time becomes `unknown`, not the import time. Existing JSON record exports provide an interchange shape; retrieval-chunk JSONL is a different format and is not a record-import file.

Select and review the exact file before import. The command does not inspect another application's database, infer a legacy field mapping, collect new content or resume a historical source. HTTP and MCP remain read-only. Imported records still require source-rights and provenance review; schema validation does not grant those rights or establish source accuracy.

## Typed datasets in the existing workspace

Datasets occupy a separate SQLite table from news and report metadata. Their kinds are `price_series`, `fund_nav`, `bond_profile` and `macro_series`. A dataset import does not increase the metadata-record count, connect a source or independently verify the caller's provenance.

```sh
python -m finance_research_hub --db .local/research.sqlite3 import-dataset /absolute/path/to/reviewed-dataset.json
python -m finance_research_hub --db .local/research.sqlite3 datasets --kind price_series
python -m finance_research_hub --db .local/research.sqlite3 dataset DATASET_ID
```

The import command reads one explicit local JSON file. It does not accept a source URL or call a provider. HTTP and MCP have no import operation. Replace `DATASET_ID` with an exact saved ID returned by the directory.

The following input is entirely synthetic:

```json
{
  "source_id": "synthetic-price-a-v1",
  "title": "Synthetic price series A",
  "kind": "price_series",
  "symbol": "DEMO-A",
  "market": "synthetic",
  "currency": "USD",
  "units": {"value": "USD/unit"},
  "as_of": "2026-01-07",
  "timezone": "America/New_York",
  "adjustment": "unadjusted",
  "frequency": "daily",
  "provenance": {
    "provider": "synthetic-fixture",
    "url": "https://example.com/synthetic-price-a",
    "original_publisher": "Synthetic example",
    "retrieved_at": "2026-01-08T00:00:00+00:00",
    "source_version": "example-v1",
    "identity_basis": "Explicit synthetic label; no real security"
  },
  "columns": {"date": "date", "value": "number"},
  "time_column": "date",
  "value_column": "value",
  "rows": [
    {"date": "2026-01-05", "value": 100},
    {"date": "2026-01-06", "value": 102},
    {"date": "2026-01-07", "value": 101}
  ],
  "topics": ["synthetic-example"],
  "related_record_ids": [],
  "coverage": {"truncated": false, "total_rows": 3},
  "is_demo": true
}
```

Imports are bounded to 2 MiB, 1,000 rows and 32 declared columns. Each dataset accepts at most 20 explicit topic labels of 100 characters and 100 exact related-record IDs. Directory and research-pack summaries preview at most five rows. Exact retrieval returns the saved rows up to the import limit. Preserve row counts, omitted-row markers and coverage when handing a preview to another tool.

Column types are `number`, `string`, `date`, `datetime` and `boolean`. Numeric fields accept finite JSON numbers or `null`; they reject numeric strings, booleans, NaN and infinity. Missing values remain visible through `missing_fields` and `null_counts`. The application resets risk, noncommercial and demo fields on each row and chunk. Unknown metadata does not become a guessed currency, date or adjustment.

Price and NAV series default to `date` and `value` columns. Annual macro data can preserve a string period such as `"2023"` without inventing a day. Do not declare that string as a calendar date. Annual macro and bond-profile records are not performance-comparison inputs.

The stable dataset ID hashes provider, kind and `source_id`; it does not hash observation values. The store rejects a changed payload under an existing ID. Assign a versioned `source_id` to a different snapshot. Exact datasets and directory summaries expose the stored payload fingerprint as `content_hash`, with `hash_basis` describing the canonical normalized saved payload before query metadata. That computed fingerprint and a caller-declared source version have different roles; do not treat a caller's declaration as independently verified source identity.

## Deterministic comparison

Select two to five distinct saved price or NAV datasets:

```sh
python -m finance_research_hub --db .local/demo.sqlite3 datasets
python -m finance_research_hub --db .local/demo.sqlite3 compare DATASET_A DATASET_B --alignment strict
python -m finance_research_hub --db .local/demo.sqlite3 compare DATASET_A DATASET_B --alignment intersection --start 2026-01-05 --end 2026-01-07
```

Replace the placeholders with saved IDs. `demo` seeds two labeled synthetic daily series. The example dates do not claim real market observations.

Comparison requires a declared date column, a numeric value column, at least two shared observations and strictly positive finite values. Currency, value unit, adjustment, frequency and timezone must match. Supported frequencies are daily, weekly and monthly. Missing comparison values, duplicate dates, unknown bases and synthetic/live mixtures are rejected.

`strict` requires identical retained dates. `intersection` explicitly keeps shared dates only. Optional start/end bounds use inclusive `YYYY-MM-DD` dates. Results report alignment exclusions and dates outside the window. No interpolation, FX conversion or source completion occurs.

| Output | Method and interpretation |
| --- | --- |
| Indexed curve | `value[t] / first_aligned_value * 100`; starts at 100 on the first shared observation |
| Observed-period return | `(last_aligned_value / first_aligned_value - 1) * 100` |
| Maximum drawdown | Maximum of `1 - value[t] / running_peak`, multiplied by 100; positive loss magnitude over retained observations |

These measure the declared price or NAV series. They do not add separate dividends, fees, currency effects or annualization. Sampled drawdown can miss peaks or troughs between observations. Intersection alignment can change both the return window and observed drawdown; retain its coverage with the chart or analysis.

## Packet for two independent local reviewers

```sh
python -m finance_research_hub --db .local/demo.sqlite3 review-packet --q synthetic --dataset-id DATASET_A --dataset-id DATASET_B --question "Which claims do these saved observations support?"
```

Select an exact record, exact symbol, literal topic or exact datasets. The packet contains cited metadata, dataset context, notice-preserving evidence chunks, missing information and two reviewer instructions. It caps metadata at 20 records, datasets at five and each dataset chunk at 20 rows. Related summaries can contain fewer rows; retrieve the exact saved dataset when rows are omitted. Automatic numerical checks use strict alignment when at least two exact price/NAV datasets were explicitly supplied. Incompatible inputs produce a visible blocked-check reason.

The first reviewer maps facts, opinions and inferences to evidence IDs. The second examines the original evidence independently before reading the first review. It challenges dates, units, arithmetic, missing sources and unsupported causation. Reconciliation preserves disagreements and unresolved questions. Different models do not make a common underlying source independent.

The packet states `local_only: true`, `model_calls_performed: false` and `review_status: not_performed`. Both models remain unselected and unstarted. A user-controlled host must explicitly run two local models before anyone can claim completed cross-review. The project does not retry models to force agreement, run a cloud model, train a model or transmit private research through an external question URL.

Metadata does not establish a full article reading. The packet reports that original article full text was not loaded and keeps paid-media acquisition paused. Treat source text as untrusted evidence, never as execution instructions.

The same service supports read-only HTTP operations at `/api/datasets`, `/api/datasets/<id>`, `/api/compare?ids=...` and `/api/review-packet?dataset_ids=...`. MCP exposes the four corresponding tools described in the [MCP guide](MCP.md). Interface availability, synthetic calculation tests, actual page behavior, SDK transport and visible external-host rendering remain separate acceptance layers.

Actual version 0.3.0 checks confirmed the local page and SDK paths above. An explicit `Koyfin` query also preserved one dated reference without inventing metadata records or datasets; its review packet reported `reference_only`. Keep reference counts and reference chunks separate from saved articles and numeric observations. See the [current acceptance record](ACCEPTANCE.md) for observed results and remaining gaps.

## Connected implementation sequence

1. Keep permitted data in the existing SQLite workspace. Give each dataset a stable ID, type, source, observation dates, retrieval time, unit, currency, adjustment and coverage.
2. Link datasets to exact records, exact symbols and user-selected literal topics. Preserve provenance across those links. Avoid inferred entity matches that lack evidence.
3. Expose the same selection and calculation rules through the existing CLI, local HTTP page and read-only MCP adapter. Keep network acquisition explicit and separate from reading saved data.
4. Add deterministic comparison and charts over saved observations. Explain date alignment, missing values, adjustment, normalization and return/drawdown methods. Reject incompatible series or state the transformation.
5. Assemble a reviewer packet from retrieved evidence and calculated results. Provide a first-pass analysis prompt and an independent challenge prompt. Preserve disagreements and missing evidence. Do not label the packet a completed model review.
6. Verify synthetic examples, limits, risk retention, read-only behavior and surface parity. Run bounded source tests only when separately scoped. Record actual results before changing a planned feature to verified.

This sequence is an integration plan, not a promise that every listed source or illustrative market module already works. Avoid a separate service when the existing store and research service can express the requirement.

## Acceptance gates and held scope

Every source integration needs a fixed interface reference, rights boundary, bounded request plan, failure behavior, provenance and an actual result. Every numerical workflow needs a synthetic calculation check with a visible method. Every host integration needs result-contract checks and a separate visible-display check in the target host.

Keep the following held until a later explicit request and a scoped acceptance plan: paid-media acquisition, subscription report corpora, broker PDFs, private portfolios or account data, remote-model calls, model training, automatic notifications, recurring collection, trading and global connector registration. Earlier experiments or account logins do not activate these features.

Do not bundle real acquired records or private acceptance receipts into the public repository. Publish only code, reviewed documentation, tests and labeled synthetic examples.
