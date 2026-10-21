# SPDX-License-Identifier: MIT
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from ab_modbus.application import Application, LocalHTTPServer
from ab_modbus.profiles import DEFAULT, Profiles
from ab_modbus.protocol import ProtocolError


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.app = Application(Path(self.directory.name))
        self.server = LocalHTTPServer(self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .05}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(1)
        self.app.simulator.stop(); self.directory.cleanup()

    def request(self, method="GET", path="/api/state", body=None, token=True, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        request_headers = {"Content-Type": "application/json"}
        if token: request_headers["Authorization"] = "Bearer " + self.app.token
        request_headers.update(headers or {})
        if isinstance(body, dict): body = json.dumps(body)
        connection.request(method, path, body, request_headers)
        response = connection.getresponse(); raw = response.read()
        result = (response.status, dict(response.getheaders()), raw)
        connection.close()
        return result

    def test_auth_required(self):
        self.assertEqual(self.request(token=False)[0], 401)
        self.assertEqual(self.request(headers={"Authorization": "Bearer wrong"})[0], 401)
        status, _, raw = self.request()
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(raw)["writes_enabled"])

    def test_origin_host_and_cross_site_blocked(self):
        for headers in ({"Origin": "https://attacker.example"}, {"Host": "evil.local"}, {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.request(headers=headers)[0], 403)
        self.assertEqual(self.request(headers={"Origin": self.server.origin})[0], 200)

    def test_security_headers_and_assets(self):
        for path in ("/", "/app.js", "/style.css", "/favicon.svg"):
            status, headers, raw = self.request(path=path, token=False)
            self.assertEqual(status, 200)
            self.assertGreater(len(raw), 0)
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertNotIn("Access-Control-Allow-Origin", headers)
            self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.request(path="/../profiles.json")[0], 404)

    def test_simulator_and_read_api(self):
        status, _, _ = self.request("POST", "/api/simulator/start", {"port": 0, "unit": 1})
        self.assertEqual(status, 400)  # La UI no admite puertos privilegiados ni 0.
        self.app.simulator.start(0)
        profile = dict(DEFAULT, port=self.app.simulator.port)
        status, _, raw = self.request("POST", "/api/read", {"profile": profile, "allow_lan": False})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["values"][0], 230)
        profile["function"] = 6
        self.assertEqual(self.request("POST", "/api/read", {"profile": profile, "allow_lan": False})[0], 400)

    def test_mutations_require_auth_and_json(self):
        self.assertEqual(self.request("POST", "/api/monitor/clear", {}, token=False)[0], 401)
        self.assertEqual(self.request("POST", "/api/monitor/clear", "{}", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/monitor/clear", "{")[0], 400)
        self.assertEqual(self.request("POST", "/api/monitor/clear", "[]")[0], 400)
        self.assertEqual(self.request("POST", "/api/monitor/clear", "x" * 65537)[0], 413)
        self.assertEqual(self.request("POST", "/api/write", {})[0], 400)

    def test_memory_api_is_local(self):
        self.app.simulator.start(0)
        self.assertEqual(self.request("POST", "/api/simulator/memory", {"function": 3, "address": 0, "value": 234})[0], 200)
        self.assertEqual(self.app.client.read(port=self.app.simulator.port, count=1)["values"], [234])
        self.assertEqual(self.request("POST", "/api/simulator/memory", {"function": 1, "address": 0, "value": 2})[0], 400)

    def test_profile_roundtrip_and_atomic_invalid_rejection(self):
        doc = {"schema": 1, "profiles": [dict(DEFAULT, name="Prueba á", host="192.168.1.10")]}
        self.app.profiles.replace(doc)
        self.assertEqual(Profiles(Path(self.directory.name)).document(), doc)
        invalid = {"schema": 1, "profiles": [dict(DEFAULT, allow_lan=True)]}
        with self.assertRaises(ProtocolError): self.app.profiles.replace(invalid)
        self.assertEqual(Profiles(Path(self.directory.name)).document(), doc)

    def test_profile_limits(self):
        cases = [{"schema": 2, "profiles": [DEFAULT]}, {"schema": True, "profiles": [DEFAULT]},
                 {"schema": 1, "profiles": []}, {"schema": 1, "profiles": [DEFAULT] * 51},
                 {"schema": 1, "profiles": [DEFAULT, dict(DEFAULT, name="LABORATORIO LOCAL")]},
                 {"schema": 1, "profiles": [dict(DEFAULT, host="8.8.8.8")]},
                 {"schema": 1, "profiles": [dict(DEFAULT, name="\n")]},
                 {"schema": 1, "profiles": [dict(DEFAULT, function=23)]}]
        for doc in cases:
            with self.subTest(doc=doc), self.assertRaises(ProtocolError): self.app.profiles.replace(doc)

    def test_secrets_not_exported(self):
        encoded = json.dumps(self.app.state())
        self.assertNotIn(self.app.token, encoded)
        self.assertNotIn("allow_lan", encoded)
