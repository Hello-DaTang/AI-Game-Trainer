"use strict";
const el = (id) => document.getElementById(id);
let currentGame = null;
let snapshot = {games: []};
let activeStates = {};

async function api(path, payload) {
  const options = payload === undefined ? {} : {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  };
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "操作失败");
  return result;
}
function notice(message, ok = false) {
  const node = el("notice");
  node.textContent = message;
  node.classList.remove("hidden");
  node.classList.toggle("ok", ok);
}
function clearNotice() { el("notice").classList.add("hidden"); }
async function reload() {
  snapshot = await api("/api/state");
  const games = snapshot.games;
  activeStates = Object.fromEntries(games.flatMap((game) =>
    game.features.map((feature) => [feature.id, feature.enabled])));
  el("games").replaceChildren();
  games.forEach((g) => {
    const btn = document.createElement("button");
    btn.className = "game-nav" + (g.id === currentGame ? " selected" : "");
    btn.textContent = "◈  " + g.name;
    btn.addEventListener("click", () => { currentGame = g.id; clearNotice(); render(); });
    el("games").append(btn);
  });
  if (!currentGame && games.length) currentGame = games[0].id;
  if (currentGame && !games.some((g) => g.id === currentGame))
    currentGame = games.length ? games[0].id : null;
  render();
}
function render() {
  const game = snapshot.games.find((g) => g.id === currentGame);
  const selected = !!game;
  el("welcome").classList.toggle("hidden", selected);
  el("workspace").classList.toggle("hidden", !selected);
  el("page-title").textContent = selected ? "游戏修改工作台" : "管理你自己的游戏修改器";
  el("breadcrumb").textContent = selected ? game.name : "开始";
  el("page-intro").textContent = selected
    ? "已保存的修改功能将保留在本地。只有在你点击时才会尝试修改游戏进程。"
    : "把通过 Cheat Engine 验证过的功能保存为可复用按钮。游戏重启后仍能从 CT 文件中恢复。";
  document.querySelectorAll(".game-nav").forEach((btn, i) => {
    btn.classList.toggle("selected", snapshot.games[i].id === currentGame);
  });
  if (!game) return;
  el("game-name").textContent = game.name;
  el("game-exe").textContent = game.exe;
  el("table-status").textContent = game.has_table ? "CT 已保存" : "未保存 CT";
  el("table-status").classList.toggle("ready", game.has_table);
  const host = el("features");
  host.replaceChildren();
  if (!game.features.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "暂无已保存的修改功能。先在 CE 中制作一条记录，再从下面导入。";
    host.append(empty);
  }
  game.features.forEach((feature) => {
    const row = document.createElement("div");
    row.className = "feature-row";
    const info = document.createElement("div");
    const name = document.createElement("div");
    name.className = "feature-name";
    name.textContent = feature.title;
    const sub = document.createElement("div");
    sub.className = "feature-sub";
    sub.textContent = "CE 记录：" + feature.record_description;
    info.append(name, sub);
    const toggle = document.createElement("button");
    const enabled = !!activeStates[feature.id];
    toggle.className = "switch" + (enabled ? " active" : "");
    toggle.setAttribute("aria-label", enabled ? "关闭 " + feature.title : "开启 " + feature.title);
    toggle.setAttribute("aria-pressed", String(enabled));
    toggle.title = enabled ? "关闭" : "开启";
    toggle.addEventListener("click", async () => {
      toggle.disabled = true;
      try {
        const result = await api("/api/features/toggle", {
          feature_id: feature.id, enabled: !activeStates[feature.id]
        });
        activeStates[feature.id] = result.enabled;
        notice(feature.title + "：" + (result.enabled ? "已开启" : "已关闭"), true);
      } catch (err) { notice(err.message); }
      finally { toggle.disabled = false; render(); }
    });
    row.append(info, toggle);
    host.append(row);
  });
}
async function refreshBridge() {
  try {
    const status = await api("/api/bridge");
    el("bridge-dot").classList.toggle("connected", !!status.connected);
    el("bridge-status").textContent = status.connected ? "Cheat Engine 已连接" : "Cheat Engine 未连接";
    el("bridge-status").title = status.message || "";
  } catch (err) { el("bridge-status").textContent = "Bridge 检查失败"; }
}
el("new-game").addEventListener("click", () => {
  currentGame = null;
  el("welcome").classList.remove("hidden");
  el("workspace").classList.add("hidden");
  el("page-title").textContent = "添加游戏";
  el("breadcrumb").textContent = "添加游戏";
  clearNotice();
});
el("game-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const game = await api("/api/games", data);
    currentGame = game.id;
    event.currentTarget.reset();
    await reload();
    notice("已添加游戏，请先在 Cheat Engine 中附加此进程。", true);
  } catch (err) { notice(err.message); }
});
el("read-records").addEventListener("click", async () => {
  if (!currentGame) return;
  try {
    const result = await api("/api/records?game_id=" + encodeURIComponent(currentGame));
    const select = el("record-options");
    select.replaceChildren();
    result.records.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.description;
      opt.textContent = r.description;
      select.append(opt);
    });
    el("record-hint").textContent = "读取到 " + result.records.length + " 条记录";
    el("capture-form").classList.toggle("hidden", !result.records.length);
    if (!result.records.length) notice("CE 当前地址列表为空，先创建一条有效记录。");
    else clearNotice();
  } catch (err) { notice(err.message); }
});
el("capture-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  try {
    await api("/api/features/capture", {...data, game_id: currentGame});
    el("capture-form").classList.add("hidden");
    el("record-hint").textContent = "";
    await reload();
    notice("已保存完整 CT 表与修改按钮。下次启动游戏可以直接点击开关。", true);
  } catch (err) { notice(err.message); }
});
el("refresh-bridge").addEventListener("click", refreshBridge);
reload().catch((err) => notice(err.message));
refreshBridge();
