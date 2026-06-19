"""
routers/officers.py  –  Officer management
Tables: dbo.auth_user, dbo.user_details, dbo.activities, TASK_MASTER, TASK_ACTIVITY_LOG, TASK_LOCATION, TASK_FARMER_MAPPING
"""
from fastapi import APIRouter, HTTPException
from database import db_cursor
from models import (
    OfficerOut, BlockRequest, OfficerDashboardResponse,
    OfficerDashboardProfile, OfficerDashboardStats, OfficerDashboardTask,
    OfficerDashboardActivity, OfficerDashboardAlert, OfficerDashboardInsight,
    OfficerWorkTypeStat, WorkTypePoint, WeekPoint,
)


def _build_work_type_stat(label, wid, task_count, tasks_completed, tasks_remaining,
                          farmers_total, farmers_completed, is_master=True):
    farmers_remaining = max((farmers_total or 0) - (farmers_completed or 0), 0)
    pct = round((farmers_completed / farmers_total) * 100, 1) if farmers_total else 0.0
    return OfficerWorkTypeStat(
        work_type_id=wid,
        label=label,
        task_count=task_count or 0,
        tasks_completed=tasks_completed or 0,
        tasks_remaining=tasks_remaining or 0,
        farmers_total=farmers_total or 0,
        farmers_completed=farmers_completed or 0,
        farmers_remaining=farmers_remaining,
        completion_pct=pct,
        is_master=is_master,
    )

router = APIRouter(prefix="/api/officers", tags=["officers"])


