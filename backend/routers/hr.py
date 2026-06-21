"""
routers/hr.py  –  Endpoints for the HR portal to monitor managers, employees, tasks, and system actions.
"""
from fastapi import APIRouter, HTTPException, Query
from database import db_cursor
from pydantic import BaseModel
from typing import List, Optional
import math
from auth import md5_hash

router = APIRouter(prefix="/api/hr", tags=["hr"])

# Pydantic models for request bodies
class ResetPasswordRequest(BaseModel):
    new_password: str

class ToggleBlockRequest(BaseModel):
    is_blocked: bool


@router.get("/stats")
def get_hr_stats():
    """HR Portal aggregate statistics."""
    with db_cursor() as cur:
        # Total managers and officers
        cur.execute("""
            SELECT 
                SUM(CASE WHEN is_staff = 1 AND is_superuser = 0 THEN 1 ELSE 0 END) AS managers,
                SUM(CASE WHEN is_staff = 0 THEN 1 ELSE 0 END) AS officers
            FROM dbo.auth_user
            WHERE is_active = 1
        """)
        user_row = cur.fetchone()
        managers_count = user_row[0] or 0
        officers_count = user_row[1] or 0

        # Tasks stats
        cur.execute("""
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'IN_PROGRESS' AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) AS overdue
            FROM TASK_MASTER
        """)
        task_row = cur.fetchone()
        total_tasks = task_row[0] or 0
        completed_tasks = task_row[1] or 0
        in_progress_tasks = task_row[2] or 0
        overdue_tasks = task_row[3] or 0

        # Overall completion percentage
        completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks else 0.0

        # Unique active employees who submitted work today
        cur.execute("""
            SELECT COUNT(DISTINCT employee_id)
            FROM TbL_TRN_Farmer_Meeting
            WHERE CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
        """)
        active_today = cur.fetchone()[0] or 0

    return {
        "total_managers": managers_count,
        "total_officers": officers_count,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "overdue_tasks": overdue_tasks,
        "completion_rate": completion_rate,
        "active_today": active_today
    }


