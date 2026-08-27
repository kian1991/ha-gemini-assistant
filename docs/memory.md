# Durable memory design

Gemini Assistant owns one local memory store. It does not require the separate
`ha-memory` integration, a vector database, embeddings, or an external storage
service.

## Semantics

Gemini may automatically save information only when it is stable, useful in
future conversations, and not sensitive. Appropriate memories include:

- durable preferences;
- household facts;
- recurring routines;
- names and relationships that are not sensitive;
- user-specific terminology.

Gemini must not save temporary requests, current device states, one-off events,
unverified guesses, trivia, or conversation transcripts. Health, financial,
relationship, precise presence-pattern, and similarly sensitive personal
information requires an explicit request to remember it in the current turn.
Passwords, API keys, access tokens, alarm codes, and other authentication
secrets must never be stored.

Memories do not expire automatically. They remain until Gemini or the user
updates or deletes them.

## Storage and editability

The store lives at `/config/gemini_assistant/memory`. Each memory has a stable
snake-case identifier and one Markdown file with front matter:

```markdown
---
name: "bathroom_lighting"
type: "preference"
description: "Preferred cozy bathroom lighting"
created_at: "2026-08-27T12:00:00Z"
updated_at: "2026-08-27T12:00:00Z"
---

Kian prefers 2700 K at 35 percent when asking for cozy bathroom lighting.
```

The supported types are `preference`, `home`, `routine`, `terminology`,
`person`, and `other`. Files can be edited over SSH. Keep the file name and
`name` value identical, preserve both front-matter delimiters, and use one of
the supported types.

`MEMORY.md` is regenerated after tool-driven saves and deletes. The prompt index
is built directly from the individual memory files, so valid manual edits are
used even if the generated index has not yet been refreshed. A malformed file
is ignored without hiding other valid memories and produces a warning in the
Home Assistant log.

Writes use a temporary file, flush it to disk, and atomically replace the target.
Names are path-safe, the number and size of memories are bounded, and concurrent
tool calls are serialized.

## Privacy boundary

Memory files remain on Home Assistant. To make memory useful to Gemini, each
request includes the bounded index containing memory identifiers, categories,
and descriptions. The complete content is sent only if Gemini calls
`memory_read`, or when it creates/updates a memory through `memory_save`.

Turning off **Durable memory** removes the index and tools from future Gemini
sessions. Existing files are retained so the option is reversible. Deleting the
files is a separate, explicit action.

## First-slice test

1. Say: "Remember that I prefer cozy bathroom lighting at 2700 K and 35 percent."
2. Confirm that the assistant briefly acknowledges saving the preference.
3. Check that `/config/gemini_assistant/memory/bathroom_lighting.md` exists.
4. Start a new Assist conversation or restart Home Assistant.
5. Ask: "How do I like the bathroom lighting when I say cozy?"
6. Confirm that the answer uses the stored values.
7. Say: "Forget my cozy bathroom lighting preference."
8. Confirm that the file and its `MEMORY.md` index entry are removed.

This first slice intentionally does not persist complete conversation history.
That will use a separate history store so retention and transcript privacy can
be configured independently from long-term memory.
