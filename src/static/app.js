"use strict";

// ---------- helpers ----------

const MEALS = { breakfast: "Завтрак", lunch: "Обед", dinner: "Ужин" };
const WEEKDAYS = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];
const STORES = { "wolt-market-batumi": "Wolt Market Batumi", "red-market-meat-store": "Red Market (мясо)" };
const CATEGORIES = {
  breakfast: "Завтраки", soup: "Супы", main: "Основные блюда", salad: "Салаты", snack: "Выпечка и закуски", dessert: "Десерты",
};
const APPLIANCES = { stove: "плита", air_fryer: "аэрогриль", none: "без готовки" };
const MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
const MENU_STATUS = { draft: "Черновик", awaiting_order: "Ждёт заказа", ordered: "Заказано" };

const view = document.getElementById("view");
let me = null; // the signed-in user: { id, login }

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function api(path, options = {}) {
  const init = { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } };
  if (init.body && typeof init.body !== "string") init.body = JSON.stringify(init.body);
  const resp = await fetch(path, init);
  if (!resp.ok) {
    let detail = resp.statusText;
    try { detail = (await resp.json()).detail || detail; } catch (_) { /* not json */ }
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; "); // validation errors
    const error = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    error.status = resp.status;
    if (resp.status === 401 && !path.startsWith("/api/v1/auth/")) { me = null; authView(); } // signed out meanwhile
    throw error;
  }
  return resp.status === 204 ? null : resp.json();
}

function isoDate(d) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
function parseDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}
function addDays(iso, n) {
  const d = parseDate(iso);
  d.setDate(d.getDate() + n);
  return isoDate(d);
}
function today() { return isoDate(new Date()); }
function dayTitle(iso) {
  const d = parseDate(iso);
  const rel = { [today()]: "Сегодня", [addDays(today(), 1)]: "Завтра", [addDays(today(), -1)]: "Вчера" }[iso];
  const date = `${WEEKDAYS[d.getDay()]}, ${d.getDate()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
  return rel ? `${rel} · ${date}` : date;
}

function period(first, last) {
  const [a, b] = [parseDate(first), parseDate(last)];
  return a.getMonth() === b.getMonth()
    ? `${a.getDate()}–${b.getDate()} ${MONTHS[b.getMonth()]}`
    : `${a.getDate()} ${MONTHS[a.getMonth()]} – ${b.getDate()} ${MONTHS[b.getMonth()]}`;
}

function fmtAmount(amount, unit) {
  if (amount == null) return "";
  if (unit === "pcs") return `${+amount.toFixed(1)} шт`;
  const [big, small] = unit === "g" ? ["кг", "г"] : ["л", "мл"];
  if (amount >= 1000) return `${+(amount / 1000).toFixed(2)}`.replace(".", ",") + ` ${big}`;
  return `${Math.round(amount)} ${small}`;
}
const UNITS = { g: "г", ml: "мл", pcs: "шт" };
function fmtNumber(n) { return String(+n.toFixed(2)).replace(".", ","); }
function parseNumber(text) { return text.trim() === "" ? 0 : Number(text.trim().replace(",", ".")); }
function fmtMoney(tetri) { return `${(tetri / 100).toFixed(2).replace(".", ",")} ₾`; }
function fmtClock(seconds) {
  const s = Math.max(0, Math.ceil(seconds));
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function showError(err) {
  view.innerHTML = `<div class="error">Не получилось: ${esc(err.message || err)}</div>`;
}

// ---------- timers ----------

const Timers = (() => {
  const KEY = "eaty.timers";
  let list = [];
  try { list = JSON.parse(localStorage.getItem(KEY)) || []; } catch (_) { list = []; }
  let ticker = null;
  let audio = null;
  let beepLoop = null;
  let wakeLock = null;
  const tray = document.getElementById("timers");

  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (_) { /* private mode */ } };
  const left = (t) => (t.pausedLeft != null ? t.pausedLeft : (t.endAt - Date.now()) / 1000);

  function unlockAudio() {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      if (audio.state === "suspended") audio.resume();
    } catch (_) { audio = null; }
  }
  function beep() {
    if (!audio) return;
    [0, 0.25, 0.5].forEach((offset) => {
      const osc = audio.createOscillator();
      const gain = audio.createGain();
      osc.frequency.value = 880;
      gain.gain.value = 0.25;
      osc.connect(gain).connect(audio.destination);
      osc.start(audio.currentTime + offset);
      osc.stop(audio.currentTime + offset + 0.15);
    });
  }
  async function keepAwake(on) {
    try {
      if (on && !wakeLock && "wakeLock" in navigator) {
        wakeLock = await navigator.wakeLock.request("screen");
        wakeLock.addEventListener("release", () => { wakeLock = null; });
      } else if (!on && wakeLock) {
        await wakeLock.release();
        wakeLock = null;
      }
    } catch (_) { /* needs https or a visible page */ }
  }

  function ring(t) {
    t.ringing = true;
    save();
    if (navigator.vibrate) navigator.vibrate([400, 150, 400, 150, 800]);
    if ("Notification" in window && Notification.permission === "granted") {
      try { new Notification("Готово!", { body: t.label, tag: t.id }); } catch (_) { /* mobile needs SW */ }
    }
    if (!beepLoop) { beep(); beepLoop = setInterval(beep, 1500); }
  }

  function tick() {
    let anyRunning = false;
    for (const t of list) {
      if (t.pausedLeft == null && !t.ringing) {
        if (left(t) <= 0) ring(t); else anyRunning = true;
      }
    }
    if (!list.some((t) => t.ringing) && beepLoop) { clearInterval(beepLoop); beepLoop = null; }
    keepAwake(anyRunning || list.some((t) => t.ringing));
    document.title = list.some((t) => t.ringing) ? "⏰ Готово! — eaty" : "eaty";
    render();
    if (!list.length && ticker) { clearInterval(ticker); ticker = null; }
  }

  function render() {
    tray.hidden = !list.length;
    tray.innerHTML = list.map((t) => `
      <div class="timer ${t.ringing ? "ringing" : ""}" data-id="${esc(t.id)}">
        <span class="clock">${t.ringing ? "0:00" : fmtClock(left(t))}</span>
        <span class="label">${esc(t.label)}</span>
        ${t.ringing ? `<button class="primary" data-act="stop">Стоп</button>` : `
          <button class="ghost" data-act="plus">+1 мин</button>
          <button class="ghost" data-act="${t.pausedLeft != null ? "resume" : "pause"}">${t.pausedLeft != null ? "▶" : "❚❚"}</button>
          <button class="ghost" data-act="stop">✕</button>`}
      </div>`).join("");
    document.querySelectorAll("[data-timer-key]").forEach((btn) => {
      const t = list.find((x) => x.key === btn.dataset.timerKey);
      btn.textContent = t ? (t.ringing ? "Готово!" : `⏱ ${fmtClock(left(t))}`) : `▶ ${fmtClock(+btn.dataset.seconds)}`;
    });
  }

  tray.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    const t = list.find((x) => x.id === btn.closest(".timer").dataset.id);
    if (!t) return;
    const act = btn.dataset.act;
    if (act === "stop") list = list.filter((x) => x !== t);
    if (act === "plus") { if (t.pausedLeft != null) t.pausedLeft += 60; else t.endAt += 60000; }
    if (act === "pause") t.pausedLeft = left(t);
    if (act === "resume") { t.endAt = Date.now() + t.pausedLeft * 1000; t.pausedLeft = null; }
    save();
    tick();
  });

  function start(key, label, seconds) {
    unlockAudio();
    if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
    const existing = list.find((t) => t.key === key);
    if (existing && !existing.ringing) return; // already running: the button shows the countdown
    list = list.filter((t) => t.key !== key);
    list.push({ id: `${key}:${Date.now()}`, key, label, endAt: Date.now() + seconds * 1000, pausedLeft: null, ringing: false });
    save();
    if (!ticker) ticker = setInterval(tick, 250);
    tick();
  }

  if (list.length) ticker = setInterval(tick, 250);
  render();
  return { start, render };
})();

// ---------- views ----------

async function dayView(day) {
  const [plan, recipes] = await Promise.all([api(`/api/v1/plan?start=${day}&days=1`), api("/api/v1/recipes")]);
  view.innerHTML = `
    <div class="daynav">
      <button class="ghost" data-go="${addDays(day, -1)}">‹</button>
      <h1>${esc(dayTitle(day))}</h1>
      <button class="ghost" data-go="${addDays(day, 1)}">›</button>
    </div>
    <div class="stack">
      ${Object.keys(MEALS).map((meal) => mealCard(day, meal, plan.find((p) => p.meal === meal))).join("")}
    </div>
    ${day !== today() ? `<p><a href="#/">← к сегодняшнему дню</a></p>` : ""}`;
  view.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => { location.hash = `#/day/${b.dataset.go}`; }));
  view.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", (e) => {
    e.preventDefault();
    editMeal(day, b.dataset.edit, plan.find((p) => p.meal === b.dataset.edit), recipes);
  }));
}

