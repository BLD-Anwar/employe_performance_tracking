/**
 * auth-store.js
 * Session helpers shared between login and all dashboard pages.
 * Stores the JWT token returned by the backend alongside basic profile info.
 */
const AgriAuth = {
  SESSION_KEY: "agriPulseSession",
  REMEMBER_KEY: "agriPulseRemember",

  getSession() {
    const rawSession = sessionStorage.getItem(this.SESSION_KEY);
    const rawRemember = localStorage.getItem(this.REMEMBER_KEY);

    if (rawSession) {
      try { return JSON.parse(rawSession); }
      catch { sessionStorage.removeItem(this.SESSION_KEY); }
    }
    if (rawRemember) {
      try { return JSON.parse(rawRemember); }
      catch { localStorage.removeItem(this.REMEMBER_KEY); }
    }
    return null;
  },

  /**
   * Called after a successful API login.
   * @param {object} profile  - ProfileResponse from GET /me
   * @param {string} token    - JWT access_token from POST /auth/login
   * @param {boolean} remember - persist to localStorage
   */
  setSession(profile, token, remember) {
    const payload = {
      userId:   profile.id,          // "SS-0042"
      username: profile.username,
      email:    profile.email,
      name:     profile.name,
      isStaff:  profile.is_staff,
      token:    token,               // JWT — used by api.js for every request
      loginAt:  new Date().toISOString(),
    };
    sessionStorage.setItem(this.SESSION_KEY, JSON.stringify(payload));
    if (remember) {
      localStorage.setItem(this.REMEMBER_KEY, JSON.stringify(payload));
    } else {
      localStorage.removeItem(this.REMEMBER_KEY);
    }
    return payload;
  },

  clearSession() {
    sessionStorage.removeItem(this.SESSION_KEY);
    localStorage.removeItem(this.REMEMBER_KEY);
  },

  requireAuth(loginPath) {
    if (!this.getSession()) {
      window.location.href = loginPath;
      return false;
    }
    return true;
  },
};
