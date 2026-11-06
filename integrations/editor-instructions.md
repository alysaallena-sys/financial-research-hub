# Editor and knowledge-base integration

**投资有风险，分析结果和查询结果不构成投资建议。**

These rules apply to editors, agents, RAG services and personal knowledge bases that use this project's software, export formats or integration facilities. The integration must comply with the noncommercial requirements in [LICENSE](../LICENSE).

## Required visible result

Every time you show a query or analysis result to a user, display this exact Chinese notice in the result text or in a readable persistent banner next to it:

> 投资有风险，分析结果和查询结果不构成投资建议。

The bundled product uses a Simplified Chinese interface. Preserve the required Chinese notice even if an integrating editor uses another interface language. Hidden metadata, collapsed terms and a one-time dialog do not replace visible display.

## Integration steps

1. Read the [machine-readable contract](editor-contract.json), the project license and the source terms.
   Read the [canonical workspace requirements](../docs/FINANCE-WORKSPACE.md) and the packaged [workspace policy](../finance_research_hub/workspace-policy.json). Preserve their paid-media hold, local-only model boundary and source-role distinctions.
2. Add the rules below to the editor's project rules or the knowledge base's system instructions.
3. Before import, check every record's `risk_notice`, source, date and `is_demo`. Reject incomplete records or regenerate a complete export first.
4. When splitting content, retain the notice in both the chunk text and chunk metadata. Inheriting only parent-document metadata is insufficient.
5. Preserve the notice, citations, times and demo labels during retrieval and model calls. Do not replace unknown fields with invented facts.
6. Implement a fixed notice in the final answer renderer. Do not rely solely on a model following a prompt.
7. Check the final interface using the acceptance steps below before claiming that integration is complete.

Empty JSONL and CSV results contain a `record_type: notice` entry to retain the warning. It is not source material; an importer must not count it as a report or news item. Nonempty JSONL uses `record_type: chunk`; nonempty CSV uses `record_type: record`.

You can add the following rules to the appropriate project-rule mechanism in Cursor, VS Code, Obsidian or another editor. Products expose different rule entry points and rendering capabilities; use the mechanisms the selected product actually supports.

```text
Financial Research Hub integration rules:
- Noncommercial use only. Preserve LICENSE, NOTICE and attribution.
- Show this exact notice with every query and analysis result:
  投资有风险，分析结果和查询结果不构成投资建议。
- Preserve the notice in every record, retrieval chunk and exported file.
- Hidden metadata alone does not satisfy visible-display requirements.
- Keep broker opinions, disclosed facts and generated analysis separate.
- Cite original source, direct provider and publication date when available.
- Preserve is_demo and clearly mark synthetic examples.
- Do not bypass source access controls or assume third-party redistribution rights.
- Distinguish a saved metadata record from a full source reading.
- Keep dataset units, currency, adjustments, dates and calculation methods.
- Use deterministic calculations for numerical claims.
- A reviewer packet does not prove that a model or cross-check ran.
- Use two independent local reviewers only when the host explicitly runs them.
- Do not send private material to cloud models or through external question URLs.
- Keep paid-media acquisition paused.
```

## Integration acceptance

Use synthetic records for these checks. Do not upload private research reports for acceptance testing.

| Action | Observable pass condition |
| --- | --- |
| Search for a record after import | The full Chinese notice is visible next to the result; the source and demo labels remain intact |
| Ask the editor to generate analysis | The result displays the same notice and separates source content from generated inference |
| Split a document into retrieval chunks | Every chunk retains the notice in its text and metadata |
| Export JSON, CSV or Markdown | Every record keeps the notice, date and source |
| Attempt an import after removing the notice | The integration rejects it or first regenerates compliant data |

This repository can test its bundled output paths. It cannot technically control an unrelated editor. The integrator must implement the display layer and retain actual acceptance results. Copying this file or saving `editor-contract.json` does not establish that an editor meets the requirements.

