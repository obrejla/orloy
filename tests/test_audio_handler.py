"""Tests for AudioHandler.

All pygame interaction is mocked — no audio device or hardware needed.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestAudioHandlerInit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mock_pygame = MagicMock()
        self.patcher = patch("src.audio_handler.pygame", self.mock_pygame)
        self.patcher.start()
        from src.audio_handler import AudioHandler
        self.handler = AudioHandler(directory=self.tmp)

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_mixer_init_called(self):
        self.mock_pygame.mixer.init.assert_called_once()


class TestAudioHandlerListTracks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.mock_pygame = MagicMock()
        self.patcher = patch("src.audio_handler.pygame", self.mock_pygame)
        self.patcher.start()
        from src.audio_handler import AudioHandler
        self.handler = AudioHandler(directory=str(self.tmp))

    def tearDown(self):
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


class TestAudioHandlerPlay(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "cerveni.mp3").touch()
        self.mock_pygame = MagicMock()
        self.patcher = patch("src.audio_handler.pygame", self.mock_pygame)
        self.patcher.start()
        from src.audio_handler import AudioHandler
        self.handler = AudioHandler(directory=str(self.tmp))

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_play_calls_load_and_play(self):
        self.handler.play("cerveni.mp3")
        self.mock_pygame.mixer.music.load.assert_called_once_with(
            str(self.tmp.resolve() / "cerveni.mp3")
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


class TestAudioHandlerIsPlaying(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mock_pygame = MagicMock()
        self.patcher = patch("src.audio_handler.pygame", self.mock_pygame)
        self.patcher.start()
        from src.audio_handler import AudioHandler
        self.handler = AudioHandler(directory=self.tmp)

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_is_playing_true_when_busy(self):
        self.mock_pygame.mixer.music.get_busy.return_value = True
        self.assertTrue(self.handler.is_playing)

    def test_is_playing_false_when_not_busy(self):
        self.mock_pygame.mixer.music.get_busy.return_value = False
        self.assertFalse(self.handler.is_playing)


class TestAudioHandlerStop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mock_pygame = MagicMock()
        self.patcher = patch("src.audio_handler.pygame", self.mock_pygame)
        self.patcher.start()
        from src.audio_handler import AudioHandler
        self.handler = AudioHandler(directory=self.tmp)

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_stop_calls_mixer_stop(self):
        self.handler.stop()
        self.mock_pygame.mixer.music.stop.assert_called_once()


class TestAudioHandlerClose(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mock_pygame = MagicMock()
        self.patcher = patch("src.audio_handler.pygame", self.mock_pygame)
        self.patcher.start()
        from src.audio_handler import AudioHandler
        self.handler = AudioHandler(directory=self.tmp)

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp)

    def test_close_stops_and_quits_mixer(self):
        self.handler.close()
        self.mock_pygame.mixer.music.stop.assert_called()
        self.mock_pygame.mixer.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
