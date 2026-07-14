"""
routers/performance.py  –  Officer performance analytics
Tables: TbL_TRN_Farmer_Meeting, TASK_MASTER, TASK_LOCATION, dbo.auth_user
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from database import db_cursor
from auth import require_role

router = APIRouter(prefix="/api/performance", tags=["performance"], dependencies=[Depends(require_role("manager"))])


@router.get("/periods")
def get_periods():
    with db_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT YEAR(created_at) AS yr, MONTH(created_at) AS mo, DATENAME(MONTH, created_at) AS mon_name
            FROM TbL_TRN_Farmer_Meeting
            WHERE created_at IS NOT NULL
            ORDER BY yr DESC, mo DESC
        """)
        rows = cur.fetchall()
    return [{"year": r[0], "month": r[1], "label": f"{r[Mon_name or '']} {r[0]}"} if False else {"year": r[0], "month": r[1], "label": f"{r[2]} {r[0]}"} for r in rows]


@router.get("/ranking")
def get_ranking(year: Optional[int] = Query(default=None), month: Optional[int] = Query(default=None)):
    with db_cursor() as cur:
        # Get total meetings count first (filtered by selected month/year)
        total_sql = "SELECT COUNT(*) FROM TbL_TRN_Farmer_Meeting m WHERE 1=1"
        total_params = []
        if year:
            total_sql += " AND YEAR(m.created_at) = ?"
            total_params.append(year)
        if month:
            total_sql += " AND MONTH(m.created_at) = ?"
            total_params.append(month)
        cur.execute(total_sql, *total_params)
        total_all = cur.fetchone()[0] or 1

        # Query officers and their meeting count
        join_conds = []
        join_params = []
        if year:
            join_conds.append("YEAR(m.created_at) = ?")
            join_params.append(year)
        if month:
            join_conds.append("MONTH(m.created_at) = ?")
            join_params.append(month)
        join_sql = (" AND " + " AND ".join(join_conds)) if join_conds else ""

        query = f"""
            SELECT
                u.id AS officer_id,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name,
                COUNT(m.meeting_id) AS cnt
            FROM dbo.auth_user u
            LEFT JOIN TbL_TRN_Farmer_Meeting m ON m.employee_id = u.id {join_sql}
            WHERE u.is_active = 1
            GROUP BY u.id, u.first_name, u.last_name
            ORDER BY cnt DESC
        """
        cur.execute(query, *join_params)
        rows = cur.fetchall()

    result = []
    for r in rows:
        oid = r[0]
        cnt = r[2]
        
        # Get top work type for this officer from completed meetings (filtered by period)
        with db_cursor() as cur2:
            tw_conds = ["m.employee_id = ?"]
            tw_params = [oid]
            if year:
                tw_conds.append("YEAR(m.created_at) = ?")
                tw_params.append(year)
            if month:
                tw_conds.append("MONTH(m.created_at) = ?")
                tw_params.append(month)
            tw_sql = " AND ".join(tw_conds)

            cur2.execute(f"""
                SELECT TOP 1 ISNULL(t.work_type, 'Unknown')
                FROM TbL_TRN_Farmer_Meeting m
                JOIN TASK_MASTER t ON t.task_id = m.work_plan_id
                WHERE {tw_sql}
                GROUP BY t.work_type
                ORDER BY COUNT(*) DESC
            """, *tw_params)
            tw = cur2.fetchone()
            top_work = tw[0] if tw else "—"

            # Get last active date
            la_conds = ["employee_id = ?"]
            la_params = [oid]
            if year:
                la_conds.append("YEAR(created_at) = ?")
                la_params.append(year)
            if month:
                la_conds.append("MONTH(created_at) = ?")
                la_params.append(month)
            la_sql = " AND ".join(la_conds)

            cur2.execute(f"""
                SELECT TOP 1 CONVERT(VARCHAR, created_at, 106)
                FROM TbL_TRN_Farmer_Meeting
                WHERE {la_sql}
                ORDER BY created_at DESC
            """, *la_params)
            la = cur2.fetchone()
            last_active = la[0] if la else "—"

            # Get weekly trend (last 7 weeks or filtered by month/year)
            trend_conds = ["employee_id = ?"]
            trend_params = [oid]
            if year:
                trend_conds.append("YEAR(created_at) = ?")
                trend_params.append(year)
            if month:
                trend_conds.append("MONTH(created_at) = ?")
                trend_params.append(month)
            else:
                trend_conds.append("created_at >= DATEADD(WEEK, -7, GETDATE())")
            trend_sql = " AND ".join(trend_conds)

            cur2.execute(f"""
                SELECT
                    DATEPART(WEEK, created_at) AS wk,
                    COUNT(*) AS cnt
                FROM TbL_TRN_Farmer_Meeting
                WHERE {trend_sql}
                GROUP BY DATEPART(WEEK, created_at)
                ORDER BY DATEPART(WEEK, created_at)
            """, *trend_params)
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
def get_work_type_distribution(year: Optional[int] = Query(default=None), month: Optional[int] = Query(default=None)):
    where_parts = ["1=1"]
    params = []
    if year:
        where_parts.append("YEAR(m.created_at) = ?")
        params.append(year)
    if month:
        where_parts.append("MONTH(m.created_at) = ?")
        params.append(month)

    sql = f"""
        SELECT
            ISNULL(t.work_type, 'Unknown') AS work_type,
            COUNT(m.meeting_id) AS cnt
        FROM TbL_TRN_Farmer_Meeting m
        JOIN TASK_MASTER t ON t.task_id = m.work_plan_id
        WHERE {' AND '.join(where_parts)}
        GROUP BY t.work_type
        ORDER BY cnt DESC
    """
    with db_cursor() as cur:
        cur.execute(sql, *params)
        rows = cur.fetchall()

    total = sum(r[1] for r in rows) or 1
    return [
        {"label": r[0], "count": r[1], "pct": round(r[1] / total * 100, 1)}
        for r in rows
    ]


