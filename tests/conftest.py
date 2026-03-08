"""
Stub out hardware-dependent packages before any test module is imported.

bluedot pulls in `dbus` at import time, which is unavailable in CI.
Inserting a MagicMock into sys.modules before the first import prevents the
real package from loading while still letting tests patch specific attributes.
"""
import sys
from unittest.mock import MagicMock

for _mod in ("bluedot", "bluedot.dot", "bluedot.btcomm", "bluedot.utils"):
    sys.modules.setdefault(_mod, MagicMock())
