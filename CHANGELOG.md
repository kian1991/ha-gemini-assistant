# Changelog

All notable changes to Gemini Assistant for Home Assistant are documented here.

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
