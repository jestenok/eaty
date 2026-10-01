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
const WEEKDAYS_LONG = ["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"];
const MENU_STATUS = { draft: "Черновик", awaiting_order: "Ждёт заказа", ordered: "Заказано" };

// Line icons in the logo's round strokes (24×24, stroke = currentColor).
const ICONS = {
  breakfast: '<path d="M12 3.5v2.5M5.3 7.3l1.6 1.6M18.7 7.3l-1.6 1.6M2.5 15.5h2.5M19 15.5h2.5M7.5 15.5a4.5 4.5 0 0 1 9 0M2.5 19.5h19"/>',
  lunch: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
  dinner: '<path d="M20 14.6A8.2 8.2 0 0 1 9.4 4a8.2 8.2 0 1 0 10.6 10.6Z"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  edit: '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  back: '<path d="m15 5-7 7 7 7"/>',
  prev: '<path d="m14.5 6-6 6 6 6"/>',
  next: '<path d="m9.5 6 6 6-6 6"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
  timer: '<circle cx="12" cy="13.5" r="7.5"/><path d="M12 10v3.5l2.2 1.6M9.5 2.5h5"/>',
  play: '<path d="M8 5.8v12.4a.8.8 0 0 0 1.2.7l10-6.2a.8.8 0 0 0 0-1.4l-10-6.2a.8.8 0 0 0-1.2.7Z"/>',
  pause: '<path d="M9 5.5v13M15 5.5v13"/>',
  close: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  flame: '<path d="M12 21.5c-3.8 0-6.5-2.6-6.5-6.3 0-3.4 2.5-5.4 3.9-7.9.5 1.8 1.3 2.9 2.6 3.5.2-2.9 1.4-5.4 3.6-7.3.4 3.2 3.9 6.2 3.9 11.4 0 3.9-3 6.6-7.5 6.6Z"/>',
  people: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 14a6.5 6.5 0 0 1 3 6"/>',
  stove: '<rect x="3.5" y="3.5" width="17" height="17" rx="3.5"/><circle cx="9" cy="9" r="2"/><circle cx="15" cy="9" r="2"/><circle cx="9" cy="15" r="2"/><circle cx="15" cy="15" r="2"/>',
  air_fryer: '<path d="M6.5 3.5h11a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z"/><path d="M4.5 11h15M10 7h4M9.5 15h5"/>',
  none: '<path d="M4 12h3l2-6 4 12 2-6h5"/>',
  external: '<path d="M8 16 16 8M9.5 8H16v6.5"/>',
  bag: '<path d="M4.8 8.5h14.4l-1 11a1.8 1.8 0 0 1-1.8 1.6H7.6a1.8 1.8 0 0 1-1.8-1.6l-1-11Z"/><path d="M8.5 11V7.5a3.5 3.5 0 0 1 7 0V11"/>',
  sync: '<path d="M20 11.5A8 8 0 0 0 5.6 7M4 4v3.5h3.5M4 12.5A8 8 0 0 0 18.4 17M20 20v-3.5h-3.5"/>',
  logout: '<path d="M14 4h3.5A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5H14M10 16.5 5.5 12 10 7.5M5.5 12H15"/>',
  system: '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17A8.5 8.5 0 0 0 12 3.5Z" fill="currentColor"/>',
  light: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
  dark: '<path d="M20 14.6A8.2 8.2 0 0 1 9.4 4a8.2 8.2 0 1 0 10.6 10.6Z"/>',
  pin: '<path d="M8.5 3.5h7"/><path class="fill" d="M10 3.5 9.4 9.2 6.5 12.4V14h11v-1.6l-2.9-3.2L14 3.5"/><path d="M12 14v6.5"/>',
  alarm: '<circle cx="12" cy="13" r="7.5"/><path d="M12 9.5V13l2.5 2M3.5 6 6.5 3M20.5 6l-3-3"/>',
  copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2.5"/><path d="M15.5 8.5v-2a2 2 0 0 0-2-2h-7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h2"/>',
};
const icon = (name) => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;

const view = document.getElementById("view");

// ---------- theme: as the system has it, or light or dark picked on the account page (per device) ----------

const THEMES = { system: "Авто", light: "Светлая", dark: "Тёмная" };
const THEME_BG = { light: "#f6f1ea", dark: "#121010" };   // --bg, for the browser's bar
function savedTheme() {
  try { return THEMES[localStorage.getItem("eaty.theme")] ? localStorage.getItem("eaty.theme") : "system"; } catch (_) { return "system"; }
}
function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme; else root.dataset.theme = theme;
  document.querySelectorAll('meta[name="theme-color"]').forEach((m) => {
    m.content = THEME_BG[theme] || THEME_BG[m.media.includes("dark") ? "dark" : "light"];
  });
}
function pickTheme(theme) {
  try { if (theme === "system") localStorage.removeItem("eaty.theme"); else localStorage.setItem("eaty.theme", theme); } catch (_) { /* private mode: this visit only */ }
  applyTheme(theme);
}
applyTheme(savedTheme());
const avatar = document.getElementById("avatar");
let me = null; // the signed-in user: { id, login }

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function api(path, options = {}) {
  const init = { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } };
  if (init.body && typeof init.body !== "string" && !(init.body instanceof Blob)) init.body = JSON.stringify(init.body);
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
const longDate = (iso) => { const d = parseDate(iso); return `${d.getDate()} ${MONTHS[d.getMonth()]}`; };
const weekdayLong = (iso) => WEEKDAYS_LONG[parseDate(iso).getDay()];
function monday(iso) { return addDays(iso, -((parseDate(iso).getDay() + 6) % 7)); }

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
function plural(n, one, few, many) {
  const [m10, m100] = [n % 10, n % 100];
  return m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? few : many;
}
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

// iPhone or iPad (an iPad says it is a Mac, but has touch).
const IOS = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
// A locked iPhone puts sites to sleep, so eaty can't ring like the Clock app does. On the account page a timer can
// go to the Clock app itself, through a shortcut made once: it rings in silent mode and counts down on the lock screen.
const CLOCK_SHORTCUT = "Кухонный таймер";
function clockTimers() {
  try { return IOS && localStorage.getItem("eaty.clock-timers") === "1"; } catch (_) { return false; }
}
function pickClockTimers(on) {
  try { if (on) localStorage.setItem("eaty.clock-timers", "1"); else localStorage.removeItem("eaty.clock-timers"); } catch (_) { /* private mode */ }
}
function startClockTimer(seconds) {
  location.href = `shortcuts://run-shortcut?name=${encodeURIComponent(CLOCK_SHORTCUT)}&input=text&text=${Math.round(seconds)}`;
}

// ---------- timer sounds: made here as WAVs, or the account's own ----------

