"""
Audio (MP3) playback handler.

Uses pygame.mixer to play MP3 files from a configured directory.

Playback is serialised through an internal queue: if a track is already
playing when ``play()`` is called, the new request replaces any pending
item in the queue and plays as soon as the current track finishes.
Only one track can be pending at a time (last-write wins).
"""

import logging
import os
import re
import threading
import time
from pathlib import Path

# Suppress SDL display requirement so pygame.mixer works headless / as a service.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

# Use ALSA directly (no PulseAudio session in a service context).
os.environ.setdefault("SDL_AUDIODRIVER", "alsa")

# Point ALSA at the first USB audio card if present, so the correct output
# device is used when a USB sound card is connected alongside built-in audio.
# The user can override this by setting AUDIODEV in the environment before
# starting the service (e.g. via systemd override or ~/.config/environment.d/).
def _find_usb_audio_card() -> str | None:
    """Return 'plughw:N' for the first USB audio card, or None."""
    try:
        text = Path("/proc/asound/cards").read_text()
        for line in text.splitlines():
            # Format: " N [shortname]: driver_name - long description"
            m = re.match(r"^\s*(\d+)\s+\[.*\]:\s+(\S+)", line)
            if m and "USB" in m.group(2):
                return f"plughw:{m.group(1)}"
    except OSError:
        pass
    return None

if "AUDIODEV" not in os.environ:
    _usb_card = _find_usb_audio_card()
    if _usb_card:
        os.environ["AUDIODEV"] = _usb_card

import pygame  # noqa: E402  (must follow SDL env-var setup above)

from src.config import AUDIO_TEAMS_DIR  # noqa: E402

logger = logging.getLogger(__name__)


class AudioHandler:
    """
    Plays MP3 files from a designated directory via pygame.mixer.

    Thread-safe.  Only bare filenames are accepted — path separators in the
    filename argument are rejected to prevent directory traversal.

    Playback is serialised: a new ``play()`` call while a track is already
    playing queues the incoming track (replacing any previously queued but
    not-yet-started track).  The queued track starts automatically when the
    current one ends.

    Args:
        directory: Path to the default folder containing MP3 files.
                   Defaults to AUDIO_TEAMS_DIR from config.
    """

    def __init__(self, directory: str = AUDIO_TEAMS_DIR) -> None:
        self._lock = threading.Lock()
        self._directory = Path(directory).resolve()

        # Queue state: _next_path holds the next track to play (or None).
        # Protected by _next_cond.
        self._next_cond = threading.Condition(threading.Lock())
        self._next_path: Path | None = None

        self._stop_event = threading.Event()
        self._closed = False

        pygame.mixer.init()
        logger.info(
            "Audio handler ready – directory: %s  (mixer: %s, device: %s)",
            self._directory, pygame.mixer.get_init(), os.environ.get("AUDIODEV", "default"),
        )

        self._consumer = threading.Thread(
            target=self._consume, daemon=True, name="audio-consumer"
        )
        self._consumer.start()

    # ------------------------------------------------------------------ #
    # Internal queue consumer                                              #
    # ------------------------------------------------------------------ #

    def _consume(self) -> None:
        """Background thread: waits for queued tracks and plays them."""
        while not self._stop_event.is_set():
            with self._next_cond:
                while self._next_path is None and not self._stop_event.is_set():
                    self._next_cond.wait(timeout=0.1)
                if self._stop_event.is_set():
                    return
                filepath = self._next_path
                self._next_path = None

            # Wait for the mixer to finish the current track.
            while not self._stop_event.is_set() and pygame.mixer.music.get_busy():
                time.sleep(0.05)

            if self._stop_event.is_set():
                return

            with self._lock:
                pygame.mixer.music.load(str(filepath))
                pygame.mixer.music.play()

    def _enqueue(self, path: Path) -> None:
        """Replace any pending track with *path* and wake the consumer."""
        with self._next_cond:
            self._next_path = path
            self._next_cond.notify()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def list_tracks(self, directory: Path | None = None) -> list[str]:
        """Return sorted list of .mp3 filenames in *directory*.

        Args:
            directory: Directory to list.  Defaults to the handler's own
                       directory when not provided.
        """
        d = Path(directory).resolve() if directory is not None else self._directory
        with self._lock:
            return sorted(p.name for p in d.glob("*.mp3"))

    def play(self, filename: str, directory: Path | None = None) -> None:
        """Queue a track for playback.

        If a track is currently playing the new track will start as soon as
        it finishes.  Any previously queued (but not yet started) track is
        replaced.

        Args:
            filename:  Bare filename (e.g. ``"cerveni.mp3"``).  Must not
                       contain path separators.
            directory: Directory that must contain the file.  Defaults to
                       the handler's own directory when not provided.

        Raises:
            ValueError: If ``filename`` is empty, contains a path separator,
                        or resolves outside *directory*.
        """
        d = Path(directory).resolve() if directory is not None else self._directory
        path = self._validate(filename, d)
        self._enqueue(path)
        logger.info("Audio: queued %s", filename)

    @staticmethod
    def _validate(filename: str, directory: Path) -> Path:
        """Return the absolute path for *filename* inside *directory*.

        Raises:
            ValueError: On empty filename, path separators, or traversal.
        """
        if not filename or "/" in filename or "\\" in filename:
            raise ValueError(f"Invalid filename: {filename!r}")
        full_path = directory / filename
        if full_path.parent.resolve() != directory:
            raise ValueError(f"Path traversal attempt: {filename!r}")
        return full_path

    @property
    def is_playing(self) -> bool:
        """True while a track is playing or one is queued to play next."""
        with self._next_cond:
            has_pending = self._next_path is not None
        return bool(pygame.mixer.music.get_busy()) or has_pending

    def stop(self) -> None:
        """Stop playback and discard any queued track."""
        with self._next_cond:
            self._next_path = None
        with self._lock:
            pygame.mixer.music.stop()
        logger.info("Audio: stopped")

    def close(self) -> None:
        """Stop playback, shut down the consumer thread, and quit pygame.mixer."""
        if self._closed:
            return
        self._closed = True
        with self._lock:
            pygame.mixer.music.stop()
        self._stop_event.set()
        with self._next_cond:
            self._next_cond.notify_all()
        if self._consumer.is_alive():
            self._consumer.join(timeout=2)
        pygame.mixer.quit()
        logger.info("Audio handler closed")

    def wait_idle(self, timeout: float = 2.0) -> None:
        """Block until no track is playing or queued.

        Intended for use in tests — not part of the production API.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.is_playing:
                return
            time.sleep(0.01)
