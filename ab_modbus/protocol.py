# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
"""PDU de lectura y MBAP. Sin sockets, UI ni bibliotecas Modbus externas."""
from dataclasses import dataclass
import struct

READ_FUNCTIONS = (1, 2, 3, 4)


class ProtocolError(ValueError):
    """Una trama no cumple el contrato del protocolo."""


class ModbusException(ProtocolError):
    def __init__(self, function: int, code: int):
        self.function, self.code = function, code
        labels = {1: "función no admitida", 2: "dirección no disponible",
                  3: "valor o cantidad no válido", 4: "fallo del servidor",
                  11: "unidad sin respuesta"}
        super().__init__(f"Excepción Modbus {code:02X}: {labels.get(code, 'error del equipo')}")


def integer(value, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ProtocolError(f"{label}: se requiere un entero entre {minimum} y {maximum}")
    return value


def validate_read(function: int, address: int, count: int) -> None:
    if type(function) is not int or function not in READ_FUNCTIONS:
        raise ProtocolError("Solo se admiten lecturas FC01, FC02, FC03 y FC04")
    integer(address, 0, 65535, "Dirección PDU")
    integer(count, 1, 2000 if function < 3 else 125, "Cantidad")
    if address + count > 65536:
        raise ProtocolError("El rango supera la dirección PDU 65535")


def read_request(function: int, address: int, count: int) -> bytes:
    validate_read(function, address, count)
    return struct.pack(">BHH", function, address, count)


@dataclass(frozen=True)
class Frame:
    transaction: int
    unit: int
    pdu: bytes

    def encode(self) -> bytes:
        integer(self.transaction, 0, 65535, "Transacción")
        integer(self.unit, 0, 255, "Unidad")
        if not isinstance(self.pdu, bytes) or not 1 <= len(self.pdu) <= 253:
            raise ProtocolError("La PDU debe contener entre 1 y 253 bytes")
        return struct.pack(">HHHB", self.transaction, 0, len(self.pdu) + 1, self.unit) + self.pdu


def header_length(header: bytes) -> int:
    if len(header) != 7:
        raise ProtocolError("Cabecera MBAP incompleta")
    _, protocol, length, _ = struct.unpack(">HHHB", header)
    if protocol != 0:
        raise ProtocolError("Identificador de protocolo MBAP distinto de cero")
    if not 2 <= length <= 254:
        raise ProtocolError("Longitud MBAP fuera de límites")
    return length - 1


def decode_frame(data: bytes) -> Frame:
    length = header_length(data[:7])
    if len(data) != 7 + length:
        raise ProtocolError("La longitud de la trama no coincide con MBAP")
    transaction, _, _, unit = struct.unpack(">HHHB", data[:7])
    return Frame(transaction, unit, data[7:])


def read_response(pdu: bytes, function: int, count: int) -> list[int]:
    validate_read(function, 0, count)
    if not pdu:
        raise ProtocolError("Respuesta sin función")
    if pdu[0] == function | 0x80:
        if len(pdu) != 2 or pdu[1] == 0:
            raise ProtocolError("Respuesta de excepción mal formada")
        raise ModbusException(function, pdu[1])
    if pdu[0] != function:
        raise ProtocolError("La función de respuesta no coincide")
    expected = (count + 7) // 8 if function < 3 else count * 2
    if len(pdu) != expected + 2 or pdu[1] != expected:
        raise ProtocolError("Número de bytes de respuesta incorrecto")
    payload = pdu[2:]
    if function < 3:
        if count % 8 and payload[-1] >> (count % 8):
            raise ProtocolError("Bits de relleno distintos de cero")
        return [(payload[i // 8] >> (i % 8)) & 1 for i in range(count)]
    return list(struct.unpack(">" + "H" * count, payload))


def pack_values(function: int, values: list[int]) -> bytes:
    validate_read(function, 0, len(values))
    if function < 3:
        payload = bytearray((len(values) + 7) // 8)
        for i, value in enumerate(values):
            integer(value, 0, 1, "Bit")
            payload[i // 8] |= value << (i % 8)
        payload = bytes(payload)
    else:
        for value in values:
            integer(value, 0, 65535, "Registro")
        payload = struct.pack(">" + "H" * len(values), *values)
    return bytes((function, len(payload))) + payload
