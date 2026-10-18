#!/usr/bin/env python3
# Regression tests for scripts/check_readme_limitations.py.
#
# Self-contained and standard-library only. Every negative case runs against a
# TEMPORARY COPY of the README table; the real README.md and
# docs/LIMITATIONS.md are only ever read, never modified.
#
# Run:  python3 scripts/test_check_readme_limitations.py
# Exit: 0 = all tests passed, 1 = failures (unittest's own convention).
import contextlib
import importlib.util
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CHECKER = HERE / "check_readme_limitations.py"
REAL_README = REPO / "README.md"
CANONICAL = REPO / "docs" / "LIMITATIONS.md"


def load_checker():
    """Import the checker without triggering its __main__ entry point."""
    spec = importlib.util.spec_from_file_location("check_readme_limitations", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # main() is guarded by __name__ == "__main__"
    return module


def read_text(path):
    """Read a file with its handle closed (read-only)."""
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class CheckerTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chk = load_checker()
        cls.readme_text = read_text(REAL_README)
        cls.rows = [l for l in cls.readme_text.split("\n")
                    if re.match(r"^\|\s*L-\d{3}\s*\|", l)]
        assert len(cls.rows) == 28, f"expected 28 README rows, got {len(cls.rows)}"

    def run_checker(self, table_rows):
        """Run the checker's main() against a temp README carrying table_rows."""
        body = "\n".join(["# synthetic", ""] + list(table_rows) + [""]) + "\n"
        tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                          encoding="utf-8")
        try:
            tmp.write(body)
            tmp.close()
            original = self.chk.README
            self.chk.README = Path(tmp.name)
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    rc = self.chk.main()
            finally:
                self.chk.README = original
            return rc, buf.getvalue()
        finally:
            os.unlink(tmp.name)

    def assertFails(self, rows, *needles):
        rc, out = self.run_checker(rows)
        self.assertEqual(rc, 1, f"expected exit 1, got {rc}\n{out}")
        for needle in needles:
            self.assertIn(needle, out)
        return out

    def assertPasses(self, rows):
        rc, out = self.run_checker(rows)
        self.assertEqual(rc, 0, f"expected exit 0, got {rc}\n{out}")
        return out


class TestImportSafety(unittest.TestCase):
    def test_import_does_not_run_main(self):
        src = read_text(CHECKER)
        self.assertIn('if __name__ == "__main__":', src)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            load_checker()
        self.assertEqual(buf.getvalue(), "", "importing the checker printed output")

    def test_checker_has_no_write_or_shell_calls(self):
        src = read_text(CHECKER)
        self.assertIsNone(re.search(r"open\([^)]*,\s*[\"'][wa]", src))
        for banned in ("subprocess", "shutil", "pytest", "unlink", "remove("):
            self.assertNotIn(banned, src, f"checker must not use {banned}")


