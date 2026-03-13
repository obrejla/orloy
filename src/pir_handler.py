"""
PIR (Passive Infrared) motion sensor handler.

Monitors a PIR sensor and logs motion events when detection is enabled.
Detection can be toggled ON/OFF via the physical toggle button or the web API.

Detection starts enabled at launch.
"""

import logging
import threading

from gpiozero import Button, MotionSensor

from src.config import BUTTON_PIR_TOGGLE_PIN, PIR_SENSOR_PIN

logger = logging.getLogger(__name__)


class PIRHandler:
    """
    Manages a PIR motion sensor and its physical enable/disable toggle button.

    When detection is enabled and motion is detected, an INFO log entry is
    written.  Detection can be toggled at runtime via the physical button or
    the web API.

    Args:
        sensor_pin:      GPIO pin connected to the PIR sensor (default GPIO 12).
        toggle_pin:      GPIO pin connected to the toggle button (default GPIO 16).
        initial_enabled: Whether detection starts enabled (default True).
    """

    def __init__(
        self,
        sensor_pin: int = PIR_SENSOR_PIN,
        toggle_pin: int = BUTTON_PIR_TOGGLE_PIN,
        initial_enabled: bool = True,
    ) -> None:
        self._lock = threading.Lock()
        self._enabled = initial_enabled

        self._sensor = MotionSensor(sensor_pin)
        self._btn = Button(toggle_pin)

        self._sensor.when_motion = self._on_motion
        self._btn.when_pressed = self.toggle

        logger.info(
            "PIR handler ready – sensor GPIO %d, toggle button GPIO %d, detection=%s",
            sensor_pin,
            toggle_pin,
            self._enabled,
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def toggle(self) -> bool:
        """Toggle motion detection on/off.  Returns the new enabled state."""
        with self._lock:
            self._enabled = not self._enabled
            state = self._enabled
        logger.info("PIR detection %s", "ON" if state else "OFF")
        return state

    # ------------------------------------------------------------------ #
    # Callbacks                                                            #
    # ------------------------------------------------------------------ #

    def _on_motion(self) -> None:
        with self._lock:
            enabled = self._enabled
        if enabled:
            logger.info("PIR: motion detected")

    # ------------------------------------------------------------------ #
    # Cleanup                                                              #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        self._sensor.close()
        self._btn.close()
        logger.info("PIR handler closed")
