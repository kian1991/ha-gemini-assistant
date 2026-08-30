# Changelog

All notable changes to Gemini Assistant for Home Assistant are documented here.

## 1.2.0

- Added a generic **Home Assistant LLM APIs** multi-select to the setup,
  reconfigure, and options flows. Any LLM API registered in Home Assistant can
  be selected: the Assist API, Model Context Protocol server entries (for
  example Google Gmail/Drive/Docs/Calendar MCP), and future providers.
- Selected APIs are resolved through Home Assistant's official LLM API layer.
  Multiple APIs are merged by Home Assistant itself, which namespaces tool
  names as `<api-name>__<tool>` and routes calls back to the owning API, so
  tool execution, MCP transport, OAuth, and reauthentication stay owned by
  Home Assistant.
- Existing config entries keep their behavior: without a stored selection the
  Assist API is used, exactly as before. Selecting only Assist produces the
  identical tool set and tool names as previous releases.
- An unavailable API (for example an unloaded MCP server entry) is skipped
  with a warning instead of breaking the Live session.
- HA LLM tools whose names collide with integration-owned tools
  (`show_text`, `end_conversation`, `memory_*`) are excluded from the Gemini
  tool set with a warning; local tools always win.
- Made the OpenAPI schema converter compatible with Home Assistant 2026.9,
  which replaces `voluptuous_openapi` with `probatio`.
- Detailed logging now reports the loaded API IDs and names, tool counts per
  API, the final Gemini tool inventory, and per-call routing
  (`route=local|ha_llm`) with argument keys instead of raw argument values.
- Added `translations/en.json` so option labels render from the bundled
  strings.

## 1.1.0

- Added built-in durable long-term memory with local Markdown storage.
- Added `memory_save`, `memory_read`, and `memory_delete` Gemini Live tools.
- Added a bounded live memory index and explicit privacy/retention policy.
- Added atomic writes, input limits, path validation, and unit tests.
- Kept Gemini's response audio at its native 24 kHz sample rate.
- Renamed the distribution to Gemini Assistant while retaining the existing
  `gemini_live` integration domain for config-entry compatibility.

## 1.0.2

- Added an `end_conversation` callback that lets Gemini tell Home Assistant when
  to stop listening for follow-up requests. Completion state is tracked
  independently for each conversation.
- Made short opening commands such as "stop" prioritize stopping an actively
  ringing alarm or timer before ending the conversation.
- Documented the Home Assistant Core custom-component override that reduces
  response latency on ESPHome Assist satellites.

## 1.0.1

- Fixed HACS and Hassfest validation metadata.

## 1.0.0

- Added Gemini Live speech-to-text, conversation, and cached native-audio
  text-to-speech entities.
- Added HACS metadata, brand assets, translations, validation workflow, and
  installation documentation.
