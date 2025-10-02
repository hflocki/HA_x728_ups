import logging
import asyncio
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_ON

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# X728 Safe Shutdown Trigger/Charging Control Pin: GPIO 26
PIN_CONTROL = 26 
# Die Pulsdauer in Sekunden (basierend auf X728 Scripts)
SHUTDOWN_PULSE_TIME = 3 
# Shutdown-Puls ist HIGH, daher Active-Low=False
ACTIVE_LOW = False 

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup for the switch platform (Safe Shutdown Trigger)."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub = data["hub"]

    if not hub.online:
        _LOGGER.error("Hub is offline, skipping switch setup.")
        return

    ent = UpsShutdownSwitch(hub)
    async_add_entities([ent])

class UpsShutdownSwitch(SwitchEntity, RestoreEntity):
    """
    Represents a momentary switch to trigger the X728 Safe Shutdown sequence via GPIO 26.
    """
    _attr_name = "UPS Safe Shutdown Trigger"
    _attr_unique_id = "ups_safe_shutdown_trigger"
    _attr_should_poll = False
    _attr_icon = "mdi:power-settings"

    def __init__(self, hub):
        self._hub = hub
        self._line = None
        self._attr_is_on = False 

    async def async_added_to_hass(self) -> None:
        """Called when the entity is added. Requests the GPIO line."""
        await super().async_added_to_hass()
        
        prev_state = await self.async_get_last_state()
        init_state = (prev_state and prev_state.state == STATE_ON)
        
        try:
            self._line = self._hub.add_switch(
                port=PIN_CONTROL,
                active_low=ACTIVE_LOW,  
                init_state=False # Startet immer LOW (OFF)
            )
        except Exception as e:
            _LOGGER.error("Failed to request GPIO line %d for Shutdown Switch: %s", PIN_CONTROL, e)
            self._line = None
            return
            
        if init_state:
             self._attr_is_on = False
             self.async_write_ha_state()


    async def async_will_remove_from_hass(self) -> None:
        """Called when the entity is about to be removed."""
        await super().async_will_remove_from_hass()
        if self._line:
            self._line.release()
            self._line = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Führt den Shutdown-Puls aus."""
        if not self._line:
            return
            
        _LOGGER.info("Starting X728 Safe Shutdown pulse on GPIO %d for %d seconds...", PIN_CONTROL, SHUTDOWN_PULSE_TIME)
        
        # Puls START (HIGH)
        self._hub.turn_on(self._line, PIN_CONTROL)
        self._attr_is_on = True
        self.async_write_ha_state()
        
        # Wartezeit
        await asyncio.sleep(SHUTDOWN_PULSE_TIME)
        
        # Puls ENDE (LOW)
        self._hub.turn_off(self._line, PIN_CONTROL)
        self._attr_is_on = False
        self.async_write_ha_state()
        
        _LOGGER.info("X728 Safe Shutdown pulse completed.")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Sorgt dafür, dass der Pin LOW ist (Switch ist momentary)."""
        if not self._line:
            return
            
        self._hub.turn_off(self._line, PIN_CONTROL)
        self._attr_is_on = False
        self.async_write_ha_state()