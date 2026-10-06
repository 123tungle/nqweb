/* Nguyên Quân Web – giao diện một trang (không cần thư viện ngoài, trừ bản đồ Leaflet tải khi cần) */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const view = $("#view");
const S = { me: null, menu: {}, lastList: {}, lastReport: {}, seq: 0 };

/* ------------------------------------------------------------ API */
async function api(path, opts = {}) {
  const o = { headers: {}, ...opts };
  if (o.body && typeof o.body !== "string") { o.body = JSON.stringify(o.body); o.headers["Content-Type"] = "application/json"; }
  const r = await fetch(path, o);
  if (r.status === 401 && !path.endsWith("/login")) { showLogin(); throw new Error("Phiên đăng nhập đã hết, đăng nhập lại."); }
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = j.detail || msg; } catch (_) { /* không phải JSON */ }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : r;
}
async function download(path, body) {
  const r = await api(path, { method: "POST", body });
  const blob = await r.blob();
  const cd = r.headers.get("content-disposition") || "";
  const m = /filename\*=UTF-8''([^;]+)/.exec(cd);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = m ? decodeURIComponent(m[1]) : "du_lieu.xlsx";
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}
function toast(msg, err = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast" + (err ? " err" : ""); t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), err ? 6000 : 2800);
}
const busy = (msg = "Đang tải dữ liệu…") => `<div class="busy"><span class="spin"></span>${esc(msg)}</div>`;

/* ------------------------------------------------------------ định dạng */
const nf0 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nfx = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 });
function dmy(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(s || "");
  if (!m) return s ?? "";
  return `${m[3]}/${m[2]}/${m[1]}`;
}
function cleanText(s) {
  return String(s).replace(/<\s*\/?\s*br\s*\/?\s*>/gi, "\n").replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim();
}
const isMapLink = (s) => typeof s === "string" && /Mapdata\.aspx/i.test(s);
const isNum = (v) => typeof v === "number" && isFinite(v);
function fmt(v, f) {
  if (v === null || v === undefined || v === "") return "";
  if (typeof v === "boolean") return v ? "✓" : "";
  if (f === "D" || (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T00:00:00$/.test(v))) return dmy(v);
  if (isNum(v)) {
    if (f === "N2") return nf2.format(v);
    if (f === "N") return nf0.format(v);
    return Number.isInteger(v) ? nf0.format(v) : nfx.format(v);
  }
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(v)) return dmy(v) + " " + v.slice(11, 16);
  return cleanText(v).replace(/,\s*$/, "");
}
const alignClass = (c, sample) => (c.fmt === "N" || c.fmt === "N2" || isNum(sample)) ? "n" : c.fmt === "D" ? "d" : c.fmt === "B" || typeof sample === "boolean" ? "c" : "";
function argbColor(v) {
  if (!isNum(v)) return null;
  const rgb = (v >>> 0) & 0xffffff;
  return "#" + rgb.toString(16).padStart(6, "0");
}
const todayIso = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);

/* ------------------------------------------------------------ đăng nhập + khung */
function showLogin() {
  $("#shell").hidden = true; $("#login").hidden = false;
  setTimeout(() => $("#lu").focus(), 50);
}
$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#loginErr").textContent = "";
  try {
    await api("/api/login", { method: "POST", body: { username: $("#lu").value, password: $("#lp").value } });
    $("#lp").value = "";
    await boot();
  } catch (err) { $("#loginErr").textContent = err.message; }
});

async function boot() {
  let me;
  try { me = await api("/api/me"); } catch (_) { showLogin(); return; }
  S.me = me; S.menu = {};
  $("#login").hidden = true; $("#shell").hidden = false;
  $("#company").textContent = me.company; $("#companySub").textContent = me.company_sub;
  $("#loginCompany").textContent = me.company;
  $("#userName").textContent = me.name || me.user;
  $("#avatar").textContent = (me.name || me.user || "?").trim().split(/\s+/).pop()[0].toUpperCase();
  $$(".admin-only").forEach((b) => (b.hidden = !me.admin));
  $$(".local-only").forEach((b) => (b.hidden = me.nguon !== "local"));   // đổi mật khẩu chỉ cho tài khoản web
  buildNav();
  route();
}

