"""
BlueDot Bluetooth interface.

The large dot is split into four zones by comparing |x| vs |y|:

            ┌──────────────────┐
            │      RANDOM      │   y > 0, |y| >= |x|
            │  ┌────────────┐  │
            │  │            │  │
   MANUAL   │  │            │  │  GEARBOX
  x<0,|x|≥|y| │            │  │  x>0,|x|≥|y|
            │  │            │  │
            │  └────────────┘  │
            │     SHUTDOWN     │   y < 0, |y| >= |x|
            └──────────────────┘

Interaction:
  • RANDOM / MANUAL : single tap toggles the mode
  • GEARBOX         : output pin HIGH while finger held, LOW on release
  • SHUTDOWN        : hold finger for ≥3 s to trigger OS shutdown
"""

import logging
import subprocess
import threading

from bluedot import BlueDot

from src.config import SHUTDOWN_HOLD_TIME

logger = logging.getLogger(__name__)


def _get_zone(pos) -> str:
    """Return 'top', 'bottom', 'left', or 'right' for a BlueDotPosition."""
    x, y = pos.x, pos.y
    if abs(y) >= abs(x):
        return "top" if y > 0 else "bottom"
    return "left" if x < 0 else "right"


class BluetoothHandler:
    """
    Exposes all four buttons over Bluetooth via the BlueDot Android app.

    Args:
        mode_manager:    ModeManager instance.
        gearbox_output:  gpiozero OutputDevice (or compatible) that mirrors
                         the physical gearbox pin state.  Pass None to skip.
        shutdown_hold_time: seconds the SHUTDOWN zone must be held.
    """

    def __init__(
        self,
        mode_manager,
        gearbox_output=None,
        shutdown_hold_time: float = SHUTDOWN_HOLD_TIME,
    ) -> None:
        self._mode_manager = mode_manager
        self._gearbox_output = gearbox_output
        self._shutdown_hold_time = shutdown_hold_time
        self._shutdown_timer: threading.Timer | None = None

        self._bd = BlueDot()
        self._bd.when_pressed = self._on_pressed
        self._bd.when_released = self._on_released
        logger.info("Bluetooth (BlueDot) handler ready")

    # ------------------------------------------------------------------ #
    # BlueDot callbacks                                                    #
    # ------------------------------------------------------------------ #

    def _on_pressed(self, pos) -> None:
        zone = _get_zone(pos)
        logger.info("BlueDot pressed: zone=%s", zone)

        if zone == "top":
            self._mode_manager.toggle_random()
        elif zone == "left":
            self._mode_manager.toggle_manual()
        elif zone == "right":
            if self._gearbox_output is not None:
                self._gearbox_output.on()
        elif zone == "bottom":
            self._start_shutdown_timer()

    def _on_released(self, pos) -> None:
        zone = _get_zone(pos)
        logger.info("BlueDot released: zone=%s", zone)

        if zone == "right":
            if self._gearbox_output is not None:
                self._gearbox_output.off()
        elif zone == "bottom":
            self._cancel_shutdown_timer()

    # ------------------------------------------------------------------ #
    # Shutdown timer                                                       #
    # ------------------------------------------------------------------ #

    def _start_shutdown_timer(self) -> None:
        self._cancel_shutdown_timer()
        self._shutdown_timer = threading.Timer(
            self._shutdown_hold_time, self._do_shutdown
        )
        self._shutdown_timer.daemon = True
        self._shutdown_timer.start()

    def _cancel_shutdown_timer(self) -> None:
        if self._shutdown_timer is not None:
            self._shutdown_timer.cancel()
            self._shutdown_timer = None

    def _do_shutdown(self) -> None:
        logger.info("BlueDot: shutdown hold triggered – shutting down")
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)

    # ------------------------------------------------------------------ #
    # Cleanup                                                              #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        self._cancel_shutdown_timer()
        self._bd.stop()
        logger.info("Bluetooth handler closed")
