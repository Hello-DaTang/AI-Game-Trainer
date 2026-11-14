import tempfile
import unittest
from pathlib import Path

from trainer.store import Store, StoreError


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "nested" / "trainer.sqlite3"
        self.store = Store(self.db_path)

    def test_persists_game_and_feature_across_instances(self):
        game = self.store.add_game("Demo", "demo.exe")
        feature = self.store.add_feature(game["id"], "Health", "Player Health")
        restarted = Store(self.db_path)
        self.assertEqual(restarted.games()[0]["exe"], "demo.exe")
        self.assertEqual(restarted.features(game["id"])[0]["id"], feature["id"])

    def test_rejects_duplicate_process_and_record(self):
        game = self.store.add_game("Demo", "demo.exe")
        with self.assertRaises(StoreError):
            self.store.add_game("Demo 2", "DEMO.EXE")
        self.store.add_feature(game["id"], "Health", "Player Health")
        with self.assertRaises(StoreError):
            self.store.add_feature(game["id"], "Health again", "Player Health")

    def test_rejects_executable_paths_and_empty_fields(self):
        for name in ("", " "):
            with self.assertRaises(StoreError):
                self.store.add_game(name, "demo.exe")
        for exe in ("C:\\Games\\game.exe", "../game.exe", "game", ""):
            with self.assertRaises(StoreError):
                self.store.add_game("Game", exe)


if __name__ == "__main__":
    unittest.main()
