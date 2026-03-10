"""
Web (HTTP) interface – Orloy control panel served over Wi-Fi.

Starts a lightweight Werkzeug server in a background daemon thread.
Open the control panel at:

    http://<Pi's WiFi IP>:<WEB_PORT>/

REST API:
    GET  /api/status          – current mode as JSON
    POST /api/toggle_random   – toggle random mode
    POST /api/toggle_manual   – toggle manual mode
    POST /api/gearbox/on      – drive gearbox output HIGH
    POST /api/gearbox/off     – drive gearbox output LOW
    POST /api/shutdown        – trigger OS shutdown
"""

import logging
import subprocess
import threading

from flask import Flask, Response, jsonify

from src.config import WEB_AP_IP, WEB_HOST, WEB_PORT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedded HTML/CSS/JS control panel
# ---------------------------------------------------------------------------

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Orloy</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0d0d1a;
      color: #d0d0e8;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1rem 3rem;
      gap: 1.5rem;
    }

    h1 {
      font-size: 2.8rem;
      letter-spacing: 0.4em;
      color: #c0c0ff;
      text-shadow: 0 0 20px rgba(160,160,255,0.4);
    }

    #status-bar {
      padding: 0.5rem 1.8rem;
      border-radius: 999px;
      font-size: 0.95rem;
      font-weight: 700;
      letter-spacing: 0.18em;
      border: 2px solid #333;
      color: #666;
      transition: all 0.3s;
    }
    #status-bar.IDLE    { border-color: #444; color: #888; }
    #status-bar.RANDOM  { border-color: #4cc9f0; color: #4cc9f0;
                          box-shadow: 0 0 12px rgba(76,201,240,0.3); }
    #status-bar.MANUAL  { border-color: #f72585; color: #f72585;
                          box-shadow: 0 0 12px rgba(247,37,133,0.3); }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      width: 100%;
      max-width: 400px;
    }

    .btn {
      padding: 1.8rem 1rem;
      border-radius: 14px;
      border: 2px solid #333;
      background: #12122a;
      color: #c0c0e0;
      font-size: 1rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      cursor: pointer;
      user-select: none;
      -webkit-user-select: none;
      -webkit-tap-highlight-color: transparent;
      transition: transform 0.1s, background 0.2s, box-shadow 0.2s;
      touch-action: none;
    }
    .btn:active { transform: scale(0.95); }

    /* RANDOM */
    #btn-random { border-color: #4cc9f0; }
    #btn-random.active {
      background: #4cc9f0; color: #0d0d1a;
      box-shadow: 0 0 18px rgba(76,201,240,0.5);
    }

    /* MANUAL */
    #btn-manual { border-color: #f72585; }
    #btn-manual.active {
      background: #f72585; color: #fff;
      box-shadow: 0 0 18px rgba(247,37,133,0.5);
    }

    /* GEARBOX – full width */
    #btn-gearbox {
      grid-column: 1 / -1;
      border-color: #7209b7;
    }
    #btn-gearbox.pressing {
      background: #7209b7; color: #fff;
      box-shadow: 0 0 18px rgba(114,9,183,0.5);
    }

    /* SHUTDOWN – full width with progress bar */
    #btn-shutdown {
      grid-column: 1 / -1;
      border-color: #e63946;
      position: relative;
      overflow: hidden;
    }
    #btn-shutdown .progress {
      position: absolute;
      bottom: 0; left: 0;
      height: 4px;
      width: 0%;
      background: #e63946;
    }
    #btn-shutdown.holding .progress {
      width: 100%;
      transition: width var(--hold-ms) linear;
    }

    .error-toast {
      position: fixed;
      bottom: 1.5rem;
      left: 50%; transform: translateX(-50%);
      background: #e63946;
      color: #fff;
      padding: 0.6rem 1.4rem;
      border-radius: 999px;
      font-size: 0.85rem;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s;
    }
    .error-toast.show { opacity: 1; }
  </style>
