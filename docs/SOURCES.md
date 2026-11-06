# Sources, Interface References and Data Boundaries

投资有风险，分析结果和查询结果不构成投资建议。

Investing involves risk. Analysis and query results do not constitute investment advice.

This project combines public information, research-report metadata and explicitly reviewed public-data interfaces. The table below records fixed source references. The third-party projects provide interface or design references; this project does not bundle their source code or research databases. Any future code reuse requires a separate review of the specific file's license, attribution requirements and compatibility.

Use the [canonical workspace requirements](FINANCE-WORKSPACE.md) to determine each source's role. The packaged [workspace policy and research catalog](../finance_research_hub/workspace-policy.json) supplies the same source-role boundaries to application surfaces. A catalog entry is not permission to acquire or redistribute data.

## Reviewed projects

| Project and fixed commit | Code license or documentation status | Reference scope |
| --- | --- | --- |
| [AKShare](https://github.com/akfamily/akshare/tree/a199a70684165f08c16557a7b59b37bebdda7495) · `a199a70684165f08c16557a7b59b37bebdda7495` | MIT; separate data-use restrictions apply | Company-report titles, institutions, dates, ratings, annual EPS/PE forecasts and PDF links; the interface itself does not read PDFs |
| [report-cli](https://github.com/manymore13/report-cli/tree/0d98dde87a6b295359ae68152ca2693428baef83) · `0d98dde87a6b295359ae68152ca2693428baef83` | MIT | Interface categories for company, industry, macro, strategy and broker morning reports; the old `manymore13/eastmoney` URL redirects to this repository |
| [a-share-research-monitor](https://github.com/nexaforgelab/a-share-research-monitor/tree/87940e4c87d2bde2af56813decb701bdb26d39a1) · `87940e4c87d2bde2af56813decb701bdb26d39a1` | Apache-2.0 | Stable identifiers, snapshots and new/updated diff methods; this project does not inherit its default news, model or notification configuration |
| [manymore13/report](https://github.com/manymore13/report/tree/4818d294141c827ae056babfe1c63a51b0e4103d) · `4818d294141c827ae056babfe1c63a51b0e4103d` | Apache-2.0 | Reading organization through daily, weekly, monthly and industry indexes; the index repository is not a complete collector |
| [yfinance](https://github.com/ranaroussi/yfinance/tree/e2f6104164b70085556fe2f8e194cf3ca18550f5) · `e2f6104164b70085556fe2f8e194cf3ca18550f5` | Apache-2.0; the README notes personal-use conditions for Yahoo data | Yahoo-aggregated institutional rating events and consensus price targets; yfinance has no official affiliation with Yahoo |
| [equity-research-reports-skill](https://github.com/Ray-Yuan21/equity-research-reports-skill/tree/0b0e11c133768681fb73bc33c3b779fdb0c93b3d) · `0b0e11c133768681fb73bc33c3b779fdb0c93b3d` | MIT | Source, freshness and manifest conventions for public candidates; its open-source search script only generates query plans |
| [AKTools](https://github.com/akfamily/aktools/tree/b22c979fa1b018b1dba7353df12ca281b5fe3835) · `b22c979fa1b018b1dba7353df12ca281b5fe3835` | MIT; dated source review on 2026-11-02, version 0.1.4 | Discovery-first `search_interfaces` → `describe_interface` → `get_data`; approved interfaces and explicit schemas before collection. No package installation, live data or client acceptance in that review |
| [DBX v0.6.64](https://github.com/t8y2/dbx/tree/c107fa773905994a726bbba19cfaaa42a4ecd678) · `c107fa773905994a726bbba19cfaaa42a4ecd678` | Apache-2.0; dated source review on 2026-11-02 | Candidate for manual SQLite inspection and maintenance. Reviewed [main](https://github.com/t8y2/dbx/tree/51f31ef6aa9aeb7a128639121b29202e87e979ec) differs from the stable release; no installation, database access, locking or model/client acceptance |

AKShare, report-cli and the monitor above mainly use Eastmoney-related interfaces. Matching results from different libraries do not establish multiple independent data sources.

## Version 1 source scope

| Source | Content boundary | Checks required for use |
| --- | --- | --- |
| Fixed public information feeds, including BBC and Guardian | Titles, links, publication times and short summaries | Whether the feed permits the intended use; full articles and media attachments are outside default collection |
| TED public feed | Talk-entry titles, links, times and short summaries | Current feed reachability, attribution and content-use terms; no default video or transcript download |
| Eastmoney research-report interfaces | Index fields and public original-source links | Pagination, date range, count limits, field changes, source-access conditions and original-report rights |
| Yahoo through the optional yfinance adapter | Institutional rating events | Aggregate-source coverage, delay, missing records and personal-use conditions; complete investment-bank coverage is not guaranteed |

A readable page, an obtainable URL or an MIT/Apache software license does not by itself establish permission to bulk-save, build a database from or redistribute third-party data. Users must determine local retention scope from the original source's terms.

## Retained limitations

- Identify index or rating-event results as such; do not present them as full-report analysis.
- Record the original publisher and direct provider for each dataset. An institution-name field does not mean that the program connects directly to that institution.
- Preserve publication time and first-observed time. First observation does not mean recent publication.
- Show missing reports, pagination truncation, unknown fields and source failures explicitly.
- An update to a metadata record does not establish a change in the institution's underlying view. View changes require original-text and time evidence.
- The public repository contains no live collection results, full articles, report PDFs or commercial-database content.

## Projects not bundled or connected by default

| Project | Reason |
| --- | --- |
| [efinance](https://github.com/Micro-sheep/efinance/tree/c8fd370a3109b2d14a121e3a32a86e9c8354b01b) | The reviewed source disables certificate verification in some paths and also uses HTTP. Its README noncommercial statement coexists with MIT license text. Three isolated, security-patched paths passed bounded requests on 2026-11-06: stock history, fund NAV and convertible-bond base data. This does not establish safe upstream defaults or an integrated production adapter; it is not a default dependency |
| [FinceptTerminal](https://github.com/Fincept-Corporation/FinceptTerminal/tree/7716ee8613249fb44c4d14036c5bc16ed6f34e97) | License documents conflict at the fixed commit. It also includes cloud-model, external-MCP and live-trading paths. One isolated World Bank connector/source path parsed a bounded response on 2026-11-06. Native desktop installation and other connectors remain unverified. This project does not copy its UI, assets or code |
| [ReportGem](https://github.com/littlemosquito123/reportgem-global-research/tree/835da7dc04df38856d5152324cf64690f4d556a7) | The repository provides connection documentation for a commercial remote MCP service. The official terms summary restricts bulk scraping, database building and redistribution. Paid services and account access are outside the default scope |

ReportGem's website rules can differ from its fixed README. The review found updated search-pricing and subscription rules on the website. Any later evaluation must reread the [official documentation](https://www.reportgem.com/en/mcp.html) and full terms rather than promise old prices.

The efinance test matched the official 0.5.9 package's Python source to the fixed commit before applying transport-only changes. It replaced insecure certificate/HTTP behavior inside an isolated request boundary; it did not weaken TLS or modify this project's production network rules. Fund NAV, estimated changes and dated holdings disclosures remain different datasets. The Fincept check exercised only the original [World Bank connector](https://github.com/Fincept-Corporation/FinceptTerminal/blob/7716ee8613249fb44c4d14036c5bc16ed6f34e97/fincept-qt/scripts/worldbank_data.py) path; Python timed out, then one explicitly scoped system-curl request to the same source succeeded. Neither check grants data-retention or redistribution rights.

## Market navigation and official connectors: dated 2026-11-02 review

These entries preserve earlier source findings. They are not fresh runtime checks or active integrations. Recheck the source's current documentation and terms before implementation.

| Source | Official evidence | Workspace role and unresolved boundary |
| --- | --- | --- |
| Finviz | [Official Maps embed announcement](https://finviz.com/blog/you-can-now-embed-finviz-maps-on-your-website-blog-or-app-2/), [official API announcement](https://finviz.com/blog/our-upgraded-api-higher-limits-clearer-data-and-more-ways-to-connect/) | Map-embed/API candidates. Neither was connected locally. API account rights, retention and redistribution remain separate questions |
| Koyfin | [API FAQ](https://www.koyfin.com/help/faq/can-i-get-the-data-via-api/), [download FAQ](https://www.koyfin.com/help/faq/can-i-download-data/), [pricing](https://www.koyfin.com/pricing/) | Manual research and interaction reference. The FAQ offered no data API; download scope differs by data type. A contextual question button is not an API grant |
| Stock Analysis | [API-access FAQ](https://stockanalysis.com/help/faq/api-access/), [terms](https://stockanalysis.com/terms-of-use/) | Company-research navigation. No general API/MCP connection or bulk collector accepted |
| ETFdb / VettaFi | [VettaFi terms](https://www.vettafi.com/terms-of-use) | ETF-research navigation. Website requests failed during the dated review; export/API and internal-database rights remain unconfirmed |
| CompaniesMarketCap | [Official API page](https://companiesmarketcap.com/stockmarket-api/) | Ranking and discovery reference. The page did not offer its own API; an external recommendation is a different provider |
| MacroMicro | [Official data-download FAQ](https://support.macromicro.me/en/faq/182) | Macro-theme navigation. Download and enterprise/API rights depend on the relevant plan; no client or source acceptance |
| FRED / ALFRED | [Official FRED MCP connector guide](https://fred.stlouisfed.org/help/data/connecting-fred-to-ai-services/FRED-MCP-Connector), [service terms](https://fred.stlouisfed.org/legal/) | Official query connector documented, not registered. Host/account authorization and local acceptance remain unperformed. Query support does not grant unrestricted archiving or a persistent database. Retain observation, release, retrieval and vintage times |
| Seeking Alpha | [Official terms](https://about.seekingalpha.com/terms) | Opinion navigation only; paid-content collection is held |
| Reddit | [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) | Research leads only. API approval and original-source verification remain separate; discussion popularity does not verify facts |
| AnalysisSite | [Original deployment](https://analysissite.vercel.app/) | The dated review observed a paused deployment. Author, repository, data rights, citations and functions remain unverified |

FRED's official connector supports a query workflow. This statement does not classify all AI reading as prohibited. Apply the actual service terms to the proposed retention and use. Similarly, an existing browser subscription to WSJ or another paid site does not activate collection in this project. The later paid-media hold controls the current workspace scope.

## HTTPS transport and the TED path

System curl keeps normal certificate verification. The implementation references the [curl certificate documentation](https://curl.se/docs/sslcerts.html) and [official option manual](https://curl.se/docs/manpage.html). The project offers explicit transport selection only. It does not switch automatically after a Python certificate error or change system CAs or trust settings.

On 2026-11-06, responses from the official starting URL `https://www.ted.com/feeds/talks.rss` pointed in sequence to `https://pa.tedcdn.com/feeds/talks.rss` and `https://feeds.acast.com/public/shows/67587e77c705e441797aff96`. The project added only these two exact hosts, without wildcard domains. The final network read failed during this check. Confirmation of the source chain is not successful TED collection.

## Software licensing and interface references

[LICENSE](../LICENSE) applies to this project's original implementation. Optional packages retain their own software licenses. Interface and data-format references do not establish agency, partnership or endorsement by the original providers.

The base GitHub Actions configuration references the [GitHub Python testing documentation](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) and the [official actions/setup-python repository](https://github.com/actions/setup-python). Official GitHub tag refs were checked and pinned on 2026-11-06:

- [`actions/checkout` v7](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1): `3d3c42e5aac5ba805825da76410c181273ba90b1`.
- [`actions/setup-python` v7](https://github.com/actions/setup-python/tree/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0): `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`.

The workflow runs offline tests only. It does not schedule collection from financial sources. Preparing Actions and Python can connect to GitHub; the tests themselves do not request information feeds or research-report interfaces.

## Official MCP dependency and protocol references

The optional MCP extra pins the official [Python SDK v2.3.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0) at commit [`2118f14f8a19bc158d8a1cf90af58d85d187f849`](https://github.com/modelcontextprotocol/python-sdk/tree/2118f14f8a19bc158d8a1cf90af58d85d187f849). The SDK is MIT-licensed; it is an optional dependency, not vendored source. This project's original code retains its noncommercial license.

The fixed SDK [protocol registry](https://github.com/modelcontextprotocol/python-sdk/blob/2118f14f8a19bc158d8a1cf90af58d85d187f849/src/mcp-types/mcp_types/version.py) includes both the `2025-11-25` handshake era and the `2026-07-28` per-request era. The corresponding primary specifications are [2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25) and [2026-07-28 changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog). Local acceptance in both SDK modes does not establish behavior in every external host.

Implementation uses the official high-level `MCPServer`, `Client` and `StdioServerParameters` APIs. See [the MCP guide](MCP.md) for fixed examples, result-channel behavior and the version-pinned process-observation instrumentation used only by the standalone acceptance helper.
