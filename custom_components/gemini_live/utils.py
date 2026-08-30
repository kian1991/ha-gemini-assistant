"""Utility functions for audio processing."""

from collections.abc import Sequence
import logging
import struct


def normalize_llm_api_selection(
    value: object,
    default: Sequence[str],
) -> list[str]:
    """Return the configured HA LLM API IDs as a clean list.

    A missing value means the config entry predates the LLM API selector, so the
    legacy default applies. An explicit empty selection stays empty: the user
    deliberately disabled all HA LLM APIs.
    """
    if value is None:
        return list(default)
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return list(default)
    selection: list[str] = []
    for api_id in value:
        if isinstance(api_id, str) and api_id and api_id not in selection:
            selection.append(api_id)
    return selection


def set_detailed_logging(enabled: bool) -> None:
    """Set package logging verbosity for Gemini Live."""
    level = logging.DEBUG if enabled else logging.ERROR
    logging.getLogger("custom_components.gemini_live").setLevel(level)

def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """Wrap raw 16-bit signed PCM mono audio in a WAV container."""
    num_channels = 1
    sample_width = 2  # 16-bit

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(pcm_data),
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM format code
        num_channels,
        sample_rate,
        sample_rate * num_channels * sample_width,
        num_channels * sample_width,
        sample_width * 8,
        b"data",
        len(pcm_data),
    )
    return header + pcm_data


def streaming_wav_header(sample_rate: int = 24000) -> bytes:
    """Return a WAV header whose data length is terminated by end-of-stream."""
    num_channels = 1
    sample_width = 2
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        0xFFFFFFFF,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        sample_rate * num_channels * sample_width,
        num_channels * sample_width,
        sample_width * 8,
        b"data",
        0xFFFFFFFF,
    )
