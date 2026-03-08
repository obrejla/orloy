import time
import unittest
from unittest.mock import MagicMock, patch

from src.bluetooth_handler import _get_zone


# ------------------------------------------------------------------ #
# Helper                                                               #
# ------------------------------------------------------------------ #

def _pos(x: float, y: float):
    p = MagicMock()
    p.x = x
    p.y = y
    return p


def _make_bt_handler(mode_manager, gearbox_output=None, hold_time=3.0):
    mock_bd = MagicMock()
    with patch("src.bluetooth_handler.BlueDot", return_value=mock_bd):
        from src.bluetooth_handler import BluetoothHandler
        handler = BluetoothHandler(
            mode_manager,
            gearbox_output=gearbox_output,
            shutdown_hold_time=hold_time,
        )
    return handler, mock_bd


# ------------------------------------------------------------------ #
# Zone detection                                                        #
# ------------------------------------------------------------------ #

class TestGetZone(unittest.TestCase):
    def test_top(self):
        self.assertEqual(_get_zone(_pos(0.0, 0.9)), "top")

    def test_bottom(self):
        self.assertEqual(_get_zone(_pos(0.0, -0.9)), "bottom")

    def test_left(self):
        self.assertEqual(_get_zone(_pos(-0.9, 0.0)), "left")

    def test_right(self):
        self.assertEqual(_get_zone(_pos(0.9, 0.0)), "right")

    def test_top_diagonal(self):
        # y slightly > x → top
        self.assertEqual(_get_zone(_pos(0.5, 0.6)), "top")

    def test_right_diagonal(self):
        # x slightly > y → right
        self.assertEqual(_get_zone(_pos(0.6, 0.5)), "right")

    def test_equal_magnitude_favors_y(self):
        # |y| == |x| → uses y branch
        self.assertEqual(_get_zone(_pos(0.5, 0.5)), "top")
        self.assertEqual(_get_zone(_pos(0.5, -0.5)), "bottom")


# ------------------------------------------------------------------ #
# Press events                                                          #
# ------------------------------------------------------------------ #

class TestBluetoothHandlerPress(unittest.TestCase):
    def setUp(self):
        self.mode_manager = MagicMock()
        self.gearbox_output = MagicMock()
        self.handler, _ = _make_bt_handler(self.mode_manager, self.gearbox_output)

    def test_top_press_toggles_random(self):
        self.handler._on_pressed(_pos(0, 0.8))
        self.mode_manager.toggle_random.assert_called_once()

    def test_left_press_toggles_manual(self):
        self.handler._on_pressed(_pos(-0.8, 0))
        self.mode_manager.toggle_manual.assert_called_once()

    def test_right_press_activates_gearbox_output(self):
        self.handler._on_pressed(_pos(0.8, 0))
        self.gearbox_output.on.assert_called_once()

    def test_right_release_deactivates_gearbox_output(self):
        self.handler._on_released(_pos(0.8, 0))
        self.gearbox_output.off.assert_called_once()

    def test_right_press_without_gearbox_output_is_noop(self):
        handler, _ = _make_bt_handler(self.mode_manager, gearbox_output=None)
        # Should not raise even when gearbox_output is None
        handler._on_pressed(_pos(0.8, 0))

    def test_bottom_press_starts_shutdown_timer(self):
        self.handler._on_pressed(_pos(0, -0.8))
        self.assertIsNotNone(self.handler._shutdown_timer)
        self.handler._cancel_shutdown_timer()

    def test_bottom_release_cancels_shutdown_timer(self):
        self.handler._on_pressed(_pos(0, -0.8))
        self.handler._on_released(_pos(0, -0.8))
        self.assertIsNone(self.handler._shutdown_timer)


# ------------------------------------------------------------------ #
# Shutdown timer                                                        #
# ------------------------------------------------------------------ #

class TestBluetoothShutdown(unittest.TestCase):
    def setUp(self):
        self.mode_manager = MagicMock()

    def test_shutdown_fires_after_hold_time(self):
        handler, _ = _make_bt_handler(self.mode_manager, hold_time=0.1)
        with patch("src.bluetooth_handler.subprocess.run") as mock_run:
            handler._on_pressed(_pos(0, -0.8))
            time.sleep(0.3)
            mock_run.assert_called_once_with(
                ["sudo", "shutdown", "-h", "now"], check=False
            )

    def test_shutdown_does_not_fire_if_released_early(self):
        handler, _ = _make_bt_handler(self.mode_manager, hold_time=0.5)
        with patch("src.bluetooth_handler.subprocess.run") as mock_run:
            handler._on_pressed(_pos(0, -0.8))
            time.sleep(0.1)
            handler._on_released(_pos(0, -0.8))
            time.sleep(0.6)  # wait past would-be trigger
            mock_run.assert_not_called()

    def test_close_cancels_pending_timer(self):
        handler, _ = _make_bt_handler(self.mode_manager, hold_time=10.0)
        with patch("src.bluetooth_handler.subprocess.run") as mock_run:
            handler._on_pressed(_pos(0, -0.8))
            handler.close()
            self.assertIsNone(handler._shutdown_timer)
            mock_run.assert_not_called()
