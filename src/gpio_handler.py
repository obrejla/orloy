import logging
import subprocess

from gpiozero import Button, OutputDevice

from src.config import (
    BUTTON_RANDOM_PIN,
    BUTTON_MANUAL_PIN,
    BUTTON_GEARBOX_PIN,
    BUTTON_SHUTDOWN_PIN,
    GEARBOX_OUTPUT_PIN,
    SHUTDOWN_HOLD_TIME,
)

logger = logging.getLogger(__name__)


class GPIOHandler:
    """
    Maps physical GPIO buttons to application actions.

    Wiring (all buttons use internal pull-up; connect button between pin and GND):
        Random   → GPIO 17
        Manual   → GPIO 27
        Gearbox  → GPIO 22
        Shutdown → GPIO 23  (hold ≥3 s to trigger)

    Output:
        Gearbox signal → GPIO 5  (HIGH while button held)
    """

    def __init__(
        self,
        mode_manager,
        random_pin: int = BUTTON_RANDOM_PIN,
        manual_pin: int = BUTTON_MANUAL_PIN,
        gearbox_btn_pin: int = BUTTON_GEARBOX_PIN,
        shutdown_pin: int = BUTTON_SHUTDOWN_PIN,
        gearbox_out_pin: int = GEARBOX_OUTPUT_PIN,
        shutdown_hold_time: float = SHUTDOWN_HOLD_TIME,
    ) -> None:
        self._mode_manager = mode_manager

        self._btn_random = Button(random_pin, pull_up=True)
        self._btn_manual = Button(manual_pin, pull_up=True)
        self._btn_gearbox = Button(gearbox_btn_pin, pull_up=True)
        self._btn_shutdown = Button(shutdown_pin, pull_up=True, hold_time=shutdown_hold_time)

        self.gearbox_output = OutputDevice(gearbox_out_pin, initial_value=False)

        self._setup_callbacks()
        logger.info("GPIO handler ready")

    # ------------------------------------------------------------------ #
    # Callback wiring                                                      #
    # ------------------------------------------------------------------ #

    def _setup_callbacks(self) -> None:
        self._btn_random.when_pressed = self._on_random
        self._btn_manual.when_pressed = self._on_manual
        self._btn_gearbox.when_pressed = self._on_gearbox_pressed
        self._btn_gearbox.when_released = self._on_gearbox_released
        self._btn_shutdown.when_held = self._on_shutdown

    # ------------------------------------------------------------------ #
    # Handlers                                                             #
    # ------------------------------------------------------------------ #

    def _on_random(self) -> None:
        logger.info("GPIO: random button pressed")
        self._mode_manager.toggle_random()

    def _on_manual(self) -> None:
        logger.info("GPIO: manual button pressed")
        self._mode_manager.toggle_manual()

    def _on_gearbox_pressed(self) -> None:
        logger.info("GPIO: gearbox button pressed")
        self.gearbox_output.on()

    def _on_gearbox_released(self) -> None:
        logger.info("GPIO: gearbox button released")
        self.gearbox_output.off()

    def _on_shutdown(self) -> None:
        logger.info("GPIO: shutdown button held – shutting down")
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)

    # ------------------------------------------------------------------ #
    # Cleanup                                                              #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        for device in (
            self._btn_random,
            self._btn_manual,
            self._btn_gearbox,
            self._btn_shutdown,
            self.gearbox_output,
        ):
            device.close()
        logger.info("GPIO handler closed")