function mealCard(day, meal, row) {
  const x = row && row.multiplier > 1 ? `<span class="badge">×${row.multiplier}</span>` : "";
  const cooked = row && row.cooked_at ? `<span class="badge ok">готово</span>` : "";
  const title = row ? (row.title || row.note || "—") : "Ничего не запланировано";
  const sub = row && row.title && row.note ? `<div class="muted small">${esc(row.note)}</div>` : "";
  const body = `
    <div class="row between">
      <div class="grow">
        <div class="meal-label">${MEALS[meal]}</div>
        <div class="meal-title">${esc(title)}</div>
        ${sub}
      </div>
      ${x} ${cooked}
      <button class="ghost" data-edit="${meal}" aria-label="Изменить">✎</button>
    </div>`;
  if (row && row.recipe_id) {
    return `<a class="card ${row.cooked_at ? "cooked" : ""}" href="#/recipe/${row.recipe_id}?day=${day}&meal=${meal}&x=${row.multiplier}">${body}</a>`;
  }
  return `<div class="card">${body}</div>`;
}

function editMeal(day, meal, row, recipes) {
  const dlg = document.createElement("dialog");
  dlg.innerHTML = `
    <form method="dialog" class="stack">
      <h2>${MEALS[meal]} · ${esc(dayTitle(day))}</h2>
      <label class="small muted">Рецепт</label>
      <select name="recipe">
        <option value="">— без рецепта (остатки, кафе…) —</option>
        ${Object.entries(CATEGORIES).map(([category, label]) => {
          const options = recipes.filter((r) => r.category === category)
            .map((r) => `<option value="${r.id}" ${row && row.recipe_id === r.id ? "selected" : ""}>${esc(r.title)}</option>`);
          return options.length ? `<optgroup label="${label}">${options.join("")}</optgroup>` : "";
        }).join("")}
      </select>
      <label class="small muted">Сколько готовить</label>
      <select name="x">
        ${[1, 2, 3].map((n) => `<option value="${n}" ${row && +row.multiplier === n ? "selected" : ""}>×${n} (${n * 2} порции)</option>`).join("")}
      </select>
      <label class="small muted">Заметка</label>
      <input name="note" value="${esc(row ? row.note : "")}" placeholder="например: половина — на обед завтра">
      <div class="row between">
        <button value="cancel" class="ghost">Отмена</button>
        <button value="save" class="primary">Сохранить</button>
      </div>
    </form>`;
  document.body.appendChild(dlg);
  dlg.addEventListener("close", async () => {
    const form = dlg.querySelector("form");
    if (dlg.returnValue === "save") {
      try {
        await api(`/api/v1/plan/${day}/${meal}`, {
          method: "PUT",
          body: { recipe_id: form.recipe.value ? +form.recipe.value : null, multiplier: +form.x.value, note: form.note.value },
        });
        route();
      } catch (err) { alert(err.message); }
    }
    dlg.remove();
  });
  dlg.showModal();
}

