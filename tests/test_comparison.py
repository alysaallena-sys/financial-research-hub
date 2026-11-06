"""Arithmetic and evidence boundaries for saved series, using synthetic data."""
import copy
import unittest

from finance_research_hub import RISK_NOTICE
from finance_research_hub.comparison import compare_datasets


def series(identifier, values, days=None):
    days = days or [f"2026-01-{i+1:02d}" for i in range(len(values))]
    return {"id": identifier, "title": "Synthetic " + identifier, "symbol": "DEMO-" + identifier,
            "kind": "price_series", "columns": {"date": "date", "value": "number"},
            "time_column": "date", "value_column": "value", "units": {"value": "CNY/share"},
            "currency": "CNY", "adjustment": "unadjusted", "frequency": "daily", "timezone": "Asia/Shanghai",
            "rows": [{"date": d, "value": v} for d, v in zip(days, values)],
            "coverage": {"truncated": True}, "provenance": {"url": "https://example.com/synthetic"}, "is_demo": True}


class ComparisonTests(unittest.TestCase):
    def test_known_return_and_peak_to_trough_loss(self):
        a, b = series("a", [100, 120, 90, 108]), series("b", [50, 45, 60, 60])
        original = copy.deepcopy([a, b])
        result = compare_datasets([a, b])
        self.assertEqual([a, b], original)
        first = result["curves"][0]
        self.assertAlmostEqual(first["metrics"]["period_return_pct"], 8)
        self.assertAlmostEqual(first["metrics"]["max_drawdown_pct"], 25)
        self.assertEqual([p["indexed_value"] for p in first["points"]], [100, 120, 90, 108])
        self.assertAlmostEqual(result["curves"][1]["metrics"]["period_return_pct"], 20)
        self.assertAlmostEqual(result["curves"][1]["metrics"]["max_drawdown_pct"], 10)
        self.assertFalse(result["model_calls_performed"])
        self.assertEqual(result["mode"], "demo")
        self.assertTrue(result["coverage"]["source_coverage"]["a"]["truncated"])
        for curve in result["curves"]:
            for point in curve["points"]:
                self.assertEqual(point["risk_notice"], RISK_NOTICE)

    def test_mismatched_dates_require_explicit_intersection_without_fill(self):
        a = series("a", [100, 110, 120])
        b = series("b", [100, 130], ["2026-01-01", "2026-01-03"])
        with self.assertRaisesRegex(ValueError, "dates differ"):
            compare_datasets([a, b])
        result = compare_datasets([a, b], alignment="intersection")
        self.assertEqual(result["coverage"]["common_dates"], ["2026-01-01", "2026-01-03"])
        self.assertEqual(result["coverage"]["excluded_dates_by_dataset"]["a"], ["2026-01-02"])
        self.assertEqual(len(result["curves"][0]["points"]), 2)

    def test_date_window_changes_the_baseline_and_discloses_excluded_periods(self):
        result = compare_datasets([series("a", [100, 50, 75]), series("b", [50, 100, 110])], start="2026-01-02")
        self.assertAlmostEqual(result["curves"][0]["metrics"]["period_return_pct"], 50)
        self.assertEqual(result["curves"][0]["points"][0]["indexed_value"], 100)
        self.assertEqual(result["coverage"]["window_excluded_dates_by_dataset"]["a"], ["2026-01-01"])

    def test_unknown_or_incompatible_basis_is_rejected(self):
        a = series("a", [10, 11])
        for field, value in [("currency", None), ("currency", "USD"), ("adjustment", "unknown"),
                             ("adjustment", "forward_adjusted"), ("frequency", "unknown"),
                             ("frequency", "weekly"), ("timezone", None), ("timezone", "America/New_York")]:
            b = series("b", [20, 21]); b[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                compare_datasets([a, b])
        b = series("b", [20, 21]); b["units"]["value"] = "USD/share"
        with self.assertRaises(ValueError): compare_datasets([a, b])

    def test_no_implicit_numeric_conversion_missing_values_or_duplicate_dates(self):
        for value in [None, "12", True, float("nan"), float("inf"), 0, -1]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare_datasets([series("a", [10, 11]), series("b", [20, value])])
        b = series("b", [20, 21], ["2026-01-01", "2026-01-01"])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compare_datasets([series("a", [10, 11]), b])

    def test_invalid_scope_macro_intraday_and_calendar_values_are_rejected(self):
        a = series("a", [10, 11])
        b = series("b", [20, 21])
        with self.assertRaises(ValueError): compare_datasets([a])
        with self.assertRaises(ValueError): compare_datasets([a, a])
        with self.assertRaises(ValueError): compare_datasets([a, b], start="2026-02-30")
        with self.assertRaises(ValueError): compare_datasets([a, b], start="2026-01-03", end="2026-01-01")
        with self.assertRaises(ValueError): compare_datasets([a, b], alignment="forward_fill")
        b["is_demo"] = False
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            compare_datasets([a, b])
        b["is_demo"] = True
        for kind in ["macro_series", "bond_profile"]:
            b["kind"] = kind
            with self.assertRaises(ValueError): compare_datasets([a, b])
        b["kind"] = "price_series"; b["columns"]["date"] = "datetime"
        with self.assertRaises(ValueError): compare_datasets([a, b])


if __name__ == "__main__":
    unittest.main()
