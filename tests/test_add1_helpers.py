"""
Unit tests for pure helper functions in lisflood.global_modules.add1 that are
not exercised by the end-to-end suite.

Scope is limited to functions with real branching / edge-case logic where a
regression could slip through silently:

  * generateName    - 8.3 "DOS style" timestep filename builder with several
                      validation branches.
  * takeClosest     - bisect-based "closest left value" lookup with boundary
                      behavior.
  * read_tss_header - .tss header parser with two format branches (with header
                      vs bare table), used by the inflow module.

These are characterization tests: they pin the current behavior so a future
refactor is caught.
"""

import os

import pytest

from lisflood.global_modules.add1 import generateName, takeClosest, read_tss_header
from lisflood.global_modules.errors import LisfloodError


class TestGenerateName:
    """8.3-style name: <tail><zeros><timestep>, total 12 chars incl. the dot,
    directory preserved."""

    def test_pads_timestep_into_8_3_format(self):
        # 'dis' (3) + timestep 5 -> zero-filled to 8 chars before the dot
        assert generateName("dis", 5) == "dis00000.005"

    def test_large_timestep_fills_available_width(self):
        # space = 11 - (len('dis') + len('12345')) = 3 zeros -> 'dis00012345',
        # then split into 8.3 -> 'dis00012.345'
        assert generateName("dis", 12345) == "dis00012.345"

    def test_directory_component_is_preserved(self):
        result = generateName(os.path.join("out", "dis"), 5)
        assert result == os.path.join("out", "dis00000.005")

    def test_extension_in_name_is_rejected(self):
        with pytest.raises(LisfloodError):
            generateName("dis.map", 5)

    def test_empty_filename_is_rejected(self):
        with pytest.raises(LisfloodError):
            generateName("", 5)

    def test_name_longer_than_8_chars_is_rejected(self):
        with pytest.raises(LisfloodError):
            generateName("longname9", 5)

    def test_negative_timestep_is_rejected(self):
        with pytest.raises(LisfloodError):
            generateName("dis", -1)


class TestTakeClosest:
    """Returns the closest left (<=) value in a sorted list; clamps at both
    ends."""

    def test_exact_match_returns_left_neighbor(self):
        # bisect_left on an exact match points at it, so 'before' is returned
        assert takeClosest([0, 10, 20, 30], 20) == 10

    def test_between_values_returns_lower(self):
        assert takeClosest([0, 10, 20, 30], 17) == 10

    def test_below_range_clamps_to_first(self):
        assert takeClosest([0, 10, 20], -5) == 0

    def test_above_range_clamps_to_last(self):
        assert takeClosest([0, 10, 20], 999) == 20


class TestReadTssHeader:
    """Parses a LISFLOOD .tss file header. Two branches: a 'timeseries' header
    (returns the listed outlet IDs) or a bare table (returns 1..N-1 column
    indices)."""

    def _write(self, tmp_path, content):
        f = tmp_path / "series.tss"
        f.write_text(content)
        return str(f)

    def test_with_timeseries_header_returns_outlet_ids(self, tmp_path):
        # header format: 'timeseries ...', then a count, a title line, then
        # (count-1) outlet id lines, then data.
        content = (
            "timeseries scalar\n"
            "3\n"
            "timestep\n"
            "101\n"
            "202\n"
            "1 1.0 2.0\n"
        )
        path = self._write(tmp_path, content)
        assert read_tss_header(path) == [101, 202]

    def test_bare_table_returns_column_indices(self, tmp_path):
        # no 'timeseries' keyword: first row has N whitespace columns, header
        # is the progressive indices 1..N-1 (first column is the timestep).
        content = "1 3.14 2.71 9.9\n2 1.0 2.0 3.0\n"
        path = self._write(tmp_path, content)
        assert read_tss_header(path) == [1, 2, 3]