@router.get("", response_model=list[OfficerOut])
def list_officers(search: str = "", role: str = "all"):
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                u.id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                u.username,
                u.email,
                NULL AS phone,
                u.is_staff,
                ISNULL(ud.is_blocked, 0)  AS is_blocked,
                CONVERT(VARCHAR, u.date_joined, 106)    AS joined,
                CONVERT(VARCHAR, ud.last_loged_in, 106) AS last_login,
                ISNULL(act.cnt, 0) AS activities,
                ISNULL(ts.total, 0) AS total_assigned,
                ISNULL(ts.completed, 0) AS completed_tasks,
                ISNULL(ts.in_progress, 0) AS in_progress_tasks,
                ISNULL(ts.pending, 0) AS pending_tasks,
                ISNULL(ts.overdue, 0) AS overdue_tasks,
                ISNULL(fc.cnt, 0) AS farmers_assigned
            FROM dbo.auth_user u
            LEFT JOIN dbo.user_details ud ON ud.user_id = u.id
            LEFT JOIN (
                SELECT employee_id, COUNT(*) AS cnt
                FROM TbL_TRN_Farmer_Meeting
                GROUP BY employee_id
            ) act ON act.employee_id = u.id
            LEFT JOIN (
                SELECT assigned_officer,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status = 'IN_PROGRESS' AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as in_progress,
                       SUM(CASE WHEN status IN ('ASSIGNED', 'PENDING') AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as pending,
                       SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) as overdue
                FROM TASK_MASTER
                GROUP BY assigned_officer
            ) ts ON ts.assigned_officer = u.id
            LEFT JOIN (
                SELECT tm.assigned_officer, COUNT(*) AS cnt
                FROM TASK_FARMER_MAPPING tfm
                JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
                GROUP BY tm.assigned_officer
            ) fc ON fc.assigned_officer = u.id
            WHERE u.is_active = 1
              AND u.id IS NOT NULL
            ORDER BY activities DESC
        """)
        rows = cur.fetchall()

    result = []
    for r in rows:
        uid, name, uname, email, phone, is_staff, is_blocked, joined, last_login, activities, total, completed, in_progress, pending, overdue, farmers_assigned = r
        name = (name or "").strip()

        if search and search.lower() not in name.lower() and search.lower() not in (uname or "").lower():
            continue
        if role == "officer" and is_staff:
            continue
        if role == "staff" and not is_staff:
            continue

        result.append(OfficerOut(
            id=uid, name=name or uname, username=uname or "",
            email=email, phone=phone,
            is_staff=bool(is_staff), is_blocked=bool(is_blocked),
            joined=joined, last_login=last_login,
            activities=activities or 0,
            total_assigned=total,
            completed_tasks=completed,
            in_progress_tasks=in_progress,
            pending_tasks=pending,
            overdue_tasks=overdue,
            farmers_assigned=farmers_assigned
        ))
    return result


@router.get("/{officer_id}", response_model=OfficerOut)
def get_officer(officer_id: int):
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                u.id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                u.username, u.email, NULL AS phone,
                u.is_staff,
                ISNULL(ud.is_blocked, 0),
                CONVERT(VARCHAR, u.date_joined, 106),
                CONVERT(VARCHAR, ud.last_loged_in, 106),
                ISNULL(act.cnt, 0),
                ISNULL(ts.total, 0),
                ISNULL(ts.completed, 0),
                ISNULL(ts.in_progress, 0),
                ISNULL(ts.pending, 0),
                ISNULL(ts.overdue, 0),
                ISNULL(fc.cnt, 0)
            FROM dbo.auth_user u
            LEFT JOIN dbo.user_details ud ON ud.user_id = u.id
            LEFT JOIN (
                SELECT employee_id, COUNT(*) AS cnt
                FROM TbL_TRN_Farmer_Meeting
                GROUP BY employee_id
            ) act ON act.employee_id = u.id
            LEFT JOIN (
                SELECT assigned_officer,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status = 'IN_PROGRESS' AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as in_progress,
                       SUM(CASE WHEN status IN ('ASSIGNED', 'PENDING') AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as pending,
                       SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) as overdue
                FROM TASK_MASTER
                GROUP BY assigned_officer
            ) ts ON ts.assigned_officer = u.id
            LEFT JOIN (
                SELECT tm.assigned_officer, COUNT(*) AS cnt
                FROM TASK_FARMER_MAPPING tfm
                JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
                GROUP BY tm.assigned_officer
            ) fc ON fc.assigned_officer = u.id
            WHERE u.id = ?
        """, officer_id)
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Officer not found")

    uid, name, uname, email, phone, is_staff, is_blocked, joined, last_login, activities, total, completed, in_progress, pending, overdue, farmers_assigned = row
    return OfficerOut(
        id=uid, name=(name or "").strip() or uname, username=uname or "",
        email=email, phone=phone,
        is_staff=bool(is_staff), is_blocked=bool(is_blocked),
        joined=joined, last_login=last_login,
        activities=activities or 0,
        total_assigned=total,
        completed_tasks=completed,
        in_progress_tasks=in_progress,
        pending_tasks=pending,
        overdue_tasks=overdue,
        farmers_assigned=farmers_assigned
    )


