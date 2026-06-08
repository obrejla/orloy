"""
Active speech-folder selection.

The speech player (web UI) and the PIR motion auto-play both draw their MP3
tracks from a single sub-folder of the ``mp3/`` root.  ``SpeechDirectory`` is
the thread-safe source of truth for *which* sub-folder is currently active.

A single instance is shared between ``WebHandler`` (which lets the user switch
folders) and ``PIRHandler`` (which reads the current folder each time motion
fires), so a change made from the web is seen immediately by the motion
callback.  The selection is in-memory only and resets to the default on restart.
"""

import threading
from pathlib import Path

from src.config import DEFAULT_SPEECH_SUBDIR, SPEECH_DIR_EXCLUDE


class SpeechDirectory:
    """
    Thread-safe holder for the currently selected speech sub-folder.

    Only immediate sub-directories of *root* are valid selections, and folders
    named in *exclude* are never offered or accepted.

    Args:
        root:    Path to the parent folder containing the speech sub-folders
                 (typically ``AUDIO_MP3_ROOT``).
        default: Sub-folder name selected at startup (default ``"speech"``).
        exclude: Sub-folder names hidden from the selector and rejected by
                 :meth:`set_name` (default: the separate teams player).
    """

    def __init__(
        self,
        root: str,
        default: str = DEFAULT_SPEECH_SUBDIR,
        exclude=SPEECH_DIR_EXCLUDE,
    ) -> None:
        self._lock = threading.Lock()
        self._root = Path(root).resolve()
        self._exclude = tuple(exclude)
        self._name = default

    def list_dirs(self) -> list[str]:
        """Return the sorted names of selectable sub-folders of the root.

        Immediate sub-directories only; names in ``exclude`` are filtered out.
        """
        with self._lock:
            return sorted(
                p.name
                for p in self._root.iterdir()
                if p.is_dir() and p.name not in self._exclude
            )

    @property
    def name(self) -> str:
        """The currently selected sub-folder name."""
        with self._lock:
            return self._name

    def current_path(self) -> Path:
        """Return the resolved absolute path of the currently selected folder."""
        with self._lock:
            return (self._root / self._name).resolve()

    def set_name(self, name: str) -> None:
        """Select *name* as the active speech sub-folder.

        Args:
            name: Bare sub-folder name (no path separators).

        Raises:
            ValueError: If *name* is empty, contains a path separator, is
                        excluded, escapes the root, or is not an existing
                        directory.  The current selection is left unchanged.
        """
        if not name or "/" in name or "\\" in name:
            raise ValueError(f"Invalid directory: {name!r}")
        if name in self._exclude:
            raise ValueError(f"Directory not selectable: {name!r}")
        candidate = (self._root / name).resolve()
        if candidate.parent != self._root:
            raise ValueError(f"Path traversal attempt: {name!r}")
        if not candidate.is_dir():
            raise ValueError(f"Directory does not exist: {name!r}")
        with self._lock:
            self._name = name
