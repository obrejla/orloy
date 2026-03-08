import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from src.mode_manager import AppMode, ModeManager


class TestModeManagerInitial(unittest.TestCase):
    def setUp(self):
        self.motor = MagicMock()
        self.mgr = ModeManager(self.motor)

    def test_initial_mode_is_idle(self):
        self.assertEqual(self.mgr.mode, AppMode.IDLE)


class TestManualMode(unittest.TestCase):
    def setUp(self):
        self.motor = MagicMock()
        self.mgr = ModeManager(self.motor)

    def test_toggle_manual_enters_manual_mode(self):
        self.mgr.toggle_manual()
        self.assertEqual(self.mgr.mode, AppMode.MANUAL)

    def test_toggle_manual_starts_motor_forward(self):
        self.mgr.toggle_manual()
        self.motor.forward.assert_called_once()

    def test_toggle_manual_twice_returns_to_idle(self):
        self.mgr.toggle_manual()
        self.mgr.toggle_manual()
        self.assertEqual(self.mgr.mode, AppMode.IDLE)

    def test_toggle_manual_twice_stops_motor(self):
        self.mgr.toggle_manual()
        self.mgr.toggle_manual()
        self.motor.stop.assert_called()

    def test_stop_all_from_manual_returns_to_idle(self):
        self.mgr.toggle_manual()
        self.mgr.stop_all()
        self.assertEqual(self.mgr.mode, AppMode.IDLE)
        self.motor.stop.assert_called()


class TestRandomMode(unittest.TestCase):
    def setUp(self):
        self.motor = MagicMock()
        self.mgr = ModeManager(self.motor)

    def test_toggle_random_enters_random_mode(self):
        self.mgr.toggle_random()
        self.assertEqual(self.mgr.mode, AppMode.RANDOM)
        self.mgr.toggle_random()  # cleanup

    def test_toggle_random_twice_returns_to_idle(self):
        self.mgr.toggle_random()
        self.mgr.toggle_random()
        self.assertEqual(self.mgr.mode, AppMode.IDLE)

    def test_toggle_random_twice_stops_motor(self):
        self.mgr.toggle_random()
        self.mgr.toggle_random()
        self.motor.stop.assert_called()

    def test_stop_all_from_random_returns_to_idle(self):
        self.mgr.toggle_random()
        self.mgr.stop_all()
        self.assertEqual(self.mgr.mode, AppMode.IDLE)

    def test_random_loop_drives_motor_then_stops(self):
        """The random background thread should call forward/backward then stop."""
        with (
            patch("src.mode_manager.random.choice", return_value="forward"),
            patch("src.mode_manager.random.uniform", return_value=0.05),
        ):
            self.mgr.toggle_random()
            time.sleep(0.3)
            self.mgr.toggle_random()  # stop

        self.motor.forward.assert_called()
        self.motor.stop.assert_called()

    def test_random_loop_backward_direction(self):
        with (
            patch("src.mode_manager.random.choice", return_value="backward"),
            patch("src.mode_manager.random.uniform", return_value=0.05),
        ):
            self.mgr.toggle_random()
            time.sleep(0.3)
            self.mgr.toggle_random()

        self.motor.backward.assert_called()


class TestModeTransitions(unittest.TestCase):
    def setUp(self):
        self.motor = MagicMock()
        self.mgr = ModeManager(self.motor)

    def test_manual_stops_random_first(self):
        self.mgr.toggle_random()
        self.assertEqual(self.mgr.mode, AppMode.RANDOM)
        self.mgr.toggle_manual()
        self.assertEqual(self.mgr.mode, AppMode.MANUAL)

    def test_random_stops_manual_first(self):
        self.mgr.toggle_manual()
        self.assertEqual(self.mgr.mode, AppMode.MANUAL)
        self.mgr.toggle_random()
        self.assertEqual(self.mgr.mode, AppMode.RANDOM)
        self.mgr.toggle_random()  # cleanup

    def test_stop_all_from_idle_is_noop(self):
        self.mgr.stop_all()
        self.assertEqual(self.mgr.mode, AppMode.IDLE)
        self.motor.stop.assert_not_called()
