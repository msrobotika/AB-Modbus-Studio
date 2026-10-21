# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
import socket
import threading
import time

from .monitor import Monitor
from .protocol import Frame, ProtocolError, decode_frame, integer, read_request, read_response
from .transport import receive_adu, safe_target, set_remaining


class ReadClient:
    """Una lectura por conexión, sin reintentos ni envío de PDU arbitrarias."""
    def __init__(self, monitor: Monitor | None = None):
        self.monitor = monitor if monitor is not None else Monitor()
        self._lock = threading.Lock()
        self._transaction = 0

    def read(self, host="127.0.0.1", port=15020, unit=1, function=3,
             address=0, count=8, timeout_ms=1500, allow_lan=False):
        host = safe_target(host, allow_lan)
        integer(port, 1, 65535, "Puerto")
        integer(unit, 0, 255, "Unidad TCP")
        integer(timeout_ms, 100, 10000, "Tiempo de espera (ms)")
        pdu = read_request(function, address, count)
        if not self._lock.acquire(blocking=False):
            raise ProtocolError("Ya hay una lectura en curso")
        try:
            self._transaction = (self._transaction + 1) & 0xFFFF
            request = Frame(self._transaction, unit, pdu).encode()
            start = time.monotonic()
            deadline = start + timeout_ms / 1000
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                set_remaining(sock, deadline)
                sock.connect((host, port))
                set_remaining(sock, deadline)
                sock.sendall(request)
                self.monitor.add("cliente", "TX", request, f"{host}:{port} · FC{function:02d}")
                response = receive_adu(sock, deadline)
                self.monitor.add("cliente", "RX", response, f"{host}:{port}")
                frame = decode_frame(response)
                if frame.transaction != self._transaction or frame.unit != unit:
                    raise ProtocolError("Transacción o unidad de respuesta no coincide")
                values = read_response(frame.pdu, function, count)
            return dict(values=values, elapsed_ms=round((time.monotonic() - start) * 1000, 2),
                        transaction=self._transaction, function=function, address=address,
                        host=host, port=port, unit=unit)
        except (OSError, ProtocolError) as error:
            self.monitor.add("cliente", "ERROR", detail=str(error))
            raise
        finally:
            self._lock.release()