async function recipeView(id, params) {
  let recipe = await api(`/api/v1/recipes/${id}`);
  const day = params.get("day");
  const meal = params.get("meal");
  let x = +(params.get("x") || 1);
  let planRow = null;
  if (day && meal) planRow = (await api(`/api/v1/plan?start=${day}&days=1`)).find((p) => p.meal === meal) || null;
  const usedUrl = `/api/v1/plan/${day}/${meal}/used`;
  let used = planRow && planRow.cooked_at ? await api(usedUrl) : [];
  const doneKey = `eaty.done.${id}.${day || ""}.${meal || ""}`;
  let done = [];
  try { done = JSON.parse(sessionStorage.getItem(doneKey)) || []; } catch (_) { done = []; }

  function render() {
    view.innerHTML = `
      <p class="small"><a href="${day ? `#/day/${day}` : "#/recipes"}">← ${day ? esc(dayTitle(day)) : "рецепты"}</a></p>
      <h1>${esc(recipe.title)}</h1>
      <div class="row">
        <span class="muted">${x * recipe.portions} порции · ${APPLIANCES[recipe.appliance] || recipe.appliance}</span>
        <span class="grow"></span>
        ${[1, 2].map((n) => `<button class="${n === x ? "primary" : ""}" data-x="${n}">×${n}</button>`).join("")}
      </div>
      ${x > 1 && recipe.batch_note ? `<p class="card small">${esc(recipe.batch_note)}</p>` : ""}
      <h2>Продукты</h2>
      <ul class="ingredients card">
        ${recipe.ingredients.map((i) => {
          const need = i.amount != null ? i.amount * x : null;
          const status = i.product_key == null ? "" : (i.have != null && i.have >= need ? "ok" : "missing");
          const amount = need != null ? fmtAmount(need, i.unit) : i.text_amount;
          return `<li>
            <span class="dot ${status}" title="${status === "ok" ? "есть дома" : status ? "дома не хватает" : ""}"></span>
            <span class="grow">${esc(i.name)}${i.note && x === 1 ? ` <span class="muted small">${esc(i.note)}</span>` : ""}</span>
            <span class="amount">${esc(amount)}</span>
          </li>`;
        }).join("")}
      </ul>
      <p class="muted small">Зелёная точка — дома хватает, красная — по данным «Дома» не хватает.</p>
      <h2>Готовим</h2>
      <div class="stack">
        ${recipe.steps.map((s) => `
          <div class="card step ${done.includes(s.position) ? "done" : ""}">
            <div class="num" data-done="${s.position}">${done.includes(s.position) ? "✓" : s.position + 1}</div>
            <div class="grow">
              <div class="text">${esc(s.text)}</div>
              ${s.heat ? `<div class="heat">🔥 ${esc(s.heat)}</div>` : ""}
              <div class="actions">
                ${s.timer_seconds ? `<button data-timer-key="${id}:${s.position}" data-seconds="${s.timer_seconds}" data-step="${s.position}"></button>` : ""}
                <button class="ghost" data-done="${s.position}">${done.includes(s.position) ? "Вернуть" : "Сделано"}</button>
              </div>
            </div>
          </div>`).join("")}
      </div>
      ${planRow && planRow.cooked_at ? `
        <h2>Списано из «Дома»</h2>
        ${used.length ? `<ul class="ingredients card">${used.map((u) => `
          <li><span class="grow">${esc(u.name)}</span><span class="amount">${esc(u.amount_text)}</span></li>`).join("")}
        </ul>` : `<p class="card small muted">Ничего не списано.</p>`}
        <p><button id="edit-used">Поправить списание</button></p>` : ""}
      ${planRow ? `<p><button class="${planRow.cooked_at ? "" : "primary"}" id="cooked">${planRow.cooked_at ? "Отменить «приготовлено»" : "Приготовлено — списать продукты"}</button></p>` : ""}`;

    view.querySelectorAll("[data-x]").forEach((b) => b.addEventListener("click", () => { x = +b.dataset.x; render(); }));
    view.querySelectorAll("[data-done]").forEach((b) => b.addEventListener("click", () => {
      const pos = +b.dataset.done;
      done = done.includes(pos) ? done.filter((p) => p !== pos) : [...done, pos];
      try { sessionStorage.setItem(doneKey, JSON.stringify(done)); } catch (_) { /* ignore */ }
      render();
    }));
    view.querySelectorAll("[data-timer-key]").forEach((b) => b.addEventListener("click", () => {
      const s = recipe.steps.find((st) => st.position === +b.dataset.step);
      Timers.start(b.dataset.timerKey, `${recipe.title} · шаг ${s.position + 1}`, s.timer_seconds);
    }));
    const cookedBtn = document.getElementById("cooked");
    if (cookedBtn) cookedBtn.addEventListener("click", async () => {
      cookedBtn.disabled = true;
      try {
        const rows = await api(`/api/v1/plan/${day}/${meal}/cooked`, { method: "POST", body: { cooked: !planRow.cooked_at } });
        planRow = rows.find((p) => p.meal === meal);
        if (planRow.cooked_at) location.hash = `#/day/${day}`; else render();
      } catch (err) { alert(err.message); cookedBtn.disabled = false; }
    });
    const editUsedBtn = document.getElementById("edit-used");
    if (editUsedBtn) editUsedBtn.addEventListener("click", async () => {
      try {
        const edited = await editUsed(used, usedUrl);
        if (!edited) return;
        used = edited;
        recipe = await api(`/api/v1/recipes/${id}`); // the dots show what's left at home
        render();
      } catch (err) { alert(err.message); }
    });
    Timers.render();
  }
  render();
}

