"""
routers/tasks.py  –  Daily work plan management (NEW TASK MODULE)
Tables: TASK_MASTER, TASK_LOCATION, TASK_FARMER_MAPPING, TASK_ACTIVITY_LOG,
        TBL_MST_MASTER (farmers), auth_user (officers),
        TBL_MST_DAILY_WORKTYPE (work types),
        TBl_mst_village, TBl_mst_taluka
"""
from fastapi import APIRouter, HTTPException, Query, Header
from database import db_cursor
from datetime import datetime, timedelta
import calendar
from pydantic import BaseModel
from typing import List, Optional

VALID_SCHEDULE_TYPES = {"DAILY", "WEEKLY", "MONTHLY"}

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class AssignTaskRequest(BaseModel):
    task_name: str
    officer_id: int
    work_type_name: str
    priority: str
    from_date: str  # YYYY-MM-DD
    to_date: str    # YYYY-MM-DD
    schedule_type: str = "WEEKLY"  # DAILY | WEEKLY | MONTHLY
    remarks: str = ""
    district: str = ""
    village: str = ""
    sub_village: str = ""
    farmers: List[int]
    manager_id: int = 1 # fallback


@router.get("/officers")
def get_assignable_officers():
    """Officers available for task assignment (workload from TASK_MASTER)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                u.id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                ISNULL(plans.cnt, 0) AS pending_plans,
                ISNULL(stats.in_progress, 0) AS in_progress,
                ISNULL(stats.done, 0) AS done,
                u.username
            FROM dbo.auth_user u
            LEFT JOIN (
                SELECT assigned_officer, COUNT(*) AS cnt
                FROM TASK_MASTER
                WHERE CASE
                    WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 'OVERDUE'
                    ELSE status
                  END IN ('ASSIGNED', 'PENDING')
                GROUP BY assigned_officer
            ) plans ON plans.assigned_officer = u.id
            LEFT JOIN (
                SELECT
                    assigned_officer,
                    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS done,
                    SUM(CASE
                        WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 0
                        WHEN status = 'IN_PROGRESS' THEN 1 ELSE 0
                    END) AS in_progress
                FROM TASK_MASTER
                GROUP BY assigned_officer
            ) stats ON stats.assigned_officer = u.id
            LEFT JOIN dbo.user_details ud ON ud.user_id = u.id
            WHERE u.is_active = 1
              AND ISNULL(ud.is_blocked, 0) = 0
              AND u.id IS NOT NULL
            ORDER BY full_name
        """)
        rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "name": (r[1] or "").strip() or "Unknown",
            "pending": r[2],
            "inprogress": r[3],
            "done": r[4],
            "code": r[5] or "",
        }
        for r in rows
    ]


@router.get("/work-types")
def get_work_types():
    with db_cursor() as cur:
        cur.execute("SELECT work_type_id, work_type_name FROM dbo.TBL_MST_DAILY_WORKTYPE ORDER BY work_type_name")
        rows = cur.fetchall()
    return [{"id": r[0], "name": r[1]} for r in rows]


@router.get("/farmers")
def get_farmers(
    village: str = Query(default=""),
    taluka: str = Query(default=""),
    sub_village: str = Query(default=""),
    search: str = Query(default=""),
    exclude_task_id: Optional[int] = Query(default=None),
):
    """Farmer search from TBL_MST_MASTER, excluding active tasks."""
    where_parts = ["1=1"]
    params = []

    if village:
        where_parts.append("v.Village_NameE = ?")
        params.append(village)
    if taluka:
        where_parts.append("t.Taluka_NameE = ?")
        params.append(taluka)
    if sub_village:
        where_parts.append("s.Subvillage_NameE = ?")
        params.append(sub_village)
    if search:
        where_parts.append("(m.NameE LIKE ? OR CAST(m.code AS VARCHAR(20)) LIKE ?)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    exclude_clause = ""
    exclude_params = []
    if exclude_task_id is not None:
        exclude_clause = "AND tm.task_id != ?"
        exclude_params = [exclude_task_id]

    sql = f"""
        SELECT TOP 200
            m.code,
            m.NameE,
            ISNULL(v.Village_NameE, '') AS village,
            ISNULL(t.Taluka_NameE, '')  AS taluka,
            ISNULL(m.MobileNumber, '') AS mobile
        FROM dbo.TBL_MST_MASTER m
        LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
        LEFT JOIN dbo.TBl_mst_taluka  t ON t.Taluka_Code  = m.Talula_Code
        LEFT JOIN dbo.Tbl_mst_sub_village s ON s.Subvillage_code = m.Subvillage_code
        WHERE {' AND '.join(where_parts)}
          AND m.code NOT IN (
              SELECT farmer_id 
              FROM TASK_FARMER_MAPPING tfm
              JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
              WHERE tm.status NOT IN ('COMPLETED', 'CANCELLED')
              {exclude_clause}
          )
        ORDER BY m.NameE
    """
    with db_cursor() as cur:
        cur.execute(sql, *params, *exclude_params)
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "name": r[1],
            "village": r[2],
            "taluka": r[3],
            "mobile": r[4] or "",
        }
        for r in rows
    ]