// Notes as [start s, length s, Hz, voice]; `length` is one round of the loop that rings until «Стоп».
const SOUNDS = {
  alarm: { name: "Будильник", length: 1.24, notes: [0, .16, .32, .48].map((at) => [at, .1, 1600, "beep"]) },
  chime: { name: "Колокольчик", length: 2, notes: [[0, 1.2, 1046.5, "bell"], [.18, 1.2, 1318.5, "bell"], [.36, 1.5, 1568, "bell"]] },
  cuckoo: { name: "Кукушка", length: 2.2, notes: [[0, .22, 1175, "whistle"], [.3, .34, 932, "whistle"], [.9, .22, 1175, "whistle"], [1.2, .34, 932, "whistle"]] },
};
const VOICES = {
  beep: (w) => Math.sin(w) + 0.36 * Math.sin(3 * w),                              // the third harmonic: loud on a phone's speaker
  bell: (w, k) => Math.exp(-k / 0.35) * (Math.sin(w) + 0.3 * Math.sin(2.76 * w)),  // dies away, with an off-key overtone
  whistle: (w) => Math.sin(w) + 0.15 * Math.sin(2 * w),
};
function soundWav(kind) {
  const { length, notes } = SOUNDS[kind];
  const rate = 22050, size = Math.round(rate * length);
  const pcm = new Float32Array(size);
  for (const [at, dur, hz, voice] of notes) {
    for (let n = Math.round(at * rate); n < Math.min(size, Math.round((at + dur) * rate)); n++) {
      const k = n / rate - at;
      pcm[n] += Math.min(1, k / 0.005, (dur - k) / 0.005) * VOICES[voice](2 * Math.PI * hz * k, k); // no clicks at the edges
    }
  }
  const gain = 0.95 / pcm.reduce((peak, v) => Math.max(peak, Math.abs(v)), 1e-9);
  const wav = new DataView(new ArrayBuffer(44 + size * 2));
  const text = (at, str) => [...str].forEach((c, i) => wav.setUint8(at + i, c.charCodeAt(0)));
  text(0, "RIFF"); wav.setUint32(4, 36 + size * 2, true); text(8, "WAVE");
  text(12, "fmt "); wav.setUint32(16, 16, true); wav.setUint16(20, 1, true); wav.setUint16(22, 1, true);
  wav.setUint32(24, rate, true); wav.setUint32(28, rate * 2, true); wav.setUint16(32, 2, true); wav.setUint16(34, 16, true);
  text(36, "data"); wav.setUint32(40, size * 2, true);
  pcm.forEach((v, n) => wav.setInt16(44 + n * 2, Math.round(v * gain * 32767), true));
  return new Blob([wav], { type: "audio/wav" });
}

// Which sound rings is picked per device; the own sound is the account's (uploaded on the account page).
function timerSound() {
  try { const kind = localStorage.getItem("eaty.timer-sound"); return kind === "own" || SOUNDS[kind] ? kind : "alarm"; } catch (_) { return "alarm"; }
}
function pickTimerSound(kind, ownVersion) {
  try {
    if (kind === "alarm") localStorage.removeItem("eaty.timer-sound"); else localStorage.setItem("eaty.timer-sound", kind);
    if (ownVersion) localStorage.setItem("eaty.own-sound", ownVersion);
  } catch (_) { /* private mode */ }
}
const madeSounds = {};
function soundUrl(kind) {
  if (kind === "own") { // a new upload is a new address, so the alarm doesn't keep the old one
    let version = "";
    try { version = localStorage.getItem("eaty.own-sound") || ""; } catch (_) { /* private mode */ }
    return `/api/v1/timer-sound/file?v=${encodeURIComponent(version)}`;
  }
  return madeSounds[kind] || (madeSounds[kind] = URL.createObjectURL(soundWav(kind)));
}
let preview = null;
function previewSound(kind) { // on a tap in the list, as the iPhone's ringtone picker does
  if (preview) preview.pause();
  const a = preview = new Audio(soundUrl(kind));
  a.play().catch(() => { /* no sound to play */ });
  setTimeout(() => a.pause(), 6000); // the start of a long file is enough
}

const Timers = (() => {
  const KEY = "eaty.timers";
  let list = [];
  try { list = JSON.parse(localStorage.getItem(KEY)) || []; } catch (_) { list = []; }
  let ticker = null;
  let alarm = null;     // an <audio>: unlike Web Audio, it plays through the iPhone's silent switch
  let primed = false;
  let ringing = false;
  let wakeLock = null;
  const tray = document.getElementById("timers");

  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (_) { /* private mode */ } };
  const left = (t) => (t.pausedLeft != null ? t.pausedLeft : (t.endAt - Date.now()) / 1000);
  const loud = () => list.some((t) => t.ringing && !t.clock); // the Clock app rings its own

  function alarmSound() {
    if (!alarm) {
      alarm = new Audio();
      alarm.loop = true;
      alarm.addEventListener("error", () => { // the own sound is gone or won't play here: the alarm rings instead
        if (alarm.dataset.url === soundUrl("alarm")) return;
        alarm.src = alarm.dataset.url = soundUrl("alarm");
        if (ringing) alarm.play().catch(() => { /* the next tap lets it ring */ });
      });
    }
    const url = soundUrl(timerSound());
    if (alarm.dataset.url !== url && !ringing) alarm.src = alarm.dataset.url = url;
    return alarm;
  }
  // iOS lets a page play later only a sound it started from a tap: start the alarm muted and stop it at once.
  function unlockAudio() {
    const a = alarmSound();
    if (primed || !a.paused) return;
    primed = true;
    a.muted = true;
    a.play().then(() => { if (!ringing) a.pause(); }, () => { primed = false; }).finally(() => { a.muted = false; });
  }
  function sound(on) {
    if (on === ringing) return;
    const a = alarmSound(); // with the sound picked meanwhile
    ringing = on;
    if (on) {
      if (navigator.audioSession) navigator.audioSession.type = "playback"; // ring in silent mode too
      a.currentTime = 0;
      a.muted = false;
      a.play().catch(() => { /* no tap since the page opened: the next tap lets it ring */ });
    } else {
      a.pause();
      if (navigator.audioSession) navigator.audioSession.type = "auto";
    }
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
    if (t.clock) return;
    if (navigator.vibrate) navigator.vibrate([400, 150, 400, 150, 800]);
    if ("Notification" in window && Notification.permission === "granted") {
      try { new Notification("Готово!", { body: t.label, tag: t.id }); } catch (_) { /* mobile needs SW */ }
    }
  }

  function tick() {
    let anyRunning = false;
    for (const t of list) {
      if (t.pausedLeft == null && !t.ringing) {
        if (left(t) <= 0) ring(t); else anyRunning = true;
      }
    }
    sound(loud());
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
        <span class="label">${esc(t.label)}${t.clock ? " · в Часах" : ""}</span>
        ${t.ringing ? `<button class="primary" data-act="stop">Стоп</button>` : `
          ${t.clock ? "" /* the Clock app's timer wouldn't follow a pause or a minute more */ : `
          <button data-act="plus">+1 мин</button>
          <button class="icon" data-act="${t.pausedLeft != null ? "resume" : "pause"}" aria-label="${t.pausedLeft != null ? "Продолжить" : "Пауза"}">${icon(t.pausedLeft != null ? "play" : "pause")}</button>`}
          <button class="icon" data-act="stop" aria-label="Убрать таймер">${icon("close")}</button>`}
      </div>`).join("");
    document.querySelectorAll("[data-timer-key]").forEach((btn) => {
      const t = list.find((x) => x.key === btn.dataset.timerKey);
      const text = t ? (t.ringing ? "Готово!" : fmtClock(left(t))) : fmtClock(+btn.dataset.seconds);
      const shown = `${t ? (t.ringing ? "ring" : "run") : "idle"}:${text}`;
      if (btn.dataset.shown === shown) return; // the button keeps its nodes between ticks: taps aren't lost
      btn.dataset.shown = shown;
      btn.classList.toggle("running", !!t);
      btn.innerHTML = `${t && t.ringing ? "" : icon(t ? "timer" : "play")}${text}`;
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
    const clock = clockTimers();
    if (!clock) {
      unlockAudio();
      if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
    }
    const existing = list.find((t) => t.key === key);
    if (existing && !existing.ringing) return; // already running: the button shows the countdown
    list = list.filter((t) => t.key !== key);
    list.push({ id: `${key}:${Date.now()}`, key, label, endAt: Date.now() + seconds * 1000, pausedLeft: null, ringing: false, clock });
    save();
    if (!ticker) ticker = setInterval(tick, 250);
    tick();
    if (clock) startClockTimer(seconds);
  }

  // After a reload a running timer has had no tap yet: the first tap anywhere lets it ring.
  ["touchend", "click"].forEach((type) => document.addEventListener(type, () => { if (list.some((t) => !t.clock)) unlockAudio(); }, true));
  if (list.length) ticker = setInterval(tick, 250);
  render();
  return { start, render };
})();

// ---------- views ----------

async function dayView(day) {
  const first = monday(day);
  const [plan, recipes] = await Promise.all([api(`/api/v1/plan?start=${first}&days=7`), api("/api/v1/recipes")]);
  const rows = plan.filter((p) => p.day === day);
  const rel = { [today()]: "Сегодня", [addDays(today(), 1)]: "Завтра", [addDays(today(), -1)]: "Вчера" }[day];
  view.innerHTML = `
    <div class="page-head">
      <div class="grow">
        <div class="eyebrow">${rel ? `${weekdayLong(day)}, ${longDate(day)}` : longDate(day)}</div>
        <h1>${rel || weekdayLong(day).replace(/^./, (c) => c.toUpperCase())}</h1>
      </div>
      <div class="nav">
        <button class="icon" data-go="${addDays(day, -7)}" aria-label="Неделя назад">${icon("prev")}</button>
        <button class="icon" data-go="${addDays(day, 7)}" aria-label="Неделя вперёд">${icon("next")}</button>
      </div>
    </div>
    <nav class="week-strip" aria-label="Дни недели">
      ${Array.from({ length: 7 }, (_, i) => addDays(first, i)).map((d) => {
        const meals = plan.filter((p) => p.day === d);
        return `<a class="day-chip ${d === day ? "on" : ""} ${d === today() ? "today" : ""}" href="#/day/${d}" ${d === day ? 'aria-current="date"' : ""}>
          <span class="wd">${WEEKDAYS[parseDate(d).getDay()]}</span>
          <span class="dn">${parseDate(d).getDate()}</span>
          <span class="pips">${meals.map((p) => `<i class="${p.cooked_at ? "done" : ""}"></i>`).join("")}</span>
        </a>`;
      }).join("")}
    </nav>
    <div class="stack">
      ${Object.keys(MEALS).map((meal) => mealCard(day, meal, rows.find((p) => p.meal === meal))).join("")}
    </div>
    ${day !== today() ? `<p class="today-link"><a class="button" href="#/">К сегодняшнему дню</a></p>` : ""}`;
  view.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => { location.hash = `#/day/${b.dataset.go}`; }));
  view.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", (e) => {
    e.preventDefault();
    editMeal(day, b.dataset.edit, rows.find((p) => p.meal === b.dataset.edit), recipes);
  }));
}

