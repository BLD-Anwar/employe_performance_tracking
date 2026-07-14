const MANAGER_PAGES = new Set([
  "manager_dashboard.html", "manager_dashboard",
  "manager_officers.html", "manager_officers",
  "manager_tasks.html", "manager_tasks",
  "manager_performance.html", "manager_performance",
  "manager_reports.html", "manager_reports",
  "manager_settings.html", "manager_settings",
  "manager_task_detail.html", "manager_task_detail",
  "manager_farmers.html", "manager_farmers",
  "manager_campaign_reports.html", "manager_campaign_reports",
]);

const AgriAuth = {
  /** Backend origin — use absolute URL when HTML is not served from port 8000 */
  apiOrigin() {
    if (location.protocol === "file:") return "http://127.0.0.1:8000";
    const port = location.port;
    if (port && port !== "8000") {
      return `${location.protocol}//${location.hostname}:8000`;
    }
    return "";
  },

  apiUrl(path) {
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${this.apiOrigin()}${p}`;
  },

  async apiFetch(path, options = {}) {
    const headers = options.headers || {};
    const session = this.getSession();
    if (session && session.token) {
      headers["Authorization"] = `Bearer ${session.token}`;
    }
    options.headers = headers;
    const res = await fetch(this.apiUrl(path), options);
    if (res.status === 401) {
      this.clearSession();
      window.location.href = "/login.html";
      return null;
    }
    return res;
  },

  getSession() {
    try {
      const raw = localStorage.getItem("agri_session") || sessionStorage.getItem("agri_session");
      if (raw) {
        const s = JSON.parse(raw);
        if (s && s.role === "manager") {
          return {
            id: s.id,
            userId: s.id,
            username: s.username,
            name: s.name,
            role: s.role,
            token: s.token || s.access_token
          };
        }
      }
      return null;
    } catch {
      return null;
    }
  },

  setSession(d) {
    try { 
      const sessionStr = JSON.stringify(d);
      localStorage.setItem("agri_session", sessionStr);
    } catch {}
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
    if (!s) { window.location.replace("/login.html"); return false; }
    return true;
  },

  ensureManagerSession() {
    const s = this.getSession();
    if (!s) { window.location.replace("/login.html"); }
  },
};

const currentPage = window.location.pathname.split("/").pop() || "";
const pageKey = currentPage.replace(".html", "");

if (
  currentPage &&
  currentPage !== "login.html" &&
  currentPage !== "login" &&
  currentPage !== ""
) {
  if (!AgriAuth.getSession()) {
    window.location.replace("/login.html");
  }
}
