import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_SENSOR_DEVICE_CLASS = "Power sensor device class"
CONF_SENSOR_INVERT_LOGIC = "Power sensor invert logic"

DEVICE_CLASS_LABELS = {
    "problem": "Problem",
    "power": "Power"
}
USER_FRIENDLY_TO_INTERNAL = {v: k for k, v in DEVICE_CLASS_LABELS.items()}

# NEUE KLASSE
class GeekwormX728ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Geekworm X728 UPS."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Erster Schritt des Setups."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            # Default-Optionen für X728 (Invert Logic ist Standard)
            return self.async_create_entry(
                title="Geekworm X728 UPS",
                data={},
                options={
                    CONF_SENSOR_DEVICE_CLASS: "problem",
                    CONF_SENSOR_INVERT_LOGIC: True
                }
            )

        return self.async_show_form(
            step_id="user",
            description_placeholders={"domain": DOMAIN}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GeekwormX728OptionsFlowHandler(config_entry)


class GeekwormX728OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow (called after initial setup)."""
    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        """Displays a form for changing the device_class and invert_logic."""
        if user_input is not None:
            chosen_label = user_input[CONF_SENSOR_DEVICE_CLASS]
            actual_device_class = USER_FRIENDLY_TO_INTERNAL[chosen_label]
            user_invert = user_input[CONF_SENSOR_INVERT_LOGIC]

            return self.async_create_entry(
                title="",
                data={
                    CONF_SENSOR_DEVICE_CLASS: actual_device_class,
                    CONF_SENSOR_INVERT_LOGIC: user_invert
                }
            )

        current_internal = self._entry.options.get(CONF_SENSOR_DEVICE_CLASS, "problem")
        current_label = DEVICE_CLASS_LABELS.get(current_internal, "Problem")
        current_invert = self._entry.options.get(CONF_SENSOR_INVERT_LOGIC, True) 

        data_schema = vol.Schema({
            vol.Required(CONF_SENSOR_DEVICE_CLASS, default=current_label):
                vol.In(DEVICE_CLASS_LABELS.values()),
            vol.Required(CONF_SENSOR_INVERT_LOGIC, default=current_invert):
                cv.boolean
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders={"domain": DOMAIN}
        )