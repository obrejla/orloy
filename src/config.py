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

# How long the shutdown button must be held (seconds)
SHUTDOWN_HOLD_TIME = 3.0

# Web control panel
WEB_HOST = "0.0.0.0"   # bind on all interfaces
WEB_PORT = 8080
WEB_AP_IP = "192.168.4.1"   # static IP assigned to the Pi's access point

# Random mode timing bounds
RANDOM_MOVE_MIN_SEC = 5.0
RANDOM_MOVE_MAX_SEC = 20.0
RANDOM_PAUSE_MIN_SEC = 60.0    # 1 minute
RANDOM_PAUSE_MAX_SEC = 600.0   # 10 minutes
