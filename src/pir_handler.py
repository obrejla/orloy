"""
PIR (Passive Infrared) motion sensor handler.

Monitors a PIR sensor and logs motion events when detection is enabled.
Detection can be toggled ON/OFF via the physical toggle button or the web API.

An LED (GPIO 20 by default) lights up while motion is active and turns off
when motion stops.  The LED only activates when detection is enabled.

Detection starts enabled at launch.
"""

import logging
import threading

from gpiozero import Button, LED, MotionSensor

from src.config import BUTTON_PIR_TOGGLE_PIN, PIR_LED_PIN, PIR_SENSOR_PIN

logger = logging.getLogger(__name__)


class PIRHandler:
    """
    Manages a PIR motion sensor, its physical enable/disable toggle button,
    and an LED indicator.

    When detection is enabled and motion is detected, the LED turns on and an
    INFO log entry is written.  The LED turns off when motion stops.  If
    detection is disabled the LED stays off regardless of sensor state.

    Detection can be toggled at runtime via the physical button or the web API.

    Args:
        sensor_pin:      GPIO pin connected to the PIR sensor (default GPIO 12).
        toggle_pin:      GPIO pin connected to the toggle button (default GPIO 16).
        led_pin:         GPIO pin connected to the motion LED (default GPIO 20).
        initial_enabled: Whether detection starts enabled (default True).
    """

    def __init__(
        self,
        sensor_pin: int = PIR_SENSOR_PIN,
        toggle_pin: int = BUTTON_PIR_TOGGLE_PIN,
        led_pin: int = PIR_LED_PIN,
        initial_enabled: bool = True,
    ) -> None:
        self._lock = threading.Lock()
        self._enabled = initial_enabled

        self._sensor = MotionSensor(sensor_pin)
        self._btn = Button(toggle_pin)
        self._led = LED(led_pin)

        self._sensor.when_motion = self._on_motion
        self._sensor.when_no_motion = self._on_no_motion
        self._btn.when_pressed = self.toggle

        logger.info(
            "PIR handler ready – sensor GPIO %d, toggle button GPIO %d, LED GPIO %d, detection=%s",
            sensor_pin,
            toggle_pin,
            led_pin,
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
        if not state:
            self._led.off()
        logger.info("PIR detection %s", "ON" if state else "OFF")
        return state

    # ------------------------------------------------------------------ #
    # Callbacks                                                            #
    # ------------------------------------------------------------------ #

    def _on_motion(self) -> None:
        with self._lock:
            enabled = self._enabled
        if enabled:
            self._led.on()
            logger.info("PIR: motion detected")

    def _on_no_motion(self) -> None:
        self._led.off()

    # ------------------------------------------------------------------ #
    # Cleanup                                                              #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        self._led.off()
        self._sensor.close()
        self._btn.close()
        self._led.close()
        logger.info("PIR handler closed")
