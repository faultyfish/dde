/* ── State ───────────────────────────────────────────────── */
const state = {
  category: "", level: "", remote: "", type: "", source: "",
  visa: false, q: "", page: 0,
  total: 0, jobs: [],
};

const API = CONFIG.API_BASE_URL;
const PER_PAGE = CONFIG.JOBS_PER_PAGE;

/* ── Category colours ────────────────────────────────────── */
const CAT = {
  DevOps: { border: "#00d4aa", text: "#00d4aa", bg: "#00d4aa18" },
  Cloud:  { border: "#4f9eff", text: "#4f9eff", bg: "#4f9eff18" },
  SRE:    { border: "#ff6b35", text: "#ff6b35", bg: "#ff6b3518" },
  MLOps:  { border: "#bf5af2", text: "#bf5af2", bg: "#bf5af218" },
};
const LEVEL_COLOR = {
  Graduate: "#ffd60a", Junior: "#06d6a0", Mid: "#4f9eff",
  Senior: "#ff6b35", Lead: "#bf5af2",
};

/* ── Fetch helpers ───────────────────────────────────────── */
async function fetchStats() {
  try {
    const r = await fetch(`${API}/stats`);
    const d = await r.json();
    document.getElementById("stat-total").textContent   = d.total ?? "—";
    document.getElementById("stat-remote").textContent  = d.remote_count ?? "—";
    document.getElementById("stat-visa").textContent    = d.visa_count ?? "—";
    const ts = d.last_scraped ? new Date(d.last_scraped) : null;
    document.getElementById("stat-scraped").textContent = ts
      ? ts.toLocaleDateString("en-IE", { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" })
      : "—";
  } catch (e) {
    console.error("Stats fetch failed", e);
  }
}

async function fetchJobs() {
  const params = new URLSearchParams();
  if (state.category) params.set("category",    state.category);
  if (state.level)    params.set("level",        state.level);
  if (state.remote)   params.set("remote_type",  state.remote);
  if (state.type)     params.set("job_type",     state.type);
  if (state.source)   params.set("source",       state.source);
  if (state.visa)     params.set("visa",         "true");
  if (state.q)        params.set("q",            state.q);
  params.set("limit",  String(PER_PAGE));
  params.set("offset", String(state.page * PER_PAGE));

  showSkeletons();
  try {
    const r = await fetch(`${API}/jobs?${params}`);
    const d = await r.json();
    state.total = d.total;
    state.jobs  = d.jobs;
    renderJobs();
    renderPagination();
    document.getElementById("results-meta").textContent =
      `${d.total} role${d.total !== 1 ? "s" : ""} found`;
  } catch (e) {
    document.getElementById("jobs-grid").innerHTML =
      `<div class="empty-state"><div class="icon">⚠️</div>API unavailable. Check Render deployment.</div>`;
    console.error(e);
  }
}

/* ── Render ──────────────────────────────────────────────── */
function showSkeletons() {
  const grid = document.getElementById("jobs-grid");
  grid.innerHTML = Array(6).fill(0).map(() => `
    <div class="job-card" style="pointer-events:none">
      <div class="skeleton" style="height:18px;width:70%;margin-bottom:8px"></div>
      <div class="skeleton" style="height:12px;width:40%"></div>
      <div class="skeleton" style="height:60px;margin-top:8px"></div>
      <div class="skeleton" style="height:12px;width:80%;margin-top:8px"></div>
    </div>
  `).join("");
}

function badge(text, color, bg) {
  return `<span class="badge" style="color:${color};background:${bg||color+"18"};border-color:${color}44">${text}</span>`;
}

function renderJobs() {
  const grid = document.getElementById("jobs-grid");
  if (!state.jobs.length) {
    grid.innerHTML = `<div class="empty-state"><div class="icon">⚙️</div>No roles match your filters.<br><small>Try adjusting or resetting.</small></div>`;
    return;
  }
  grid.innerHTML = state.jobs.map(j => {
    const cat   = CAT[j.category] || CAT.DevOps;
    const lvlc  = LEVEL_COLOR[j.level] || "#94a3b8";
    const stack = (j.stack || []).slice(0, 6).map(s =>
      `<span class="stack-tag">${s}</span>`).join("");
    const salary = j.salary_raw
      ? `<span class="salary" style="color:${cat.text}">${j.salary_raw}</span>` : "";
    const since = j.last_seen_at
      ? timeAgo(new Date(j.last_seen_at)) : "";
    const src = j.source === "indeed"
      ? `<span class="source-tag" style="color:#36b0f5">Indeed</span>`
      : `<span class="source-tag" style="color:#0a66c2">LinkedIn</span>`;

    return `
    <div class="job-card" data-id="${j.id}"
      style="border-color:${cat.border}33"
      onmouseenter="this.style.borderColor='${cat.border}88';this.style.boxShadow='0 12px 40px ${cat.border}1a'"
      onmouseleave="this.style.borderColor='${cat.border}33';this.style.boxShadow='none'">
      <div class="card-glow" style="background:radial-gradient(circle at top right,${cat.border}12,transparent 70%)"></div>

      <div class="card-header">
        <div>
          <div class="card-title">${esc(j.title)}</div>
          <div class="card-company">${esc(j.company)} · ${esc(j.location || "")}</div>
        </div>
        ${badge(j.category, cat.text, cat.bg)}
      </div>

      <div class="card-desc">${esc(j.description || "No description available.")}</div>

      <div class="stack-tags">${stack}</div>

      <div class="card-footer">
        <div class="badge-row">
          ${badge(j.level || "Mid", lvlc)}
          ${badge(j.remote_type || "On-site", "#64748b")}
          ${badge(j.job_type || "Full-time", j.job_type === "Contract" ? "#fbbf24" : "#64748b")}
          ${j.visa_sponsor ? badge("✓ Visa Sponsor", "#06d6a0") : ""}
        </div>
        ${salary}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div class="card-date">${since}</div>
        ${src}
      </div>
    </div>`;
  }).join("");

  // Bind click to open modal
  grid.querySelectorAll(".job-card").forEach(card => {
    card.addEventListener("click", () => openModal(parseInt(card.dataset.id)));
  });
}

function renderPagination() {
  const total_pages = Math.ceil(state.total / PER_PAGE);
  const pg = document.getElementById("pagination");
  if (total_pages <= 1) { pg.innerHTML = ""; return; }

  let html = `<button class="page-btn" ${state.page === 0 ? "disabled" : ""}
    onclick="gotoPage(${state.page - 1})">← Prev</button>`;

  for (let i = 0; i < total_pages; i++) {
    if (i === 0 || i === total_pages-1 || Math.abs(i - state.page) <= 2) {
      html += `<button class="page-btn ${i === state.page ? "active" : ""}"
        onclick="gotoPage(${i})">${i + 1}</button>`;
    } else if (Math.abs(i - state.page) === 3) {
      html += `<span style="color:var(--dim);font-family:var(--font-mono)">…</span>`;
    }
  }

  html += `<button class="page-btn" ${state.page >= total_pages-1 ? "disabled" : ""}
    onclick="gotoPage(${state.page + 1})">Next →</button>`;
  pg.innerHTML = html;
}

function gotoPage(n) {
  state.page = n;
  window.scrollTo({ top: 0, behavior: "smooth" });
  fetchJobs();
}

/* ── Modal ───────────────────────────────────────────────── */
async function openModal(id) {
  const overlay = document.getElementById("modal-overlay");
  const body    = document.getElementById("modal-body");
  overlay.classList.add("open");
  body.innerHTML = `<div class="skeleton" style="height:180px"></div>`;

  try {
    const r = await fetch(`${API}/jobs/${id}`);
    const j = await r.json();
    const cat  = CAT[j.category] || CAT.DevOps;
    const lvlc = LEVEL_COLOR[j.level] || "#94a3b8";
    const stack = (j.stack || []).map(s => `<span class="stack-tag">${s}</span>`).join(" ");

    body.innerHTML = `
      <div class="modal-title">${esc(j.title)}</div>
      <div class="modal-company">${esc(j.company)} · ${esc(j.location || "")}</div>
      <div class="modal-badges">
        ${badge(j.category, cat.text, cat.bg)}
        ${badge(j.level || "Mid", lvlc)}
        ${badge(j.remote_type, "#64748b")}
        ${badge(j.job_type, j.job_type === "Contract" ? "#fbbf24" : "#64748b")}
        ${j.visa_sponsor ? badge("✓ Visa Sponsor", "#06d6a0") : ""}
        ${j.salary_raw ? badge(j.salary_raw, cat.text) : ""}
        ${badge(j.source === "indeed" ? "Indeed" : "LinkedIn", j.source === "indeed" ? "#36b0f5" : "#0a66c2")}
      </div>
      <div class="stack-tags" style="margin-bottom:20px">${stack}</div>
      <div class="modal-desc">${esc(j.description || "")}</div>
      <a class="modal-apply" href="${j.url}" target="_blank" rel="noopener">Apply on ${j.source === "indeed" ? "Indeed" : "LinkedIn"} →</a>
    `;
  } catch(e) {
    body.innerHTML = `<p style="color:var(--orange)">Failed to load job details.</p>`;
  }
}

document.getElementById("modal-close").addEventListener("click", () =>
  document.getElementById("modal-overlay").classList.remove("open"));
document.getElementById("modal-overlay").addEventListener("click", e => {
  if (e.target === e.currentTarget)
    e.currentTarget.classList.remove("open");
});

/* ── Filters ─────────────────────────────────────────────── */
function setupPills(groupId, stateKey) {
  document.getElementById(groupId).querySelectorAll(".pill").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById(groupId).querySelectorAll(".pill")
        .forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state[stateKey] = btn.dataset.val;
      state.page = 0;
      fetchJobs();
    });
  });
}

