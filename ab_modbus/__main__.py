# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import webbrowser

from . import __version__
from .application import Application, LocalHTTPServer
from .client import ReadClient
from .server import Simulator


def default_directory():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "MSRobotika" / "ABModbusStudio"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "ab-modbus-studio"


def self_test():
    """Ejercicio funcional del binario sin navegador ni hardware externo."""
    simulator = Simulator()
    try:
        simulator.start(port=0)
        client = ReadClient()
        expected = {1: [1, 0, 0, 1, 0, 0, 1, 0], 2: [0, 1, 0, 1, 0, 1, 0, 1],
                    3: [230, 1500, 42, 2026, 100, 0, 65535, 1234],
                    4: list(range(1000, 1008))}
        for function, values in expected.items():
            result = client.read(port=simulator.port, function=function)
            if result["values"] != values:
                raise RuntimeError(f"Autoprueba FC{function:02d} fallida")
        with tempfile.TemporaryDirectory() as directory:
            app = Application(Path(directory))
            with LocalHTTPServer(app) as http:
                if http.server_address[0] != "127.0.0.1":
                    raise RuntimeError("Interfaz fuera de loopback")
        print(json.dumps({"ok": True, "version": __version__, "functions": [1, 2, 3, 4]}))
    finally:
        simulator.stop()


def main():
    parser = argparse.ArgumentParser(description="AB-Modbus Studio · MS ROBOTIKA · solo lectura")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--self-test", action="store_true", help="Probar el motor contra el simulador local y salir")
    parser.add_argument("--no-browser", action="store_true", help="Mostrar URL sin abrir navegador")
    parser.add_argument("--port", type=int, default=0, help="Puerto web local (0: automático)")
    parser.add_argument("--data-dir", type=Path, default=default_directory(), help="Carpeta de perfiles")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not 0 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 0 y 65535")
    app = Application(args.data_dir)
    with LocalHTTPServer(app, args.port) as server:
        url = server.origin + "/#token=" + app.token
        print(f"AB-Modbus Studio {__version__} · MS ROBOTIKA\n{url}\nCtrl+C o «Cerrar aplicación» para terminar.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            pass
        finally:
            app.simulator.stop()


if __name__ == "__main__":
    main()
