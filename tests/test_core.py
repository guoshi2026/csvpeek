"""Unit tests for csvpeek.core. Run with: python -m unittest discover -s tests -v"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from csvpeek.core import load_from_text, profile_csv, render_table, to_json  # noqa: E402

SAMPLE = """id,name,score,active,joined
1,Alice,91.5,true,2024-01-05
2,Bob,78,false,2024-02-11
3,Carol,,true,2024-03-30
4,Dave,88.25,true,2024-01-19
"""


class TestProfiling(unittest.TestCase):
    def setUp(self) -> None:
        self.profiles = {p.name: p for p in load_from_text(SAMPLE)}

    def test_infers_numeric_and_text_types(self):
        self.assertEqual(self.profiles["id"].kind, "int")
        self.assertEqual(self.profiles["name"].kind, "text")
        self.assertEqual(self.profiles["score"].kind, "float")

    def test_detects_bool_and_date(self):
        self.assertEqual(self.profiles["active"].kind, "bool")
        self.assertEqual(self.profiles["joined"].kind, "date")

    def test_counts_nulls(self):
        self.assertEqual(self.profiles["score"].nulls, 1)
        self.assertEqual(self.profiles["name"].nulls, 0)
        self.assertEqual(self.profiles["id"].total, 4)

    def test_numeric_range_and_mean(self):
        score = self.profiles["score"]
        self.assertAlmostEqual(score.minimum, 78.0)
        self.assertAlmostEqual(score.maximum, 91.5)
        self.assertAlmostEqual(score.mean, (91.5 + 78 + 88.25) / 3, places=6)

    def test_cardinality(self):
        self.assertEqual(self.profiles["name"].unique, 4)
        self.assertEqual(self.profiles["active"].unique, 2)

    def test_bool_mean_is_true_ratio(self):
        self.assertAlmostEqual(self.profiles["active"].mean, 0.75)

    def test_date_range_is_lexicographic_after_parse(self):
        joined = self.profiles["joined"]
        self.assertEqual(joined.minimum, "2024-01-05")
        self.assertEqual(joined.maximum, "2024-03-30")


class TestOutput(unittest.TestCase):
    def test_json_shape(self):
        payload = to_json(load_from_text(SAMPLE))
        self.assertEqual(payload["column_count"], 5)
        self.assertEqual(payload["row_count"], 4)
        self.assertEqual(payload["columns"][0]["name"], "id")

    def test_table_contains_header_and_columns(self):
        table = render_table(load_from_text(SAMPLE))
        self.assertIn("COLUMN", table)
        self.assertIn("joined", table)
        self.assertEqual(len(table.splitlines()), 7)  # header + separator + 5 columns


class TestFileInput(unittest.TestCase):
    def test_reads_file_and_sniffs_semicolon(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as fh:
            fh.write("a;b\n1;x\n2;y\n")
            path = fh.name
        try:
            profiles = {p.name: p for p in profile_csv(path)}
            self.assertEqual(set(profiles), {"a", "b"})
            self.assertEqual(profiles["a"].kind, "int")
        finally:
            os.unlink(path)

    def test_empty_file_returns_no_profiles(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            path = fh.name
        try:
            self.assertEqual(profile_csv(path), [])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
