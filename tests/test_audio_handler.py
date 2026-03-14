"""Tests for AudioHandler.

All pygame interaction is mocked — no audio device or hardware needed.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_handler(tmp_dir):
    """Return (handler, mock_pygame, patcher) with pygame fully mocked."""
    mock_pygame = MagicMock()
    mock_pygame.mixer.music.get_busy.return_value = False
    patcher = patch("src.audio_handler.pygame", mock_pygame)
    patcher.start()
    from src.audio_handler import AudioHandler
    handler = AudioHandler(directory=str(tmp_dir))
    return handler, mock_pygame, patcher


class TestAudioHandlerInit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.handler, self.mock_pygame, self.patcher = _make_handler(self.tmp)

    def tearDown(self):
        self.handler.close()
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_mixer_init_called(self):
        self.mock_pygame.mixer.init.assert_called_once()


class TestAudioHandlerListTracks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.handler, self.mock_pygame, self.patcher = _make_handler(self.tmp)

    def tearDown(self):
        self.handler.close()
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_empty_dir_returns_empty_list(self):
        self.assertEqual(self.handler.list_tracks(), [])

    def test_returns_sorted_mp3_filenames(self):
        for name in ["zeleni.mp3", "cerveni.mp3", "modri.mp3"]:
            (self.tmp / name).touch()
        self.assertEqual(self.handler.list_tracks(), ["cerveni.mp3", "modri.mp3", "zeleni.mp3"])

    def test_ignores_non_mp3_files(self):
        (self.tmp / "cerveni.mp3").touch()
        (self.tmp / "notes.txt").touch()
        (self.tmp / "sound.wav").touch()
        self.assertEqual(self.handler.list_tracks(), ["cerveni.mp3"])

    def test_list_tracks_from_other_directory(self):
        other = Path(tempfile.mkdtemp())
        try:
            (other / "muhehe.mp3").touch()
            (other / "okamzik.mp3").touch()
            self.assertEqual(self.handler.list_tracks(other), ["muhehe.mp3", "okamzik.mp3"])
        finally:
            shutil.rmtree(other)


class TestAudioHandlerPlay(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.other = Path(tempfile.mkdtemp())
        (self.tmp / "cerveni.mp3").touch()
        (self.other / "muhehe.mp3").touch()
        self.handler, self.mock_pygame, self.patcher = _make_handler(self.tmp)

    def tearDown(self):
        self.handler.close()
        self.patcher.stop()
        shutil.rmtree(self.tmp)
        shutil.rmtree(self.other)

    def test_play_default_dir_calls_load_and_play(self):
        self.handler.play("cerveni.mp3")
        self.handler.wait_idle()
        self.mock_pygame.mixer.music.load.assert_called_once_with(
            str(self.tmp.resolve() / "cerveni.mp3")
        )
        self.mock_pygame.mixer.music.play.assert_called_once()

    def test_play_explicit_dir_calls_load_with_correct_path(self):
        self.handler.play("muhehe.mp3", self.other)
        self.handler.wait_idle()
        self.mock_pygame.mixer.music.load.assert_called_once_with(
            str(self.other.resolve() / "muhehe.mp3")
        )
        self.mock_pygame.mixer.music.play.assert_called_once()

    def test_empty_filename_raises(self):
        with self.assertRaises(ValueError):
            self.handler.play("")

    def test_filename_with_forward_slash_raises(self):
        with self.assertRaises(ValueError):
            self.handler.play("../other.mp3")

    def test_filename_with_backslash_raises(self):
        with self.assertRaises(ValueError):
            self.handler.play("sub\\file.mp3")

    def test_empty_filename_with_explicit_dir_raises(self):
        with self.assertRaises(ValueError):
            self.handler.play("", self.other)

    def test_slash_in_filename_with_explicit_dir_raises(self):
        with self.assertRaises(ValueError):
            self.handler.play("../evil.mp3", self.other)

    def test_explicit_dir_plays_after_default_dir(self):
        # Enqueue a teams track, let it play, then enqueue a speech track.
        self.handler.play("cerveni.mp3")
        self.handler.wait_idle()
        self.handler.play("muhehe.mp3", self.other)
        self.handler.wait_idle()
        load_calls = [c.args[0] for c in self.mock_pygame.mixer.music.load.call_args_list]
        self.assertIn(str(self.other.resolve() / "muhehe.mp3"), load_calls)


class TestAudioHandlerIsPlaying(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.handler, self.mock_pygame, self.patcher = _make_handler(self.tmp)

    def tearDown(self):
        self.handler.close()
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_is_playing_true_when_busy(self):
        self.mock_pygame.mixer.music.get_busy.return_value = True
        self.assertTrue(self.handler.is_playing)

    def test_is_playing_false_when_not_busy(self):
        self.mock_pygame.mixer.music.get_busy.return_value = False
        self.assertFalse(self.handler.is_playing)

    def test_is_playing_true_when_track_queued(self):
        # Keep mixer busy so the pending path stays in _next_path.
        self.mock_pygame.mixer.music.get_busy.return_value = True
        tmp = Path(self.tmp)
        (tmp / "cerveni.mp3").touch()
        self.handler.play("cerveni.mp3")
        self.assertTrue(self.handler.is_playing)


class TestAudioHandlerCurrentTrack(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.handler, self.mock_pygame, self.patcher = _make_handler(self.tmp)

    def tearDown(self):
        self.handler.close()
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_current_track_none_when_idle(self):
        self.assertIsNone(self.handler.current_track)

    def test_current_track_returns_queued_filename(self):
        self.mock_pygame.mixer.music.get_busy.return_value = True
        (self.tmp / "cerveni.mp3").touch()
        self.handler.play("cerveni.mp3")
        self.assertEqual(self.handler.current_track, "cerveni.mp3")

    def test_current_track_none_after_stop(self):
        self.mock_pygame.mixer.music.get_busy.return_value = True
        (self.tmp / "cerveni.mp3").touch()
        self.handler.play("cerveni.mp3")
        self.handler.stop()
        self.mock_pygame.mixer.music.get_busy.return_value = False
        self.assertIsNone(self.handler.current_track)


class TestAudioHandlerStop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.handler, self.mock_pygame, self.patcher = _make_handler(self.tmp)

    def tearDown(self):
        self.handler.close()
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_stop_calls_mixer_stop(self):
        self.handler.stop()
        self.mock_pygame.mixer.music.stop.assert_called_once()

    def test_stop_clears_pending_track(self):
        # Queue a track while mixer is busy.
        self.mock_pygame.mixer.music.get_busy.return_value = True
        tmp = Path(self.tmp)
        (tmp / "cerveni.mp3").touch()
        self.handler.play("cerveni.mp3")
        # Stop: clears queue and stops mixer.
        self.handler.stop()
        # Mixer now idle — is_playing must be False.
        self.mock_pygame.mixer.music.get_busy.return_value = False
        self.assertFalse(self.handler.is_playing)


class TestAudioHandlerClose(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.handler, self.mock_pygame, self.patcher = _make_handler(self.tmp)

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_close_stops_and_quits_mixer(self):
        self.handler.close()
        self.mock_pygame.mixer.music.stop.assert_called()
        self.mock_pygame.mixer.quit.assert_called_once()

    def test_close_is_idempotent(self):
        self.handler.close()
        self.handler.close()  # second call must not raise
        self.mock_pygame.mixer.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
