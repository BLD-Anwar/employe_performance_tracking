"""
routers/employee.py  –  Employee (Officer) self-service endpoints
Provides task-aware work submission and activity tracking for logged-in officers.

Tables: TASK_MASTER, TASK_FARMER_MAPPING, TASK_ACTIVITY_LOG, TASK_LOCATION,
        dbo.activities, dbo.auth_user, dbo.user_details
"""
from fastapi import APIRouter, HTTPException, Query
from database import db_cursor
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/me", tags=["employee"])


# ── Models ──────────────────────────────────────────────────────────────────
class ProgressUpdate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: str = ""

class EvidenceSubmission(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: str = ""
    farmer_name: Optional[str] = None
    mobile: Optional[str] = None

class CompleteSubmission(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: str = ""

class WorkSubmission(BaseModel):
    """Submit a telemetry / activity log (legacy dbo.activities insert)."""
    farmer_name: str = ""
    mobile: str = ""
    purpose_code: Optional[int] = None
    village: str = ""
    city: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: str = ""


# ── Profile ─────────────────────────────────────────────────────────────────
@router.get("/profile/{user_id}")
def get_my_profile(user_id: int):
    """Get own profile for the officer dashboard header."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                u.id,
                u.username,
                ISNULL(u.first_name,'') AS first_name,
                ISNULL(u.last_name,'')  AS last_name,
                u.email,
                u.is_staff,
                CONVERT(VARCHAR, u.date_joined, 106) AS joined,
                ISNULL(ud.role, 'OFFICER') AS detail_role,
                ISNULL(ud.is_blocked, 0) AS is_blocked,
                ISNULL(ud.is_login, 1)   AS is_login
            FROM dbo.auth_user u
            LEFT JOIN dbo.user_details ud ON ud.user_id = u.id
            WHERE u.id = ?
        """, user_id)
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    uid, username, first_name, last_name, email, is_staff, joined, \
        detail_role, is_blocked, is_login = row

    full_name = f"{first_name} {last_name}".strip() or username
    initials = ""
    if first_name and last_name:
        initials = (first_name[0] + last_name[0]).upper()
    elif full_name:
        parts = full_name.split()
        initials = "".join(p[0] for p in parts[:2]).upper()

    # Determine role label
    role_label = detail_role.upper() if detail_role else "OFFICER"
    if role_label == "MANAGER":
        department = "Management & Supervision"
    elif role_label == "ADMIN":
        department = "Administration"
    else:
        department = "Cane Operations — Field Division"

    # Determine status
    if is_blocked:
        status = "Blocked"
    elif not is_login:
        status = "Inactive"
    else:
        status = "Active"

    # Compute villages_count and farmer_count from real task data
    with db_cursor() as cur:
        cur.execute("""
            SELECT COUNT(DISTINCT CAST(tl.village_code AS VARCHAR(50)))
            FROM TASK_MASTER tm
            JOIN TASK_LOCATION tl ON tl.task_id = tm.task_id
            WHERE tm.assigned_officer = ? AND tl.village_code IS NOT NULL
        """, user_id)
        villages_count = cur.fetchone()[0] or 0

        cur.execute("""
            SELECT COUNT(DISTINCT tfm.farmer_id)
            FROM TASK_FARMER_MAPPING tfm
            JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
            WHERE tm.assigned_officer = ?
        """, user_id)
        farmer_count = cur.fetchone()[0] or 0

        # Derive region from assigned talukas
        cur.execute("""
            SELECT TOP 3 ISNULL(t.Taluka_NameE, '')
            FROM TASK_FARMER_MAPPING tfm
            JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
            JOIN dbo.TBL_MST_MASTER f ON f.code = tfm.farmer_id
            JOIN dbo.TBl_mst_taluka t ON t.Taluka_Code = f.Talula_Code
            WHERE tm.assigned_officer = ? AND t.Taluka_NameE IS NOT NULL
            GROUP BY t.Taluka_NameE
            ORDER BY COUNT(*) DESC
        """, user_id)
        talukas = [r[0] for r in cur.fetchall() if r[0]]
        region = ", ".join(talukas) if talukas else "Not Assigned"

    return {
        "id": uid,
        "username": username,
        "name": full_name,
        "email": email,
        "is_staff": bool(is_staff),
        "role": role_label.title(),
        "joined": joined,
        "initials": initials,
        "department": department,
        "region": region,
        "status": status,
        "villages_count": villages_count,
        "farmer_count": farmer_count,
    }


# ── Metrics ─────────────────────────────────────────────────────────────────
@router.get("/metrics/{user_id}")
def get_my_metrics(user_id: int):
    """Dashboard summary metrics for the officer — includes real KPI percentages."""
    with db_cursor() as cur:
        # Task stats
        cur.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'IN_PROGRESS' AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status IN ('ASSIGNED','PENDING') AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) as overdue
            FROM TASK_MASTER
            WHERE assigned_officer = ?
        """, user_id)
        ts = cur.fetchone()

        # Activity count
        cur.execute("""
            SELECT COUNT(*) FROM TbL_TRN_Farmer_Meeting WHERE employee_id = ?
        """, user_id)
        act_count = cur.fetchone()[0] or 0

        # Farmer count (assigned)
        cur.execute("""
            SELECT COUNT(DISTINCT tfm.farmer_id)
            FROM TASK_FARMER_MAPPING tfm
            JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
            WHERE tm.assigned_officer = ?
        """, user_id)
        farmer_count = cur.fetchone()[0] or 0

        # Village count
        cur.execute("""
            SELECT COUNT(DISTINCT CAST(tl.village_code AS VARCHAR(50)))
            FROM TASK_MASTER tm
            JOIN TASK_LOCATION tl ON tl.task_id = tm.task_id
            WHERE tm.assigned_officer = ? AND tl.village_code IS NOT NULL
        """, user_id)
        village_count = cur.fetchone()[0] or 0

        # ── KPI percentages from TbL_TRN_Farmer_Meeting ──
        cur.execute("""
            SELECT
                COUNT(*)                                             AS total_meetings,
                SUM(CASE WHEN kcc = 1 THEN 1 ELSE 0 END)            AS kcc_yes,
                SUM(CASE WHEN canara_hnt = 1 THEN 1 ELSE 0 END)     AS canara_yes,
                SUM(CASE WHEN sangola_hnt = 1 THEN 1 ELSE 0 END)    AS sangola_yes,
                SUM(CASE WHEN cane_registration = 1 THEN 1 ELSE 0 END) AS cane_reg_yes,
                SUM(CASE WHEN recovery = 1 THEN 1 ELSE 0 END)       AS recovery_yes,
                SUM(CASE WHEN vehicle_agreement = 1 THEN 1 ELSE 0 END) AS vehicle_yes
            FROM TbL_TRN_Farmer_Meeting
            WHERE employee_id = ?
        """, user_id)
        mk = cur.fetchone()

    total = ts[0] or 0
    completed = ts[1] or 0

    # Meeting KPIs (percentage of positive responses out of total meetings)
    total_meetings = mk[0] or 0
    if total_meetings > 0:
        kcc_target      = round((mk[1] or 0) / total_meetings * 100)
        canara_ht_loan  = round((mk[2] or 0) / total_meetings * 100)
        sangola_ht_loan = round((mk[3] or 0) / total_meetings * 100)
        cane_reg_target = round((mk[4] or 0) / total_meetings * 100)
        recovery_target = round((mk[5] or 0) / total_meetings * 100)
        ht_agreement    = round((mk[6] or 0) / total_meetings * 100)
    else:
        kcc_target = canara_ht_loan = sangola_ht_loan = 0
        cane_reg_target = recovery_target = ht_agreement = 0

    # Farmer meetings coverage: how many of assigned farmers have at least one meeting
    farmer_meetings = round(total_meetings / farmer_count * 100) if farmer_count > 0 else 0
    farmer_meetings = min(farmer_meetings, 100)  # cap at 100%

    # Crushing target = proxy from cane registration compliance
    crushing_target = cane_reg_target

    # Weighted score: 40% Crushing + 20% Recovery + 20% Meetings + 20% KCC
    calculated_score = round(
        crushing_target * 0.4 +
        recovery_target * 0.2 +
        farmer_meetings * 0.2 +
        kcc_target * 0.2
    )

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "in_progress_tasks": ts[2] or 0,
        "pending_tasks": ts[3] or 0,
        "overdue_tasks": ts[4] or 0,
        "activities_count": act_count,
        "farmers_assigned": farmer_count,
        "villages_count": village_count,
        "completion_score": round(completed / total * 100) if total else 0,
        # KPI percentages for the dashboard
        "crushing_target": crushing_target,
        "cane_reg_target": cane_reg_target,
        "recovery_target": recovery_target,
        "farmer_meetings": farmer_meetings,
        "kcc_target": kcc_target,
        "ht_agreement": ht_agreement,
        "canara_ht_loan": canara_ht_loan,
        "sangola_ht_loan": sangola_ht_loan,
        "calculated_score": calculated_score,
    }


# ── Tasks (from TASK_MASTER) ───────────────────────────────────────────────
@router.get("/tasks/{user_id}")
def get_my_tasks(user_id: int):
    """All tasks assigned to this officer from TASK_MASTER."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                t.task_id,
                t.task_name,
                t.work_type,
                CASE
                    WHEN t.end_date < CAST(GETDATE() AS DATE) AND t.status NOT IN ('COMPLETED','CANCELLED') THEN 'OVERDUE'
                    ELSE t.status
                END AS dynamic_status,
                CONVERT(VARCHAR, t.start_date, 23) AS start_date,
                CONVERT(VARCHAR, t.end_date, 23) AS end_date,
                ISNULL(l.village_code, '—') AS village,
                ISNULL(fc.total_farmers, 0) AS farmer_count,
                ISNULL(fc.done_farmers, 0) AS done_farmers,
                t.priority,
                t.remarks,
                ISNULL(t.schedule_type, 'WEEKLY') AS schedule_type
            FROM TASK_MASTER t
            LEFT JOIN TASK_LOCATION l ON l.task_id = t.task_id
            LEFT JOIN (
                SELECT task_id,
                       COUNT(*) AS total_farmers,
                       SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS done_farmers
                FROM TASK_FARMER_MAPPING
                GROUP BY task_id
            ) fc ON fc.task_id = t.task_id
            WHERE t.assigned_officer = ? AND t.status <> 'CANCELLED'
            ORDER BY t.created_at DESC
        """, user_id)
        rows = cur.fetchall()

    return [
        {
            "task_id": r[0],
            "task_name": r[1] or f"Task #{r[0]}",
            "work_type": r[2] or "—",
            "status": r[3] or "ASSIGNED",
            "start_date": r[4] or "",
            "end_date": r[5] or "",
            "village": r[6],
            "farmer_count": r[7] or 0,
            "done_farmers": r[8] or 0,
            "completion_pct": round((r[8] or 0) / r[7] * 100) if r[7] else 0,
            "priority": r[9] or "Medium",
            "remarks": r[10] or "",
            "schedule_type": r[11] or "WEEKLY",
        }
        for r in rows
    ]


@router.get("/tasks/{user_id}/{task_id}")
def get_my_task_detail(user_id: int, task_id: int):
    """Task detail with farmer rows — for the work submission page."""
    with db_cursor() as cur:
        # Verify this task belongs to the officer
        cur.execute("""
            SELECT task_name, work_type, priority,
                   CONVERT(VARCHAR, start_date, 23) AS start_date,
                   CONVERT(VARCHAR, end_date, 23) AS end_date,
                   status, remarks,
                   ISNULL(schedule_type, 'WEEKLY') AS schedule_type
            FROM TASK_MASTER
            WHERE task_id = ? AND assigned_officer = ?
        """, task_id, user_id)
        tm = cur.fetchone()
        if not tm:
            raise HTTPException(status_code=404, detail="Task not found or not assigned to you")

        # Location
        cur.execute("""
            SELECT ISNULL(village_code, ''), ISNULL(taluka_code, '')
            FROM TASK_LOCATION WHERE task_id = ?
        """, task_id)
        loc = cur.fetchone()

        # Farmer rows
        cur.execute("""
            SELECT
                tfm.id AS mapping_id,
                tfm.farmer_id,
                ISNULL(m.NameE, '') AS farmer_name,
                ISNULL(v.Village_NameE, '') AS village,
                ISNULL(m.MobileNumber, '') AS mobile,
                tfm.status
            FROM TASK_FARMER_MAPPING tfm
            LEFT JOIN dbo.TBL_MST_MASTER m ON m.code = tfm.farmer_id
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
            WHERE tfm.task_id = ?
        """, task_id)
        farmer_rows = cur.fetchall()

    return {
        "task_id": task_id,
        "task_name": tm[0],
        "work_type": tm[1],
        "priority": tm[2],
        "start_date": tm[3],
        "end_date": tm[4],
        "status": tm[5],
        "remarks": tm[6] or "",
        "schedule_type": tm[7] or "WEEKLY",
        "village": loc[0] if loc else "",
        "taluka": loc[1] if loc else "",
        "farmers": [
            {
                "mapping_id": r[0],
                "farmer_id": r[1],
                "name": r[2] or f"Farmer #{r[1]}",
                "village": r[3],
                "mobile": r[4] or "",
                "status": r[5],
            }
            for r in farmer_rows
        ],
    }


# ── Task Farmer Progress ───────────────────────────────────────────────────
@router.patch("/task-farmers/{mapping_id}/progress")
def update_farmer_progress(mapping_id: int, body: ProgressUpdate, user_id: int = Query(...)):
    """Mark a farmer mapping as IN_PROGRESS and log activity."""
    with db_cursor() as cur:
        # Verify mapping exists and belongs to user's task
        cur.execute("""
            SELECT tfm.task_id, tm.assigned_officer
            FROM TASK_FARMER_MAPPING tfm
            JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
            WHERE tfm.id = ?
        """, mapping_id)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Mapping not found")
        if row[1] != user_id:
            raise HTTPException(status_code=403, detail="Not your task")

        task_id = row[0]

        cur.execute("""
            UPDATE TASK_FARMER_MAPPING SET status = 'IN_PROGRESS' WHERE id = ?
        """, mapping_id)

        # Also update task status to IN_PROGRESS if it was ASSIGNED/PENDING
        cur.execute("""
            UPDATE TASK_MASTER SET status = 'IN_PROGRESS'
            WHERE task_id = ? AND status IN ('ASSIGNED', 'PENDING')
        """, task_id)

        # Log activity
        remarks = body.description or "Started work on farmer"
        if body.latitude and body.longitude:
            remarks += f" (GPS: {body.latitude}, {body.longitude})"
        cur.execute("""
            INSERT INTO TASK_ACTIVITY_LOG (task_id, action, remarks, officer)
            VALUES (?, 'FARMER_IN_PROGRESS', ?, ?)
        """, task_id, remarks, user_id)

    return {"ok": True, "status": "IN_PROGRESS"}


@router.post("/task-farmers/{mapping_id}/evidence")
def submit_farmer_evidence(mapping_id: int, body: EvidenceSubmission, user_id: int = Query(...)):
    """Log evidence / telemetry for a farmer visit. Also inserts into dbo.activities."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT tfm.task_id, tfm.farmer_id, tm.assigned_officer, tm.work_type
            FROM TASK_FARMER_MAPPING tfm
            JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
            WHERE tfm.id = ?
        """, mapping_id)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Mapping not found")
        if row[2] != user_id:
            raise HTTPException(status_code=403, detail="Not your task")

        task_id, farmer_id, _, work_type = row

        # Log to TASK_ACTIVITY_LOG
        remarks = body.description or "Evidence submitted"
        if body.latitude and body.longitude:
            remarks += f" (GPS: {body.latitude}, {body.longitude})"
        cur.execute("""
            INSERT INTO TASK_ACTIVITY_LOG (task_id, action, remarks, officer)
            VALUES (?, 'EVIDENCE_SUBMITTED', ?, ?)
        """, task_id, remarks, user_id)

        # Also insert into dbo.activities for backward compatibility
        cur.execute("""
            INSERT INTO dbo.activities
                (user_id, farmer_name, mobile_number, purpose_of_work_id, village, city,
                 latitude, longitude, description, created_on, deleted)
            VALUES (?, ?, ?, NULL, ?, '', ?, ?, ?, GETDATE(), 0)
        """, user_id, body.farmer_name or "", body.mobile or "",
             "", body.latitude, body.longitude, body.description or "")

    return {"ok": True}


@router.post("/task-farmers/{mapping_id}/complete")
def complete_farmer(mapping_id: int, body: CompleteSubmission, user_id: int = Query(...)):
    """Mark a farmer mapping as COMPLETED and check if all farmers are done."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT tfm.task_id, tm.assigned_officer
            FROM TASK_FARMER_MAPPING tfm
            JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
            WHERE tfm.id = ?
        """, mapping_id)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Mapping not found")
        if row[1] != user_id:
            raise HTTPException(status_code=403, detail="Not your task")

        task_id = row[0]

        cur.execute("""
            UPDATE TASK_FARMER_MAPPING SET status = 'COMPLETED' WHERE id = ?
        """, mapping_id)

        # Log activity
        remarks = body.description or "Farmer visit completed"
        if body.latitude and body.longitude:
            remarks += f" (GPS: {body.latitude}, {body.longitude})"
        cur.execute("""
            INSERT INTO TASK_ACTIVITY_LOG (task_id, action, remarks, officer)
            VALUES (?, 'FARMER_COMPLETED', ?, ?)
        """, task_id, remarks, user_id)

        # Check if all farmers for this task are completed
        cur.execute("""
            SELECT COUNT(*) FROM TASK_FARMER_MAPPING
            WHERE task_id = ? AND status <> 'COMPLETED'
        """, task_id)
        remaining = cur.fetchone()[0]

        if remaining == 0:
            cur.execute("""
                UPDATE TASK_MASTER SET status = 'COMPLETED' WHERE task_id = ?
            """, task_id)
            cur.execute("""
                INSERT INTO TASK_ACTIVITY_LOG (task_id, action, remarks, officer)
                VALUES (?, 'TASK_COMPLETED', 'All farmers completed — task auto-closed', ?)
            """, task_id, user_id)

    return {"ok": True, "status": "COMPLETED", "remaining": remaining}


# ── Activity History ────────────────────────────────────────────────────────
@router.get("/activity/{user_id}")
def get_my_activity(user_id: int):
    """Officer's own activity history from TASK_ACTIVITY_LOG."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT TOP 30
                al.log_id,
                tm.task_name,
                tm.work_type,
                ISNULL(tl.village_code, '—') AS village,
                al.action,
                CONVERT(VARCHAR, al.timestamp, 106) AS act_date,
                al.remarks
            FROM TASK_ACTIVITY_LOG al
            JOIN TASK_MASTER tm ON tm.task_id = al.task_id
            LEFT JOIN TASK_LOCATION tl ON tl.task_id = tm.task_id
            WHERE al.officer = ?
            ORDER BY al.timestamp DESC
        """, user_id)
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "task_name": r[1] or "—",
            "work_type": r[2] or "—",
            "village": r[3],
            "action": r[4] or "—",
            "date": r[5] or "—",
            "remarks": r[6],
        }
        for r in rows
    ]


# ── Alerts (dynamically computed) ──────────────────────────────────────────
@router.get("/alerts/{user_id}")
def get_my_alerts(user_id: int):
    """Dynamic alerts based on task states."""
    alerts = []
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) as overdue,
                SUM(CASE WHEN status IN ('ASSIGNED','PENDING') THEN 1 ELSE 0 END) as pending
            FROM TASK_MASTER
            WHERE assigned_officer = ?
        """, user_id)
        row = cur.fetchone()
        overdue = row[0] or 0
        pending = row[1] or 0

    if overdue:
        alerts.append({
            "type": "warning",
            "title": "Overdue Tasks",
            "message": f"You have {overdue} overdue task(s) that need immediate attention.",
            "icon": "warning",
        })
    if pending:
        alerts.append({
            "type": "info",
            "title": "Pending Assignments",
            "message": f"You have {pending} new task(s) waiting for you to start.",
            "icon": "assignment",
        })
    if not overdue and not pending:
        alerts.append({
            "type": "success",
            "title": "All Clear",
            "message": "You're up to date! No pending or overdue tasks.",
            "icon": "check_circle",
        })

    return alerts


