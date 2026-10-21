# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
"""Simulador de laboratorio: memoria propia, sin pasarela a equipos reales."""
import socketserver
import threading
import time

from .monitor import Monitor
from .protocol import (Frame, ProtocolError, decode_frame, integer,
                       pack_values, validate_read)
from .transport import receive_adu, set_remaining


class LimitedThreads:
    """Limita hilos activos antes de crearlos, también para peticiones incompletas."""
    daemon_threads = True
    block_on_close = False

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Memory:
    SIZE = 4096

    def __init__(self):
        self._lock = threading.Lock()
        self._banks = {1: [int(i % 3 == 0) for i in range(self.SIZE)],
                       2: [i % 2 for i in range(self.SIZE)],
                       3: [i * 10 % 65536 for i in range(self.SIZE)],
                       4: [(1000 + i) % 65536 for i in range(self.SIZE)]}
        self._banks[3][:8] = [230, 1500, 42, 2026, 100, 0, 65535, 1234]

    def edit_local(self, function, address, value):
        validate_read(function, address, 1)
        integer(address, 0, self.SIZE - 1, "Dirección del simulador")
        integer(value, 0, 1 if function < 3 else 65535, "Valor del simulador")
        with self._lock:
            self._banks[function][address] = value

    def reply(self, pdu: bytes) -> bytes:
        function = pdu[0]
        if function not in (1, 2, 3, 4):
            return bytes((function | 0x80, 1))
        if len(pdu) != 5:
            return bytes((function | 0x80, 3))
        address = int.from_bytes(pdu[1:3], "big")
        count = int.from_bytes(pdu[3:5], "big")
        maximum = 2000 if function < 3 else 125
        if not 1 <= count <= maximum:
            return bytes((function | 0x80, 3))
        if address + count > self.SIZE:
            return bytes((function | 0x80, 2))
        with self._lock:
            return pack_values(function, self._banks[function][address:address + count])


class _TCPServer(LimitedThreads, socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = False

    def __init__(self, address, owner):
        self.owner = owner
        self.slots = threading.BoundedSemaphore(16)
        self.connections = set()
        self.connections_lock = threading.Lock()
        super().__init__(address, _Handler)

    def get_request(self):
        request, address = super().get_request()
        with self.connections_lock:
            self.connections.add(request)
        return request, address

    def shutdown_request(self, request):
        with self.connections_lock:
            self.connections.discard(request)
        super().shutdown_request(request)

    def close_connections(self):
        import socket
        with self.connections_lock:
            connections = list(self.connections)
        for request in connections:
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            request.close()


class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        owner = self.server.owner
        try:
            # Máximo 120 ADU por conexión; las conexiones inactivas caducan en 2 s.
            for _ in range(120):
                if owner.stopping.is_set():
                    break
                deadline = time.monotonic() + 2
                raw = receive_adu(self.request, deadline)
                owner.monitor.add("simulador", "RX", raw)
                frame = decode_frame(raw)
                # Unit ID es configuración explícita de este simulador TCP.
                pdu = (owner.memory.reply(frame.pdu) if frame.unit == owner.unit
                       else bytes((frame.pdu[0] | 0x80, 11)))
                response = Frame(frame.transaction, frame.unit, pdu).encode()
                set_remaining(self.request, deadline)
                self.request.sendall(response)
                owner.monitor.add("simulador", "TX", response)
                # Límite sostenido por conexión de 50 respuestas/s.
                if owner.stopping.wait(0.02):
                    break
        except (OSError, ProtocolError) as error:
            # El cierre normal del cliente de una sola lectura no es un fallo de laboratorio.
            if str(error) != "Conexión cerrada antes de completar la trama":
                owner.monitor.add("simulador", "ERROR", detail=str(error))


class Simulator:
    def __init__(self, monitor: Monitor | None = None):
        self.monitor = monitor if monitor is not None else Monitor()
        self.memory = Memory()
        self.stopping = threading.Event()
        self.unit = 1
        self._server = None
        self._thread = None
        self._lock = threading.Lock()

    @property
    def port(self):
        with self._lock:
            return self._server.server_address[1] if self._server else None

    def start(self, port=15020, unit=1):
        integer(port, 0, 65535, "Puerto del simulador")
        integer(unit, 0, 255, "Unidad TCP")
        with self._lock:
            if self._server:
                raise ProtocolError("El simulador ya está iniciado")
            self.unit = unit
            self.stopping.clear()
            self._server = _TCPServer(("127.0.0.1", port), self)
            self._thread = threading.Thread(target=self._server.serve_forever,
                                            kwargs={"poll_interval": 0.05}, daemon=True)
            self._thread.start()
            self.monitor.add("simulador", "ESTADO", detail=f"Escuchando 127.0.0.1:{self._server.server_address[1]}")

    def stop(self):
        with self._lock:
            if self._server:
                self.stopping.set()
                self._server.shutdown()
                self._server.close_connections()
                self._server.server_close()
                self._thread.join(timeout=1)
                self._server = None
                self.monitor.add("simulador", "ESTADO", detail="Detenido")
