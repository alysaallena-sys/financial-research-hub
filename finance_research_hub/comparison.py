"""Deterministic comparison of compatible saved price or NAV observations."""
from __future__ import annotations

from datetime import date
import math
import re
from typing import Any

from . import RISK_NOTICE
from .core import envelope


def _day(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{field} must be a YYYY-MM-DD date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError(f"{field} must be a valid calendar date") from None


def compare_datasets(datasets: list[dict[str, Any]], *, alignment: str = "strict",
                     start: str = "", end: str = "") -> dict[str, Any]:
    """Compute index levels, observed-period returns and drawdown without a model.

    Missing dates require explicit intersection alignment. No FX conversion,
    interpolation, annualization, dividend reinvestment or source completion.
    """
    if not isinstance(datasets, list) or not 2 <= len(datasets) <= 5:
        raise ValueError("Compare between 2 and 5 saved datasets")
    if alignment not in {"strict", "intersection"}:
        raise ValueError("alignment must be strict or intersection")
    if len({bool(dataset.get("is_demo", False)) for dataset in datasets}) > 1:
        raise ValueError("Synthetic and live datasets must be compared separately")
    start = _day(start, "start") if start else ""
    end = _day(end, "end") if end else ""
    if start and end and start > end:
        raise ValueError("start must not be after end")
    ids = [dataset.get("id") for dataset in datasets]
    if any(not isinstance(identifier, str) or not identifier for identifier in ids) or len(set(ids)) != len(ids):
        raise ValueError("Datasets must have distinct saved IDs")
    prepared = []
    basis = None
    for dataset in datasets:
        if dataset.get("kind") not in {"price_series", "fund_nav"}:
            raise ValueError("Performance comparison supports price_series and fund_nav only")
        columns = dataset.get("columns", {})
        time_column = dataset.get("time_column", "date")
        value_column = dataset.get("value_column", "value")
        if columns.get(time_column) != "date" or columns.get(value_column) != "number":
            raise ValueError("Comparison requires a declared date column and numeric value column")
        currency = dataset.get("currency")
        unit = dataset.get("units", {}).get(value_column)
        adjustment = dataset.get("adjustment")
        frequency = dataset.get("frequency")
        timezone = dataset.get("timezone")
        if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Comparison requires an explicitly known three-letter currency")
        if not isinstance(unit, str) or not unit.strip() or unit.casefold() in {"unknown", "not_applicable"}:
            raise ValueError("Comparison requires an explicitly known value unit")
        if adjustment not in {"unadjusted", "forward_adjusted", "backward_adjusted", "not_applicable"}:
            raise ValueError("Comparison requires an explicitly known adjustment basis")
        if frequency not in {"daily", "weekly", "monthly"}:
            raise ValueError("Comparison requires an explicit daily, weekly or monthly frequency")
        if not isinstance(timezone, str) or not timezone or timezone in {"unknown", "not_applicable"}:
            raise ValueError("Comparison requires an explicitly known market timezone")
        current_basis = (currency, unit, adjustment, frequency, timezone)
        if basis is not None and current_basis != basis:
            raise ValueError("Currency, value unit, adjustment, frequency and timezone must match; no conversion is performed")
        basis = current_basis
        rows = dataset.get("rows", [])
        if not isinstance(rows, list) or not 2 <= len(rows) <= 1000:
            raise ValueError("Each dataset must contain between 2 and 1000 observations")
        values = {}
        outside = []
        for row in rows:
            day = _day(row.get(time_column), "observation date")
            value = row.get(value_column)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Every compared value must be numeric; missing values require explicit correction")
            try:
                number = float(value)
            except (ValueError, OverflowError):
                raise ValueError("Every compared value must be finite and strictly positive") from None
            if not math.isfinite(number) or number <= 0:
                raise ValueError("Every compared value must be finite and strictly positive")
            if day in values or day in outside:
                raise ValueError("Duplicate observation dates are not permitted")
            if (start and day < start) or (end and day > end):
                outside.append(day)
            else:
                values[day] = number
        if len(values) < 2:
            raise ValueError("The requested window must retain at least two observations per dataset")
        prepared.append((dataset, values, sorted(outside)))
    date_sets = [set(values) for _, values, _ in prepared]
    if alignment == "strict" and any(days != date_sets[0] for days in date_sets[1:]):
        raise ValueError("Observation dates differ; explicitly choose intersection alignment or correct the input")
    shared = sorted(set.intersection(*date_sets))
    if len(shared) < 2:
        raise ValueError("At least two shared observation dates are required")
    curves, summaries, excluded, window_excluded = [], [], {}, {}
    for dataset, values, outside in prepared:
        initial, peak, drawdown = values[shared[0]], values[shared[0]], 0.0
        points = []
        for day in shared:
            current = values[day]
            peak = max(peak, current)
            drawdown = max(drawdown, 1.0 - current / peak)
            level = current / initial * 100.0
            if not math.isfinite(level):
                raise ValueError("Normalization exceeded the supported finite range")
            points.append({"date": day, "raw_value": current, "indexed_value": level,
                           "risk_notice": RISK_NOTICE, "noncommercial": True,
                           "is_demo": bool(dataset.get("is_demo", False))})
        period_return = (values[shared[-1]] / initial - 1.0) * 100.0
        if not math.isfinite(period_return):
            raise ValueError("Return calculation exceeded the supported finite range")
        curves.append({"dataset_id": dataset["id"], "label": dataset["title"],
                       "symbol": dataset.get("symbol", ""), "currency": basis[0], "unit": basis[1],
                       "adjustment": basis[2], "frequency": basis[3], "timezone": basis[4],
                       "points": points, "is_demo": bool(dataset.get("is_demo", False)),
                       "risk_notice": RISK_NOTICE, "noncommercial": True,
                       "metrics": {"start_date": shared[0], "end_date": shared[-1],
                                   "point_count": len(points), "period_return_pct": period_return,
                                   "max_drawdown_pct": drawdown * 100.0}})
        summaries.append({key: dataset.get(key) for key in ("id", "kind", "title", "symbol", "currency",
                         "adjustment", "frequency", "timezone", "provenance", "coverage", "is_demo")})
        summaries[-1].update(risk_notice=RISK_NOTICE, noncommercial=True)
        excluded[dataset["id"]] = sorted(set(values) - set(shared))
        window_excluded[dataset["id"]] = outside
    return envelope(summaries, curves=curves, analysis_type="deterministic_series_comparison",
                    model_calls_performed=False,
                    methods={"normalization": "index[t] = value[t] / first_aligned_value * 100",
                             "period_return": "(last_aligned_value / first_aligned_value - 1) * 100",
                             "max_drawdown": "max(1 - value[t] / running_max(value[0:t])) * 100; positive loss magnitude",
                             "return_basis": "Observed price or NAV change in the declared currency and adjustment basis; no separate dividends, fees, FX or annualization.",
                             "sampling_scope": "Drawdown uses retained observations and can miss between-observation peaks or troughs."},
                    coverage={"alignment": alignment, "common_dates": shared,
                              "excluded_dates_by_dataset": excluded, "window_excluded_dates_by_dataset": window_excluded,
                              "requested_start": start, "requested_end": end,
                              "source_coverage": {d["id"]: d.get("coverage", {}) for d, _, _ in prepared},
                              "upstream_completeness_established": False})
