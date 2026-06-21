/**
 * auth-store.js
 * Session helpers shared between login and all dashboard pages.
 * Stores the JWT token returned by the backend alongside basic profile info.
 */
const AgriAuth = {
  SESSION_KEY: "agriPulseSession",
  REMEMBER_KEY: "agriPulseRemember",

  /** Backend origin — relative when served from FastAPI, absolute for file:// or different port */
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

  getSession() {
    try {
      const raw = localStorage.getItem("agri_session") || sessionStorage.getItem("agri_session");
      if (raw) {
        const s = JSON.parse(raw);
        if (s && s.role === "officer") {
          return {
            userId: s.id,
            username: s.username,
            name: s.name,
            role: s.role
          };
        }
      }
      return null;
    } catch {
      return null;
    }
  },

  /**
   * Called after a successful API login (backward compatibility fallback).
   */
  setSession(profile, token, remember) {
    const payload = {
      id: profile.id,
      username: profile.username,
      name: profile.name,
      role: "officer"
    };
    const sessionStr = JSON.stringify(payload);
    if (remember) {
      localStorage.setItem("agri_session", sessionStr);
    } else {
      sessionStorage.setItem("agri_session", sessionStr);
    }
    return {
      userId: payload.id,
      username: payload.username,
      name: payload.name,
      role: payload.role
    };
  },

  clearSession() {
    try {
      localStorage.removeItem("agri_session");
      sessionStorage.removeItem("agri_session");
    } catch {}
  },

  requireAuth(loginPath) {
    if (!this.getSession()) {
      window.location.href = "/login.html";
      return false;
    }
    return true;
  },

  requireOfficer() {
    if (!this.getSession()) {
      window.location.href = "/login.html";
      return false;
    }
    return true;
  },
};