function buildNav() {
  const me = S.me;
  let html = `<a href="#/" class="home">Trang chủ</a>`;
  for (const g of me.menu) {
    html += `<details open><summary>${esc(g.title)}</summary>`;
    for (const it of g.items) {
      S.menu[it.id] = it;
      html += `<a href="#/${it.kind}/${esc(it.id)}">${esc(it.title)}${it.off ? '<span class="off">tắt</span>' : ""}</a>`;
    }
    html += `</details>`;
  }
  if (me.admin) {
    html += `<details open><summary>Hệ thống web</summary><a href="#/users">Người dùng web</a><a href="#/log">Nhật ký web</a></details>`;
  }
  $("#nav").innerHTML = html;
}
function markNav() {
  const h = location.hash || "#/";
  $$("#nav a").forEach((a) => {
    const href = a.getAttribute("href");
    const on = href === "#/" ? h === "#/" || h === "" : h === href || h.startsWith(href + "/");
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
}
function setTitle(t) { $("#pageTitle").textContent = t; document.title = t + " – " + (S.me?.company || ""); }
function closeSide() { $("#side").classList.remove("open"); $("#scrim").hidden = true; $("#menuBtn").setAttribute("aria-expanded", "false"); }
$("#menuBtn").onclick = () => { $("#side").classList.add("open"); $("#scrim").hidden = false; $("#menuBtn").setAttribute("aria-expanded", "true"); };
$("#scrim").onclick = closeSide;
$("#nav").addEventListener("click", (e) => { if (e.target.closest("a")) closeSide(); });
$("#userBtn").onclick = (e) => { e.stopPropagation(); const m = $("#userMenu"); m.hidden = !m.hidden; $("#userBtn").setAttribute("aria-expanded", String(!m.hidden)); };
document.addEventListener("click", () => { $("#userMenu").hidden = true; });
$("#userMenu").addEventListener("click", async (e) => {
  const act = e.target.dataset.act;
  if (act === "logout") { await api("/api/logout", { method: "POST" }).catch(() => {}); showLogin(); }
  if (act === "password") passwordDialog();
  if (act === "refresh") { await api("/api/lam-moi", { method: "POST" }); await boot(); toast("Đã đọc lại cấu hình menu, màn hình từ database"); }
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSide(); });

/* ------------------------------------------------------------ bộ định tuyến */
window.addEventListener("hashchange", route);
async function route() {
  if (!S.me) return;
  markNav();
  const seq = ++S.seq;
  const parts = (location.hash.replace(/^#\/?/, "") || "").split("/");
  const [kind, id] = parts;
  const rest = parts.slice(2).join("/");
  try {
    if (!kind) await pageHome(seq);
    else if (kind === "order" && rest) await pageOrder(seq, id, rest === "new" ? "" : decodeURIComponent(rest));
    else if (kind === "list" && rest) await pageRecord(seq, id, decodeURIComponent(rest));
    else if (kind === "list") await pageList(seq, id);
    else if (kind === "report") await pageReport(seq, id);
    else if (kind === "users" && S.me.admin) await pageUsers(seq);
    else if (kind === "log" && S.me.admin) await pageLog(seq);
    else { setTitle("Không tìm thấy"); view.innerHTML = `<div class="card pad">Không có trang này.</div>`; }
  } catch (err) {
    if (seq !== S.seq) return;
    view.innerHTML = `<div class="errbox">${esc(err.message)}</div>`;
  }
  view.focus({ preventScroll: true });
}
const stale = (seq) => seq !== S.seq;

/* ------------------------------------------------------------ ô chọn có tìm kiếm */
let comboId = 0;
function combo({ label, value = "", locked = false, load, placeholder = "Tất cả" }) {
  const id = "cb" + ++comboId;
  const wrap = document.createElement("div");
  wrap.innerHTML = `<label for="${id}">${esc(label)}</label><input id="${id}" list="${id}l" placeholder="${esc(placeholder)}" ${locked ? "readonly" : ""} autocomplete="off"><datalist id="${id}l"></datalist>`;
  const input = $("input", wrap), dl = $("datalist", wrap);
  let opts = [], loaded = false;
  const fill = async () => {
    if (loaded || !load) return;
    loaded = true;
    try { opts = await load(); } catch (e) { opts = []; toast(e.message, true); }
    dl.innerHTML = opts.map((o) => `<option value="${esc(o.label)}"></option>`).join("");
    if (value) { const o = opts.find((x) => x.value === value); if (o) input.value = o.label; }
  };
  input.value = value;
  input.addEventListener("focus", fill);
  if (value) fill();
  return {
    el: wrap,
    get value() {
      const t = input.value.trim();
      if (!t) return "";
      const o = opts.find((x) => x.label === t || x.value === t);
      if (o) return o.value;
      const m = / - ([^-]+)$/.exec(t);
      return m ? m[1].trim() : t;
    },
    get text() { return input.value.trim(); },
    set value(v) { value = v; input.value = v; if (v) fill(); },
  };
}

/* ------------------------------------------------------------ bảng dữ liệu */
class Grid {
  constructor(host, { cols, rows, groups = null, keys = null, keyNames = null, onRow = null, cards = false, pageSize = 50, note = "" }) {
    Object.assign(this, { host, cols, rows, groups, keys, keyNames, onRow, cards, pageSize, note });
    this.sort = null; this.q = ""; this.page = 0;
    this.idx = rows.map((_, i) => i);
    this.sample = cols.map((_, j) => { const r = rows.find((x) => x[j] !== null && x[j] !== ""); return r ? r[j] : null; });
    host.innerHTML = `
      <div class="grid-head"><input class="search" type="search" placeholder="Lọc nhanh trong kết quả…" aria-label="Lọc nhanh trong kết quả"><span class="count"></span></div>
      <div class="table-wrap"><table class="grid"><thead></thead><tbody></tbody><tfoot></tfoot></table></div>
      <div class="cards"></div>
      <div class="pager"></div>`;
    $(".search", host).addEventListener("input", (e) => { this.q = e.target.value.trim().toLowerCase(); this.page = 0; this.apply(); });
    $("thead", host).addEventListener("click", (e) => {
      const th = e.target.closest("th"); if (!th) return;
      const j = +th.dataset.j;
      this.sort = this.sort && this.sort.j === j ? { j, dir: -this.sort.dir } : { j, dir: 1 };
      this.apply();
    });
    const clickRow = (e) => { const tr = e.target.closest("[data-i]"); if (tr && this.onRow) this.onRow(+tr.dataset.i, e); };
    $("tbody", host).addEventListener("click", clickRow);
    $(".cards", host).addEventListener("click", clickRow);
    $("tbody", host).addEventListener("keydown", (e) => { if (e.key === "Enter") clickRow(e); });
    this.apply();
  }
  text(i) {
    if (!this._txt) this._txt = [];
    if (this._txt[i] === undefined) this._txt[i] = this.rows[i].map((v, j) => fmt(v, this.cols[j].fmt)).join(" ").toLowerCase() + " " + (this.groups ? String(this.groups[i] || "").toLowerCase() : "");
    return this._txt[i];
  }
  apply() {
    let idx = this.rows.map((_, i) => i);
    if (this.q) idx = idx.filter((i) => this.text(i).includes(this.q));
    if (this.sort) {
      const { j, dir } = this.sort;
      const g = this.groups;
      idx.sort((a, b) => {
        if (g && g[a] !== g[b]) return 0;
        const x = this.rows[a][j], y = this.rows[b][j];
        if (x === y) return 0; if (x === null || x === "") return 1; if (y === null || y === "") return -1;
        return (isNum(x) && isNum(y) ? x - y : String(x).localeCompare(String(y), "vi")) * dir;
      });
    }
    this.idx = idx;
    this.render();
  }
  sums(list) {
    return this.cols.map((c, j) => c.sum ? list.reduce((s, i) => s + (isNum(this.rows[i][j]) ? this.rows[i][j] : 0), 0) : null);
  }
  render() {
    const { cols, rows, host } = this;
    const al = cols.map((c, j) => alignClass(c, this.sample[j]));
    $("thead", host).innerHTML = "<tr>" + cols.map((c, j) => `<th data-j="${j}" class="${al[j]}" ${this.sort && this.sort.j === j ? `aria-sort="${this.sort.dir > 0 ? "ascending" : "descending"}"` : ""}>${esc(c.caption)}</th>`).join("") + "</tr>";
    const total = this.idx.length;
    const size = this.pageSize || total || 1;
    const pages = Math.max(1, Math.ceil(total / size));
    if (this.page >= pages) this.page = pages - 1;
    const pageIdx = this.idx.slice(this.page * size, this.page * size + size);
    const g = this.groups;
    const groupSums = {}, pos = new Map();
    if (g) this.idx.forEach((i, p) => { (groupSums[g[i]] ||= []).push(i); pos.set(i, p); });
    const cell = (v, j) => {
      if (isMapLink(v)) return `<td><span class="btn small">Mở bản đồ</span></td>`;
      const txt = fmt(v, cols[j].fmt);
      const multi = typeof v === "string" && /<\s*\/?\s*br/i.test(v);
      const wide = !al[j] && txt.length > 16 ? " w" : "";
      return `<td class="${al[j]}${wide}">${multi ? `<span class="multi">${esc(txt)}</span>` : esc(txt)}</td>`;
    };
    const statusCell = (i, j) => {
      if (!this.keys || !this.keyNames || this.keyNames.status === null) return null;
      if (cols[j].name.toLowerCase() !== "statusname") return null;
      const col = this.keyNames.color !== null ? argbColor(this.keys[i][this.keyNames.color]) : null;
      return `<td><span class="pill" style="${col ? `background:${col}` : ""}">${esc(fmt(rows[i][j]))}</span></td>`;
    };
    let body = "";
    pageIdx.forEach((i, k) => {
      if (g && (k === 0 || g[pageIdx[k - 1]] !== g[i])) body += `<tr class="group"><td colspan="${cols.length}">${esc(cleanText(g[i] ?? ""))}</td></tr>`;
      body += `<tr data-i="${i}" ${this.onRow ? 'class="click" tabindex="0"' : ""}>` + rows[i].map((v, j) => statusCell(i, j) ?? cell(v, j)).join("") + "</tr>";
      const next = g ? this.idx[pos.get(i) + 1] : undefined;
      const lastOfGroup = g && (next === undefined || g[next] !== g[i]);
      if (lastOfGroup && cols.some((c) => c.sum)) {
        const s = this.sums(groupSums[g[i]]);
        body += `<tr class="subtotal">` + cols.map((c, j) => `<td class="${al[j]}">${s[j] !== null ? esc(fmt(s[j], c.fmt || "N")) : j === 0 ? "Cộng" : ""}</td>`).join("") + "</tr>";
      }
    });
    $("tbody", host).innerHTML = body || `<tr><td colspan="${cols.length}" class="empty">Không có dữ liệu</td></tr>`;
    const s = this.sums(this.idx);
    $("tfoot", host).innerHTML = cols.some((c) => c.sum) && total
      ? "<tr>" + cols.map((c, j) => `<td class="${al[j]}">${s[j] !== null ? esc(fmt(s[j], c.fmt || "N")) : j === 0 ? "Tổng cộng" : ""}</td>`).join("") + "</tr>" : "";
    if (this.cards) this.renderCards(pageIdx, s);
    $(".count", host).textContent = (this.q ? `${nf0.format(total)} / ${nf0.format(rows.length)}` : nf0.format(total)) + " dòng" + (this.note ? " · " + this.note : "");
    const pager = $(".pager", host);
    if (pages <= 1) { pager.hidden = true; return; }
    pager.hidden = false;
    pager.innerHTML = `<select aria-label="Số dòng mỗi trang">${[25, 50, 100, 500].map((n) => `<option ${n === size ? "selected" : ""}>${n}</option>`).join("")}</select> dòng/trang
      <button class="btn small" data-p="prev" ${this.page === 0 ? "disabled" : ""}>‹ Trước</button>
      <span>Trang ${this.page + 1}/${pages}</span>
      <button class="btn small" data-p="next" ${this.page >= pages - 1 ? "disabled" : ""}>Sau ›</button>`;
    $("select", pager).onchange = (e) => { this.pageSize = +e.target.value; this.page = 0; this.render(); };
    pager.onclick = (e) => {
      const p = e.target.dataset.p; if (!p) return;
      this.page += p === "next" ? 1 : -1; this.render();
      $(".table-wrap", host).scrollTop = 0;
    };
  }
  renderCards(pageIdx, sums) {
    const { cols, rows } = this;
    const stJ = cols.findIndex((c) => c.name.toLowerCase() === "statusname");
    let html = pageIdx.map((i) => {
      const r = rows[i];
      const col = stJ >= 0 && this.keyNames && this.keyNames.color !== null ? argbColor(this.keys[i][this.keyNames.color]) : null;
      const pill = stJ >= 0 ? `<span class="pill" style="${col ? `background:${col}` : ""}">${esc(fmt(r[stJ]))}</span>` : "";
      const dl = cols.map((c, j) => (j === 0 || j === stJ || r[j] === null || r[j] === "") ? "" :
        `<dt>${esc(c.caption)}</dt><dd>${isMapLink(r[j]) ? "Có bản đồ" : esc(fmt(r[j], c.fmt))}</dd>`).join("");
      return `<div class="rcard" data-i="${i}" role="button" tabindex="0"><div class="top"><b>${esc(fmt(r[0], cols[0].fmt))}</b>${pill}</div><dl>${dl}</dl></div>`;
    }).join("");
    const sumTxt = cols.map((c, j) => sums[j] !== null ? `${esc(c.caption)}: ${esc(fmt(sums[j], c.fmt || "N"))}` : "").filter(Boolean).join(" · ");
    if (sumTxt && pageIdx.length) html += `<div class="sum">Tổng cộng — ${sumTxt}</div>`;
    $(".cards", this.host).innerHTML = html || `<div class="empty">Không có dữ liệu</div>`;
  }
}

/* ------------------------------------------------------------ trang chủ */
async function pageHome(seq, den) {
  setTitle("Trang chủ");
  view.innerHTML = busy();
  const d = await api("/api/dashboard" + (den ? "?den=" + den : ""));
  if (stale(seq)) return;
  const k = d.kpi;
  const warn = [];
  if (S.me.menu_error) warn.push(`<div class="errbox">${esc(S.me.menu_error)}</div>`);
  if (S.me.menu_skipped?.length) warn.push(`<details class="warnbox"><summary>${S.me.menu_skipped.length} menu bị ẩn vì cấu hình trong database bị lỗi (chỉ quản trị thấy thông báo này)</summary><ul>` +
    S.me.menu_skipped.map((m) => `<li><b>${esc(m.id)} – ${esc(m.title)}</b>: ${esc(m.why)}</li>`).join("") + `</ul></details>`);
  const money = (v) => nf0.format(v || 0);
  view.innerHTML = warn.join("") + `
    <div class="toolbar"><p class="note grow">Số liệu bán hàng (phiếu đã duyệt hàng về hoặc gửi kho)${S.me.ma_nv ? " của nhân viên " + esc(S.me.ma_nv) : ""}.</p>
      <label for="dden" style="margin:0">Đến ngày</label><input id="dden" type="date" value="${d.den}" style="width:auto"></div>
    <div class="kpis">
      <div class="card kpi"><span>Doanh thu ngày ${dmy(d.den)}</span><b>${money(k.ngay)}</b></div>
      <div class="card kpi"><span>Doanh thu tháng ${d.den.slice(5, 7)}/${d.den.slice(0, 4)}</span><b>${money(k.thang)}</b></div>
      <div class="card kpi"><span>Số phiếu bán trong tháng</span><b>${nf0.format(k.so_phieu || 0)}</b></div>
      <div class="card kpi"><span>Khách hàng mua trong tháng</span><b>${nf0.format(k.so_kh || 0)}</b></div>
      ${k.don_cho_duyet !== null ? `<div class="card kpi"><span>Đơn web chờ duyệt</span><b>${nf0.format(k.don_cho_duyet)}</b></div>` : ""}
    </div>
    <div class="charts">
      <section class="card chart"><h2>Doanh thu theo tháng</h2>${barChart(d.thang)}</section>
      <section class="card chart"><h2>Top nhân viên bán hàng tháng ${d.den.slice(5, 7)}/${d.den.slice(0, 4)}</h2>${hbars(d.nhan_vien)}</section>
    </div>`;
  $("#dden").onchange = (e) => e.target.value && pageHome(S.seq, e.target.value);
}
function short(v) {
  if (v >= 1e9) return nfx.format(+(v / 1e9).toFixed(2)) + " tỷ";
  if (v >= 1e6) return nfx.format(+(v / 1e6).toFixed(1)) + " tr";
  return nf0.format(v);
}
function barChart(rows) {
  if (!rows.length) return `<p class="empty">Chưa có dữ liệu</p>`;
  const W = 640, H = 260, L = 8, B = 28, T = 22;
  const max = Math.max(...rows.map((r) => r.tien || 0), 1);
  const bw = (W - L * 2) / rows.length;
  const bars = rows.map((r, i) => {
    const h = ((r.tien || 0) / max) * (H - B - T);
    const x = L + i * bw + bw * 0.18, w = bw * 0.64, y = H - B - h;
    return `<rect class="bar ${i === rows.length - 1 ? "last" : ""}" x="${x}" y="${y}" width="${w}" height="${h}" rx="4"><title>${esc(r.thang)}: ${nf0.format(r.tien)}</title></rect>
      <text class="val" x="${x + w / 2}" y="${y - 6}" text-anchor="middle">${short(r.tien || 0)}</text>
      <text class="axis" x="${x + w / 2}" y="${H - 8}" text-anchor="middle">${esc(r.thang.slice(5))}/${esc(r.thang.slice(2, 4))}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Biểu đồ doanh thu theo tháng"><line class="gridline" x1="0" x2="${W}" y1="${H - B}" y2="${H - B}"/>${bars}</svg>`;
}
function hbars(rows) {
  if (!rows.length) return `<p class="empty">Chưa có dữ liệu</p>`;
  const max = Math.max(...rows.map((r) => r.tien || 0), 1);
  return `<div class="hbar">` + rows.map((r) => `<span class="nm" title="${esc(r.EmployeeID)}">${esc(r.EmployeeName || r.EmployeeID)}</span>
    <span><span class="t" style="display:block;width:${Math.max(2, ((r.tien || 0) / max) * 100)}%"></span></span><span class="am">${short(r.tien || 0)}</span>`).join("") + `</div>`;
}

/* ------------------------------------------------------------ màn hình danh sách */
async function pageList(seq, id) {
  setTitle(S.menu[id]?.title || "Danh sách");
  view.innerHTML = busy();
  const meta = await api(`/api/list/${id}/meta`);
  if (stale(seq)) return;
  setTitle(meta.title);
  const saved = S.lastList[id] || {};
  view.innerHTML = `
    <div class="card list-filters">
      <div class="filters" id="flt"></div>
      <div class="filters-foot"><p class="note" id="fltNote"></p>
        ${meta.excel ? `<button class="btn" id="bXls" type="button">Xuất Excel</button>` : ""}
        ${meta.entry?.add ? `<a class="btn" href="#/order/${esc(id)}/new">+ Thêm ${esc(meta.entry.ten.toLowerCase())}</a>` : ""}
        <button class="btn primary" id="bFind" type="button">Tìm</button></div>
    </div>
    ${meta.entry === null && /đơn hàng/i.test(meta.title) && S.me.admin ? `<p class="note">Muốn nhập đơn trên màn hình này: chạy file <b>sql\\NQW_CapNhatDatabase.sql</b> trong SSMS.</p>` : ""}
    <div class="card grid-card list-page" id="grid"></div>`;
  const flt = $("#flt");
  const ctrls = {};
  if (meta.has_date) {
    flt.insertAdjacentHTML("beforeend", `<div><label for="ftu">Từ ngày</label><input id="ftu" type="date" value="${saved.tu || meta.tu}"></div>
      <div><label for="fden">Đến ngày</label><input id="fden" type="date" value="${saved.den || meta.den}"></div>`);
  }
  for (const f of meta.filters) {
    const c = combo({ label: f.caption, value: f.locked ? f.default : (saved.filters?.[f.col] ?? f.default), locked: f.locked,
      load: f.has_options ? () => api(`/api/list/${id}/options/${encodeURIComponent(f.col)}`) : null });
    ctrls[f.col] = c; flt.append(c.el);
  }
  flt.insertAdjacentHTML("beforeend", `<div class="wide"><label for="fq">Tìm nhanh</label><input id="fq" type="search" placeholder="Số CT, khách hàng, mã hàng…" value="${esc(saved.q || "")}"></div>`);
  const body = () => ({
    tu: $("#ftu")?.value || null, den: $("#fden")?.value || null, q: $("#fq").value.trim(),
    filters: Object.fromEntries(Object.entries(ctrls).map(([k, c]) => [k, c.value])),
  });
  const load = async () => {
    const b = body();
    S.lastList[id] = b;
    const host = $("#grid");
    host.innerHTML = busy();
    try {
      const r = await api(`/api/list/${id}/rows`, { method: "POST", body: b });
      if (stale(seq)) return;
      new Grid(host, { cols: r.cols, rows: r.rows, keys: r.keys, keyNames: r.key_names, cards: true,
        note: r.truncated ? `chỉ hiện ${nf0.format(r.max_rows)} dòng đầu, hãy thu hẹp điều kiện` : "",
        onRow: (i, e) => {
          const key = String(r.keys[i][0]);
          try { sessionStorage.setItem("openMap", e && e.target.closest(".btn") ? key : ""); } catch (_) { /* bỏ qua */ }
          location.hash = `#/list/${id}/${encodeURIComponent(key)}`;
        } });
    } catch (e) { host.innerHTML = `<div class="errbox">${esc(e.message)}</div>`; }
  };
  $("#bFind").onclick = load;
  $("#fq").addEventListener("keydown", (e) => { if (e.key === "Enter") load(); });
  if ($("#bXls")) $("#bXls").onclick = async () => { try { await download(`/api/list/${id}/excel`, body()); } catch (e) { toast(e.message, true); } };
  $("#fltNote").textContent = meta.has_date ? "Mặc định: từ hôm qua đến 14 ngày tới (giống web cũ)." : "";
  load();
}

async function pageRecord(seq, id, key) {
  setTitle(S.menu[id]?.title || "Chứng từ");
  view.innerHTML = busy();
  const d = await api(`/api/list/${id}/record/${encodeURIComponent(key)}`);
  if (stale(seq)) return;
  setTitle(`${d.title} · ${d.key}`);
  const fields = d.fields.map((f) => {
    let v = f.value;
    let cls = "";
    if (f.type === "bool") v = v ? "Có" : "Không";
    else if (f.type === "date") v = dmy(v);
    else if (isNum(v)) { v = nf0.format(v); cls = "n"; }
    else v = fmt(v);
    return `<div class="f"><label>${esc(f.caption)}</label><div class="v ${cls}">${esc(v) || "&nbsp;"}</div></div>`;
  }).join("");
  view.innerHTML = `
    <div class="toolbar"><a class="btn" href="#/list/${esc(id)}">‹ Quay lại danh sách</a><span class="grow"></span>
      ${d.points.length ? `<button class="btn" id="bMap">Xem bản đồ (${d.points.length} điểm)</button>` : ""}
      ${d.entry && !d.approved && d.entry.edit ? `<a class="btn primary" href="#/order/${esc(id)}/${encodeURIComponent(d.key)}">Sửa đơn</a>` : ""}
      ${d.entry && !d.approved && d.entry.delete ? `<button class="btn danger" id="bDel">Xóa đơn</button>` : ""}
      ${d.entry && d.approved ? `<span class="chip">${esc(d.lock_reason || "Không sửa được")}</span>` : ""}
      <button class="btn" onclick="window.print()">In</button></div>
    <section class="card"><div class="form-view">${fields}</div></section>
    ${d.cols.length ? `<section class="card grid-card"><h2 class="sec-title">Chi tiết</h2><div id="lines"></div></section>` : ""}
    <section class="card" id="mapCard" hidden><div class="toolbar pad" style="padding-bottom:10px"><h2 class="grow" style="font-size:15px">Bản đồ giao hàng</h2><a class="btn small" id="gmaps" target="_blank" rel="noopener">Chỉ đường Google Maps</a></div><div id="map"></div></section>`;
  if (d.cols.length) new Grid($("#lines"), { cols: d.cols, rows: d.lines, pageSize: 0 });
  if ($("#bDel")) $("#bDel").onclick = async () => {
    if (!confirm(`Xóa đơn ${d.key}? Không khôi phục được.`)) return;
    try { await api(`/api/order/${id}/doc/${encodeURIComponent(d.key)}`, { method: "DELETE" }); toast("Đã xóa " + d.key); location.hash = `#/list/${id}`; }
    catch (e) { toast(e.message, true); }
  };
  if (d.points.length) {
    $("#bMap").onclick = () => showMap(d.points);
    let auto = false;
    try { auto = sessionStorage.getItem("openMap") === key; sessionStorage.removeItem("openMap"); } catch (_) { /* bỏ qua */ }
    if (auto) showMap(d.points);
  }
}
function loadLeaflet() {
  if (window.L) return Promise.resolve();
  return new Promise((ok, fail) => {
    const css = document.createElement("link");
    css.rel = "stylesheet"; css.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css";
    document.head.append(css);
    const s = document.createElement("script");
    s.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js";
    s.onload = ok; s.onerror = () => fail(new Error("Không tải được bản đồ (máy cần có Internet)"));
    document.head.append(s);
  });
}
async function showMap(points) {
  const card = $("#mapCard");
  card.hidden = false;
  const pts = points.slice(0, 10).map((p) => `${p.lat},${p.lng}`).join("/");
  $("#gmaps").href = "https://www.google.com/maps/dir/" + pts;
  try { await loadLeaflet(); } catch (e) { $("#map").style.height = "auto"; $("#map").innerHTML = `<div class="errbox">${esc(e.message)}</div>`; return; }
  if (card._map) { card.scrollIntoView({ behavior: "smooth" }); return; }
  const map = L.map("map");
  card._map = map;
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
  const b = [];
  for (const p of points) {
    const icon = L.divIcon({ className: "", html: `<span style="display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:#1d5fbf;color:#fff;font:700 12px sans-serif;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">${p.i}</span>`, iconSize: [26, 26], iconAnchor: [13, 13] });
    L.marker([p.lat, p.lng], { icon }).addTo(map).bindPopup(`<b>${esc(p.i)}. ${esc(p.name)}</b><br>${esc(p.addr)}<br><a target="_blank" rel="noopener" href="https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lng}">Chỉ đường</a>`);
    b.push([p.lat, p.lng]);
  }
  map.fitBounds(b, { padding: [30, 30], maxZoom: 16 });
  card.scrollIntoView({ behavior: "smooth" });
}

/* ------------------------------------------------------------ nhập đơn hàng sỉ / lẻ */
const num = (v) => { const n = parseFloat(String(v ?? "").replace(/\./g, "").replace(",", ".")); return isFinite(n) ? n : 0; };
function lineAmount(l) {
  const p = num(l.UnitPrice) - num(l.TienChietKhau), q = num(l.QuyDoi) || 1;
  return num(l.Ket) * p + num(l.Chai) * Math.round(p / q);
}
async function pageOrder(seq, id, key) {
  setTitle(S.menu[id]?.title || "Đơn hàng");
  view.innerHTML = busy();
  const meta = await api(`/api/list/${id}/meta`);
  if (stale(seq)) return;
  const ent = meta.entry;
  if (!ent) { view.innerHTML = `<div class="errbox">Màn hình này chưa nhập đơn được. Quản trị cần chạy file sql\\NQW_CapNhatDatabase.sql.</div>`; return; }
  let doc = null;
  if (key) {
    doc = await api(`/api/order/${id}/doc/${encodeURIComponent(key)}`);
    if (stale(seq)) return;
  }
  const today = todayIso();
  const tomorrow = new Date(Date.now() + 86400000 - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const h = doc ? doc.head : {};
  setTitle(`${ent.ten} · ${key || "Thêm mới"}`);
  const st = {
    lines: doc ? doc.lines.map((l) => ({ ...l, KetKM: l.KetKM, ChaiKM: l.ChaiKM })) : [],
    items: {}, cust: null,
  };
  const readOnly = doc && doc.approved;
  view.innerHTML = `
    <div class="toolbar"><a class="btn" href="#/list/${esc(id)}${key ? "/" + encodeURIComponent(key) : ""}">‹ Quay lại</a><span class="grow"></span>
      ${readOnly ? `<span class="chip">Đơn đã gửi duyệt / đã duyệt – chỉ xem</span>` : ""}</div>
    <div id="oMsg"></div>
    <section class="card"><div class="form-view order-head">
      <div class="f"><label>Số CT</label><div class="v">${esc(key || "(tự cấp khi lưu)")}</div></div>
      <div class="f"><label for="oNgay">Ngày CT</label><input id="oNgay" type="date" value="${esc((h.DocumentDate || today).slice(0, 10))}"></div>
      <div class="f" id="oEmpWrap"></div>
      <div class="f wide2" id="oCustWrap"></div>
      <div class="f"><label>Tên khách hàng</label><div class="v" id="oCustName">&nbsp;</div></div>
      <div class="f wide2"><label>Địa chỉ</label><div class="v" id="oCustAddr">&nbsp;</div></div>
      <div class="f"><label>Nợ đầu</label><div class="v n" id="oNoDau">&nbsp;</div></div>
      <div class="f"><label for="oPhone">Điện thoại</label><input id="oPhone" value="${esc(h.Phone || "")}" maxlength="50"></div>
      <div class="f"><label for="oGiao">Ngày giao</label><input id="oGiao" type="date" value="${esc((h.DeliveryDate || tomorrow).slice(0, 10))}"></div>
      <div class="f"><label>&nbsp;</label><label class="check"><input id="oTrongNgay" type="checkbox" ${h.isTrongNgay ? "checked" : ""}> Giao trong ngày</label></div>
      <div class="f"><label>&nbsp;</label><label class="check"><input id="oKhongKM" type="checkbox" ${h.isKhongKM ? "checked" : ""}> Không khuyến mãi</label></div>
      <div class="f wide2"><label for="oMemo">Ghi chú</label><input id="oMemo" value="${esc(h.Memo || "")}" maxlength="200"></div>
    </div></section>
    <section class="card grid-card">
      <div class="grid-head"><h2 class="sec-title" style="padding:0">Mặt hàng</h2><span class="count" id="oItemsNote"></span></div>
      <div class="table-wrap order-lines"><table class="grid edit"><thead><tr>
        <th>Mã hàng</th><th>Tên hàng</th><th class="n">Quy đổi</th><th class="n">Két/Thùng</th><th class="n">Chai/Lon</th>
        <th class="n">Giá chuẩn</th><th class="n">Đơn giá</th>${ent.ck ? `<th class="n">Tiền C.K</th>` : ""}
        <th class="n">Két KM</th><th class="n">Chai KM</th><th>CTKM</th><th class="n">Thành tiền</th><th></th></tr></thead>
        <tbody id="oLines"></tbody><tfoot id="oFoot"></tfoot></table></div>
      ${readOnly ? "" : `<div class="pager" style="justify-content:flex-start"><button class="btn small" id="oAdd">+ Thêm dòng</button></div>`}
      <datalist id="oItemList"></datalist><datalist id="oKmList"></datalist>
    </section>
    ${readOnly ? "" : `<div class="toolbar"><span class="grow"></span>
      <button class="btn" id="oSave">Lưu nháp</button>
      <button class="btn primary" id="oSend">Lưu &amp; gửi duyệt</button></div>
      <p class="note">“Lưu nháp”: đơn ở trạng thái <b>Đang lên đơn</b>. “Lưu &amp; gửi duyệt”: chuyển sang <b>Chờ duyệt</b> để phần mềm duyệt.</p>`}`;

  // nhân viên
  const emp = combo({ label: "Nhân viên bán hàng", value: h.EmployeeID || S.me.ma_nv || "", locked: !!S.me.ma_nv || readOnly,
    placeholder: "Chọn nhân viên", load: () => api(`/api/order/${id}/employees`) });
  $("#oEmpWrap").append(emp.el);

  // khách hàng: tìm trên server theo nhân viên + chữ gõ
  const cw = $("#oCustWrap");
  cw.innerHTML = `<label for="oCust">Khách hàng (${esc(ent.ten.replace(/^Đơn hàng /i, "khách "))})</label>
    <input id="oCust" list="oCustList" placeholder="Gõ mã, tên, địa chỉ hoặc điện thoại…" autocomplete="off" ${readOnly ? "readonly" : ""}>
    <datalist id="oCustList"></datalist>`;
  const custIn = $("#oCust");
  let custOpts = [], tmr;
  const searchCust = async () => {
    try {
      custOpts = await api(`/api/order/${id}/customers?emp=${encodeURIComponent(emp.value)}&q=${encodeURIComponent(custIn.value.includes(" - ") ? "" : custIn.value.trim())}`);
      $("#oCustList").innerHTML = custOpts.map((c) => `<option value="${esc(c.ObjectID + " - " + c.ObjectName)}">${esc(c.Address || "")}</option>`).join("");
    } catch (e) { toast(e.message, true); }
  };
  custIn.addEventListener("focus", () => { if (!custOpts.length) searchCust(); });
  custIn.addEventListener("input", () => { clearTimeout(tmr); tmr = setTimeout(searchCust, 350); });
  const custId = () => { const t = custIn.value.trim(); const m = /^([^\s]+) - /.exec(t); return m ? m[1] : t; };
  const loadCust = async (oid) => {
    if (!oid) return;
    try {
      const c = await api(`/api/order/${id}/customer/${encodeURIComponent(oid)}?ngay=${$("#oNgay").value}`);
      st.cust = c;
      custIn.value = `${c.ObjectID} - ${c.ObjectName}`;
      $("#oCustName").textContent = c.ObjectName || ""; $("#oCustAddr").textContent = c.Address || "";
      $("#oNoDau").textContent = nf0.format(c.NoDau || 0);
      if (!$("#oPhone").value) $("#oPhone").value = c.Phone || "";
      if (c.LoaiDon && c.LoaiDon !== ent.loai) showMsg([`Khách ${c.ObjectID} thuộc loại đơn ${c.LoaiDon}, không nhập ở màn hình ${ent.ten}.`]);
      else showMsg([]);
      if (!emp.value && c.EmployeeID) emp.value = c.EmployeeID;
      await loadItems(c.ObjectID);
    } catch (e) { showMsg([e.message]); }
  };
  custIn.addEventListener("change", () => loadCust(custId()));

  // hàng hóa + giá theo khách
  const loadItems = async (oid) => {
    const list = await api(`/api/order/${id}/items?obj=${encodeURIComponent(oid || "")}`);
    st.items = Object.fromEntries(list.map((i) => [i.ItemID, i]));
    $("#oItemList").innerHTML = list.map((i) => `<option value="${esc(i.ItemID)}">${esc(i.ItemName)} – ${nf0.format(i.GiaChuan)}</option>`).join("");
    $("#oItemsNote").textContent = `${list.length} mặt hàng có giá ${ent.loai === "SI" ? "sỉ" : "lẻ"}`;
    for (const l of st.lines) { const it = st.items[l.ItemID]; if (it) { l.GiaChuan = it.GiaChuan; l.QuyDoi = it.QuyDoi; l.ItemName = it.ItemName; } }
    render();
  };

  const showMsg = (errs, warns = []) => {
    $("#oMsg").innerHTML = (errs.length ? `<div class="errbox"><b>Chưa lưu được:</b><ul>${errs.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>` : "") +
      (warns.length ? `<div class="warnbox"><ul>${warns.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>` : "");
    if (errs.length) $("#oMsg").scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const LBL = { Ket: "Két/Thùng", Chai: "Chai/Lon", UnitPrice: "Đơn giá", TienChietKhau: "Tiền C.K", KetKM: "Két KM", ChaiKM: "Chai KM" };
  const inp = (i, k, v, extra = "") => `<td class="n" data-label="${LBL[k] || k}"><input data-i="${i}" data-k="${k}" inputmode="numeric" value="${v === null || v === undefined || v === "" ? "" : esc(v)}" ${readOnly ? "readonly" : ""} ${extra}></td>`;
  function render() {
    const ro = readOnly ? "readonly" : "";
    $("#oLines").innerHTML = st.lines.map((l, i) => `<tr>
      <td class="item" data-label="Mã hàng"><input data-i="${i}" data-k="ItemID" list="oItemList" value="${esc(l.ItemID || "")}" placeholder="Mã hàng" ${ro}></td>
      <td class="w name" data-label="Tên hàng">${esc(l.ItemName || "")}</td><td class="n" data-label="Quy đổi">${l.QuyDoi ? nf0.format(l.QuyDoi) : ""}</td>
      ${inp(i, "Ket", l.Ket)}${inp(i, "Chai", l.Chai)}
      <td class="n" data-label="Giá chuẩn">${l.GiaChuan ? nf0.format(l.GiaChuan) : ""}</td>
      ${inp(i, "UnitPrice", l.UnitPrice ?? l.GiaChuan)}${ent.ck ? inp(i, "TienChietKhau", l.TienChietKhau) : ""}
      ${inp(i, "KetKM", l.KetKM)}${inp(i, "ChaiKM", l.ChaiKM)}
      <td data-label="CTKM"><input data-i="${i}" data-k="KhuyenMaiID" list="oKmList" value="${esc(l.KhuyenMaiID || "")}" ${ro} class="ctkm"></td>
      <td class="n" data-label="Thành tiền"><b data-amt="${i}">${nf0.format(lineAmount({ ...l, UnitPrice: l.UnitPrice ?? l.GiaChuan }))}</b></td>
      <td class="act">${readOnly ? "" : `<button class="x" data-del="${i}" aria-label="Xóa dòng">×</button>`}</td></tr>`).join("") ||
      `<tr><td colspan="${ent.ck ? 13 : 12}" class="empty">Chưa có mặt hàng. ${readOnly ? "" : "Bấm “+ Thêm dòng”."}</td></tr>`;
    renderFoot();
  }
  function renderFoot() {
    const tk = st.lines.reduce((a, l) => a + num(l.Ket), 0), tc = st.lines.reduce((a, l) => a + num(l.Chai), 0);
    const tt = st.lines.reduce((a, l) => a + lineAmount({ ...l, UnitPrice: l.UnitPrice ?? l.GiaChuan }), 0);
    $("#oFoot").innerHTML = `<tr><td colspan="3">Tổng cộng (${st.lines.length} dòng)</td><td class="n">${nf0.format(tk)}</td><td class="n">${nf0.format(tc)}</td>
      <td colspan="${ent.ck ? 6 : 5}"></td><td class="n">${nf0.format(tt)}</td><td></td></tr>`;
  }
  $("#oLines").addEventListener("change", (e) => {
    const t = e.target, i = +t.dataset.i, k = t.dataset.k;
    if (k === undefined || isNaN(i)) return;
    const l = st.lines[i];
    if (k === "ItemID") {
      const code = t.value.trim().split(/\s/)[0];
      const it = st.items[code];
      l.ItemID = code;
      if (it) { l.ItemName = it.ItemName; l.QuyDoi = it.QuyDoi; l.GiaChuan = it.GiaChuan; l.UnitPrice = it.GiaChuan; }
      else { l.ItemName = code ? "⚠ không có trong bảng giá" : ""; l.GiaChuan = null; }
      setTimeout(() => {   // vẽ lại sau khi sự kiện blur/change kết thúc
        render();
        const next = $(`#oLines input[data-i="${i}"][data-k="Ket"]`); if (next) next.focus();
      }, 0);
      return;
    }
    l[k] = k === "KhuyenMaiID" ? t.value.trim().replace(/^.* - /, "") : (t.value.trim() === "" ? null : num(t.value));
    if (k === "KhuyenMaiID") t.value = l[k];
    const amt = $(`#oLines [data-amt="${i}"]`);
    if (amt) amt.textContent = nf0.format(lineAmount({ ...l, UnitPrice: l.UnitPrice ?? l.GiaChuan }));
    renderFoot();
  });
  $("#oLines").addEventListener("click", (e) => {
    const d = e.target.dataset.del; if (d === undefined) return;
    st.lines.splice(+d, 1); render();
  });
  if ($("#oAdd")) $("#oAdd").onclick = () => {
    st.lines.push({ ItemID: "", Ket: null, Chai: null });
    render();
    const ins = $$(`#oLines input[data-k="ItemID"]`); ins[ins.length - 1]?.focus();
  };
  $("#oTrongNgay").addEventListener("change", (e) => { if (e.target.checked) $("#oGiao").value = $("#oNgay").value; });

  const save = async (hoanTat) => {
    const btns = [$("#oSave"), $("#oSend")];
    btns.forEach((b) => (b.disabled = true));
    showMsg([]);
    const body = {
      DocumentID: key, DocumentDate: $("#oNgay").value, DeliveryDate: $("#oGiao").value, ObjectID: custId(), EmployeeID: emp.value,
      Phone: $("#oPhone").value.trim(), Memo: $("#oMemo").value.trim(), isTrongNgay: $("#oTrongNgay").checked,
      isKhongKM: $("#oKhongKM").checked, HoanTat: hoanTat,
      lines: st.lines.filter((l) => l.ItemID).map((l) => ({ ItemID: l.ItemID, Ket: l.Ket, Chai: l.Chai, KetKM: l.KetKM, ChaiKM: l.ChaiKM,
        UnitPrice: l.UnitPrice ?? l.GiaChuan, TienChietKhau: ent.ck ? l.TienChietKhau : null, KhuyenMaiID: l.KhuyenMaiID || null })),
    };
    try {
      const r = await fetch(`/api/order/${id}/save`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const j = await r.json().catch(() => ({}));
      if (r.status === 401) { showLogin(); return; }
      if (!r.ok || !j.ok) { showMsg(j.errors || [typeof j.detail === "string" ? j.detail : "Không lưu được"], j.warnings || []); return; }
      toast(`Đã lưu ${j.DocumentID}` + (hoanTat ? " – chờ duyệt" : ""));
      location.hash = `#/list/${id}/${encodeURIComponent(j.DocumentID)}`;
    } catch (e) { showMsg([e.message]); }
    finally { btns.forEach((b) => b && (b.disabled = false)); }
  };
  if ($("#oSave")) { $("#oSave").onclick = () => save(false); $("#oSend").onclick = () => save(true); }

  render();
  const loadPromos = async () => {
    try {
      const ps = await api(`/api/order/${id}/promos?ngay=${$("#oNgay").value}`);
      $("#oKmList").innerHTML = ps.map((p) => `<option value="${esc(p.label)}"></option>`).join("");
    } catch (_) { /* không có CTKM thì bỏ qua */ }
  };
  loadPromos();
  $("#oNgay").addEventListener("change", loadPromos);
  if (h.ObjectID) await loadCust(h.ObjectID);
  else { try { await loadItems(""); } catch (e) { showMsg([e.message]); } }
  if (!key && !st.lines.length) { st.lines.push({ ItemID: "", Ket: null, Chai: null }); render(); }
}

/* ------------------------------------------------------------ báo cáo */
async function pageReport(seq, id) {
  setTitle(S.menu[id]?.title || "Báo cáo");
  view.innerHTML = busy();
  const meta = await api(`/api/report/${id}/meta`);
  if (stale(seq)) return;
  setTitle(meta.title);
  const saved = S.lastReport[id] || {};
  view.innerHTML = `
    <div class="card"><div class="filters" id="prm"></div>
      <div class="filters-foot"><p class="note" id="rNote"></p>
        ${meta.excel ? `<button class="btn" id="bXls" type="button">Xuất Excel</button>` : ""}
        <button class="btn primary" id="bRun" type="button">Xem dữ liệu</button></div></div>
    <div class="card grid-card" id="grid"><div class="empty">Chọn điều kiện rồi bấm <b>Xem dữ liệu</b>.</div></div>`;
  const prm = $("#prm");
  const ctrls = {};
  for (const p of meta.params) {
    const val = saved[p.name] ?? p.default;
    if (p.type === "date") {
      const el = document.createElement("div");
      el.innerHTML = `<label for="p_${esc(p.name)}">${esc(p.caption)}</label><input id="p_${esc(p.name)}" type="date" value="${esc(val)}">`;
      prm.append(el);
      ctrls[p.name] = { get value() { return $("input", el).value; } };
    } else if (p.type === "bool") {
      const el = document.createElement("div");
      el.innerHTML = `<label>&nbsp;</label><label class="check"><input type="checkbox" ${val === "1" ? "checked" : ""}> ${esc(p.caption)}</label>`;
      prm.append(el);
      ctrls[p.name] = { get value() { return $("input", el).checked ? "1" : "0"; } };
    } else {
      const c = combo({ label: p.caption, value: p.locked ? p.default : val, locked: p.locked, placeholder: p.has_options ? "Tất cả" : "",
        load: p.has_options ? () => api(`/api/report/${id}/options/${encodeURIComponent(p.name)}`) : null });
      prm.append(c.el);
      ctrls[p.name] = c;
    }
  }
  const values = () => Object.fromEntries(Object.entries(ctrls).map(([k, c]) => [k, c.value]));
  $("#bRun").onclick = async () => {
    const v = values();
    S.lastReport[id] = v;
    const host = $("#grid");
    host.innerHTML = busy("Đang chạy báo cáo…");
    $("#bRun").disabled = true;
    try {
      const r = await api(`/api/report/${id}/run`, { method: "POST", body: { values: v } });
      if (stale(seq)) return;
      new Grid(host, { cols: r.cols, rows: r.rows, groups: r.groups, pageSize: r.groups ? 500 : 50,
        note: r.truncated ? `chỉ hiện ${nf0.format(r.max_rows)} dòng đầu` : "" });
    } catch (e) { host.innerHTML = `<div class="errbox">${esc(e.message)}</div>`; }
    finally { $("#bRun").disabled = false; }
  };
  if ($("#bXls")) $("#bXls").onclick = async () => {
    $("#bXls").disabled = true;
    try { await download(`/api/report/${id}/excel`, { values: values() }); } catch (e) { toast(e.message, true); }
    finally { $("#bXls").disabled = false; }
  };
}

/* ------------------------------------------------------------ hộp thoại */
function dialog(html, onSubmit) {
  const dlg = $("#dlg"), form = $("#dlgForm");
  form.innerHTML = html;
  form.onsubmit = async (e) => {
    const btn = e.submitter;
    if (btn && btn.value === "cancel") return;
    e.preventDefault();
    try { if ((await onSubmit(form, btn ? btn.value : "")) !== false) dlg.close(); }
    catch (err) { const p = $(".err", form); if (p) p.textContent = err.message; else toast(err.message, true); }
  };
  dlg.showModal();
}
function passwordDialog() {
  dialog(`<h2>Đổi mật khẩu</h2>
    <div><label for="pw0">Mật khẩu hiện tại</label><input id="pw0" type="password" autocomplete="current-password" required></div>
    <div><label for="pw1">Mật khẩu mới (tối thiểu 6 ký tự)</label><input id="pw1" type="password" autocomplete="new-password" minlength="6" required></div>
    <div><label for="pw2">Nhập lại mật khẩu mới</label><input id="pw2" type="password" autocomplete="new-password" minlength="6" required></div>
    <p class="err"></p>
    <div class="actions"><button class="btn" value="cancel" formnovalidate>Hủy</button><button class="btn primary">Lưu</button></div>`,
  async (f) => {
    if ($("#pw1", f).value !== $("#pw2", f).value) throw new Error("Hai lần nhập mật khẩu mới không giống nhau");
    await api("/api/doi-mat-khau", { method: "POST", body: { old: $("#pw0", f).value, new: $("#pw1", f).value } });
    toast("Đã đổi mật khẩu");
  });
}

/* ------------------------------------------------------------ người dùng web */
async function pageUsers(seq) {
  setTitle("Người dùng web");
  view.innerHTML = busy();
  const [users, lists] = await Promise.all([api("/api/nguoi-dung"), api("/api/danh-muc-quyen")]);
  if (stale(seq)) return;
  const gname = Object.fromEntries(lists.nhom.map((g) => [g.UserGroupID, g.UserGroupName]));
  view.innerHTML = `
    <div class="toolbar"><p class="note grow">Tài khoản đăng nhập web lưu riêng trong web này. Quyền xem menu lấy theo <b>nhóm</b> trong phần mềm (bảng phân quyền web WA_UserGroupPermisstion). Gán <b>mã nhân viên</b> thì người dùng chỉ thấy dữ liệu của nhân viên đó.</p>
      <button class="btn primary" id="bAdd">Thêm người dùng</button></div>
    ${lists.loi ? `<div class="errbox">Không đọc được nhóm/nhân viên từ database: ${esc(lists.loi)}</div>` : ""}
    <div class="card grid-card" id="ugrid"></div>
    <div id="khoaBox"></div>`;
  const cols = [{ name: "u", caption: "Tên đăng nhập" }, { name: "n", caption: "Họ tên" }, { name: "r", caption: "Vai trò" },
    { name: "g", caption: "Nhóm quyền" }, { name: "e", caption: "Chỉ xem NV" }, { name: "s", caption: "Trạng thái" }];
  const rows = users.map((u) => [u.ten_dang_nhap, u.ho_ten, u.la_admin ? "Quản trị" : "Người dùng",
    u.nhom ? `${u.nhom}${gname[u.nhom] ? " – " + gname[u.nhom] : ""}` : "", u.ma_nv || "", u.dang_dung ? "Đang dùng" : "Đã khóa"]);
  new Grid($("#ugrid"), { cols, rows, pageSize: 0, onRow: (i) => userDialog(users[i], lists) });
  $("#bAdd").onclick = () => userDialog(null, lists);
  loadKhoa(seq);
}

async function loadKhoa(seq) {
  const box = $("#khoaBox");
  if (!box) return;
  let ds = [];
  try { ds = await api("/api/khoa/danh-sach"); } catch (_) { return; }
  if (stale(seq) || !box.isConnected) return;
  if (!ds.length) {
    box.innerHTML = `<p class="note" style="margin-top:14px">Không có tài khoản nào đang bị khóa đăng nhập.</p>`;
    return;
  }
  box.innerHTML = `<h3 style="margin:18px 0 8px">Tài khoản đang bị khóa đăng nhập (${ds.length})</h3>
    <div class="card grid-card"><table class="grid"><thead><tr>
      <th>Tên đăng nhập</th><th class="num">Số lần sai</th><th>Tình trạng</th><th></th>
    </tr></thead><tbody>${ds.map((k) => `<tr>
      <td>${esc(k.ten_dang_nhap)}</td>
      <td class="num">${k.so_lan_sai}</td>
      <td>${k.vinh_vien ? "Khóa (chờ admin mở)" : `Tạm khóa, còn ~${k.con_phut} phút`}</td>
      <td><button class="btn primary small" data-mo="${esc(k.ten_dang_nhap)}">Mở khóa</button></td>
    </tr>`).join("")}</tbody></table></div>`;
  $$("[data-mo]", box).forEach((b) => b.onclick = async () => {
    const name = b.getAttribute("data-mo");
    if (!confirm("Mở khóa đăng nhập cho tài khoản " + name + "?")) return;
    try { await api("/api/khoa/mo/" + encodeURIComponent(name), { method: "POST" }); toast("Đã mở khóa " + name); route(); }
    catch (err) { toast(err.message, true); }
  });
}
function userDialog(u, lists) {
  const isNew = !u;
  u = u || { ten_dang_nhap: "", ho_ten: "", la_admin: 0, nhom: "", ma_nv: "", dang_dung: 1 };
  const gOpts = `<option value="">— Chọn nhóm —</option>` + lists.nhom.map((g) => `<option value="${esc(g.UserGroupID)}" ${g.UserGroupID === u.nhom ? "selected" : ""}>${esc(g.UserGroupID)} – ${esc(g.UserGroupName || "")}</option>`).join("");
  dialog(`<h2>${isNew ? "Thêm người dùng" : "Sửa người dùng " + esc(u.ten_dang_nhap)}</h2>
    <div class="row2"><div><label for="uu">Tên đăng nhập</label><input id="uu" value="${esc(u.ten_dang_nhap)}" ${isNew ? "" : "readonly"} required pattern="[A-Za-z0-9_.\\-]{2,40}"></div>
    <div><label for="un">Họ tên</label><input id="un" value="${esc(u.ho_ten)}"></div></div>
    <div><label for="up">${isNew ? "Mật khẩu" : "Mật khẩu mới (để trống nếu không đổi)"}</label><input id="up" type="password" autocomplete="new-password" minlength="6" ${isNew ? "required" : ""}></div>
    <label class="check"><input id="ua" type="checkbox" ${u.la_admin ? "checked" : ""}> Quản trị (xem được tất cả menu, quản lý người dùng)</label>
    <div class="row2"><div><label for="ug">Nhóm quyền</label><select id="ug">${gOpts}</select></div><div id="ueWrap"></div></div>
    <label class="check"><input id="us" type="checkbox" ${u.dang_dung ? "checked" : ""}> Đang dùng</label>
    <p class="err"></p>
    <div class="actions">${isNew ? "" : `<button class="btn danger" value="delete" type="submit" formnovalidate>Xóa</button><span style="flex:1"></span>`}<button class="btn" value="cancel" formnovalidate>Hủy</button><button class="btn primary" value="save">Lưu</button></div>`,
  async (f, act) => {
    if (act === "delete") {
      if (!confirm("Xóa tài khoản " + u.ten_dang_nhap + "?")) return false;
      await api("/api/nguoi-dung/" + encodeURIComponent(u.ten_dang_nhap), { method: "DELETE" });
    } else {
      await api("/api/nguoi-dung", { method: "POST", body: {
        ten_dang_nhap: $("#uu", f).value.trim(), ho_ten: $("#un", f).value.trim(), mat_khau: $("#up", f).value || null,
        la_admin: $("#ua", f).checked, nhom: $("#ug", f).value || null, ma_nv: emp.value || null, dang_dung: $("#us", f).checked } });
    }
    toast("Đã lưu"); route();
  });
  const emp = combo({ label: "Chỉ xem dữ liệu nhân viên", value: u.ma_nv || "", placeholder: "Để trống = xem tất cả",
    load: async () => lists.nhan_vien.map((e) => ({ value: e.EmployeeID, label: `${e.EmployeeName} - ${e.EmployeeID}` })) });
  $("#ueWrap").append(emp.el);
}

/* ------------------------------------------------------------ nhật ký */
async function pageLog(seq) {
  setTitle("Nhật ký web");
  const t = todayIso();
  view.innerHTML = `<div class="card"><div class="filters"><div><label for="lt">Từ ngày</label><input id="lt" type="date" value="${t.slice(0, 8)}01"></div>
    <div><label for="ld">Đến ngày</label><input id="ld" type="date" value="${t}"></div>
    <div><label for="ln">Người dùng</label><input id="ln" placeholder="Tất cả"></div></div>
    <div class="filters-foot"><span class="grow"></span><button class="btn primary" id="bLog">Xem</button></div></div>
    <div class="card grid-card" id="lgrid"></div>`;
  const load = async () => {
    const rows = await api(`/api/nhat-ky?tu=${$("#lt").value}&den=${$("#ld").value}&nguoi=${encodeURIComponent($("#ln").value.trim())}`);
    if (stale(seq)) return;
    new Grid($("#lgrid"), { cols: [{ name: "t", caption: "Thời gian" }, { name: "u", caption: "Người dùng" }, { name: "a", caption: "Thao tác" }, { name: "d", caption: "Chi tiết" }],
      rows: rows.map((r) => [r.thoi_gian, r.nguoi, r.hanh_dong, r.chi_tiet]) });
  };
  $("#bLog").onclick = load;
  load();
}

boot();
