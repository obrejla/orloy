import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_pir_handler(
    initial_enabled=True,
    audio_handler=None,
    speech_directory=None,
    initial_cooldown_sec=0,
):
    """Helper: build a PIRHandler with all gpiozero devices mocked.

    Cooldown defaults to 0 (disabled) so existing behavioural tests are
    unaffected; cooldown tests pass an explicit value.
    """
    mock_sensor = MagicMock()
    mock_btn = MagicMock()
    mock_led = MagicMock()

    with (
        patch("src.pir_handler.MotionSensor", return_value=mock_sensor),
        patch("src.pir_handler.Button", return_value=mock_btn),
        patch("src.pir_handler.LED", return_value=mock_led),
    ):
        from src.pir_handler import PIRHandler
        handler = PIRHandler(
            initial_enabled=initial_enabled,
            audio_handler=audio_handler,
            speech_directory=speech_directory,
            initial_cooldown_sec=initial_cooldown_sec,
        )

    return handler, mock_sensor, mock_btn, mock_led


class TestPIRHandlerInit(unittest.TestCase):
    def test_disabled_by_default(self):
        with (
            patch("src.pir_handler.MotionSensor", return_value=MagicMock()),
            patch("src.pir_handler.Button", return_value=MagicMock()),
            patch("src.pir_handler.LED", return_value=MagicMock()),
        ):
            from src.pir_handler import PIRHandler
            handler = PIRHandler()
        self.assertFalse(handler.enabled)

    def test_disabled_on_start(self):
        handler, _, _, _ = _make_pir_handler(initial_enabled=False)
        self.assertFalse(handler.enabled)

    def test_motion_callback_wired(self):
        handler, mock_sensor, _, _ = _make_pir_handler()
        self.assertEqual(mock_sensor.when_motion, handler._on_motion)

    def test_no_motion_callback_wired(self):
        handler, mock_sensor, _, _ = _make_pir_handler()
        self.assertEqual(mock_sensor.when_no_motion, handler._on_no_motion)

    def test_button_callback_wired(self):
        handler, _, mock_btn, _ = _make_pir_handler()
        self.assertEqual(mock_btn.when_pressed, handler.toggle)


class TestPIRHandlerToggle(unittest.TestCase):
    def test_toggle_disables(self):
        handler, _, _, _ = _make_pir_handler(initial_enabled=True)
        result = handler.toggle()
        self.assertFalse(result)
        self.assertFalse(handler.enabled)

    def test_toggle_enables(self):
        handler, _, _, _ = _make_pir_handler(initial_enabled=False)
        result = handler.toggle()
        self.assertTrue(result)
        self.assertTrue(handler.enabled)

    def test_toggle_return_matches_enabled(self):
        handler, _, _, _ = _make_pir_handler()
        result = handler.toggle()
        self.assertEqual(result, handler.enabled)

    def test_double_toggle_restores_state(self):
        handler, _, _, _ = _make_pir_handler(initial_enabled=True)
        handler.toggle()
        handler.toggle()
        self.assertTrue(handler.enabled)

    def test_toggle_off_turns_led_off(self):
        handler, _, _, mock_led = _make_pir_handler(initial_enabled=True)
        handler.toggle()  # disable
        mock_led.off.assert_called()

    def test_toggle_on_does_not_force_led_on(self):
        """Re-enabling does not turn LED on immediately; LED lights on next motion."""
        handler, _, _, mock_led = _make_pir_handler(initial_enabled=False)
        handler.toggle()  # enable
        mock_led.on.assert_not_called()


class TestPIRHandlerMotion(unittest.TestCase):
    def test_motion_logged_when_enabled(self):
        handler, _, _, _ = _make_pir_handler(initial_enabled=True)
        with self.assertLogs("src.pir_handler", level="INFO") as cm:
            handler._on_motion()
        self.assertTrue(any("motion detected" in line for line in cm.output))

    def test_motion_suppressed_when_disabled(self):
        handler, _, _, _ = _make_pir_handler(initial_enabled=False)
        with self.assertNoLogs("src.pir_handler", level="INFO"):
            handler._on_motion()

    def test_motion_logged_after_re_enable(self):
        handler, _, _, _ = _make_pir_handler(initial_enabled=True)
        handler.toggle()   # disable
        handler.toggle()   # re-enable
        with self.assertLogs("src.pir_handler", level="INFO") as cm:
            handler._on_motion()
        self.assertTrue(any("motion detected" in line for line in cm.output))

    def test_led_on_when_motion_enabled(self):
        handler, _, _, mock_led = _make_pir_handler(initial_enabled=True)
        handler._on_motion()
        mock_led.on.assert_called_once()

    def test_led_stays_off_when_disabled(self):
        handler, _, _, mock_led = _make_pir_handler(initial_enabled=False)
        handler._on_motion()
        mock_led.on.assert_not_called()

    def test_led_off_on_no_motion(self):
        handler, _, _, mock_led = _make_pir_handler()
        handler._on_no_motion()
        mock_led.off.assert_called()


class TestPIRHandlerClose(unittest.TestCase):
    def test_close_closes_all_devices(self):
        handler, mock_sensor, mock_btn, mock_led = _make_pir_handler()
        handler.close()
        mock_sensor.close.assert_called_once()
        mock_btn.close.assert_called_once()
        mock_led.close.assert_called_once()

    def test_close_turns_led_off(self):
        handler, _, _, mock_led = _make_pir_handler()
        handler.close()
        mock_led.off.assert_called()