function mealCard(day, meal, row) {
  const x = row && row.multiplier > 1 ? `<span class="badge">×${row.multiplier}</span>` : "";
  const cooked = row && row.cooked_at ? `<span class="badge ok">готово</span>` : "";
  const title = row ? (row.title || row.note || "—") : "Ничего не запланировано";
  const sub = row && row.title && row.note ? `<div class="meal-note">${esc(row.note)}</div>` : "";
  const body = `
    <span class="meal-icon">${icon(row && row.cooked_at ? "check" : meal)}</span>
    <div class="grow">
      <div class="meal-label">${MEALS[meal]}</div>
      <div class="meal-title">${esc(title)}</div>
      ${sub}
    </div>
    ${x || cooked ? `<div class="badges">${x}${cooked}</div>` : ""}
    <button class="ghost icon" data-edit="${meal}" aria-label="${row ? "Изменить" : "Запланировать"}">${icon(row ? "edit" : "plus")}</button>`;
  const cls = `card meal meal-${meal} ${row ? "" : "empty"} ${row && row.cooked_at ? "cooked" : ""}`;
  if (row && row.recipe_id) {
    return `<a class="${cls}" href="#/recipe/${row.recipe_id}?day=${day}&meal=${meal}&x=${row.multiplier}">${body}</a>`;
  }
  return `<div class="${cls}">${body}</div>`;
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
    const tracked = recipe.ingredients.filter((i) => i.product_key != null);
    const missing = tracked.filter((i) => !(i.have != null && i.have >= i.amount * x)).length;
    view.innerHTML = `
      <a class="back-link" href="${day ? `#/day/${day}` : "#/recipes"}">${icon("back")} ${day ? esc(dayTitle(day)) : "Рецепты"}</a>
      <div class="recipe-head">
        <h1>${esc(recipe.title)}</h1>
        <div class="recipe-meta">
          <span class="tag">${icon("people")} ${x * recipe.portions} порции</span>
          <span class="tag">${icon(recipe.appliance)} ${esc(APPLIANCES[recipe.appliance] || recipe.appliance)}</span>
          <span class="seg" role="group" aria-label="Сколько готовить">
            ${[1, 2].map((n) => `<button class="${n === x ? "on" : ""}" data-x="${n}">×${n}</button>`).join("")}
          </span>
        </div>
        ${x > 1 && recipe.batch_note ? `<p class="note-card">${esc(recipe.batch_note)}</p>` : ""}
      </div>
      <h2 class="section-title">Продукты
        ${tracked.length ? `<span class="muted">${missing ? `не хватает: ${missing}` : "всё есть дома"}</span>` : ""}</h2>
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
      <div class="legend"><span><i class="dot ok"></i>дома хватает</span><span><i class="dot missing"></i>по данным «Дома» не хватает</span></div>
      <h2 class="section-title">Готовим <span class="muted">${done.length} из ${recipe.steps.length}</span></h2>
      <ol class="cook">
        ${recipe.steps.map((s) => `
          <li class="step ${done.includes(s.position) ? "done" : ""}">
            <span class="num" data-done="${s.position}" role="button" aria-label="Шаг ${s.position + 1}: ${done.includes(s.position) ? "вернуть" : "сделано"}">${done.includes(s.position) ? icon("check") : s.position + 1}</span>
            <div class="body">
              <div class="text">${esc(s.text)}</div>
              ${s.heat ? `<div class="heat">${icon("flame")} ${esc(s.heat)}</div>` : ""}
              <div class="actions">
                ${s.timer_seconds ? `<button data-timer-key="${id}:${s.position}" data-seconds="${s.timer_seconds}" data-step="${s.position}"></button>` : ""}
                <button class="ghost" data-done="${s.position}">${done.includes(s.position) ? "Вернуть" : "Сделано"}</button>
              </div>
            </div>
          </li>`).join("")}
      </ol>
      ${planRow && planRow.cooked_at ? `
        <h2>Списано из «Дома»</h2>
        ${used.length ? `<ul class="ingredients card">${used.map((u) => `
          <li><span class="grow">${esc(u.name)}</span><span class="amount">${esc(u.amount_text)}</span></li>`).join("")}
        </ul>` : `<p class="card small muted">Ничего не списано.</p>`}
        <p><button id="edit-used">Поправить списание</button></p>` : ""}
      ${planRow ? `<p class="cta"><button class="block ${planRow.cooked_at ? "" : "primary"}" id="cooked">${planRow.cooked_at ? "Отменить «приготовлено»" : `${icon("check")} Приготовлено — списать продукты`}</button></p>` : ""}`;

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
  let only = params.get("cat") || "";   // a category chip, or all of them
  view.innerHTML = `
    <div class="page-head"><h1>Рецепты</h1></div>
    <label class="search">${icon("search")}
      <input id="search" type="search" placeholder="Курица, суп, аэрогриль…" value="${esc(query)}" aria-label="Поиск рецептов">
    </label>
    <div class="chips" id="chips"></div>
    <div id="recipe-list"></div>`;
  const list = document.getElementById("recipe-list");
  const chips = document.getElementById("chips");

  function render() {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    const found = recipes.filter((r) => {
      const text = `${r.title} ${CATEGORIES[r.category] || ""} ${APPLIANCES[r.appliance] || ""}`.toLowerCase();
      return words.every((w) => text.includes(w));
    });
    const count = (category) => found.filter((r) => !category || r.category === category).length;
    chips.innerHTML = [["", "Все"], ...Object.entries(CATEGORIES)].map(([category, label]) =>
      `<button class="chip ${only === category ? "on" : ""}" data-cat="${category}">${label} <span class="count">${count(category)}</span></button>`).join("");
    list.innerHTML = Object.entries(CATEGORIES).filter(([category]) => !only || only === category).map(([category, label]) => {
      const rows = found.filter((r) => r.category === category);
      return rows.length ? `
        <h2 class="section-title">${label} <span class="muted">${rows.length}</span></h2>
        <div class="card list">${rows.map((r) => `
          <a class="line recipe-row" href="#/recipe/${r.id}">
            <span class="title">${esc(r.title)}</span>
            ${r.appliance !== "stove" ? `<span class="appl">${icon(r.appliance)} ${esc(APPLIANCES[r.appliance] || "")}</span>` : ""}
            ${icon("chevron").replace('class="i"', 'class="i chev"')}
          </a>`).join("")}
        </div>` : "";
    }).join("") || `<div class="empty-state">Ничего не нашлось</div>`;
  }

  function remember() {
    const q = new URLSearchParams();
    if (query) q.set("q", query);
    if (only) q.set("cat", only);
    const qs = q.toString();
    history.replaceState(null, "", `#/recipes${qs ? `?${qs}` : ""}`);
  }
  document.getElementById("search").addEventListener("input", (e) => {
    query = e.target.value;
    remember();
    render();
  });
  chips.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-cat]");
    if (!chip) return;
    only = chip.dataset.cat;
    remember();
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
    <div class="page-head"><div class="grow"><div class="eyebrow">меню, покупки и заказ в Wolt</div><h1>Неделя</h1></div></div>
    ${menus.map((m, i) => menuSection(m, orders[i])).join("")}
    ${menus.length ? "" : planDays(plan, start)}
    <h2>Новое меню</h2>
    <div class="card stack">
      <div class="small muted">Рецепты подберутся из базы: на ужин блюдо ×2, вторая половина — обед на завтра.
        Что не понравится — замени, потом утверди, и меню будет ждать заказа в Wolt.</div>
      <label class="check">
        <input type="checkbox" id="menu-home">
        <span><b>Только из того, что дома</b>
          <span class="small muted">Рецепты, на которые хватает продуктов из «Дома» за вычетом того, что уйдёт
            на уже запланированные блюда и на сами рецепты меню. На что не хватит, останется пустым.</span></span>
      </label>
      <div class="row">
        <label class="small muted" for="menu-start">с</label>
        <input type="date" id="menu-start" value="${next}" min="${start}">
        <button class="primary" id="new-menu">Накидать</button>
      </div>
    </div>`;

  document.getElementById("new-menu").addEventListener("click", () =>
    menuAction(() => api("/api/v1/menus", { method: "POST", body: {
      start: document.getElementById("menu-start").value, from_home: document.getElementById("menu-home").checked } })));
  view.querySelectorAll("[data-swap]").forEach((b) => b.addEventListener("click", () => {
    b.disabled = true;
    b.classList.add("spin");
    menuAction(() => api(`/api/v1/menus/${b.dataset.menu}/${b.dataset.swap}/swap`, { method: "POST" }));
  }));
  view.querySelectorAll("[data-reshuffle]").forEach((b) => b.addEventListener("click", () => {
    if (confirm("Подобрать всё меню заново? Замены пропадут.")) {
      menuAction(() => api("/api/v1/menus", { method: "POST", body: { start: b.dataset.reshuffle, from_home: !!b.dataset.home } }));
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
        return `<a class="card plan-day" href="#/day/${d}">
          <div class="meal-label">${esc(dayTitle(d))}</div>
          ${rows.length ? rows.map((r) => `<div class="menu-meal meal-${r.meal} ${r.cooked_at ? "cooked" : ""}">
              <span class="mini-icon">${icon(r.cooked_at ? "check" : r.meal)}</span>
              <span class="grow ${r.cooked_at ? "muted" : ""}"><b>${MEALS[r.meal]}</b>
                ${esc(r.title || r.note || "—")}${r.multiplier > 1 ? ` ×${r.multiplier}` : ""}</span>
            </div>`).join("") : `<div class="muted small">пусто</div>`}
        </a>`;
      }).join("")}
    </div>`;
}

