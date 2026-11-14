#!/usr/bin/env python3
"""Servidor local del frontend y disparador del pipeline bajo demanda."""

import json
import os
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(ROOT, "output")
STATE_LOCK = threading.Lock()
STATE = {
    "running": False,
    "mode": "firms" if os.environ.get("USE_SYNTHETIC_DATA", "true").lower() != "true" else "synthetic",
    "error": None,
}


def generate_data(mode):
    command = [sys.executable, "pipeline_incendios_nasa.py"]
    if mode == "synthetic":
        command.append("--offline")
    else:
        command.extend(["--key", os.environ["FIRMS_MAP_KEY"]])

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout[-1200:].strip() or "Falló el pipeline")
    if "No se registraron focos térmicos" in result.stdout:
        raise RuntimeError("NASA FIRMS no devolvió detecciones para el área y período consultados.")


def run_job(mode):
    try:
        generate_data(mode)
        with STATE_LOCK:
            STATE["mode"] = mode
            STATE["error"] = None
    except Exception as exc:  # El error se devuelve al panel de estado del frontend.
        with STATE_LOCK:
            STATE["error"] = str(exc)
    finally:
        with STATE_LOCK:
            STATE["running"] = False


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT, **kwargs)

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/status":
            with STATE_LOCK:
                snapshot = dict(STATE)
            return self._send_json(200, snapshot)
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/run":
            return self._send_json(404, {"error": "Ruta no encontrada"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1024:
                return self._send_json(413, {"error": "Solicitud demasiado grande"})
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send_json(400, {"error": "JSON inválido"})

        mode = payload.get("mode")
        if mode not in ("synthetic", "firms"):
            return self._send_json(400, {"error": "Modo inválido"})
        if mode == "firms" and not os.environ.get("FIRMS_MAP_KEY"):
            return self._send_json(400, {"error": "Configura FIRMS_MAP_KEY en Docker para consultar datos reales."})

        with STATE_LOCK:
            if STATE["running"]:
                return self._send_json(409, {"error": "Ya hay un análisis en curso."})
            STATE["running"] = True
            STATE["error"] = None

        threading.Thread(target=run_job, args=(mode,), daemon=True).start()
        return self._send_json(202, {"status": "started", "mode": mode})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), AppHandler)
    print("Servidor AURA-FIRE disponible en http://localhost:8080", flush=True)
    server.serve_forever()