@router.get("/talukas")
def get_talukas():
    with db_cursor() as cur:
        cur.execute("SELECT DISTINCT Taluka_NameE FROM dbo.TBl_mst_taluka WHERE Taluka_NameE IS NOT NULL ORDER BY Taluka_NameE")
        return [r[0] for r in cur.fetchall()]


@router.get("/villages")
def get_villages(taluka: str = Query(default="")):
    with db_cursor() as cur:
        if taluka:
            cur.execute("""
                SELECT DISTINCT v.Village_NameE
                FROM dbo.TBl_mst_village v
                JOIN dbo.TBl_mst_taluka t ON t.Taluka_Code = v.Taluka_Code
                WHERE t.Taluka_NameE = ? AND v.Village_NameE IS NOT NULL
                ORDER BY v.Village_NameE
            """, taluka)
        else:
            cur.execute("SELECT DISTINCT Village_NameE FROM dbo.TBl_mst_village WHERE Village_NameE IS NOT NULL ORDER BY Village_NameE")
        return [r[0] for r in cur.fetchall()]


@router.get("/sub-villages")
def get_sub_villages(village: str = Query(default="")):
    with db_cursor() as cur:
        if village:
            cur.execute("""
                SELECT DISTINCT s.Subvillage_NameE
                FROM dbo.Tbl_mst_sub_village s
                JOIN dbo.TBl_mst_village v ON v.Village_Code = s.Village_code
                WHERE v.Village_NameE = ? AND s.Subvillage_NameE IS NOT NULL
                ORDER BY s.Subvillage_NameE
            """, village)
        else:
            cur.execute("SELECT DISTINCT Subvillage_NameE FROM dbo.Tbl_mst_sub_village WHERE Subvillage_NameE IS NOT NULL ORDER BY Subvillage_NameE")
        return [r[0] for r in cur.fetchall()]