class TestCanonicalTable(CheckerTestBase):
    def test_1_canonical_table_passes(self):
        out = self.assertPasses(self.rows)
        self.assertIn("OK:", out)
        self.assertIn("28 entries", out)
        self.assertIn("order verified", out)

    def test_1b_real_repository_files_pass(self):
        rc, out = self.run_checker_against_repo()
        self.assertEqual(rc, 0, out)

    def run_checker_against_repo(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = self.chk.main()
        return rc, buf.getvalue()


class TestDuplicates(CheckerTestBase):
    def test_2_historical_duplicate_L001_fails(self):
        rows = self.rows + [self.rows[0]]
        out = self.assertFails(rows, "L-001", "duplicated")
        self.assertIn("table rows 1, 29", out)

    def test_2b_duplicate_of_middle_row_fails(self):
        rows = list(self.rows)
        rows.insert(10, rows[10])
        self.assertFails(rows, "L-011", "duplicated")

    def test_2c_duplicate_does_not_hide_a_title_mismatch(self):
        """A trailing duplicate must not replace the earlier entry silently."""
        rows = list(self.rows)
        rows[3] = rows[3].replace("RateLimiter Jitter Insufficient Against Adaptive WAF",
                                  "Falsification Engine ~78% catch rate")
        self.assertFails(rows + [rows[3]], "L-004", "title mismatch")


class TestOrdering(CheckerTestBase):
    def test_3_reordering_two_valid_rows_fails(self):
        rows = list(self.rows)
        rows[0], rows[1] = rows[1], rows[0]
        self.assertFails(rows, "row order mismatch at position 1",
                         "expected L-001", "README has L-002")

    def test_3b_single_row_moved_to_end_fails(self):
        rows = list(self.rows)
        moved = rows.pop(5)
        rows.append(moved)
        self.assertFails(rows, "row order mismatch")

    def test_3c_swapped_titles_only_still_fails(self):
        """Correct IDs, correct order, but wrong titles -> title mismatch, not order."""
        rows = list(self.rows)
        a, b = rows[0].split("|")[2], rows[1].split("|")[2]
        rows[0] = rows[0].replace(a, "\x00", 1).replace("\x00", b, 1)
        rows[1] = rows[1].replace(b, "\x00", 1).replace("\x00", a, 1)
        self.assertFails(rows, "title mismatch")


class TestMissingAndExtra(CheckerTestBase):
    def test_4_missing_id_fails(self):
        rows = [r for r in self.rows if not r.startswith("| L-014")]
        self.assertFails(rows, "L-014", "missing from README table")

    def test_5_unexpected_id_fails(self):
        rows = self.rows + ["| L-029 | Invented Limitation | HIGH | Nowhere |"]
        self.assertFails(rows, "L-029", "absent from docs/LIMITATIONS.md")


class TestTitles(CheckerTestBase):
    def test_6_title_mismatch_fails(self):
        rows = list(self.rows)
        rows[3] = rows[3].replace("RateLimiter Jitter Insufficient Against Adaptive WAF",
                                  "Falsification Engine ~78% catch rate")
        out = self.assertFails(rows, "L-004", "title mismatch")
        self.assertIn("canonical:", out)
        self.assertIn("README    :", out)


class TestSeverities(CheckerTestBase):
    def test_7_severity_mismatch_fails(self):
        rows = [re.sub(r"\| MEDIUM \|", "| CRITICAL |", self.rows[3])] + self.rows[4:]
        self.assertFails(rows, "L-004", "severity mismatch")

    def test_8_severity_present_where_canonical_declares_none_fails(self):
        """L-019 canonical entry declares no severity; README says '—'."""
        rows = [r.replace("| — (official assessment) |", "| MEDIUM |") if r.startswith("| L-019") else r
                for r in self.rows]
        self.assertFails(rows, "L-019", "canonical declares no severity")

    def test_8b_severity_missing_where_canonical_declares_one_fails(self):
        """L-001 canonical declares MEDIUM; README must not use '—'."""
        rows = [re.sub(r"\| MEDIUM \|", "| — |", self.rows[0])] + self.rows[1:]
        self.assertFails(rows, "L-001", "severity mismatch")


class TestCombined(CheckerTestBase):
    def test_multiple_defects_are_all_reported(self):
        rows = list(self.rows)
        rows[3] = rows[3].replace("RateLimiter Jitter Insufficient Against Adaptive WAF", "Wrong")
        rows[0], rows[1] = rows[1], rows[0]
        out = self.assertFails(rows, "row order mismatch", "L-004")
        self.assertGreaterEqual(out.count("  - "), 2)

    def test_empty_table_fails(self):
        self.assertFails([], "README limitations table not found or parsed empty")

    def test_canonical_file_missing_is_reported(self):
        original = self.chk.CANONICAL
        self.chk.CANONICAL = Path(tempfile.gettempdir()) / "definitely_absent.md"
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = self.chk.main()
            self.assertEqual(rc, 1)
            self.assertIn("missing", buf.getvalue())
        finally:
            self.chk.CANONICAL = original


class TestCanonicalOrderSource(unittest.TestCase):
    def test_canonical_defines_L001_through_L028_in_order(self):
        rows = load_checker().parse_canonical(CANONICAL)
        ids = [lid for lid, _ in rows]
        self.assertEqual(ids, [f"L-{i:03d}" for i in range(1, 29)])


if __name__ == "__main__":
    unittest.main(verbosity=2)