// What a cooked meal really took: amounts in base units, 0 or ✕ means "not written off".
// Resolves with the saved write-off, or null if cancelled.
async function editUsed(used, url) {
  const products = await api("/api/v1/pantry");
  const dlg = document.createElement("dialog");
  const usedRow = (key, name, unit, amount) => `
    <div class="used-row" data-key="${esc(key)}" data-name="${esc(name)}">
      <span class="grow">${esc(name)}</span>
      <input inputmode="decimal" autocomplete="off" value="${amount == null ? "" : esc(fmtNumber(amount))}" aria-label="${esc(name)}, ${UNITS[unit]}">
      <span class="unit muted">${UNITS[unit]}</span>
      <button type="button" class="ghost" data-remove aria-label="Не списывать">✕</button>
    </div>`;
  dlg.innerHTML = `
    <form method="dialog" class="stack">
      <h2>Поправить списание</h2>
      <p class="small muted">Сколько ушло на самом деле. 0 или ✕ — не списывать.</p>
      <div class="used-rows">${used.map((u) => usedRow(u.key, u.name, u.base_unit, u.amount)).join("")}</div>
      <select></select>
      <div class="row between">
        <button type="button" class="ghost" data-cancel>Отмена</button>
        <button class="primary">Сохранить</button>
      </div>
    </form>`;
  const form = dlg.querySelector("form");
  const rows = dlg.querySelector(".used-rows");
  const add = dlg.querySelector("select");
  const fillAdd = () => {
    const taken = new Set([...rows.querySelectorAll("[data-key]")].map((r) => r.dataset.key));
    add.innerHTML = `<option value="">+ добавить продукт</option>` + products.filter((p) => !taken.has(p.key))
      .map((p) => `<option value="${esc(p.key)}">${esc(p.name)}</option>`).join("");
  };
  fillAdd();
  add.addEventListener("change", () => {
    const p = products.find((x) => x.key === add.value);
    if (!p) return;
    rows.insertAdjacentHTML("beforeend", usedRow(p.key, p.name, p.base_unit, null));
    fillAdd();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (e) => {
    if (!e.target.closest("[data-remove]")) return;
    e.target.closest("[data-key]").remove();
    fillAdd();
  });
  dlg.querySelector("[data-cancel]").addEventListener("click", () => dlg.close());
  document.body.appendChild(dlg);
  return new Promise((resolve) => {
    let saved = null;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const amounts = {};
      for (const row of rows.querySelectorAll("[data-key]")) {
        const input = row.querySelector("input");
        const value = parseNumber(input.value);
        if (!(value >= 0)) { alert(`${row.dataset.name}: не понимаю «${input.value}»`); input.focus(); return; }
        amounts[row.dataset.key] = value;
      }
      const btn = form.querySelector("button.primary");
      btn.disabled = true;
      try {
        saved = await api(url, { method: "PUT", body: { amounts } });
        dlg.close();
      } catch (err) { alert(err.message); btn.disabled = false; }
    });
    dlg.addEventListener("close", () => { dlg.remove(); resolve(saved); });
    dlg.showModal();
  });
}

async function recipesView(params) {
  const recipes = await api("/api/v1/recipes");
  let query = params.get("q") || "";
  view.innerHTML = `
    <h1>Рецепты</h1>
    <input id="search" type="search" placeholder="Поиск: курица, суп, аэрогриль…" value="${esc(query)}">
    <div id="recipe-list"></div>`;
  const list = document.getElementById("recipe-list");

  function render() {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    const found = recipes.filter((r) => {
      const text = `${r.title} ${CATEGORIES[r.category] || ""} ${APPLIANCES[r.appliance] || ""}`.toLowerCase();
      return words.every((w) => text.includes(w));
    });
    list.innerHTML = Object.entries(CATEGORIES).map(([category, label]) => {
      const rows = found.filter((r) => r.category === category);
      return rows.length ? `
        <h2>${label} <span class="muted small">${rows.length}</span></h2>
        <div class="card list">${rows.map((r) => `
          <a class="line row" href="#/recipe/${r.id}">
            <span class="grow">${esc(r.title)}</span>
            <span class="muted small">${esc(APPLIANCES[r.appliance] || "")}</span>
          </a>`).join("")}
        </div>` : "";
    }).join("") || `<p class="card">Ничего не нашлось</p>`;
  }

  document.getElementById("search").addEventListener("input", (e) => {
    query = e.target.value;
    history.replaceState(null, "", query ? `#/recipes?q=${encodeURIComponent(query)}` : "#/recipes");
    render();
  });
  render();
}

// The week tab: menus put together from the recipes. Draft (swap what you don't like) ->
// awaiting order (the list goes to Wolt, e.g. with Claude in the browser) -> ordered (the
// extension brought the orders back).
async function weekView() {
  const start = today();
  const menus = await api(`/api/v1/menus?since=${start}`);
  const orders = await Promise.all(menus.map((m) => (m.status === "awaiting_order"
    ? api(`/api/v1/menus/${m.id}/order?today=${start}`) : null)));
  const last = menus.length ? addDays(menus[menus.length - 1].last_day, 1) : start;
  const next = last > start ? last : start;
  const plan = menus.length ? [] : await api(`/api/v1/plan?start=${start}&days=7`);
  view.innerHTML = `
    <h1>Неделя</h1>
    ${menus.map((m, i) => menuSection(m, orders[i])).join("")}
    ${menus.length ? "" : planDays(plan, start)}
    <h2>Новое меню</h2>
    <div class="card stack">
      <div class="small muted">Рецепты подберутся из базы: на ужин блюдо ×2, вторая половина — обед на завтра.
        Что не понравится — замени ↻, потом утверди, и меню будет ждать заказа в Wolt.</div>
      <div class="row">
        <label class="small muted" for="menu-start">с</label>
        <input type="date" id="menu-start" value="${next}" min="${start}">
        <button class="primary" id="new-menu">Накидать</button>
      </div>
    </div>`;

  document.getElementById("new-menu").addEventListener("click", () =>
    menuAction(() => api("/api/v1/menus", { method: "POST", body: { start: document.getElementById("menu-start").value } })));
  view.querySelectorAll("[data-swap]").forEach((b) => b.addEventListener("click", () => {
    b.disabled = true;
    b.classList.add("spin");
    menuAction(() => api(`/api/v1/menus/${b.dataset.menu}/${b.dataset.swap}/swap`, { method: "POST" }));
  }));
  view.querySelectorAll("[data-reshuffle]").forEach((b) => b.addEventListener("click", () => {
    if (confirm("Подобрать всё меню заново? Замены пропадут.")) {
      menuAction(() => api("/api/v1/menus", { method: "POST", body: { start: b.dataset.reshuffle } }));
    }
  }));
  view.querySelectorAll("[data-status]").forEach((b) => b.addEventListener("click", () =>
    menuAction(() => api(`/api/v1/menus/${b.dataset.menu}/status`, { method: "PUT", body: { status: b.dataset.status } }))));
  view.querySelectorAll("[data-task]").forEach((b) => b.addEventListener("click", async () => {
    const order = orders[menus.findIndex((m) => m.id === +b.dataset.task)];
    if (await copyText(order.task)) {
      b.textContent = "Скопировано ✓";
      setTimeout(() => { b.textContent = "Скопировать задание для Claude"; }, 2500);
    } else showText("Задание для Claude", order.task);
  }));
  view.querySelectorAll("[data-sync]").forEach((b) => b.addEventListener("click", async () => {
    const status = view.querySelector(`[data-sync-status="${b.dataset.sync}"]`);
    b.disabled = true;
    b.textContent = "Синхронизирую…";
    status.textContent = "Забираю последние заказы из Wolt, это займёт до минуты.";
    const result = await syncWithWolt();
    if (result.error) { // also when orders were found but not imported
      status.textContent = `Не получилось: ${result.error}.`;
      b.disabled = false;
      b.textContent = "Обновить из Wolt";
    } else refreshWeek();
  }));
}

