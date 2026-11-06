# Contributing

投资有风险，分析结果和查询结果不构成投资建议。

By contributing, you confirm that you can submit the material and offer it under this project's [noncommercial license](LICENSE). Do not submit third-party report full text, credentials, personal information, or data you cannot redistribute.

1. Reuse existing modules first. State the specific problem a new source or feature solves.
2. Keep collection explicit, read-only and bounded. Preserve TLS verification, timeouts and response-size limits.
3. Do not bypass logins, paywalls, CAPTCHAs or source-site restrictions.
4. Distinguish catalog metadata, public full text, institutional opinions and generated analysis.
5. Preserve the direct provider, original publisher, publication time, retrieval time and coverage status.
6. Include the exact Chinese risk notice with every query, analysis, exported record and retrieval chunk. Display it visibly in the UI.
7. Test additions, updates, replay, filtering, notice retention and invalid input offline. Do not make CI request live sources.
8. Use labeled synthetic examples. State their scope. Do not fabricate live success, institutional views or returns.
9. Review the Git file list before publication. Exclude `.local/`, databases, logs, `.env`, API keys, cookies and PDFs.
10. Use English as the primary language for repository descriptions, README files, documentation, templates and new commit messages. Preserve the required Chinese risk notice and product UI localization.

Run the base checks:

```sh
python -B -m unittest discover -s tests -v
```

In a pull request, describe the problem, resulting behavior, validation and remaining gaps. Before using third-party code, check its license and attribution requirements. Record the exact files and versions in `docs/SOURCES.md`. An interface or design reference does not mean this project copied the referenced code.

