"""Typed, source-attributed numeric evidence kept separate from news records."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import RISK_NOTICE
from .core import canonical, safe_url

DATASET_KINDS = {"price_series", "fund_nav", "bond_profile", "macro_series"}
COLUMN_TYPES = {"number", "string", "date", "datetime", "boolean"}
ADJUSTMENTS = {"unadjusted", "forward_adjusted", "backward_adjusted", "not_applicable", "unknown"}
FREQUENCIES = {"daily", "weekly", "monthly", "annual", "unknown"}
POLICY_FIELDS = {"risk_notice", "noncommercial", "is_demo"}
MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000
MAX_COLUMNS = 32
CONTENT_HASH_BASIS = "sha256 of canonical normalized saved dataset before query metadata"


def text(value: Any, name: str, maximum: int = 200, *, required: bool = False) -> str | None:
    if value in (None, "") and not required:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError(f"{name} must be nonempty text of at most {maximum} characters without control characters")
    return value


def dataset_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("dataset_id must be a 64-character lowercase hexadecimal ID")
    return value


def _date_value(value: Any, kind: str, name: str) -> str:
    result = text(value, name, 64, required=True)
    assert result is not None
    try:
        if kind == "date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", result):
                raise ValueError()
            date.fromisoformat(result)
        else:
            if "T" not in result:
                raise ValueError()
            datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO {kind}") from exc
    return result


def _as_of(value: Any) -> str | None:
    value = text(value, "as_of", 64)
    if value is None:
        return None
    if re.fullmatch(r"\d{4}", value):
        if not 1 <= int(value) <= 9999:
            raise ValueError("Invalid as_of year")
        return value
    if re.fullmatch(r"\d{4}-\d{2}", value):
        _date_value(value + "-01", "date", "as_of")
        return value
    return _date_value(value, "datetime" if "T" in value else "date", "as_of")


def normalize_dataset(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Dataset import must be one JSON object")
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in DATASET_KINDS:
        raise ValueError("Unknown numeric dataset kind")
    source_id = text(raw.get("source_id"), "source_id", 300, required=True)
    title = text(raw.get("title"), "title", 1000, required=True)
    if not isinstance(raw.get("is_demo"), bool):
        raise ValueError("Dataset is_demo must be an explicit boolean")
    is_demo = raw["is_demo"]
    missing: set[str] = set()
    symbol = text(raw.get("symbol"), "symbol", 100)
    market = text(raw.get("market"), "market", 100)
    currency = text(raw.get("currency"), "currency", 32)
    if currency is not None and currency != "not_applicable" and not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("currency must be a three-letter uppercase code, not_applicable, or null")
    timezone = text(raw.get("timezone"), "timezone", 100)
    if timezone is not None and timezone != "not_applicable":
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be an IANA timezone, not_applicable, or null") from exc
    as_of = _as_of(raw.get("as_of"))
    adjustment = raw.get("adjustment")
    if adjustment in (None, ""):
        adjustment = "unknown"
    if not isinstance(adjustment, str) or adjustment not in ADJUSTMENTS:
        raise ValueError("Unknown adjustment basis")
    for key, value in (("symbol", symbol), ("market", market), ("currency", currency), ("timezone", timezone), ("as_of", as_of)):
        if value is None:
            missing.add(key)
    if adjustment == "unknown":
        missing.add("adjustment")
    frequency = raw.get("frequency")
    if frequency in (None, ""):
        frequency = "unknown"
    if not isinstance(frequency, str) or frequency not in FREQUENCIES:
        raise ValueError("Unknown observation frequency")
    if frequency == "unknown":
        missing.add("frequency")
    provenance_raw = raw.get("provenance")
    if not isinstance(provenance_raw, dict):
        raise ValueError("provenance must be an object")
    provenance = {}
    for key, value in provenance_raw.items():
        if not isinstance(key, str) or len(key) > 100:
            raise ValueError("Invalid provenance key")
        text(key, "provenance key", 100, required=True)
        provenance[key] = text(value, "provenance." + key, 2048)
    provider = text(provenance.get("provider"), "provenance.provider", 200, required=True)
    provenance["provider"] = provider
    provenance["url"] = safe_url(str(provenance.get("url") or ""))
    retrieved = provenance.get("retrieved_at")
    if retrieved is not None:
        provenance["retrieved_at"] = _date_value(retrieved, "datetime", "provenance.retrieved_at")
        if datetime.fromisoformat(retrieved.replace("Z", "+00:00")).tzinfo is None:
            missing.add("provenance.retrieved_at_timezone")
    for key in ("original_publisher", "retrieved_at", "source_version", "identity_basis"):
        if not provenance.get(key):
            missing.add("provenance." + key)
    columns = raw.get("columns")
    if not isinstance(columns, dict) or not 1 <= len(columns) <= MAX_COLUMNS:
        raise ValueError("columns must declare between 1 and 32 typed fields")
    for key, declared in columns.items():
        text(key, "column name", 64, required=True)
        if key in POLICY_FIELDS or not isinstance(declared, str) or declared not in COLUMN_TYPES:
            raise ValueError("Column names cannot use policy fields, and column types must be declared")
    units_raw = raw.get("units", {})
    if not isinstance(units_raw, dict) or any(key not in columns for key in units_raw):
        raise ValueError("units must be an object keyed by declared columns")
    units = {key: text(units_raw.get(key), "units." + key, 100) for key in columns if columns[key] == "number" or key in units_raw}
    for key, declared in columns.items():
        if declared == "number" and not units.get(key):
            missing.add("units." + key)
    time_column = text(raw.get("time_column"), "time_column", 64)
    value_column = text(raw.get("value_column"), "value_column", 64)
    if kind in {"price_series", "fund_nav"}:
        time_column, value_column = time_column or "date", value_column or "value"
    if time_column is not None and (time_column not in columns or columns[time_column] not in {"date", "datetime"}):
        raise ValueError("time_column must name a declared date or datetime column")
    if value_column is not None and (value_column not in columns or columns[value_column] != "number"):
        raise ValueError("value_column must name a declared number column")
    rows_raw = raw.get("rows")
    if not isinstance(rows_raw, list) or len(rows_raw) > MAX_ROWS:
        raise ValueError("rows must be a list of at most 1000 typed records")
    rows = []
    null_counts = {key: 0 for key in columns}
    for index, raw_row in enumerate(rows_raw):
        if not isinstance(raw_row, dict) or any(key not in columns and key not in POLICY_FIELDS for key in raw_row):
            raise ValueError(f"rows[{index}] contains undeclared fields")
        row = {}
        for key, declared in columns.items():
            value = raw_row.get(key)
            if value is None:
                null_counts[key] += 1
                missing.add("rows." + key)
            elif declared == "number":
                try:
                    valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                except (ValueError, OverflowError):
                    valid = False
                if not valid:
                    raise ValueError(f"rows[{index}].{key} must be a finite JSON number or null; numeric strings need explicit conversion")
            elif declared == "boolean":
                if not isinstance(value, bool):
                    raise ValueError(f"rows[{index}].{key} must be boolean or null")
            elif declared in {"date", "datetime"}:
                value = _date_value(value, declared, f"rows[{index}].{key}")
            else:
                value = text(value, f"rows[{index}].{key}", 4096, required=True)
            row[key] = value
        row.update(risk_notice=RISK_NOTICE, noncommercial=True, is_demo=is_demo)
        rows.append(row)
    if not rows:
        missing.add("rows")
    coverage_raw = raw.get("coverage", {})
    if not isinstance(coverage_raw, dict):
        raise ValueError("coverage must be an object")
    # Retain caller-declared coverage without treating it as independently verified.
    coverage = json.loads(canonical(coverage_raw))
    if coverage.get("truncated") is not None and not isinstance(coverage["truncated"], bool):
        raise ValueError("coverage.truncated must be true, false, or null")
    coverage.setdefault("truncated", None)
    total_rows = coverage.get("total_rows")
    if total_rows is not None:
        if not isinstance(total_rows, int) or isinstance(total_rows, bool) or total_rows < len(rows):
            raise ValueError("coverage.total_rows must be an integer not smaller than the saved row count, or null")
        if coverage["truncated"] is False and total_rows != len(rows):
            raise ValueError("coverage.total_rows conflicts with truncated=false")
    if coverage["truncated"] is None:
        missing.add("coverage.truncated")
    coverage["returned_rows"] = len(rows)
    coverage["scope"] = "Saved local dataset; coverage and provenance are caller declarations, not independent source acceptance."
    topics_raw = raw.get("topics", [])
    if not isinstance(topics_raw, list) or len(topics_raw) > 20:
        raise ValueError("topics must contain at most 20 explicit labels")
    topics = list(dict.fromkeys(text(value, "topic", 100, required=True) for value in topics_raw))
    related = raw.get("related_record_ids", [])
    if not isinstance(related, list) or len(related) > 100:
        raise ValueError("related_record_ids must contain at most 100 exact IDs")
    related = list(dict.fromkeys(dataset_id(value) for value in related))
    identity = hashlib.sha256(f"dataset\0{provider}\0{kind}\0{source_id}".encode()).hexdigest()
    if raw.get("id") is not None and raw["id"] != identity:
        raise ValueError("Supplied dataset ID does not match provider, kind and source_id")
    return {"id": identity, "source_id": source_id, "kind": kind, "title": title, "symbol": symbol,
            "market": market, "currency": currency, "units": units, "as_of": as_of,
            "timezone": timezone, "adjustment": adjustment, "provenance": provenance,
            "frequency": frequency,
            "columns": dict(columns), "rows": rows, "row_count": len(rows),
            "time_column": time_column, "value_column": value_column,
            "coverage": coverage, "missing_fields": sorted(missing), "null_counts": null_counts,
            "topics": topics, "related_record_ids": related,
            "risk_notice": RISK_NOTICE, "noncommercial": True, "is_demo": is_demo}


def dataset_summary(dataset: dict[str, Any], *, preview_rows: int = 5) -> dict[str, Any]:
    preview = dataset["rows"][:preview_rows]
    return {key: value for key, value in dataset.items() if key != "rows"} | {
        "rows_preview": [{**row, "risk_notice": RISK_NOTICE, "noncommercial": True, "is_demo": dataset["is_demo"]}
                         for row in preview], "rows_omitted": len(dataset["rows"]) > len(preview),
        "is_summary": True,
        "row_count": len(dataset["rows"]), "risk_notice": RISK_NOTICE, "noncommercial": True,
    }


def dataset_chunks(dataset: dict[str, Any], *, max_rows: int = 5) -> list[dict[str, Any]]:
    if not isinstance(max_rows, int) or isinstance(max_rows, bool) or not 1 <= max_rows <= 1000:
        raise ValueError("Dataset chunk row limit must be 1..1000")
    all_rows = dataset.get("rows", dataset.get("rows_preview", []))
    total_rows = dataset.get("row_count", len(all_rows))
    selected = all_rows[:max_rows]
    context = {key: dataset.get(key) for key in ("symbol", "market", "currency", "units", "as_of", "timezone", "adjustment", "frequency", "missing_fields", "coverage", "content_hash", "hash_basis")}
    contents = selected or [{"record_type": "notice", "risk_notice": RISK_NOTICE,
                             "noncommercial": True, "is_demo": dataset["is_demo"]}]
    return [{"record_type": "dataset_chunk", "dataset_id": dataset["id"], "row_index": index if selected else None,
             "risk_notice": RISK_NOTICE, "noncommercial": True, "is_demo": dataset["is_demo"],
             "source_url": dataset["provenance"]["url"],
             "content_hash": dataset.get("content_hash"), "hash_basis": dataset.get("hash_basis"),
             "rows_returned": len(selected), "total_rows": total_rows,
             "truncated": total_rows > len(selected), "context": context,
             "content": RISK_NOTICE + "\nNoncommercial numeric evidence. Source declarations require verification.\n"
                        + str(dataset["title"]) + "\n" + canonical(row) + "\nContext: " + canonical(context)
                        + "\nProvenance: " + canonical(dataset["provenance"])}
            for index, row in enumerate(contents)]


def demo_datasets() -> list[dict[str, Any]]:
    """Two synthetic daily series for local workflow and arithmetic acceptance."""
    return [{"source_id": "demo-price-" + suffix, "kind": "price_series", "title": "示例价格序列 " + suffix.upper(),
             "symbol": "DEMO-CN", "market": "synthetic", "currency": "CNY", "units": {"value": "CNY/share"},
             "as_of": "2026-01-07", "timezone": "Asia/Shanghai", "adjustment": "unadjusted", "frequency": "daily",
             "provenance": {"provider": "demo", "url": "https://example.com/datasets/demo-" + suffix,
                            "original_publisher": "Synthetic fixture", "retrieved_at": "2026-01-08T00:00:00+00:00",
                            "source_version": "synthetic-0.3", "identity_basis": "Explicit synthetic label; no real security"},
             "columns": {"date": "date", "value": "number"}, "time_column": "date", "value_column": "value",
             "rows": [{"date": day, "value": value} for day, value in zip(("2026-01-05", "2026-01-06", "2026-01-07"), values)],
             "topics": ["示例", "synthetic"], "related_record_ids": [],
             "coverage": {"truncated": False, "total_rows": 3, "scope": "synthetic example only"}, "is_demo": True}
            for suffix, values in (("a", (100, 102, 101)), ("b", (100, 99, 103)))]
