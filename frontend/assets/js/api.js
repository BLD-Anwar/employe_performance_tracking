/**
 * api.js  –  Unified API client for AgriPulse
 * All fetch calls to the backend go through this module.
 * Uses relative URLs when served from the same origin (port 8000).
 */

const AgriAPI = {
  /** Base URL — relative when served from FastAPI, absolute for file:// */
  _baseUrl() {
    return AgriAuth.apiOrigin() + "/api";
  },

  /**
   * Make a request. Handles JSON parsing and 401 redirects.
   */
  async _request(method, path, body = null) {
    const session = AgriAuth.getSession();
    const headers = { "Content-Type": "application/json" };

    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const url = `${this._baseUrl()}${path}`;
    const res = await fetch(url, options);

    if (res.status === 401) {
      AgriAuth.clearSession();
      window.location.href = "/login.html";
      return null;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `Request failed: ${res.status}`);
    }

    if (res.status === 204) return null;
    return res.json();
  },

  // ── Auth ─────────────────────────────────────────────────────────────────
  async login(username, password) {
    const res = await fetch(`${this._baseUrl()}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed." }));
      throw new Error(err.detail || "Login failed.");
    }
    return res.json(); // SessionUser { id, username, name, role }
  },

  async logout() {
    try { await this._request("POST", "/auth/logout"); } catch {}
  },

  // ── Manager Dashboard ────────────────────────────────────────────────────
  getDashboardStats()        { return this._request("GET", "/dashboard/stats"); },
  getDashboardWeekly()       { return this._request("GET", "/dashboard/weekly"); },
  getDashboardWorkTypes()    { return this._request("GET", "/dashboard/work-types"); },
  getDashboardTopOfficers()  { return this._request("GET", "/dashboard/top-officers"); },
  getDashboardRecent()       { return this._request("GET", "/dashboard/recent-activities"); },

  // ── Manager Officers ─────────────────────────────────────────────────────
  getOfficers(search, role)  { 
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (role) params.set("role", role);
    return this._request("GET", `/officers?${params}`); 
  },
  getOfficer(id)             { return this._request("GET", `/officers/${id}`); },
  getOfficerDashboard(id)    { return this._request("GET", `/officers/${id}/dashboard`); },
  blockOfficer(id, block)    { return this._request("PUT", `/officers/${id}/block`, { is_blocked: block }); },

  // ── Manager Tasks ────────────────────────────────────────────────────────
  getTasks(officerId)        { 
    const q = officerId ? `?officer_id=${officerId}` : "";
    return this._request("GET", `/tasks${q}`); 
  },
  getTask(id)                { return this._request("GET", `/tasks/${id}`); },
  getTaskRows(id)            { return this._request("GET", `/tasks/${id}/rows`); },
  getTaskHistory(id)         { return this._request("GET", `/tasks/${id}/history`); },
  assignTask(data)           { return this._request("POST", "/tasks/assign", data); },
  updateTask(id, data)       { return this._request("PUT", `/tasks/${id}`, data); },
  getAssignableOfficers()    { return this._request("GET", "/tasks/officers"); },
  getWorkTypes()             { return this._request("GET", "/tasks/work-types"); },
  getFarmers(params)         {
    const q = new URLSearchParams(params);
    return this._request("GET", `/tasks/farmers?${q}`);
  },
  getTalukas()               { return this._request("GET", "/tasks/talukas"); },
  getVillages(taluka)        { return this._request("GET", `/tasks/villages?taluka=${taluka || ""}`); },
  getSubVillages(village)    { return this._request("GET", `/tasks/sub-villages?village=${village || ""}`); },

  // ── Manager Performance ──────────────────────────────────────────────────
  getPerformanceRanking()       { return this._request("GET", "/performance/ranking"); },
  getPerformanceWorkTypes()     { return this._request("GET", "/performance/work-types"); },
  getPerformanceTopVillages()   { return this._request("GET", "/performance/top-villages"); },
  getPerformanceWeekly()        { return this._request("GET", "/performance/weekly"); },
  getOfficerPerformance(id)     { return this._request("GET", `/performance/officer/${id}`); },

  // ── Manager Reports ──────────────────────────────────────────────────────
  getActivityLog(params)     {
    const q = new URLSearchParams(params);
    return this._request("GET", `/reports/activities?${q}`);
  },
  downloadActivityLog(params) {
    const q = new URLSearchParams(params);
    window.open(`${this._baseUrl()}/reports/activities/download?${q}`, "_blank");
  },
  getReportSummary()         { return this._request("GET", "/reports/summary"); },
  getReportArchive()         { return this._request("GET", "/reports/archive"); },
  getReportCount()           { return this._request("GET", "/reports/archive/count"); },
  getTaskStats()             { return this._request("GET", "/reports/task-stats"); },
  generateTaskReport(taskId, managerId) {
    return this._request("POST", `/reports/generate-task-report?task_id=${taskId}&manager_id=${managerId || 1}`);
  },
  generateAllReports(managerId) {
    return this._request("POST", `/reports/generate-all?manager_id=${managerId || 1}`);
  },
  getOfficersForFilter()     { return this._request("GET", "/reports/officers-for-filter"); },
  getWorkTypesForFilter()    { return this._request("GET", "/reports/work-types-for-filter"); },
  getReports(params)         { return this.getReportArchive(); },
  generateReport(payload)    { return this.generateAllReports(); },

  // ── Report System (New) ────────────────────────────────────────────────
  getMyReports() {
    const s = AgriAuth.getSession();
    return this._request("GET", `/reports/my-reports/${s.userId}`);
  },
  getOfficerRanking()        { return this._request("GET", "/reports/officer-ranking"); },
  downloadReportCSV(reportId) {
    window.open(`${this._baseUrl()}/reports/download-file?report_id=${reportId}`, "_blank");
  },
  getFarmerMeetings(taskId) {
    return this._request("GET", `/reports/farmer-meetings/${taskId}`);
  },

  // ── Officer Meeting KPIs ────────────────────────────────────────────────
  getOfficerMeetingKpis(officerId) {
    return this._request("GET", `/officers/${officerId}/meeting-kpis`);
  },

  // ── Manager Settings ─────────────────────────────────────────────────────
  getProfile(userId)         { return this._request("GET", `/settings/profile/${userId}`); },
  updateProfile(userId, d)   { return this._request("PUT", `/settings/profile/${userId}`, d); },
  changePassword(userId, d)  { return this._request("POST", `/settings/change-password/${userId}`, d); },

  // ── Employee (Officer self-service) ──────────────────────────────────────
  getMyProfile() { 
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/profile/${s.userId}`); 
  },
  getMetrics() { 
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/metrics/${s.userId}`); 
  },
  getOfficerTasks() { 
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/tasks/${s.userId}`); 
  },
  getMyTaskDetail(taskId) { 
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/tasks/${s.userId}/${taskId}`); 
  },
  updateTaskFarmerProgress(mappingId, payload) {
    const s = AgriAuth.getSession();
    return this._request("PATCH", `/me/task-farmers/${mappingId}/progress?user_id=${s.userId}`, payload);
  },
  submitTaskFarmerEvidence(mappingId, payload) {
    const s = AgriAuth.getSession();
    return this._request("POST", `/me/task-farmers/${mappingId}/evidence?user_id=${s.userId}`, payload);
  },
  completeTaskFarmer(mappingId, payload) {
    const s = AgriAuth.getSession();
    return this._request("POST", `/me/task-farmers/${mappingId}/complete?user_id=${s.userId}`, payload);
  },
  getMyActivity() { 
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/activity/${s.userId}`); 
  },
  getAlerts() { 
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/alerts/${s.userId}`); 
  },
  getInsights() { 
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/insights/${s.userId}`); 
  },
  getVillages() { 
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/villages/${s.userId}`); 
  },
  createSubmission(data) {
    const s = AgriAuth.getSession();
    return this._request("POST", `/me/submissions?user_id=${s.userId}`, data);
  },
  getSubmissions(skip, limit) {
    const s = AgriAuth.getSession();
    return this._request("GET", `/me/submissions/${s.userId}?skip=${skip || 0}&limit=${limit || 20}`);
  },

  // ── Farmer Meetings ────────────────────────────────────────────────────
  submitFarmerMeeting(data) {
    return this._request("POST", "/meetings", data);
  },
  getMyMeetings(skip, limit) {
    const s = AgriAuth.getSession();
    return this._request("GET", `/meetings/my/${s.userId}?skip=${skip || 0}&limit=${limit || 50}`);
  },
  getMeetingDetail(meetingId) {
    return this._request("GET", `/meetings/${meetingId}`);
  },
  checkExistingMeeting(farmerCode) {
    const s = AgriAuth.getSession();
    return this._request("GET", `/meetings/check/${s.userId}/${farmerCode}`);
  },
  getAllMeetings(params) {
    const q = new URLSearchParams(params || {});
    return this._request("GET", `/meetings?${q}`);
  },
  async uploadMeetingPhoto(file) {
    const s = AgriAuth.getSession();
    const fd = new FormData();
    fd.append("file", file);
    const url = `${this._baseUrl()}/meetings/upload-photo?user_id=${s.userId}`;
    const res = await fetch(url, { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },
};