@router.get("/activities")
def get_global_activities(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100)
):
    """System-wide audit trail of all manager and employee actions."""
    where_sql = "1=1"
    offset = (page - 1) * page_size

    with db_cursor() as cur:
        # Total count
        cur.execute(f"SELECT COUNT(*) FROM TASK_ACTIVITY_LOG WHERE {where_sql}")
        total = cur.fetchone()[0]

        # Paginated rows
        cur.execute(f"""
            SELECT 
                al.log_id,
                al.action,
                al.remarks,
                CONVERT(VARCHAR, al.timestamp, 120) AS timestamp,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS user_name,
                u.username,
                u.is_staff,
                tm.task_name,
                al.task_id
            FROM TASK_ACTIVITY_LOG al
            LEFT JOIN dbo.auth_user u ON u.id = al.officer
            LEFT JOIN TASK_MASTER tm ON tm.task_id = al.task_id
            WHERE {where_sql}
            ORDER BY al.timestamp DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, offset, page_size)
        rows = cur.fetchall()

    activities = []
    for r in rows:
        user_role = "System"
        if r[4] or r[5]:
            user_role = "Manager" if r[6] else "Field Officer"

        activities.append({
            "log_id": r[0],
            "action": r[1],
            "remarks": r[2],
            "timestamp": r[3],
            "user_name": (r[4] or "").strip() or r[5] or "System",
            "user_role": user_role,
            "task_name": r[7] or f"Task #{r[8]}" if r[8] else "N/A",
            "task_id": r[8]
        })

    return {
        "items": activities,
        "total": total,
        "page": page,
        "pages": math.ceil(total / page_size) if total else 1
    }


@router.get("/managers")
def get_managers():
    """List of all manager profiles, workloads, and audit stats."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT 
                u.id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                u.username,
                u.email,
                CONVERT(VARCHAR, u.date_joined, 106) AS joined,
                CONVERT(VARCHAR, ud.last_loged_in, 106) AS last_login,
                ISNULL(tc.cnt, 0) AS tasks_assigned,
                ISNULL(rc.cnt, 0) AS reports_generated,
                ISNULL(ud.is_blocked, 0) AS is_blocked
            FROM dbo.auth_user u
            LEFT JOIN dbo.user_details ud ON ud.user_id = u.id
            LEFT JOIN (
                SELECT assigned_by, COUNT(*) as cnt 
                FROM TASK_MASTER 
                GROUP BY assigned_by
            ) tc ON tc.assigned_by = u.id
            LEFT JOIN (
                SELECT generated_by, COUNT(*) as cnt 
                FROM REPORT_MASTER 
                GROUP BY generated_by
            ) rc ON rc.generated_by = u.id
            WHERE u.is_staff = 1 AND u.id IS NOT NULL AND u.is_active = 1
            ORDER BY full_name
        """)
        rows = cur.fetchall()

    managers = []
    for r in rows:
        managers.append({
            "id": r[0],
            "name": (r[1] or "").strip() or r[2],
            "username": r[2],
            "email": r[3] or "—",
            "joined": r[4] or "—",
            "last_login": r[5] or "—",
            "tasks_assigned": r[6],
            "reports_generated": r[7],
            "is_blocked": bool(r[8])
        })
    return managers


@router.get("/officers")
def get_officers():
    """List of all field officer profiles, task workloads, and aggregate scores."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT 
                u.id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                u.username,
                u.email,
                CONVERT(VARCHAR, u.date_joined, 106) AS joined,
                CONVERT(VARCHAR, ud.last_loged_in, 106) AS last_login,
                ISNULL(ud.is_blocked, 0) AS is_blocked,
                ISNULL(tc.total, 0) AS total_tasks,
                ISNULL(tc.completed, 0) AS completed_tasks,
                ISNULL(tc.overdue, 0) AS overdue_tasks,
                ISNULL(act.cnt, 0) AS total_meetings
            FROM dbo.auth_user u
            LEFT JOIN dbo.user_details ud ON ud.user_id = u.id
            LEFT JOIN (
                SELECT assigned_officer,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) as overdue
                FROM TASK_MASTER
                GROUP BY assigned_officer
            ) tc ON tc.assigned_officer = u.id
            LEFT JOIN (
                SELECT employee_id, COUNT(*) AS cnt
                FROM TbL_TRN_Farmer_Meeting
                GROUP BY employee_id
            ) act ON act.employee_id = u.id
            WHERE u.is_staff = 0 AND u.id IS NOT NULL AND u.is_active = 1
            ORDER BY full_name
        """)
        rows = cur.fetchall()

    officers = []
    for r in rows:
        total = r[7]
        completed = r[8]
        completion_score = round(completed / total * 100) if total else 0

        officers.append({
            "id": r[0],
            "name": (r[1] or "").strip() or r[2],
            "username": r[2],
            "email": r[3] or "—",
            "joined": r[4] or "—",
            "last_login": r[5] or "—",
            "is_blocked": bool(r[6]),
            "total_tasks": total,
            "completed_tasks": completed,
            "overdue_tasks": r[9],
            "total_meetings": r[10],
            "completion_score": completion_score
        })
    return officers


@router.post("/users/{user_id}/reset-password")
def reset_user_password(user_id: int, body: ResetPasswordRequest):
    """Allows HR to reset any user's credentials."""
    new_hash = md5_hash(body.new_password)
    with db_cursor() as cur:
        cur.execute("SELECT id FROM dbo.auth_user WHERE id = ? AND is_active = 1", user_id)
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        # Update auth_user password
        cur.execute("UPDATE dbo.auth_user SET password = ? WHERE id = ?", new_hash, user_id)
        
        # Also update user_details password if entry exists
        cur.execute("UPDATE dbo.user_details SET password = ? WHERE user_id = ?", new_hash, user_id)

    return {"success": True, "message": "Password reset successful"}


@router.post("/users/{user_id}/block")
def toggle_user_block(user_id: int, body: ToggleBlockRequest):
    """Allows HR to block or unblock any manager or employee account."""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM dbo.auth_user WHERE id = ?", user_id)
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        # Check if row exists in user_details, if not insert, else update
        cur.execute("SELECT COUNT(*) FROM dbo.user_details WHERE user_id = ?", user_id)
        exists = cur.fetchone()[0] > 0

        if exists:
            cur.execute("UPDATE dbo.user_details SET is_blocked = ? WHERE user_id = ?", int(body.is_blocked), user_id)
        else:
            cur.execute("""
                INSERT INTO dbo.user_details (user_id, is_blocked, password)
                VALUES (?, ?, '')
            """, user_id, int(body.is_blocked))

    return {"success": True, "is_blocked": body.is_blocked}


