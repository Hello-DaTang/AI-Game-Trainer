# AI Game Trainer v0.1.3 — Windows 便携版

这一版不需要在本机安装 Python、Node.js、Rust、Git 或 pip。

## 使用步骤
1. 解压整个 ZIP，例如到 D:\Tools\AI-Game-Trainer。
2. 双击 AI-Game-Trainer.exe。不能单独移动这个 exe；同目录的 _internal 运行库是必需的。
3. 控制台窗口会保持打开，并自动弹出浏览器 http://127.0.0.1:8765 。关闭控制台会退出程序。
4. 修改器保存的配置、SQLite 和 CE 表位于 %LOCALAPPDATA%\AI-Game-Trainer，升级时不会随着程序文件夹清理。

## 零学习一键测试（修复版）

完成 CE Bridge 加载后，回到浏览器首页，点击「开始一键实测」。软件会自动启动内置 AITrainerDemo.exe，并通过 CE 完成 123 → 777 → 123 的内存读写校验，结束后关闭测试进程。你不必手动扫描地址，也不需要打开真实游戏。

## Cheat Engine 的准备
这版仍然需要自行安装 Cheat Engine 主程序，不随 ZIP 附带。

1. 运行 Cheat Engine。在 File → Execute Script 加载 CE-Bridge\ce_mcp_bridge.lua。
2. 如果找不到该菜单，进入 Table → Show Cheat Table Lua Script，执行：
   dofile([[D:\Tools\AI-Game-Trainer\CE-Bridge\ce_mcp_bridge.lua]])
   （请改成实际路径）
3. 在 CE 中手动选择并附加到正在运行的离线单机游戏 EXE。
4. 回到网页左下方检查 CE Bridge 连接状态。
5. 在 CE 中扫描/分析并验证一条修改记录，回到网页保存为按钮。下次可从 CT 重新加载。

## 注意
- 此版提供持久化及一键开启/关闭，尚未集成 Codex 自然语言 AI Agent。
- 游戏重启后可能重新定位，游戏更新或地址失效时不保证修改成功。
- 修改行为应仅用于有权限修改的本地离线单机程序；不提供反作弊绕过或内核隐藏。
- 本程序没有代码签名，请仅从官方 Releases 下载并核对随包提供的 SHA256 文件。若杀毒软件报警，请先验证来源，不要贸然关闭防护。
- 如果端口 8765 已被占用，请关闭上一个进程，或从命令行运行 AI-Game-Trainer.exe --port 8766。
- 本程序启动的是本地网页控制台，不是独立原生 GUI。
- 如需故障排查，保留黑色控制台中的错误信息反馈给开发者。

项目与源码：https://github.com/Hello-DaTang/AI-Game-Trainer