// Re-render the week tab where it was scrolled to.
async function refreshWeek() {
  const y = window.scrollY;
  try { await weekView(); } catch (err) { showError(err); }
  window.scrollTo(0, y);
}

async function menuAction(call) {
  try { await call(); } catch (err) { alert(err.message); }
  refreshWeek();
}

function planDays(plan, start) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i));
  return `
    <div class="stack">
      ${days.map((d) => {
        const rows = plan.filter((p) => p.day === d);
        return `<a class="card" href="#/day/${d}">
          <div class="meal-label">${esc(dayTitle(d))}</div>
          ${rows.length ? rows.map((r) => `<div class="small ${r.cooked_at ? "muted" : ""}">
              <b>${MEALS[r.meal]}:</b> ${esc(r.title || r.note || "—")}${r.multiplier > 1 ? ` ×${r.multiplier}` : ""}${r.cooked_at ? " ✓" : ""}
            </div>`).join("") : `<div class="muted small">пусто</div>`}
        </a>`;
      }).join("")}
    </div>`;
}

function menuSection(menu, order) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(menu.start, i));
  const meal = (r) => `
    <div class="menu-meal">
      <span class="grow ${r.cooked_at ? "muted" : ""}"><b>${MEALS[r.meal]}:</b>
        ${r.recipe_id ? `<a href="#/recipe/${r.recipe_id}?day=${r.day}&meal=${r.meal}&x=${r.multiplier}">${esc(r.title)}</a>` : esc(r.note || "—")}${r.multiplier > 1 ? ` ×${r.multiplier}` : ""}${r.cooked_at ? " ✓" : ""}</span>
      ${r.swappable ? `<button class="ghost swap" data-menu="${menu.id}" data-swap="${r.day}/${r.meal}" title="Заменить на другой рецепт" aria-label="Заменить">↻</button>` : ""}
    </div>`;
  const linked = menu.orders.length ? `<div class="small muted">Заказы в Wolt: ${menu.orders.map((o) =>
    `${esc(o.venue_name || "Wolt")}${o.ordered_at ? `, ${new Date(o.ordered_at).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}` : ""}${o.total != null ? ` — ${fmtMoney(o.total)}` : ""}`).join("; ")}</div>` : "";
  let actions = "";
  if (menu.status === "draft") {
    actions = `
      <div class="row wrap">
        <button data-reshuffle="${menu.start}">Перемешать всё</button>
        <span class="grow"></span>
        <button class="primary" data-menu="${menu.id}" data-status="awaiting_order">Утвердить — ждёт заказа</button>
      </div>`;
  } else if (menu.status === "awaiting_order") {
    const ext = extensionVersion();
    actions = `
      <div class="card stack">
        <div><b>Ждёт заказа в Wolt.</b> <span class="small muted">Скопируй задание и попроси Claude в браузере
          заказать всё (а если eaty подключён к Claude — см. «Дома», — выбери там промпт «Собрать корзину в Wolt»),
          или закажи сам по ссылкам. Когда заказ появится в Wolt, расширение заберёт его, и меню станет «Заказано».</span></div>
        ${linked}
        <div class="row wrap">
          <button class="primary" data-task="${menu.id}">Скопировать задание для Claude</button>
          <button data-sync="${menu.id}" ${ext ? "" : "disabled title=\"Нужно расширение eaty\""}>Обновить из Wolt</button>
        </div>
        <div class="small muted" data-sync-status="${menu.id}"></div>
        ${orderList(order.shopping)}
        <div class="row wrap">
          <button class="ghost" data-menu="${menu.id}" data-status="draft">← Вернуть в черновик</button>
          <span class="grow"></span>
          <button class="ghost" data-menu="${menu.id}" data-status="ordered">Уже всё заказано</button>
        </div>
      </div>`;
  } else {
    actions = `
      <div class="card stack">
        <div><b>Заказано</b>${menu.ordered_at ? ` <span class="small muted">${new Date(menu.ordered_at).toLocaleString("ru-RU")}</span>` : ""}</div>
        ${linked}
        <div><button class="ghost" data-menu="${menu.id}" data-status="awaiting_order">Заказано не всё</button></div>
      </div>`;
  }
  return `
    <section class="menu">
      <div class="row between">
        <h2 class="grow">Меню на ${esc(period(menu.start, menu.last_day))}</h2>
        <span class="badge status-${menu.status}">${MENU_STATUS[menu.status]}</span>
      </div>
      <div class="stack">
        ${days.map((d) => `
          <div class="card">
            <a class="meal-label" href="#/day/${d}">${esc(dayTitle(d))}</a>
            ${menu.meals.filter((r) => r.day === d).map(meal).join("") || `<div class="muted small">пусто</div>`}
          </div>`).join("")}
      </div>
      ${actions}
    </section>`;
}

