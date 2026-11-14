"""A one-click read/write smoke test against an owned, harmless Windows process.

Never writes to the user's game or an arbitrary executable. The demo process
is started by us and terminated after the test. CE's previous attachment is
restored when possible. This is not a game cheat or an AI discovery agent.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .bridge import BridgeError


class DiagnosticError(RuntimeError):
    """Local demo target or CE test failed."""


def demo_exe_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "Tools" / "AITrainerDemo.exe"
    return Path(__file__).resolve().parents[1] / "bin" / "AITrainerDemo.exe"


def verify_memory_roundtrip(bridge, pid: int, address: str) -> dict:
    """Attach to our freshly spawned process; test and restore a DWORD."""
    bridge.call("open_process", {"process_id_or_name": pid})
    info = bridge.call("get_opened_process_id")
    if int(info.get("process_id", 0)) != pid:
        raise DiagnosticError("Cheat Engine 未能附加到自动测试进程")

    args = {"address": address, "type": "dword"}
    original = bridge.call("read_integer", args).get("value")
    if original != 123:
        raise DiagnosticError(f"测试初始值不正确：期望 123，得到 {original!r}")

    changed_value = 777
    try:
        bridge.call("write_integer", {**args, "value": changed_value})
        actual = bridge.call("read_integer", args).get("value")
        if actual != changed_value:
            raise DiagnosticError(
                f"内存写入校验未通过：期望 {changed_value}，得到 {actual!r}"
            )
    finally:
        # The only target is the throwaway process created by this diagnostic.
        bridge.call("write_integer", {**args, "value": original})

    restored = bridge.call("read_integer", args).get("value")
    if restored != original:
        raise DiagnosticError("内存原值恢复失败")
    return {"initial": original, "changed": changed_value, "restored": restored}


def run_selftest(bridge, target: Path | None = None) -> dict:
    """Use the bundled demo process. No game/CT database is modified."""
    if os.name != "nt":
        raise DiagnosticError("一键 CE 实测仅支持 Windows")
    binary = Path(target) if target is not None else demo_exe_path()
    if not binary.is_file():
        raise DiagnosticError("缺少内置测试进程 AITrainerDemo.exe，请安装 v0.1.2 或更新版本的完整 ZIP")

    # Verify the CE bridge first, before touching any process.
    ping = bridge.call("ping")
    previous_pid = None
    try:
        info = bridge.call("get_opened_process_id")
        previous_pid = int(info.get("process_id") or 0) or None
    except BridgeError:
        # Fresh CE session with no process attached is expected.
        pass

    result = {}
    warnings = []
    with tempfile.TemporaryDirectory(prefix="ai-trainer-demo-") as folder:
        ready_file = Path(folder) / "ready.json"
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            [str(binary), "--ready-file", str(ready_file)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        try:
            deadline = time.monotonic() + 8.0
            while not ready_file.is_file():
                if process.poll() is not None:
                    raise DiagnosticError("测试进程启动失败，退出码：" + str(process.returncode))
                if time.monotonic() >= deadline:
                    raise DiagnosticError("等待自动测试进程启动超时")
                time.sleep(0.1)
            try:
                ready = json.loads(ready_file.read_text("utf-8"))
                pid = int(ready["pid"])
                address = ready["address"]
                if pid != process.pid or not isinstance(address, str) or not address.startswith("0x"):
                    raise ValueError("Fixture PID/address mismatch")
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                raise DiagnosticError("测试进程返回了无效的内存信息") from exc
            result = verify_memory_roundtrip(bridge, pid, address)
        finally:
            # Avoid leaving the fixture process running if anything fails.
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            if previous_pid is not None:
                try:
                    bridge.call("open_process", {"process_id_or_name": previous_pid})
                except BridgeError:
                    warnings.append("原来的 CE 进程附加状态未能恢复，请手动重新附加")

    return {
        "success": True,
        "bridge_version": ping.get("version", "unknown"),
        "initial": result["initial"],
        "changed": result["changed"],
        "restored": result["restored"],
        "steps": [
            "Cheat Engine 通信正常",
            "自动启动专用测试进程",
            "读取目标进程 DWORD：123",
            "写入并重新读取：777",
            "恢复原值：123",
            "自动关闭测试进程",
        ],
        "warnings": warnings,
        "note": "已验证 CE 内存读写链路；尚未测试 CT 跨重启或 AI 自动探索功能。",
    }
