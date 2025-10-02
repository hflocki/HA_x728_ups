import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .hub import X728Hub 

_LOGGER = logging.getLogger(__name__)

# NEUE DOMAIN
DOMAIN = "geekworm_ups_x728"
PLATFORMS = ["sensor", "binary_sensor", "switch"]

async def async_setup(hass: HomeAssistant, config: dict):
    """Wir verwenden kein YAML-basiertes Setup."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Wird beim Einrichten der Integration über die UI aufgerufen."""
    _LOGGER.info("Setting up Geekworm X728 UPS (entry_id=%s)", entry.entry_id)

    # Hub-Instanz erstellen
    try:
        # X728Hub versucht, den GPIO-Chip zu öffnen und schlägt fehl, wenn keine Host-Rechte vorhanden sind.
        hub = X728Hub()
    except Exception as e:
        _LOGGER.error("Failed to initialize X728 Hub (GPIO/I2C issue): %s", e)
        # Setup abbrechen, wenn der Host-Zugriff fehlschlägt
        return False 

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "hub": hub
    }

    # Setup an die Plattformen weiterleiten
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Wird beim Entfernen der Integration aufgerufen."""
    _LOGGER.info("Unloading Geekworm X728 UPS (entry_id=%s)", entry.entry_id)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            
    return unload_ok