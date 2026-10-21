# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
"""Transporte TCP con plazo total, lecturas exactas y política de destino."""
import ipaddress
import socket
import time

from .protocol import ProtocolError, header_length

PRIVATE_V4 = tuple(ipaddress.ip_network(n) for n in
                   ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def safe_target(host: str, allow_lan: bool = False) -> str:
    if type(allow_lan) is not bool:
        raise ProtocolError("La autorización de red debe ser booleana")
    if host == "localhost":
        host = "127.0.0.1"
    try:
        address = ipaddress.IPv4Address(host)
    except (ValueError, TypeError):
        raise ProtocolError("Usa una IPv4 literal o localhost; DNS e IPv6 no están habilitados") from None
    if address.is_loopback:
        return str(address)
    if allow_lan and any(address in network for network in PRIVATE_V4):
        return str(address)
    raise ProtocolError("Destino bloqueado: solo equipo local; habilita red privada para una IPv4 RFC1918")


def set_remaining(sock: socket.socket, deadline: float) -> None:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Tiempo de transacción agotado")
    sock.settimeout(remaining)


def receive_exact(sock: socket.socket, count: int, deadline: float) -> bytes:
    result = bytearray()
    while len(result) < count:
        set_remaining(sock, deadline)
        chunk = sock.recv(count - len(result))
        if not chunk:
            raise ProtocolError("Conexión cerrada antes de completar la trama")
        result.extend(chunk)
    return bytes(result)


def receive_adu(sock: socket.socket, deadline: float) -> bytes:
    header = receive_exact(sock, 7, deadline)
    return header + receive_exact(sock, header_length(header), deadline)
