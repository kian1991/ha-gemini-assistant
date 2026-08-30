"""Config flow for Gemini Live integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import llm, selector

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_DETAILED_LOGGING,
    CONF_ENCOURAGE_WEB_SEARCH,
    CONF_LLM_HASS_API,
    CONF_MEMORY_ENABLED,
    CONF_MODEL,
    CONF_SHOW_TEXT,
    CONF_TRANSCRIBE_GEMINI,
    CONF_VOICE,
    DEFAULT_LLM_HASS_API,
    DEFAULT_TRANSCRIBE_GEMINI,
    DEFAULT_ENCOURAGE_WEB_SEARCH,
    DEFAULT_MEMORY_ENABLED,
    DEFAULT_SHOW_TEXT,
    CONF_SYSTEM_INSTRUCTION,
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    AVAILABLE_MODELS,
    AVAILABLE_VOICES_INFO,
)
from .utils import normalize_llm_api_selection


VOICE_OPTIONS = [
    selector.SelectOptionDict(
        value=name,
        label=f"{name} - {gender}, {description}",
    )
    for name, gender, description in AVAILABLE_VOICES_INFO
]

VOICE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=VOICE_OPTIONS,
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)


def _llm_api_selector(hass: HomeAssistant) -> selector.SelectSelector:
    """Return a multi-select over the LLM APIs currently registered in HA.

    The choices are dynamic: the Assist API, every loaded Model Context
    Protocol server entry, and any other integration-registered LLM API.
    """
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=api.id, label=api.name)
                for api in llm.async_get_apis(hass)
            ],
            multiple=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _current_llm_api_selection(hass: HomeAssistant, config: dict) -> list[str]:
    """Return the stored LLM API selection restricted to available APIs."""
    known_ids = {api.id for api in llm.async_get_apis(hass)}
    return [
        api_id
        for api_id in normalize_llm_api_selection(
            config.get(CONF_LLM_HASS_API),
            DEFAULT_LLM_HASS_API,
        )
        if api_id in known_ids
    ]


class GeminiLiveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gemini Assistant."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            user_input.setdefault(CONF_SYSTEM_INSTRUCTION, "")
            return self.async_create_entry(title="Gemini Assistant", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_MODEL, default=DEFAULT_MODEL): vol.In(AVAILABLE_MODELS),
                    vol.Required(CONF_VOICE, default=DEFAULT_VOICE): VOICE_SELECTOR,
                    vol.Optional(
                        CONF_LLM_HASS_API,
                        default=list(DEFAULT_LLM_HASS_API),
                    ): _llm_api_selector(self.hass),
                    vol.Optional(CONF_SYSTEM_INSTRUCTION): str,
                    vol.Optional(CONF_DETAILED_LOGGING, default=False): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_TRANSCRIBE_GEMINI,
                        default=DEFAULT_TRANSCRIBE_GEMINI,
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_ENCOURAGE_WEB_SEARCH,
                        default=DEFAULT_ENCOURAGE_WEB_SEARCH,
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_SHOW_TEXT,
                        default=DEFAULT_SHOW_TEXT,
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_MEMORY_ENABLED,
                        default=DEFAULT_MEMORY_ENABLED,
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of the integration."""
        errors = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            user_input.setdefault(CONF_SYSTEM_INSTRUCTION, "")
            return self.async_update_reload_and_abort(
                entry,
                data_updates=user_input,
                options={},
            )

        config = {**entry.data, **entry.options}
        current_api_key = config.get(CONF_API_KEY, "")
        current_model = config.get(CONF_MODEL, DEFAULT_MODEL)
        current_voice = config.get(CONF_VOICE, DEFAULT_VOICE)
        current_system_instruction = config.get(CONF_SYSTEM_INSTRUCTION, "")
        current_detailed_logging = config.get(CONF_DETAILED_LOGGING, False)
        current_transcribe_gemini = config.get(
            CONF_TRANSCRIBE_GEMINI, DEFAULT_TRANSCRIBE_GEMINI
        )
        current_encourage_web_search = config.get(
            CONF_ENCOURAGE_WEB_SEARCH, DEFAULT_ENCOURAGE_WEB_SEARCH
        )
        current_show_text = config.get(
            CONF_SHOW_TEXT, DEFAULT_SHOW_TEXT
        )
        current_memory_enabled = config.get(
            CONF_MEMORY_ENABLED, DEFAULT_MEMORY_ENABLED
        )
        current_llm_apis = _current_llm_api_selection(self.hass, config)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY, default=current_api_key): str,
                    vol.Required(CONF_MODEL, default=current_model): vol.In(AVAILABLE_MODELS),
                    vol.Required(CONF_VOICE, default=current_voice): VOICE_SELECTOR,
                    vol.Optional(
                        CONF_LLM_HASS_API,
                        default=current_llm_apis,
                    ): _llm_api_selector(self.hass),
                    vol.Optional(
                        CONF_SYSTEM_INSTRUCTION,
                        description={"suggested_value": current_system_instruction},
                    ): str,
                    vol.Optional(CONF_DETAILED_LOGGING, default=current_detailed_logging): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_TRANSCRIBE_GEMINI,
                        default=current_transcribe_gemini,
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_ENCOURAGE_WEB_SEARCH,
                        default=current_encourage_web_search,
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_SHOW_TEXT,
                        default=current_show_text,
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_MEMORY_ENABLED,
                        default=current_memory_enabled,
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return GeminiLiveOptionsFlowHandler()


class GeminiLiveOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Gemini Live re-configuration."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            user_input.setdefault(CONF_SYSTEM_INSTRUCTION, "")
            return self.async_create_entry(title="", data=user_input)

        # Pre-populate fields with existing data or options merged
        config = {**self.config_entry.data, **self.config_entry.options}
        current_api_key = config.get(CONF_API_KEY, "")
        current_model = config.get(CONF_MODEL, DEFAULT_MODEL)
        current_voice = config.get(CONF_VOICE, DEFAULT_VOICE)
        current_system_instruction = config.get(CONF_SYSTEM_INSTRUCTION, "")
        current_detailed_logging = config.get(CONF_DETAILED_LOGGING, False)
        current_transcribe_gemini = config.get(
            CONF_TRANSCRIBE_GEMINI, DEFAULT_TRANSCRIBE_GEMINI
        )
        current_encourage_web_search = config.get(
            CONF_ENCOURAGE_WEB_SEARCH, DEFAULT_ENCOURAGE_WEB_SEARCH
        )
        current_show_text = config.get(
            CONF_SHOW_TEXT, DEFAULT_SHOW_TEXT
        )
        current_memory_enabled = config.get(
            CONF_MEMORY_ENABLED, DEFAULT_MEMORY_ENABLED
        )
        current_llm_apis = _current_llm_api_selection(self.hass, config)

        schema_dict = {
            vol.Required(CONF_API_KEY, default=current_api_key): str,
            vol.Required(CONF_MODEL, default=current_model): vol.In(AVAILABLE_MODELS),
            vol.Required(CONF_VOICE, default=current_voice): VOICE_SELECTOR,
            vol.Optional(
                CONF_LLM_HASS_API,
                default=current_llm_apis,
            ): _llm_api_selector(self.hass),
            vol.Optional(
                CONF_SYSTEM_INSTRUCTION,
                description={"suggested_value": current_system_instruction},
            ): str,
            vol.Optional(CONF_DETAILED_LOGGING, default=current_detailed_logging): selector.BooleanSelector(),
            vol.Optional(
                CONF_TRANSCRIBE_GEMINI,
                default=current_transcribe_gemini,
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENCOURAGE_WEB_SEARCH,
                default=current_encourage_web_search,
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_SHOW_TEXT,
                default=current_show_text,
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_MEMORY_ENABLED,
                default=current_memory_enabled,
            ): selector.BooleanSelector(),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )
