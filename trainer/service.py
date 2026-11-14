"""Business operations: capture a CE table and replay verified, named records.

The upstream v12 Lua code expects filename (not path) for load_table/save_table,
and its set_memory_record_value ignores the documented freeze parameter.
For switching record.Active we therefore use a fixed Lua snippet with a numeric
record ID obtained from CE, never user-submitted Lua.
"""
from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path

from .bridge import BridgeError, CEBridge
from .store import Store, StoreError


def default_data_dir() -> Path:
    base = os.environ.get("TRAINER_DATA_DIR")
    if base:
        return Path(base).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AI-Game-Trainer"
    return Path.home() / ".local" / "share" / "ai-game-trainer"


class TrainerService:
    def __init__(self, data_dir: Path | None = None, bridge=None):
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "tables").mkdir(parents=True, exist_ok=True)
        self.store = Store(self.data_dir / "trainer.sqlite3")
        self.bridge = bridge or CEBridge()
        self._lock = threading.RLock()
        self._loaded = None

    def table_path(self, game_id: str) -> Path:
        self.store.game(game_id)
        return (self.data_dir / "tables" / (game_id + ".CT")).resolve()

    def snapshot(self) -> dict:
        games = self.store.games()
        return {
            "games": [
                {**game, "features": self.store.features(game["id"]),
                 "has_table": self.table_path(game["id"]).is_file()}
                for game in games
            ],
            "data_dir": str(self.data_dir),
        }

    def status(self) -> dict:
        try:
            reply = self.bridge.call("ping")
            return {"connected": True, "version": reply.get("version"), "message": reply.get("message")}
        except BridgeError as exc:
            return {"connected": False, "message": str(exc)}

    def _target_pid(self, game: dict) -> int:
        result = self.bridge.call("get_process_list")
        matches = [
            p for p in result.get("processes", [])
            if str(p.get("name", "")).casefold().rsplit("\\", 1)[-1].casefold()
            == game["exe"].casefold()
        ]
        if not matches:
            raise StoreError("未检测到 " + game["exe"] + "，请先启动对应的单机游戏")
        if len(matches) != 1:
            raise StoreError("发现同名进程多于一个；当前版本禁止自动选择进程")
        return int(matches[0]["pid"])

    def _attached_to(self, pid: int):
        result = self.bridge.call("get_opened_process_id")
        if int(result.get("process_id", 0)) != pid:
            raise StoreError("Cheat Engine 当前连接的不是该游戏，请在 CE 中先选择正确进程")

    def _records(self):
        result = self.bridge.call("get_address_list", {"offset": 0, "limit": 1000})
        if int(result.get("total", len(result.get("records", [])))) > 1000:
            raise StoreError("CE 表超过 1000 条记录；当前版本不支持自动匹配")
        return result.get("records", [])

    def records(self, game_id: str):
        with self._lock:
            game = self.store.game(game_id)
            self._attached_to(self._target_pid(game))
            return [
                {"id": r.get("id"), "description": r.get("description"),
                 "enabled": bool(r.get("enabled"))}
                for r in self._records() if r.get("description")
            ]

    def capture(self, game_id: str, title: str, description: str) -> dict:
        """Save the entire current CE table after validating all referenced records."""
        with self._lock:
            game = self.store.game(game_id)
            self._attached_to(self._target_pid(game))
            records = self._records()
            descriptions = [r.get("description") for r in records]
            if descriptions.count(description) != 1:
                raise StoreError("CE 表中必须有且仅有一条同名记录：" + description)
            for saved in self.store.features(game_id):
                if descriptions.count(saved["record_description"]) != 1:
                    raise StoreError("CE 当前表缺少已保存功能：" + saved["record_description"] + "；请先加载旧表再追加")
            if any(f["record_description"] == description for f in self.store.features(game_id)):
                raise StoreError("这条 CE 记录已经保存过")
            if not title.strip() or len(title.strip()) > 128:
                raise StoreError("功能名称需要 1–128 个字符")
            target = self.table_path(game_id)
            staging = target.with_name(target.stem + ".pending.CT")
            try:
                self.bridge.call("save_table", {"filename": str(staging)})
                if not staging.is_file() or staging.stat().st_size == 0:
                    raise StoreError("CE 没有生成有效 CT 文件")
                staging.replace(target)
                new_feature = self.store.add_feature(game_id, title, description)
            finally:
                staging.unlink(missing_ok=True)
            self._loaded = None
            return new_feature

    def toggle(self, feature_id: str, enabled: bool):
        if type(enabled) is not bool:
            raise StoreError("enabled 必须为 true 或 false")
        with self._lock:
            feature = self.store.feature(feature_id)
            game = self.store.game(feature["game_id"])
            path = self.table_path(game["id"])
            if not path.is_file():
                raise StoreError("此游戏尚未保存 CT 文件")
            pid = self._target_pid(game)
            table_key = (game["id"], pid, path.stat().st_mtime_ns)
            if self._loaded != table_key:
                self.bridge.call("open_process", {"process_id_or_name": pid})
                self._attached_to(pid)
                self.bridge.call("load_table", {"filename": str(path), "merge": False})
                self._loaded = table_key
            else:
                self._attached_to(pid)
            matches = [r for r in self._records() if r.get("description") == feature["record_description"]]
            if len(matches) != 1:
                raise StoreError("CT 中找不到唯一对应的记录，请检查游戏更新及 CT 文件")
            record_id = int(matches[0]["id"])
            if record_id < 0 or record_id > 2**31 - 1:
                raise StoreError("无效的 CE 记录 ID")
            # Lua expression contains only a checked integer, never raw client input.
            expression = (
                "local r=getAddressList():getMemoryRecordByID(" + str(record_id) + "); "
                "if not r then error('record not found') end; "
                "r.Active=" + ("true" if enabled else "false") + "; "
                "return tostring(r.Active)"
            )
            self.bridge.call("evaluate_lua", {"code": expression})
            actual = self.bridge.call("get_memory_record", {"id": record_id}).get("record", {})
            if bool(actual.get("enabled")) != enabled:
                raise BridgeError("CE 未能切换记录状态；按钮状态未更新")
            return {"feature_id": feature_id, "enabled": enabled, "process_id": pid}