@router.get("/top-villages")
def get_top_villages(year: Optional[int] = Query(default=None), month: Optional[int] = Query(default=None)):
    where_parts = ["1=1"]
    params = []
    if year:
        where_parts.append("YEAR(m.created_at) = ?")
        params.append(year)
    if month:
        where_parts.append("MONTH(m.created_at) = ?")
        params.append(month)

    sql = f"""
        SELECT TOP 10
            ISNULL(v.Village_NameE, 'Unknown') AS village,
            COUNT(m.meeting_id) AS cnt
        FROM TbL_TRN_Farmer_Meeting m
        JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
        LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
        WHERE {' AND '.join(where_parts)}
        GROUP BY v.Village_NameE
        ORDER BY cnt DESC
    """
    with db_cursor() as cur:
        cur.execute(sql, *params)
        rows = cur.fetchall()
    return [{"village": r[0], "count": r[1]} for r in rows]


@router.get("/weekly")
def get_weekly_trend(year: Optional[int] = Query(default=None), month: Optional[int] = Query(default=None)):
    where_parts = ["created_at >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)"]
    params = []
    if year:
        where_parts = ["1=1"]
        where_parts.append("YEAR(created_at) = ?")
        params.append(year)
    if month:
        where_parts.append("MONTH(created_at) = ?")
        params.append(month)

    sql = f"""
        SELECT
            'Wk' + CAST(DATEPART(WEEK, created_at) AS VARCHAR) AS wk,
            COUNT(meeting_id) AS cnt
        FROM TbL_TRN_Farmer_Meeting
        WHERE {' AND '.join(where_parts)}
        GROUP BY DATEPART(WEEK, created_at)
        ORDER BY DATEPART(WEEK, created_at)
    """
    with db_cursor() as cur:
        cur.execute(sql, *params)
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
