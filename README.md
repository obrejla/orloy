# Orloy – Motor Controller for Raspberry Pi 5

Python application that controls a DC motor via GPIO buttons and a **browser-based web control panel** served over Wi-Fi.

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
| PIR motion sensor      | GPIO 12  |
| Button – PIR toggle    | GPIO 16  |
| LED – PIR motion indicator | GPIO 20  |

All buttons are wired between the GPIO pin and **GND** (active-low, internal pull-up used).
The PIR sensor output is wired directly to GPIO 12 (the sensor drives the pin; no pull resistor required).
The LED anode connects to GPIO 20 through a suitable current-limiting resistor (e.g. 330 Ω), cathode to GND.
Use a suitable motor driver (e.g. L298N) between the Raspberry Pi and the motor.

---

## Button behaviour

| Button      | Short press / hold                                            |
|-------------|---------------------------------------------------------------|
| Random      | Toggles "random" mode (see below)                             |
| Manual      | Toggles "manual" mode (see below)                             |
| Gearbox     | Drives GPIO 5 HIGH while held, LOW on release                 |
| Shutdown    | **Hold ≥ 3 s** → `sudo shutdown -h now`                       |
| PIR toggle  | Toggles PIR motion detection ON / OFF (starts OFF)             |

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

When the application starts it binds a small HTTP server on **port 8080** (all interfaces).  Connect to the **Orloy** Wi-Fi network broadcast by the Pi (see [Wi-Fi access point setup](#wi-fi-access-point-setup) below) and open the URL that matches your AP setup method:

| AP setup method | URL |
|---|---|
| Option A / B (NetworkManager) | `http://10.42.0.1:8080/` |
| Option C (hostapd/dnsmasq) | `http://192.168.4.1:8080/` |

The page displays the current mode (IDLE / RANDOM / MANUAL) and seven control sections:

| Button / Section | Behaviour                                               |
|------------------|---------------------------------------------------------|
| **RANDOM**       | Tap to toggle random mode                               |
| **MANUAL**       | Tap to toggle manual mode                               |
| **GEARBOX**      | Held HIGH while pressed, LOW on release                 |
| **MOTION**       | Tap to toggle PIR motion detection ON / OFF             |
| **TEAM SOUND**   | Select a track from the dropdown and tap PLAY; tap STOP to stop |
| **SPEECH**       | Select a speech track and tap PLAY; tap STOP to stop    |
| **SHUTDOWN**     | Hold for 3 seconds to trigger `sudo shutdown -h now`    |

Both TEAM SOUND and SPEECH share the same audio player.  If one is already playing, a new PLAY request from either section is queued and starts automatically when the current track ends.  All player controls (PLAY, STOP, dropdown) are disabled while any audio is playing or pending.

The page polls `/api/status` every 2 seconds so the mode indicator stays in sync when the mode changes via a physical button.

### REST API

| Method | Path                  | Action                                                              |
|--------|-----------------------|---------------------------------------------------------------------|
| GET    | `/api/status`         | Returns `{"mode": "…", "pir_enabled": true\|false}`                |
| POST   | `/api/toggle_random`  | Toggle random mode; returns updated mode                            |
| POST   | `/api/toggle_manual`  | Toggle manual mode; returns updated mode                            |
| POST   | `/api/gearbox/on`     | Drive gearbox output HIGH                                           |
| POST   | `/api/gearbox/off`    | Drive gearbox output LOW                                            |
| POST   | `/api/pir/toggle`     | Toggle PIR detection ON/OFF; returns `{"pir_enabled": true\|false}` |
| POST   | `/api/shutdown`       | Trigger `sudo shutdown -h now`                                      |
| GET    | `/api/audio/tracks`   | Returns `{"tracks": ["cerveni.mp3", …]}`                            |
| POST   | `/api/audio/play`     | Play a team track; body `{"filename": "cerveni.mp3"}`; returns `{"playing": "…"}` |
| POST   | `/api/audio/stop`     | Stop playback; returns `{"stopped": true}`                          |
| GET    | `/api/speech/tracks`  | Returns `{"tracks": ["muhehe.mp3", …]}`                             |
| POST   | `/api/speech/play`    | Play a speech track; body `{"filename": "muhehe.mp3"}`; returns `{"playing": "…"}` |
| POST   | `/api/speech/stop`    | Stop playback; returns `{"stopped": true}`                          |

---

## Wi-Fi access point setup

The Raspberry Pi is configured as a **standalone Wi-Fi access point** — it broadcasts its own network named **Orloy** so no external router is needed.  Once the AP is set up the Pi always creates the network on boot; you connect your phone or laptop to it and open the control panel URL.

Three methods are described below.  Use whichever matches your OS version and setup.

---

### Option A — Desktop GUI *(preferred, Raspberry Pi OS Bookworm with Desktop)*

Raspberry Pi OS Bookworm uses NetworkManager, which has built-in hotspot support accessible from the taskbar.

1. Click the **network icon** in the taskbar (top-right corner).
2. Select **Advanced Options → Create Wireless Hotspot…**
3. Fill in the form:
   - **SSID:** `Orloy`
   - **Security:** WPA2
   - **Password:** `orloy1234`
4. Click **Create**.

NetworkManager writes and manages the configuration automatically.  The hotspot starts immediately.

5. Force 2.4 GHz band and a fixed channel so all devices (including iPhones) can see the network:

```bash
sudo nmcli connection modify Orloy 802-11-wireless.band bg 802-11-wireless.channel 6
sudo nmcli connection down Orloy && sudo nmcli connection up Orloy
sudo nmcli connection modify Orloy connection.autoconnect yes
```

The hotspot will now reconnect on every subsequent boot.

**Pi's IP on this network:** `10.42.0.1`
**Connect via:** `http://10.42.0.1:8080/` or `http://raspberrypi.local:8080/` (if avahi-daemon is running)

---

### Option B — `nmcli` one-liner *(Raspberry Pi OS Bookworm, headless/Lite)*

If there is no desktop available but the OS is still Bookworm (NetworkManager present), use the command line:

```bash
sudo nmcli device wifi hotspot \
    ifname wlan0 \
    ssid Orloy \
    password orloy1234
```

Force 2.4 GHz band and a fixed channel so all devices (including iPhones) can see the network, then enable autoconnect:

```bash
sudo nmcli connection modify Hotspot 802-11-wireless.band bg 802-11-wireless.channel 6
sudo nmcli connection modify Hotspot connection.autoconnect yes
sudo nmcli connection down Hotspot && sudo nmcli connection up Hotspot
```

Reboot to verify:

```bash
sudo reboot
# After reboot:
nmcli connection show --active
```

**Pi's IP on this network:** `10.42.0.1`
**Connect via:** `http://10.42.0.1:8080/` or `http://raspberrypi.local:8080/` (if avahi-daemon is running)

---

### Option C — `hostapd` + `dnsmasq` *(fallback for Raspberry Pi OS Bullseye and older)*

Use this method only if the OS pre-dates Bookworm or NetworkManager is not available.

#### C.1 Install packages

```bash
sudo apt update
sudo apt install -y hostapd dnsmasq
sudo systemctl stop hostapd dnsmasq
```

#### C.2 Assign a static IP to `wlan0`

Append the following to `/etc/dhcpcd.conf`:

```
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
```

#### C.3 Configure DHCP server (dnsmasq)

Back up the default config and create a new one:

```bash
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
sudo nano /etc/dnsmasq.conf
```

Paste the following:

```
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/orloy.local/192.168.4.1
```

The last line makes `orloy.local` resolve to the Pi for every DHCP client, so the hostname can be used instead of the raw IP.

#### C.4 Configure the access point (hostapd)

Create `/etc/hostapd/hostapd.conf`:

```
interface=wlan0
driver=nl80211
ssid=Orloy
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=orloy1234
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
```

Tell hostapd where the config file is — edit `/etc/default/hostapd` and set:

```
DAEMON_CONF="/etc/hostapd/hostapd.conf"
```

#### C.5 Enable services and reboot

```bash
sudo systemctl unmask hostapd
sudo systemctl enable hostapd dnsmasq
sudo reboot
```

Verify after reboot:

```bash
sudo systemctl status hostapd
sudo systemctl status dnsmasq
```

**Pi's IP on this network:** `192.168.4.1`
**Connect via:** `http://192.168.4.1:8080/` or `http://orloy.local:8080/` (resolved by dnsmasq for all DHCP clients)

---

### Troubleshooting the access point

**Hotspot exists but wlan0 is disconnected (`nmcli device status` shows `wlan0 disconnected`):**
```bash
sudo nmcli connection up Orloy
```

**Error: `802.1X supplicant took too long to authenticate`** — the connection is misconfigured as a client instead of an AP.  Delete and recreate it:
```bash
sudo nmcli connection delete Orloy
sudo nmcli device wifi hotspot ifname wlan0 ssid Orloy password orloy1234
sudo nmcli connection modify Hotspot 802-11-wireless.band bg 802-11-wireless.channel 6
sudo nmcli connection modify Hotspot connection.autoconnect yes connection.id Orloy
```

**Network not visible on iPhone (band/channel unset):**
```bash
nmcli connection show Orloy | grep -E "mode|band|channel"
```
If `band` is `--` and `channel` is `0`, force 2.4 GHz:
```bash
sudo nmcli connection modify Orloy 802-11-wireless.band bg 802-11-wireless.channel 6
sudo nmcli connection down Orloy && sudo nmcli connection up Orloy
```

---

### Connecting from a phone or laptop

1. Open **Wi-Fi settings** and select the network **Orloy**.
2. Enter the password: `orloy1234`
3. Open a browser and use the URL for your AP setup method:

| AP setup | IP-based URL | Hostname-based URL |
|---|---|---|
| Option A / B (NetworkManager) | `http://10.42.0.1:8080/` | `http://raspberrypi.local:8080/` ¹ |
| Option C (hostapd/dnsmasq) | `http://192.168.4.1:8080/` | `http://orloy.local:8080/` ² |

¹ Requires avahi-daemon on the Pi (pre-installed on Raspberry Pi OS with Desktop).  Windows clients also need the Bonjour service.
² Resolved by dnsmasq for all DHCP clients automatically; no extra software needed.

> **Note:** The Orloy network has no internet access — it only connects your device to the Pi.  Some phones show a "no internet" warning and may silently switch to mobile data.  If the page does not load, check that your device stayed on the Orloy network.
>
> **iPhone specifically:** when iOS shows the *"Use Without Internet?"* prompt after joining Orloy, tap **Use Without Internet** — otherwise iOS will drop the connection silently and fall back to mobile data.

---

## Raspberry Pi OS setup

### 1. Install OS dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
```

> `hostapd` and `dnsmasq` are only needed for the Option C fallback AP setup — see the [Wi-Fi access point setup](#wi-fi-access-point-setup) section above.

### 2. Add the `david` user to the `gpio` group

```bash
sudo usermod -aG gpio david
```

Log out and back in (or reboot) for group changes to take effect.

### 3. Deploy the application

```bash
# Clone / copy the project to the Pi
scp -r . david@raspberrypi.local:/home/david/Projects/orloy_app

# On the Pi:
cd /home/david/Projects/orloy_app
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 5. Create the log file with correct permissions

```bash
sudo touch /var/log/orloy_app.log
sudo chown david:david /var/log/orloy_app.log
```

### 6. Allow the `david` user to call `shutdown` without a password

```bash
sudo visudo
```

Add this line at the end:

```
david ALL=(ALL) NOPASSWD: /sbin/shutdown
```

### 7. Install and enable the systemd service

```bash
sudo cp /home/david/Projects/orloy_app/orloy_app.service /etc/systemd/system/
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
venv/bin/pip install -r requirements.txt
venv/bin/python -m pytest tests/ -v
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
│   ├── pir_handler.py        # PIR motion sensor + detection toggle
│   ├── audio_handler.py      # MP3 playback via pygame.mixer
│   ├── web_handler.py        # HTTP control panel (Flask/Werkzeug)
│   └── index.html            # Browser UI served by web_handler
├── tests/
│   ├── test_motor_controller.py
│   ├── test_mode_manager.py
│   ├── test_gpio_handler.py
│   ├── test_pir_handler.py
│   ├── test_audio_handler.py
│   └── test_web_handler.py
├── mp3/
│   ├── teams/                # MP3 team colour files (cerveni, modri, zeleni, zluti)
│   └── speech/               # MP3 speech files
├── main.py                   # Application entry point
├── orloy_app.service         # systemd unit file
└── requirements.txt
```
