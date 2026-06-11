const MANAGER_PAGES = new Set([
  "manager_dashboard.html", "manager_dashboard",
  "manager_officers.html", "manager_officers",
  "manager_tasks.html", "manager_tasks",
  "manager_performance.html", "manager_performance",
  "manager_reports.html", "manager_reports",
  "manager_settings.html", "manager_settings",
]);

const AgriAuth = {
  /** Backend origin — use absolute URL when HTML is not served from port 8000 */
  apiOrigin() {
    if (location.protocol === "file:") return "http://127.0.0.1:8000";
    const host = location.hostname;
    const port = location.port;
    if ((host === "localhost" || host === "127.0.0.1") && port && port !== "8000") {
      return "http://127.0.0.1:8000";
    }
    return "";
  },

  apiUrl(path) {
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${this.apiOrigin()}${p}`;
  },

  async apiFetch(path, options) {
    const res = await fetch(this.apiUrl(path), options);
    return res;
  },

  getSession() {
    try {
      const raw = localStorage.getItem("agri_session") || sessionStorage.getItem("agri_session");
      if (raw) return JSON.parse(raw);

      const userData = localStorage.getItem("user_data") || sessionStorage.getItem("user_data");
      if (userData) {
        const user = JSON.parse(userData);
        const fullName = ((user.first_name || "") + " " + (user.last_name || "")).trim() || user.name || user.username || "User";
        const role = (user.is_staff || user.role === "manager") ? "manager" : "officer";
        const mapped = { id: user.id, username: user.username, name: fullName, role: role };
        this.setSession(mapped);
        return mapped;
      }
      return null;
    } catch {
      return null;
    }
  },

  setSession(d) {
    try { localStorage.setItem("agri_session", JSON.stringify(d)); } catch {}
  },

  clearSession() {
    try {
      localStorage.removeItem("agri_session");
      localStorage.removeItem("user_data");
      localStorage.removeItem("access_token");
      sessionStorage.removeItem("user_data");
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("agri_session");
    } catch {}
  },

  requireAuth(p) {
    const s = this.getSession();
    if (!s) { window.location.replace(p); return false; }
    return true;
  },

  /** Default manager session so portal pages work without login during development */
  ensureManagerSession() {
    if (this.getSession()) return;
    this.setSession({
      id: 1,
      username: "admin",
      name: "Manager",
      role: "manager",
    });
  },
};

const currentPage = window.location.pathname.split("/").pop() || "";
const pageKey = currentPage.replace(".html", "");

if (MANAGER_PAGES.has(currentPage) || MANAGER_PAGES.has(pageKey)) {
  AgriAuth.ensureManagerSession();
} else if (
  currentPage &&
  currentPage !== "login.html" &&
  currentPage !== "login" &&
  currentPage !== ""
) {
  if (!AgriAuth.getSession()) {
    window.location.replace("login.html");
  }
}
