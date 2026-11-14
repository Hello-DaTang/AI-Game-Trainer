## AI Game Trainer v0.1.2 — CE 一键实测

你不需要手动操作 CE、学习扫描或打开真实游戏，就能验证内存读写链路。

新增：
- 首页和游戏工作台都有「开始一键实测」按钮。
- 随包提供独立、无网络功能的 Tools\AITrainerDemo.exe 测试进程。
- 自动通过已启动的 Cheat Engine Bridge：附加测试进程、读取 DWORD 123、改写为 777、校验、恢复 123，并结束测试进程。
- 尝试恢复 CE 原先附加的进程；如果恢复失败会给出提示。
- 内存修改不接触用户游戏，也不会更改游戏库和已保存 CT。
- 扩展自动化测试与 Windows 打包的示例 EXE 启动验证。

安装：下载 AI-Game-Trainer-Windows-x64.zip，完整解压，运行 AI-Game-Trainer.exe；保持 Cheat Engine 7.7 与其 Lua Bridge 运行，在首页点击「开始一键实测」。

此版本验证的是 CE 通信和读写，不是自然语言 AI Agent 或 CT 跨重启测试。Cheat Engine 主程序仍需单独安装。本项目仅面向有权修改的离线单机测试程序。
