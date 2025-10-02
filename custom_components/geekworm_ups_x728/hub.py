import logging
import gpiod
from datetime import timedelta
from gpiod.line import Direction, Value, Bias, Drive, Edge, Clock

_LOGGER = logging.getLogger(__name__)

# NEUE KLASSE
class X728Hub:
    """
    Hilfsklasse, die den GPIO-Chip des Raspberry Pi verwaltet.
    """

    def __init__(self):
        CHIP_PATH = "/dev/gpiochip0" 
        _LOGGER.debug("X728Hub init: opening %s", CHIP_PATH)
        
        try:
            self._chip = gpiod.Chip(CHIP_PATH)
            self._online = True
        except Exception as e:
            _LOGGER.error("Failed to open GPIO chip at %s. Error: %s. Check host configuration.", CHIP_PATH, e)
            self._chip = None
            self._online = False

    @property
    def online(self):
        """Gibt True zurück, wenn der GPIO-Zugriff erfolgreich war."""
        return self._online

    def add_sensor(self, port, active_low, bounce_ms=50):
        """Fordert eine GPIO-Leitung für einen Sensor-Input (z.B. Stromausfall) an."""
        if not self._online:
            raise Exception("X728Hub ist offline (GPIO chip failed to open).")
            
        cfg = gpiod.LineSettings(
            direction=Direction.INPUT,
            active_low=active_low,
            bias=Bias.PULL_UP,
            edge_detection=Edge.BOTH,
            debounce_period=timedelta(milliseconds=bounce_ms),
            event_clock=Clock.REALTIME
        )
        line_request = self._chip.request_lines(
            consumer="geekworm_x728_sensor",
            config={port: cfg}
        )
        val = line_request.get_value(port)
        is_on = (val == Value.ACTIVE)
        return line_request, is_on

    def add_switch(self, port, active_low, init_state):
        """Fordert eine GPIO-Leitung als Output (z.B. Shutdown-Trigger) an."""
        if not self._online:
            raise Exception("X728Hub ist offline (GPIO chip failed to open).")
            
        cfg = gpiod.LineSettings(
            direction=Direction.OUTPUT,
            active_low=active_low,
            bias=Bias.AS_IS,
            drive=Drive.PUSH_PULL,
            output_value=Value.ACTIVE if init_state else Value.INACTIVE
        )
        line_request = self._chip.request_lines(
            consumer="geekworm_x728_switch",
            config={port: cfg}
        )
        return line_request

    def turn_on(self, line_req, port):
        """Setzt die GPIO-Leitung auf ACTIVE (z.B. High für den Shutdown-Puls)."""
        line_req.set_value(port, Value.ACTIVE)

    def turn_off(self, line_req, port):
        """Setzt die GPIO-Leitung auf INACTIVE."""
        line_req.set_value(port, Value.INACTIVE)

    def close(self):
        """Schließt die Chip-Referenz."""
        if self._chip:
            self._chip.close()
            self._online = False