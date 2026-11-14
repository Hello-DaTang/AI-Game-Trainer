# MVP 与后续路线

## v0.1 — 已编写，等待 Windows 实机验证

- Python 3.10+ stdlib localhost web UI
- SQLite 游戏与功能定义
- 直接对接 CE Bridge v12 的 JSON-RPC 命名管道
- 导出/导入 CT，按唯一 MemoryRecord.Description 创建按钮
- 目标 EXE 校验与记录状态校验
- Fake Bridge 模拟测试 + GitHub Actions

## v0.2 — 完成真实联调后

- 把运行时开关状态和异常恢复做得更严密
- 新建/删除游戏及功能、手动修复 CT、游戏版本 fingerprint
- 指针/AOB、脚本启停回滚校验、失败时事务式恢复
- 真实 Windows CE Bridge 适配测试记录
- 自动化安装、自检以及错误日志

## v0.3 — Agent 探索与人工验证

- Codex app-server 或 SDK 接入，隔离审批与实际执行
- 内存扫描与写入的操作计划、审计、用户确认
- 将探索中的临时数据自动导出到已验证 CT，明确用户验收
- 日常修改调用执行器而不是每次消耗 AI token

## v0.4 — 桌面产品

- Tauri + React 打包 Windows 应用
- 更完整的游戏库、快捷键与运行时状态检测
- 一键启动/关闭、备份/恢复、可选数据迁移

## 跨阶段准则

安全默认拒绝：无目标进程、多个同名进程、CE 未连接、CT 缺记录、开关失败，均不应该对未知地址进行写入。联网对战、反作弊绕过、驱动与 DBVM 均不在范围内。
