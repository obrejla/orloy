# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests (no hardware required)
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_mode_manager.py -v

# Run a single test case
python -m pytest tests/test_mode_manager.py::TestManualMode::test_toggle_manual_enters_manual_mode -v

# Run the application (Raspberry Pi only)
python main.py
```

## Architecture

The app is a motor controller for Raspberry Pi 5. It has two input surfaces (physical GPIO buttons and web) that both delegate to the same core logic.

### Layered design

```
GPIO buttons  ──┐
                ├──▶  ModeManager  ──▶  MotorController  ──▶  gpiozero.Motor
Web (HTTP)    ──┘         │
                           └──▶  gearbox_output (OutputDevice, GPIO 5)

Web (HTTP)    ──▶  AudioHandler  ──▶  pygame.mixer
              (teams + speech routes share one AudioHandler instance;
               playback is serialised through an internal queue)
```

- **`ModeManager`** (`src/mode_manager.py`) is the single source of truth for state (IDLE / RANDOM / MANUAL). It is thread-safe (`threading.Lock`). The random loop runs in a daemon thread and uses `threading.Event.wait()` so it wakes immediately when stopped.
- **`GPIOHandler`** (`src/gpio_handler.py`) wires `gpiozero.Button` callbacks → `ModeManager`. It owns the shared `gearbox_output` (`OutputDevice`) as a public attribute so `WebHandler` can reuse it.
- **`WebHandler`** (`src/web_handler.py`) serves `src/index.html` and a REST API over HTTP (default port 8080). Runs a Werkzeug server in a daemon thread. Shutdown hold is implemented client-side in JavaScript.
- **`PIRHandler`** (`src/pir_handler.py`) manages a `gpiozero.MotionSensor` on GPIO 12, a toggle button on GPIO 16, and a `gpiozero.LED` indicator on GPIO 20. Detection is OFF at startup; logs motion events when enabled and turns the LED on during motion (off when motion stops). Exposes `toggle()` and `enabled` for the web API.
- **`AudioHandler`** (`src/audio_handler.py`) plays MP3 files via `pygame.mixer`. Thread-safe. No GPIO pins. A single shared instance handles both the Teams (`mp3/teams/`) and Speech (`mp3/speech/`) players. Playback requests are serialised through an internal condition-variable queue: a new `play()` or `play_from()` call while a track is already playing waits in queue until it finishes. Exposes `list_tracks(directory?)`, `play(filename)`, `play_from(filename, directory)`, `stop()`, and `close()`.
- **`MotorController`** (`src/motor_controller.py`) is a thin wrapper around `gpiozero.Motor` to make it easily mockable.
- **`config.py`** (`src/config.py`) holds all GPIO pin numbers, timing constants, and web server settings (`WEB_HOST`, `WEB_PORT`).

### Testing approach

All `gpiozero` classes are patched before import using `unittest.mock.patch`. Tests never require Raspberry Pi hardware. Timing-sensitive random-loop tests patch `random.choice` / `random.uniform` to return small values and use `time.sleep` for brief waits.

### Pin assignments (from `src/config.py`)

| Signal              | GPIO |
|---------------------|------|
| Motor forward       | 24   |
| Motor backward      | 25   |
| Button: Random      | 17   |
| Button: Manual      | 27   |
| Button: Gearbox     | 22   |
| Button: Shutdown    | 23   |
| Gearbox signal out  | 5    |
| PIR sensor          | 12   |
| Button: PIR toggle  | 16   |
| LED: PIR indicator  | 20   |

## Development conventions

- **Web UI — SHUTDOWN button position**: The SHUTDOWN button must always be the last control on the web UI page (`src/index.html`). Do not add any new button or section after it.
- **Documentation**: Every new feature or feature adjustment must be properly documented — public classes and methods must have docstrings, and changes must be reflected in `README.md`.
