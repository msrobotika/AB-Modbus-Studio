# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
from collections import deque
from datetime import datetime, timezone
import threading


class Monitor:
    """Memoria acotada; el monitor muestra las ADU de esta aplicación, no captura paquetes."""
    def __init__(self, capacity: int = 500):
        self._events = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._sequence = 0

    def add(self, source: str, direction: str, data: bytes = b"", detail: str = ""):
        with self._lock:
            self._sequence += 1
            event = dict(id=self._sequence, time=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                         source=source, direction=direction, hex=data.hex(" ").upper(), detail=detail)
            self._events.append(event)

    def snapshot(self):
        with self._lock:
            return [dict(event) for event in self._events]

    def clear(self):
        with self._lock:
            self._events.clear()
