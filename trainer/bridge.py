"""Small direct client for miscusi-peek/cheatengine-mcp-bridge v12.

Wire format: little-endian uint32 payload length + JSON-RPC 2.0 bytes.
No arbitrary command endpoint is exposed to HTTP clients.
"""
from __future__ import annotations

import json
import os
import socket
import struct

PIPE_NAME = r"\\.\pipe\CE_MCP_Bridge_v99"
MAX_REPLY = 8 * 1024 * 1024


class BridgeError(RuntimeError):
    """The CE bridge is unavailable or returned an error."""


def _read_socket(sock: socket.socket, count: int) -> bytes:
    pieces = []
    while count:
        data = sock.recv(count)
        if not data:
            raise BridgeError("CE bridge closed the connection")
        pieces.append(data)
        count -= len(data)
    return b"".join(pieces)


class CEBridge:
    """One connection per request; avoids sharing a named-pipe handle across threads."""

    def __init__(self, transport: str | None = None, port: int | None = None):
        self.transport = transport or os.environ.get(
            "TRAINER_CE_TRANSPORT", "pipe" if os.name == "nt" else "tcp"
        )
        self.port = int(port or os.environ.get("TRAINER_CE_PORT", "9876"))
        if self.transport not in ("pipe", "tcp"):
            raise ValueError("TRAINER_CE_TRANSPORT must be pipe or tcp")
        if not 1 <= self.port <= 65535:
            raise ValueError("Invalid CE relay port")
        if self.transport == "pipe" and os.name != "nt":
            raise ValueError("Named pipes require Windows")

    def call(self, method: str, params: dict | None = None) -> dict:
        payload = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1},
            ensure_ascii=False,
        ).encode("utf-8")
        request = struct.pack("<I", len(payload)) + payload
        try:
            if self.transport == "tcp":
                with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
                    sock.settimeout(8)
                    sock.sendall(request)
                    length = struct.unpack("<I", _read_socket(sock, 4))[0]
                    if length > MAX_REPLY:
                        raise BridgeError("CE bridge response exceeds size limit")
                    raw = _read_socket(sock, length)
            else:
                raw = self._pipe_exchange(request)
            result = json.loads(raw)
        except BridgeError:
            raise
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise BridgeError("Cannot communicate with CE Bridge: " + str(exc)) from exc
        if not isinstance(result, dict):
            raise BridgeError("Invalid CE bridge response")
        if "error" in result:
            raise BridgeError(str(result["error"]))
        value = result.get("result", result)
        if not isinstance(value, dict):
            raise BridgeError("Invalid CE bridge result")
        if value.get("success") is False:
            raise BridgeError(str(value.get("error", "CE command failed")))
        return value

    @staticmethod
    def _pipe_exchange(request: bytes) -> bytes:
        try:
            import win32file
        except ImportError as exc:
            raise BridgeError("Install Windows dependencies: py -m pip install -r requirements-windows.txt") from exc
        handle = None
        try:
            handle = win32file.CreateFile(
                PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None,
            )
            # Keep the two writes used by upstream v12 (header, then JSON body).
            win32file.WriteFile(handle, request[:4])
            win32file.WriteFile(handle, request[4:])
            length_bytes = CEBridge._read_pipe(handle, 4, win32file)
            length = struct.unpack("<I", length_bytes)[0]
            if length > MAX_REPLY:
                raise BridgeError("CE bridge response exceeds size limit")
            return CEBridge._read_pipe(handle, length, win32file)
        finally:
            if handle is not None:
                win32file.CloseHandle(handle)

    @staticmethod
    def _read_pipe(handle, length: int, win32file) -> bytes:
        output = bytearray()
        while len(output) < length:
            _, part = win32file.ReadFile(handle, length - len(output))
            if not part:
                raise BridgeError("CE pipe disconnected")
            output.extend(part)
        return bytes(output)
