/**
 * api.js
 * Central API client for AgriPulse.
 * All fetch calls to the backend go through this module.
 *
 * Change API_BASE_URL to point at your live server when deploying.
 */

const API_BASE_URL = "http://127.0.0.1:8002/api/v1";

const AgriAPI = {
  // ─── Internal helper ──────────────────────────────────────────────────────

  /**
   * Make an authenticated request. Automatically attaches the JWT token
   * from the session and handles 401 by redirecting to login.
   */
  async _request(method, path, body = null) {
    const session = AgriAuth.getSession();
    const headers = { "Content-Type": "application/json" };
    if (session && session.token) {
      headers["Authorization"] = `Bearer ${session.token}`;
    }

    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE_URL}${path}`, options);

    // Token expired or invalid — force re-login
    if (res.status === 401) {
      AgriAuth.clearSession();
      window.location.href = "login.html";
      return null;
    }

    if (!res.ok) {
      const err = await res
        .json()
        .catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `Request failed: ${res.status}`);
    }

    // 204 No Content
    if (res.status === 204) return null;
    return res.json();
  },

  // ─── Auth ─────────────────────────────────────────────────────────────────

  /**
   * POST /auth/login
   * Returns { access_token, token_type, expires_in }
   */
  async login(identity, password) {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identity, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed." }));
      throw new Error(err.detail || "Login failed.");
    }
    return res.json(); // { access_token, token_type, expires_in }
  },

  /** POST /auth/logout (stateless — just notifies server) */
  async logout() {
    try {
      await this._request("POST", "/auth/logout");
    } catch {
      /* ignore */
    }
  },

  // ─── My Profile ───────────────────────────────────────────────────────────

  /** GET /me → ProfileResponse */
  getProfile() {
    return this._request("GET", "/me");
  },

  /** GET /me/metrics → MetricsResponse */
  getMetrics() {
    return this._request("GET", "/me/metrics");
  },

  // Tasks (Phase 1 compatibility)

  /**
   * GET /me/phase1/workplans → WorkPlanResponse[]
   * Legacy Phase-1 workplans (moved off /me/tasks during TASK_* migration).
   */
  getPhase1Workplans() {
    return this._request("GET", "/me/phase1/workplans");
  },

  /**
   * GET /me/phase1/workplans/{id} → WorkPlanResponse
   * Legacy detail.
   */
  getPhase1WorkplanById(id) {
    return this._request("GET", `/me/phase1/workplans/${id}`);
  },

  // ─── TASK_* Officer APIs ───────────────────────────────────────────────
  /** GET /me/tasks → OfficerTaskResponse[] */
  getOfficerTasks() {
    return this._request("GET", "/me/tasks");
  },

  /** GET /me/tasks/{task_master_id} → OfficerTaskDetailResponse */
  getOfficerTaskDetail(task_master_id) {
    return this._request("GET", `/me/tasks/${task_master_id}`);
  },

  /** PATCH /me/task-farmers/{task_farmer_mapping_id}/progress */
  updateTaskFarmerProgress(task_farmer_mapping_id, payload) {
    return this._request(
      "PATCH",
      `/me/task-farmers/${task_farmer_mapping_id}/progress`,
      payload,
    );
  },

  /** POST /me/task-farmers/{task_farmer_mapping_id}/evidence */
  submitTaskFarmerEvidence(task_farmer_mapping_id, payload) {
    return this._request(
      "POST",
      `/me/task-farmers/${task_farmer_mapping_id}/evidence`,
      payload,
    );
  },

  /** POST /me/task-farmers/{task_farmer_mapping_id}/complete */
  completeTaskFarmer(task_farmer_mapping_id, payload) {
    return this._request(
      "POST",
      `/me/task-farmers/${task_farmer_mapping_id}/complete`,
      payload,
    );
  },

  /** GET /me/activity → OfficerActivityResponse[] wrapper */
  getMyActivity() {
    return this._request("GET", "/me/activity");
  },

  /** GET /me/activity/{task_farmer_mapping_id} */
  getMyActivityForMapping(task_farmer_mapping_id) {
    return this._request("GET", `/me/activity/${task_farmer_mapping_id}`);
  },

  // ─── Backward compatibility: keep old method names but point to phase1 endpoints ─────────
  getTasks() {
    return this.getPhase1Workplans();
  },
  getWorkPlans() {
    return this.getPhase1Workplans();
  },

  /** GET /me/alerts → AlertResponse[] */
  getAlerts() {
    return this._request("GET", "/me/alerts");
  },

  /** GET /me/insights → InsightResponse[] */
  getInsights() {
    return this._request("GET", "/me/insights");
  },

  /** GET /me/villages → VillageStats[] */
  getVillages() {
    return this._request("GET", "/me/villages");
  },

  // ─── Submissions ──────────────────────────────────────────────────────────

  /**
   * POST /submissions
   * body: { farmer_name, mobile, purpose_code, village, city, latitude, longitude, description }
   */
  createSubmission(data) {
    return this._request("POST", "/submissions", data);
  },

  /**
   * GET /submissions?skip=0&limit=20 → SubmissionResponse[]
   */
  getSubmissions(skip = 0, limit = 20) {
    return this._request("GET", `/submissions?skip=${skip}&limit=${limit}`);
  },

  // ─── Reports (TASK_* architecture) ──────────────────────────────────────

  /**
   * POST /reports/generate
   * Body: ReportGenerateRequest (see backend/schemas.py)
   */
  generateReport(payload) {
    return this._request("POST", "/reports/generate", payload);
  },

  /**
   * GET /reports
   */
  getReports({ skip = 0, limit = 20, report_code = null, status = null } = {}) {
    const params = new URLSearchParams();
    params.set("skip", skip);
    params.set("limit", limit);
    if (report_code) params.set("report_code", report_code);
    if (status) params.set("status", status);
    return this._request("GET", `/reports?${params.toString()}`);
  },

  /**
   * GET /reports/{report_master_id}
   */
  getReport(report_master_id) {
    return this._request("GET", `/reports/${report_master_id}`);
  },

  /**
   * GET /reports/{report_master_id}/download
   */
  downloadReport(report_master_id) {
    return this._request("GET", `/reports/${report_master_id}/download`);
  },
};
