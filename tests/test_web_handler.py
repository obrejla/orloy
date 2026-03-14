import subprocess
import unittest
from unittest.mock import MagicMock, patch

from src.mode_manager import AppMode


def _make_handler(mode=AppMode.IDLE, gearbox_output=None, pir_handler=None, audio_handler=None):
    """Build a WebHandler with server thread disabled for testing."""
    from src.web_handler import WebHandler

    mode_manager = MagicMock()
    mode_manager.mode = mode
    handler = WebHandler(
        mode_manager,
        gearbox_output=gearbox_output,
        pir_handler=pir_handler,
        audio_handler=audio_handler,
        _start=False,
    )
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


class TestWebHandlerPIR(unittest.TestCase):
    def test_status_includes_pir_enabled(self):
        mock_pir = MagicMock()
        mock_pir.enabled = True
        handler, _ = _make_handler(pir_handler=mock_pir)
        client = handler._app.test_client()
        resp = client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("pir_enabled", data)
        self.assertTrue(data["pir_enabled"])

    def test_status_excludes_pir_enabled_without_handler(self):
        handler, _ = _make_handler(pir_handler=None)
        client = handler._app.test_client()
        resp = client.get("/api/status")
        data = resp.get_json()
        self.assertNotIn("pir_enabled", data)

    def test_pir_toggle_calls_handler(self):
        mock_pir = MagicMock()
        mock_pir.toggle.return_value = False
        handler, _ = _make_handler(pir_handler=mock_pir)
        client = handler._app.test_client()
        client.post("/api/pir/toggle")
        mock_pir.toggle.assert_called_once()

    def test_pir_toggle_returns_new_state(self):
        mock_pir = MagicMock()
        mock_pir.toggle.return_value = False
        handler, _ = _make_handler(pir_handler=mock_pir)
        client = handler._app.test_client()
        resp = client.post("/api/pir/toggle")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"pir_enabled": False})

    def test_pir_toggle_without_handler_returns_none(self):
        handler, _ = _make_handler(pir_handler=None)
        client = handler._app.test_client()
        resp = client.post("/api/pir/toggle")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"pir_enabled": None})

    def test_pir_toggle_get_not_allowed(self):
        handler, _ = _make_handler()
        client = handler._app.test_client()
        resp = client.get("/api/pir/toggle")
        self.assertEqual(resp.status_code, 405)


class TestWebHandlerAudio(unittest.TestCase):
    def setUp(self):
        self.mock_audio = MagicMock()
        self.mock_audio.list_tracks.return_value = ["cerveni.mp3", "modri.mp3"]
        self.handler, _ = _make_handler(audio_handler=self.mock_audio)
        self.client = self.handler._app.test_client()

    def test_status_includes_audio_playing(self):
        self.mock_audio.is_playing = True
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["audio_playing"])

    def test_status_audio_playing_false_when_idle(self):
        self.mock_audio.is_playing = False
        resp = self.client.get("/api/status")
        self.assertFalse(resp.get_json()["audio_playing"])

    def test_status_excludes_audio_playing_without_handler(self):
        handler, _ = _make_handler(audio_handler=None)
        client = handler._app.test_client()
        resp = client.get("/api/status")
        self.assertNotIn("audio_playing", resp.get_json())

    def test_get_tracks_returns_list(self):
        resp = self.client.get("/api/audio/tracks")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"tracks": ["cerveni.mp3", "modri.mp3"]})

    def test_get_tracks_without_handler_returns_empty(self):
        handler, _ = _make_handler(audio_handler=None)
        client = handler._app.test_client()
        resp = client.get("/api/audio/tracks")
        self.assertEqual(resp.get_json(), {"tracks": []})

    def test_play_calls_handler(self):
        resp = self.client.post(
            "/api/audio/play",
            json={"filename": "cerveni.mp3"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.mock_audio.play.assert_called_once_with("cerveni.mp3")

    def test_play_returns_playing_filename(self):
        resp = self.client.post("/api/audio/play", json={"filename": "modri.mp3"})
        self.assertEqual(resp.get_json(), {"playing": "modri.mp3"})

    def test_play_invalid_filename_returns_400(self):
        self.mock_audio.play.side_effect = ValueError("invalid")
        resp = self.client.post("/api/audio/play", json={"filename": "../evil.mp3"})
        self.assertEqual(resp.status_code, 400)

    def test_play_without_handler_returns_503(self):
        handler, _ = _make_handler(audio_handler=None)
        client = handler._app.test_client()
        resp = client.post("/api/audio/play", json={"filename": "cerveni.mp3"})
        self.assertEqual(resp.status_code, 503)

    def test_stop_calls_handler(self):
        resp = self.client.post("/api/audio/stop")
        self.assertEqual(resp.status_code, 200)
        self.mock_audio.stop.assert_called_once()

    def test_stop_without_handler_is_noop(self):
        handler, _ = _make_handler(audio_handler=None)
        client = handler._app.test_client()
        resp = client.post("/api/audio/stop")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"stopped": True})

    def test_play_get_not_allowed(self):
        resp = self.client.get("/api/audio/play")
        self.assertEqual(resp.status_code, 405)

    def test_stop_get_not_allowed(self):
        resp = self.client.get("/api/audio/stop")
        self.assertEqual(resp.status_code, 405)
