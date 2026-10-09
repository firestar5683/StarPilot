"""Galaxy BLE v1: bounded framing and authenticated, direction-bound messages."""
import json
import os
import struct
import zlib

from Crypto.Cipher import AES

SERVICE_UUID = "bd490001-6dc1-4de7-a7d0-6cdb441f7650"
RX_UUID = "bd490002-6dc1-4de7-a7d0-6cdb441f7650"
TX_UUID = "bd490003-6dc1-4de7-a7d0-6cdb441f7650"
INFO_UUID = "bd490004-6dc1-4de7-a7d0-6cdb441f7650"
MAX_FRAME = 2 * 1024 * 1024
MAX_BODY = 1024 * 1024
AAD_PREFIX = b"galaxy-ble-v1/"


def seal(value, key, direction, nonce=None):
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce or os.urandom(12))
    cipher.update(AAD_PREFIX + direction.encode())
    plaintext = json.dumps(value, separators=(",", ":")).encode()
    if len(plaintext) > MAX_FRAME:
        raise ValueError("Decoded message exceeds limit")
    compressed = zlib.compress(plaintext, wbits=-15)
    encoded = (b"\x01" + struct.pack(">I", len(plaintext)) + compressed
               if len(compressed) < len(plaintext) else b"\x00" + struct.pack(">I", len(plaintext)) + plaintext)
    ciphertext, tag = cipher.encrypt_and_digest(encoded)
    data = cipher.nonce + ciphertext + tag
    if len(data) > MAX_FRAME:
        raise ValueError("Message exceeds BLE frame limit")
    return struct.pack(">I", len(data)) + data


def open_message(data, key, direction):
    if not 28 <= len(data) <= MAX_FRAME:
        raise ValueError("Invalid message length")
    cipher = AES.new(key, AES.MODE_GCM, nonce=data[:12])
    cipher.update(AAD_PREFIX + direction.encode())
    encoded = cipher.decrypt_and_verify(data[12:-16], data[-16:])
    if len(encoded) < 5:
        raise ValueError("Invalid compressed envelope")
    length = struct.unpack(">I", encoded[1:5])[0]
    if not 1 <= length <= MAX_FRAME:
        raise ValueError("Invalid decoded message length")
    if encoded[0] == 1:
        decoder = zlib.decompressobj(wbits=-15)
        plaintext = decoder.decompress(encoded[5:], length + 1)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("Invalid compressed message")
    elif encoded[0] == 0:
        plaintext = encoded[5:]
    else:
        raise ValueError("Unknown compression codec")
    if len(plaintext) != length:
        raise ValueError("Incorrect decoded message length")
    value = json.loads(plaintext)
    if not isinstance(value, dict):
        raise ValueError("Expected an object")
    return value


class Assembler:
    def __init__(self):
        self.reset()

    def reset(self):
        self.buffer = bytearray()
        self.sequence = 0
        self.length = None

    def add(self, packet):
        if len(packet) < 6 or packet[0] != 1:
            raise ValueError("Invalid data packet")
        sequence = struct.unpack(">I", packet[1:5])[0]
        if sequence != self.sequence:
            raise ValueError("Out-of-order fragment")
        self.sequence += 1
        self.buffer.extend(packet[5:])
        if self.length is None and len(self.buffer) >= 4:
            self.length = struct.unpack(">I", self.buffer[:4])[0]
            if not 28 <= self.length <= MAX_FRAME:
                self.reset()
                raise ValueError("Invalid frame length")
        if len(self.buffer) > MAX_FRAME + 4:
            self.reset()
            raise ValueError("Frame limit exceeded")
        if self.length is not None and len(self.buffer) >= self.length + 4:
            if len(self.buffer) != self.length + 4:
                self.reset()
                raise ValueError("Trailing frame bytes")
            result = bytes(self.buffer[4:])
            self.reset()
            return result
        return None


def packets(frame, size=180):
    if not 20 <= size <= 180:
        raise ValueError("Invalid ATT payload size")
    for sequence, start in enumerate(range(0, len(frame), size - 5)):
        yield b"\x01" + struct.pack(">I", sequence) + frame[start:start + size - 5]
