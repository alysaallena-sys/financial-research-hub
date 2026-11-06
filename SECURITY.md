# Security

投资有风险，分析结果和查询结果不构成投资建议。

This project supports personal, local research. The default server binds only to loopback. Its HTTP interface is read-only. It provides no arbitrary command execution, arbitrary URL proxy, trading or account operations.

## Usage boundaries

- Use only explicitly selected sources. Preserve TLS certificate verification, timeouts and size limits.
- Keep secrets, cookies, personal databases, acquired reports and logs out of the public repository.
- Treat source links and text as untrusted input. Escape displayed text and restrict link protocols.
- Do not expose the local service directly to the public internet. Review authentication, network isolation and source terms before enabling remote access.
- Inspect actual outbound content before integrating a model or external editor. Preserve the visible risk notice.

## Reporting a concern

Use GitHub private vulnerability reporting if the repository enables it. Otherwise, open an issue without sensitive details and ask the maintainer for a private contact method. Do not publish secrets, cookies, personal data, immediately exploitable details or complete third-party reports.

## Publication checks

Before publication, review the proposed files, dependencies, source configuration and output examples. Offline tests do not establish live availability, completeness or source permissions. Repository terms cannot technically force an unrelated editor to display the risk notice.

