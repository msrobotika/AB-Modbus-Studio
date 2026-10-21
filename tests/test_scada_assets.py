# SPDX-License-Identifier: MIT
"""Regresión del módulo SCADA. No conecta a PLC de terceros."""
import http.client
from pathlib import Path
import tempfile
import threading
import unittest

from ab_modbus.application import Application, LocalHTTPServer


class ScadaAssetsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="abmodbus-scada-tests-")
        self.app = Application(Path(self.tmp.name))
        self.http = LocalHTTPServer(self.app)
        self.thread = threading.Thread(
            target=self.http.serve_forever, kwargs={"poll_interval": .05}, daemon=True
        )
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
        self.app.simulator.stop()
        self.tmp.cleanup()

    def get(self, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.http.server_port, timeout=3)
        conn.request("GET", path, headers=headers or {})
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return result

    def test_static_scada_assets_and_csp(self):
        required = {
            "/scada.html": (b"AB-Modbus", "text/html"),
            "/scada.css": (b".sc-kpis", "text/css"),
            "/scada.js": (b"/api/read", "text/javascript"),
        }
        for path, (needle, mime) in required.items():
            with self.subTest(path=path):
                status, headers, body = self.get(path)
                self.assertEqual(status, 200)
                self.assertIn(mime, headers["Content-Type"])
                self.assertIn(needle, body)
                self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_scada_uses_auth_but_never_enables_writes(self):
        _, _, app_js = self.get("/scada.js")
        self.assertIn(b'"/api/read"', app_js)
        self.assertNotIn(b'"/api/write"', app_js)
        status, _, _ = self.get("/api/state")
        self.assertEqual(status, 401)
        status, _, _ = self.get("/scada.html", {"Origin": "https://other.example"})
        self.assertEqual(status, 403)
        self.assertFalse(self.app.state()["writes_enabled"])


if __name__ == "__main__":
    unittest.main()
