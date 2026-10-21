# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
"""Aplicación local; API autenticada con secreto efímero y sin CORS."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading

from . import __version__
from .client import ReadClient
from .monitor import Monitor
from .profiles import Profiles, validate_profile
from .protocol import ProtocolError, integer
from .server import LimitedThreads, Simulator


class Application:
    def __init__(self, directory: Path):
        self.monitor = Monitor()
        self.client = ReadClient(self.monitor)
        self.simulator = Simulator(self.monitor)
        self.profiles = Profiles(directory)
        self.token = secrets.token_urlsafe(32)
        self.shutdown = lambda: None

    def state(self):
        return dict(version=__version__, simulator_port=self.simulator.port,
                    simulator_unit=self.simulator.unit, events=self.monitor.snapshot(),
                    profiles=self.profiles.document(), writes_enabled=False)

    def action(self, path, body):
        if type(body) is not dict:
            raise ProtocolError("Se requiere un objeto JSON")
        if path == "/api/read":
            if set(body) != {"profile", "allow_lan"} or type(body["allow_lan"]) is not bool:
                raise ProtocolError("Lectura: perfil y autorización de red explícitos requeridos")
            profile = validate_profile(body["profile"])
            return self.client.read(**{k: v for k, v in profile.items() if k != "name"},
                                    allow_lan=body["allow_lan"])
        if path == "/api/simulator/start":
            if set(body) != {"port", "unit"}:
                raise ProtocolError("Se requieren puerto y unidad")
            integer(body["port"], 1024, 65535, "Puerto del simulador")
            self.simulator.start(**body)
            return {"port": self.simulator.port}
        if path == "/api/simulator/stop" and not body:
            self.simulator.stop()
            return {"ok": True}
        if path == "/api/simulator/memory" and set(body) == {"function", "address", "value"}:
            self.simulator.memory.edit_local(**body)
            return {"ok": True}
        if path == "/api/profiles":
            self.profiles.replace(body)
            return self.profiles.document()
        if path == "/api/monitor/clear" and not body:
            self.monitor.clear()
            return {"ok": True}
        if path == "/api/shutdown" and not body:
            return {"ok": True}
        raise ProtocolError("Operación no disponible")


class LocalHTTPServer(LimitedThreads, ThreadingHTTPServer):
    allow_reuse_address = False

    def __init__(self, application, port=0):
        self.application = application
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(("127.0.0.1", port), Handler)
        self.authority = f"127.0.0.1:{self.server_port}"
        self.origin = f"http://{self.authority}"
        application.shutdown = self.shutdown


class Handler(BaseHTTPRequestHandler):
    server_version = "ABModbus/0.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *args):
        # Evita registrar secretos o perfiles en la consola.
        pass

    def respond(self, status, payload, content_type="application/json; charset=utf-8"):
        if not isinstance(payload, bytes):
            payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)

    def guard(self, auth=False):
        if self.headers.get_all("Host", []) != [self.server.authority]:
            self.respond(403, {"error": "Host no autorizado"})
            return False
        origins = self.headers.get_all("Origin", [])
        if origins and origins != [self.server.origin]:
            self.respond(403, {"error": "Origen no autorizado"})
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.respond(403, {"error": "Petición entre sitios bloqueada"})
            return False
        expected = "Bearer " + self.server.application.token
        if auth and not secrets.compare_digest(self.headers.get("Authorization", "").encode("utf-8"), expected.encode("ascii")):
            self.respond(401, {"error": "Sesión no autorizada. Abre la URL de inicio completa."})
            return False
        return True

    def do_GET(self):
        if not self.guard(auth=self.path.startswith("/api/")):
            return
        if self.path == "/api/state":
            self.respond(200, self.server.application.state())
            return
        assets = {"/": ("index.html", "text/html; charset=utf-8"),
                  "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                  "/style.css": ("style.css", "text/css; charset=utf-8"),
                  "/scada.html": ("scada.html", "text/html; charset=utf-8"),
                  "/scada.js": ("scada.js", "text/javascript; charset=utf-8"),
                  "/scada.css": ("scada.css", "text/css; charset=utf-8"),
                  "/favicon.svg": ("favicon.svg", "image/svg+xml")}
        if self.path in assets:
            filename, content_type = assets[self.path]
            self.respond(200, (Path(__file__).parent / "web" / filename).read_bytes(), content_type)
        else:
            self.respond(404, {"error": "Ruta no disponible"})

    def do_POST(self):
        if not self.guard(auth=True):
            return
        if self.headers.get_content_type() != "application/json":
            self.respond(415, {"error": "Se requiere application/json"})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
            self.respond(400, {"error": "Longitud de petición requerida"})
            return
        try:
            length = int(lengths[0])
            if not 1 <= length <= 65536:
                self.respond(413, {"error": "Petición fuera del límite de 64 KiB"})
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ProtocolError("Cuerpo de petición incompleto")
            body = json.loads(raw)
            result = self.server.application.action(self.path, body)
            self.respond(200, result)
            if self.path == "/api/shutdown":
                self.wfile.flush()
                threading.Thread(target=self.server.application.shutdown, daemon=True).start()
        except (ProtocolError, ValueError, TypeError, UnicodeError, OSError, RecursionError) as error:
            self.respond(400, {"error": str(error)[:400]})
