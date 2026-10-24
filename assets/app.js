// 新北垃圾車倒數 — 前端（無外部套件）
// 清運點資料格式：[name, village, time, lon, lat, garbage7, recycling7, food7, linename]
(() => {
const WD = ["日","一","二","三","四","五","六"];
const ICS_DAY = ["SU","MO","TU","WE","TH","FR","SA"];
const KINDS = [["垃圾", 5, "g", "🗑️"], ["回收", 6, "r", "♻️"], ["廚餘", 7, "f", "🥬"]];
const LS_LAST = "ntpc-trash", LS_FAVS = "ntpc-trash-favs", LS_THEME = "theme";

const $ = id => document.getElementById(id);
const esc = v => String(v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const tpeNow = () => new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Taipei" }));
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  raw(k) { try { return localStorage.getItem(k); } catch { return null; } },
  setRaw(k, v) { try { localStorage.setItem(k, v); } catch {} }
};
const stopKey = s => s[0] + "|" + s[2] + "|" + s[8];
const page = document.body.dataset;            // data-city / data-village：分區頁預設
const cache = new Map();
let city = "", cityData = null, selStop = null, selCity = "", timer = null, listShown = [];

function toast(msg) {
  let t = $("toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
  t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2200);
}

// ===== 深淺色 =====
const ICON_SUN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const ICON_MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
const sysDark = () => matchMedia("(prefers-color-scheme: dark)").matches;
function applyTheme(t) {
  if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
  const dark = t ? t === "dark" : sysDark();
  const b = $("themeBtn");
  if (b) { b.innerHTML = dark ? ICON_SUN : ICON_MOON; b.setAttribute("aria-label", dark ? "切換為淺色" : "切換為深色"); }
}
const savedTheme = () => { const t = store.raw(LS_THEME); return t === "dark" || t === "light" ? t : null; };
applyTheme(savedTheme());
$("themeBtn")?.addEventListener("click", () => {
  const cur = document.documentElement.dataset.theme || (sysDark() ? "dark" : "light");
  const next = cur === "dark" ? "light" : "dark";
  store.setRaw(LS_THEME, next); applyTheme(next);
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (!savedTheme()) applyTheme(null); });

// ===== 分享網站 =====
document.querySelectorAll("[data-share]").forEach(b => b.addEventListener("click", async () => {
  const url = location.origin + location.pathname;
  const raw = `🚛 ${document.title.split("｜")[0]}：查你家垃圾車幾點到，即時倒數＋手機日曆提醒`;
  const u = encodeURIComponent(url), t = encodeURIComponent(raw);
  const links = {
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${u}`,
    line: `https://social-plugins.line.me/lineit/share?url=${u}&text=${t}`,
    threads: `https://www.threads.net/intent/post?text=${t}%0A${u}`,
    x: `https://twitter.com/intent/tweet?text=${t}&url=${u}`
  };
  if (b.dataset.share === "copy") { await copy(url); return; }
  window.open(links[b.dataset.share], "_blank", "noopener,width=600,height=560");
}));
async function copy(text) {
  try { await navigator.clipboard.writeText(text); toast("✅ 連結已複製"); }
  catch { prompt("複製這個連結：", text); }
}

if (!$("city")) return;   // 沒有查詢工具的頁面（如隱私權政策）到此為止

// ===== 資料 =====
async function getJSON(path) {
  if (cache.has(path)) return cache.get(path);
  const p = fetch(path).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
  cache.set(path, p);
  p.catch(() => cache.delete(path));
  return p;
}
const getCity = name => getJSON(`/data/${encodeURIComponent(name)}.json`);

function parseHash() {
  try {
    const h = decodeURIComponent(location.hash.slice(1));
    if (!h || !h.includes("~")) return null;
    const [c, village, key] = h.split("~");
    return c ? { city: c, village, stopKey: key } : null;
  } catch { return null; }
}

async function init() {
  const idx = await getJSON("/data/index.json");
  $("city").innerHTML = '<option value="">選擇行政區</option>' +
    idx.cities.map(c => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join("");
  renderFavs();
  const has = c => idx.cities.some(x => x.name === c);
  const pageCtx = page.city ? { city: page.city, village: page.village || "" } : null;
  const start = parseHash() || pageCtx || store.get(LS_LAST, {});
  if (start.city && has(start.city)) await loadCity(start.city, start);
  else emptyState();
  $("city").addEventListener("change", () => { $("village").value = ""; $("q").value = ""; loadCity($("city").value, {}); });
  $("village").addEventListener("change", renderStops);
  $("q").addEventListener("input", renderStops);
  $("geoBtn").addEventListener("click", geoLocate);
  $("stops").addEventListener("click", e => {
    const el = e.target.closest(".stop-item");
    if (!el) return;
    const [s, c] = listShown[+el.dataset.i];
    pick(s, c);
  });
  window.addEventListener("hashchange", async () => {
    const h = parseHash();
    if (!h || !has(h.city)) return;
    if (selStop && h.city === selCity && h.stopKey === stopKey(selStop)) return;
    await loadCity(h.city, h);
    $(matchMedia("(max-width: 860px)").matches ? "detail" : "tool")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

async function loadCity(name, opts = {}, render = true) {
  if (!name) { cityData = null; city = ""; $("village").disabled = $("q").disabled = true; $("stops").innerHTML = ""; return; }
  $("city").value = name;
  if (render) $("stops").innerHTML = '<div class="hint">載入中⋯</div>';
  const data = await getCity(name);
  city = name; cityData = data;
  const villages = [...new Set(data.stops.map(s => s[1]))];
  const vSel = $("village");
  vSel.disabled = false; $("q").disabled = false;
  vSel.innerHTML = '<option value="">全部里</option>' + villages.map(v => `<option>${esc(v)}</option>`).join("");
  if (opts.village && villages.includes(opts.village)) vSel.value = opts.village;
  if (render) renderStops();
  if (opts.stopKey) {
    const s = data.stops.find(s => stopKey(s) === opts.stopKey);
    if (s) { selectStop(s, name, false); markSel(); }
  }
}

function stopRow(s, c, i, extra = "") {
  return `<button type="button" class="stop-item" data-i="${i}">
    <span><span class="n">${esc(s[0])}</span><span class="v">${esc(c === city ? "" : c)}${esc(s[1])}・${esc(s[8])}</span></span>
    <span class="t">${esc(s[2])}${extra}</span></button>`;
}

function renderStops() {
  if (!cityData) return;
  const v = $("village").value, q = $("q").value.trim();
  let list = cityData.stops;
  if (v) list = list.filter(s => s[1] === v);
  if (q) list = list.filter(s => s[0].includes(q) || s[8].includes(q));
  listShown = list.slice(0, 200).map(s => [s, city]);
  $("stops").innerHTML = listShown.map(([s, c], i) => stopRow(s, c, i)).join("") +
    (list.length > 200 ? `<div class="hint">還有 ${(list.length - 200).toLocaleString()} 筆，選里別或輸入路名縮小範圍</div>` : "") +
    (list.length === 0 ? `<div class="hint">找不到清運點，換個關鍵字試試（例如只打路名「中山」）</div>` : "");
  markSel();
}
function markSel() {
  const k = selStop && stopKey(selStop);
  document.querySelectorAll(".stop-item").forEach(el => {
    const [s, c] = listShown[+el.dataset.i] || [];
    el.classList.toggle("sel", !!s && c === selCity && stopKey(s) === k);
  });
}

// ===== 定位：跨區找最近 20 個清運點 =====
function geoLocate() {
  if (!navigator.geolocation) { toast("你的瀏覽器不支援定位"); return; }
  const btn = $("geoBtn"), label = btn.innerHTML;
  btn.disabled = true; btn.textContent = "定位中⋯";
  navigator.geolocation.getCurrentPosition(async pos => {
    try {
      const { latitude: la, longitude: lo } = pos.coords;
      const dist = (x, y) => Math.hypot((x - lo) * 101000 * Math.cos(la * Math.PI / 180), (y - la) * 110600);
      const geo = await getJSON("/data/geo.json");
      const near = geo.map(g => [dist(g.lon, g.lat), g.name]).sort((a, b) => a[0] - b[0]);
      if (near[0][0] > 40000) { toast("你好像不在新北市，請改用行政區選單"); return; }
      const names = near.slice(0, 3).map(n => n[1]);
      const datas = await Promise.all(names.map(getCity));
      const all = datas.flatMap((d, i) => d.stops.map(s => [dist(s[3], s[4]), s, names[i]]));
      all.sort((a, b) => a[0] - b[0]);
      const top = all.slice(0, 20);
      await loadCity(top[0][2], {}, false);
      $("village").value = ""; $("q").value = "";
      listShown = top.map(([, s, c]) => [s, c]);
      const fmt = d => d < 1000 ? Math.round(d) + " m" : (d / 1000).toFixed(1) + " km";
      $("stops").innerHTML = `<div class="hint" style="padding:6px 0 10px">📍 離你最近的 20 個清運點</div>` +
        top.map(([d, s, c], i) => stopRow(s, c, i, `<span class="d">${fmt(d)}</span>`)).join("");
      markSel();
    } catch (e) { toast("讀取資料失敗，請稍後再試"); }
    finally { btn.disabled = false; btn.innerHTML = label; }
  }, err => {
    btn.disabled = false; btn.innerHTML = label;
    toast(err.code === 1 ? "請允許定位權限，或改用行政區選單" : "定位失敗，請改用行政區選單");
  }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
}

// ===== 常用清運點 =====
const getFavs = () => store.get(LS_FAVS, []);
const isFav = (s, c) => getFavs().some(f => f.stopKey === stopKey(s) && f.city === c);
function renderFavs() {
  const favs = getFavs(), box = $("favs");
  if (!box) return;
  box.hidden = !favs.length;
  $("favList").innerHTML = favs.map((f, i) =>
    `<span class="chip" data-i="${i}" role="button" tabindex="0" title="${esc(f.city + f.village)}">
      <span>⭐ ${esc(f.name)}</span><button type="button" class="x" data-x="${i}" aria-label="移除 ${esc(f.name)}">×</button></span>`).join("");
}
$("favList")?.addEventListener("click", async e => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  const favs = getFavs();
  if (e.target.dataset.x !== undefined) {
    favs.splice(+e.target.dataset.x, 1); store.set(LS_FAVS, favs); renderFavs();
    if (selStop) renderDetail(); return;
  }
  const f = favs[+chip.dataset.i];
  await loadCity(f.city, f);
});
$("favList")?.addEventListener("keydown", e => { if (e.key === "Enter" && e.target.classList.contains("chip")) e.target.click(); });
function toggleFav() {
  const favs = getFavs(), key = stopKey(selStop);
  const i = favs.findIndex(f => f.stopKey === key && f.city === selCity);
  if (i >= 0) { favs.splice(i, 1); toast("已從常用移除"); }
  else { favs.push({ city: selCity, village: selStop[1], name: selStop[0], stopKey: key }); toast("⭐ 已加入常用，下次打開一鍵切換"); }
  store.set(LS_FAVS, favs); renderFavs(); renderDetail();
}

// ===== 倒數 =====
function nextOccur(s, fi) {
  const flags = s[fi];
  const [hh, mm] = s[2].split(":").map(Number);
  const now = tpeNow();
  for (let d = 0; d < 14; d++) {
    const c = new Date(now); c.setDate(now.getDate() + d); c.setHours(hh, mm, 0, 0);
    if (flags[c.getDay()] === "1" && c > now) return c;
  }
  return null;
}
// 表定時間前後 10 分鐘內：垃圾車可能就在附近
function arrivingNow(s) {
  const [hh, mm] = s[2].split(":").map(Number);
  const now = tpeNow(), t = new Date(now); t.setHours(hh, mm, 0, 0);
  const diff = (now - t) / 60000;
  return diff >= -10 && diff <= 10 && KINDS.some(([, fi]) => s[fi][now.getDay()] === "1");
}
const p2 = n => String(n).padStart(2, "0");
const fmtDate = (t, s) => !t ? "近期無收運" : `${t.getMonth() + 1}/${t.getDate()}（${WD[t.getDay()]}）${s[2]}`;
function bigCountdown(t) {
  if (!t) return "—";
  const diff = t - tpeNow();
  const d = Math.floor(diff / 86400000), h = Math.floor(diff % 86400000 / 3600000), m = Math.floor(diff % 3600000 / 60000), sec = Math.floor(diff % 60000 / 1000);
  if (diff < 3600000) return `${m}<small>分</small>${p2(sec)}<small>秒</small>`;
  if (diff < 86400000) return `${h}<small>小時</small>${p2(m)}<small>分</small>${p2(sec)}<small>秒</small>`;
  return `${d}<small>天</small>${h}<small>小時</small>${p2(m)}<small>分</small>`;
}
function shortCountdown(t) {
  if (!t) return "";
  const diff = t - tpeNow(), h = Math.floor(diff / 3600000), m = Math.floor(diff % 3600000 / 60000);
  if (diff < 3600000) return `${m} 分後`;
  if (diff < 86400000) return `${h} 小時 ${m} 分後`;
  const d = Math.round(diff / 86400000);
  return d === 1 ? "明天" : `${d} 天後`;
}
function relDay(t) {
  if (!t) return "";
  const now = tpeNow(), a = new Date(now.getFullYear(), now.getMonth(), now.getDate()), b = new Date(t.getFullYear(), t.getMonth(), t.getDate());
  const d = Math.round((b - a) / 86400000);
  return d === 0 ? "今天" : d === 1 ? "明天" : d === 2 ? "後天" : `週${WD[t.getDay()]}`;
}

function emptyState() {
  $("detail").innerHTML = `<div class="card result-empty">
    <img class="truck" src="/assets/icon.svg" alt="" width="84" height="84">
    <h2>選一個清運點，馬上開始倒數</h2>
    <p>從左邊選行政區與里別，或按「找我附近的清運點」用 GPS 自動找。</p>
  </div>`;
}

function selectStop(s, c, scroll = true) {
  selStop = s; selCity = c;
  store.set(LS_LAST, { city: c, village: s[1], stopKey: stopKey(s) });
  history.replaceState(null, "", "#" + encodeURIComponent(`${c}~${s[1]}~${stopKey(s)}`));
  if (timer) clearInterval(timer);
  renderDetail();
  timer = setInterval(renderDetail, 1000);
  if (scroll && matchMedia("(max-width: 860px)").matches) $("detail").scrollIntoView({ behavior: "smooth", block: "start" });
}
function pick(s, c) {
  const go = () => { selectStop(s, c); markSel(); };
  if (c !== city) loadCity(c, {}, false).then(go); else go();
}

function renderDetail() {
  const s = selStop, c = selCity;
  if (!s) return;
  const next = KINDS.map(([lb, fi, cl, em]) => ({ lb, fi, cl, em, t: nextOccur(s, fi) }));
  const g = next[0].t || next.map(n => n.t).filter(Boolean).sort((a, b) => a - b)[0];
  const now = tpeNow(), live = arrivingNow(s);
  const fav = isFav(s, c);
  $("detail").innerHTML = `<article class="card result" aria-live="off">
    <div class="result-head">
      <div><h2>${esc(s[0])}</h2><div class="meta">${esc(c + s[1])}・${esc(s[8])}</div></div>
      ${live ? '<span class="badge live">垃圾車就在附近</span>' : `<span class="badge">表定 ${esc(s[2])}</span>`}
    </div>
    <div class="countdown">
      <div class="lbl">下一班${next[0].t ? "垃圾車" : "收運"}還有</div>
      <div class="big">${bigCountdown(g)}</div>
      <div class="when">${g ? `${relDay(g)} ${fmtDate(g, s)}` : "此清運點目前無收運資訊"}</div>
    </div>
    <div class="kinds">${next.map(n => `<div class="kind ${n.cl}"><div class="k">${n.em} ${n.lb}</div><div class="w">${n.t ? `${n.t.getMonth() + 1}/${n.t.getDate()} 週${WD[n.t.getDay()]}` : "—"}</div><div class="c">${shortCountdown(n.t)}</div></div>`).join("")}</div>
    <div class="week" role="table" aria-label="每週收運時刻表">
      <div class="h" role="columnheader"></div>${WD.map((w, i) => `<div class="h ${i === now.getDay() ? "today" : ""}" role="columnheader">${w}</div>`).join("")}
      ${KINDS.map(([lb, fi, cl, em]) => `<div class="lb" role="rowheader">${em} ${lb}</div>` +
        WD.map((w, i) => s[fi][i] === "1" ? `<div class="on ${cl}" aria-label="週${w}有收">✓</div>` : `<div class="off" aria-label="週${w}不收">·</div>`).join("")).join("")}
    </div>
    <div class="actions">
      <button type="button" class="btn btn-primary" data-act="ics"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18M12 14v4M10 16h4"/></svg>加入手機日曆提醒</button>
      <button type="button" class="btn btn-ghost" data-act="fav">${fav ? "★ 已收藏" : "☆ 收藏"}</button>
      <button type="button" class="btn btn-ghost" data-act="map">地圖</button>
      <button type="button" class="btn btn-ghost" data-act="share">分享</button>
    </div>
    <p class="fine">日曆提醒為每週重複、提前 10 分鐘通知，支援 iPhone、Android、Google 日曆。表定時間僅供參考，實際以現場為準。</p>
  </article>`;
}
$("detail").addEventListener("click", e => {
  const a = e.target.closest("[data-act]")?.dataset.act;
  if (a === "ics") downloadICS();
  else if (a === "fav") toggleFav();
  else if (a === "map") window.open(`https://www.google.com/maps/search/?api=1&query=${selStop[4]},${selStop[3]}`, "_blank", "noopener");
  else if (a === "share") shareStop();
});

async function shareStop() {
  const url = location.href;
  const title = `🚛 ${selStop[0]} 垃圾車時間表`;
  if (navigator.share) { try { await navigator.share({ title, text: title, url }); } catch {} }
  else copy(url);
}

// ===== .ics（每週重複 + 提前 10 分鐘提醒）=====
const icsDate = t => `${t.getFullYear()}${p2(t.getMonth() + 1)}${p2(t.getDate())}T${p2(t.getHours())}${p2(t.getMinutes())}00`;
const icsText = v => String(v).replace(/[\\;,]/g, m => "\\" + m);
function makeEvent(s, c, fi, label, emoji) {
  const start = nextOccur(s, fi);
  if (!start) return "";
  const days = [...s[fi]].map((f, i) => f === "1" ? ICS_DAY[i] : null).filter(Boolean).join(",");
  const end = new Date(start.getTime() + 10 * 60000);
  const u = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
  return [
    "BEGIN:VEVENT",
    `UID:${encodeURIComponent(c + stopKey(s)).replace(/%/g, "").slice(0, 60)}-${fi}@ntpc-trash-countdown.sectools.tw`,
    `DTSTAMP:${u}`,
    `DTSTART;TZID=Asia/Taipei:${icsDate(start)}`,
    `DTEND;TZID=Asia/Taipei:${icsDate(end)}`,
    `RRULE:FREQ=WEEKLY;BYDAY=${days}`,
    `SUMMARY:${emoji} ${label}車來了－${icsText(s[0])}`,
    `LOCATION:${icsText(c + s[1] + " " + s[0])}`,
    `DESCRIPTION:表定時間 ${s[2]}（${icsText(s[8])}）\\n由新北垃圾車倒數產生：https://ntpc-trash-countdown.sectools.tw/`,
    "BEGIN:VALARM", "TRIGGER:-PT10M", "ACTION:DISPLAY",
    `DESCRIPTION:${emoji} ${label}車 10 分鐘後到 ${icsText(s[0])}`,
    "END:VALARM", "END:VEVENT"
  ].join("\r\n");
}
function downloadICS() {
  const s = selStop, c = selCity;
  const events = [makeEvent(s, c, 5, "垃圾", "🗑️"), makeEvent(s, c, 6, "資源回收", "♻️"), makeEvent(s, c, 7, "廚餘", "🥬")].filter(Boolean);
  if (!events.length) { toast("這個清運點目前沒有收運資訊"); return; }
  const ics = [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//sectools.tw//ntpc-trash-countdown//TW", "CALSCALE:GREGORIAN",
    "BEGIN:VTIMEZONE", "TZID:Asia/Taipei", "BEGIN:STANDARD", "DTSTART:19700101T000000",
    "TZOFFSETFROM:+0800", "TZOFFSETTO:+0800", "TZNAME:CST", "END:STANDARD", "END:VTIMEZONE",
    ...events, "END:VCALENDAR"
  ].join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" }));
  a.download = `垃圾車提醒-${s[0]}.ics`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  toast("📅 已下載，打開檔案即可加入日曆");
}

init().catch(e => {
  $("stops").innerHTML = `<div class="hint">資料載入失敗（${esc(e.message)}），請重新整理再試一次</div>`;
});
})();
