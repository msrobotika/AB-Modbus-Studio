# SPDX-License-Identifier: MIT
from contextlib import contextmanager
import socket
import threading
import time
import unittest
from unittest.mock import patch

from ab_modbus.client import ReadClient
from ab_modbus.monitor import Monitor
from ab_modbus.protocol import Frame, ModbusException, ProtocolError, decode_frame, read_request
from ab_modbus.server import Simulator
from ab_modbus.transport import receive_adu, safe_target


@contextmanager
def fake_peer(reply):
    errors = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); listener.listen(1); listener.settimeout(3)
        port = listener.getsockname()[1]
        def run():
            try:
                sock, _ = listener.accept()
                with sock:
                    request = decode_frame(receive_adu(sock, time.monotonic() + 2))
                    reply(sock, request)
            except (OSError, ProtocolError):
                pass
            except Exception as error:
                errors.append(error)
        worker = threading.Thread(target=run, daemon=True); worker.start()
        try:
            yield port
        finally:
            worker.join(3)
            if worker.is_alive():
                raise AssertionError("El servidor de prueba no terminó")
            if errors:
                raise errors[0]


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulator(); self.sim.start(0)

    def tearDown(self):
        self.sim.stop()

    def test_all_functions_over_tcp(self):
        client = ReadClient()
        self.assertEqual(client.read(port=self.sim.port)["values"], [230, 1500, 42, 2026, 100, 0, 65535, 1234])
        self.assertEqual(client.read(port=self.sim.port, function=1)["values"], [1, 0, 0, 1, 0, 0, 1, 0])
        self.assertEqual(client.read(port=self.sim.port, function=2)["values"], [0, 1] * 4)
        self.assertEqual(client.read(port=self.sim.port, function=4)["values"], list(range(1000, 1008)))

    def test_large_reads_and_local_edit(self):
        client = ReadClient()
        self.sim.memory.edit_local(3, 12, 321)
        self.assertEqual(client.read(port=self.sim.port, address=12, count=1)["values"], [321])
        self.assertEqual(len(client.read(port=self.sim.port, function=1, count=2000)["values"]), 2000)
        self.assertEqual(len(client.read(port=self.sim.port, count=125)["values"]), 125)

    def test_wrong_unit_and_unmapped_address(self):
        for kwargs, code in (({"unit": 2}, 11), ({"address": 4096}, 2)):
            with self.assertRaises(ModbusException) as error:
                ReadClient().read(port=self.sim.port, **kwargs)
            self.assertEqual(error.exception.code, code)

    def test_fragmented_response(self):
        def reply(sock, request):
            for byte in Frame(request.transaction, request.unit, bytes.fromhex("0302002a")).encode():
                sock.sendall(bytes((byte,)))
        with fake_peer(reply) as port:
            self.assertEqual(ReadClient().read(port=port, count=1)["values"], [42])

    def test_response_correlation(self):
        for transaction_delta, unit_delta in ((1, 0), (0, 1)):
            def reply(sock, request):
                sock.sendall(Frame(request.transaction + transaction_delta, request.unit + unit_delta, b"\x03\x02\x00\x01").encode())
            with fake_peer(reply) as port, self.assertRaises(ProtocolError):
                ReadClient().read(port=port, count=1)

    def test_truncated_response(self):
        with fake_peer(lambda sock, _: sock.sendall(bytes.fromhex("00010000000501030200"))) as port:
            with self.assertRaises(ProtocolError):
                ReadClient().read(port=port, count=1)

    def test_total_deadline_defeats_slow_drip(self):
        def reply(sock, request):
            for byte in Frame(request.transaction, request.unit, b"\x03\x02\x00\x01").encode():
                sock.sendall(bytes((byte,))); time.sleep(0.04)
        with fake_peer(reply) as port:
            start = time.monotonic()
            with self.assertRaises(TimeoutError):
                ReadClient().read(port=port, count=1, timeout_ms=100)
            self.assertLess(time.monotonic() - start, 0.5)

    def test_coalesced_requests_and_fragmented_request(self):
        first = Frame(8, 1, read_request(3, 0, 1)).encode()
        second = Frame(9, 1, read_request(4, 0, 1)).encode()
        with socket.create_connection(("127.0.0.1", self.sim.port)) as sock:
            sock.sendall(first[:3]); sock.sendall(first[3:] + second)
            one = decode_frame(receive_adu(sock, time.monotonic() + 1))
            two = decode_frame(receive_adu(sock, time.monotonic() + 1))
        self.assertEqual((one.transaction, two.transaction), (8, 9))
        self.assertEqual(one.pdu, bytes.fromhex("030200e6"))
        self.assertEqual(two.pdu, bytes.fromhex("040203e8"))

    def test_writes_rejected_over_wire(self):
        with socket.create_connection(("127.0.0.1", self.sim.port)) as sock:
            sock.sendall(Frame(4, 1, bytes.fromhex("0600001234")).encode())
            self.assertEqual(decode_frame(receive_adu(sock, time.monotonic() + 1)).pdu, b"\x86\x01")
        self.assertEqual(ReadClient().read(port=self.sim.port, count=1)["values"], [230])

    def test_network_policy(self):
        self.assertEqual(safe_target("localhost"), "127.0.0.1")
        for ip in ("10.0.0.1", "172.16.1.1", "192.168.0.1"):
            with self.assertRaises(ProtocolError): safe_target(ip)
            self.assertEqual(safe_target(ip, True), ip)
        for host in ("8.8.8.8", "0.0.0.0", "169.254.169.254", "100.64.0.1", "example.com", "::1", "224.0.0.1"):
            with self.assertRaises(ProtocolError): safe_target(host, True)

    def test_write_never_opens_socket(self):
        with patch("ab_modbus.client.socket.socket") as socket_mock:
            for function in (5, 6, 15, 16, 22, 23):
                with self.assertRaises(ProtocolError): ReadClient().read(function=function)
            socket_mock.assert_not_called()

    def test_sequence_rollover(self):
        client = ReadClient(); client._transaction = 65535
        self.assertEqual(client.read(port=self.sim.port, count=1)["transaction"], 0)

    def test_simulator_bind_is_local(self):
        self.assertEqual(self.sim._server.server_address[0], "127.0.0.1")

    def test_stop_closes_existing_connections(self):
        with socket.create_connection(("127.0.0.1", self.sim.port), timeout=1) as sock:
            sock.sendall(Frame(1, 1, read_request(3, 0, 1)).encode())
            receive_adu(sock, time.monotonic() + 1)
            self.sim.stop()
            self.assertEqual(sock.recv(1), b"")
        self.sim.start(0)
        self.assertEqual(ReadClient().read(port=self.sim.port, count=1)["values"], [230])

    def test_malformed_mbap_closes_connection(self):
        with socket.create_connection(("127.0.0.1", self.sim.port), timeout=1) as sock:
            sock.sendall(bytes.fromhex("000100010006010300000001"))
            try:
                data = sock.recv(1)
            except ConnectionResetError:
                data = b""
            self.assertEqual(data, b"")
        self.assertEqual(ReadClient().read(port=self.sim.port, count=1)["values"], [230])

    def test_concurrent_read_is_rejected(self):
        client = ReadClient(); client._lock.acquire()
        try:
            with self.assertRaises(ProtocolError): client.read(port=self.sim.port)
        finally: client._lock.release()

    def test_monitor_is_bounded(self):
        monitor = Monitor(3)
        for _ in range(10): monitor.add("cliente", "TX", b"\x00")
        self.assertEqual([e["id"] for e in monitor.snapshot()], [8, 9, 10])
        snapshot = monitor.snapshot(); snapshot[0]["hex"] = "bad"
        self.assertEqual(monitor.snapshot()[0]["hex"], "00")
