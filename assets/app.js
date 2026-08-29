(() => {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor("#07140e");
    tg.setBackgroundColor("#07140e");
    if (typeof tg.enableClosingConfirmation === "function") tg.enableClosingConfirmation();
  }

  const DAYS = ["Yak", "Du", "Se", "Cho", "Pay", "Ju", "Sha"];
  const DAYS_FULL = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
  const MONTHS = ["yanvar","fevral","mart","aprel","may","iyun","iyul","avgust","sentabr","oktabr","noyabr","dekabr"];
  const STATUS = {
    green: "Bo'sh",
    blue: "Qisman bo'sh",
    red: "Band",
    orange: "Tasdiq kutilmoqda",
  };

  const state = {
    config: null,
    snapshot: null,
    date: null,
    viewYear: null,
    viewMonth: null,
    slots: null,
    start: null,
    end: null,
    pendingStart: null,
  };

  const $ = (id) => document.getElementById(id);
  const CFG = window.STADION_CONFIG || {};

  function tashkentToday() {
    return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tashkent" }).format(new Date());
  }

  function tashkentNowMin() {
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Asia/Tashkent",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(new Date());
    const hour = Number((parts.find((p) => p.type === "hour") || {}).value || 0);
    const minute = Number((parts.find((p) => p.type === "minute") || {}).value || 0);
    return hour * 60 + minute;
  }

  function queryParam(name) {
    try {
      return new URLSearchParams(location.search).get(name) || "";
    } catch (err) {
      return "";
    }
  }

  function isGithubPages() {
    return location.hostname.endsWith("github.io");
  }

  function apiBase() {
    const manual = (queryParam("api") || String(CFG.apiBase || "")).trim().replace(/\/$/, "");
    if (manual) return manual;
    if (isGithubPages()) return null;
    return "";
  }

  function botUsername() {
    const fromSnap = state.snapshot && state.snapshot.bot_username;
    return (
      queryParam("bot") ||
      String(CFG.botUsername || "") ||
      String(fromSnap || "")
    )
      .trim()
      .replace(/^@/, "");
  }

  function githubRepo() {
    if (CFG.githubRepo) return String(CFG.githubRepo).replace(/^\/|\/$/g, "");
    if (!isGithubPages()) return "";
    const user = location.hostname.split(".")[0];
    const parts = location.pathname.split("/").filter(Boolean);
    const repo = parts[0] || `${user}.github.io`;
    return `${user}/${repo}`;
  }

  function occupiedMinutes(intervals, start, end) {
    const clipped = [];
    for (const [s, e] of intervals) {
      const a = Math.max(s, start);
      const b = Math.min(e, end);
      if (a < b) clipped.push([a, b]);
    }
    if (!clipped.length) return 0;
    clipped.sort((x, y) => x[0] - y[0]);
    const merged = [clipped[0].slice()];
    for (const [s, e] of clipped.slice(1)) {
      if (s <= merged[merged.length - 1][1]) {
        merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], e);
      } else merged.push([s, e]);
    }
    return merged.reduce((sum, [a, b]) => sum + (b - a), 0);
  }

  function normalizeOccupied(list) {
    return (list || [])
      .map((b) => ({
        start_min: Number(b.start_min),
        end_min: Number(b.end_min),
        status: String(b.status || "confirmed"),
      }))
      .filter((b) => b.end_min > b.start_min);
  }

  function hourColor(hour, bookings, closeMin) {
    const start = hour * 60;
    let end = hour * 60 + 60;
    if (closeMin != null) end = Math.min(end, closeMin);
    const available = Math.max(0, end - start);
    if (available <= 0) return "green";
    const list = normalizeOccupied(bookings);
    const confirmed = [];
    const pending = [];
    for (const b of list) {
      const s = b.status;
      if (s === "cancelled" || s === "rejected") continue;
      if (s === "pending_payment" || s === "pending_review") pending.push([b.start_min, b.end_min]);
      else confirmed.push([b.start_min, b.end_min]);
    }
    const bookedMins = occupiedMinutes(confirmed, start, end);
    const pendingMins = occupiedMinutes(pending, start, end);
    if (bookedMins >= available) return "red";
    if (pendingMins >= available) return "orange";
    if (bookedMins > 0 || pendingMins > 0) return "blue";
    return "green";
  }

  function buildHours(openMin, closeMin, occupied) {
    let startHour = Math.floor(openMin / 60);
    let endHour = Math.floor((closeMin + 59) / 60);
    if (closeMin % 60 === 0) endHour = closeMin / 60;
    const hours = [];
    for (let h = startHour; h < endHour; h += 1) {
      const labelStart = h * 60;
      const labelEnd = Math.min(h * 60 + 60, closeMin);
      hours.push({
        hour: h,
        start_min: labelStart,
        end_min: labelEnd,
        label: displayRange(labelStart, labelEnd),
        color: hourColor(h, occupied, closeMin),
      });
    }
    return hours;
  }

  function formatSum(n) {
    return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function hhmm(min) {
    const h = Math.floor(min / 60);
    const m = min % 60;
    if (h >= 24 && m === 0) return "24:00";
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  }

  function displayRange(start, end) {
    const last = Math.max(start, end - 1);
    return `${hhmm(start)}/${hhmm(last)}`;
  }

  function durationText(start, end) {
    const mins = Math.max(0, end - start);
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    const parts = [];
    if (h) parts.push(`${h} soat`);
    if (m) parts.push(`${m} daqiqa`);
    return parts.join(" ") || "0 daqiqa";
  }

  function ymd(d) {
    const z = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
  }

  function parseYmd(s) {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d);
  }

  function ceil30(min) {
    return Math.ceil(min / 30) * 30;
  }

  function overlaps(s, e, occ) {
    return (occ || []).some((o) => s < o.end_min && o.start_min < e);
  }

  function headers() {
    const h = { "Content-Type": "application/json" };
    if (tg && tg.initData) h["X-Telegram-Init-Data"] = tg.initData;
    return h;
  }

  async function api(path, opts = {}) {
    const base = apiBase();
    const url = `${base || ""}${path}`;
    const res = await fetch(url, {
      ...opts,
      headers: { ...headers(), ...(opts.headers || {}) },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || data.message || "Xatolik";
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;
  }

  async function fetchJson(url, extraHeaders) {
    const res = await fetch(url, {
      cache: "no-store",
      headers: extraHeaders || {},
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data && typeof data.content === "string" && data.encoding === "base64") {
      const bin = atob(data.content.replace(/\s/g, ""));
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
      return JSON.parse(new TextDecoder("utf-8").decode(bytes));
    }
    if (data && data.days && typeof data.days === "object") return data;
    throw new Error("JSON emas");
  }

  async function loadSnapshot() {
    const repo = githubRepo();
    const branch = CFG.githubBranch || "main";
    const stamp = Date.now();
    const urls = [];
    if (repo) {
      urls.push({ url: `https://raw.githubusercontent.com/${repo}/${branch}/webapp/data/public.json?t=${stamp}` });
      urls.push({ url: `https://raw.githubusercontent.com/${repo}/${branch}/data/public.json?t=${stamp}` });
      urls.push({
        url: `https://api.github.com/repos/${repo}/contents/webapp/data/public.json?ref=${branch}&t=${stamp}`,
        headers: { Accept: "application/vnd.github+json" },
      });
      urls.push({
        url: `https://api.github.com/repos/${repo}/contents/data/public.json?ref=${branch}&t=${stamp}`,
        headers: { Accept: "application/vnd.github+json" },
      });
    }
    urls.push({ url: `./data/public.json?t=${stamp}` });
    urls.push({ url: `./webapp/data/public.json?t=${stamp}` });
    let lastErr = "Bron ma'lumoti yuklanmadi";
    const found = [];
    for (const item of urls) {
      try {
        const data = await fetchJson(item.url, item.headers);
        if (data && data.days && typeof data.days === "object") found.push(data);
      } catch (err) {
        lastErr = err.message || lastErr;
      }
    }
    if (!found.length) throw new Error(lastErr);
    found.sort((a, b) => {
      const ta = Date.parse(a.updated_at || "") || 0;
      const tb = Date.parse(b.updated_at || "") || 0;
      if (tb !== ta) return tb - ta;
      const occ = (s) =>
        Object.values(s.days || {}).reduce((n, d) => n + ((d && d.occupied) || []).length, 0);
      return occ(b) - occ(a);
    });
    return found[0];
  }

  function snapshotToConfig(snap) {
    const today = tashkentToday();
    return {
      stadium_name: snap.stadium_name,
      address: snap.address,
      hourly_price: snap.hourly_price,
      hourly_price_text: snap.hourly_price_text,
      open_min: snap.open_min,
      close_min: snap.close_min,
      work_days: snap.work_days || [0, 1, 2, 3, 4, 5, 6],
      today,
      now_min: tashkentNowMin(),
      days: snap.days || {},
    };
  }

  function effectiveNowMin(date) {
    const today = (state.config && state.config.today) || tashkentToday();
    if (date < today) return 24 * 60;
    if (date === today) return tashkentNowMin();
    return -1;
  }

  function isHourPast(h, nowMin) {
    if (nowMin < 0) return false;
    if (nowMin >= h.end_min) return true;
    return ceil30(nowMin) >= h.end_min;
  }

  function workDays() {
    const raw =
      (state.config && state.config.work_days) ||
      (state.snapshot && state.snapshot.work_days) ||
      [0, 1, 2, 3, 4, 5, 6];
    if (Array.isArray(raw)) return raw.map(Number);
    return String(raw)
      .split(",")
      .map((n) => Number(n.trim()))
      .filter((n) => n >= 0 && n <= 6);
  }

  function weekdayMon0(dateStr) {
    const d = parseYmd(dateStr);
    return (d.getDay() + 6) % 7;
  }

  function dateIsRest(dateStr) {
    const days = workDays();
    if (!days.length) return false;
    return !days.includes(weekdayMon0(dateStr));
  }

  function dateFullyPast(date) {
    return effectiveNowMin(date) >= 24 * 60;
  }

  function slotsFromSnapshot(date) {
    const snap = state.snapshot || {};
    const openMin = Number(snap.open_min || 0);
    const closeMin = Number(snap.close_min || 1440);
    const occupied = normalizeOccupied(((snap.days || {})[date] || {}).occupied || []);
    return {
      date,
      open_min: openMin,
      close_min: closeMin,
      now_min: effectiveNowMin(date),
      hourly_price: Number(snap.hourly_price || 0),
      hours: buildHours(openMin, closeMin, occupied),
      occupied,
    };
  }

  function applyLocalBooking() {
    if (state.start == null || state.end == null || !state.date) return;
    const occ = {
      start_min: Number(state.start),
      end_min: Number(state.end),
      status: "pending_payment",
    };
    if (!state.snapshot) state.snapshot = { days: {}, open_min: 360, close_min: 1440 };
    if (!state.snapshot.days) state.snapshot.days = {};
    if (!state.snapshot.days[state.date]) state.snapshot.days[state.date] = { occupied: [] };
    state.snapshot.days[state.date].occupied = normalizeOccupied(
      (state.snapshot.days[state.date].occupied || []).concat([occ])
    );
    state.slots = slotsFromSnapshot(state.date);
  }

  function paintSlots(payload) {
    const openMin = Number(payload.open_min || 0);
    const closeMin = Number(payload.close_min || 1440);
    const occupied = normalizeOccupied(payload.occupied || []);
    state.slots = {
      date: payload.date || state.date,
      open_min: openMin,
      close_min: closeMin,
      now_min: effectiveNowMin(state.date),
      hourly_price: Number(payload.hourly_price || 0),
      hours: buildHours(openMin, closeMin, occupied),
      occupied,
    };
  }

  function toast(text) {
    const el = $("toast");
    el.textContent = text;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.hidden = true; }, 2800);
    if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
  }

  function renderDates() {
    const today = state.config.today;
    const todayDt = parseYmd(today);
    if (state.viewYear == null) {
      state.viewYear = todayDt.getFullYear();
      state.viewMonth = todayDt.getMonth();
    }

    const titleMonths = ["Yanvar","Fevral","Mart","Aprel","May","Iyun","Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"];
    $("calTitle").textContent = `${titleMonths[state.viewMonth]} ${state.viewYear}`;

    const week = $("calWeekdays");
    if (week && !week.childElementCount) {
      ["Du", "Se", "Cho", "Pay", "Ju", "Sha", "Yak"].forEach((name) => {
        const el = document.createElement("div");
        el.textContent = name;
        week.appendChild(el);
      });
    }

    const first = new Date(state.viewYear, state.viewMonth, 1);
    const startPad = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(state.viewYear, state.viewMonth + 1, 0).getDate();
    const grid = $("calGrid");
    grid.innerHTML = "";

    const minMonth = todayDt.getFullYear() * 12 + todayDt.getMonth();
    const viewIndex = state.viewYear * 12 + state.viewMonth;
    $("calPrev").disabled = viewIndex <= minMonth;

    for (let i = 0; i < startPad; i += 1) {
      const empty = document.createElement("div");
      empty.className = "cal-day empty";
      grid.appendChild(empty);
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      const d = new Date(state.viewYear, state.viewMonth, day);
      const key = ymd(d);
      const past = key < today;
      const btn = document.createElement("button");
      btn.type = "button";
      const rest = !past && dateIsRest(key);
      const busy = past || rest ? "" : dayOccupancyColor(key);
      btn.className =
        "cal-day" +
        (key === state.date ? " active" : "") +
        (past ? " past" : "") +
        (rest ? " rest" : "") +
        (key === today ? " today" : "") +
        (busy ? ` ${busy}` : "");
      btn.textContent = String(day);
      btn.addEventListener("click", () => {
        state.date = key;
        state.start = null;
        state.end = null;
        renderDates();
        if (dateIsRest(key) && key >= today) toast("Bu kun dam olish — bron qilib bo'lmaydi");
        loadSlots();
      });
      grid.appendChild(btn);
    }
  }

  const HOUR_PAINT = {
    green: { bg: "rgba(34,197,94,0.34)", fg: "#dcfce7", bar: "#22c55e" },
    blue: { bg: "rgba(37,99,235,0.5)", fg: "#dbeafe", bar: "#3b82f6" },
    red: { bg: "rgba(220,38,38,0.52)", fg: "#fecaca", bar: "#ef4444" },
    orange: { bg: "rgba(234,88,12,0.55)", fg: "#ffedd5", bar: "#f97316" },
    past: { bg: "#2a2d2b", fg: "#9ca3af", bar: "#6b7280" },
  };

  function dayOccupancyColor(date) {
    const occupied = normalizeOccupied((((state.snapshot || {}).days || {})[date] || {}).occupied || []);
    if (!occupied.length) return "";
    const closeMin = Number((state.snapshot && state.snapshot.close_min) || 1440);
    const colors = new Set(occupied.map((b) => hourColor(Math.floor(b.start_min / 60), occupied, closeMin)));
    if (colors.has("red")) return "busy-red";
    if (colors.has("orange")) return "busy-orange";
    if (colors.has("blue")) return "busy-blue";
    return "busy-blue";
  }

  function colorLabel(color) {
    return STATUS[color] || color;
  }

  function renderHours() {
    const box = $("hours");
    box.innerHTML = "";
    const d = parseYmd(state.date);
    $("dayTitle").textContent = `${DAYS_FULL[d.getDay()]}, ${d.getDate()}-${MONTHS[d.getMonth()]}`;
    if (dateIsRest(state.date) && !dateFullyPast(state.date)) {
      box.innerHTML = "<p class='muted'>Dam olish kuni — bron qilib bo'lmaydi</p>";
      return;
    }
    const nowMin = effectiveNowMin(state.date);
    const start = state.start;
    const end = state.end;
    const fullyPast = dateFullyPast(state.date);
    for (const h of (state.slots && state.slots.hours) || []) {
      const past = fullyPast || isHourPast(h, nowMin);
      const color = past ? "past" : h.color;
      const paint = HOUR_PAINT[color] || HOUR_PAINT.green;
      const inRange = !past && start != null && end != null && h.start_min < end && start < h.end_min;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `hour ${color}${inRange ? " in-range" : ""}`;
      btn.setAttribute("data-color", color);
      btn.style.background = paint.bg;
      btn.style.color = paint.fg;
      btn.style.boxShadow = `inset 5px 0 0 ${paint.bar}`;
      btn.innerHTML = `<div class="t">${h.label}</div><div class="s">${past ? "O'tib ketgan" : colorLabel(h.color)}</div>`;
      btn.addEventListener("click", () => onHourClick(h, past));
      box.appendChild(btn);
    }
  }

  function firstFreeStart(hourStart, hourEnd) {
    const occ = state.slots.occupied;
    const nowMin = effectiveNowMin(state.date);
    let t = hourStart;
    if (nowMin >= 0) t = Math.max(t, ceil30(nowMin));
    for (; t + 30 <= Math.min(hourEnd, state.slots.close_min); t += 30) {
      if (!overlaps(t, t + 30, occ)) return t;
    }
    return null;
  }

  function onHourClick(h, past) {
    if (past) return;
    if (dateIsRest(state.date)) {
      toast("Bu kun dam olish — bron qilib bo'lmaydi");
      return;
    }
    if (h.color === "red") {
      toast("Bu soat band. Boshqa vaqt tanlang.");
      return;
    }
    if (h.color === "orange") {
      toast("Bu soat kutilmoqda. Boshqa vaqt tanlang yoki admin bilan bog'laning.");
      return;
    }
    const start = firstFreeStart(h.start_min, h.end_min);
    if (start == null) {
      toast("Bu soatda bron qilish uchun bo'sh 30 daqiqa yo'q");
      return;
    }
    if (tg && tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
    state.start = start;
    fillStartSelect();
    $("startSel").value = String(start);
    fillEndSelect();
    const firstEnd = $("endSel").options[0];
    state.end = firstEnd ? Number(firstEnd.value) : null;
    if (state.end) $("endSel").value = String(state.end);
    updateSummary();
    renderHours();
  }

  function fillStartSelect() {
    const sel = $("startSel");
    const occ = state.slots.occupied;
    const nowMin = effectiveNowMin(state.date);
    const open = state.slots.open_min;
    const close = state.slots.close_min;
    const prev = state.start;
    sel.innerHTML = "";
    let first = null;
    for (let t = open; t + 30 <= close; t += 30) {
      if (nowMin >= 0 && t < ceil30(nowMin)) continue;
      if (overlaps(t, t + 30, occ)) continue;
      const opt = document.createElement("option");
      opt.value = String(t);
      opt.textContent = hhmm(t);
      sel.appendChild(opt);
      if (first == null) first = t;
    }
    if (!sel.options.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Bo'sh yo'q";
      sel.appendChild(opt);
      state.start = null;
      return;
    }
    if (prev != null && [...sel.options].some((o) => Number(o.value) === prev)) {
      sel.value = String(prev);
      state.start = prev;
    } else {
      state.start = Number(sel.value || first);
    }
  }

  function fillEndSelect() {
    const sel = $("endSel");
    const occ = state.slots.occupied;
    const close = state.slots.close_min;
    const start = state.start;
    const prev = state.end;
    sel.innerHTML = "";
    if (start == null) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "—";
      sel.appendChild(opt);
      state.end = null;
      return;
    }
    for (let t = start + 30; t <= close; t += 30) {
      if (overlaps(start, t, occ)) break;
      const opt = document.createElement("option");
      opt.value = String(t);
      opt.textContent = `${hhmm(t)}  (${displayRange(start, t)})`;
      sel.appendChild(opt);
    }
    if (!sel.options.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Band";
      sel.appendChild(opt);
      state.end = null;
      return;
    }
    if (prev != null && [...sel.options].some((o) => Number(o.value) === prev)) {
      sel.value = String(prev);
      state.end = prev;
    } else {
      state.end = Number(sel.value);
    }
  }

  function updateSummary() {
    const box = $("summary");
    const btn = $("bookBtn");
    const priceHour = state.slots.hourly_price || (state.config && state.config.hourly_price) || 0;
    if (dateFullyPast(state.date)) {
      box.innerHTML = "Bu kun o'tib ketgan — bron qilib bo'lmaydi";
      btn.disabled = true;
      btn.textContent = "Bron qilish";
      $("startSel").disabled = true;
      $("endSel").disabled = true;
      return;
    }
    if (dateIsRest(state.date)) {
      box.innerHTML = "Dam olish kuni — bron qilib bo'lmaydi";
      btn.disabled = true;
      btn.textContent = "Bron qilish";
      $("startSel").disabled = true;
      $("endSel").disabled = true;
      return;
    }
    $("startSel").disabled = false;
    $("endSel").disabled = false;
    if (state.start == null || state.end == null) {
      box.innerHTML = "Vaqt oralig'ini tanlang";
      btn.disabled = true;
      btn.textContent = "Bron qilish";
      return;
    }
    const mins = state.end - state.start;
    const price = Math.round(priceHour * mins / 60);
    box.innerHTML =
      `<b>${displayRange(state.start, state.end)}</b> · ${durationText(state.start, state.end)}<br>` +
      `<span class="sum">${formatSum(price)} so'm</span>`;
    btn.disabled = false;
    btn.textContent = `Bron qilish · ${formatSum(price)} so'm`;
  }

  async function loadSlots() {
    const first = !$("hours").querySelector(".hour");
    if (first) $("hours").innerHTML = "<p class='muted'>Yuklanmoqda…</p>";
    try {
      if (apiBase() === null) {
        try {
          const snap = await loadSnapshot();
          state.snapshot = snap;
          if (state.config) {
            state.config.hourly_price = snap.hourly_price;
            state.config.hourly_price_text = snap.hourly_price_text;
            state.config.open_min = snap.open_min;
            state.config.close_min = snap.close_min;
            state.config.work_days = snap.work_days || state.config.work_days;
            state.config.days = snap.days || {};
          }
        } catch (err) {
          if (!state.snapshot) throw err;
        }
        state.slots = slotsFromSnapshot(state.date);
        if (dateIsRest(state.date)) {
          state.slots.hours = [];
          state.slots.occupied = [];
          state.slots.rest = true;
        }
      } else {
        const payload = await api(`/api/slots?date=${state.date}`);
        paintSlots(payload);
        if (payload.rest) {
          $("hours").innerHTML = "<p class='muted'>Dam olish kuni — bron qilib bo'lmaydi</p>";
          fillStartSelect();
          fillEndSelect();
          updateSummary();
          renderDates();
          return;
        }
      }
      fillStartSelect();
      fillEndSelect();
      updateSummary();
      renderHours();
      renderDates();
    } catch (err) {
      $("hours").innerHTML = `<p class="muted">${err.message}</p>`;
    }
  }

  function showOk(title, hint, btnText) {
    const titleEl = $("okTitle");
    const hintEl = $("okHint");
    if (titleEl) titleEl.textContent = title;
    if (hintEl) hintEl.textContent = hint;
    $("closeBtn").textContent = btnText;
    $("okModal").hidden = false;
  }

  function bookViaTelegram() {
    applyLocalBooking();
    renderHours();
    updateSummary();
    const payload = `b${String(state.date).replace(/-/g, "")}-${state.start}-${state.end}`;
    state.pendingStart = payload;
    if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
    $("okText").textContent =
      `${displayRange(state.start, state.end)}  ·  ${durationText(state.start, state.end)}  ·  ${formatSum(Math.round((state.slots.hourly_price || 0) * (state.end - state.start) / 60))} so'm`;
    const bot = botUsername();
    if (bot) {
      showOk(
        "Oxirgi qadam",
        "«Botga o'tish» ni bosing — to'lov ko'rsatmasi ochiladi. Bekor qilish kerak bo'lsa botdagi «Mening bronlarim» dan admin bilan bog'laning.",
        "Botga o'tish"
      );
    } else {
      showOk(
        "Oxirgi qadam",
        `Botda shu buyruqni yuboring: /start ${payload}`,
        "Yopish"
      );
    }
  }

  async function book() {
    if (state.start == null || state.end == null) return;
    if (dateFullyPast(state.date)) {
      toast("Faqat oldindagi kun va vaqtni bron qilish mumkin");
      return;
    }
    if (dateIsRest(state.date)) {
      toast("Bu kun dam olish — bron qilib bo'lmaydi");
      return;
    }
    const nowMin = effectiveNowMin(state.date);
    if (nowMin >= 0 && state.start < ceil30(nowMin)) {
      toast("Faqat oldindagi vaqtni bron qilish mumkin");
      return;
    }
    if (overlaps(state.start, state.end, (state.slots && state.slots.occupied) || [])) {
      toast("Bu vaqt band yoki kutilmoqda. Boshqa vaqt tanlang.");
      return;
    }
    const btn = $("bookBtn");
    btn.disabled = true;
    state.pendingStart = null;
    try {
      if (apiBase() !== null) {
        const res = await api("/api/book", {
          method: "POST",
          body: JSON.stringify({
            date: state.date,
            start_min: state.start,
            end_min: state.end,
          }),
        });
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
        $("okText").textContent =
          `${res.range}  ·  ${res.duration}  ·  ${res.price_text} so'm`;
        showOk(
          "Bron yaratildi",
          "Kartaga pul o'tkazib, skrinshot yuboring. Bekor qilish kerak bo'lsa botdagi «Mening bronlarim» dan admin bilan bog'laning.",
          "Davom etish"
        );
        applyLocalBooking();
        await loadSlots();
        return;
      }
      bookViaTelegram();
    } catch (err) {
      const raw = String(err && err.message ? err.message : err);
      const msg = raw.indexOf("band") >= 0 || raw.indexOf("kutil") >= 0 || raw.indexOf("bron bor") >= 0
        ? raw
        : (raw || "Bron qilinmadi. Boshqa vaqt tanlang.");
      toast(msg);
      try { loadSlots(); } catch (e) {}
    } finally {
      updateSummary();
    }
  }

  $("startSel").addEventListener("change", () => {
    state.start = Number($("startSel").value);
    fillEndSelect();
    updateSummary();
    renderHours();
  });
  $("endSel").addEventListener("change", () => {
    state.end = Number($("endSel").value);
    updateSummary();
    renderHours();
  });
  $("bookBtn").addEventListener("click", book);
  $("closeBtn").addEventListener("click", () => {
    $("okModal").hidden = true;
    const payload = state.pendingStart;
    const bot = botUsername();
    if (payload && bot) {
      const link = `https://t.me/${bot}?start=${payload}`;
      state.pendingStart = null;
      if (tg && typeof tg.openTelegramLink === "function") tg.openTelegramLink(link);
      else window.open(link, "_blank");
      return;
    }
    if (payload && !bot) {
      toast(`/start ${payload}`);
    }
    state.pendingStart = null;
  });
  $("calPrev").addEventListener("click", () => {
    const todayDt = parseYmd(state.config.today);
    const minMonth = todayDt.getFullYear() * 12 + todayDt.getMonth();
    const next = state.viewYear * 12 + state.viewMonth - 1;
    if (next < minMonth) return;
    state.viewMonth -= 1;
    if (state.viewMonth < 0) {
      state.viewMonth = 11;
      state.viewYear -= 1;
    }
    renderDates();
  });
  $("calNext").addEventListener("click", () => {
    state.viewMonth += 1;
    if (state.viewMonth > 11) {
      state.viewMonth = 0;
      state.viewYear += 1;
    }
    renderDates();
  });

  async function init() {
    try {
      if (apiBase() === null) {
        const snap = await loadSnapshot();
        state.snapshot = snap;
        state.config = snapshotToConfig(snap);
      } else {
        state.config = await api("/api/config");
      }
      $("stadiumName").textContent = state.config.stadium_name || "Mini Stadion";
      $("stadiumAddr").textContent = state.config.address || "";
      $("priceChip").textContent = `1 soat — ${state.config.hourly_price_text} so'm`;
      state.date = state.config.today;
      renderDates();
      await loadSlots();
      setInterval(() => {
        if (document.visibilityState === "visible") loadSlots();
      }, 8000);
    } catch (err) {
      $("stadiumAddr").textContent = err.message;
    }
  }

  init();
})();
