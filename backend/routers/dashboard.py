"""
routers/dashboard.py  –  Manager Overview page data
Tables used:
  TASK_MASTER          – task records and status
  TASK_LOCATION        – village/taluka per task
  dbo.auth_user        – officer names (first_name + last_name)
"""
from fastapi import APIRouter, Depends
from database import db_cursor
from models import DashboardStats, WeekPoint, WorkTypePoint, TopOfficer, RecentActivity
from auth import require_role

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(require_role("manager"))])


@router.get("/stats", response_model=DashboardStats)
def get_stats():
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'IN_PROGRESS' AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) AS overdue
            FROM TASK_MASTER
        """)
        row = cur.fetchone()

    return DashboardStats(
        total_tasks=row[0] or 0,
        completed_tasks=row[1] or 0,
        in_progress_tasks=row[2] or 0,
        overdue_tasks=row[3] or 0,
        period_label="Real-time Task Metrics",
    )


@router.get("/weekly", response_model=list[WeekPoint])
def get_weekly():
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                'Wk' + CAST(DATEPART(WEEK, start_date) AS VARCHAR) AS week_label,
                DATEPART(WEEK, start_date) AS wk_num,
                COUNT(*) AS cnt
            FROM TASK_MASTER
            GROUP BY DATEPART(WEEK, start_date)
            ORDER BY DATEPART(WEEK, start_date)
        """)
        rows = cur.fetchall()

    if not rows:
        return []
    max_cnt = max(r[2] for r in rows)
    return [
        WeekPoint(week_label=r[0], count=r[2], is_peak=(r[2] == max_cnt))
        for r in rows
    ]


@router.get("/work-types", response_model=list[WorkTypePoint])
def get_work_types():
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                ISNULL(work_type, 'Unknown') AS work_type,
                COUNT(*) AS cnt
            FROM TASK_MASTER
            GROUP BY work_type
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()

    total = sum(r[1] for r in rows) or 1
    return [
        WorkTypePoint(label=r[0], count=r[1], pct=round(r[1] / total * 100, 1))
        for r in rows
    ]


@router.get("/top-officers", response_model=list[TopOfficer])
def get_top_officers():
    with db_cursor() as cur:
        cur.execute("""
            SELECT TOP 5
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                COUNT(t.task_id) AS cnt
            FROM TASK_MASTER t
            JOIN dbo.auth_user u ON u.id = t.assigned_officer
            GROUP BY u.first_name, u.last_name
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()

    return [
        TopOfficer(rank=i + 1, name=r[0].strip() or "Unknown", tasks=r[1])
        for i, r in enumerate(rows)
    ]


@router.get("/recent-activities", response_model=list[RecentActivity])
def get_recent_activities():
    with db_cursor() as cur:
        cur.execute("""
            SELECT TOP 10
                t.task_name,
                t.work_type,
                ISNULL(l.village_code, '—') AS village,
                CONVERT(VARCHAR, t.start_date, 106) AS start_date_str,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS officer_name
            FROM TASK_MASTER t
            LEFT JOIN TASK_LOCATION l ON l.task_id = t.task_id
            LEFT JOIN dbo.auth_user u ON u.id = t.assigned_officer
            ORDER BY t.task_id DESC
        """)
        rows = cur.fetchall()

    return [
        RecentActivity(
            task=r[0] or "—",
            work_type=r[1],
            village=r[2] or "—",
            date=r[3] or "—",
            officer=r[4].strip() or "Unknown",
        )
        for r in rows
    ]


@router.get("/overdue-tasks")
def get_overdue_tasks():
    """Detailed list of overdue tasks: who, which task, how overdue."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                t.task_id,
                t.task_name,
                ISNULL(t.work_type, 'Unknown') AS work_type,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS officer_name,
                u.id AS officer_id,
                CONVERT(VARCHAR, t.start_date, 106) AS start_date,
                CONVERT(VARCHAR, t.end_date, 106) AS end_date,
                DATEDIFF(DAY, t.end_date, GETDATE()) AS days_overdue,
                t.status,
                ISNULL(l.village_code, '—') AS village,
                t.priority
            FROM TASK_MASTER t
            LEFT JOIN dbo.auth_user u ON u.id = t.assigned_officer
            LEFT JOIN TASK_LOCATION l ON l.task_id = t.task_id
            WHERE t.end_date < CAST(GETDATE() AS DATE)
              AND t.status NOT IN ('COMPLETED','CANCELLED')
            ORDER BY DATEDIFF(DAY, t.end_date, GETDATE()) DESC
        """)
        rows = cur.fetchall()

    return [
        {
            "task_id": r[0],
            "task_name": r[1] or f"Task #{r[0]}",
            "work_type": r[2],
            "officer_name": (r[3] or "").strip() or "Unassigned",
            "officer_id": r[4],
            "start_date": r[5] or "—",
            "end_date": r[6] or "—",
            "days_overdue": r[7] or 0,
            "status": r[8] or "PENDING",
            "village": r[9] or "—",
            "priority": r[10] or "Medium",
        }
        for r in rows
    ]


@router.get("/schedule-stats")
def get_schedule_stats():
    """Task counts grouped by schedule_type for dashboard cards."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                SUM(CASE WHEN ISNULL(schedule_type, 'WEEKLY') = 'DAILY'   THEN 1 ELSE 0 END) AS daily_count,
                SUM(CASE WHEN ISNULL(schedule_type, 'WEEKLY') = 'WEEKLY'  THEN 1 ELSE 0 END) AS weekly_count,
                SUM(CASE WHEN ISNULL(schedule_type, 'WEEKLY') = 'MONTHLY' THEN 1 ELSE 0 END) AS monthly_count
            FROM TASK_MASTER
            WHERE status NOT IN ('CANCELLED')
        """)
        row = cur.fetchone()

    return {
        "daily": row[0] or 0,
        "weekly": row[1] or 0,
        "monthly": row[2] or 0,
    }