@router.get("/tasks")
def get_tasks_list(
    manager_id: Optional[int] = None,
    officer_id: Optional[int] = None,
    status: Optional[str] = None,
    work_type: Optional[str] = None
):
    """Advanced task list for HR monitoring with filtering."""
    where_parts = ["1=1"]
    params = []

    # Check for instances of fastapi params Query which can happen when run directly from python tests
    from fastapi.params import Query as FastAPIQuery
    
    if manager_id is not None and not isinstance(manager_id, FastAPIQuery):
        where_parts.append("t.assigned_by = ?")
        params.append(manager_id)
    if officer_id is not None and not isinstance(officer_id, FastAPIQuery):
        where_parts.append("t.assigned_officer = ?")
        params.append(officer_id)
    if status is not None and not isinstance(status, FastAPIQuery) and status:
        if status == "OVERDUE":
            where_parts.append("t.end_date < CAST(GETDATE() AS DATE) AND t.status NOT IN ('COMPLETED', 'CANCELLED')")
        else:
            where_parts.append("t.status = ?")
            params.append(status)
    if work_type is not None and not isinstance(work_type, FastAPIQuery) and work_type:
        where_parts.append("t.work_type = ?")
        params.append(work_type)

    where_sql = " AND ".join(where_parts)

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT 
                t.task_id,
                t.task_name,
                t.work_type,
                t.priority,
                CONVERT(VARCHAR, t.start_date, 23) AS start_date,
                CONVERT(VARCHAR, t.end_date, 23) AS end_date,
                CASE
                    WHEN t.end_date < CAST(GETDATE() AS DATE) AND t.status NOT IN ('COMPLETED','CANCELLED') THEN 'OVERDUE'
                    ELSE t.status
                END AS dynamic_status,
                ISNULL(u1.first_name,'') + ' ' + ISNULL(u1.last_name,'') AS officer_name,
                ISNULL(u2.first_name,'') + ' ' + ISNULL(u2.last_name,'') AS manager_name,
                (SELECT COUNT(*) FROM TASK_FARMER_MAPPING r WHERE r.task_id = t.task_id) AS farmer_count
            FROM TASK_MASTER t
            LEFT JOIN dbo.auth_user u1 ON u1.id = t.assigned_officer
            LEFT JOIN dbo.auth_user u2 ON u2.id = t.assigned_by
            WHERE {where_sql}
            ORDER BY t.task_id DESC
        """, *params)
        rows = cur.fetchall()

    tasks = []
    for r in rows:
        tasks.append({
            "task_id": r[0],
            "task_name": r[1] or f"Task #{r[0]}",
            "work_type": r[2] or "—",
            "priority": r[3] or "Medium",
            "start_date": r[4] or "",
            "end_date": r[5] or "",
            "status": r[6] or "PENDING",
            "officer_name": (r[7] or "").strip() or "Unassigned",
            "manager_name": (r[8] or "").strip() or "System",
            "farmer_count": r[9] or 0
        })

    return tasks


@router.get("/tasks/{task_id}")
def get_task_micro_detail(task_id: int):
    """Returns micro-level detail for a specific task including checklist compliance metrics and timelines."""
    with db_cursor() as cur:
        # 1. Fetch Task Info
        cur.execute("""
            SELECT 
                t.task_id,
                t.task_name,
                t.work_type,
                t.priority,
                CONVERT(VARCHAR, t.start_date, 23) AS start_date,
                CONVERT(VARCHAR, t.end_date, 23) AS end_date,
                CASE
                    WHEN t.end_date < CAST(GETDATE() AS DATE) AND t.status NOT IN ('COMPLETED','CANCELLED') THEN 'OVERDUE'
                    ELSE t.status
                END AS dynamic_status,
                t.remarks,
                t.schedule_type,
                t.assigned_officer,
                ISNULL(u1.first_name,'') + ' ' + ISNULL(u1.last_name,'') AS officer_name,
                t.assigned_by,
                ISNULL(u2.first_name,'') + ' ' + ISNULL(u2.last_name,'') AS manager_name
            FROM TASK_MASTER t
            LEFT JOIN dbo.auth_user u1 ON u1.id = t.assigned_officer
            LEFT JOIN dbo.auth_user u2 ON u2.id = t.assigned_by
            WHERE t.task_id = ?
        """, task_id)
        tm_row = cur.fetchone()
        if not tm_row:
            raise HTTPException(status_code=404, detail="Task not found")

        officer_id = tm_row[9]

        # 2. Get TASK_LOCATION
        cur.execute("""
            SELECT taluka_code, village_code, subvillage_code
            FROM TASK_LOCATION
            WHERE task_id = ?
        """, task_id)
        loc_row = cur.fetchone()
        location = {
            "district": loc_row[0] if loc_row else "—",
            "village": loc_row[1] if loc_row else "—",
            "sub_village": loc_row[2] if loc_row else "—"
        }

        # 3. Get all mapped farmers and their meeting checklist answers
        cur.execute("""
            SELECT
                tfm.farmer_id,
                ISNULL(m.NameE, 'Unknown') AS farmer_name,
                ISNULL(v.Village_NameE, '') AS village,
                tfm.status AS mapping_status,
                fm.kcc, fm.kcc_reason,
                fm.canara_hnt, fm.canara_reason,
                fm.sangola_hnt, fm.sangola_reason,
                fm.cane_registration, fm.cane_registration_remark,
                fm.recovery, fm.recovery_reason,
                fm.vehicle_agreement, fm.vehicle_reason,
                fm.expected_tonnage,
                fm.feedback,
                fm.remark,
                CONVERT(VARCHAR, fm.created_at, 120) AS meeting_date
            FROM TASK_FARMER_MAPPING tfm
            LEFT JOIN dbo.TBL_MST_MASTER m ON m.code = tfm.farmer_id
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
            LEFT JOIN TbL_TRN_Farmer_Meeting fm ON fm.farmer_code = tfm.farmer_id 
                AND fm.employee_id = ? AND fm.work_plan_id = ?
            WHERE tfm.task_id = ?
        """, officer_id, task_id, task_id)
        farmer_rows = cur.fetchall()

        # 4. Get Task Timeline Activity Logs
        cur.execute("""
            SELECT 
                al.log_id,
                al.action,
                al.remarks,
                CONVERT(VARCHAR, al.timestamp, 120) AS timestamp_str,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS officer_name
            FROM TASK_ACTIVITY_LOG al
            LEFT JOIN dbo.auth_user u ON u.id = al.officer
            WHERE al.task_id = ?
            ORDER BY al.timestamp ASC
        """, task_id)
        timeline_rows = cur.fetchall()

    # Formulate farmers checklist list
    farmers = []
    completed_farmers = 0
    total_farmers = len(farmer_rows)

    for r in farmer_rows:
        has_meeting = r[18] is not None
        if r[3] == 'COMPLETED' or has_meeting:
            completed_farmers += 1

        farmers.append({
            "farmer_code": r[0],
            "farmer_name": (r[1] or "").strip() or f"Farmer #{r[0]}",
            "village": r[2] or "—",
            "status": r[3] or "PENDING",
            "has_meeting": has_meeting,
            "kcc": bool(r[4]) if r[4] is not None else None,
            "kcc_reason": r[5] or "",
            "canara_hnt": bool(r[6]) if r[6] is not None else None,
            "canara_reason": r[7] or "",
            "sangola_hnt": bool(r[8]) if r[8] is not None else None,
            "sangola_reason": r[9] or "",
            "cane_registration": bool(r[10]) if r[10] is not None else None,
            "cane_registration_remark": r[11] or "",
            "recovery": bool(r[12]) if r[12] is not None else None,
            "recovery_reason": r[13] or "",
            "vehicle_agreement": bool(r[14]) if r[14] is not None else None,
            "vehicle_reason": r[15] or "",
            "expected_tonnage": float(r[16]) if r[16] is not None else 0.0,
            "feedback": r[17] or "",
            "remark": r[18] or "",
            "meeting_date": r[19] or ""
        })

    completion_pct = round(completed_farmers / total_farmers * 100) if total_farmers else 0

    timeline = []
    for r in timeline_rows:
        timeline.append({
            "log_id": r[0],
            "action": r[1],
            "remarks": r[2],
            "timestamp": r[3],
            "user_name": (r[4] or "").strip() or "System"
        })

    # Task metrics object
    metrics = {
        "total_farmers": total_farmers,
        "completed_farmers": completed_farmers,
        "completion_rate": completion_pct,
    }

    return {
        "task_id": tm_row[0],
        "task_name": tm_row[1],
        "work_type": tm_row[2],
        "priority": tm_row[3],
        "start_date": tm_row[4],
        "end_date": tm_row[5],
        "status": tm_row[6],
        "remarks": tm_row[7] or "",
        "schedule_type": tm_row[8] or "WEEKLY",
        "officer_name": (tm_row[10] or "").strip() or "Unassigned",
        "manager_name": (tm_row[12] or "").strip() or "System",
        "location": location,
        "farmers": farmers,
        "timeline": timeline,
        "metrics": metrics
    }
