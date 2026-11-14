import unittest

from trainer.diagnostics import DiagnosticError, verify_memory_roundtrip


class FakeMemoryBridge:
    def __init__(self, initial=123):
        self.pid = None
        self.value = initial
        self.calls = []

    def call(self, method, params=None):
        params = params or {}
        self.calls.append((method, params))
        if method == "open_process":
            self.pid = int(params["process_id_or_name"])
            return {"success": True}
        if method == "get_opened_process_id":
            return {"success": True, "process_id": self.pid}
        if method == "read_integer":
            return {"success": True, "value": self.value}
        if method == "write_integer":
            self.value = params["value"]
            return {"success": True}
        raise AssertionError(method)


class DiagnosticsTests(unittest.TestCase):
    def test_read_write_restore(self):
        bridge = FakeMemoryBridge()
        out = verify_memory_roundtrip(bridge, 991, "0x1234")
        self.assertEqual(out, {"initial": 123, "changed": 777, "restored": 123})
        self.assertEqual(bridge.value, 123)
        self.assertEqual(bridge.calls[0], ("open_process", {"process_id_or_name": 991}))
        self.assertEqual(sum(x[0] == "write_integer" for x in bridge.calls), 2)
        self.assertTrue(all(
            params.get("address", "0x1234") == "0x1234"
            for method, params in bridge.calls if method in ("write_integer", "read_integer")
        ))

    def test_bad_initial_value_fails_without_writing(self):
        bridge = FakeMemoryBridge(initial=999)
        with self.assertRaises(DiagnosticError):
            verify_memory_roundtrip(bridge, 991, "0x1234")
        self.assertEqual(bridge.value, 999)
        self.assertFalse(any(method == "write_integer" for method, _ in bridge.calls))

    def test_write_that_does_not_change_memory_fails_safely(self):
        class NoOpWrites(FakeMemoryBridge):
            def call(self, method, params=None):
                if method == "write_integer":
                    self.calls.append((method, params))
                    return {"success": True}
                return super().call(method, params)

        bridge = NoOpWrites()
        with self.assertRaises(DiagnosticError):
            verify_memory_roundtrip(bridge, 991, "0x1234")
        self.assertEqual(bridge.value, 123)


if __name__ == "__main__":
    unittest.main()
