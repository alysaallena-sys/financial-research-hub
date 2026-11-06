# Acceptance Scope

投资有风险，分析结果和查询结果不构成投资建议。

Investing involves risk. Analysis and query results do not constitute investment advice.

This file separates source implementation, synthetic tests, local pages, third-party sources and public publication. A pass at one layer does not replace acceptance at another layer.

## Local acceptance on 2026-11-06

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