function menuSection(menu, order) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(menu.start, i));
  const draft = menu.status === "draft";
  const meal = (r) => `
    <div class="menu-meal meal-${r.meal} ${r.cooked_at ? "cooked" : ""}">
      <span class="mini-icon">${icon(r.cooked_at ? "check" : r.meal)}</span>
      <span class="grow ${r.cooked_at ? "muted" : ""}"><b>${MEALS[r.meal]}</b>
        ${r.recipe_id ? `<a href="#/recipe/${r.recipe_id}?day=${r.day}&meal=${r.meal}&x=${r.multiplier}">${esc(r.title)}</a>` : esc(r.note || "—")}${r.multiplier > 1 ? ` ×${r.multiplier}` : ""}${r.cooked_at ? " ✓" : ""}
        ${r.missing.length ? `<span class="missing small" title="Этого дома не хватает">🛒 ${esc(r.missing.join(", "))}</span>` : ""}</span>
      ${r.swappable ? `<button class="ghost swap" data-menu="${menu.id}" data-swap="${r.day}/${r.meal}" title="Заменить на другой рецепт" aria-label="Заменить">${icon("sync")}</button>` : ""}
    </div>`;
  // a draft shows its empty meals too, with a button to pick a recipe for them
  const empty = (day, m) => `
    <div class="menu-meal meal-${m} empty">
      <span class="mini-icon">${icon(m)}</span>
      <span class="grow muted"><b>${MEALS[m]}</b> ${menu.from_home ? "дома не из чего" : "пусто"}</span>
      <button class="ghost swap" data-menu="${menu.id}" data-swap="${day}/${m}" title="Подобрать рецепт" aria-label="Подобрать рецепт">${icon("plus")}</button>
    </div>`;
  const dayMeals = (d) => {
    const rows = menu.meals.filter((r) => r.day === d);
    if (!draft) return rows.map(meal).join("") || `<div class="muted small">пусто</div>`;
    return Object.keys(MEALS).map((m) => { const r = rows.find((x) => x.meal === m); return r ? meal(r) : empty(d, m); }).join("");
  };
  const linked = menu.orders.length ? `<div class="small muted">Заказы в Wolt: ${menu.orders.map((o) =>
    `${esc(o.venue_name || "Wolt")}${o.ordered_at ? `, ${new Date(o.ordered_at).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}` : ""}${o.total != null ? ` — ${fmtMoney(o.total)}` : ""}`).join("; ")}</div>` : "";
  let actions = "";
  if (menu.status === "draft") {
    actions = `
      <div class="row wrap">
        <button data-reshuffle="${menu.start}" data-home="${menu.from_home ? 1 : ""}">Перемешать всё</button>
        <span class="grow"></span>
        <button class="primary" data-menu="${menu.id}" data-status="awaiting_order">Утвердить — ждёт заказа</button>
      </div>`;
  } else if (menu.status === "awaiting_order") {
    const ext = extensionVersion();
    actions = `
      <div class="card stack">
        <div><b>Ждёт заказа в Wolt.</b> <span class="small muted">Скопируй задание и попроси Claude в браузере
          заказать всё (а если eaty подключён к Claude — <a href="/guide#claude">как подключить</a>, — выбери там промпт «Собрать корзину в Wolt»),
          или закажи сам по ссылкам. Когда заказ появится в Wolt, расширение заберёт его, и меню станет «Заказано».</span></div>
        ${linked}
        <div class="row wrap">
          <button class="primary" data-task="${menu.id}">Скопировать задание для Claude</button>
          <button data-sync="${menu.id}" ${ext ? "" : "disabled title=\"Нужно расширение eaty\""}>Обновить из Wolt</button>
        </div>
        <div class="small muted" data-sync-status="${menu.id}"></div>
        ${orderList(order.shopping)}
        <div class="row wrap">
          <button class="ghost" data-menu="${menu.id}" data-status="draft">Вернуть в черновик</button>
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
      ${menu.from_home ? fromHomeNote(menu) : ""}
      <div class="stack">
        ${days.map((d) => `
          <div class="card">
            <a class="meal-label" href="#/day/${d}">${esc(dayTitle(d))}</a>
            ${dayMeals(d)}
          </div>`).join("")}
      </div>
      ${actions}
    </section>`;
}

