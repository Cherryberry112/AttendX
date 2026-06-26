/* ============================================================
   AttendX — API Client & Shared JS Utilities
   ============================================================ */

const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
  ? "http://localhost:5000/api" 
  : "https://attendx-api.onrender.com/api";

/* ── Auth Token Helpers ──────────────────────────────────────── */
const Auth = {
  setToken: (token) => localStorage.setItem("ax_token", token),
  getToken: () => localStorage.getItem("ax_token"),
  setUser:  (user) => localStorage.setItem("ax_user", JSON.stringify(user)),
  getUser:  () => {
    try { return JSON.parse(localStorage.getItem("ax_user")); }
    catch { return null; }
  },
  clear: () => { localStorage.removeItem("ax_token"); localStorage.removeItem("ax_user"); },
  guard: (requiredRole) => {
    const user = Auth.getUser();
    if (!user || !Auth.getToken()) {
      window.location.href = "/index.html";
      return false;
    }
    if (requiredRole && user.role !== requiredRole) {
      window.location.href = "/index.html";
      return false;
    }
    return true;
  },
};

/* ── API Fetch Wrapper ───────────────────────────────────────── */
const api = {
  _req: async (method, path, body = null) => {
    const token = Auth.getToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  },
  get:    (path)         => api._req("GET",    path),
  post:   (path, body)   => api._req("POST",   path, body),
  put:    (path, body)   => api._req("PUT",    path, body),
  delete: (path)         => api._req("DELETE", path),
};

/* ── Toast Notifications ─────────────────────────────────────── */
function ensureToastContainer() {
  let c = document.getElementById("toast-container");
  if (!c) {
    c = document.createElement("div");
    c.id = "toast-container";
    c.className = "toast-container";
    document.body.appendChild(c);
  }
  return c;
}

function showToast(message, type = "info", duration = 3500) {
  const container = ensureToastContainer();
  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "fadeOut 0.4s ease forwards";
    toast.addEventListener("animationend", () => toast.remove());
  }, duration);
}

/* ── Modal Helpers ───────────────────────────────────────────── */
function openModal(id) {
  document.getElementById(id)?.classList.add("open");
}
function closeModal(id) {
  document.getElementById(id)?.classList.remove("open");
}

/* ── Sidebar Rendering ───────────────────────────────────────── */
function renderSidebar(role, activePage) {
  const user = Auth.getUser();
  if (!user) return;

  const navs = {
    teacher: [
      { icon: "📊", label: "Dashboard",     href: "dashboard.html" },
      { icon: "📚", label: "My Courses",    href: "dashboard.html" },
      { icon: "👤", label: "Profile",       href: "profile.html" },
    ],
    student: [
      { icon: "📊", label: "Dashboard",     href: "dashboard.html" },
      { icon: "📚", label: "My Courses",    href: "dashboard.html" },
      { icon: "🎭", label: "Face Enroll",   href: "enroll.html" },
      { icon: "👤", label: "Profile",       href: "profile.html" },
    ],
    admin: [
      { icon: "📊", label: "Dashboard",     href: "dashboard.html" },
      { icon: "👥", label: "Users",         href: "users.html" },
      { icon: "📚", label: "Courses",       href: "courses.html" },
      { icon: "🗓️",  label: "Attendance",   href: "attendance_log.html" },
    ],
  };

  const links = navs[role] || [];
  const navHTML = links.map(n => `
    <a class="nav-link ${n.label === activePage ? "active" : ""}" href="${n.href}">
      <span class="nav-icon">${n.icon}</span> ${n.label}
    </a>
  `).join("");

  const initials = user.name?.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();

  document.getElementById("sidebar-placeholder")?.insertAdjacentHTML("afterend", `
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-logo">
        <div class="logo-icon">AX</div>
        <span class="logo-text">Attend<span>X</span></span>
      </div>
      <nav class="nav-section">
        <div class="nav-label">Navigation</div>
        ${navHTML}
      </nav>
      <div class="sidebar-footer">
        <div class="user-chip">
          <div class="avatar">${initials}</div>
          <div class="user-info">
            <div class="user-name">${user.name}</div>
            <div class="user-role">${user.role}</div>
          </div>
        </div>
        <button class="btn btn-outline btn-sm btn-block" onclick="logout()">🚪 Logout</button>
      </div>
    </aside>
  `);
  document.getElementById("sidebar-placeholder")?.remove();
}

function logout() {
  Auth.clear();
  window.location.href = "/index.html";
}

/* ── Attendance Ring ─────────────────────────────────────────── */
function createRing(pct, size = 100, strokeWidth = 8) {
  const r = (size / 2) - strokeWidth;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (pct / 100) * circumference;
  const color = pct >= 75 ? "#0F9B58" : pct >= 50 ? "#FFB347" : "#FF4D6D";

  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size/2}" cy="${size/2}" r="${r}"
        fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="${strokeWidth}"/>
      <circle cx="${size/2}" cy="${size/2}" r="${r}"
        fill="none" stroke="${color}" stroke-width="${strokeWidth}"
        stroke-linecap="round"
        stroke-dasharray="${circumference}"
        stroke-dashoffset="${offset}"
        transform="rotate(-90 ${size/2} ${size/2})"
        style="transition: stroke-dashoffset 1s ease"/>
    </svg>
  `;
}

/* ── Date Formatter ──────────────────────────────────────────── */
function fmtDate(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric"
  });
}

/* ── Export all ──────────────────────────────────────────────── */
window.Auth = Auth;
window.api = api;
window.showToast = showToast;
window.openModal = openModal;
window.closeModal = closeModal;
window.renderSidebar = renderSidebar;
window.logout = logout;
window.createRing = createRing;
window.fmtDate = fmtDate;
