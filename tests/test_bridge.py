import json
import socket
import struct
import threading
import unittest

from trainer.bridge import CEBridge, BridgeError


class BridgeTests(unittest.TestCase):
    def _exchange(self, response):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        captured = []

        def server():
            try:
                conn, _ = listener.accept()
                with conn:
                    def exact(n):
                        chunks = []
                        while n:
                            piece = conn.recv(n)
                            if not piece:
                                raise EOFError()
                            chunks.append(piece)
                            n -= len(piece)
                        return b"".join(chunks)
                    length = struct.unpack("<I", exact(4))[0]
                    captured.append(json.loads(exact(length)))
                    payload = json.dumps(response).encode()
                    conn.sendall(struct.pack("<I", len(payload)) + payload)
            finally:
                listener.close()

        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        try:
            return CEBridge(transport="tcp", port=port).call("ping"), captured
        finally:
            worker.join(timeout=3)

    def test_tcp_json_rpc_framing(self):
        reply, calls = self._exchange({"jsonrpc": "2.0", "result": {"success": True, "version": "12.0.0"}, "id": 1})
        self.assertEqual(reply["version"], "12.0.0")
        self.assertEqual(calls[0]["method"], "ping")

    def test_bridge_error_is_not_reported_successfully(self):
        with self.assertRaises(BridgeError):
            self._exchange({"jsonrpc": "2.0", "result": {"success": False, "error": "Not attached"}, "id": 1})


if __name__ == "__main__":
    unittest.main()