</head>
<body>
  <h1>ORLOY</h1>
  <div id="status-bar" class="IDLE">IDLE</div>

  <div class="grid">
    <button class="btn" id="btn-random">RANDOM</button>
    <button class="btn" id="btn-manual">MANUAL</button>
    <button class="btn" id="btn-gearbox">GEARBOX</button>
    <button class="btn" id="btn-shutdown"
            style="--hold-ms: 3s;">
      SHUTDOWN (hold 3s)
      <div class="progress" id="shutdown-progress"></div>
    </button>
  </div>

  <div class="error-toast" id="toast">Connection error</div>

  <script>
    const SHUTDOWN_HOLD_MS = 3000;

    // ------------------------------------------------------------------ //
    // Status polling
    // ------------------------------------------------------------------ //
    function updateUI(data) {
      const mode = data.mode;
      const bar = document.getElementById('status-bar');
      bar.textContent = mode;
      bar.className = mode;
      document.getElementById('btn-random').classList.toggle('active', mode === 'RANDOM');
      document.getElementById('btn-manual').classList.toggle('active', mode === 'MANUAL');
    }

    function showError() {
      const t = document.getElementById('toast');
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2500);
    }

    async function apiPost(path) {
      try {
        const res = await fetch('/api' + path, { method: 'POST' });
        if (!res.ok) { showError(); return; }
        updateUI(await res.json());
      } catch (_) { showError(); }
    }

    async function pollStatus() {
      try {
        const res = await fetch('/api/status');
        if (res.ok) updateUI(await res.json());
      } catch (_) {}
    }

    setInterval(pollStatus, 2000);
    pollStatus();

    // ------------------------------------------------------------------ //
    // RANDOM / MANUAL – simple toggle on click
    // ------------------------------------------------------------------ //
    document.getElementById('btn-random').addEventListener('click', () => apiPost('/toggle_random'));
    document.getElementById('btn-manual').addEventListener('click', () => apiPost('/toggle_manual'));

    // ------------------------------------------------------------------ //
    // GEARBOX – HIGH while held, LOW on release
    // ------------------------------------------------------------------ //
    const gearboxBtn = document.getElementById('btn-gearbox');

    function gearboxPress() {
      gearboxBtn.classList.add('pressing');
      fetch('/api/gearbox/on', { method: 'POST' }).catch(() => {});
    }
    function gearboxRelease() {
      gearboxBtn.classList.remove('pressing');
      fetch('/api/gearbox/off', { method: 'POST' }).catch(() => {});
    }

    gearboxBtn.addEventListener('mousedown',  gearboxPress);
    gearboxBtn.addEventListener('mouseup',    gearboxRelease);
    gearboxBtn.addEventListener('mouseleave', gearboxRelease);
    gearboxBtn.addEventListener('touchstart', e => { e.preventDefault(); gearboxPress(); });
    gearboxBtn.addEventListener('touchend',   e => { e.preventDefault(); gearboxRelease(); });
    gearboxBtn.addEventListener('touchcancel',e => { e.preventDefault(); gearboxRelease(); });

    // ------------------------------------------------------------------ //
    // SHUTDOWN – hold for SHUTDOWN_HOLD_MS to trigger
    // ------------------------------------------------------------------ //
    const shutdownBtn  = document.getElementById('btn-shutdown');
    const progressBar  = document.getElementById('shutdown-progress');
    let shutdownTimer  = null;

    function shutdownHoldStart() {
      // reset bar width so transition restarts
      progressBar.style.transition = 'none';
      progressBar.style.width = '0%';
      void progressBar.offsetWidth;               // force reflow

      shutdownBtn.classList.add('holding');        // triggers CSS transition

      shutdownTimer = setTimeout(() => {
        shutdownBtn.classList.remove('holding');
        fetch('/api/shutdown', { method: 'POST' }).catch(() => {});
      }, SHUTDOWN_HOLD_MS);
    }

    function shutdownHoldCancel() {
      if (shutdownTimer) { clearTimeout(shutdownTimer); shutdownTimer = null; }
      shutdownBtn.classList.remove('holding');
      progressBar.style.transition = 'none';
      progressBar.style.width = '0%';
    }

    shutdownBtn.addEventListener('mousedown',  shutdownHoldStart);
    shutdownBtn.addEventListener('mouseup',    shutdownHoldCancel);
    shutdownBtn.addEventListener('mouseleave', shutdownHoldCancel);
    shutdownBtn.addEventListener('touchstart', e => { e.preventDefault(); shutdownHoldStart(); });
    shutdownBtn.addEventListener('touchend',   e => { e.preventDefault(); shutdownHoldCancel(); });
    shutdownBtn.addEventListener('touchcancel',e => { e.preventDefault(); shutdownHoldCancel(); });
  </script>
</body>
</html>
"""


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
        host: str = WEB_HOST,
        port: int = WEB_PORT,
        _start: bool = True,
    ) -> None:
        self._mode_manager = mode_manager
        self._gearbox_output = gearbox_output
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
                "Web handler ready – connect to the 'Orloy' Wi-Fi network and open "
                "http://%s:%d/ in a browser",
                WEB_AP_IP,
                port,
            )

    # ------------------------------------------------------------------ #
    # Route registration                                                   #
    # ------------------------------------------------------------------ #

    def _register_routes(self) -> None:
        app = self._app

        @app.route("/")
        def index():
            return Response(_HTML, mimetype="text/html")

        @app.route("/api/status")
        def status():
            return jsonify({"mode": self._mode_manager.mode.name})

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

        @app.route("/api/shutdown", methods=["POST"])
        def shutdown():
            logger.info("Web: shutdown requested")
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
            return jsonify({"shutdown": "triggered"})

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
