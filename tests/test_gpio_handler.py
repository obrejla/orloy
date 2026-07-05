import unittest
from unittest.mock import MagicMock, patch, call


def _make_gpio_handler(mode_manager):
    """Helper: build a GPIOHandler with all gpiozero devices mocked."""
    mock_btn_random = MagicMock()
    mock_btn_manual = MagicMock()
    mock_btn_lights = MagicMock()
    mock_btn_shutdown = MagicMock()
    mock_lights_output = MagicMock()

    btn_iter = iter([mock_btn_random, mock_btn_manual, mock_btn_lights, mock_btn_shutdown])

    with (
        patch("src.gpio_handler.Button", side_effect=lambda *a, **kw: next(btn_iter)),
        patch("src.gpio_handler.OutputDevice", return_value=mock_lights_output),
    ):
        from src.gpio_handler import GPIOHandler
        handler = GPIOHandler(mode_manager)

    return handler, mock_lights_output


class TestGPIOHandlerCallbacks(unittest.TestCase):
    def setUp(self):
        self.mode_manager = MagicMock()
        self.handler, self.lights_output = _make_gpio_handler(self.mode_manager)

    def test_random_button_calls_toggle_random(self):
        self.handler._on_random()
        self.mode_manager.toggle_random.assert_called_once()

    def test_manual_button_calls_toggle_manual(self):
        self.handler._on_manual()
        self.mode_manager.toggle_manual.assert_called_once()

    def test_lights_button_toggles_output_pin(self):
        self.handler._on_lights_toggle()
        self.lights_output.toggle.assert_called_once()

    def test_lights_button_toggles_each_press(self):
        self.handler._on_lights_toggle()
        self.handler._on_lights_toggle()
        self.assertEqual(self.lights_output.toggle.call_count, 2)

    def test_shutdown_runs_shutdown_command(self):
        with patch("src.gpio_handler.subprocess.run") as mock_run:
            self.handler._on_shutdown()
            mock_run.assert_called_once_with(
                ["sudo", "shutdown", "-h", "now"], check=False
            )

    def test_lights_output_is_accessible(self):
        """lights_output must be a public attribute (used by WebHandler)."""
        self.assertIs(self.handler.lights_output, self.lights_output)


class TestGPIOHandlerClose(unittest.TestCase):
    def setUp(self):
        self.mode_manager = MagicMock()

        self.mock_btns = [MagicMock() for _ in range(4)]
        self.mock_output = MagicMock()

        btn_iter = iter(self.mock_btns)

        with (
            patch("src.gpio_handler.Button", side_effect=lambda *a, **kw: next(btn_iter)),
            patch("src.gpio_handler.OutputDevice", return_value=self.mock_output),
        ):
            from src.gpio_handler import GPIOHandler
            self.handler = GPIOHandler(self.mode_manager)

    def test_close_releases_all_devices(self):
        self.handler.close()
        for btn in self.mock_btns:
            btn.close.assert_called_once()
        self.mock_output.close.assert_called_once()
