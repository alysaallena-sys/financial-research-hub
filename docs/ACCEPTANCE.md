# Acceptance Scope

投资有风险，分析结果和查询结果不构成投资建议。

Investing involves risk. Analysis and query results do not constitute investment advice.

This file separates source implementation, synthetic tests, local pages, third-party sources and public publication. A pass at one layer does not replace acceptance at another layer.

## Local version 0.3.0 acceptance on 2026-11-06

The following results describe the unified metadata, dataset, comparison and local-review extension. The review used local acceptance receipts. Those receipts, databases and acquired observations remain private; this repository publishes no raw acquired sample data.

| Layer | Observed result | Scope limit |
| --- | --- | --- |
| Complete synthetic suite | `python -B -m unittest discover -s tests -v` passed all **95 tests** with the optional official MCP SDK installed; no skips; return code 0 | Synthetic tests do not establish continuous source availability or data accuracy |
| Wheel build and content audit | A local version 0.3.0 wheel built successfully. Its 22 members included the workspace policy, static resources, LICENSE and NOTICE, with all 35 catalog entries. The audit found no private/local members, databases, PDFs or private-path content | The wheel was not installed, and runtime dependencies were not installed by this build. Package-content acceptance does not establish installation or an external-host connection |
| Actual MCP stdio | The standalone helper passed with `mcp==2.3.0` in `auto` (`2026-07-28`) and `legacy` (`2025-11-25`) modes; it checked eleven tools, four fixed resources, two exact-object templates and two prompts | This is SDK-client acceptance, not installation or visible notice acceptance in an arbitrary editor |
| MCP policy and lifecycle | Text and structured notices, dataset fingerprints and row/chunk notices, comparisons, unexecuted review state and handled errors passed; each of the two exact owned children exited with return code 0; the synthetic database SHA-256 remained unchanged | The helper observes only its owned child objects through instrumentation against the pinned SDK; it performs no process scan or explicit kill |
| Imported non-demo evidence through HTTP | Twelve actual loopback GET checks returned HTTP 200 over four saved dataset kinds: price series, fund NAV, bond profile and macro series. The database SHA-256 remained unchanged; the server reported read-only mode; no new source request occurred | This proves local import/readback and interface behavior, not a continuous provider adapter, complete history or independent verification of published values |
| Missing source metadata | Readback retained declared units, missing-field flags and an unknown original macro retrieval timestamp as `null` | Import time or another source's timestamp must not replace missing evidence |
| Actual Safari layout | Apple's official Safari MCP checked CSS viewports of 1440×896 and 834×904. Neither viewport had document overflow. Visible interactive targets, including checkbox labels and source links, met the 44px minimum height. The risk bar remained sticky | The narrower viewport is a desktop Safari measurement; a physical iPad remains unverified |
| Charts and connected navigation | Exact dataset detail displayed source information, content hash, a raw table and an SVG chart. Two synthetic series produced a strict comparison and a comparison chart. Dataset-to-research-pack and pack-to-exact-dataset navigation passed | The calculation describes compatible saved observations. It adds no FX conversion, missing observations, dividends, fees or annualization |
| Reference-only research | The explicit literal query `Koyfin` returned zero saved metadata records, zero datasets and one dated catalog reference. Its review packet retained `evidence_status: reference_only` without claiming full-text access | A dated navigation reference is not acquired news, numeric data, runtime source acceptance or a data API grant |
| Review-packet export | Clicking the export control generated a Blob whose inspected JSON retained the notice in every chunk, computed numeric checks, `local_only: true`, `model_calls_performed: false`, `review_status: not_performed`, two unstarted reviewers and the paid-media hold | The test suppressed the physical download. Blob generation/content inspection is not a completed browser file download or a completed two-model review |
| Settled visual inspection | Final screenshots were captured after two `requestAnimationFrame` cycles following scrolling and were visually inspected | Initial timing captures were not promoted into settled visual evidence. Screenshots alone do not establish the full workflow |
| Functional publication and remote CI | All 42 file blobs at the fixed functional commit [30e8d2087238bbee512f0826041eed1f2399506b](https://github.com/alysaallena-sys/financial-research-hub/commit/30e8d2087238bbee512f0826041eed1f2399506b) matched local Git blob hashes. [Actions run 42263898429](https://github.com/alysaallena-sys/financial-research-hub/actions/runs/42263898429) completed successfully for Python 3.11 and 3.13, including base tests, pinned SDK installation and the actual stdio suite | This receipt applies to that fixed functional commit. Later documentation-only commits require their own CI result readback |

The HTTP request path and MCP open the selected database in read-only SQLite mode. Explicit local CLI import remains the write boundary. Source acquisition, paid-media collection, remote models, trading, notifications and global client registration were not activated by these checks.

Remaining acceptance work: a physical iPad, visible notice rendering in a named external editor, actual execution of two explicitly selected local models, and a physical browser download. The functional commit and CI receipt above establish their named version only. Later documentation-only commits require their own CI readback. The fixed earlier public commit and Actions receipt below remain historical evidence only.

## Historical initial baseline acceptance on 2026-11-06

| Layer | Pass condition | Observed result |
| --- | --- | --- |
| Offline core and parser tests | New records, updates, replay, source separation, filtering, pagination and transport boundaries | All 39 offline tests passed, using synthetic input and in-memory state |
| Risk notice | Preserve the notice in CLI, API, briefs, each exported record and every retrieval chunk | Independent contract tests passed; the notice was visible on Safari pages and in the brief; external editors remain unverified |
| Local HTTP | Output formats, empty results, invalid parameters, source boundaries and read-only constraints | 13 actual loopback-request checks passed; nonempty/empty results in four formats and 400/403/404/405 responses retained the notice |
| Local page | Filtering, change records, source status and briefs | Native Safari returned 4 synthetic records for all items and 1 for the research filter; the brief used the current query. HTTP export formats passed; browser file-download acceptance was not performed |
| Narrow viewport and iPad | Layout, touch targets and filtering remain usable | Safari's actual 1440×896 and 834×1008 viewports had no horizontal overflow; visible form and action controls had a minimum height of 44px; the risk bar remained visible after 650px of scrolling; a physical iPad remains unverified |
| BBC / Guardian | One bounded public-RSS metadata connection | Explicit system curl with certificate verification enabled returned 54 and 20 records respectively. This proves only that source window on that occasion, not continuous availability or full-text rights |
| Eastmoney | One nonempty metadata page and coverage markers | Historical company sample: 600519, 2025-04-01 through 2025-04-30, 5 records per page and at most 1 page. It returned 5 records; the upstream reported 5 total pages, with `truncated=true`. The other four report types have synthetic-test coverage only |
| TED | Official source and network path | The redirect chain from the official starting URL was checked; the final system-curl request failed in this check (exit 56). Availability remains unverified. No TLS or access restriction was bypassed |
| Optional overseas ratings adapter (yfinance/Yahoo) | Actual version, call chain and returned-field acceptance | Not performed; the base tests do not cover it |
| External-editor integration | A visible risk notice in real query and analysis results in the target editor | Not performed; a machine contract is not display acceptance |
| Public repository | Exclude local state and third-party content from the file list; read back remote commits and notices | Published as a Public repository. All 26 files in the first complete publication, fa44246, matched local Git blob hashes; anonymous Safari could read it |
| GitHub Actions | Remote workflow completes and its result is read back | Both Python 3.11 and 3.13 jobs for the first complete publication succeeded; see the fixed receipt below |

Maintainers may update status from actual receipts. Record the test command, observed result and evidence reference. Keep unperformed checks marked unverified. Do not record an expected pass or treat a screenshot's existence as proof that the entire flow passed.

The complete offline entry point is `python -B -m unittest discover -s tests -v`. JavaScript `node --check` passed. The source-connection checks above did not save or publish third-party full text or mix real content into the synthetic demo database.

The default local Python CA-chain check failed. After explicit system curl used its normal trust backend, BBC, Guardian and the report sample above succeeded. The implementation did not disable certificate verification or modify system trust. The optional transport received an independent mock review; POST requests cannot redirect across origins, and GET redirects remain subject to a fixed HTTPS-host allowlist.

The page preview shows synthetic data in actual Safari: [workbench screenshot](images/demo-workspace.png). The browser console showed messages about CSP-blocked inline styles; the project did not relax CSP in response. The table above records observed page functions and layout. It does not claim an empty console.

First complete publication: [fa442465786a6c2e8ec200f41059a92dd8e6d6ca](https://github.com/alysaallena-sys/financial-research-hub/commit/fa442465786a6c2e8ec200f41059a92dd8e6d6ca). The corresponding [Offline tests run 42245387434](https://github.com/alysaallena-sys/financial-research-hub/actions/runs/42245387434) was read back as success, with both Python versions successful. This receipt refers to a fixed version. Results for later commits must come from their corresponding Actions run records.

## Earlier metadata/research-pack extension acceptance on 2026-11-06

The MCP-specific local unittest run passed two cases using the actual official SDK `mcp==2.3.0` and child stdio servers. The client negotiated `2026-07-28` with `mode="auto"` and `2025-11-25` with `mode="legacy"`.

The run checked notices in structured and model-readable text, handled wrong-type, unknown-tool and invalid-limit errors, and found the chosen database's SHA-256 unchanged before and after the protocol checks. A missing database was refused without creating it or writing startup text to stdout. These are local SDK-client results; they do not establish arbitrary host compatibility or visible notices in an external editor.

The complete extension suite passed all **58 tests** with the optional SDK installed: `python -B -m unittest discover -s tests -v`. The 17 shared-service checks cover exact lookup beyond a 1,000-record result window, scoped history, literal-topic selection across symbols, streaming top-N queries, read deadlines, read-only SQLite, CLI/HTTP parity and export notices. The base interpreter without the optional SDK passed 56 cases and explicitly skipped the two MCP cases.

The [standalone acceptance helper](../integrations/mcp_client_acceptance.py) also passed both actual stdio paths. It observed the exact two owned child processes exit with return code 0 and found the synthetic database SHA-256 unchanged. Process observation uses private instrumentation against the exact pinned SDK; it is not a portable host API.

The linked-research page was checked in actual Safari with observed CSS viewports of 1440×896 and 834×904. An exact-symbol synthetic report opened its source and scoped history. Switching to the literal topic `示例` returned all four synthetic information types. The page kept the risk bar visible, avoided horizontal overflow and gave the new visible action/form controls at least 44px height. This is a desktop Safari viewport check; a physical iPad and browser file-download acceptance remain unverified.

Remote CI for each extension commit and external-editor display have separate acceptance scopes. The earlier 39-test and publication receipts above refer to the earlier fixed version. Do not promote those receipts into validation of every later change. See the [MCP guide](MCP.md) and [coverage matrix](COVERAGE.md).

## Completed independent offline contract checks

Command:

```sh
python -B -m unittest discover -s tests -p test_notice_contract.py -v
```

All 14 local checks passed on 2026-11-06. They used in-memory SQLite, in-memory HTTP requests and synthetic research-report input. They did not open a listening port, create a collection database, request real sources or download reports.

Reviewed scope:

- The license ID, machine contract and fixed risk text agree.
- Imported content and extra fields cannot remove mandatory notices or the noncommercial flag.
- Queries, deterministic briefs and each record or chunk in JSON, JSONL, CSV and Markdown retain the notice.
- Empty exports retain a parseable notice-only entry without impersonating real material.
- CLI argument, unauthorized live-collection and database errors all include the risk notice.
- In-memory HTTP flows return noticed results or rejections for empty results, errors, unknown endpoints, write methods and invalid Host/Origin.
- Non-loopback binding is rejected before server creation; the source allowlist rejects arbitrary targets; synthetic report queries did not initiate PDF downloads.

These checks establish the output contract and the tested code branches. They do not establish that a real browser displayed the notice or that third-party sources, external editors, the public repository or remote CI passed acceptance.

## Publication and knowledge-base boundaries

Public publication includes only project code, documentation, tests and clearly marked synthetic examples. This project's noncommercial license does not grant redistribution rights to third-party articles, reports or data.

Check each external-editor integration separately using the [integration acceptance steps](../integrations/editor-instructions.md). The project cannot guarantee that every external application follows the contract. Claims must distinguish contractual and documentation requirements, retention in built-in outputs and actual acceptance in an external editor.
