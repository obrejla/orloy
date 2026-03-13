import unittest
from unittest.mock import MagicMock, patch


def _make_pir_handler(initial_enabled=True):
    """Helper: build a PIRHandler with all gpiozero devices mocked."""
    mock_sensor = MagicMock()
    mock_btn = MagicMock()

    device_iter = iter([mock_sensor, mock_btn])

    with (
        patch("src.pir_handler.MotionSensor", return_value=mock_sensor),
        patch("src.pir_handler.Button", return_value=mock_btn),
    ):
        from src.pir_handler import PIRHandler
        handler = PIRHandler(initial_enabled=initial_enabled)

    return handler, mock_sensor, mock_btn


class TestPIRHandlerInit(unittest.TestCase):
    def test_enabled_by_default(self):
        handler, _, _ = _make_pir_handler()
        self.assertTrue(handler.enabled)

    def test_disabled_on_start(self):
        handler, _, _ = _make_pir_handler(initial_enabled=False)
        self.assertFalse(handler.enabled)

    def test_motion_callback_wired(self):
        handler, mock_sensor, _ = _make_pir_handler()
        self.assertEqual(mock_sensor.when_motion, handler._on_motion)

    def test_button_callback_wired(self):
        handler, _, mock_btn = _make_pir_handler()
        self.assertEqual(mock_btn.when_pressed, handler.toggle)


class TestPIRHandlerToggle(unittest.TestCase):
    def test_toggle_disables(self):
        handler, _, _ = _make_pir_handler(initial_enabled=True)
        result = handler.toggle()
        self.assertFalse(result)
        self.assertFalse(handler.enabled)

    def test_toggle_enables(self):
        handler, _, _ = _make_pir_handler(initial_enabled=False)
        result = handler.toggle()
        self.assertTrue(result)
        self.assertTrue(handler.enabled)

    def test_toggle_return_matches_enabled(self):
        handler, _, _ = _make_pir_handler()
        result = handler.toggle()
        self.assertEqual(result, handler.enabled)

    def test_double_toggle_restores_state(self):
        handler, _, _ = _make_pir_handler(initial_enabled=True)
        handler.toggle()
        handler.toggle()
        self.assertTrue(handler.enabled)


class TestPIRHandlerMotion(unittest.TestCase):
    def test_motion_logged_when_enabled(self):
        handler, _, _ = _make_pir_handler(initial_enabled=True)
        with self.assertLogs("src.pir_handler", level="INFO") as cm:
            handler._on_motion()
        self.assertTrue(any("motion detected" in line for line in cm.output))

    def test_motion_suppressed_when_disabled(self):
        handler, _, _ = _make_pir_handler(initial_enabled=False)
        with self.assertNoLogs("src.pir_handler", level="INFO"):
            handler._on_motion()

    def test_motion_logged_after_re_enable(self):
        handler, _, _ = _make_pir_handler(initial_enabled=True)
        handler.toggle()   # disable
        handler.toggle()   # re-enable
        with self.assertLogs("src.pir_handler", level="INFO") as cm:
            handler._on_motion()
        self.assertTrue(any("motion detected" in line for line in cm.output))


class TestPIRHandlerClose(unittest.TestCase):
    def test_close_closes_all_devices(self):
        handler, mock_sensor, mock_btn = _make_pir_handler()
        handler.close()
        mock_sensor.close.assert_called_once()
        mock_btn.close.assert_called_once()
