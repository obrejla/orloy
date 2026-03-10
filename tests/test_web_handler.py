import subprocess
import unittest
from unittest.mock import MagicMock, patch

from src.mode_manager import AppMode


def _make_handler(mode=AppMode.IDLE, gearbox_output=None):
    """Build a WebHandler with server thread disabled for testing."""
    from src.web_handler import WebHandler

    mode_manager = MagicMock()
    mode_manager.mode = mode
    handler = WebHandler(mode_manager, gearbox_output=gearbox_output, _start=False)
    return handler, mode_manager


class TestWebHandlerIndex(unittest.TestCase):
    def test_index_returns_html(self):
        handler, _ = _make_handler()
        client = handler._app.test_client()
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"ORLOY", resp.data)
        self.assertIn(b"text/html", resp.content_type.encode())


class TestWebHandlerStatus(unittest.TestCase):
    def test_status_returns_idle(self):
        handler, _ = _make_handler(mode=AppMode.IDLE)
        client = handler._app.test_client()
        resp = client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"mode": "IDLE"})

    def test_status_returns_random(self):
        handler, _ = _make_handler(mode=AppMode.RANDOM)
        client = handler._app.test_client()
        resp = client.get("/api/status")
        self.assertEqual(resp.get_json(), {"mode": "RANDOM"})

    def test_status_returns_manual(self):
        handler, _ = _make_handler(mode=AppMode.MANUAL)
        client = handler._app.test_client()
        resp = client.get("/api/status")
        self.assertEqual(resp.get_json(), {"mode": "MANUAL"})


class TestWebHandlerToggleRandom(unittest.TestCase):
    def setUp(self):
        self.handler, self.mm = _make_handler(mode=AppMode.IDLE)
        self.client = self.handler._app.test_client()

    def test_toggle_random_calls_mode_manager(self):
        self.client.post("/api/toggle_random")
        self.mm.toggle_random.assert_called_once()

    def test_toggle_random_returns_mode(self):
        self.mm.mode = AppMode.RANDOM
        resp = self.client.post("/api/toggle_random")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"mode": "RANDOM"})

    def test_toggle_random_get_not_allowed(self):
        resp = self.client.get("/api/toggle_random")
        self.assertEqual(resp.status_code, 405)


class TestWebHandlerToggleManual(unittest.TestCase):
    def setUp(self):
        self.handler, self.mm = _make_handler(mode=AppMode.IDLE)
        self.client = self.handler._app.test_client()

    def test_toggle_manual_calls_mode_manager(self):
        self.client.post("/api/toggle_manual")
        self.mm.toggle_manual.assert_called_once()

    def test_toggle_manual_returns_mode(self):
        self.mm.mode = AppMode.MANUAL
        resp = self.client.post("/api/toggle_manual")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"mode": "MANUAL"})

    def test_toggle_manual_get_not_allowed(self):
        resp = self.client.get("/api/toggle_manual")
        self.assertEqual(resp.status_code, 405)


class TestWebHandlerGearbox(unittest.TestCase):
    def test_gearbox_on_activates_output(self):
        gearbox = MagicMock()
        handler, _ = _make_handler(gearbox_output=gearbox)
        client = handler._app.test_client()
        resp = client.post("/api/gearbox/on")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"gearbox": "on"})
        gearbox.on.assert_called_once()

    def test_gearbox_off_deactivates_output(self):
        gearbox = MagicMock()
        handler, _ = _make_handler(gearbox_output=gearbox)
        client = handler._app.test_client()
        resp = client.post("/api/gearbox/off")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"gearbox": "off"})
        gearbox.off.assert_called_once()

    def test_gearbox_on_without_output_is_noop(self):
        handler, _ = _make_handler(gearbox_output=None)
        client = handler._app.test_client()
        resp = client.post("/api/gearbox/on")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"gearbox": "on"})

    def test_gearbox_off_without_output_is_noop(self):
        handler, _ = _make_handler(gearbox_output=None)
        client = handler._app.test_client()
        resp = client.post("/api/gearbox/off")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"gearbox": "off"})

    def test_gearbox_on_then_off(self):
        gearbox = MagicMock()
        handler, _ = _make_handler(gearbox_output=gearbox)
        client = handler._app.test_client()
        client.post("/api/gearbox/on")
        client.post("/api/gearbox/off")
        gearbox.on.assert_called_once()
        gearbox.off.assert_called_once()


class TestWebHandlerShutdown(unittest.TestCase):
    def test_shutdown_runs_system_command(self):
        handler, _ = _make_handler()
        client = handler._app.test_client()
        with patch("src.web_handler.subprocess.run") as mock_run:
            resp = client.post("/api/shutdown")
        self.assertEqual(resp.status_code, 200)
        mock_run.assert_called_once_with(
            ["sudo", "shutdown", "-h", "now"], check=False
        )

    def test_shutdown_get_not_allowed(self):
        handler, _ = _make_handler()
        client = handler._app.test_client()
        resp = client.get("/api/shutdown")
        self.assertEqual(resp.status_code, 405)
