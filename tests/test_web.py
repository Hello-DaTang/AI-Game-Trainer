import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from trainer.service import TrainerService
from trainer.diagnostics import DiagnosticError
from trainer.web import serve
from tests.test_service import FakeCEBridge


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = TrainerService(Path(self.tmp.name), FakeCEBridge())
        self.server = serve(self.service, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join, 2)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def test_health_and_static_page(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", "/api/health")
        res = connection.getresponse()
        self.assertEqual(res.status, 200)
        self.assertEqual(json.loads(res.read())["ok"], True)
        connection.request("GET", "/")
        res = connection.getresponse()
        self.assertEqual(res.status, 200)
        page = res.read().decode("utf-8")
        self.assertIn("AI Game Trainer", page)
        self.assertIn('id="self-test"', page)
        self.assertIn('id="self-test-result"', page)
        connection.close()

    def test_self_test_errors_are_returned_as_json(self):
        def failed():
            raise DiagnosticError("fixture unavailable")
        self.service.selftest = failed
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request(
            "POST", "/api/diagnostics/self-test", body="{}",
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(json.loads(response.read())["error"], "fixture unavailable")
        connection.close()

    def test_unauthorized_origin_rejected(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request(
            "POST", "/api/games", body='{"name":"Bad","exe":"bad.exe"}',
            headers={"Content-Type": "application/json", "Origin": "https://malicious.example"},
        )
        res = connection.getresponse()
        self.assertEqual(res.status, 403)
        res.read()
        connection.close()


if __name__ == "__main__":
    unittest.main()
