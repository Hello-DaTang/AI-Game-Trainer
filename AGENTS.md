# Developer guide for AI Game Trainer

Goal: a user-approved, reusable, local-first trainer. The first milestone is a Windows Python UI and CE Bridge integration; native Tauri/React is deferred until the CE feedback loop works on real machines.

## Local test
- python -m unittest discover -s tests -v
- python -m compileall -q trainer
- On Windows, py -m pip install -r requirements-windows.txt and py -m trainer

## Contract with CE
- Dependency: miscusi-peek/cheatengine-mcp-bridge pinned at 6bd7ce90479250a9b4b75e7944df9c105ecb2572.
- Named pipe: \\.\pipe\CE_MCP_Bridge_v99; request/response: little-endian uint32 length then UTF-8 JSON-RPC.
- IMPORTANT: Lua v12 accepts filename for load_table/save_table, and process_id_or_name for open_process. Docs use other names in places.
- IMPORTANT: set_memory_record_value in Lua v12 ignores freeze. For active/inactive use a vetted evaluate_lua snippet with a numeric record ID already returned by CE.
- The repository does not vendor/redistribute upstream code. bootstrap.ps1 checks out upstream under ignored vendor/.

## Safety and robustness
- Do not enable kernel, DBVM, anti-cheat evasion, or online multiplayer modifications.
- Never accept arbitrary Lua, shell commands, or bridge method names from the HTTP client.
- Bind HTTP to loopback and verify Host/Origin.
- A saved feature must be associated with one exact game executable; refuse ambiguous multiple matching processes.
- Never assume a runtime memory address persists across restarts. Preserve CE .CT structures, verify target and record before mutation; if invalid, fail closed.
- Do not leak secrets, save games or generated CT tables into Git.
- Tests must run without Cheat Engine; use a fake CE bridge.
- Favor Windows D: drive for checkout and dev tools when documenting local installation.