// Stores with what to put in the cart; used by the shopping tab and a menu waiting for its order.
function shopLine(l) {
  return `
    <div class="line">
      <div class="row between">
        <b class="grow">${esc(l.product)}</b>
        ${l.packs ? `<span class="price">${fmtMoney(l.cost)}</span>` : ""}
      </div>
      <div class="small muted">нужно ${esc(l.need)}${l.have ? `, дома ${esc(l.have)}` : ""}</div>
      ${l.item && l.packs ? `<div class="item">${l.packs} × ${esc(l.item.name)} (${esc(l.item.pack)}${l.item.by_weight ? ", на развес" : ""}, ${fmtMoney(l.item.price)}) · <a href="${esc(l.item.url)}" target="_blank" rel="noopener">в Wolt</a></div>` : ""}
    </div>`;
}

function orderList(list) {
  if (!list.stores.length && !list.not_found.length) return `<p class="small">Докупать ничего не нужно — всё уже дома 🎉</p>`;
  return `
    ${list.stores.map((s) => `
      <h3 class="row between"><a class="grow" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a><span class="store-total">${fmtMoney(s.total)}</span></h3>
      <div class="card">${s.lines.map(shopLine).join("")}</div>`).join("")}
    ${list.stores.length > 1 ? `<p class="store-total">Итого: ${fmtMoney(list.total)}</p>` : ""}
    ${list.not_found.length ? `<h3>Не нашлось в Wolt</h3><div class="card">${list.not_found.map(shopLine).join("")}</div>` : ""}`;
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_) {
    return false; // needs https or localhost
  }
}

function showText(title, text) {
  const dlg = document.createElement("dialog");
  dlg.innerHTML = `
    <form method="dialog" class="stack">
      <h2>${esc(title)}</h2>
      <textarea readonly rows="12">${esc(text)}</textarea>
      <div class="small muted">Выдели и скопируй.</div>
      <div class="row between"><span></span><button class="primary">Закрыть</button></div>
    </form>`;
  document.body.appendChild(dlg);
  dlg.addEventListener("close", () => dlg.remove());
  dlg.showModal();
  dlg.querySelector("textarea").select();
}

async function shopView(params) {
  const days = +(params.get("days") || 7);
  const [list, status] = await Promise.all([api(`/api/v1/shopping?start=${today()}&days=${days}`), api("/api/v1/catalog/status")]);
  const updated = list.prices_updated_at ? new Date(list.prices_updated_at).toLocaleString("ru-RU") : "ещё не обновлялись";
  view.innerHTML = `
    <h1>Покупки</h1>
    <div class="row">
      <span class="muted grow">На ${days} дн. начиная с сегодня</span>
      ${[3, 7].map((n) => `<button class="${n === days ? "primary" : ""}" data-days="${n}">${n} дн.</button>`).join("")}
    </div>
    ${list.stores.length ? list.stores.map((s) => `
      <h2 class="row between"><span>${esc(s.name)}</span><span class="store-total">${fmtMoney(s.total)}</span></h2>
      <div class="card">${s.lines.map(shopLine).join("")}</div>`).join("") : `<p class="card">Докупать ничего не нужно 🎉</p>`}
    ${list.stores.length > 1 ? `<p class="store-total">Итого: ${fmtMoney(list.total)}</p>` : ""}
    ${list.not_found.length ? `<h2>Не нашлось в Wolt</h2><div class="card">${list.not_found.map(shopLine).join("")}</div>` : ""}
    ${list.enough.length ? `<h2>Хватает дома</h2><div class="card small muted">${list.enough.map((l) => esc(l.product)).join(", ")}</div>` : ""}
    <p class="small muted">Цены: ${esc(updated)}${status.last && !status.last.ok ? ` · ошибка обновления: ${esc(status.last.error)}` : ""}</p>
    <p><button id="refresh" ${status.running ? "disabled" : ""}>${status.running ? "Обновляю цены…" : "Обновить цены из Wolt"}</button></p>
    <p class="small muted">Масло, соль и специи в список не попадают — проверь их дома сам.</p>`;
  view.querySelectorAll("[data-days]").forEach((b) => b.addEventListener("click", () => { location.hash = `#/shop?days=${b.dataset.days}`; }));
  const btn = document.getElementById("refresh");
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "Обновляю цены…";
    try { await api("/api/v1/catalog/refresh", { method: "POST" }); } catch (err) { alert(err.message); }
    pollCatalog();
  });
  if (status.running) pollCatalog();
}

function pollCatalog() {
  setTimeout(async () => {
    try {
      const st = await api("/api/v1/catalog/status");
      if (st.running) return pollCatalog();
      if (location.hash.startsWith("#/shop")) route();
    } catch (_) { pollCatalog(); }
  }, 3000);
}

// The extension's app-bridge.js marks the page and answers its requests "x" with "x-result".
const extensionVersion = () => document.documentElement.dataset.eatyExtension;
const SYNC_DAYS = 7;   // only recent orders: older food is long eaten

// The extension's answer, or null if it didn't answer in time (or is too old to know the request).
function askExtension(type, payload, timeoutMs) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => finish(null), timeoutMs);
    function finish(result) {
      clearTimeout(timer);
      window.removeEventListener("message", onMessage);
      resolve(result);
    }
    function onMessage(event) {
      if (event.source === window && event.data && event.data.source === "eaty-extension"
          && event.data.type === `${type}-result`) finish(event.data.result || {});
    }
    window.addEventListener("message", onMessage);
    window.postMessage({ source: "eaty-app", type, ...payload }, location.origin);
  });
}

async function syncWithWolt() {
  return (await askExtension("wolt-sync", { days: SYNC_DAYS }, 180000)) || { error: "Расширение не ответило за 3 минуты" };
}