@router.get("")
def list_tasks(officer_id: int = Query(default=0)):
    """List tasks from TASK_MASTER."""
    where = ""
    params = []
    if officer_id:
        where = "WHERE p.assigned_officer = ?"
        params.append(officer_id)

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT TOP 50
                p.task_id,
                p.assigned_officer,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS officer_name,
                MONTH(p.start_date),
                DATEPART(week, p.start_date) - DATEPART(week, DATEADD(month, DATEDIFF(month, 0, p.start_date), 0)) + 1,
                CONVERT(VARCHAR, p.start_date, 23) AS from_date,
                CONVERT(VARCHAR, p.end_date, 23)   AS to_date,
                (SELECT COUNT(*) FROM TASK_FARMER_MAPPING r WHERE r.task_id = p.task_id) AS farmer_count,
                p.work_type,
                (
                    SELECT STUFF((
                        SELECT TOP 5 ', ' + ISNULL(m2.NameE, '')
                        FROM TASK_FARMER_MAPPING r3
                        LEFT JOIN dbo.TBL_MST_MASTER m2 ON m2.code = r3.farmer_id
                        WHERE r3.task_id = p.task_id
                        ORDER BY r3.id
                        FOR XML PATH(''), TYPE
                    ).value('.', 'NVARCHAR(MAX)'), 1, 2, '')
                ) AS farmer_preview,
                p.task_name,
                CASE
                    WHEN p.end_date < CAST(GETDATE() AS DATE) AND p.status NOT IN ('COMPLETED','CANCELLED') THEN 'OVERDUE'
                    ELSE p.status
                END AS dynamic_status,
                ISNULL(p.schedule_type, 'WEEKLY') AS schedule_type
            FROM TASK_MASTER p
            LEFT JOIN dbo.auth_user u ON u.id = p.assigned_officer
            {where}
            ORDER BY p.task_id DESC
        """, *params)
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "officer_id": r[1],
            "officer_name": (r[2] or "").strip() or "Unknown",
            "month": r[3] or 1,
            "week": r[4] or 1,
            "from_date": r[5] or "",
            "to_date": r[6] or "",
            "farmers": r[7] or 0,
            "work_type": r[8] or "",
            "farmer_preview": r[9] or "",
            "task_name": r[10] or f"Plan #{r[0]}",
            "status": r[11] or "ASSIGNED",
            "schedule_type": r[12] or "WEEKLY"
        }
        for r in rows
    ]


@router.get("/{task_id}/rows")
def get_plan_rows(task_id: int):
    """Get individual farmer rows for a task."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                r.id,
                r.farmer_id,
                m.NameE AS farmer_name,
                ISNULL(v.Village_NameE,'') AS village,
                tm.work_type,
                0 as work_count,
                r.status
            FROM TASK_FARMER_MAPPING r
            JOIN TASK_MASTER tm ON tm.task_id = r.task_id
            LEFT JOIN dbo.TBL_MST_MASTER m ON m.code = r.farmer_id
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
            WHERE r.task_id = ?
        """, task_id)
        rows = cur.fetchall()

    return [
        {
            "id": r[0], "farmer_id": r[1], "farmer_name": r[2] or "—",
            "village": r[3], "work_type": r[4] or "—",
            "work_count": r[5], "status": r[6],
        }
        for r in rows
    ]


@router.post("/assign")
def assign_task(body: AssignTaskRequest):
    try:
        from_dt = datetime.strptime(body.from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(body.to_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expect YYYY-MM-DD")

    # Validate schedule_type
    stype = (body.schedule_type or "WEEKLY").upper()
    if stype not in VALID_SCHEDULE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid schedule_type: {body.schedule_type}")

    # Validate date constraints per schedule type
    if stype == "DAILY" and from_dt.date() != to_dt.date():
        raise HTTPException(status_code=400, detail="Daily schedule: start and end date must be the same")
    if stype == "WEEKLY":
        diff = (to_dt.date() - from_dt.date()).days
        if diff != 6:
            raise HTTPException(status_code=400, detail="Weekly schedule: date range must be exactly 7 days (Mon–Sun)")
    if stype == "MONTHLY":
        if from_dt.day != 1:
            raise HTTPException(status_code=400, detail="Monthly schedule: start date must be the 1st of the month")
        last_day = calendar.monthrange(to_dt.year, to_dt.month)[1]
        if to_dt.day != last_day or from_dt.month != to_dt.month or from_dt.year != to_dt.year:
            raise HTTPException(status_code=400, detail="Monthly schedule: dates must cover the full calendar month")

    with db_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM dbo.TBL_MST_DAILY_WORKTYPE WHERE work_type_name = ?",
            body.work_type_name,
        )
        if cur.fetchone()[0] == 0:
            raise HTTPException(status_code=400, detail=f"Invalid work type: {body.work_type_name}")

        # Insert TASK_MASTER
        cur.execute("""
            INSERT INTO TASK_MASTER (task_name, work_type, assigned_officer, assigned_by, priority, start_date, end_date, remarks, schedule_type)
            OUTPUT INSERTED.task_id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, body.task_name, body.work_type_name, body.officer_id, body.manager_id, body.priority, from_dt, to_dt, body.remarks, stype)
        
        row = cur.fetchone()
        task_id = row[0]

        # Insert TASK_LOCATION
        cur.execute("""
            INSERT INTO TASK_LOCATION (task_id, taluka_code, village_code, subvillage_code)
            VALUES (?, ?, ?, ?)
        """, task_id, body.district, body.village, body.sub_village)

        # Insert TASK_FARMER_MAPPING
        inserted = 0
        for farmer_id in body.farmers:
            cur.execute("""
                INSERT INTO TASK_FARMER_MAPPING (task_id, farmer_id, status)
                VALUES (?, ?, 'PENDING')
            """, task_id, farmer_id)
            inserted += 1

        # Insert TASK_ACTIVITY_LOG
        cur.execute("""
            INSERT INTO TASK_ACTIVITY_LOG (task_id, action, remarks, officer)
            VALUES (?, 'ASSIGNED', 'Task assigned by manager', ?)
        """, task_id, body.manager_id)

    return {
        "success": True,
        "plan_id": task_id,
        "farmer_count": inserted,
        "work_type": body.work_type_name,
        "officer_id": body.officer_id,
        "from_date": body.from_date,
        "to_date": body.to_date,
        "schedule_type": stype,
    }


