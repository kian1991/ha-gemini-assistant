"""Tests for the stored HA LLM API selection normalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "gemini_live"

UTILS_SPEC = importlib.util.spec_from_file_location(
    "gemini_live_utils", COMPONENT / "utils.py"
)
assert UTILS_SPEC is not None and UTILS_SPEC.loader is not None
utils = importlib.util.module_from_spec(UTILS_SPEC)
sys.modules[UTILS_SPEC.name] = utils
UTILS_SPEC.loader.exec_module(utils)

CONST_SPEC = importlib.util.spec_from_file_location(
    "gemini_live_const", COMPONENT / "const.py"
)
assert CONST_SPEC is not None and CONST_SPEC.loader is not None
const = importlib.util.module_from_spec(CONST_SPEC)
sys.modules[CONST_SPEC.name] = const
CONST_SPEC.loader.exec_module(const)

normalize = utils.normalize_llm_api_selection
DEFAULT = const.DEFAULT_LLM_HASS_API


class NormalizeLlmApiSelectionTests(unittest.TestCase):
    """Exercise legacy defaults, explicit selections, and bad stored values."""

    def test_missing_value_uses_legacy_default(self) -> None:
        self.assertEqual(normalize(None, DEFAULT), ["assist"])

    def test_missing_value_returns_copy_of_default(self) -> None:
        result = normalize(None, DEFAULT)
        result.append("mutated")
        self.assertEqual(DEFAULT, ["assist"])

    def test_explicit_empty_selection_stays_empty(self) -> None:
        self.assertEqual(normalize([], DEFAULT), [])

    def test_single_string_becomes_list(self) -> None:
        self.assertEqual(normalize("assist", DEFAULT), ["assist"])

    def test_multiple_apis_preserved_in_order(self) -> None:
        selection = ["assist", "mcp-abc123", "mcp-def456"]
        self.assertEqual(normalize(selection, DEFAULT), selection)

    def test_duplicates_and_invalid_entries_removed(self) -> None:
        self.assertEqual(
            normalize(["assist", "assist", "", None, 7, "mcp-x"], DEFAULT),
            ["assist", "mcp-x"],
        )

    def test_unexpected_type_falls_back_to_default(self) -> None:
        self.assertEqual(normalize({"api": "assist"}, DEFAULT), ["assist"])
        self.assertEqual(normalize(42, DEFAULT), ["assist"])


if __name__ == "__main__":
    unittest.main()
