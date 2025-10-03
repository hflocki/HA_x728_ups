import logging
import smbus2

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Default I2C address for Geekworm UPS
DEVICE_ADDRESS = 0x36

def voltage_to_percentage(voltage: float) -> int:
    """
    Schätzt den Batteriestand (in %) basierend auf der 2S-Spannung.
    Werte basierend auf typischer Li-Ion Entladekurve (4.2V pro Zelle = 8.4V max).
    Dieser SOC (State of Charge) ist genauer als der interne 1S-Chipwert.
    """
    if voltage >= 8.4:
        return 100
    if voltage >= 8.2:
        return 90
    if voltage >= 7.8:
        return 70
    if voltage >= 7.4:
        return 50
    if voltage >= 7.0:
        return 20
    if voltage >= 6.6:
        return 5
    return 0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """
    Sets up the sensor platform by creating two sensor entities:
    - BatteryLevelSensor
    - BatteryVoltageSensor
    """
    _LOGGER.debug("sensor => async_setup_entry")
    ents = [
        BatteryLevelSensor(),
        BatteryVoltageSensor()
    ]
    async_add_entities(ents, True)


class BatteryLevelSensor(SensorEntity):
    """
    Sensor entity that represents the UPS battery percentage.
    It estimates the percentage based on the corrected 2S voltage reading.
    """
    _attr_name = "UPS Battery Level"
    _attr_unique_id = "ups_battery_level"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self):
        self._state = None
        # I2C Bus im Konstruktor initialisieren
        self._bus = smbus2.SMBus(1) 

    @property
    def native_value(self):
        """Returns the current battery level percentage."""
        return self._state

    async def async_update(self):
        """
        Reads the voltage, corrects it for 2S, and converts it to a percentage.
        """
        try:
            # Register 0x02 für Spannung (VCELL)
            raw = self._read_register(DEVICE_ADDRESS, 0x02)
            if raw is not None:
                # Skalierungsfaktor 78.125 μV pro Bit (vom Chip).
                voltage_single_cell = raw * 78.125 / 1_000_000
                total_voltage = voltage_single_cell * 2 
                
                # Umwandlung der korrigierten 2S-Spannung in SOC (%)
                self._state = voltage_to_percentage(total_voltage)
            else:
                self._state = None
        except Exception as e:
            _LOGGER.error("Error reading battery level (via voltage): %s", e)
            self._state = None

    def _read_register(self, address, register):
        """
        Reads a word from the specified register via I2C.
        """
        try:
            # Verwenden von self._bus
            data = self._bus.read_word_data(address, register)
            swapped = ((data & 0xFF) << 8) | (data >> 8)
            return swapped
        except Exception:
            # Bei Fehlern (z.B. Bus-Timeout) None zurückgeben.
            return None


class BatteryVoltageSensor(SensorEntity):
    """
    Sensor entity that represents the UPS battery voltage.
    Reads raw data from I2C register 0x02 and corrects it for the 2S pack.
    """
    _attr_name = "UPS Battery Voltage"
    _attr_unique_id = "ups_battery_voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    def __init__(self):
        self._state = None
        # I2C Bus im Konstruktor initialisieren
        self._bus = smbus2.SMBus(1) 

    @property
    def native_value(self):
        """Returns the current battery voltage."""
        return self._state

    async def async_update(self):
        """
        Reads from the device using I2C and calculates the *corrected* 2S battery voltage.
        """
        try:
            # Register 0x02 für Spannung (VCELL)
            raw = self._read_register(DEVICE_ADDRESS, 0x02)
            if raw is not None:
                # Skalierungsfaktor 78.125 μV pro Bit.
                voltage_single_cell = raw * 78.125 / 1_000_000
                # WICHTIG: Multiplikation mit 2 für das 2S-Akkupack (X728).
                self._state = float(round(voltage_single_cell * 2, 3) )
            else:
                self._state = None
        except Exception as e:
            _LOGGER.error("Error reading battery voltage: %s", e)
            self._state = None

    def _read_register(self, address, register):
        """
        Reads a word from the specified register via I2C, swaps bytes, 
        and returns the integer value or None if an error occurs.
        """
        try:
            # Verwenden von self._bus
            data = self._bus.read_word_data(address, register)
            swapped = ((data & 0xFF) << 8) | (data >> 8)
            return swapped
        except Exception:
            # Bei Fehlern (z.B. Bus-Timeout) None zurückgeben.
            return None
