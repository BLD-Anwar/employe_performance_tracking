"""
routers/performance.py  –  Officer performance analytics
Tables: TbL_TRN_Farmer_Meeting, TASK_MASTER, TASK_LOCATION, dbo.auth_user
"""
from fastapi import APIRouter
from database import db_cursor

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/ranking")
def get_ranking():
    with db_cursor() as cur:
        # Get total meetings count first
        cur.execute("SELECT COUNT(*) FROM TbL_TRN_Farmer_Meeting")
        total_all = cur.fetchone()[0] or 1

        # Query officers and their meeting count
        cur.execute("""
            SELECT
                u.id AS officer_id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                COUNT(m.meeting_id) AS cnt
            FROM dbo.auth_user u
            LEFT JOIN TbL_TRN_Farmer_Meeting m ON m.employee_id = u.id
            WHERE u.is_active = 1
            GROUP BY u.id, u.first_name, u.last_name
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()

    result = []
    for r in rows:
        oid = r[0]
        cnt = r[2]
        
        # Get top work type for this officer from completed meetings
        with db_cursor() as cur2:
            cur2.execute("""
                SELECT TOP 1 ISNULL(t.work_type, 'Unknown')
                FROM TbL_TRN_Farmer_Meeting m
                JOIN TASK_MASTER t ON t.task_id = m.work_plan_id
                WHERE m.employee_id = ?
                GROUP BY t.work_type
                ORDER BY COUNT(*) DESC
            """, oid)
            tw = cur2.fetchone()
            top_work = tw[0] if tw else "—"

            # Get last active date
            cur2.execute("""
                SELECT TOP 1 CONVERT(VARCHAR, created_at, 106)
                FROM TbL_TRN_Farmer_Meeting
                WHERE employee_id = ?
                ORDER BY created_at DESC
            """, oid)
            la = cur2.fetchone()
            last_active = la[0] if la else "—"

            # Get weekly trend (last 7 weeks based on created_at)
            cur2.execute("""
                SELECT
                    DATEPART(WEEK, created_at) AS wk,
                    COUNT(*) AS cnt
                FROM TbL_TRN_Farmer_Meeting
                WHERE employee_id = ?
                  AND created_at >= DATEADD(WEEK, -7, GETDATE())
                GROUP BY DATEPART(WEEK, created_at)
                ORDER BY DATEPART(WEEK, created_at)
            """, oid)
            trend_rows = cur2.fetchall()
            trend = [tr[1] for tr in trend_rows] if trend_rows else [0]

        result.append({
            "rank": len(result) + 1,
            "name": (r[1] or "").strip() or "Unknown",
            "activities": cnt,
            "pct": round(cnt / total_all * 100, 1),
            "top": top_work,
            "last": last_active,
            "trend": trend,
        })

    return result


@router.get("/work-types")
def get_work_type_distribution():
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                ISNULL(t.work_type, 'Unknown') AS work_type,
                COUNT(m.meeting_id) AS cnt
            FROM TbL_TRN_Farmer_Meeting m
            JOIN TASK_MASTER t ON t.task_id = m.work_plan_id
            GROUP BY t.work_type
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()

    total = sum(r[1] for r in rows) or 1
    return [
        {"label": r[0], "count": r[1], "pct": round(r[1] / total * 100, 1)}
        for r in rows
    ]


@router.get("/top-villages")
def get_top_villages():
    with db_cursor() as cur:
        cur.execute("""
            SELECT TOP 10
                ISNULL(v.Village_NameE, 'Unknown') AS village,
                COUNT(m.meeting_id) AS cnt
            FROM TbL_TRN_Farmer_Meeting m
            JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            GROUP BY v.Village_NameE
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()
    return [{"village": r[0], "count": r[1]} for r in rows]


@router.get("/weekly")
def get_weekly_trend():
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                'Wk' + CAST(DATEPART(WEEK, created_at) AS VARCHAR) AS wk,
                COUNT(meeting_id) AS cnt
            FROM TbL_TRN_Farmer_Meeting
            WHERE created_at >= '2026-01-01'
            GROUP BY DATEPART(WEEK, created_at)
            ORDER BY DATEPART(WEEK, created_at)
        """)
        rows = cur.fetchall()

    if not rows:
        return []
    mx = max(r[1] for r in rows)
    return [
        {"week_label": r[0], "count": r[1], "is_peak": r[1] == mx}
        for r in rows
    ]


@router.get("/officer/{officer_id}")
def get_officer_performance(officer_id: int):
    """Detailed performance for a single officer."""
    with db_cursor() as cur:
        # Activity count by work type
        cur.execute("""
            SELECT
                ISNULL(t.work_type, 'Unknown') AS work_type,
                COUNT(m.meeting_id) AS cnt
            FROM TbL_TRN_Farmer_Meeting m
            JOIN TASK_MASTER t ON t.task_id = m.work_plan_id
            WHERE m.employee_id = ?
            GROUP BY t.work_type
            ORDER BY cnt DESC
        """, officer_id)
        work_types = [{"label": r[0], "count": r[1]} for r in cur.fetchall()]

        # Monthly trend
        cur.execute("""
            SELECT
                DATENAME(MONTH, m.created_at) AS month_name,
                COUNT(m.meeting_id) AS cnt
            FROM TbL_TRN_Farmer_Meeting m
            WHERE m.employee_id = ?
            GROUP BY DATENAME(MONTH, m.created_at), MONTH(m.created_at)
            ORDER BY MONTH(m.created_at)
        """, officer_id)
        monthly = [{"month": r[0], "count": r[1]} for r in cur.fetchall()]

    return {"work_types": work_types, "monthly": monthly}
