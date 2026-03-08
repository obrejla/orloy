#!/usr/bin/env python3
"""
Motor controller – entry point.

Run directly:
    python main.py

Or via systemd service (see motor_app.service).
"""

import logging
import signal
import threading

from src.bluetooth_handler import BluetoothHandler
from src.config import (
    MOTOR_FORWARD_PIN,
    MOTOR_BACKWARD_PIN,
    BUTTON_RANDOM_PIN,
    BUTTON_MANUAL_PIN,
    BUTTON_GEARBOX_PIN,
    BUTTON_SHUTDOWN_PIN,
    GEARBOX_OUTPUT_PIN,
    SHUTDOWN_HOLD_TIME,
)
from src.gpio_handler import GPIOHandler
from src.mode_manager import ModeManager
from src.motor_controller import MotorController


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("/var/log/motor_app.log"),
        ],
    )


def main() -> None:
    _configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Motor application starting")

    motor = MotorController(MOTOR_FORWARD_PIN, MOTOR_BACKWARD_PIN)
    mode_manager = ModeManager(motor)
    gpio_handler = GPIOHandler(
        mode_manager,
        random_pin=BUTTON_RANDOM_PIN,
        manual_pin=BUTTON_MANUAL_PIN,
        gearbox_btn_pin=BUTTON_GEARBOX_PIN,
        shutdown_pin=BUTTON_SHUTDOWN_PIN,
        gearbox_out_pin=GEARBOX_OUTPUT_PIN,
        shutdown_hold_time=SHUTDOWN_HOLD_TIME,
    )
    bt_handler = BluetoothHandler(
        mode_manager,
        gearbox_output=gpio_handler.gearbox_output,
        shutdown_hold_time=SHUTDOWN_HOLD_TIME,
    )

    stop_event = threading.Event()

    def _handle_signal(signum, _frame) -> None:
        logger.info("Received signal %d – shutting down application", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("Application ready – waiting for input")
    stop_event.wait()

    logger.info("Cleaning up…")
    mode_manager.stop_all()
    gpio_handler.close()
    bt_handler.close()
    motor.close()
    logger.info("Application stopped")


if __name__ == "__main__":
    main()
