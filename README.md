# Orloy – Motor Controller for Raspberry Pi 5

Python application that controls a DC motor via GPIO, Bluetooth (BlueDot), and a **browser-based web control panel** served over Wi-Fi.

---

## Hardware wiring

| Component              | GPIO pin |
|------------------------|----------|
| Motor driver IN1 (FWD) | GPIO 24  |
| Motor driver IN2 (BWD) | GPIO 25  |
| Button – Random        | GPIO 17  |
| Button – Manual        | GPIO 27  |
| Button – Gearbox       | GPIO 22  |
| Button – Shutdown      | GPIO 23  |
| Gearbox signal output  | GPIO 5   |

All buttons are wired between the GPIO pin and **GND** (active-low, internal pull-up used).
Use a suitable motor driver (e.g. L298N) between the Raspberry Pi and the motor.

---

## Button behaviour

| Button   | Short press / hold                                               |
|----------|------------------------------------------------------------------|
| Random   | Toggles "random" mode (see below)                                |
| Manual   | Toggles "manual" mode (see below)                                |
| Gearbox  | Drives GPIO 5 HIGH while held, LOW on release                    |
| Shutdown | **Hold ≥ 3 s** → `sudo shutdown -h now`                          |

### Random mode
1. Picks a random direction (forward / backward) and a random duration (5–20 s).
2. Runs the motor for that duration, then stops.
3. Waits for a random pause (1–10 min).
4. Repeats until the **Random** button is pressed again.

Pressing **Manual** while random mode is active stops random mode first.

### Manual mode
1. Starts the motor in the **forward** direction.
2. Pressing **Manual** again stops the motor.

Pressing **Random** while manual mode is active stops manual mode first.

---

## Web control panel

When the application starts it binds a small HTTP server on **port 8080** (all interfaces).  Connect your phone or laptop to the same Wi-Fi network as the Pi and open:

```
http://<Pi's IP address>:8080/
```

The page displays the current mode (IDLE / RANDOM / MANUAL) and four control buttons:

| Button           | Behaviour                                               |
|------------------|---------------------------------------------------------|
| **RANDOM**       | Tap to toggle random mode                               |
| **MANUAL**       | Tap to toggle manual mode                               |
| **GEARBOX**      | Held HIGH while pressed, LOW on release                 |
| **SHUTDOWN**     | Hold for 3 seconds to trigger `sudo shutdown -h now`   |

The page polls `/api/status` every 2 seconds so the mode indicator stays in sync when the mode changes via a physical button or Bluetooth.

### REST API

| Method | Path                  | Action                                        |
|--------|-----------------------|-----------------------------------------------|
| GET    | `/api/status`         | Returns `{"mode": "IDLE"|"RANDOM"|"MANUAL"}`  |
| POST   | `/api/toggle_random`  | Toggle random mode; returns updated mode      |
| POST   | `/api/toggle_manual`  | Toggle manual mode; returns updated mode      |
| POST   | `/api/gearbox/on`     | Drive gearbox output HIGH                     |
| POST   | `/api/gearbox/off`    | Drive gearbox output LOW                      |
| POST   | `/api/shutdown`       | Trigger `sudo shutdown -h now`                |

---

## BlueDot (Bluetooth) interface

Install the **BlueDot** app on an Android phone, pair it with the Raspberry Pi, and open the app.
The large dot is divided into four zones:

```
        ┌──────────────────┐
        │   RANDOM (top)   │
        ├────────┬─────────┤
        │ MANUAL │ GEARBOX │
        │ (left) │ (right) │
        ├────────┴─────────┤
        │  SHUTDOWN (bot.) │
        └──────────────────┘
```

- **RANDOM / MANUAL** – single tap toggles the mode.
- **GEARBOX** – held high while finger pressed, released on lift.
- **SHUTDOWN** – hold finger for ≥ 3 s to trigger shutdown.

---

## Raspberry Pi OS setup

### 1. Install OS dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv bluetooth bluez
```

### 2. Add the `pi` user to required groups

```bash
sudo usermod -aG gpio,bluetooth pi
```

Log out and back in (or reboot) for group changes to take effect.

### 3. Enable Bluetooth and make the Pi discoverable (one-time)

```bash
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Pair your phone:
bluetoothctl
  power on
  agent on
  discoverable on
  # Accept pairing request from the phone...
  trust <PHONE_MAC>
  quit
```

After the first pairing the phone will reconnect automatically.

### 4. Deploy the application

```bash
# Clone / copy the project to the Pi
scp -r . pi@raspberrypi.local:/home/pi/orloy_app

# On the Pi:
cd /home/pi/orloy_app
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 5. Create the log file with correct permissions

```bash
sudo touch /var/log/orloy_app.log
sudo chown pi:pi /var/log/orloy_app.log
```

### 6. Allow the `pi` user to call `shutdown` without a password

```bash
sudo visudo
```

Add this line at the end:

```
pi ALL=(ALL) NOPASSWD: /sbin/shutdown
```

### 7. Install and enable the systemd service

```bash
sudo cp /home/pi/orloy_app/orloy_app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orloy_app.service
sudo systemctl start orloy_app.service
```

Check status:

```bash
sudo systemctl status orloy_app.service
journalctl -u orloy_app.service -f
```

The service will now start automatically on every boot.

---

## Running tests

Tests run on any machine – no Raspberry Pi hardware needed.

```bash
# In the project root:
pip install -r requirements.txt   # or just: pip install gpiozero bluedot
python -m pytest tests/ -v
```

---

## Project structure

```
orloy_app/
├── src/
│   ├── config.py             # GPIO pin constants, timing defaults, web config
│   ├── motor_controller.py   # Thin wrapper around gpiozero.Motor
│   ├── mode_manager.py       # Random / Manual mode state machine
│   ├── gpio_handler.py       # Physical GPIO button callbacks
│   ├── bluetooth_handler.py  # BlueDot Bluetooth interface
│   └── web_handler.py        # HTTP control panel (Flask/Werkzeug)
├── tests/
│   ├── test_motor_controller.py
│   ├── test_mode_manager.py
│   ├── test_gpio_handler.py
│   ├── test_bluetooth_handler.py
│   └── test_web_handler.py
├── main.py                   # Application entry point
├── orloy_app.service         # systemd unit file
└── requirements.txt
```
