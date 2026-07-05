#!/usr/bin/env python3
"""
Motor controller – entry point.

Run directly:
    python main.py

Or via systemd service (see orloy_app.service).
"""

import logging
import signal
import threading

from src.audio_handler import AudioHandler
from src.config import (
    AUDIO_TEAMS_DIR,
    AUDIO_MP3_ROOT,
    MOTOR_FORWARD_PIN,
    MOTOR_BACKWARD_PIN,
    BUTTON_RANDOM_PIN,
    BUTTON_MANUAL_PIN,
    BUTTON_LIGHTS_PIN,
    BUTTON_SHUTDOWN_PIN,
    BUTTON_PIR_TOGGLE_PIN,
    LIGHTS_OUTPUT_PIN,
    PIR_SENSOR_PIN,
    SHUTDOWN_HOLD_TIME,
    WEB_HOST,
    WEB_PORT,
)
from src.gpio_handler import GPIOHandler
from src.mode_manager import ModeManager
from src.motor_controller import MotorController
from src.pir_handler import PIRHandler
from src.speech_directory import SpeechDirectory
from src.web_handler import WebHandler


def _configure_logging() -> None:
    handlers = [logging.StreamHandler()]
    # Log to file on the Pi; fall back to console-only where the path is not
    # writable (e.g. a dev machine without /var/log access).
    try:
        handlers.append(logging.FileHandler("/var/log/orloy_app.log"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
        handlers=handlers,
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
        lights_btn_pin=BUTTON_LIGHTS_PIN,
        shutdown_pin=BUTTON_SHUTDOWN_PIN,
        lights_out_pin=LIGHTS_OUTPUT_PIN,
        shutdown_hold_time=SHUTDOWN_HOLD_TIME,
    )
    audio_handler = AudioHandler(AUDIO_TEAMS_DIR)
    speech_directory = SpeechDirectory(AUDIO_MP3_ROOT)
    pir_handler = PIRHandler(
        sensor_pin=PIR_SENSOR_PIN,
        toggle_pin=BUTTON_PIR_TOGGLE_PIN,
        audio_handler=audio_handler,
        speech_directory=speech_directory,
    )
    web_handler = WebHandler(
        mode_manager,
        lights_output=gpio_handler.lights_output,
        pir_handler=pir_handler,
        audio_handler=audio_handler,
        speech_directory=speech_directory,
        host=WEB_HOST,
        port=WEB_PORT,
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
    pir_handler.close()
    audio_handler.close()
    web_handler.close()
    motor.close()
    logger.info("Application stopped")


if __name__ == "__main__":
    main()
