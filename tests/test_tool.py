import contextlib
import io
from pathlib import Path
import tempfile
import unittest
import chronogapledger as tool


class StampChecks(unittest.TestCase):
    def run_text(self, text, **kwargs):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "时间.txt"
            path.write_text(text, encoding="utf-8-sig")
            before = path.read_bytes()
            report = tool.inspect_stamps(path, **kwargs)
            self.assertEqual(path.read_bytes(), before)
            return report

    def test_inclusive_threshold(self):
        text = "2026-01-01T00:00:00Z\n2026-01-01T00:01:00Z\n"
        self.assertEqual(self.run_text(text)["gaps"], 1)
        self.assertEqual(self.run_text(text, alert_seconds=61)["gaps"], 0)

    def test_offsets_and_fraction(self):
        text = "2026-01-01T08:00:00+08:00\n2026-01-01T00:00:00.500000Z\n"
        report = self.run_text(text, alert_seconds=.5)
        self.assertEqual(report["details"][0]["seconds"], .5)
        self.assertEqual(report["gaps"], 1)

    def test_invalid_breaks_but_blank_does_not(self):
        text = "2026-01-01 00:00:00\n\n2026-01-01 00:02:00\nbad\n2026-01-01 00:10:00\n"
        report = self.run_text(text)
        self.assertEqual((report["blank_lines"], report["invalid_timestamps"], report["compared_pairs"], report["gaps"]), (1, 1, 1, 1))

    def test_order_duplicate_and_mixed_timezones(self):
        text = "2026-01-01 00:02:00\n2026-01-01 00:01:00\n2026-01-01 00:01:00\n2026-01-01T00:01:00Z\n"
        report = self.run_text(text)
        self.assertEqual((report["backwards"], report["duplicates"], report["timezone_mismatches"]), (1, 1, 1))

    def test_malformed_dates_and_limits(self):
        report = self.run_text("2026-02-30T12:00:00\n2026-01-01\n2026-01-01T00:00:00 trailing\n", max_details=1)
        self.assertEqual(report["invalid_timestamps"], 3)
        self.assertTrue(report["details_truncated"])
        self.assertEqual(len(report["details"]), 1)

    def test_empty_and_bad_settings(self):
        self.assertEqual(self.run_text("")["valid_timestamps"], 0)
        for value in [0, -1, "nan", "inf"]:
            with self.assertRaises(ValueError):
                self.run_text("", alert_seconds=value)

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.txt"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                path.write_text("2026-01-01 00:00:00\n2026-01-01 00:00:01\n", encoding="utf-8")
                self.assertEqual(tool.main([str(path)]), 0)
                path.write_text("not a timestamp", encoding="utf-8")
                self.assertEqual(tool.main([str(path)]), 1)
                self.assertEqual(tool.main([str(path), "--encoding", "missing-encoding"]), 2)


if __name__ == "__main__":
    unittest.main()
