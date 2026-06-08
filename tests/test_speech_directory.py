import shutil
import tempfile
import unittest
from pathlib import Path

from src.speech_directory import SpeechDirectory


class TestSpeechDirectory(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        for name in ("speech", "teams", "growl"):
            Path(self.root, name).mkdir()
        # A stray file should never be offered as a directory.
        Path(self.root, "notes.txt").write_text("ignore me")
        self.holder = SpeechDirectory(self.root)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_list_dirs_sorted_and_excludes_teams(self):
        self.assertEqual(self.holder.list_dirs(), ["growl", "speech"])

    def test_list_dirs_ignores_files(self):
        self.assertNotIn("notes.txt", self.holder.list_dirs())

    def test_default_name_is_speech(self):
        self.assertEqual(self.holder.name, "speech")

    def test_current_path_resolves_to_default(self):
        self.assertEqual(self.holder.current_path(), Path(self.root, "speech").resolve())

    def test_set_name_updates_name_and_path(self):
        self.holder.set_name("growl")
        self.assertEqual(self.holder.name, "growl")
        self.assertEqual(self.holder.current_path(), Path(self.root, "growl").resolve())

    def test_custom_default(self):
        holder = SpeechDirectory(self.root, default="growl")
        self.assertEqual(holder.name, "growl")

    def _assert_rejected(self, name):
        with self.assertRaises(ValueError):
            self.holder.set_name(name)
        # State must be unchanged after a rejected selection.
        self.assertEqual(self.holder.name, "speech")

    def test_set_name_rejects_excluded(self):
        self._assert_rejected("teams")

    def test_set_name_rejects_nonexistent(self):
        self._assert_rejected("nope")

    def test_set_name_rejects_traversal(self):
        self._assert_rejected("../x")

    def test_set_name_rejects_separator(self):
        self._assert_rejected("a/b")

    def test_set_name_rejects_empty(self):
        self._assert_rejected("")

    def test_set_name_rejects_file(self):
        self._assert_rejected("notes.txt")


if __name__ == "__main__":
    unittest.main()
