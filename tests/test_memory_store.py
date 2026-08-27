"""Tests for the local durable memory store."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "gemini_live"
    / "memory_store.py"
)
SPEC = importlib.util.spec_from_file_location("gemini_memory_store", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
memory_store = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = memory_store
SPEC.loader.exec_module(memory_store)

MemoryStore = memory_store.MemoryStore
MemoryStoreError = memory_store.MemoryStoreError


class MemoryStoreTests(unittest.TestCase):
    """Exercise persistence, editing, validation, and index behavior."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.path = Path(self.temporary_directory.name)
        self.store = MemoryStore(self.path)

    def test_memory_survives_new_store_instance(self) -> None:
        self.store.save(
            "bathroom_lighting",
            "preference",
            "Preferred cozy bathroom lighting",
            "Kian prefers 2700 K at 35 percent when asking for cozy lighting.",
        )

        restarted_store = MemoryStore(self.path)
        record = restarted_store.read("bathroom_lighting")

        self.assertEqual(record.memory_type, "preference")
        self.assertIn("2700 K", record.content)
        self.assertIn("bathroom_lighting", restarted_store.read_index())

    def test_save_updates_existing_memory_without_changing_creation_time(self) -> None:
        original = self.store.save(
            "coffee",
            "preference",
            "Coffee preference",
            "Kian likes lighter roasts.",
        )
        updated = self.store.save(
            "coffee",
            "preference",
            "Current coffee preference",
            "Kian likes light, fruity roasts and avoids very dark roasts.",
        )

        self.assertEqual(updated.created_at, original.created_at)
        self.assertEqual(len(self.store.list_records()), 1)
        self.assertIn("fruity", self.store.read("coffee").content)

    def test_delete_removes_file_and_index_entry(self) -> None:
        self.store.save(
            "bedroom_name",
            "terminology",
            "Bedroom terminology",
            "Kian calls this room Schlafzimmer.",
        )

        self.store.delete("bedroom_name")

        self.assertNotIn("bedroom_name", self.store.read_index())
        with self.assertRaises(MemoryStoreError):
            self.store.read("bedroom_name")

    def test_rejects_path_traversal_and_unsafe_names(self) -> None:
        for invalid_name in ("../secret", "BadName", "with-dash", "", "a" * 65):
            with self.subTest(name=invalid_name):
                with self.assertRaises(MemoryStoreError):
                    self.store.save(
                        invalid_name,
                        "other",
                        "Invalid memory",
                        "This must never be written.",
                    )

        self.assertFalse((self.path.parent / "secret.md").exists())

    def test_rejects_oversized_or_unknown_fields(self) -> None:
        with self.assertRaises(MemoryStoreError):
            self.store.save("large", "other", "x" * 201, "content")
        with self.assertRaises(MemoryStoreError):
            self.store.save("large", "other", "description", "x" * 4001)
        with self.assertRaises(MemoryStoreError):
            self.store.save("wrong_type", "secret", "description", "content")

    def test_manual_markdown_edit_is_used_by_the_live_index(self) -> None:
        self.store.save(
            "office_light",
            "preference",
            "Old office lighting preference",
            "Use neutral light.",
        )
        path = self.path / "office_light.md"
        edited = path.read_text(encoding="utf-8").replace(
            'description: "Old office lighting preference"',
            'description: "Manually edited office lighting preference"',
        ).replace("Use neutral light.", "Use warm light after sunset.")
        path.write_text(edited, encoding="utf-8")

        self.assertIn("warm light", self.store.read("office_light").content)
        self.assertIn("Manually edited", self.store.read_index())

    def test_invalid_manual_file_does_not_hide_valid_memories(self) -> None:
        self.store.save(
            "valid_memory",
            "other",
            "A valid memory",
            "This record remains available.",
        )
        (self.path / "broken.md").write_text("not front matter", encoding="utf-8")

        records = self.store.list_records()

        self.assertEqual([record.name for record in records], ["valid_memory"])


if __name__ == "__main__":
    unittest.main()