// A menu from home: how much of the week what's at home is enough for.
function fromHomeNote(menu) {
  const empty = 21 - menu.meals.length;
  const notes = [];
  if (empty) notes.push(`на ${empty} из 21 приёма пищи продуктов не хватило${menu.status === "draft" ? " — + подберёт рецепт, но его продукты придётся купить" : ""}`);
  if (menu.meals.some((r) => r.missing.length)) notes.push("🛒 — чего для блюда дома нет");
  return `<p class="small muted from-home">Только из того, что дома${notes.length ? `: ${notes.join("; ")}` : " — хватает на всю неделю"}.</p>`;
}

// Stores with what to put in the cart; used by the shopping tab and a menu waiting for its order.
function shopLine(l) {
  return `
    <div class="line shop-line">
      <div class="row between">
        <b class="grow">${esc(l.product)}</b>
        ${l.packs ? `<span class="price">${fmtMoney(l.cost)}</span>` : ""}
      </div>
      <div class="need">нужно ${esc(l.need)}${l.have ? ` · дома ${esc(l.have)}` : ""}</div>
      ${l.item && l.packs ? `<div class="item"><span>${l.packs} × ${esc(l.item.name)} (${esc(l.item.pack)}${l.item.by_weight ? ", на развес" : ""}, ${fmtMoney(l.item.price)})</span>
        <a class="wolt-link" href="${esc(l.item.url)}" target="_blank" rel="noopener">Wolt ${icon("external")}</a></div>` : ""}
    </div>`;
}

function orderList(list) {
  if (!list.stores.length && !list.not_found.length) return `<p class="small">Докупать ничего не нужно — всё уже дома 🎉</p>`;
  return `
    ${list.stores.map((s) => `${storeHead(s)}
      <div class="card list">${s.lines.map(shopLine).join("")}</div>`).join("")}
    ${list.stores.length > 1 ? `<p class="store-total">Итого: ${fmtMoney(list.total)}</p>` : ""}
    ${list.not_found.length ? `<h3>Не нашлось в Wolt</h3><div class="card list">${list.not_found.map(shopLine).join("")}</div>` : ""}`;
}

