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

# --- PIN DEFINITIONEN ---
# Pin für die Ladekontrolle (dauerhaftes Schalten)
PIN_CHARGING = 16
# Pin für den Safe Shutdown Trigger (Pulsen)
PIN_CONTROL = 26 
# Die Pulsdauer in Sekunden
SHUTDOWN_PULSE_TIME = 3 

# --- SETUP FUNKTION ---
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup für die Switch-Plattform. Erstellt beide Schalter-Entitäten."""
    _LOGGER.debug("switch => async_setup_entry")
    data = hass.data[DOMAIN][entry.entry_id]
    hub = data["hub"]

    if not hub.online:
        _LOGGER.error("Hub ist offline, überspringe Switch-Setup.")
        return

    # Beide Schalter hinzufügen
    entities = [
        UpsChargingSwitch(hub),
        UpsShutdownSwitch(hub)
    ]
    async_add_entities(entities)

# --- KLASSE 1: LADEKONTROLLE (GPIO 16) ---
class UpsChargingSwitch(SwitchEntity, RestoreEntity):
    """Repräsentiert einen Schalter zum Aktivieren/Deaktivieren des Ladens über GPIO 16."""
    _attr_name = "UPS Battery Charging" # NEUER NAME: Besser für die Benutzeroberfläche
    _attr_unique_id = "ups_charging_on_off"
    _attr_should_poll = False
    _attr_icon = "mdi:power-plug-outline" # Passendes Icon

    def __init__(self, hub):
        self._hub = hub
        self._line = None
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Wird aufgerufen, wenn die Entität hinzugefügt wird."""
        await super().async_added_to_hass()
        
        # Zustand wiederherstellen
        prev_state = await self.async_get_last_state()
        if prev_state and prev_state.state == STATE_ON:
            self._attr_is_on = True
        else:
            self._attr_is_on = False

        # GPIO-Leitung für OUTPUT anfordern
        try:
            # X728 Charging ist Active-Low: True = Laden AN
            self._line = self._hub.add_switch(
                port=PIN_CHARGING,
                active_low=True,  
                init_state=self._attr_is_on
            )
            _LOGGER.debug("Charging switch line requested for port=%d => is_on=%s", PIN_CHARGING, self._attr_is_on)
        except Exception as e:
            _LOGGER.error("Failed to setup charging switch: %s", e)
            self._line = None
            return

    async def async_will_remove_from_hass(self) -> None:
        """Wird aufgerufen, wenn die Entität entfernt wird."""
        await super().async_will_remove_from_hass()
        if self._line:
            self._line.release()
            self._line = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Laden aktivieren (GPIO 16 auf ACTIVE setzen)."""
        if not self._line:
            return
        self._hub.turn_on(self._line, PIN_CHARGING)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Laden deaktivieren (GPIO 16 auf INACTIVE setzen)."""
        if not self._line:
            return
        self._hub.turn_off(self._line, PIN_CHARGING)
        self._attr_is_on = False
        self.async_write_ha_state()


# --- KLASSE 2: SAFE SHUTDOWN TRIGGER (GPIO 26) ---
class UpsShutdownSwitch(SwitchEntity, RestoreEntity):
    """Repräsentiert einen Taster (momentary switch) zum Auslösen der Safe Shutdown Sequenz."""
    _attr_name = "UPS Safe Shutdown Trigger"
    _attr_unique_id = "ups_safe_shutdown_trigger"
    _attr_should_poll = False
    _attr_icon = "mdi:power-settings"

    def __init__(self, hub):
        self._hub = hub
        self._line = None
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Wird aufgerufen, wenn die Entität hinzugefügt wird."""
        await super().async_added_to_hass()
        
        # Der Shutdown-Taster ist kein dauerhafter Zustand, bleibt immer 'OFF' in HA,
        # wird aber für die Initialisierung des Pins benötigt.
        # Shutdown-Puls ist HIGH, daher Active-Low=False. Initialzustand INACTIVE (LOW).
        init_state = False 
        
        try:
            self._line = self._hub.add_switch(
                port=PIN_CONTROL,
                active_low=False,
                init_state=init_state
            )
        except Exception as e:
            _LOGGER.error("Failed to setup shutdown switch: %s", e)
            self._line = None
            return
            
        # Wir setzen den Zustand in HA auf OFF (False), da es ein momentary switch ist.
        # Der Zustand wird nur kurz ON (True) während des Pulses.
        if self.hass.states.is_state(self.entity_id, STATE_ON):
             self._attr_is_on = False
             self.async_write_ha_state()


    async def async_will_remove_from_hass(self) -> None:
        """Wird aufgerufen, wenn die Entität entfernt wird."""
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
        """Beim Ausschalten wird keine Aktion ausgeführt, da es ein Taster ist."""
        # Nur den Zustand im Home Assistant setzen, falls er aus einem Grund noch auf ON steht.
        self._attr_is_on = False
        self.async_write_ha_state()
