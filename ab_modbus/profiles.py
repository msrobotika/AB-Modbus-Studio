# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
import json
import os
from pathlib import Path
import tempfile
import threading

from .protocol import ProtocolError, integer, validate_read
from .transport import safe_target

DEFAULT = dict(name="Laboratorio local", host="127.0.0.1", port=15020, unit=1,
               function=3, address=0, count=8, timeout_ms=1500)
FIELDS = set(DEFAULT)


def validate_profile(data):
    if type(data) is not dict or set(data) != FIELDS:
        raise ProtocolError("Campos de perfil no válidos; no se importan permisos de red")
    if type(data["name"]) is not str or not 1 <= len(data["name"].strip()) <= 64:
        raise ProtocolError("Nombre del perfil: entre 1 y 64 caracteres")
    if any(ord(c) < 32 for c in data["name"]):
        raise ProtocolError("Nombre del perfil con caracteres de control")
    host = safe_target(data["host"], allow_lan=True)
    integer(data["port"], 1, 65535, "Puerto")
    integer(data["unit"], 0, 255, "Unidad")
    integer(data["timeout_ms"], 100, 10000, "Tiempo de espera")
    validate_read(data["function"], data["address"], data["count"])
    return dict(data, host=host, name=data["name"].strip())


class Profiles:
    def __init__(self, directory: Path):
        self.path = Path(directory) / "profiles.json"
        self._lock = threading.Lock()
        self._profiles = [dict(DEFAULT)]
        if self.path.exists():
            if self.path.stat().st_size > 65536:
                raise ProtocolError("El archivo de perfiles supera 64 KiB")
            self._profiles = self.validate_document(json.loads(self.path.read_text(encoding="utf-8")))

    @staticmethod
    def validate_document(document):
        if (type(document) is not dict or set(document) != {"schema", "profiles"}
                or type(document["schema"]) is not int or document["schema"] != 1
                or type(document["profiles"]) is not list or not 1 <= len(document["profiles"]) <= 50):
            raise ProtocolError("Documento de perfiles incompatible (schema 1, entre 1 y 50 perfiles)")
        profiles = [validate_profile(profile) for profile in document["profiles"]]
        if len({p["name"].casefold() for p in profiles}) != len(profiles):
            raise ProtocolError("Hay nombres de perfil duplicados")
        return profiles

    def document(self):
        with self._lock:
            return {"schema": 1, "profiles": [dict(p) for p in self._profiles]}

    def replace(self, document):
        profiles = self.validate_document(document)
        encoded = json.dumps({"schema": 1, "profiles": profiles}, ensure_ascii=False, indent=2)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, filename = tempfile.mkstemp(prefix=".profiles-", suffix=".tmp", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(filename, self.path)
                self._profiles = profiles
            finally:
                if os.path.exists(filename):
                    os.unlink(filename)