class EditTaskRequest(BaseModel):
    task_name: str
    work_type_name: str = ""
    priority: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    schedule_type: str = "WEEKLY"  # DAILY | WEEKLY | MONTHLY
    status: str
    remarks: str = ""
    district: str = ""      # maps to taluka_code
    village: str = ""       # maps to village_code
    sub_village: str = ""   # maps to subvillage_code
    farmers: List[int]
    manager_id: int = 1     # fallback


@router.get("/{task_id}")
def get_task(task_id: int):
    with db_cursor() as cur:
        # Get TASK_MASTER
        cur.execute("""
            SELECT task_name, work_type, assigned_officer, assigned_by, priority,
                   CONVERT(VARCHAR, start_date, 23) AS start_date,
                   CONVERT(VARCHAR, end_date, 23) AS end_date,
                   status, remarks,
                   ISNULL(schedule_type, 'WEEKLY') AS schedule_type
            FROM TASK_MASTER
            WHERE task_id = ?
        """, task_id)
        tm_row = cur.fetchone()
        if not tm_row:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get TASK_LOCATION
        cur.execute("""
            SELECT taluka_code, village_code, subvillage_code
            FROM TASK_LOCATION
            WHERE task_id = ?
        """, task_id)
        loc_row = cur.fetchone()
        loc = {
            "district": loc_row[0] if loc_row else "",
            "village": loc_row[1] if loc_row else "",
            "sub_village": loc_row[2] if loc_row else ""
        }

        # Get TASK_FARMER_MAPPING along with farmer details
        cur.execute("""
            SELECT 
                tfm.farmer_id,
                m.NameE AS farmer_name,
                ISNULL(v.Village_NameE, '') AS village,
                ISNULL(t.Taluka_NameE, '')  AS taluka,
                ISNULL(m.MobileNumber, '') AS mobile,
                tfm.status
            FROM TASK_FARMER_MAPPING tfm
            LEFT JOIN dbo.TBL_MST_MASTER m ON m.code = tfm.farmer_id
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
            LEFT JOIN dbo.TBl_mst_taluka  t ON t.Taluka_Code  = m.Talula_Code
            WHERE tfm.task_id = ?
        """, task_id)
        farmer_rows = cur.fetchall()

    farmers = [
        {
            "id": r[0],
            "name": (r[1] or "").strip() or f"Farmer #{r[0]}",
            "village": r[2],
            "taluka": r[3],
            "mobile": r[4] or "",
            "status": r[5]
        }
        for r in farmer_rows
    ]

    return {
        "task_id": task_id,
        "task_name": tm_row[0],
        "work_type": tm_row[1],
        "assigned_officer": tm_row[2],
        "assigned_by": tm_row[3],
        "priority": tm_row[4],
        "start_date": tm_row[5],
        "end_date": tm_row[6],
        "status": tm_row[7],
        "remarks": tm_row[8] or "",
        "schedule_type": tm_row[9] or "WEEKLY",
        "location": loc,
        "farmers": farmers
    }


