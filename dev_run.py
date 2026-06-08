#!/usr/bin/env python3
"""
Dev-only launcher for running the app on a non-Pi host (e.g. macOS).

It substitutes a PWM-capable mock GPIO factory and a software audio driver so
the web UI and core logic can be exercised without Raspberry Pi hardware.  The
plain ``mock`` factory selected via ``GPIOZERO_PIN_FACTORY=mock`` cannot drive
the PWM motor pins, which is why this launcher exists.

    python dev_run.py                    # silent audio (no audio device needed)
    ORLOY_DEV_AUDIO=1 python dev_run.py  # real audio output (CoreAudio on macOS)

Then open http://localhost:8080/ .  This file is for local development only;
``main.py`` remains the production entry point on the Pi.
"""

import os
import sys

# The SDL audio driver must be chosen before src.audio_handler is imported
# (it pins the driver via os.environ.setdefault at import time).
if os.environ.get("ORLOY_DEV_AUDIO") == "1":
    os.environ.setdefault("SDL_AUDIODRIVER", "coreaudio")  # macOS real output
else:
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")  # no device required

from gpiozero import Device
from gpiozero.pins.mock import MockFactory, MockPWMPin

# MockPWMPin (unlike the default MockPin) supports the PWM used by the motor.
Device.pin_factory = MockFactory(pin_class=MockPWMPin)

from main import main  # noqa: E402  (must follow pin-factory / SDL setup above)

if __name__ == "__main__":
    sys.exit(main())
