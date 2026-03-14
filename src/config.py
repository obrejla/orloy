import os

# GPIO pin assignments
# Motor driver (e.g. L298N IN1/IN2)
MOTOR_FORWARD_PIN = 24
MOTOR_BACKWARD_PIN = 25

# Input buttons (active-low with internal pull-up)
BUTTON_RANDOM_PIN = 17
BUTTON_MANUAL_PIN = 27
BUTTON_GEARBOX_PIN = 22
BUTTON_SHUTDOWN_PIN = 23

# Output signal driven HIGH while gearbox button is held
GEARBOX_OUTPUT_PIN = 5

# PIR motion sensor
PIR_SENSOR_PIN = 12
BUTTON_PIR_TOGGLE_PIN = 16
PIR_LED_PIN = 20

# How long the shutdown button must be held (seconds)
SHUTDOWN_HOLD_TIME = 3.0

# Web control panel
WEB_HOST = "0.0.0.0"           # bind on all interfaces
WEB_PORT = 8080
WEB_AP_IP_NM      = "10.42.0.1"    # NetworkManager hotspot (Options A & B)
WEB_AP_IP_HOSTAPD = "192.168.4.1"  # hostapd/dnsmasq (Option C)

# Random mode timing bounds
RANDOM_MOVE_MIN_SEC = 5.0
RANDOM_MOVE_MAX_SEC = 20.0
RANDOM_PAUSE_MIN_SEC = 60.0    # 1 minute
RANDOM_PAUSE_MAX_SEC = 600.0   # 10 minutes

# Audio tracks directories (relative to this file)
AUDIO_TEAMS_DIR  = os.path.join(os.path.dirname(__file__), "..", "mp3", "teams")
AUDIO_SPEECH_DIR = os.path.join(os.path.dirname(__file__), "..", "mp3", "speech")