// Who the extension is signed in as. The button signs it in as whoever is signed in here: the
// extension takes the sign-in itself, so no password is typed in it.
async function extensionAccount() {
  const box = document.getElementById("ext-account");
  const text = box.querySelector(".grow");
  const button = box.querySelector("button");
  const status = await askExtension("extension-status", {}, 5000);
  if (!box.isConnected) return; // the view changed meanwhile
  box.hidden = false;
  button.hidden = !status;
  if (!status) {
    text.textContent = "Чтобы подключать расширение отсюда, обнови его: ↻ на его карточке в chrome://extensions, потом обнови эту страницу.";
  } else if (status.login === me.login) {
    text.innerHTML = `Расширение подключено к аккаунту <b>${esc(me.login)}</b> <span class="badge ok">✓</span>`;
    button.hidden = true;
  } else if (status.login) {
    text.innerHTML = `Расширение вошло как <b>${esc(status.login)}</b> — заказы уходят в тот аккаунт.`;
    button.textContent = `Подключить к ${me.login}`;
  } else {
    text.textContent = status.error
      ? `Расширение не узнало свой вход: ${status.error}.`
      : "Расширение не подключено к аккаунту — без этого заказы из Wolt сюда не попадут.";
    button.textContent = "Подключить расширение";
  }
}

async function connectExtension(button) {
  button.disabled = true;
  button.textContent = "Подключаю…";
  const result = await askExtension("extension-connect", {}, 15000);
  button.disabled = false;
  if (result && !result.error) return extensionAccount();
  const box = document.getElementById("ext-account");
  box.querySelector(".grow").textContent = `Не получилось подключить: ${result ? result.error : "расширение не ответило"}.`;
  button.textContent = "Попробовать ещё раз";
}

function skippedText(skipped) {
  if (!skipped) return "";
  const parts = [];
  if (skipped.restaurants) parts.push(`ресторанов: ${skipped.restaurants}`);
  if (skipped.unknown) parts.push(`непонятных заведений: ${skipped.unknown}`);
  if (skipped.old) parts.push(`старше ${SYNC_DAYS} дн.: ${skipped.old}`);
  return parts.length ? ` Пропущено — ${parts.join(", ")}.` : "";
}

function syncSummary(log) {
  if (!log) return "Синхронизаций ещё не было.";
  const when = new Date(log.created_at).toLocaleString("ru-RU");
  if (log.error) return `${when}: ${log.error}.`;
  return `${when}: заказов из магазинов — ${log.orders_imported}, в «Дома» добавлено продуктов: ${log.pantry_items}.`
    + skippedText(log.details && log.details.skipped);
}

async function pantryView() {
  const [items, orders, syncs] = await Promise.all([
    api("/api/v1/pantry"), api("/api/v1/wolt-orders"), api("/api/v1/wolt-orders/sync-log?limit=1"),
  ]);
  const ext = extensionVersion();
  items.sort((a, b) => (b.have > 0) - (a.have > 0));   // what's at home first, then by name
  view.innerHTML = `
    <h1>Дома</h1>
    <div class="card stack">
      <div class="row between">
        <div class="grow"><b>Заказы из Wolt</b>
          <div class="small muted">только магазины, за последние ${SYNC_DAYS} дней</div></div>
        <button class="primary" id="sync" ${ext ? "" : "disabled"}>Обновить из Wolt</button>
      </div>
      <div class="row between" id="ext-account" hidden>
        <span class="small muted grow"></span>
        <button id="ext-connect">Подключить расширение</button>
      </div>
      <div class="small muted" id="sync-status">${esc(ext
        ? `Последняя синхронизация — ${syncSummary(syncs[0])}`
        : "Расширение eaty 0.2+ на этой странице не найдено. Если оно уже стоит — нажми ↻ на его карточке в chrome://extensions и обнови эту страницу; если нет — установи его.")}</div>
    </div>
    <h2>Продукты</h2>
    <div class="card">
      ${items.map((p) => `
        <div class="line row between">
          <span class="grow">${esc(p.name)}</span>
          <span class="${p.have > 0 ? "" : "muted"}">${esc(p.have > 0 ? p.have_text : "нет")}</span>
          <button class="ghost" data-set="${esc(p.key)}" data-unit="${esc(p.base_unit)}" data-name="${esc(p.name)}">✎</button>
        </div>`).join("")}
    </div>
    <p class="small muted">Продукты приходят из заказов Wolt и списываются, когда жмёшь «Приготовлено» (поправить списание можно в рецепте приготовленного блюда). ✎ — поправить вручную.</p>
    <h2>Последние заказы</h2>
    ${orders.length ? `<div class="stack">${orders.map((o) => `
      <div class="card">
        <div class="row between"><b>${esc(o.venue_name || "Wolt")}</b>
          <span class="muted small">${o.ordered_at ? new Date(o.ordered_at).toLocaleString("ru-RU") : ""}</span></div>
        <div class="small muted">${o.items.map((i) => `${esc(i.name)}${i.count > 1 ? ` ×${+i.count}` : ""}${i.product_key ? "" : " (не в рецептах)"}`).join(", ")}</div>
      </div>`).join("")}</div>`
    : `<p class="card small">Пока пусто. Подключи расширение и нажми «Обновить из Wolt» — расширение заберёт последние заказы.</p>`}
    <h2>Claude</h2>
    <div class="card stack">
      <div><b>Подключить eaty к своему Claude</b>
        <div class="small muted">Claude увидит меню и сам соберёт корзины в Wolt — на твоей подписке Claude.</div></div>
      <div class="row">
        <input class="grow" id="mcp-url" readonly value="${esc(location.origin)}/mcp">
        <button id="mcp-copy">Скопировать</button>
      </div>
      <div class="small muted">claude.ai или Claude Desktop: настройки → Коннекторы → добавить свой коннектор (Add custom
        connector), вставить адрес и войти в eaty. Claude Code: <code>claude mcp add --transport http eaty ${esc(location.origin)}/mcp</code>.
        Потом выбери промпт «Собрать корзину в Wolt» (в Claude Code — <code>/mcp__eaty__wolt_order</code>). Корзину Claude
        собирает в браузере, где открыт твой Wolt: нужен Claude, который управляет Chrome (Claude в Chrome, Claude Code с /chrome).</div>
    </div>
    <p class="small muted account">Аккаунт: <b>${esc(me.login)}</b> · <a href="#" id="logout">Выйти</a></p>`;
  document.getElementById("logout").addEventListener("click", (e) => { e.preventDefault(); logout(); });
  const mcpCopy = document.getElementById("mcp-copy");
  mcpCopy.addEventListener("click", async () => {
    const url = document.getElementById("mcp-url");
    if (await copyText(url.value)) {
      mcpCopy.textContent = "Скопировано ✓";
      setTimeout(() => { mcpCopy.textContent = "Скопировать"; }, 2500);
    } else url.select();
  });
  if (ext) {
    const connectBtn = document.getElementById("ext-connect");
    connectBtn.addEventListener("click", () => connectExtension(connectBtn));
    extensionAccount();
  }

  const syncBtn = document.getElementById("sync");
  syncBtn.addEventListener("click", async () => {
    const status = document.getElementById("sync-status");
    syncBtn.disabled = true;
    syncBtn.textContent = "Синхронизирую…";
    status.textContent = "Открываю историю заказов в Wolt в фоновой вкладке и забираю последние заказы. Это займёт до минуты.";
    const result = await syncWithWolt();
    if (result.error) status.textContent = `Не получилось: ${result.error}.`; // also when orders were found but not imported
    else status.textContent = `Готово: заказов из магазинов — ${result.orders_imported}, в «Дома» добавлено продуктов: ${result.pantry_items}.`
      + skippedText(result.skipped) + (result.menus_ordered ? " Меню на неделю — заказано ✓" : "");
    syncBtn.disabled = false;
    syncBtn.textContent = "Обновить из Wolt";
    if (result.orders_imported) setTimeout(route, 1500);
  });

  view.querySelectorAll("[data-set]").forEach((b) => b.addEventListener("click", async () => {
    const unit = { g: "граммах", ml: "миллилитрах", pcs: "штуках" }[b.dataset.unit];
    const value = prompt(`${b.dataset.name}: сколько дома (в ${unit})?`);
    if (value == null || value.trim() === "" || isNaN(+value.replace(",", "."))) return;
    try {
      await api(`/api/v1/pantry/${encodeURIComponent(b.dataset.set)}`, { method: "PUT", body: { amount: +value.replace(",", ".") } });
      route();
    } catch (err) { alert(err.message); }
  }));
}

