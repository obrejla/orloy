import unittest
from unittest.mock import MagicMock, patch


class TestMotorController(unittest.TestCase):
    def setUp(self):
        self.mock_motor = MagicMock()
        self.mock_motor.value = 0

        patcher = patch("src.motor_controller.Motor", return_value=self.mock_motor)
        patcher.start()
        self.addCleanup(patcher.stop)

        from src.motor_controller import MotorController
        self.ctrl = MotorController(24, 25)

    # ------------------------------------------------------------------ #

    def test_forward_delegates_to_gpiozero(self):
        self.ctrl.forward()
        self.mock_motor.forward.assert_called_once()

    def test_backward_delegates_to_gpiozero(self):
        self.ctrl.backward()
        self.mock_motor.backward.assert_called_once()

    def test_stop_delegates_to_gpiozero(self):
        self.ctrl.stop()
        self.mock_motor.stop.assert_called_once()

    def test_is_active_true_when_motor_running(self):
        self.mock_motor.value = 1.0
        self.assertTrue(self.ctrl.is_active)

    def test_is_active_false_when_motor_stopped(self):
        self.mock_motor.value = 0
        self.assertFalse(self.ctrl.is_active)

    def test_is_active_true_for_backward(self):
        self.mock_motor.value = -1.0
        self.assertTrue(self.ctrl.is_active)

    def test_close_delegates_to_gpiozero(self):
        self.ctrl.close()
        self.mock_motor.close.assert_called_once()
