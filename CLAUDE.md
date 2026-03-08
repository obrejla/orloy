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

The app is a motor controller for Raspberry Pi 5. It has two input surfaces (physical GPIO buttons and Bluetooth via BlueDot) that both delegate to the same core logic.

### Layered design

```
GPIO buttons  ──┐
                ├──▶  ModeManager  ──▶  MotorController  ──▶  gpiozero.Motor
BlueDot (BT)  ──┘         │
                           └──▶  gearbox_output (OutputDevice, GPIO 5)
```

- **`ModeManager`** (`src/mode_manager.py`) is the single source of truth for state (IDLE / RANDOM / MANUAL). It is thread-safe (`threading.Lock`). The random loop runs in a daemon thread and uses `threading.Event.wait()` so it wakes immediately when stopped.
- **`GPIOHandler`** (`src/gpio_handler.py`) wires `gpiozero.Button` callbacks → `ModeManager`. It owns the shared `gearbox_output` (`OutputDevice`) as a public attribute so `BluetoothHandler` can reuse it.
- **`BluetoothHandler`** (`src/bluetooth_handler.py`) wires BlueDot touch zones → the same `ModeManager` methods and the same `gearbox_output`. Shutdown hold is implemented with `threading.Timer`.
- **`MotorController`** (`src/motor_controller.py`) is a thin wrapper around `gpiozero.Motor` to make it easily mockable.
- **`config.py`** (`src/config.py`) holds all GPIO pin numbers and timing constants.

### Testing approach

All `gpiozero` and `bluedot` classes are patched before import using `unittest.mock.patch`. Tests never require Raspberry Pi hardware. Timing-sensitive random-loop tests patch `random.choice` / `random.uniform` to return small values and use `time.sleep` for brief waits.

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
