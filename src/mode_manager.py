import logging
import random
import threading
from enum import Enum, auto

from src.config import (
    RANDOM_MOVE_MIN_SEC,
    RANDOM_MOVE_MAX_SEC,
    RANDOM_PAUSE_MIN_SEC,
    RANDOM_PAUSE_MAX_SEC,
)

logger = logging.getLogger(__name__)


class AppMode(Enum):
    IDLE = auto()
    RANDOM = auto()
    MANUAL = auto()


class ModeManager:
    """
    Manages the two operating modes of the motor.

    State machine:
        IDLE  ──toggle_random──▶  RANDOM  ──toggle_random──▶  IDLE
        IDLE  ──toggle_manual──▶  MANUAL  ──toggle_manual──▶  IDLE
        RANDOM ──toggle_manual──▶ MANUAL   (random stopped first)
        MANUAL ──toggle_random──▶ RANDOM   (manual stopped first)
    """

    def __init__(self, motor_controller) -> None:
        self._motor = motor_controller
        self._mode = AppMode.IDLE
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @property
    def mode(self) -> AppMode:
        return self._mode

    def toggle_random(self) -> None:
        with self._lock:
            if self._mode == AppMode.RANDOM:
                logger.info("Random mode: stopping")
                self._stop_random()
            else:
                if self._mode == AppMode.MANUAL:
                    logger.info("Manual mode: stopping (random requested)")
                    self._stop_manual()
                logger.info("Random mode: starting")
                self._start_random()

    def toggle_manual(self) -> None:
        with self._lock:
            if self._mode == AppMode.MANUAL:
                logger.info("Manual mode: stopping")
                self._stop_manual()
            else:
                if self._mode == AppMode.RANDOM:
                    logger.info("Random mode: stopping (manual requested)")
                    self._stop_random()
                logger.info("Manual mode: starting")
                self._start_manual()

    def stop_all(self) -> None:
        with self._lock:
            if self._mode == AppMode.RANDOM:
                self._stop_random()
            elif self._mode == AppMode.MANUAL:
                self._stop_manual()

    # ------------------------------------------------------------------ #
    # Internal helpers (must be called with self._lock held)              #
    # ------------------------------------------------------------------ #

    def _start_random(self) -> None:
        self._stop_event.clear()
        self._mode = AppMode.RANDOM
        self._thread = threading.Thread(target=self._random_loop, daemon=True, name="random-loop")
        self._thread.start()

    def _stop_random(self) -> None:
        self._stop_event.set()
        self._motor.stop()
        self._mode = AppMode.IDLE
        # Thread is daemon – it will notice the event on its next wait()

    def _start_manual(self) -> None:
        self._mode = AppMode.MANUAL
        self._motor.forward()

    def _stop_manual(self) -> None:
        self._motor.stop()
        self._mode = AppMode.IDLE

    # ------------------------------------------------------------------ #
    # Random loop (runs in a background daemon thread)                    #
    # ------------------------------------------------------------------ #

    def _random_loop(self) -> None:
        logger.debug("Random loop started")
        while not self._stop_event.is_set():
            direction = random.choice(("forward", "backward"))
            duration = random.uniform(RANDOM_MOVE_MIN_SEC, RANDOM_MOVE_MAX_SEC)

            logger.info("Random: moving %s for %.1fs", direction, duration)
            if direction == "forward":
                self._motor.forward()
            else:
                self._motor.backward()

            if self._stop_event.wait(timeout=duration):
                break

            self._motor.stop()

            pause = random.uniform(RANDOM_PAUSE_MIN_SEC, RANDOM_PAUSE_MAX_SEC)
            logger.info("Random: pausing for %.1fs", pause)

            if self._stop_event.wait(timeout=pause):
                break

        self._motor.stop()
        logger.debug("Random loop ended")