setupPills("f-category", "category");
setupPills("f-level",    "level");
setupPills("f-remote",   "remote");
setupPills("f-type",     "type");
setupPills("f-source",   "source");

// Visa toggle
const visaToggle = document.getElementById("visa-toggle");
visaToggle.addEventListener("click", () => {
  state.visa = !state.visa;
  visaToggle.classList.toggle("on", state.visa);
  document.getElementById("visa-label").style.color = state.visa ? "var(--green)" : "var(--muted)";
  state.page = 0;
  fetchJobs();
});

// Search (debounced)
let searchTimer;
document.getElementById("search").addEventListener("input", e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.q = e.target.value.trim();
    state.page = 0;
    fetchJobs();
  }, 400);
});

// Reset
document.getElementById("reset-btn").addEventListener("click", () => {
  state.category = ""; state.level = ""; state.remote = "";
  state.type = ""; state.source = ""; state.visa = false;
  state.q = ""; state.page = 0;
  document.getElementById("search").value = "";
  document.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".pills").forEach(g => {
    const first = g.querySelector("[data-val='']");
    if (first) first.classList.add("active");
  });
  visaToggle.classList.remove("on");
  document.getElementById("visa-label").style.color = "var(--muted)";
  fetchJobs();
});

/* ── Helpers ─────────────────────────────────────────────── */
function esc(str) {
  return String(str || "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function timeAgo(date) {
  const s = Math.floor((Date.now() - date) / 1000);
  if (s < 60)   return "just now";
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400)return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

/* ── Boot ────────────────────────────────────────────────── */
fetchStats();
fetchJobs();
