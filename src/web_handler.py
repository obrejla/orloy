"""
Web (HTTP) interface – Orloy control panel served over Wi-Fi.

Starts a lightweight Werkzeug server in a background daemon thread.
Open the control panel at:

    http://<Pi's WiFi IP>:<WEB_PORT>/

REST API:
    GET  /api/status          – current mode and pir_enabled as JSON
    POST /api/toggle_random   – toggle random mode
    POST /api/toggle_manual   – toggle manual mode
    POST /api/gearbox/on      – drive gearbox output HIGH
    POST /api/gearbox/off     – drive gearbox output LOW
    POST /api/pir/toggle      – toggle PIR motion detection on/off
    POST /api/shutdown        – trigger OS shutdown
    GET  /api/audio/tracks    – list available MP3 filenames
    POST /api/audio/play      – play a track  {"filename": "cerveni.mp3"}
    POST /api/audio/stop      – stop playback
"""

import logging
import subprocess
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file

from src.config import WEB_AP_IP_HOSTAPD, WEB_AP_IP_NM, WEB_HOST, WEB_PORT

logger = logging.getLogger(__name__)

_INDEX_HTML = Path(__file__).parent / "index.html"


# ---------------------------------------------------------------------------
# WebHandler
# ---------------------------------------------------------------------------


class WebHandler:
    """
    Serves the Orloy control panel over HTTP.

    Starts a Werkzeug server in a background daemon thread.  All four
    control actions (random, manual, gearbox, shutdown) are exposed as
    POST endpoints so the browser-based UI can trigger them.

    Args:
        mode_manager:    ModeManager instance.
        gearbox_output:  gpiozero OutputDevice (or compatible) for the
                         gearbox pin.  Pass None to skip.
        host:            Address to bind (default "0.0.0.0" – all interfaces).
        port:            TCP port (default 8080).
        _start:          Internal flag; set False in tests to skip launching
                         the background server thread.
    """

    def __init__(
        self,
        mode_manager,
        gearbox_output=None,
        pir_handler=None,
        audio_handler=None,
        host: str = WEB_HOST,
        port: int = WEB_PORT,
        _start: bool = True,
    ) -> None:
        self._mode_manager = mode_manager
        self._gearbox_output = gearbox_output
        self._pir_handler = pir_handler
        self._audio_handler = audio_handler
        self._host = host
        self._port = port
        self._server = None

        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        self._app = Flask(__name__)
        self._register_routes()

        if _start:
            self._thread = threading.Thread(
                target=self._run_server, daemon=True, name="web-server"
            )
            self._thread.start()
            logger.info(
                "Web handler ready on port %d – "
                "NetworkManager AP: http://%s:%d/ or http://raspberrypi.local:%d/ | "
                "hostapd AP: http://%s:%d/ or http://orloy.local:%d/",
                port,
                WEB_AP_IP_NM, port, port,
                WEB_AP_IP_HOSTAPD, port, port,
            )

    # ------------------------------------------------------------------ #
    # Route registration                                                   #
    # ------------------------------------------------------------------ #

    def _register_routes(self) -> None:
        app = self._app

        @app.route("/")
        def index():
            return send_file(_INDEX_HTML)

        @app.route("/api/status")
        def status():
            payload = {"mode": self._mode_manager.mode.name}
            if self._pir_handler is not None:
                payload["pir_enabled"] = self._pir_handler.enabled
            if self._audio_handler is not None:
                payload["audio_playing"] = self._audio_handler.is_playing
            return jsonify(payload)

        @app.route("/api/toggle_random", methods=["POST"])
        def toggle_random():
            logger.info("Web: toggle_random")
            self._mode_manager.toggle_random()
            return jsonify({"mode": self._mode_manager.mode.name})

        @app.route("/api/toggle_manual", methods=["POST"])
        def toggle_manual():
            logger.info("Web: toggle_manual")
            self._mode_manager.toggle_manual()
            return jsonify({"mode": self._mode_manager.mode.name})

        @app.route("/api/gearbox/on", methods=["POST"])
        def gearbox_on():
            logger.info("Web: gearbox on")
            if self._gearbox_output is not None:
                self._gearbox_output.on()
            return jsonify({"gearbox": "on"})

        @app.route("/api/gearbox/off", methods=["POST"])
        def gearbox_off():
            logger.info("Web: gearbox off")
            if self._gearbox_output is not None:
                self._gearbox_output.off()
            return jsonify({"gearbox": "off"})

        @app.route("/api/pir/toggle", methods=["POST"])
        def pir_toggle():
            logger.info("Web: PIR toggle")
            new_state = self._pir_handler.toggle() if self._pir_handler is not None else None
            return jsonify({"pir_enabled": new_state})

        @app.route("/api/shutdown", methods=["POST"])
        def shutdown():
            logger.info("Web: shutdown requested")
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
            return jsonify({"shutdown": "triggered"})

        @app.route("/api/audio/tracks")
        def audio_tracks():
            tracks = self._audio_handler.list_tracks() if self._audio_handler is not None else []
            return jsonify({"tracks": tracks})

        @app.route("/api/audio/play", methods=["POST"])
        def audio_play():
            if self._audio_handler is None:
                return jsonify({"error": "no audio handler"}), 503
            body = request.get_json(silent=True) or {}
            filename = body.get("filename", "")
            try:
                self._audio_handler.play(filename)
                return jsonify({"playing": filename})
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

        @app.route("/api/audio/stop", methods=["POST"])
        def audio_stop():
            if self._audio_handler is not None:
                self._audio_handler.stop()
            return jsonify({"stopped": True})

    # ------------------------------------------------------------------ #
    # Server thread                                                        #
    # ------------------------------------------------------------------ #

    def _run_server(self) -> None:
        from werkzeug.serving import make_server

        self._server = make_server(self._host, self._port, self._app)
        self._server.serve_forever()

    # ------------------------------------------------------------------ #
    # Cleanup                                                              #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
        logger.info("Web handler closed")
