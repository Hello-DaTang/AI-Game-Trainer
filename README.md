# AI Game Trainer

## 免安装下载（Windows x64）

**优先推荐 [GitHub Releases](https://github.com/Hello-DaTang/AI-Game-Trainer/releases)**：下载 AI-Game-Trainer-Windows-x64.zip → 完整解压 → 双击 AI-Game-Trainer.exe，即可打开本地控制台，无须在电脑上安装 Python、Git、Node.js、Rust 或 pip。

ZIP 包内包含 CE-Bridge/ce_mcp_bridge.lua，仍需单独安装 Cheat Engine 并手动加载 Lua Bridge。详见 ZIP 内的《使用说明.md》。本版本仍是修改记录持久化 MVP，**没有内嵌 Codex 对话 Agent**。

在 Cheat Engine + AI 的探索阶段制作修改功能，验证满意后保存为游戏专属按钮。下次进入单机游戏，直接点击按钮即可调用已经保存的 CE 修改记录。

> **当前版本：0.1.3，开发验证版。** 已实现游戏库、CE Bridge 探活、从 CE 捕获地址列表记录、将整张 CE 表保存为 .CT、重新载入后开启/关闭指定记录、SQLite 持久化、本地网页控制台。**尚未集成内置自然语言聊天或 Codex SDK，已提供 Windows 免 Python 便携包，但仍未提供 Tauri 安装包。** Agent 可以在外部 Codex + CE MCP 中探索，再把结果导入本软件。不能保证任何游戏中的修改成功或跨版本稳定。

## 不用学习 CE 的一键实测（v0.1.3）

启动 CE 并加载 Lua Bridge 后，打开本程序页面，点击 **「开始一键实测」**。软件会自动运行随包测试进程、由 CE 读取数值 123、改写为 777、再次读取确认、恢复成 123 后退出。不会操作你添加的真实游戏，也不需要手动做内存扫描。

通过说明基础内存读写通路正常，**不能代表 AI 自动探索或 CT 复用已验证**。

## 架构

- Windows Cheat Engine 7.x，加载上游 Lua Bridge（版本 12.0.0 / wire v99）。
- Python 3.10+ 标准库 HTTP 服务与 SQLite：不用 Node/Rust 就能运行第一阶段 UI。
- 本地管理页面：127.0.0.1:8765；数据库位于 %LOCALAPPDATA%\AI-Game-Trainer\trainer.sqlite3；CE 表位于其 tables 目录。
- 默认 Windows Named Pipe；可切换到仅监听 127.0.0.1 的 TCP Relay。
- 上游 CE Bridge **不在此仓库中复制**，通过脚本固定版本下载到 vendor/。

## Windows 从零开始（建议装在 D: 盘）

先确保安装 **Git、Python 3.10 或更新版本，以及 Cheat Engine**。使用 PowerShell：

~~~powershell
Set-Location D:\
git clone https://github.com/Hello-DaTang/AI-Game-Trainer.git
Set-Location .\AI-Game-Trainer
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
py -m pip install -r requirements-windows.txt
~~~

然后按顺序：

1. 启动 Cheat Engine（本阶段**不要启动 DBVM/内核工具**）。
2. CE 顶部菜单选择 File → Execute Script，加载 vendor\cheatengine-mcp-bridge\MCP_Server\ce_mcp_bridge.lua。正确加载后 Lua 日志包含 CE_MCP_Bridge_v99。若该菜单不存在，可在 CE Table → Show Cheat Table Lua Script 中执行 dofile 的完整绝对路径（使用双中括号 Lua 字符串）。
3. 启动你的离线单机游戏，在 CE 中通过进程列表**附加到这个游戏的 EXE**。
4. 在 PowerShell 执行：

~~~powershell
py -m trainer
~~~

浏览器会自动打开 http://127.0.0.1:8765 。若没有自动打开，手动访问该地址。

### 第一次保存一个按钮

1. 在浏览器添加游戏，填入游戏进程文件名，例如 mygame.exe。
2. 在 CE 中完成扫描/分析；验证成功后在 CE 地址列表创建一个唯一描述的记录（例如 Player Stamina）。对于开关功能，建议使用带 [ENABLE]/[DISABLE] 的 Auto Assembler 记录。
3. 回到浏览器：读取 CE 记录 → 选择记录 → 给按钮命名 → 保存。
4. 此时软件把 CE 当前表全部保存为 CT 文件，并在 SQLite 中登记按钮。需要保存第二个按钮时请先加载**原来的 CT**，在原表中增加记录后再保存；软件会拒绝删除已登记记录的覆盖操作。
5. 关闭游戏并重启。再启动游戏、CE 与 Bridge 后，在网页点击按钮；软件检查目标进程，重载 CT，并切换对应 CE MemoryRecord 的 Active 状态。

**重要区别：** 按钮的关闭表示取消 CE 记录的激活/冻结。它**不保证**已更改的金币、存档或游戏机制完全复原；具体取决于 CT 脚本的 Disable 实现。保存了错误的绝对地址不会自动变成稳定指针，必须在 CE 中采用可靠指针链、AOB 或其他经验证的定位技术。

### 与 Codex Agent 配合

可以在原生 Windows Codex CLI 中另外配置 CE MCP（对应 bootstrap 下载的同一份脚本）：

~~~toml
[mcp_servers.cheatengine]
command = "python"
args = ['D:\AI-Game-Trainer\vendor\cheatengine-mcp-bridge\MCP_Server\mcp_cheatengine.py']
~~~

上面的盘符路径仅是示例，需要替换为实际绝对路径。安装该 MCP 的依赖：

~~~powershell
py -m pip install -r .\vendor\cheatengine-mcp-bridge\MCP_Server\requirements.txt
~~~

你可让 Codex 在允许的本地测试进程上探索，并把经验证的逻辑保存成 CE 地址列表记录。**目前对话仍在 Codex 外部进行**；这不是嵌入式 AI 聊天。若 Codex 在 WSL 中运行，请按照上游 README 的 TCP Relay 方案；Windows 命名管道不能直接跨 WSL 访问。

### 可选 TCP Relay

用上游的 ce_tcp_relay.py（Windows）监听 loopback：

~~~powershell
py .\vendor\cheatengine-mcp-bridge\MCP_Server\ce_tcp_relay.py --host 127.0.0.1 --port 9876
$env:TRAINER_CE_TRANSPORT = "tcp"
py -m trainer
~~~

不要将 TCP Relay 绑定到公网或不可信网络接口，它能控制 Cheat Engine。

## 当前限制及风险

- 仅用于你有权限修改的**本地离线单机程序**。不提供反作弊绕过、联机游戏服务器数值修改或内核隐藏能力。
- 页面按钮需要 CE 和 Lua Bridge 处于运行状态。无 CE 时仍能打开页面及查看已保存的按钮。
- 只能在发现唯一匹配 EXE 的进程时运行，且首次切换会加载整张保存的 CT，可能覆盖 CE 当前未保存的表。
- 同一张表内的记录描述必须唯一；不要将运行时绝对内存地址当成永久有效的标识。
- 此版本不会自动识别游戏更新或修复失效的指针/AOB。跨重启持久化的是 CT 和功能定义，**不是成功修改的承诺**。
- 上游 CE Bridge v12 的底层脚本具有 Lua 执行能力，所以仅加载可信任的 CT 与 Lua 文件；定期备份游戏存档。
- 默认服务仅在 127.0.0.1 上监听；不会将任何训练数据/游戏内存发往云端。

## 开发测试

~~~powershell
py -m unittest discover -s tests -v
py -m compileall -q trainer
~~~

测试使用模拟 CE Bridge，不会触碰真实游戏。真实 Windows + CE 联调需在本机完成。具体阶段规划见 docs/ROADMAP.md。
