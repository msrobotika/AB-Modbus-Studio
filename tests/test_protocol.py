# SPDX-License-Identifier: MIT
import random
import struct
import unittest

from ab_modbus.protocol import (Frame, ModbusException, ProtocolError, decode_frame,
                                pack_values, read_request, read_response)
from ab_modbus.server import Memory


class ProtocolTests(unittest.TestCase):
    def test_independent_request_vector(self):
        # Vector calculado manualmente: TID 0x1234, unidad 1, FC03, inicio 107, 3 registros.
        self.assertEqual(Frame(0x1234, 1, read_request(3, 107, 3)).encode(),
                         bytes.fromhex("1234 0000 0006 01 03 006b 0003"))

    def test_independent_response_vectors(self):
        self.assertEqual(read_response(bytes.fromhex("03 06 022b 0000 0064"), 3, 3), [555, 0, 100])
        self.assertEqual(read_response(bytes.fromhex("04 02 000a"), 4, 1), [10])
        self.assertEqual(read_response(bytes.fromhex("01 03 cd6b05"), 1, 19),
                         [1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1])
        self.assertEqual(read_response(bytes.fromhex("02 01 05"), 2, 3), [1, 0, 1])

    def test_maximum_sizes(self):
        for function, count in ((1, 2000), (2, 2000), (3, 125), (4, 125)):
            with self.subTest(function=function):
                pdu = pack_values(function, [1] * count)
                frame = Frame(65535, 255, pdu)
                self.assertEqual(decode_frame(frame.encode()), frame)
                self.assertLessEqual(len(frame.encode()), 260)
                self.assertEqual(read_response(pdu, function, count), [1] * count)
                read_request(function, 65536 - count, count)

    def test_invalid_read_ranges_and_writes(self):
        cases = [(3, 0, 0), (3, 0, 126), (1, 0, 2001), (1, 65535, 2), (4, -1, 1),
                 (3, True, 1), (3, 0, 1.0), (True, 0, 1)]
        cases += [(fc, 0, 1) for fc in (0, 5, 6, 15, 16, 22, 23, 43, 127, 255)]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ProtocolError):
                read_request(*args)

    def test_malformed_mbap(self):
        good = bytes.fromhex("000100000006010300000001")
        bad = [b"", good[:6], good[:-1], good + b"\0", good[:2] + b"\x00\x01" + good[4:]]
        bad += [good[:4] + struct.pack(">H", n) + good[6:] for n in (0, 1, 255, 65535)]
        for data in bad:
            with self.subTest(data=data.hex()), self.assertRaises(ProtocolError):
                decode_frame(data)

    def test_malformed_response(self):
        for pdu, fc, count in ((b"", 3, 1), (b"\x04\x02\x00\x01", 3, 1),
                               (b"\x03\x01\x00", 3, 1), (b"\x03\x02\x00", 3, 1),
                               (b"\x01\x01\x80", 1, 1), (b"\x83", 3, 1),
                               (b"\x83\x00", 3, 1), (b"\x83\x02\x00", 3, 1)):
            with self.subTest(pdu=pdu.hex()), self.assertRaises(ProtocolError):
                read_response(pdu, fc, count)

    def test_exception_information(self):
        with self.assertRaises(ModbusException) as error:
            read_response(b"\x83\x02", 3, 1)
        self.assertEqual((error.exception.function, error.exception.code), (3, 2))

    def test_seeded_frames(self):
        rng = random.Random(20261021)
        for _ in range(400):
            function = rng.choice((1, 2, 3, 4))
            count = rng.randint(1, 2000 if function < 3 else 125)
            values = [rng.randint(0, 1 if function < 3 else 65535) for _ in range(count)]
            self.assertEqual(read_response(pack_values(function, values), function, count), values)

    def test_seeded_malformed_inputs_are_bounded(self):
        rng = random.Random(75)
        for _ in range(500):
            data = rng.randbytes(rng.randint(0, 300))
            try:
                decode_frame(data)
            except ProtocolError:
                pass

    def test_simulator_never_accepts_write(self):
        memory = Memory()
        before = memory.reply(bytes.fromhex("0300000001"))
        for function in (5, 6, 15, 16, 22, 23):
            self.assertEqual(memory.reply(bytes((function, 0, 0, 255, 0))), bytes((function | 128, 1)))
        self.assertEqual(memory.reply(bytes.fromhex("0300000001")), before)

    def test_simulator_exceptions(self):
        memory = Memory()
        self.assertEqual(memory.reply(bytes.fromhex("0300000000")), b"\x83\x03")
        self.assertEqual(memory.reply(bytes.fromhex("03ffff0001")), b"\x83\x02")
        self.assertEqual(memory.reply(b"\x03"), b"\x83\x03")
        self.assertEqual(memory.reply(bytes.fromhex("030000007e")), b"\x83\x03")

    def test_invalid_encode(self):
        for frame in (Frame(-1, 1, b"\x03"), Frame(0, 256, b"\x03"), Frame(0, 1, b""), Frame(0, 1, b"x" * 254)):
            with self.assertRaises(ProtocolError):
                frame.encode()