function storeHead(s) {
  return `
    <div class="store-head">
      <span class="store-badge">${icon("bag")}</span>
      <a class="name" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a>
      <span class="store-total">${fmtMoney(s.total)}</span>
    </div>`;
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
  const items = list.stores.reduce((n, s) => n + s.lines.length, 0);
  view.innerHTML = `
    <div class="page-head">
      <h1>Покупки</h1>
      <span class="seg" role="group" aria-label="На сколько дней">
        ${[3, 7].map((n) => `<button class="${n === days ? "on" : ""}" data-days="${n}">${n} дн.</button>`).join("")}
      </span>
    </div>
    ${list.stores.length ? `
      <div class="total-card">
        <div class="label">На ${days} дн. с сегодня</div>
        <div class="sum">${fmtMoney(list.total)}</div>
        <div class="sub">${list.stores.length > 1 ? `${list.stores.length} ${plural(list.stores.length, "магазин", "магазина", "магазинов")} · ` : ""}${items} ${plural(items, "товар", "товара", "товаров")} в Wolt</div>
      </div>
      ${list.stores.map((s) => `${storeHead(s)}
        <div class="card list">${s.lines.map(shopLine).join("")}</div>`).join("")}` : `<div class="card empty-state">Докупать ничего не нужно 🎉</div>`}
    ${list.not_found.length ? `<h2>Не нашлось в Wolt</h2><div class="card list">${list.not_found.map(shopLine).join("")}</div>` : ""}
    ${list.enough.length ? `<h2>Хватает дома</h2><div class="enough">${list.enough.map((l) => `<span class="tag">${esc(l.product)}</span>`).join("")}</div>` : ""}
    <div class="card stack refresh-card">
      <div class="row"><span class="grow small muted">Цены: ${esc(updated)}${status.last && !status.last.ok ? ` · ошибка обновления: ${esc(status.last.error)}` : ""}</span></div>
      <button id="refresh" ${status.running ? "disabled" : ""}>${icon("sync")} <span>${status.running ? "Обновляю цены…" : "Обновить цены из Wolt"}</span></button>
    </div>
    <p class="footnote">Масло, соль и специи в список не попадают — проверь их дома сам.</p>`;
  view.querySelectorAll("[data-days]").forEach((b) => b.addEventListener("click", () => { location.hash = `#/shop?days=${b.dataset.days}`; }));
  const btn = document.getElementById("refresh");
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.querySelector("span").textContent = "Обновляю цены…";
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
  const dot = box.querySelector(".dot"); // on the account page
  if (dot) dot.className = `dot ${status && status.login === me.login ? "ok" : "missing"}`;
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

// «Дома»: «Всегда дома» on top (what to buy when you go to the shop), the Wolt orders, the products.
async function pantryView() {
  const [loaded, orders, syncs] = await Promise.all([
    api("/api/v1/pantry"), api("/api/v1/wolt-orders"), api("/api/v1/wolt-orders/sync-log?limit=1"),
  ]);
  let items = loaded;
  const ext = extensionVersion();
  view.innerHTML = `
    <div class="page-head"><div class="grow"><div class="eyebrow">что есть на кухне</div><h1>Дома</h1></div></div>
    <section id="staples"></section>
    <div class="card stack sync-card">
      <div class="head">
        <span class="tile">${icon("bag")}</span>
        <div class="grow"><b>Заказы из Wolt</b>
          <div class="small muted">только магазины, за последние ${SYNC_DAYS} дней</div></div>
      </div>
      <button class="primary block" id="sync" ${ext ? "" : "disabled"}>Обновить из Wolt</button>
      <div class="row between" id="ext-account" hidden>
        <span class="small muted grow"></span>
        <button id="ext-connect">Подключить расширение</button>
      </div>
      <div class="small muted" id="sync-status">${ext
        ? esc(`Последняя синхронизация — ${syncSummary(syncs[0])}`)
        : `Расширение eaty 0.2+ на этой странице не найдено. Если оно уже стоит — нажми ↻ на его карточке в chrome://extensions и обнови эту страницу; если нет — <a href="/guide#extension">установи его по инструкции</a>.`}</div>
    </div>
    <div id="products"></div>
    <p class="footnote">Продукты приходят из заказов Wolt и списываются, когда жмёшь «Приготовлено» (поправить списание можно в рецепте приготовленного блюда). Нажми на продукт, чтобы поправить, сколько его дома; булавка — всегда держать дома.</p>
    <h2>Последние заказы</h2>
    ${orders.length ? `<div class="stack">${orders.map((o) => `
      <div class="card">
        <div class="row between"><b>${esc(o.venue_name || "Wolt")}</b>
          <span class="muted small">${o.ordered_at ? new Date(o.ordered_at).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : ""}</span></div>
        <div class="order-items">${o.items.map((i) => `${esc(i.name)}${i.count > 1 ? ` ×${+i.count}` : ""}${i.product_key ? "" : " (не в рецептах)"}`).join(", ")}</div>
      </div>`).join("")}</div>`
    : `<p class="card small">Пока пусто. <a href="/guide#extension">Подключи расширение</a> и нажми «Обновить из Wolt» — расширение заберёт последние заказы.</p>`}
    <p class="footnote account">Расширение, Claude и выход — в <a href="#/account">аккаунте</a>.</p>`;
  const staples = document.getElementById("staples");
  const products = document.getElementById("products");

  const product = (p) => `
    <div class="line pantry-row">
      <button class="open" data-open="${esc(p.key)}">
        <span class="grow">${esc(p.name)}</span>
        <span class="qty ${p.have > 0 ? "" : "none"} ${p.missing ? "short" : ""}">${esc(p.have > 0 ? p.have_text : "нет")}</span>
      </button>
      <button class="ghost icon pin ${p.pinned ? "on" : ""}" data-pin="${esc(p.key)}" aria-pressed="${p.pinned}"
        aria-label="${p.pinned ? "Открепить" : "Всегда держать дома"}: ${esc(p.name)}" title="${p.pinned ? "Открепить" : "Всегда держать дома"}">${icon("pin")}</button>
    </div>`;
  const needRow = (p) => `
    <button class="need-row" data-open="${esc(p.key)}">
      <span class="dot missing"></span>
      <span class="grow">${esc(p.name)}${p.min_amount ? `<span class="sub">держать от ${esc(p.min_text)}</span>` : ""}</span>
      <span class="qty">${esc(p.have > 0 ? p.have_text : "нет")}</span>
    </button>`;

  function render() {
    const foldOpen = !!products.querySelector("details.fold[open]");
    const pinned = items.filter((p) => p.pinned);
    const missing = pinned.filter((p) => p.missing);
    const stocked = pinned.filter((p) => !p.missing);
    staples.innerHTML = `
      <div class="card staples ${!pinned.length ? "empty" : missing.length ? "short" : "full"}">
        <div class="staples-head">
          <span class="tile">${icon(pinned.length && !missing.length ? "check" : "pin")}</span>
          <div class="grow"><b>Всегда дома</b>
            <div class="small state">${!pinned.length
              ? "Закрепи булавкой то, что всегда должно быть дома, — здесь будет видно, чего не хватает, когда идёшь в магазин."
              : missing.length ? `не хватает ${missing.length} из ${pinned.length}` : `всё есть · ${pinned.length} ${plural(pinned.length, "продукт", "продукта", "продуктов")}`}</div>
          </div>
          ${missing.length ? `<button class="ghost" id="copy-missing">${icon("copy")} Список</button>` : ""}
        </div>
        ${missing.length ? `<div class="need">${missing.map(needRow).join("")}</div>` : ""}
        ${stocked.length ? `<div class="stocked">${stocked.map((p) =>
          `<button class="tag" data-open="${esc(p.key)}">${esc(p.name)} <span>${esc(p.have_text)}</span></button>`).join("")}</div>` : ""}
      </div>`;
    const have = items.filter((p) => p.have > 0);
    const out = items.filter((p) => !(p.have > 0));
    products.innerHTML = `
      <h2 class="section-title">Есть дома <span class="muted">${have.length}</span></h2>
      ${have.length ? `<div class="card list">${have.map(product).join("")}</div>` : `<div class="card empty-state">Пока пусто — обнови заказы из Wolt</div>`}
      ${out.length ? `
        <details class="fold" ${foldOpen ? "open" : ""}>
          <summary>Нет дома <span class="muted">${out.length}</span>${icon("down")}</summary>
          <div class="card list">${out.map(product).join("")}</div>
        </details>` : ""}`;
  }

  // the clicked row stays where it was on screen, though the card on top grows or shrinks
  function update(item, key) {
    const before = view.querySelector(`[data-pin="${CSS.escape(key)}"]`);
    const top = before && before.getBoundingClientRect().top;
    items = items.map((p) => (p.key === item.key ? item : p));
    render();
    const after = view.querySelector(`[data-pin="${CSS.escape(key)}"]`);
    if (before && after) window.scrollBy(0, after.getBoundingClientRect().top - top);
  }

  // on the page's own elements: #view outlives this tab, a listener on it would pile up
  const onClick = async (e) => {
    const pin = e.target.closest("[data-pin]");
    const open = e.target.closest("[data-open]");
    if (pin) {
      const p = items.find((x) => x.key === pin.dataset.pin);
      pin.disabled = true;
      try {
        update(await api(`/api/v1/pantry/${encodeURIComponent(p.key)}/pin`, p.pinned ? { method: "DELETE" } : { method: "PUT", body: {} }), p.key);
      } catch (err) { alert(err.message); pin.disabled = false; }
    } else if (open) {
      const saved = await editProduct(items.find((x) => x.key === open.dataset.open));
      if (saved) update(saved, saved.key);
    } else if (e.target.closest("#copy-missing")) {
      const btn = e.target.closest("#copy-missing");
      const text = ["Купить:", ...items.filter((p) => p.missing).map((p) =>
        `— ${p.name}${p.have > 0 ? ` (дома ${p.have_text}, держать от ${p.min_text})` : ""}`)].join("\n");
      if (await copyText(text)) {
        btn.innerHTML = `${icon("check")} Скопировано`;
        setTimeout(() => { if (btn.isConnected) btn.innerHTML = `${icon("copy")} Список`; }, 2500);
      } else showText("Чего не хватает", text);
    }
  };
  staples.addEventListener("click", onClick);
  products.addEventListener("click", onClick);
  render();

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
}

// A product's sheet: how much is at home, and whether to always keep it there (and how much at least).
// Resolves with the product as saved, or null if cancelled.
function editProduct(p) {
  const unit = UNITS[p.base_unit];
  const dlg = document.createElement("dialog");
  dlg.innerHTML = `
    <form method="dialog" class="stack" novalidate>
      <h2>${esc(p.name)}</h2>
      <label class="small muted" for="pp-have">Сейчас дома, ${unit}</label>
      <input id="pp-have" name="have" inputmode="decimal" autocomplete="off" value="${esc(fmtNumber(Math.max(p.have, 0)))}">
      <label class="check">
        <input type="checkbox" name="pinned" ${p.pinned ? "checked" : ""}>
        <span><b>Всегда держать дома</b>
          <span class="small muted">Закончится — окажется сверху на «Дома», в списке того, что купить.</span></span>
      </label>
      <div class="stack" data-min ${p.pinned ? "" : "hidden"}>
        <label class="small muted" for="pp-min">Держать не меньше, ${unit}</label>
        <input id="pp-min" name="min" inputmode="decimal" autocomplete="off" placeholder="пусто — когда совсем закончится"
          value="${p.min_amount ? esc(fmtNumber(p.min_amount)) : ""}">
      </div>
      <p class="error small" hidden></p>
      <div class="row between">
        <button type="button" class="ghost" data-cancel>Отмена</button>
        <button class="primary">Сохранить</button>
      </div>
    </form>`;
  const form = dlg.querySelector("form");
  const errorEl = dlg.querySelector(".error");
  const fail = (text) => { errorEl.textContent = text; errorEl.hidden = false; };
  form.pinned.addEventListener("change", () => { dlg.querySelector("[data-min]").hidden = !form.pinned.checked; });
  dlg.querySelector("[data-cancel]").addEventListener("click", () => dlg.close());
  document.body.appendChild(dlg);
  return new Promise((resolve) => {
    let saved = null;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const have = parseNumber(form.have.value);
      const least = form.min.value.trim() === "" ? null : parseNumber(form.min.value);
      if (!(have >= 0)) return fail(`Сколько дома — число в ${unit}, например 0 или 1,5.`);
      if (least !== null && !(least > 0)) return fail("Минимум — число больше нуля, или оставь пустым.");
      const key = encodeURIComponent(p.key);
      const btn = form.querySelector("button.primary");
      btn.disabled = true;
      try {
        let item = p;
        if (have !== Math.max(p.have, 0)) item = await api(`/api/v1/pantry/${key}`, { method: "PUT", body: { amount: have } });
        if (form.pinned.checked && (!p.pinned || least !== p.min_amount)) {
          item = await api(`/api/v1/pantry/${key}/pin`, { method: "PUT", body: { min_amount: least } });
        } else if (!form.pinned.checked && p.pinned) item = await api(`/api/v1/pantry/${key}/pin`, { method: "DELETE" });
        saved = item;
        dlg.close();
      } catch (err) { fail(err.message); btn.disabled = false; }
    });
    dlg.addEventListener("close", () => { dlg.remove(); resolve(saved); });
    dlg.showModal();
  });
}

// ---------- accounts ----------

const initial = (login) => login.slice(0, 1).toUpperCase();
const fmtWhen = (iso) => new Date(iso).toLocaleString("ru-RU", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });

// Who you are here, and what is connected to this account: the Chrome extension and Claude.
async function accountView() {
  let [connections, syncs, ownSound] = await Promise.all([
    api("/api/v1/claude/connections"), api("/api/v1/wolt-orders/sync-log?limit=1"), api("/api/v1/timer-sound"),
  ]);
  const ext = extensionVersion();
  const mcpUrl = `${location.origin}/mcp`;
  view.innerHTML = `
    <div class="page-head"><h1>Аккаунт</h1></div>
    <div class="card profile">
      <span class="avatar big">${esc(initial(me.login))}</span>
      <div class="grow"><b>${esc(me.login)}</b><div class="small muted">твой аккаунт в eaty</div></div>
      <button class="ghost" id="logout">${icon("logout")} Выйти</button>
    </div>

    <h2>Оформление</h2>
    <div class="card stack">
      <div class="seg wide" role="radiogroup" aria-label="Тема" id="theme">
        ${Object.entries(THEMES).map(([key, label]) => `<button class="${savedTheme() === key ? "on" : ""}" data-theme-pick="${key}" role="radio" aria-checked="${savedTheme() === key}">${icon(key)} ${label}</button>`).join("")}
      </div>
      <div class="small muted">«Авто» — как в системе телефона или компьютера. Выбор запоминается на этом устройстве.</div>
    </div>

    <h2>Таймеры</h2>
    <div class="card stack" id="timer-settings">
      ${IOS ? `
      <div class="seg wide two" role="radiogroup" aria-label="Чем звонит таймер">
        ${[[false, "timer", "Звонит eaty"], [true, "alarm", "Часы iPhone"]].map(([on, ic, label]) => `
        <button class="${clockTimers() === on ? "on" : ""}" data-clock="${on ? 1 : ""}" role="radio" aria-checked="${clockTimers() === on}">${icon(ic)} ${label}</button>`).join("")}
      </div>` : ""}
      <div class="note stack"></div>
      <input type="file" id="sound-file" accept="audio/*" hidden>
    </div>

    <h2>Расширение для Chrome</h2>
    <div class="card stack">
      ${ext ? `
      <div class="row" id="ext-account" hidden>
        <span class="dot"></span><span class="grow"></span>
        <button id="ext-connect">Подключить расширение</button>
      </div>` : `
      <div class="row"><span class="dot missing"></span>
        <span class="grow">На этой странице расширения нет. Оно работает в Chrome на компьютере — там его и ставят.</span></div>`}
      <div class="small muted">${ext ? `Версия ${esc(ext)}. ` : ""}${esc(syncs.length
        ? `Последняя синхронизация — ${syncSummary(syncs[0])}` : "Синхронизаций с Wolt ещё не было.")}</div>
      <div class="small"><a href="/guide#extension">${ext ? "Как обновить" : "Как установить"}</a> ·
        <a href="#/pantry">Заказы и продукты — во вкладке «Дома»</a></div>
    </div>

    <h2>Claude</h2>
    <div class="card stack">
      ${connections.length ? connections.map((c) => `
      <div class="row">
        <span class="dot ok"></span>
        <div class="grow"><b>${esc(c.name)}</b>
          <div class="small muted">подключён · последний вход ${esc(fmtWhen(c.signed_in_at))}</div></div>
        <button class="ghost" data-disconnect="${esc(c.client_id)}" data-name="${esc(c.name)}">Отключить</button>
      </div>`).join("") : `
      <div class="row"><span class="dot missing"></span>
        <span class="grow">Claude ещё не подключён. Подключи eaty к своему Claude — и он сам соберёт корзины в Wolt по меню, на твоей подписке Claude.</span></div>`}
      <div class="row">
        <input class="grow" id="mcp-url" readonly value="${esc(mcpUrl)}">
        <button id="mcp-copy">Скопировать</button>
      </div>
      <div class="small muted">claude.ai или приложение Claude: Customize → Connectors → «+» → Add custom connector,
        вставить адрес и войти в eaty. Claude Code: <code>claude mcp add --transport http eaty ${esc(mcpUrl)}</code>.
        Потом выбери промпт «Собрать корзину в Wolt» (в Claude Code — <code>/mcp__eaty__wolt_order</code>). Корзину Claude
        собирает в браузере, где открыт твой Wolt: нужен Claude, который управляет Chrome (Claude в Chrome, Claude Code с /chrome).
        <a href="/guide#claude">Пошаговая инструкция</a>.</div>
    </div>`;

  document.getElementById("logout").addEventListener("click", logout);
  document.getElementById("theme").addEventListener("click", (e) => {
    const b = e.target.closest("[data-theme-pick]");
    if (!b) return;
    pickTheme(b.dataset.themePick);
    view.querySelectorAll("[data-theme-pick]").forEach((x) => {
      x.classList.toggle("on", x === b);
      x.setAttribute("aria-checked", x === b);
    });
  });
  if (ownSound) pickTimerSound(timerSound(), ownSound.updated_at); // the alarm takes the latest upload
  else if (timerSound() === "own") pickTimerSound("alarm");        // removed on another device
  const timerCard = document.getElementById("timer-settings");
  const timerNote = () => {
    const sounds = [...Object.entries(SOUNDS).map(([kind, s]) => [kind, s.name]), ...(ownSound ? [["own", ownSound.name]] : [])];
    timerCard.querySelector(".note").innerHTML = clockTimers() ? `
      <div class="small muted">Таймер из шага уходит в «Часы»: звенит, как обычный таймер айфона, — и в беззвучном режиме,
        и на заблокированном экране, а отсчёт виден на экране блокировки. Айфон на миг откроет «Быстрые команды» —
        назад в eaty стрелкой ◀ слева вверху. Звук — тот, что выбран в «Часах». Один раз нужна быстрая команда:</div>
      <ol class="howto small">
        <li>Открой «Быстрые команды» (Shortcuts) → «+».</li>
        <li>Добавь действие «Запустить таймер» (Start Timer) из «Часов».</li>
        <li>Тапни на число в действии, выбери вместо него переменную «Входные данные команды» (Shortcut Input), единицы — секунды.</li>
        <li>Назови команду «${esc(CLOCK_SHORTCUT)}» — точно так.</li>
      </ol>
      <button id="clock-test">${icon("alarm")} Проверить — таймер на 10 секунд</button>` : `
      <div class="sounds" role="radiogroup" aria-label="Звук таймера">
        ${sounds.map(([kind, name]) => `
        <div class="sound ${timerSound() === kind ? "on" : ""}">
          <button data-sound="${kind}" role="radio" aria-checked="${timerSound() === kind}">
            <span class="grow">${kind === "own" ? `Свой · ${esc(name)}` : esc(name)}</span>${timerSound() === kind ? icon("check") : ""}</button>
          ${kind === "own" ? `<button class="icon ghost" id="sound-delete" aria-label="Убрать свой звук">${icon("close")}</button>` : ""}
        </div>`).join("")}
      </div>
      <button id="sound-upload">${icon("plus")} ${ownSound ? "Заменить свой звук" : "Загрузить свой звук"}</button>
      <div class="small muted">Тапни звук, чтобы послушать. Свой — mp3, m4a или wav до 2 МБ, хранится в аккаунте:
        он есть на всех твоих устройствах, а какой звенит — выбирается на каждом.</div>
      ${IOS ? `<div class="small muted">eaty звенит сам, громко и в беззвучном режиме, пока не нажмёшь «Стоп», а экран с таймером не гаснет.
        Но только пока eaty открыт: заблокированный айфон усыпляет сайты, и они молчат. Чтобы звенело и так —
        выбери «Часы iPhone».</div>` : ""}`;
  };
  timerNote();
  timerCard.addEventListener("click", async (e) => {
    if (e.target.closest("#clock-test")) return startClockTimer(10);
    if (e.target.closest("#sound-upload")) return document.getElementById("sound-file").click();
    const sound = e.target.closest("[data-sound]");
    if (sound) {
      pickTimerSound(sound.dataset.sound);
      previewSound(sound.dataset.sound);
      return timerNote();
    }
    if (e.target.closest("#sound-delete")) {
      if (!confirm(`Убрать свой звук «${ownSound.name}»?`)) return;
      try {
        await api("/api/v1/timer-sound", { method: "DELETE" });
        ownSound = null;
        if (timerSound() === "own") pickTimerSound("alarm");
        timerNote();
      } catch (err) { alert(err.message); }
      return;
    }
    const clock = e.target.closest("[data-clock]");
    if (!clock) return;
    pickClockTimers(!!clock.dataset.clock);
    timerCard.querySelectorAll("[data-clock]").forEach((x) => {
      x.classList.toggle("on", x === clock);
      x.setAttribute("aria-checked", x === clock);
    });
    timerNote();
  });
  document.getElementById("sound-file").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    e.target.value = ""; // the same file again is a change too
    if (!file) return;
    const upload = document.getElementById("sound-upload");
    upload.disabled = true;
    upload.textContent = "Загружаю…";
    try {
      ownSound = await api(`/api/v1/timer-sound?name=${encodeURIComponent(file.name)}`, {
        method: "PUT", body: file, headers: { "Content-Type": file.type || "application/octet-stream" },
      });
      pickTimerSound("own", ownSound.updated_at);
      previewSound("own");
    } catch (err) { alert(err.message); }
    timerNote();
  });
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
  view.querySelectorAll("[data-disconnect]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm(`Отключить ${b.dataset.name} от eaty? Чтобы подключить снова, Claude попросит разрешения ещё раз.`)) return;
    b.disabled = true;
    try {
      await api(`/api/v1/claude/connections/${encodeURIComponent(b.dataset.disconnect)}`, { method: "DELETE" });
      route();
    } catch (err) {
      b.disabled = false;
      alert(err.message);
    }
  }));
}

function authView(mode = "login") {
  const signup = mode === "signup";
  document.body.classList.add("signed-out");
  view.innerHTML = `
    <div class="auth">
      <h1 class="brand" aria-label="eaty">${document.querySelector(".topbar .logo").outerHTML.replaceAll("bite", "bite-auth")}</h1>
      <p class="tagline">Меню на неделю, рецепты и продукты из Wolt</p>
      <p class="muted">${signup ? "У каждого свой план, список покупок и продукты дома." : "Войди, чтобы увидеть свой план, покупки и продукты дома."}</p>
      <form class="card stack" id="auth" novalidate>
        <label class="small muted" for="auth-login">Логин</label>
        <input id="auth-login" name="login" autocomplete="username" autocapitalize="none" spellcheck="false" required>
        <label class="small muted" for="auth-password">Пароль</label>
        <input id="auth-password" name="password" type="password" autocomplete="${signup ? "new-password" : "current-password"}" required>
        ${signup ? `<p class="small muted">Логин — от 3 символов, без пробелов. Пароль — от 8 символов.</p>` : ""}
        <p class="error small" id="auth-error" hidden></p>
        <button class="primary block">${signup ? "Зарегистрироваться" : "Войти"}</button>
      </form>
      <p class="small switch-mode">${signup ? `Уже есть аккаунт? <a href="#" data-mode="login">Войти</a>` : `Нет аккаунта? <a href="#" data-mode="signup">Зарегистрироваться</a>`}</p>
      <p class="small muted switch-mode"><a href="/guide">Как подключить расширение для Wolt и Claude</a></p>
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
  const tab = parts[0] === "account" ? null
    : { week: "week", recipes: "recipes", shop: "shop", pantry: "pantry" }[parts[0]]
      || (parts[0] === "recipe" && !params.get("day") ? "recipes" : "day");
  document.querySelectorAll(".tabs a").forEach((a) => a.classList.toggle("active", a.dataset.tab === tab));
  avatar.classList.toggle("active", parts[0] === "account");
  try {
    me = me || await api("/api/v1/auth/me");
  } catch (err) {
    if (err.status === 401) authView(); else showError(err);
    return;
  }
  document.body.classList.remove("signed-out");
  avatar.textContent = initial(me.login);
  try {
    if (parts[0] === "recipe") await recipeView(+parts[1], params);
    else if (parts[0] === "account") await accountView();
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
