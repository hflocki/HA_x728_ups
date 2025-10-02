import logging
import gpiod
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import DEVICE_CLASS_PROBLEM 

from . import DOMAIN
from .config_flow import (
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_INVERT_LOGIC
)

_LOGGER = logging.getLogger(__name__)

# X728 Power Loss Detection Pin: GPIO 6
PIN_POWER_LOSS = 6

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup for the binary_sensor platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub = data["hub"]

    if not hub.online:
        _LOGGER.error("Hub is offline, skipping binary sensor setup.")
        return

    ent = UpsPowerLossBinarySensor(hub, entry)
    async_add_entities([ent])

class UpsPowerLossBinarySensor(BinarySensorEntity):
    """Represents the X728 UPS Power Loss detection."""
    _attr_name = "UPS AC Power Status"
    _attr_unique_id = "ups_ac_power_status"
    _attr_should_poll = False
    _attr_device_class = DEVICE_CLASS_PROBLEM 

    def __init__(self, hub, config_entry: ConfigEntry):
        self._hub = hub
        self._entry = config_entry
        self._line: gpiod.LineRequest = None
        self._attr_device_class = self._entry.options.get(CONF_SENSOR_DEVICE_CLASS, DEVICE_CLASS_PROBLEM)

    async def async_added_to_hass(self) -> None:
        """Called when the entity is added to Home Assistant. Requests the GPIO line."""
        await super().async_added_to_hass()
        
        # Default for X728 is Active-Low=True (Power Loss = HIGH signal)
        invert = self._entry.options.get(CONF_SENSOR_INVERT_LOGIC, True)

        try:
            self._line, is_on = self._hub.add_sensor(
                port=PIN_POWER_LOSS,
                active_low=invert,
                bounce_ms=50
            )
        except Exception as e:
            _LOGGER.error("Failed to request GPIO line %d for AC Power Status: %s", PIN_POWER_LOSS, e)
            self._line = None
            return

        self._attr_is_on = is_on
        self.hass.loop.add_reader(self._line.fd, self._handle_gpio_event)

    async def async_will_remove_from_hass(self):
        """Called when the entity is about to be removed."""
        await super().async_will_remove_from_hass()
        if self._line:
            self.hass.loop.remove_reader(self._line.fd)
            self._line.release()
            self._line = None

    @callback
    def _handle_gpio_event(self):
        """Callback to handle GPIO edge events from gpiod."""
        for event in self._line.read_edge_events():
            # X728: AC Loss is HIGH (RISING edge)
            if event.event_type == gpiod.EdgeEvent.RISING_EDGE:
                 self._attr_is_on = True # AC Loss
            elif event.event_type == gpiod.EdgeEvent.FALLING_EDGE:
                 self._attr_is_on = False # AC OK

            _LOGGER.debug("GPIO Event on pin=%d: %s => is_on=%s", PIN_POWER_LOSS, event.event_type.name, self._attr_is_on)
            self.async_write_ha_state()