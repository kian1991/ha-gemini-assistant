"""Gemini tool integration for local durable memory."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.core import HomeAssistant

from .memory_store import MemoryRecord, MemoryStore, VALID_MEMORY_TYPES

MEMORY_SAVE_TOOL_NAME = "memory_save"
MEMORY_READ_TOOL_NAME = "memory_read"
MEMORY_DELETE_TOOL_NAME = "memory_delete"
MEMORY_TOOL_NAMES = frozenset(
    {MEMORY_SAVE_TOOL_NAME, MEMORY_READ_TOOL_NAME, MEMORY_DELETE_TOOL_NAME}
)
MAX_PROMPT_INDEX_LENGTH = 12000

_MEMORY_INSTRUCTION = """You have a local, durable long-term memory that survives restarts and new conversations.

The memory index below contains identifiers and short descriptions. Call memory_read when an indexed description is relevant but does not contain enough detail. Call memory_save to create or update durable information that is likely to be useful in future conversations, including stable preferences, names, household facts, recurring routines, and the user's terminology. Reuse an existing identifier when updating a fact instead of creating a duplicate. Call memory_delete when the user asks you to forget something or when a stored fact is no longer valid.

Do not save temporary requests, current device states, one-off events, guesses, full conversation transcripts, or trivia. Never save passwords, API keys, access tokens, alarm codes, or other authentication secrets. Health, financial, relationship, precise presence-pattern, and other sensitive personal information may only be saved when the user explicitly asks you to remember it in the current turn. Keep each memory concise and factual. Briefly confirm after saving, updating, or deleting a memory.

Memory files remain local to Home Assistant, but the index and any memory you read are included in requests to Gemini.

Current memory index:
{index}"""


def _string_property(description: str) -> dict[str, Any]:
    return {"type": "STRING", "description": description}


MEMORY_TOOLS: list[dict[str, Any]] = [
    {
        "function_declarations": [
            {
                "name": MEMORY_SAVE_TOOL_NAME,
                "description": (
                    "Create or update one durable memory. Use only according to the "
                    "privacy and durability rules in the system instruction."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "name": _string_property(
                            "Stable snake_case identifier using lowercase letters, numbers, and underscores."
                        ),
                        "memory_type": {
                            "type": "STRING",
                            "description": "Category of the memory.",
                            "enum": list(VALID_MEMORY_TYPES),
                        },
                        "description": _string_property(
                            "Short, non-sensitive summary shown in the memory index."
                        ),
                        "content": _string_property(
                            "Concise factual detail that will remain useful later."
                        ),
                    },
                    "required": ["name", "memory_type", "description", "content"],
                },
            }
        ]
    },
    {
        "function_declarations": [
            {
                "name": MEMORY_READ_TOOL_NAME,
                "description": "Read the complete content of one indexed memory.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "name": _string_property(
                            "The exact snake_case identifier from the memory index."
                        )
                    },
                    "required": ["name"],
                },
            }
        ]
    },
    {
        "function_declarations": [
            {
                "name": MEMORY_DELETE_TOOL_NAME,
                "description": "Permanently delete one memory at the user's request.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "name": _string_property(
                            "The exact snake_case identifier from the memory index."
                        )
                    },
                    "required": ["name"],
                },
            }
        ]
    },
]


class MemoryManager:
    """Serialize persistent memory operations outside Home Assistant's event loop."""

    def __init__(self, hass: HomeAssistant, store: MemoryStore) -> None:
        self._hass = hass
        self._store = store
        self._lock = asyncio.Lock()

    @classmethod
    async def async_create(cls, hass: HomeAssistant, path: str) -> MemoryManager:
        """Create the store without blocking Home Assistant's event loop."""
        store = await hass.async_add_executor_job(MemoryStore, path)
        return cls(hass, store)

    async def async_system_instruction(self) -> str:
        """Return current memory policy and a bounded live index."""
        index = await self._hass.async_add_executor_job(self._store.read_index)
        if len(index) > MAX_PROMPT_INDEX_LENGTH:
            index = (
                index[:MAX_PROMPT_INDEX_LENGTH]
                + "\n(index truncated; ask the user to remove or consolidate memories)"
            )
        return _MEMORY_INSTRUCTION.format(index=index.strip() or "(no memories yet)")

    async def async_call_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute one integration-owned memory tool."""
        async with self._lock:
            if tool_name == MEMORY_SAVE_TOOL_NAME:
                record = await self._hass.async_add_executor_job(
                    self._store.save,
                    tool_args.get("name", ""),
                    tool_args.get("memory_type", ""),
                    tool_args.get("description", ""),
                    tool_args.get("content", ""),
                )
                return {
                    "saved": record.name,
                    "memory_type": record.memory_type,
                    "updated_at": record.updated_at,
                }
            if tool_name == MEMORY_READ_TOOL_NAME:
                record = await self._hass.async_add_executor_job(
                    self._store.read,
                    tool_args.get("name", ""),
                )
                return self._record_response(record)
            if tool_name == MEMORY_DELETE_TOOL_NAME:
                name = tool_args.get("name", "")
                await self._hass.async_add_executor_job(self._store.delete, name)
                return {"deleted": name}
        raise ValueError(f"unknown memory tool: {tool_name}")

    @staticmethod
    def _record_response(record: MemoryRecord) -> dict[str, Any]:
        return {
            "name": record.name,
            "memory_type": record.memory_type,
            "description": record.description,
            "content": record.content,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
