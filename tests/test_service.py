import tempfile
import unittest
from pathlib import Path

from trainer.service import TrainerService
from trainer.store import StoreError


class FakeCEBridge:
    def __init__(self):
        self.pid = 731
        self.list = [{"pid": 731, "name": "Demo.exe"}]
        self.records = [
            {"id": 42, "description": "Infinite HP", "enabled": False},
            {"id": 43, "description": "Infinite Ammo", "enabled": False},
        ]
        self.calls = []

    def call(self, method, params=None):
        params = params or {}
        self.calls.append((method, params))
        if method == "ping":
            return {"success": True, "version": "12.0.0"}
        if method == "get_process_list":
            return {"processes": self.list}
        if method == "get_opened_process_id":
            return {"process_id": self.pid}
        if method == "get_address_list":
            return {"records": self.records, "total": len(self.records)}
        if method == "save_table":
            Path(params["filename"]).write_text("<CheatTable />", encoding="utf-8")
            return {"success": True}
        if method == "load_table":
            if not Path(params["filename"]).is_file():
                raise RuntimeError("CT not found")
            for record in self.records:
                record["enabled"] = False
            return {"success": True}
        if method == "open_process":
            self.pid = params["process_id_or_name"]
            return {"success": True}
        if method == "evaluate_lua":
            code = params["code"]
            if "getMemoryRecordByID(42)" in code:
                self.records[0]["enabled"] = "r.Active=true" in code
            elif "getMemoryRecordByID(43)" in code:
                self.records[1]["enabled"] = "r.Active=true" in code
            return {"success": True}
        if method == "get_memory_record":
            record = next(r for r in self.records if r["id"] == params["id"])
            return {"success": True, "record": record}
        raise AssertionError("Unexpected CE call: " + method)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bridge = FakeCEBridge()
        self.app = TrainerService(Path(self.tmp.name), self.bridge)
        self.game = self.app.store.add_game("Demo", "demo.exe")

    def test_capture_and_replay_after_restart(self):
        feature = self.app.capture(self.game["id"], "Unlimited HP", "Infinite HP")
        self.assertTrue(self.app.table_path(self.game["id"]).is_file())
        self.assertEqual(self.app.snapshot()["games"][0]["features"][0]["id"], feature["id"])
        restarted_bridge = FakeCEBridge()
        app2 = TrainerService(Path(self.tmp.name), restarted_bridge)
        result = app2.toggle(feature["id"], True)
        self.assertTrue(result["enabled"])
        self.assertTrue(restarted_bridge.records[0]["enabled"])
        self.assertIn(("load_table", {"filename": str(app2.table_path(self.game["id"])), "merge": False}), restarted_bridge.calls)
        app2.toggle(feature["id"], False)
        self.assertFalse(restarted_bridge.records[0]["enabled"])
        self.assertEqual(sum(m == "load_table" for m, _ in restarted_bridge.calls), 1)

    def test_capture_must_be_attached_to_exact_target(self):
        self.bridge.pid = 999
        with self.assertRaises(StoreError):
            self.app.capture(self.game["id"], "HP", "Infinite HP")
        self.assertFalse(self.app.table_path(self.game["id"]).exists())

    def test_capture_blocks_duplicate_description_and_missing_existing_record(self):
        self.app.capture(self.game["id"], "HP", "Infinite HP")
        with self.assertRaises(StoreError):
            self.app.capture(self.game["id"], "HP2", "Infinite HP")
        self.bridge.records = [{"id": 43, "description": "Infinite Ammo", "enabled": False}]
        with self.assertRaises(StoreError):
            self.app.capture(self.game["id"], "Ammo", "Infinite Ammo")

    def test_no_process_and_multiple_processes_fail_closed(self):
        self.app.capture(self.game["id"], "HP", "Infinite HP")
        feature_id = self.app.snapshot()["games"][0]["features"][0]["id"]
        self.bridge.list = []
        with self.assertRaises(StoreError):
            self.app.toggle(feature_id, True)
        self.bridge.list = [{"pid": 731, "name": "demo.exe"}, {"pid": 732, "name": "demo.exe"}]
        with self.assertRaises(StoreError):
            self.app.toggle(feature_id, True)

    def test_untrusted_input_does_not_become_lua(self):
        with self.assertRaises(StoreError):
            self.app.capture(self.game["id"], "Bad", "nonexistent'; os.execute('bad')")
        self.app.capture(self.game["id"], "HP", "Infinite HP")
        feature_id = self.app.snapshot()["games"][0]["features"][0]["id"]
        with self.assertRaises(StoreError):
            self.app.toggle(feature_id, "true")
        self.app.toggle(feature_id, True)
        code = [data["code"] for method, data in self.bridge.calls if method == "evaluate_lua"][0]
        self.assertNotIn("Infinite HP", code)
        self.assertIn("getMemoryRecordByID(42)", code)


if __name__ == "__main__":
    unittest.main()
