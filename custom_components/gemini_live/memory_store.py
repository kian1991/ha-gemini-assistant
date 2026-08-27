"""Local Markdown-backed storage for durable assistant memories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import tempfile

_LOGGER = logging.getLogger(__name__)

INDEX_FILENAME = "MEMORY.md"
VALID_MEMORY_TYPES = (
    "preference",
    "home",
    "routine",
    "terminology",
    "person",
    "other",
)
MAX_MEMORIES = 100
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 200
MAX_CONTENT_LENGTH = 4000

_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


class MemoryStoreError(Exception):
    """Raised when a memory cannot be validated or stored safely."""


@dataclass(frozen=True)
class MemoryRecord:
    """One durable memory and its human-editable metadata."""

    name: str
    memory_type: str
    description: str
    content: str
    created_at: str
    updated_at: str


def _now_iso() -> str:
    """Return a stable UTC timestamp suitable for Markdown front matter."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _encode_scalar(value: str) -> str:
    """Encode a metadata string as a single, safely parseable line."""
    return json.dumps(value, ensure_ascii=False)


def _decode_scalar(value: str) -> str:
    """Decode a JSON-quoted scalar while accepting simple manual edits."""
    value = value.strip()
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return value
    return decoded if isinstance(decoded, str) else str(decoded)


class MemoryStore:
    """Synchronous file store; Home Assistant calls it through its executor."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    @property
    def index_path(self) -> Path:
        """Return the generated human-readable index path."""
        return self.path / INDEX_FILENAME

    def save(
        self,
        name: str,
        memory_type: str,
        description: str,
        content: str,
    ) -> MemoryRecord:
        """Create or replace one memory atomically."""
        self._validate(name, memory_type, description, content)
        target = self._memory_path(name)
        existing: MemoryRecord | None = None
        if target.exists():
            existing = self._read_path(target)
        elif len(self.list_records()) >= MAX_MEMORIES:
            raise MemoryStoreError(f"memory limit reached ({MAX_MEMORIES})")

        now = _now_iso()
        record = MemoryRecord(
            name=name,
            memory_type=memory_type,
            description=description.strip(),
            content=content.strip(),
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._atomic_write(target, self._render_record(record))
        self._write_index()
        return record

    def read(self, name: str) -> MemoryRecord:
        """Read a memory by its validated identifier."""
        self._validate_name(name)
        target = self._memory_path(name)
        if not target.exists():
            raise MemoryStoreError(f"memory not found: {name}")
        return self._read_path(target)

    def delete(self, name: str) -> None:
        """Delete one memory and rebuild the index."""
        self._validate_name(name)
        target = self._memory_path(name)
        if not target.exists():
            raise MemoryStoreError(f"memory not found: {name}")
        target.unlink()
        self._write_index()

    def list_records(self) -> list[MemoryRecord]:
        """Return all valid memories sorted by identifier."""
        records: list[MemoryRecord] = []
        for path in sorted(self.path.glob("*.md")):
            if path.name == INDEX_FILENAME:
                continue
            try:
                records.append(self._read_path(path))
            except MemoryStoreError as err:
                _LOGGER.warning("Ignoring invalid memory file %s: %s", path, err)
        return records

    def read_index(self) -> str:
        """Build the current index from files so manual edits are reflected."""
        return self._render_index(self.list_records())

    def _memory_path(self, name: str) -> Path:
        return self.path / f"{name}.md"

    @staticmethod
    def _validate_name(name: str) -> None:
        if (
            not isinstance(name, str)
            or len(name) > MAX_NAME_LENGTH
            or not _NAME_PATTERN.fullmatch(name)
        ):
            raise MemoryStoreError(
                "name must contain only lowercase letters, numbers, and underscores "
                f"and be at most {MAX_NAME_LENGTH} characters"
            )

    @classmethod
    def _validate(
        cls,
        name: str,
        memory_type: str,
        description: str,
        content: str,
    ) -> None:
        cls._validate_name(name)
        if memory_type not in VALID_MEMORY_TYPES:
            raise MemoryStoreError(
                f"invalid memory type; choose one of: {', '.join(VALID_MEMORY_TYPES)}"
            )
        if not isinstance(description, str) or not description.strip():
            raise MemoryStoreError("description must not be empty")
        if len(description) > MAX_DESCRIPTION_LENGTH:
            raise MemoryStoreError(
                f"description exceeds {MAX_DESCRIPTION_LENGTH} characters"
            )
        if not isinstance(content, str) or not content.strip():
            raise MemoryStoreError("content must not be empty")
        if len(content) > MAX_CONTENT_LENGTH:
            raise MemoryStoreError(f"content exceeds {MAX_CONTENT_LENGTH} characters")

    @staticmethod
    def _render_record(record: MemoryRecord) -> str:
        return (
            "---\n"
            f"name: {_encode_scalar(record.name)}\n"
            f"type: {_encode_scalar(record.memory_type)}\n"
            f"description: {_encode_scalar(record.description)}\n"
            f"created_at: {_encode_scalar(record.created_at)}\n"
            f"updated_at: {_encode_scalar(record.updated_at)}\n"
            "---\n\n"
            f"{record.content}\n"
        )

    @classmethod
    def _read_path(cls, path: Path) -> MemoryRecord:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as err:
            raise MemoryStoreError(f"could not read {path.name}: {err}") from err

        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            raise MemoryStoreError(f"invalid front matter in {path.name}")
        try:
            end = next(
                index for index, line in enumerate(lines[1:], start=1)
                if line.strip() == "---"
            )
        except StopIteration as err:
            raise MemoryStoreError(f"unterminated front matter in {path.name}") from err

        metadata: dict[str, str] = {}
        for line in lines[1:end]:
            key, separator, value = line.partition(":")
            if not separator:
                raise MemoryStoreError(f"invalid metadata line in {path.name}")
            metadata[key.strip()] = _decode_scalar(value)

        content = "\n".join(lines[end + 1 :]).strip()
        required = {"name", "type", "description", "created_at", "updated_at"}
        missing = required.difference(metadata)
        if missing:
            raise MemoryStoreError(
                f"missing metadata in {path.name}: {', '.join(sorted(missing))}"
            )
        cls._validate(
            metadata["name"],
            metadata["type"],
            metadata["description"],
            content,
        )
        if path.stem != metadata["name"]:
            raise MemoryStoreError(
                f"file name {path.stem!r} does not match memory name "
                f"{metadata['name']!r}"
            )
        return MemoryRecord(
            name=metadata["name"],
            memory_type=metadata["type"],
            description=metadata["description"],
            content=content,
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
        )

    @staticmethod
    def _render_index(records: list[MemoryRecord]) -> str:
        lines = [
            "# Gemini Assistant Memory",
            "",
            "This file is generated from the editable Markdown files in this directory.",
            "",
        ]
        if not records:
            lines.append("(no memories yet)")
        else:
            for record in records:
                lines.append(
                    f"- [{record.name}]({record.name}.md) "
                    f"({record.memory_type}) — {record.description}"
                )
        return "\n".join(lines) + "\n"

    def _write_index(self) -> None:
        self._atomic_write(self.index_path, self.read_index())

    def _atomic_write(self, target: Path, content: str) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.path,
            prefix=".tmp_",
            suffix=".md",
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
