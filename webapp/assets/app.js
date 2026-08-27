(() => {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor("#07140e");
    tg.setBackgroundColor("#07140e");
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

  function isGithubPages() {
    return location.hostname.endsWith("github.io");
  }

  function apiBase() {
    const manual = String(CFG.apiBase || "").trim().replace(/\/$/, "");
    if (manual) return manual;
    if (isGithubPages()) return null;
    return "";
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

  function hourColor(hour, bookings, closeMin) {
    const start = hour * 60;
    let end = hour * 60 + 60;
    if (closeMin != null) end = Math.min(end, closeMin);
    const available = Math.max(0, end - start);
    if (available <= 0) return "green";
    const confirmed = bookings.filter((b) => b.status === "confirmed").map((b) => [b.start_min, b.end_min]);
    const pending = bookings
      .filter((b) => b.status === "pending_payment" || b.status === "pending_review")
      .map((b) => [b.start_min, b.end_min]);
    const bookedMins = occupiedMinutes(confirmed, start, end);
    const pendingMins = occupiedMinutes(pending, start, end);
    if (bookedMins >= available) return "red";
    if (pendingMins > 0) return "orange";
    if (bookedMins > 0) return "blue";
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

  async function loadSnapshot() {
    const repo = githubRepo();
    const branch = CFG.githubBranch || "main";
    const urls = [];
    if (repo) {
      urls.push(`https://raw.githubusercontent.com/${repo}/${branch}/webapp/data/public.json?t=${Date.now()}`);
    }
    urls.push(`./data/public.json?t=${Date.now()}`);
    let lastErr = "Bron ma'lumoti yuklanmadi";
    for (const url of urls) {
      try {
        const res = await fetch(url, { cache: "no-store" });
        if (res.ok) return await res.json();
        lastErr = `HTTP ${res.status}`;
      } catch (err) {
        lastErr = err.message || lastErr;
      }
    }
    throw new Error(lastErr);
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

  function dateFullyPast(date) {
    return effectiveNowMin(date) >= 24 * 60;
  }

  function slotsFromSnapshot(date) {
    const snap = state.snapshot || {};
    const openMin = Number(snap.open_min || 0);
    const closeMin = Number(snap.close_min || 1440);
    const occupied = ((snap.days || {})[date] || {}).occupied || [];
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
      btn.className = "cal-day" + (key === state.date ? " active" : "") + (past ? " past" : "") + (key === today ? " today" : "");
      btn.textContent = String(day);
      btn.addEventListener("click", () => {
        state.date = key;
        state.start = null;
        state.end = null;
        renderDates();
        loadSlots();
      });
      grid.appendChild(btn);
    }
  }

  function colorLabel(color) {
    return STATUS[color] || color;
  }

  function renderHours() {
    const box = $("hours");
    box.innerHTML = "";
    const nowMin = effectiveNowMin(state.date);
    const start = state.start;
    const end = state.end;
    const fullyPast = dateFullyPast(state.date);
    for (const h of state.slots.hours) {
      const past = fullyPast || isHourPast(h, nowMin);
      const inRange = !past && start != null && end != null && h.start_min < end && start < h.end_min;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `hour ${past ? "past" : h.color}${inRange ? " in-range" : ""}`;
      btn.innerHTML = `<div class="t">${h.label}</div><div class="s">${past ? "O'tib ketgan" : colorLabel(h.color)}</div>`;
      btn.addEventListener("click", () => onHourClick(h, past));
      box.appendChild(btn);
    }
    const d = parseYmd(state.date);
    $("dayTitle").textContent = `${DAYS_FULL[d.getDay()]}, ${d.getDate()}-${MONTHS[d.getMonth()]}`;
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
    if (past || h.color === "red" || h.color === "orange") return;
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
    $("hours").innerHTML = "<p class='muted'>Yuklanmoqda…</p>";
    try {
      if (apiBase() === null) {
        state.slots = slotsFromSnapshot(state.date);
      } else {
        state.slots = await api(`/api/slots?date=${state.date}`);
        state.slots.now_min = effectiveNowMin(state.date);
      }
      fillStartSelect();
      fillEndSelect();
      updateSummary();
      renderHours();
    } catch (err) {
      $("hours").innerHTML = `<p class="muted">${err.message}</p>`;
    }
  }

  function bookViaTelegram() {
    if (!tg || typeof tg.sendData !== "function") {
      throw new Error("Pastdagi «🏟️ Bron qilish» tugmasidan oching — shunda bron botga ketadi.");
    }
    tg.sendData(JSON.stringify({
      date: state.date,
      start_min: state.start,
      end_min: state.end,
    }));
    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
    $("okText").textContent =
      `${displayRange(state.start, state.end)}  ·  ${durationText(state.start, state.end)}  ·  ${formatSum(Math.round((state.slots.hourly_price || 0) * (state.end - state.start) / 60))} so'm`;
    $("okModal").hidden = false;
    setTimeout(() => { try { tg.close(); } catch (e) {} }, 1200);
  }

  async function book() {
    if (state.start == null || state.end == null) return;
    if (dateFullyPast(state.date)) {
      toast("Faqat oldindagi kun va vaqtni bron qilish mumkin");
      return;
    }
    const nowMin = effectiveNowMin(state.date);
    if (nowMin >= 0 && state.start < ceil30(nowMin)) {
      toast("Faqat oldindagi vaqtni bron qilish mumkin");
      return;
    }
    const btn = $("bookBtn");
    btn.disabled = true;
    try {
      if (apiBase() === null) {
        bookViaTelegram();
        return;
      }
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
      $("okModal").hidden = false;
    } catch (err) {
      toast(err.message);
      btn.disabled = false;
      loadSlots();
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
    if (tg) tg.close();
    else $("okModal").hidden = true;
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
    } catch (err) {
      $("stadiumAddr").textContent = err.message;
    }
  }

  init();
})();
