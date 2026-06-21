const HR_PAGES = new Set([
  "hr_dashboard.html", "hr_dashboard",
  "hr_managers.html", "hr_managers",
  "hr_officers.html", "hr_officers",
  "hr_tasks.html", "hr_tasks",
  "hr_task_detail.html", "hr_task_detail",
  "hr_settings.html", "hr_settings",
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

  async apiFetch(path, options = {}) {
    // If body is present and it is an object, convert to string
    const headers = options.headers || {};
    if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
      options.body = JSON.stringify(options.body);
      headers["Content-Type"] = "application/json";
    }
    options.headers = headers;
    const res = await fetch(this.apiUrl(path), options);
    return res;
  },

  getSession() {
    try {
      const raw = localStorage.getItem("agri_session") || sessionStorage.getItem("agri_session");
      if (raw) {
        const session = JSON.parse(raw);
        if (session && session.role === "hr") {
          return session;
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

  /** Default HR session so portal pages work without login during development if dev_mode is set */
  ensureHrSession() {
    if (this.getSession()) return;
    if (localStorage.getItem("dev_mode") === "true") {
      this.setSession({
        id: 1,
        username: "admin",
        name: "HR Administrator",
        role: "hr",
      });
    }
  },
};

const currentPage = window.location.pathname.split("/").pop() || "";
const pageKey = currentPage.replace(".html", "");

if (HR_PAGES.has(currentPage) || HR_PAGES.has(pageKey)) {
  AgriAuth.ensureHrSession();
}

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