@router.get("/{officer_id}/dashboard", response_model=OfficerDashboardResponse)
def get_officer_dashboard(officer_id: int):
    """Full task-based dashboard payload for manager officer profile view."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                u.id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                u.username, u.email, u.is_staff,
                ISNULL(ud.is_blocked, 0),
                CONVERT(VARCHAR, u.date_joined, 106),
                CONVERT(VARCHAR, ud.last_loged_in, 106),
                ISNULL(act.cnt, 0),
                ISNULL(ts.total, 0),
                ISNULL(ts.completed, 0),
                ISNULL(ts.in_progress, 0),
                ISNULL(ts.pending, 0),
                ISNULL(ts.overdue, 0),
                ISNULL(fc.cnt, 0),
                ISNULL(vc.cnt, 0)
            FROM dbo.auth_user u
            LEFT JOIN dbo.user_details ud ON ud.user_id = u.id
            LEFT JOIN (
                SELECT employee_id, COUNT(*) AS cnt
                FROM TbL_TRN_Farmer_Meeting
                GROUP BY employee_id
            ) act ON act.employee_id = u.id
            LEFT JOIN (
                SELECT assigned_officer,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status = 'IN_PROGRESS' AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as in_progress,
                       SUM(CASE WHEN status IN ('ASSIGNED', 'PENDING') AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as pending,
                       SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) as overdue
                FROM TASK_MASTER
                GROUP BY assigned_officer
            ) ts ON ts.assigned_officer = u.id
            LEFT JOIN (
                SELECT tm.assigned_officer, COUNT(*) AS cnt
                FROM TASK_FARMER_MAPPING tfm
                JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
                GROUP BY tm.assigned_officer
            ) fc ON fc.assigned_officer = u.id
            LEFT JOIN (
                SELECT tm.assigned_officer, COUNT(DISTINCT tl.village_code) AS cnt
                FROM TASK_MASTER tm
                JOIN TASK_LOCATION tl ON tl.task_id = tm.task_id
                WHERE tl.village_code IS NOT NULL AND tl.village_code <> ''
                GROUP BY tm.assigned_officer
            ) vc ON vc.assigned_officer = u.id
            WHERE u.id = ?
        """, officer_id)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Officer not found")

        uid, name, uname, email, is_staff, is_blocked, joined, last_login, act_count, total, completed, in_progress, pending, overdue, farmers, villages = row
        name = (name or "").strip() or uname or "Unknown"
        initials = "".join(p[0].upper() for p in name.split()[:2]) or "?"

        cur.execute("""
            SELECT STUFF((
                SELECT TOP 3 ', ' + ISNULL(tl.village_code, '')
                FROM TASK_MASTER tm
                JOIN TASK_LOCATION tl ON tl.task_id = tm.task_id
                WHERE tm.assigned_officer = ? AND tl.village_code IS NOT NULL
                GROUP BY tl.village_code
                ORDER BY COUNT(*) DESC
                FOR XML PATH(''), TYPE
            ).value('.', 'NVARCHAR(MAX)'), 1, 2, '')
        """, officer_id)
        region_row = cur.fetchone()
        region = region_row[0] if region_row and region_row[0] else "—"

        completion_score = round((completed or 0) / total * 100) if total else 0

        cur.execute("""
            SELECT
                ISNULL(work_type, 'Unknown') AS work_type,
                COUNT(*) AS cnt
            FROM TASK_MASTER
            WHERE assigned_officer = ?
            GROUP BY work_type
            ORDER BY cnt DESC
        """, officer_id)
        wt_rows = cur.fetchall()
        wt_total = sum(r[1] for r in wt_rows) or 1
        work_types = [
            WorkTypePoint(label=r[0], count=r[1], pct=round(r[1] / wt_total * 100, 1))
            for r in wt_rows
        ]

        cur.execute("""
            SELECT
                tm.work_type,
                COUNT(DISTINCT tm.task_id) AS task_count,
                COUNT(DISTINCT CASE WHEN tm.status = 'COMPLETED' THEN tm.task_id END) AS tasks_completed,
                COUNT(DISTINCT CASE WHEN tm.status NOT IN ('COMPLETED', 'CANCELLED') THEN tm.task_id END) AS tasks_remaining,
                COUNT(tfm.id) AS farmers_total,
                SUM(CASE WHEN tfm.status = 'COMPLETED' THEN 1 ELSE 0 END) AS farmers_completed
            FROM TASK_MASTER tm
            LEFT JOIN TASK_FARMER_MAPPING tfm ON tfm.task_id = tm.task_id
            WHERE tm.assigned_officer = ? AND tm.status <> 'CANCELLED'
            GROUP BY tm.work_type
        """, officer_id)
        agg_rows = {r[0]: r[1:] for r in cur.fetchall()}

        cur.execute("""
            SELECT work_type_id, work_type_name
            FROM dbo.TBL_MST_DAILY_WORKTYPE
            ORDER BY work_type_name
        """)
        master_rows = cur.fetchall()
        master_names = {r[1] for r in master_rows}

        work_type_stats = []
        for wid, wname in master_rows:
            stats = agg_rows.get(wname, (0, 0, 0, 0, 0))
            work_type_stats.append(_build_work_type_stat(
                wname, wid, stats[0], stats[1], stats[2], stats[3], stats[4], True
            ))

        for wname, stats in agg_rows.items():
            if wname not in master_names:
                work_type_stats.append(_build_work_type_stat(
                    wname, None, stats[0], stats[1], stats[2], stats[3], stats[4], False
                ))

        cur.execute("""
            SELECT
                'Wk' + CAST(DATEPART(WEEK, created_at) AS VARCHAR) AS week_label,
                COUNT(*) AS cnt
            FROM TASK_MASTER
            WHERE assigned_officer = ?
            GROUP BY DATEPART(WEEK, created_at)
            ORDER BY DATEPART(WEEK, created_at)
        """, officer_id)
        wk_rows = cur.fetchall()
        max_wk = max((r[1] for r in wk_rows), default=0)
        weekly = [
            WeekPoint(week_label=r[0], count=r[1], is_peak=(r[1] == max_wk and max_wk > 0))
            for r in wk_rows
        ]

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
                MONTH(t.start_date),
                DATEPART(week, t.start_date) - DATEPART(week, DATEADD(month, DATEDIFF(month, 0, t.start_date), 0)) + 1
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
        """, officer_id)
        task_rows = cur.fetchall()
        tasks = []
        for r in task_rows:
            total_f = r[7] or 0
            done_f = r[8] or 0
            pct = round(done_f / total_f * 100) if total_f else 0
            tasks.append(OfficerDashboardTask(
                task_id=r[0], task_name=r[1] or f"Task #{r[0]}",
                work_type=r[2] or "—", status=r[3] or "ASSIGNED",
                start_date=r[4] or "", end_date=r[5] or "",
                village=r[6], farmer_count=total_f, completion_pct=pct,
                month=r[9], week=r[10],
            ))

        cur.execute("""
            SELECT TOP 20
                al.log_id,
                tm.task_name,
                tm.work_type,
                ISNULL(tl.village_code, '—') AS village,
                al.action,
                CONVERT(VARCHAR, al.timestamp, 106) AS act_date,
                al.remarks,
                al.timestamp
            FROM TASK_ACTIVITY_LOG al
            JOIN TASK_MASTER tm ON tm.task_id = al.task_id
            LEFT JOIN TASK_LOCATION tl ON tl.task_id = tm.task_id
            WHERE tm.assigned_officer = ?
            ORDER BY al.timestamp DESC
        """, officer_id)
        act_rows = cur.fetchall()
        activities = [
            OfficerDashboardActivity(
                id=r[0], task_name=r[1] or "—", work_type=r[2] or "—",
                village=r[3], action=r[4] or "—", date=r[5] or "—",
                remarks=r[6],
            )
            for r in act_rows
        ]

        day_activity = [0] * 7
        for r in act_rows:
            if r[7]:
                dow = r[7].weekday()
                day_activity[dow] += 1

    alerts = []
    if is_blocked:
        alerts.append(OfficerDashboardAlert(type="alert", message="This officer account is currently blocked."))
    if overdue:
        alerts.append(OfficerDashboardAlert(type="warning", message=f"{overdue} task(s) are overdue and need attention."))
    if pending:
        alerts.append(OfficerDashboardAlert(type="info", message=f"{pending} task(s) are pending assignment follow-up."))
    if not total:
        alerts.append(OfficerDashboardAlert(type="info", message="No tasks assigned to this officer yet."))

    insights = []
    if total:
        insights.append(OfficerDashboardInsight(
            content=f"Task completion rate is {completion_score}% ({completed} of {total} tasks completed)."
        ))
    if work_types:
        insights.append(OfficerDashboardInsight(
            content=f"Most assigned work type: {work_types[0].label} ({work_types[0].count} tasks)."
        ))
    if overdue:
        insights.append(OfficerDashboardInsight(
            content=f"{overdue} overdue task(s) — review deadlines on the task board below."
        ))
    if farmers:
        insights.append(OfficerDashboardInsight(
            content=f"Managing {farmers} farmer mapping(s) across {villages or 0} village(s)."
        ))

    status = "Blocked" if is_blocked else "Active"
    role = "Staff / Manager" if is_staff else "Field Officer"

    return OfficerDashboardResponse(
        profile=OfficerDashboardProfile(
            id=uid, name=name, username=uname or "",
            email=email, role=role, status=status, initials=initials,
            joined=joined, last_login=last_login, region=region,
            is_blocked=bool(is_blocked),
        ),
        stats=OfficerDashboardStats(
            total_tasks=total or 0,
            completed_tasks=completed or 0,
            in_progress_tasks=in_progress or 0,
            pending_tasks=pending or 0,
            overdue_tasks=overdue or 0,
            farmers_assigned=farmers or 0,
            villages_count=villages or 0,
            activities_count=act_count or 0,
            completion_score=completion_score,
        ),
        work_type_stats=work_type_stats,
        work_types=work_types,
        weekly=weekly,
        tasks=tasks,
        activities=activities,
        alerts=alerts,
        insights=insights,
        day_activity=day_activity,
    )


@router.put("/{officer_id}/block")
def toggle_block(officer_id: int, body: BlockRequest):
    with db_cursor() as cur:
        cur.execute(
            "UPDATE dbo.user_details SET is_blocked = ? WHERE user_id = ?",
            int(body.is_blocked), officer_id
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Officer not found")
    return {"ok": True, "is_blocked": body.is_blocked}


@router.get("/{officer_id}/tasks")
def get_officer_tasks(officer_id: int):
    """Get active tasks assigned to an officer from TASK_MASTER."""
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
                CONVERT(VARCHAR, t.start_date, 106) AS start_date,
                CONVERT(VARCHAR, t.end_date, 106) AS end_date,
                ISNULL(l.village_code, 'Unknown') AS village,
                (SELECT COUNT(*) FROM TASK_FARMER_MAPPING WHERE task_id = t.task_id) AS farmer_count
            FROM TASK_MASTER t
            LEFT JOIN TASK_LOCATION l ON l.task_id = t.task_id
            WHERE t.assigned_officer = ? AND t.status NOT IN ('COMPLETED', 'CANCELLED')
            ORDER BY t.created_at DESC
        """, officer_id)
        rows = cur.fetchall()

    return [
        {
            "task_id": r[0],
            "task_name": r[1],
            "work_type": r[2],
            "status": r[3],
            "start_date": r[4],
            "end_date": r[5],
            "village": r[6],
            "farmer_count": r[7]
        }
        for r in rows
    ]


