"""Durable game and trainer feature metadata, separated from runtime state."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
import uuid
from pathlib import Path


class StoreError(ValueError):
    pass


def _as_dict(row):
    return dict(row) if row is not None else None


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    exe TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS features (
                    id TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    record_description TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(game_id, record_description)
                );
            """)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA busy_timeout = 10000")
            with db:
                yield db
        finally:
            db.close()

    def add_game(self, name: str, exe: str):
        name, exe = name.strip(), exe.strip()
        if not name or len(name) > 128:
            raise StoreError("游戏名称需要 1–128 个字符")
        if not exe or len(exe) > 255 or "/" in exe or "\\" in exe or not exe.lower().endswith(".exe"):
            raise StoreError("请输入游戏进程文件名，例如 game.exe（不能是完整路径）")
        item_id = uuid.uuid4().hex
        try:
            with self._connect() as db:
                db.execute("INSERT INTO games(id, name, exe) VALUES(?, ?, ?)", (item_id, name, exe))
        except sqlite3.IntegrityError as exc:
            raise StoreError("此 EXE 已经添加到游戏库") from exc
        return self.game(item_id)

    def game(self, game_id: str):
        with self._connect() as db:
            row = db.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        if not row:
            raise StoreError("未找到游戏")
        return _as_dict(row)

    def games(self):
        with self._connect() as db:
            rows = db.execute("SELECT * FROM games ORDER BY created_at, rowid").fetchall()
        return list(map(_as_dict, rows))

    def add_feature(self, game_id: str, title: str, record_description: str):
        title, record_description = title.strip(), record_description.strip()
        self.game(game_id)
        if not title or len(title) > 128 or not record_description or len(record_description) > 255:
            raise StoreError("请提供功能名称与准确的 CE 记录描述")
        item_id = uuid.uuid4().hex
        try:
            with self._connect() as db:
                db.execute(
                    "INSERT INTO features(id, game_id, title, record_description) VALUES(?, ?, ?, ?)",
                    (item_id, game_id, title, record_description),
                )
        except sqlite3.IntegrityError as exc:
            raise StoreError("该 CE 记录已经保存为按钮") from exc
        return self.feature(item_id)

    def feature(self, feature_id: str):
        with self._connect() as db:
            row = db.execute("SELECT * FROM features WHERE id = ?", (feature_id,)).fetchone()
        if not row:
            raise StoreError("未找到修改功能")
        return _as_dict(row)

    def features(self, game_id: str):
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM features WHERE game_id = ? ORDER BY created_at, rowid",
                (game_id,),
            ).fetchall()
        return list(map(_as_dict, rows))