@router.put("/{task_id}")
def update_task(task_id: int, body: EditTaskRequest):
    try:
        from_dt = datetime.strptime(body.start_date, "%Y-%m-%d")
        to_dt = datetime.strptime(body.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expect YYYY-MM-DD")

    with db_cursor() as cur:
        # Fetch current details for audit logging
        cur.execute("""
            SELECT task_name, work_type, priority, start_date, end_date, status, remarks
            FROM TASK_MASTER WHERE task_id = ?
        """, task_id)
        old_tm = cur.fetchone()
        if not old_tm:
            raise HTTPException(status_code=404, detail="Task not found")

        cur.execute("""
            SELECT taluka_code, village_code, subvillage_code
            FROM TASK_LOCATION WHERE task_id = ?
        """, task_id)
        old_loc = cur.fetchone()

        cur.execute("SELECT farmer_id FROM TASK_FARMER_MAPPING WHERE task_id = ?", task_id)
        old_farmers = {r[0] for r in cur.fetchall()}

        logs = []
        
        work_type = (body.work_type_name or old_tm[1] or "").strip()
        if work_type:
            cur.execute(
                "SELECT COUNT(*) FROM dbo.TBL_MST_DAILY_WORKTYPE WHERE work_type_name = ?",
                work_type,
            )
            if cur.fetchone()[0] == 0:
                raise HTTPException(status_code=400, detail=f"Invalid work type: {work_type}")

        # Validate schedule_type
        stype = (body.schedule_type or "WEEKLY").upper()
        if stype not in VALID_SCHEDULE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid schedule_type: {body.schedule_type}")

        # Update TASK_MASTER
        cur.execute("""
            UPDATE TASK_MASTER
            SET task_name = ?, work_type = ?, priority = ?, start_date = ?, end_date = ?, status = ?, remarks = ?, schedule_type = ?
            WHERE task_id = ?
        """, body.task_name, work_type, body.priority, from_dt, to_dt, body.status, body.remarks, stype, task_id)

        # Update TASK_LOCATION
        cur.execute("""
            UPDATE TASK_LOCATION
            SET taluka_code = ?, village_code = ?, subvillage_code = ?
            WHERE task_id = ?
        """, body.district, body.village, body.sub_village, task_id)

        # Check changes and add to audit logs
        if old_tm[5] != body.status:
            logs.append(("TASK_STATUS_CHANGED", f"Status changed from {old_tm[5]} to {body.status}"))
        if old_tm[1] != work_type:
            logs.append(("TASK_WORK_TYPE_CHANGED", f"Work type changed from {old_tm[1]} to {work_type}"))
        if old_tm[2] != body.priority:
            logs.append(("TASK_PRIORITY_CHANGED", f"Priority changed from {old_tm[2]} to {body.priority}"))
        if not old_loc or old_loc[0] != body.district or old_loc[1] != body.village or old_loc[2] != body.sub_village:
            logs.append(("TASK_LOCATION_CHANGED", "Task location updated"))
        if old_tm[0] != body.task_name or old_tm[3] != from_dt.date() or old_tm[4] != to_dt.date() or (old_tm[6] or "") != body.remarks:
            logs.append(("TASK_UPDATED", "Task details updated"))

        # Update TASK_FARMER_MAPPING
        new_farmers = set(body.farmers)
        to_add = new_farmers - old_farmers
        to_remove = old_farmers - new_farmers

        if to_remove:
            placeholders = ",".join(["?"] * len(to_remove))
            cur.execute(f"""
                DELETE FROM TASK_FARMER_MAPPING
                WHERE task_id = ? AND farmer_id IN ({placeholders})
            """, task_id, *list(to_remove))
            logs.append(("TASK_FARMER_REMOVED", f"Removed farmer IDs: {', '.join(map(str, to_remove))}"))

        if to_add:
            for fid in to_add:
                cur.execute("""
                    INSERT INTO TASK_FARMER_MAPPING (task_id, farmer_id, status)
                    VALUES (?, ?, 'PENDING')
                """, task_id, fid)
            logs.append(("TASK_FARMER_ADDED", f"Added farmer IDs: {', '.join(map(str, to_add))}"))

        # Insert audit logs into TASK_ACTIVITY_LOG
        for action, remarks in logs:
            cur.execute("""
                INSERT INTO TASK_ACTIVITY_LOG (task_id, action, remarks, officer)
                VALUES (?, ?, ?, ?)
            """, task_id, action, remarks, body.manager_id)

    return {"success": True, "message": "Task updated successfully"}


@router.get("/{task_id}/history")
def get_task_history(task_id: int):
    with db_cursor() as cur:
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
            ORDER BY al.timestamp DESC
        """, task_id)
        rows = cur.fetchall()

    return [
        {
            "log_id": r[0],
            "action": r[1],
            "remarks": r[2],
            "timestamp": r[3],
            "officer_name": r[4].strip() or "System"
        }
        for r in rows
    ]
