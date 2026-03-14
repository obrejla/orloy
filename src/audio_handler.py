"""
Audio (MP3) playback handler.

Uses pygame.mixer to play MP3 files from a configured directory.
"""

import logging
import os
import re
import threading
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

    Args:
        directory: Path to the folder containing MP3 files.
                   Defaults to AUDIO_TEAMS_DIR from config.
    """

    def __init__(self, directory: str = AUDIO_TEAMS_DIR) -> None:
        self._lock = threading.Lock()
        self._directory = Path(directory).resolve()
        pygame.mixer.init()
        logger.info(
            "Audio handler ready – directory: %s  (mixer: %s, device: %s)",
            self._directory, pygame.mixer.get_init(), os.environ.get("AUDIODEV", "default"),
        )

    def list_tracks(self) -> list[str]:
        """Return sorted list of .mp3 filenames in the directory."""
        with self._lock:
            return sorted(p.name for p in self._directory.glob("*.mp3"))

    def play(self, filename: str) -> None:
        """Load and play a track by filename.

        Args:
            filename: Bare filename (e.g. ``"cerveni.mp3"``).  Must not
                      contain path separators.

        Raises:
            ValueError: If ``filename`` is empty or contains a path separator.
        """
        if not filename or "/" in filename or "\\" in filename:
            raise ValueError(f"Invalid filename: {filename!r}")
        full_path = self._directory / filename
        if full_path.parent.resolve() != self._directory:
            raise ValueError(f"Path traversal attempt: {filename!r}")
        with self._lock:
            pygame.mixer.music.load(str(full_path))
            pygame.mixer.music.play()
        logger.info("Audio: playing %s", filename)

    @property
    def is_playing(self) -> bool:
        """True while a track is currently playing."""
        return bool(pygame.mixer.music.get_busy())

    def stop(self) -> None:
        """Stop any currently playing audio."""
        with self._lock:
            pygame.mixer.music.stop()
        logger.info("Audio: stopped")

    def close(self) -> None:
        """Stop playback and shut down pygame.mixer."""
        self.stop()
        pygame.mixer.quit()
        logger.info("Audio handler closed")