# ── Insights (dynamically computed) ────────────────────────────────────────
@router.get("/insights/{user_id}")
def get_my_insights(user_id: int):
    """Dynamic performance insights for the officer."""
    insights = []
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed
            FROM TASK_MASTER
            WHERE assigned_officer = ?
        """, user_id)
        row = cur.fetchone()
        total = row[0] or 0
        completed = row[1] or 0
        score = round(completed / total * 100) if total else 0

        if total:
            insights.append({
                "icon": "trending_up",
                "title": "Completion Rate",
                "value": f"{score}%",
                "detail": f"{completed} of {total} tasks completed",
            })

        # Top work type
        cur.execute("""
            SELECT TOP 1 work_type, COUNT(*) AS cnt
            FROM TASK_MASTER
            WHERE assigned_officer = ?
            GROUP BY work_type
            ORDER BY cnt DESC
        """, user_id)
        wt = cur.fetchone()
        if wt:
            insights.append({
                "icon": "category",
                "title": "Top Work Type",
                "value": wt[0] or "—",
                "detail": f"{wt[1]} tasks assigned",
            })

        # Farmer coverage
        cur.execute("""
            SELECT COUNT(DISTINCT tfm.farmer_id)
            FROM TASK_FARMER_MAPPING tfm
            JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
            WHERE tm.assigned_officer = ?
        """, user_id)
        fc = cur.fetchone()[0] or 0
        if fc:
            insights.append({
                "icon": "groups",
                "title": "Farmers Covered",
                "value": str(fc),
                "detail": "Total unique farmers in your assignments",
            })

    return insights


@router.get("/villages/{user_id}")
def get_my_villages(user_id: int):
    """Top villages visited by this officer from TbL_TRN_Farmer_Meeting."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT TOP 5
                ISNULL(v.Village_NameE, 'Unknown') AS village,
                COUNT(*) AS cnt
            FROM TbL_TRN_Farmer_Meeting m
            JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            WHERE m.employee_id = ? AND v.Village_NameE IS NOT NULL AND v.Village_NameE <> ''
            GROUP BY v.Village_NameE
            ORDER BY cnt DESC
        """, user_id)
        rows = cur.fetchall()
    return [{"village": r[0], "count": r[1]} for r in rows]


# ── Legacy Work Submission (dbo.activities) ─────────────────────────────────
@router.post("/submissions")
def create_submission(body: WorkSubmission, user_id: int = Query(...)):
    """Insert a telemetry/activity log into dbo.activities."""
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO dbo.activities
                (user_id, farmer_name, mobile_number, purpose_of_work_id, village, city,
                 latitude, longitude, description, created_on, deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 0)
        """, user_id, body.farmer_name, body.mobile, body.purpose_code,
             body.village, body.city, body.latitude, body.longitude, body.description)

    return {"ok": True, "message": "Submission recorded"}


@router.get("/submissions/{user_id}")
def get_my_submissions(user_id: int, skip: int = Query(default=0), limit: int = Query(default=20)):
    """List the officer's own farmer meetings from TbL_TRN_Farmer_Meeting."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                m.meeting_id,
                ISNULL(f.NameE, '—') AS farmer,
                ISNULL(tm.work_type, 'Unknown') AS work_type,
                ISNULL(v.Village_NameE, '—') AS village,
                CONVERT(VARCHAR, m.created_at, 106) AS act_date,
                m.remark
            FROM TbL_TRN_Farmer_Meeting m
            LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            LEFT JOIN TASK_MASTER tm ON tm.task_id = m.work_plan_id
            WHERE m.employee_id = ?
            ORDER BY m.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, user_id, skip, limit)
        rows = cur.fetchall()
    return [
        {"id": r[0], "farmer": r[1], "work_type": r[2], "village": r[3], "date": r[4], "description": r[5] or ""}
        for r in rows
    ]