@router.get("/{officer_id}/activities")
def get_officer_activities(officer_id: int):
    """Get activity history from TASK_ACTIVITY_LOG."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT TOP 20
                al.log_id,
                tm.task_name,
                tm.work_type,
                ISNULL(tl.village_code, 'Unknown') AS village,
                al.action,
                CONVERT(VARCHAR, al.timestamp, 106) AS act_date,
                al.remarks
            FROM TASK_ACTIVITY_LOG al
            JOIN TASK_MASTER tm ON tm.task_id = al.task_id
            LEFT JOIN TASK_LOCATION tl ON tl.task_id = tm.task_id
            WHERE al.officer = ?
            ORDER BY al.timestamp DESC
        """, officer_id)
        rows = cur.fetchall()

    return [
        {"id": r[0], "task_name": r[1], "work_type": r[2],
         "village": r[3], "action": r[4], "date": r[5], "remarks": r[6]}
        for r in rows
    ]


@router.get("/{officer_id}/meeting-kpis")
def get_officer_meeting_kpis(officer_id: int):
    """
    Aggregated meeting KPI data for an officer from TbL_TRN_Farmer_Meeting.
    Shows compliance rates and recent meeting list with all fields.
    """
    with db_cursor() as cur:
        # Aggregated KPI counts
        cur.execute("""
            SELECT
                COUNT(*) AS total_meetings,
                SUM(CASE WHEN kcc = 1 THEN 1 ELSE 0 END) AS kcc_yes,
                SUM(CASE WHEN kcc = 0 THEN 1 ELSE 0 END) AS kcc_no,
                SUM(CASE WHEN canara_hnt = 1 THEN 1 ELSE 0 END) AS canara_yes,
                SUM(CASE WHEN canara_hnt = 0 THEN 1 ELSE 0 END) AS canara_no,
                SUM(CASE WHEN sangola_hnt = 1 THEN 1 ELSE 0 END) AS sangola_yes,
                SUM(CASE WHEN sangola_hnt = 0 THEN 1 ELSE 0 END) AS sangola_no,
                SUM(CASE WHEN cane_registration = 1 THEN 1 ELSE 0 END) AS cane_reg_yes,
                SUM(CASE WHEN cane_registration = 0 THEN 1 ELSE 0 END) AS cane_reg_no,
                SUM(CASE WHEN recovery = 1 THEN 1 ELSE 0 END) AS recovery_yes,
                SUM(CASE WHEN recovery = 0 THEN 1 ELSE 0 END) AS recovery_no,
                SUM(CASE WHEN vehicle_agreement = 1 THEN 1 ELSE 0 END) AS vehicle_yes,
                SUM(CASE WHEN vehicle_agreement = 0 THEN 1 ELSE 0 END) AS vehicle_no,
                AVG(CAST(expected_tonnage AS FLOAT)) AS avg_tonnage
            FROM TbL_TRN_Farmer_Meeting
            WHERE employee_id = ?
        """, officer_id)
        agg = cur.fetchone()

        total = agg[0] or 0

        # Recent meetings with farmer details
        cur.execute("""
            SELECT TOP 20
                fm.meeting_id,
                fm.farmer_code,
                ISNULL(m.NameE, 'Unknown') AS farmer_name,
                ISNULL(v.Village_NameE, '') AS village,
                fm.kcc, fm.kcc_reason,
                fm.canara_hnt, fm.canara_reason,
                fm.sangola_hnt, fm.sangola_reason,
                fm.cane_registration, fm.cane_registration_remark,
                fm.recovery, fm.recovery_reason,
                fm.vehicle_agreement, fm.vehicle_reason,
                fm.expected_tonnage,
                fm.cane_development,
                fm.feedback,
                fm.remark,
                CONVERT(VARCHAR, fm.created_at, 106) AS meeting_date
            FROM TbL_TRN_Farmer_Meeting fm
            LEFT JOIN dbo.TBL_MST_MASTER m ON m.code = fm.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
            WHERE fm.employee_id = ?
            ORDER BY fm.created_at DESC
        """, officer_id)
        recent_rows = cur.fetchall()

    def pct(yes_count):
        return round(yes_count / total * 100, 1) if total else 0

    kpis = {
        "total_meetings": total,
        "kcc": {"yes": agg[1] or 0, "no": agg[2] or 0, "pct": pct(agg[1] or 0)},
        "canara_hnt": {"yes": agg[3] or 0, "no": agg[4] or 0, "pct": pct(agg[3] or 0)},
        "sangola_hnt": {"yes": agg[5] or 0, "no": agg[6] or 0, "pct": pct(agg[5] or 0)},
        "cane_registration": {"yes": agg[7] or 0, "no": agg[8] or 0, "pct": pct(agg[7] or 0)},
        "recovery": {"yes": agg[9] or 0, "no": agg[10] or 0, "pct": pct(agg[9] or 0)},
        "vehicle_agreement": {"yes": agg[11] or 0, "no": agg[12] or 0, "pct": pct(agg[11] or 0)},
        "avg_tonnage": round(float(agg[13]), 1) if agg[13] else 0,
    }

    recent_meetings = []
    for r in recent_rows:
        recent_meetings.append({
            "meeting_id": r[0],
            "farmer_code": r[1],
            "farmer_name": r[2],
            "village": r[3],
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
            "expected_tonnage": float(r[16]) if r[16] is not None else 0,
            "cane_development": r[17] or "",
            "feedback": r[18] or "",
            "remark": r[19] or "",
            "meeting_date": r[20] or "",
        })

    return {"kpis": kpis, "recent_meetings": recent_meetings}