// ---------- accounts ----------

function authView(mode = "login") {
  const signup = mode === "signup";
  document.body.classList.add("signed-out");
  view.innerHTML = `
    <div class="auth">
      <h1>eaty</h1>
      <p class="muted">${signup ? "У каждого свой план, список покупок и продукты дома." : "Войди, чтобы увидеть свой план, покупки и продукты дома."}</p>
      <form class="card stack" id="auth" novalidate>
        <label class="small muted" for="auth-login">Логин</label>
        <input id="auth-login" name="login" autocomplete="username" autocapitalize="none" spellcheck="false" required>
        <label class="small muted" for="auth-password">Пароль</label>
        <input id="auth-password" name="password" type="password" autocomplete="${signup ? "new-password" : "current-password"}" required>
        ${signup ? `<p class="small muted">Логин — от 3 символов, без пробелов. Пароль — от 8 символов.</p>` : ""}
        <p class="error small" id="auth-error" hidden></p>
        <button class="primary">${signup ? "Зарегистрироваться" : "Войти"}</button>
      </form>
      <p class="small">${signup ? `Уже есть аккаунт? <a href="#" data-mode="login">Войти</a>` : `Нет аккаунта? <a href="#" data-mode="signup">Зарегистрироваться</a>`}</p>
    </div>`;
  const form = document.getElementById("auth");
  const errorEl = document.getElementById("auth-error");
  const fail = (text) => { errorEl.textContent = text; errorEl.hidden = false; };
  view.querySelector("[data-mode]").addEventListener("click", (e) => { e.preventDefault(); authView(e.target.dataset.mode); });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const login = form.login.value.trim();
    const password = form.password.value;
    if (!login || !password) return fail("Впиши логин и пароль.");
    if (signup && !/^[\p{L}\p{N}_.@+-]{3,64}$/u.test(login)) return fail("Логин — от 3 до 64 символов без пробелов: буквы, цифры и . _ - @ +");
    if (signup && password.length < 8) return fail("Пароль должен быть не короче 8 символов.");
    const btn = form.querySelector("button");
    btn.disabled = true;
    try {
      me = await api(`/api/v1/auth/${signup ? "register" : "login"}`, { method: "POST", body: { login, password } });
      route();
    } catch (err) {
      fail(err.message);
      btn.disabled = false;
    }
  });
  form.login.focus();
}

async function logout() {
  try { await api("/api/v1/auth/logout", { method: "POST" }); } catch (_) { /* signed out anyway */ }
  me = null;
  history.replaceState(null, "", "#/");
  authView();
}

// ---------- router ----------

async function route() {
  const [path, query = ""] = (location.hash.slice(1) || "/").split("?");
  const params = new URLSearchParams(query);
  const parts = path.split("/").filter(Boolean);
  const tab = { week: "week", recipes: "recipes", shop: "shop", pantry: "pantry" }[parts[0]]
    || (parts[0] === "recipe" && !params.get("day") ? "recipes" : "day");
  document.querySelectorAll(".tabs a").forEach((a) => a.classList.toggle("active", a.dataset.tab === tab));
  try {
    me = me || await api("/api/v1/auth/me");
  } catch (err) {
    if (err.status === 401) authView(); else showError(err);
    return;
  }
  document.body.classList.remove("signed-out");
  try {
    if (parts[0] === "recipe") await recipeView(+parts[1], params);
    else if (parts[0] === "week") await weekView();
    else if (parts[0] === "recipes") await recipesView(params);
    else if (parts[0] === "shop") await shopView(params);
    else if (parts[0] === "pantry") await pantryView();
    else await dayView(parts[0] === "day" && parts[1] ? parts[1] : today());
  } catch (err) {
    if (err.status !== 401) showError(err); // 401: api() already shows the sign-in screen
  }
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", route);
route();
