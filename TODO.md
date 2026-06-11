# TODO

- [ ] Backend: backend/routers/employee.py
  - [ ] Remove GET /employee/debug/row-columns
  - [ ] Remove GET /employee/debug/row-data
  - [ ] In update_progress() error response, remove SQL/params/id_col diagnostics and return HTTPException(500, detail=str(e))

- [ ] Frontend: frontend/manager/manager_tasks.html
  - [ ] Fix API paths: remove `/api` prefix for work-types and tasks list
  - [ ] Remove calls to nonexistent endpoints (/api/tasks/officers, /api/tasks/talukas, /api/tasks/villages, /api/tasks/sub-villages, /api/tasks/farmers, /api/tasks/assign, /api/tasks/{id}/rows)
  - [ ] Hide/replace officer cards + location/farmer sections with simple emp_code input and placeholders
  - [ ] Fix history rendering to use GET /tasks/list response shape

- [ ] Frontend: frontend/employee/work_submission.html
  - [ ] Rewrite only the script logic to:
    - [ ] Read emp_code from localStorage/session
    - [ ] Render emp_code input override
    - [ ] GET /employee/tasks/{emp_code} and build task selector + right panel cards
    - [ ] POST /employee/update-progress with payload {row_id, progress, status}

- [ ] Verification steps
  - [ ] GET /tasks/work-types -> dropdown populates
  - [ ] POST /tasks/create -> {created:true,...}
  - [ ] GET /tasks/list -> task history renders
  - [ ] GET /employee/tasks/{emp_code} -> rows populate
  - [ ] POST /employee/update-progress -> {updated:true, affected:1}