class TestPIRHandlerAudio(unittest.TestCase):
    def _make_with_audio(
        self, is_playing=False, tracks=None, enabled=True, cooldown=0
    ):
        from src.speech_directory import SpeechDirectory

        mock_audio = MagicMock()
        mock_audio.is_playing = is_playing
        mock_audio.list_tracks.return_value = tracks if tracks is not None else ["muhehe.mp3"]
        tmp = tempfile.mkdtemp()
        Path(tmp, "speech").mkdir()
        Path(tmp, "growl").mkdir()
        holder = SpeechDirectory(tmp)
        handler, _, _, _ = _make_pir_handler(
            initial_enabled=enabled,
            audio_handler=mock_audio,
            speech_directory=holder,
            initial_cooldown_sec=cooldown,
        )
        return handler, mock_audio, holder, tmp

    def test_motion_plays_random_track_when_idle(self):
        handler, mock_audio, _, tmp = self._make_with_audio(is_playing=False)
        handler._on_motion()
        mock_audio.play.assert_called_once()
        shutil.rmtree(tmp)

    def test_motion_does_not_play_when_audio_busy(self):
        handler, mock_audio, _, tmp = self._make_with_audio(is_playing=True)
        handler._on_motion()
        mock_audio.play.assert_not_called()
        shutil.rmtree(tmp)

    def test_motion_does_not_play_when_disabled(self):
        handler, mock_audio, _, tmp = self._make_with_audio(enabled=False)
        handler._on_motion()
        mock_audio.play.assert_not_called()
        shutil.rmtree(tmp)

    def test_motion_plays_from_speech_dir(self):
        handler, mock_audio, holder, tmp = self._make_with_audio(tracks=["okamzik.mp3"])
        handler._on_motion()
        args = mock_audio.play.call_args
        self.assertEqual(args[0][1], holder.current_path())
        shutil.rmtree(tmp)

    def test_motion_follows_selected_folder(self):
        handler, mock_audio, holder, tmp = self._make_with_audio(tracks=["okamzik.mp3"])
        holder.set_name("growl")
        handler._on_motion()
        args = mock_audio.play.call_args
        self.assertEqual(args[0][1], Path(tmp, "growl").resolve())
        mock_audio.list_tracks.assert_called_with(Path(tmp, "growl").resolve())
        shutil.rmtree(tmp)

    def test_motion_no_play_when_no_tracks(self):
        handler, mock_audio, _, tmp = self._make_with_audio(tracks=[])
        handler._on_motion()
        mock_audio.play.assert_not_called()
        shutil.rmtree(tmp)


class TestPIRHandlerCooldown(TestPIRHandlerAudio):
    def test_default_cooldown_from_config(self):
        from src.config import PIR_TRIGGER_COOLDOWN_SEC

        handler, _, _, _ = _make_pir_handler(
            initial_cooldown_sec=PIR_TRIGGER_COOLDOWN_SEC
        )
        self.assertEqual(handler.cooldown_sec, PIR_TRIGGER_COOLDOWN_SEC)

    def test_set_cooldown_updates_value(self):
        handler, _, _, _ = _make_pir_handler(initial_cooldown_sec=0)
        self.assertEqual(handler.set_cooldown(120), 120.0)
        self.assertEqual(handler.cooldown_sec, 120.0)

    def test_set_cooldown_rejects_negative(self):
        handler, _, _, _ = _make_pir_handler()
        with self.assertRaises(ValueError):
            handler.set_cooldown(-1)

    def test_zero_cooldown_plays_every_motion(self):
        handler, mock_audio, _, tmp = self._make_with_audio(cooldown=0)
        handler._on_motion()
        handler._on_motion()
        self.assertEqual(mock_audio.play.call_count, 2)
        shutil.rmtree(tmp)

    def test_second_motion_within_cooldown_suppressed(self):
        handler, mock_audio, _, tmp = self._make_with_audio(cooldown=1800)
        with patch("src.pir_handler.time.monotonic", side_effect=[0.0, 60.0]):
            handler._on_motion()   # t=0 → plays
            handler._on_motion()   # t=60s → within 30-min window, suppressed
        mock_audio.play.assert_called_once()
        shutil.rmtree(tmp)

    def test_suppressed_motion_still_lights_led_and_logs(self):
        handler, mock_audio, _, tmp = self._make_with_audio(cooldown=1800)
        with patch("src.pir_handler.time.monotonic", side_effect=[0.0, 60.0]):
            handler._on_motion()
            handler._led.on.reset_mock()
            with self.assertLogs("src.pir_handler", level="INFO") as cm:
                handler._on_motion()
        handler._led.on.assert_called_once()  # LED still responds while suppressed
        self.assertTrue(any("motion detected" in line for line in cm.output))
        self.assertTrue(any("cooldown" in line for line in cm.output))
        shutil.rmtree(tmp)

    def test_motion_plays_again_after_cooldown_elapses(self):
        handler, mock_audio, _, tmp = self._make_with_audio(cooldown=1800)
        with patch("src.pir_handler.time.monotonic", side_effect=[0.0, 1801.0]):
            handler._on_motion()   # t=0 → plays
            handler._on_motion()   # t=1801s → past window, plays again
        self.assertEqual(mock_audio.play.call_count, 2)
        shutil.rmtree(tmp)

    def test_re_enable_resets_cooldown(self):
        handler, mock_audio, _, tmp = self._make_with_audio(cooldown=1800)
        with patch("src.pir_handler.time.monotonic", side_effect=[0.0, 60.0]):
            handler._on_motion()   # t=0 → plays, records trigger
            handler.toggle()       # disable
            handler.toggle()       # re-enable → clears last trigger
            handler._on_motion()   # t=60s but timer reset → plays
        self.assertEqual(mock_audio.play.call_count, 2)
        shutil.rmtree(tmp)
