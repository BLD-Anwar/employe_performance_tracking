/**
 * AgriPulse Shared Task Editing Module (TaskEdit)
 * Handles task info loading, flexible dates (V2 creation style), locations populating, and farmer assignments.
 */
const TaskEdit = {
  onSaveSuccess: null,
  currentEditingTaskId: null,
  selectedFarmers: [],
  availableFarmers: [],

  init(onSaveSuccessCallback) {
    this.onSaveSuccess = onSaveSuccessCallback;
    this.injectModals();
  },

  injectModals() {
    if (document.getElementById("editModal")) return;

    const modalHTML = `
      <!-- Edit Task Modal -->
      <div class="modal-bg" id="editModal">
        <div style="background:#fff;border-radius:16px;width:100%;max-width:650px;max-height:90vh;box-shadow:0 20px 60px rgba(0,0,0,0.2);display:flex;flex-direction:column;overflow:hidden;">
          <div style="padding:16px 20px;background:#f9fafb;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;">
            <span style="font-size:15px;font-weight:700;color:#7c2d12;" id="editModalTitle">Edit Task Assignment</span>
            <button onclick="TaskEdit.closeEditModal()" style="background:none;border:none;cursor:pointer;color:#6b7280;">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div style="padding:20px;display:flex;flex-direction:column;gap:14px;overflow-y:auto;flex:1;" id="editModalBody">
          </div>
        </div>
      </div>

      <!-- History Modal -->
      <div class="modal-bg" id="historyModal">
        <div style="background:#fff;border-radius:16px;width:100%;max-width:550px;max-height:85vh;box-shadow:0 20px 60px rgba(0,0,0,0.2);display:flex;flex-direction:column;overflow:hidden;">
          <div style="padding:16px 20px;background:#f9fafb;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;">
            <span style="font-size:15px;font-weight:700;color:#7c2d12;">Task Audit History</span>
            <button onclick="TaskEdit.closeHistoryModal()" style="background:none;border:none;cursor:pointer;color:#6b7280;">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div style="padding:20px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:12px;" id="historyModalBody">
          </div>
        </div>
      </div>
    `;
    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = modalHTML;
    while (tempDiv.firstChild) {
      document.body.appendChild(tempDiv.firstChild);
    }
  },

  closeEditModal() {
    document.getElementById("editModal").classList.remove("show");
  },

  closeHistoryModal() {
    document.getElementById("historyModal").classList.remove("show");
  },

  toISO(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  },

  formatDateDisplay(d) {
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  },

  onEditScheduleTypeChange() {
    const schedType = document.getElementById("editScheduleType").value;
    const startInput = document.getElementById("editStartDate");
    const endInput = document.getElementById("editEndDate");
    const endWrapper = document.getElementById("editEndDateWrapper");
    const startLabel = document.getElementById("editStartDateLabel");
    const hint = document.getElementById("editDateAutoHint");

    // Reset
    startInput.type = "date";
    endInput.readOnly = false;
    hint.style.display = "none";
    hint.textContent = "";

    // Ensure start date has a value
    if (!startInput.value) {
      const today = new Date();
      startInput.value = this.toISO(today);
    }

    if (schedType === "DAILY") {
      startLabel.innerHTML = 'Task Date <span style="color:#dc2626;">*</span>';
      endWrapper.style.display = "block";
      hint.style.display = "flex";
      this.onEditDateChange(true);
    } else if (schedType === "WEEKLY") {
      startLabel.innerHTML = 'Start Date <span style="color:#dc2626;">*</span>';
      endWrapper.style.display = "block";
      hint.style.display = "flex";
      this.onEditDateChange(true);
    } else if (schedType === "MONTHLY") {
      startLabel.innerHTML = 'Start Date <span style="color:#dc2626;">*</span>';
      endWrapper.style.display = "block";
      hint.style.display = "flex";
      this.onEditDateChange(true);
    }
  },

  onEditDateChange(isStartChange = false) {
    const schedType = document.getElementById("editScheduleType").value;
    const startInput = document.getElementById("editStartDate");
    const endInput = document.getElementById("editEndDate");
    const hint = document.getElementById("editDateAutoHint");

    if (!startInput.value) return;

    if (schedType === "DAILY") {
      if (isStartChange) {
        endInput.value = startInput.value;
      } else if (endInput.value) {
        startInput.value = endInput.value;
      }
      const d = new Date(startInput.value);
      hint.style.display = "flex";
      hint.innerHTML = `<span class="material-symbols-outlined" style="font-size:14px;">today</span> ${this.formatDateDisplay(d)} — single day task.`;
    } else if (schedType === "WEEKLY") {
      const start = new Date(startInput.value);
      if (isStartChange || !endInput.value) {
        const end = new Date(start);
        end.setDate(start.getDate() + 7);
        endInput.value = this.toISO(end);
      }
      const end = new Date(endInput.value);
      const diffDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
      hint.style.display = "flex";
      hint.innerHTML = `<span class="material-symbols-outlined" style="font-size:14px;">date_range</span> ${this.formatDateDisplay(start)} → ${this.formatDateDisplay(end)} (${diffDays} days)`;
    } else if (schedType === "MONTHLY") {
      const start = new Date(startInput.value);
      if (isStartChange || !endInput.value) {
        const end = new Date(start);
        end.setMonth(start.getMonth() + 1);
        endInput.value = this.toISO(end);
      }
      const end = new Date(endInput.value);
      hint.style.display = "flex";
      hint.innerHTML = `<span class="material-symbols-outlined" style="font-size:14px;">calendar_month</span> ${this.formatDateDisplay(start)} → ${this.formatDateDisplay(end)}`;
    }
  },

  async populateLocations(selectedTaluka = "", selectedVillage = "", selectedSubVillage = "") {
    try {
      const tRes = await AgriAuth.apiFetch("/api/tasks/talukas");
      const talukas = await tRes.json();
      const tSelect = document.getElementById("editDistrict");
      tSelect.innerHTML = '<option value="">Select Taluka</option>';
      talukas.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        if (t === selectedTaluka) opt.selected = true;
        tSelect.appendChild(opt);
      });

      const triggerChange = async () => {
        const tVal = tSelect.value;
        const vSelect = document.getElementById("editVillage");
        vSelect.innerHTML = '<option value="">Select Village</option>';
        document.getElementById("editSubVillage").innerHTML = '<option value="">Select Sub Village</option>';
        if (tVal) {
          const vRes = await AgriAuth.apiFetch(`/api/tasks/villages?taluka=${encodeURIComponent(tVal)}`);
          const villages = await vRes.json();
          villages.forEach(v => {
            const opt = document.createElement("option");
            opt.value = v;
            opt.textContent = v;
            if (v === selectedVillage) opt.selected = true;
            vSelect.appendChild(opt);
          });
          if (selectedVillage) {
            await triggerVillageChange();
          }
        }
      };

      const triggerVillageChange = async () => {
        const vVal = document.getElementById("editVillage").value;
        const sSelect = document.getElementById("editSubVillage");
        sSelect.innerHTML = '<option value="">Select Sub Village</option>';
        if (vVal) {
          const sRes = await AgriAuth.apiFetch(`/api/tasks/sub-villages?village=${encodeURIComponent(vVal)}`);
          const subs = await sRes.json();
          subs.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s;
            opt.textContent = s;
            if (s === selectedSubVillage) opt.selected = true;
            sSelect.appendChild(opt);
          });
          this.loadAvailableFarmers(vVal, sSelect.value);
        } else {
          document.getElementById("availableFarmersList").innerHTML = '<div style="font-size:12px;color:#9ca3af;text-align:center;">Choose a village to load available farmers</div>';
        }
      };

      tSelect.onchange = () => { selectedVillage = ""; selectedSubVillage = ""; triggerChange(); };
      document.getElementById("editVillage").onchange = () => { selectedSubVillage = ""; triggerVillageChange(); };
      document.getElementById("editSubVillage").onchange = () => {
        const vVal = document.getElementById("editVillage").value;
        const svVal = document.getElementById("editSubVillage").value;
        this.loadAvailableFarmers(vVal, svVal);
      };

      await triggerChange();
    } catch (err) {
      console.error("populateLocations error:", err);
    }
  },

  async editTask(taskId) {
    this.currentEditingTaskId = taskId;

    document.getElementById("editModal").classList.add("show");
    document.getElementById("editModalBody").innerHTML = '<div style="padding:20px;text-align:center;color:#6b7280;">Loading task details...</div>';

    try {
      const [res, wtRes] = await Promise.all([
        AgriAuth.apiFetch(`/api/tasks/${taskId}`),
        AgriAuth.apiFetch("/api/tasks/work-types"),
      ]);
      if (!res.ok) throw new Error("Failed to load task");
      const task = await res.json();
      const workTypes = wtRes.ok ? await wtRes.json() : [];
      const workTypeOptions = workTypes.map(wt => {
        const sel = wt.name === task.work_type ? "selected" : "";
        return `<option value="${wt.name}" ${sel}>${wt.name}</option>`;
      }).join("");
      const legacyOption = task.work_type && !workTypes.some(w => w.name === task.work_type)
        ? `<option value="${task.work_type}" selected>${task.work_type} (update required)</option>` : "";

      this.selectedFarmers = task.farmers.map(f => ({
        id: f.id,
        name: f.name,
        village: f.village,
        taluka: f.taluka,
        mobile: f.mobile
      }));

      document.getElementById("editModalBody").innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div>
            <label class="form-label" style="font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">Task Name</label>
            <input type="text" id="editTaskName" value="${task.task_name}" style="width:100%;box-sizing:border-box;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;">
          </div>
          <div>
            <label class="form-label" style="font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">Work Type</label>
            <select id="editWorkType" style="width:100%;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;">
              <option value="">Select work type...</option>
              ${legacyOption}${workTypeOptions}
            </select>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr;gap:12px;margin-top:4px;">
          <div>
            <label class="form-label" style="font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">Schedule Type</label>
            <select id="editScheduleType" onchange="TaskEdit.onEditScheduleTypeChange()" style="width:100%;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;">
              <option value="DAILY" ${task.schedule_type === 'DAILY' ? 'selected' : ''}>Daily</option>
              <option value="WEEKLY" ${task.schedule_type === 'WEEKLY' ? 'selected' : ''}>Weekly</option>
              <option value="MONTHLY" ${task.schedule_type === 'MONTHLY' ? 'selected' : ''}>Monthly</option>
            </select>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:4px;">
          <div>
            <label class="form-label" id="editStartDateLabel" style="font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">Start Date</label>
            <input type="date" id="editStartDate" onchange="TaskEdit.onEditDateChange(true)" style="width:100%;box-sizing:border-box;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;">
          </div>
          <div id="editEndDateWrapper">
            <label class="form-label" style="font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">End Date</label>
            <input type="date" id="editEndDate" onchange="TaskEdit.onEditDateChange(false)" style="width:100%;box-sizing:border-box;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;">
          </div>
        </div>
        <div id="editDateAutoHint" style="font-size:11px;color:#7c2d12;background:#ffedd5;border:1px solid #fed7aa;padding:6px 10px;border-radius:8px;margin-top:4px;display:none;align-items:center;gap:6px;font-weight:600;"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:4px;">
          <div>
            <label class="form-label" style="font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">Status</label>
            <select id="editStatus" style="width:100%;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;">
              <option value="ASSIGNED" ${task.status === 'ASSIGNED' ? 'selected' : ''}>ASSIGNED</option>
              <option value="PENDING" ${task.status === 'PENDING' ? 'selected' : ''}>PENDING</option>
              <option value="IN_PROGRESS" ${task.status === 'IN_PROGRESS' ? 'selected' : ''}>IN_PROGRESS</option>
              <option value="COMPLETED" ${task.status === 'COMPLETED' ? 'selected' : ''}>COMPLETED</option>
              <option value="CANCELLED" ${task.status === 'CANCELLED' ? 'selected' : ''}>CANCELLED</option>
            </select>
          </div>
          <div>
            <label class="form-label" style="font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">Remarks</label>
            <input type="text" id="editRemarks" value="${task.remarks || ''}" style="width:100%;box-sizing:border-box;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;">
          </div>
        </div>
        
        <div style="border-top:1px solid #e5e7eb;padding-top:10px;margin-top:4px;">
          <span style="font-size:12px;font-weight:700;color:#7c2d12;display:block;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.05em;">Task Location</span>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
            <select id="editDistrict" style="width:100%;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;"></select>
            <select id="editVillage" style="width:100%;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;"></select>
            <select id="editSubVillage" style="width:100%;border:1.5px solid #d1d5db;border-radius:8px;padding:8px 10px;"></select>
          </div>
        </div>

        <div style="border-top:1px solid #e5e7eb;padding-top:10px;margin-top:4px;display:grid;grid-template-columns:1fr 1fr;gap:16px;">
          <div>
            <span style="font-size:11px;font-weight:700;color:#7c2d12;display:block;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.05em;">Currently Mapped Farmers</span>
            <div id="selectedFarmersList" style="border:1px solid #e5e7eb;border-radius:8px;padding:8px;max-height:160px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;min-height:100px;background:#f9fafb;">
            </div>
          </div>
          <div>
            <span style="font-size:11px;font-weight:700;color:#7c2d12;display:block;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.05em;">Search & Add Farmers</span>
            <input type="text" id="farmerSearchInput" placeholder="Search farmer name or ID..." style="width:100%;box-sizing:border-box;margin-bottom:6px;padding:6px 10px;font-size:12px;border:1.5px solid #d1d5db;border-radius:8px;" oninput="TaskEdit.filterAvailableFarmers()">
            <div id="availableFarmersList" style="border:1px solid #e5e7eb;border-radius:8px;padding:8px;max-height:160px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;min-height:100px;background:#f9fafb;">
              <div style="font-size:12px;color:#9ca3af;text-align:center;padding:12px;">Choose a village to load available farmers</div>
            </div>
          </div>
        </div>

        <div style="border-top:1px solid #e5e7eb;padding-top:12px;margin-top:6px;display:flex;gap:10px;justify-content:flex-end;">
          <button onclick="TaskEdit.closeEditModal()" style="background:#f3f4f6;border:1px solid #d1d5db;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;color:#374151;cursor:pointer;">Cancel</button>
          <button id="saveEditBtn" onclick="TaskEdit.saveTaskChanges()" style="background:#7c2d12;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:6px;">
            <span class="material-symbols-outlined" style="font-size:18px;">save</span>Save Changes
          </button>
        </div>
      `;

      // Set input values & trigger date initialization
      document.getElementById("editStartDate").value = task.start_date || "";
      document.getElementById("editEndDate").value = task.end_date || "";
      this.onEditScheduleTypeChange();

      this.renderSelectedFarmers();
      await this.populateLocations(task.location.district, task.location.village, task.location.sub_village);
    } catch (err) {
      document.getElementById("editModalBody").innerHTML = `<div style="padding:20px;text-align:center;color:#dc2626;">${err.message}</div>`;
    }
  },

  renderSelectedFarmers() {
    const container = document.getElementById("selectedFarmersList");
    if (!container) return;
    if (this.selectedFarmers.length === 0) {
      container.innerHTML = '<div style="font-size:12px;color:#9ca3af;text-align:center;padding:12px;">No farmers assigned to this task.</div>';
      return;
    }
    container.innerHTML = this.selectedFarmers.map(f => `
      <div style="display:flex;align-items:center;justify-content:space-between;background:#fff;padding:6px 10px;border-radius:8px;border:1px solid #e5e7eb;">
        <div>
          <div style="font-size:12px;font-weight:700;color:#111827;">${f.name}</div>
          <div style="font-size:10px;color:#6b7280;">ID ${f.id} · ${f.village}</div>
        </div>
        <button onclick="TaskEdit.removeFarmerFromTask(${f.id})" style="background:none;border:none;color:#dc2626;cursor:pointer;display:flex;align-items:center;padding:2px;">
          <span class="material-symbols-outlined" style="font-size:18px;">delete</span>
        </button>
      </div>
    `).join("");
  },

  async loadAvailableFarmers(village, subVillage = "") {
    const list = document.getElementById("availableFarmersList");
    if (!list) return;
    list.innerHTML = '<div style="font-size:12px;color:#6b7280;text-align:center;padding:12px;">Loading eligible farmers...</div>';
    try {
      let url = `/api/tasks/farmers?village=${encodeURIComponent(village)}&exclude_task_id=${this.currentEditingTaskId}`;
      if (subVillage) {
        url += `&sub_village=${encodeURIComponent(subVillage)}`;
      }
      const res = await AgriAuth.apiFetch(url);
      if (!res.ok) throw new Error("Failed");
      this.availableFarmers = await res.json();
      this.renderAvailableFarmers();
    } catch (err) {
      list.innerHTML = '<div style="font-size:12px;color:#dc2626;text-align:center;padding:12px;">Failed to load farmers</div>';
    }
  },

  renderAvailableFarmers() {
    const container = document.getElementById("availableFarmersList");
    if (!container) return;
    const query = document.getElementById("farmerSearchInput")?.value.toLowerCase() || "";
    const selectedIds = new Set(this.selectedFarmers.map(f => f.id));
    const filtered = this.availableFarmers.filter(f => {
      const matchQuery = !query || f.name.toLowerCase().includes(query) || String(f.id).includes(query);
      const notSelected = !selectedIds.has(f.id);
      return matchQuery && notSelected;
    });

    if (filtered.length === 0) {
      container.innerHTML = '<div style="font-size:12px;color:#9ca3af;text-align:center;padding:12px;">No available farmers found.</div>';
      return;
    }

    container.innerHTML = filtered.map(f => `
      <div style="display:flex;align-items:center;justify-content:space-between;background:#fff;padding:6px 10px;border-radius:8px;border:1px solid #e5e7eb;">
        <div>
          <div style="font-size:12px;font-weight:700;color:#111827;">${f.name}</div>
          <div style="font-size:10px;color:#6b7280;">ID ${f.id} · ${f.mobile || 'No Mobile'}</div>
        </div>
        <button onclick="TaskEdit.addFarmerToTask(${f.id})" style="background:#7c2d12;border:none;border-radius:6px;color:#fff;cursor:pointer;padding:4px 8px;font-size:11px;font-weight:700;display:flex;align-items:center;gap:2px;">
          <span class="material-symbols-outlined" style="font-size:13px;">add</span>Add
        </button>
      </div>
    `).join("");
  },

  filterAvailableFarmers() {
    this.renderAvailableFarmers();
  },

  addFarmerToTask(farmerId) {
    const f = this.availableFarmers.find(x => x.id === farmerId);
    if (f && !this.selectedFarmers.some(x => x.id === farmerId)) {
      this.selectedFarmers.push(f);
      this.renderSelectedFarmers();
      this.renderAvailableFarmers();
    }
  },

  removeFarmerFromTask(farmerId) {
    this.selectedFarmers = this.selectedFarmers.filter(x => x.id !== farmerId);
    this.renderSelectedFarmers();
    this.renderAvailableFarmers();
  },

  async saveTaskChanges() {
    const btn = document.getElementById("saveEditBtn");
    btn.disabled = true;
    btn.textContent = "Saving...";

    const session = AgriAuth.getSession();
    const managerId = session ? session.id : 1;

    const schedType = document.getElementById("editScheduleType").value;
    const startDateVal = document.getElementById("editStartDate").value;
    const endDateVal = document.getElementById("editEndDate").value;

    const payload = {
      task_name: document.getElementById("editTaskName").value,
      work_type_name: document.getElementById("editWorkType").value,
      priority: "Medium",
      start_date: startDateVal,
      end_date: endDateVal,
      status: document.getElementById("editStatus").value,
      remarks: document.getElementById("editRemarks").value,
      district: document.getElementById("editDistrict").value,
      village: document.getElementById("editVillage").value,
      sub_village: document.getElementById("editSubVillage").value,
      farmers: this.selectedFarmers.map(f => f.id),
      manager_id: managerId,
      schedule_type: schedType
    };

    if (!payload.task_name || !payload.work_type_name || !payload.start_date || !payload.end_date || !payload.district || !payload.village) {
      alert("Please fill in all required fields (Task Name, Work Type, Dates, and Location).");
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined" style="font-size:18px;">save</span>Save Changes';
      return;
    }

    try {
      const res = await AgriAuth.apiFetch(`/api/tasks/${this.currentEditingTaskId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save changes");
      }
      this.closeEditModal();
      if (this.onSaveSuccess) {
        await this.onSaveSuccess(this.currentEditingTaskId);
      }
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span class="material-symbols-outlined" style="font-size:18px;">save</span>Save Changes';
    }
  },

  async viewTaskHistory(taskId) {
    document.getElementById("historyModal").classList.add("show");
    const body = document.getElementById("historyModalBody");
    body.innerHTML = '<div style="padding:20px;text-align:center;color:#6b7280;">Loading audit history...</div>';

    try {
      const res = await AgriAuth.apiFetch(`/api/tasks/${taskId}/history`);
      if (!res.ok) throw new Error("Failed to load history");
      const history = await res.json();

      if (history.length === 0) {
        body.innerHTML = '<div style="padding:20px;text-align:center;color:#9ca3af;font-size:13px;">No history logs found for this task.</div>';
        return;
      }

      body.innerHTML = `
        <div style="border-left:2px solid #e5e7eb;margin-left:10px;padding-left:16px;display:flex;flex-direction:column;gap:16px;padding-top:4px;padding-bottom:4px;">
          ${history.map(h => {
            let dotColor = '#7c2d12';
            if (h.action === 'TASK_STATUS_CHANGED') dotColor = '#3b82f6';
            else if (h.action === 'TASK_FARMER_REMOVED') dotColor = '#dc2626';
            else if (h.action === 'TASK_FARMER_ADDED') dotColor = '#ea580c';

            return `
            <div style="position:relative;">
              <div style="position:absolute;left:-22px;top:4px;width:10px;height:10px;border-radius:99px;background:${dotColor};"></div>
              <div style="font-size:11px;font-weight:700;color:#9ca3af;">${h.timestamp} · by ${h.officer_name}</div>
              <div style="font-size:13px;font-weight:700;color:#111827;margin-top:2px;">${h.action}</div>
              <div style="font-size:12px;color:#6b7280;margin-top:1px;">${h.remarks}</div>
            </div>`;
          }).join("")}
        </div>
      `;
    } catch (err) {
      body.innerHTML = `<div style="padding:20px;text-align:center;color:#dc2626;">${err.message}</div>`;
    }
  }
};
