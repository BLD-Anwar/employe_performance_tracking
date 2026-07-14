"""
routers/reports.py  –  Activity log and CSV export
Tables: dbo.activities, dbo.auth_user, dbo.purpose_of_work
"""
import csv, io, math, os, logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse
from database import db_cursor
from auth import require_role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(require_role("manager"))])
def _build_where(search, work_type, officer, date_from, date_to):
    parts = ["1=1"]
    params = []

    if search:
        parts.append("(f.NameE LIKE ? OR v.Village_NameE LIKE ? OR tl.Taluka_NameE LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if work_type:
        parts.append("tm.work_type = ?")
        params.append(work_type)
    if officer:
        parts.append("(ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'')) LIKE ?")
        params.append(f"%{officer}%")
    if date_from:
        parts.append("CAST(m.created_at AS DATE) >= ?")
        params.append(date_from)
    if date_to:
        parts.append("CAST(m.created_at AS DATE) <= ?")
        params.append(date_to)

    return " AND ".join(parts), params


@router.get("/activities")
def get_activity_log(
    search:    str = Query(default=""),
    work_type: str = Query(default=""),
    officer:   str = Query(default=""),
    date_from: str = Query(default=""),
    date_to:   str = Query(default=""),
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=200),
):
    where_sql, params = _build_where(search, work_type, officer, date_from, date_to)

    with db_cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM TbL_TRN_Farmer_Meeting m
            LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            LEFT JOIN dbo.TBl_mst_taluka tl ON tl.Taluka_Code = f.Talula_Code
            LEFT JOIN TASK_MASTER tm ON tm.task_id = m.work_plan_id
            LEFT JOIN dbo.auth_user u ON u.id = m.employee_id
            WHERE {where_sql}
            """, *params
        )
        total = cur.fetchone()[0]

        offset = (page - 1) * page_size
        cur.execute(
            f"""
            SELECT
                CONVERT(VARCHAR, m.created_at, 106) AS act_date,
                ISNULL(f.NameE, '—')          AS farmer,
                ISNULL(tm.work_type, 'Unknown')            AS work_type,
                ISNULL(v.Village_NameE, '—')               AS village,
                ISNULL(tl.Taluka_NameE, '—')                  AS city,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS officer
            FROM TbL_TRN_Farmer_Meeting m
            LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            LEFT JOIN dbo.TBl_mst_taluka tl ON tl.Taluka_Code = f.Talula_Code
            LEFT JOIN TASK_MASTER tm ON tm.task_id = m.work_plan_id
            LEFT JOIN dbo.auth_user u ON u.id = m.employee_id
            WHERE {where_sql}
            ORDER BY m.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """, *params, offset, page_size
        )
        rows = cur.fetchall()

    items = [
        {"date": r[0], "farmer": r[1], "work_type": r[2],
          "village": r[3], "city": r[4], "officer": (r[5] or "").strip()}
        for r in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": math.ceil(total / page_size) if total else 1,
    }


@router.get("/activities/download")
def download_activity_log(
    search:    str = Query(default=""),
    work_type: str = Query(default=""),
    officer:   str = Query(default=""),
    date_from: str = Query(default=""),
    date_to:   str = Query(default=""),
):
    where_sql, params = _build_where(search, work_type, officer, date_from, date_to)

    with db_cursor() as cur:
        cur.execute(
            f"""
            SELECT
                CONVERT(VARCHAR, m.created_at, 106),
                ISNULL(f.NameE,'—'),
                ISNULL(tm.work_type,'Unknown'),
                ISNULL(v.Village_NameE,'—'),
                ISNULL(tl.Taluka_NameE,'—'),
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'')
            FROM TbL_TRN_Farmer_Meeting m
            LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            LEFT JOIN dbo.TBl_mst_taluka tl ON tl.Taluka_Code = f.Talula_Code
            LEFT JOIN TASK_MASTER tm ON tm.task_id = m.work_plan_id
            LEFT JOIN dbo.auth_user u ON u.id = m.employee_id
            WHERE {where_sql}
            ORDER BY m.created_at DESC
            """, *params
        )
        rows = cur.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Farmer", "Work Type", "Village", "City", "Officer"])
    for r in rows:
        writer.writerow([r[0], r[1], r[2], r[3], r[4], (r[5] or "").strip()])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_log.csv"},
    )


@router.get("/officers-for-filter")
def get_officers_for_filter():
    with db_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS full_name
            FROM TbL_TRN_Farmer_Meeting m
            JOIN dbo.auth_user u ON u.id = m.employee_id
            ORDER BY full_name
        """)
        return [r[0].strip() for r in cur.fetchall() if r[0] and r[0].strip()]


@router.get("/work-types-for-filter")
def get_work_types_for_filter():
    with db_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT tm.work_type
            FROM TbL_TRN_Farmer_Meeting m
            JOIN TASK_MASTER tm ON tm.task_id = m.work_plan_id
            ORDER BY tm.work_type
        """)
        return [r[0] for r in cur.fetchall() if r[0]]


@router.get("/summary")
def get_summary(year: Optional[int] = Query(default=None), month: Optional[int] = Query(default=None)):
    """High-level summary stats for the reports page."""
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
            COUNT(m.meeting_id)                    AS total,
            COUNT(DISTINCT m.employee_id)          AS officers,
            COUNT(DISTINCT f.Village_code)         AS villages,
            COUNT(DISTINCT CAST(m.created_at AS DATE)) AS active_days
        FROM TbL_TRN_Farmer_Meeting m
        LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
        WHERE {' AND '.join(where_parts)}
    """
    with db_cursor() as cur:
        cur.execute(sql, *params)
        r = cur.fetchone()
    return {
        "total_activities": r[0] or 0,
        "active_officers": r[1] or 0,
        "villages_covered": r[2] or 0,
        "active_days": r[3] or 1,
    }


@router.post("/generate-task-report")
def generate_task_report_endpoint(task_id: int = Query(...), manager_id: int = Query(default=1)):
    """Generate a task performance report with CSV file and DB snapshot."""
    try:
        from utils.report_generator import generate_task_report
        report_id = generate_task_report(task_id, manager_id)
        if report_id is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return {"success": True, "report_id": report_id, "message": f"Report generated for task {task_id}"}
    except Exception as e:
        log.error("Report generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Report generation failed. Please try again.")


@router.post("/generate-all")
def generate_all_reports(manager_id: int = Query(default=1)):
    """Scan and generate reports for all eligible tasks."""
    try:
        from utils.report_generator import check_and_generate_eligible_reports
        check_and_generate_eligible_reports(manager_id)
        return {"success": True, "message": "Eligible reports generated"}
    except Exception as e:
        log.error("Report generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Report generation failed. Please try again.")


@router.get("/archive")
def get_report_archive():
    """List ALL tasks with report data where available.
    Tasks without a generated report (e.g. IN_PROGRESS) still appear
    with live status and farmer count from TASK_MASTER directly.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                rm.report_id,
                tm.task_id,
                ISNULL(rm.report_type, tm.schedule_type),
                ISNULL(CONVERT(VARCHAR, rm.generated_date, 106), CONVERT(VARCHAR, tm.created_at, 106)) AS generated_date,
                ISNULL(rm.status, 'PENDING'),
                rm.file_path,
                ISNULL(rd.farmer_count,   (SELECT COUNT(*) FROM TASK_FARMER_MAPPING WHERE task_id = tm.task_id)),
                ISNULL(rd.village_count,  0),
                ISNULL(rd.completion_rate, 0),
                CASE
                    WHEN tm.end_date < CAST(GETDATE() AS DATE)
                         AND tm.status NOT IN ('COMPLETED','CANCELLED') THEN 'OVERDUE'
                    ELSE tm.status
                END AS task_status,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS officer_name,
                tm.task_name,
                rd.performance_grade,
                rd.calculated_score,
                rd.officer_rank,
                rd.total_officers,
                rd.kcc_pct,
                rd.canara_pct,
                rd.sangola_pct,
                rd.cane_reg_pct,
                rd.recovery_pct,
                rd.vehicle_pct,
                rd.meetings_coverage_pct,
                rd.prev_score,
                rd.score_trend,
                rd.missed_farmers_json,
                ISNULL(tm.schedule_type, 'WEEKLY'),
                rd.officer_id
            FROM TASK_MASTER tm
            LEFT JOIN REPORT_MASTER rm ON rm.task_id = tm.task_id
            LEFT JOIN REPORT_DETAILS rd ON rd.report_id = rm.report_id
            LEFT JOIN dbo.auth_user u ON u.id = tm.assigned_officer
            WHERE tm.status NOT IN ('CANCELLED')
            ORDER BY tm.created_at DESC
        """)
        rows = cur.fetchall()

    import json as _json
    results = []
    for r in rows:
        missed = []
        if r[25]:
            try:
                missed = _json.loads(r[25])
            except:
                pass
        results.append({
            "report_id": r[0],
            "task_id": r[1],
            "report_type": r[2],
            "generated_date": r[3],
            "status": r[4],
            "file_path": r[5],
            "farmer_count": r[6],
            "village_count": r[7],
            "completion_rate": float(r[8]) if r[8] else 0,
            "task_status": r[9],
            "officer_name": (r[10] or '').strip() or 'Unknown',
            "task_name": r[11] or f'Task #{r[1]}',
            "performance_grade": r[12] or "—",
            "calculated_score": float(r[13]) if r[13] is not None else 0,
            "officer_rank": r[14] or 0,
            "total_officers": r[15] or 0,
            "kcc_pct": float(r[16]) if r[16] is not None else 0,
            "canara_pct": float(r[17]) if r[17] is not None else 0,
            "sangola_pct": float(r[18]) if r[18] is not None else 0,
            "cane_reg_pct": float(r[19]) if r[19] is not None else 0,
            "recovery_pct": float(r[20]) if r[20] is not None else 0,
            "vehicle_pct": float(r[21]) if r[21] is not None else 0,
            "meetings_coverage_pct": float(r[22]) if r[22] is not None else 0,
            "prev_score": float(r[23]) if r[23] is not None else None,
            "score_trend": float(r[24]) if r[24] is not None else None,
            "missed_farmers": missed,
            "schedule_type": r[26] or "WEEKLY",
            "officer_id": r[27],
        })
    return results


@router.get("/my-reports/{user_id}")
def get_my_reports(user_id: int):
    """Get reports for a specific officer (employee self-service)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT 
                rm.report_id,
                rm.task_id,
                rm.report_type,
                CONVERT(VARCHAR, rm.generated_date, 106) AS generated_date,
                rm.status,
                ISNULL(rd.farmer_count, 0),
                ISNULL(rd.village_count, 0),
                ISNULL(rd.completion_rate, 0),
                ISNULL(rd.task_status, ''),
                tm.task_name,
                rd.performance_grade,
                rd.calculated_score,
                rd.officer_rank,
                rd.total_officers,
                rd.kcc_pct,
                rd.canara_pct,
                rd.sangola_pct,
                rd.cane_reg_pct,
                rd.recovery_pct,
                rd.vehicle_pct,
                rd.meetings_coverage_pct,
                rd.prev_score,
                rd.score_trend,
                rd.missed_farmers_json,
                ISNULL(tm.schedule_type, 'WEEKLY')
            FROM REPORT_MASTER rm
            JOIN REPORT_DETAILS rd ON rd.report_id = rm.report_id
            LEFT JOIN TASK_MASTER tm ON tm.task_id = rm.task_id
            WHERE rd.officer_id = ?
            ORDER BY rm.generated_date DESC
        """, user_id)
        rows = cur.fetchall()

    import json as _json
    results = []
    for r in rows:
        missed = []
        if r[23]:
            try:
                missed = _json.loads(r[23])
            except:
                pass
        results.append({
            "report_id": r[0],
            "task_id": r[1],
            "report_type": r[2],
            "generated_date": r[3],
            "status": r[4],
            "farmer_count": r[5],
            "village_count": r[6],
            "completion_rate": float(r[7]) if r[7] else 0,
            "task_status": r[8],
            "task_name": r[9] or f'Task #{r[1]}',
            "performance_grade": r[10] or "—",
            "calculated_score": float(r[11]) if r[11] is not None else 0,
            "officer_rank": r[12] or 0,
            "total_officers": r[13] or 0,
            "kcc_pct": float(r[14]) if r[14] is not None else 0,
            "canara_pct": float(r[15]) if r[15] is not None else 0,
            "sangola_pct": float(r[16]) if r[16] is not None else 0,
            "cane_reg_pct": float(r[17]) if r[17] is not None else 0,
            "recovery_pct": float(r[18]) if r[18] is not None else 0,
            "vehicle_pct": float(r[19]) if r[19] is not None else 0,
            "meetings_coverage_pct": float(r[20]) if r[20] is not None else 0,
            "prev_score": float(r[21]) if r[21] is not None else None,
            "score_trend": float(r[22]) if r[22] is not None else None,
            "missed_farmers": missed,
            "schedule_type": r[24] or "WEEKLY",
        })
    return results


@router.get("/officer-ranking")
def get_officer_ranking():
    """Get all officers ranked by performance score for the leaderboard."""
    from utils.report_generator import compute_officer_rankings, compute_grade
    rankings = compute_officer_rankings()

    if not rankings:
        return []

    # Enrich with officer names
    officer_ids = list(rankings.keys())
    results = []
    with db_cursor() as cur:
        for oid in officer_ids:
            cur.execute("""
                SELECT ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS name,
                       u.username
                FROM dbo.auth_user u WHERE u.id = ?
            """, oid)
            row = cur.fetchone()
            name = (row[0] or "").strip() if row else "Unknown"
            username = row[1] if row else ""
            info = rankings[oid]
            score = info["score"]
            results.append({
                "officer_id": oid,
                "name": name or username,
                "username": username,
                "rank": info["rank"],
                "total_officers": info["total"],
                "score": score,
                "grade": compute_grade(score),
            })

    results.sort(key=lambda x: x["rank"])
    return results


@router.get("/archive/count")
def get_report_count():
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM REPORT_MASTER")
        count = cur.fetchone()[0]
    return {"count": count or 0}


@router.get("/download-file")
def download_report_file(report_id: int = Query(...)):
    with db_cursor() as cur:
        cur.execute("SELECT file_path, task_id FROM REPORT_MASTER WHERE report_id = ?", report_id)
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    file_path = row[0]
    task_id = row[1]

    # Try to serve existing file first
    if file_path:
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        full_path = os.path.join(reports_dir, file_path.replace('/', os.sep))
        if os.path.isfile(full_path):
            ext = os.path.splitext(full_path)[1].lower()
            if ext == ".xlsx":
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                media_type = "text/csv"
            return FileResponse(full_path, media_type=media_type, filename=os.path.basename(full_path))

    # File not on disk — generate Excel on-the-fly from snapshot
    with db_cursor() as cur:
        cur.execute("SELECT generated_snapshot_json FROM REPORT_DETAILS WHERE report_id = ?", report_id)
        det_row = cur.fetchone()
        
    if not det_row or not det_row[0]:
        raise HTTPException(status_code=404, detail="Report snapshot not found to generate Excel")
        
    import json
    snap = json.loads(det_row[0])
    
    from utils.report_generator import build_excel_report
    
    officer_id = None
    with db_cursor() as cur:
        cur.execute("SELECT assigned_officer FROM TASK_MASTER WHERE task_id = ?", task_id)
        trow = cur.fetchone()
        if trow:
            officer_id = trow[0]
            
    meeting_rows = []
    if officer_id:
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    tfm.farmer_id,
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
                    CONVERT(VARCHAR, fm.created_at, 106) AS meeting_date,
                    fm.is_working_vehicle, fm.vehicle_working_reason
                FROM TASK_FARMER_MAPPING tfm
                LEFT JOIN dbo.TBL_MST_MASTER m ON m.code = tfm.farmer_id
                LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
                LEFT JOIN TbL_TRN_Farmer_Meeting fm ON fm.farmer_code = tfm.farmer_id
                    AND fm.employee_id = ? AND fm.work_plan_id = ?
                WHERE tfm.task_id = ?
            """, officer_id, task_id, task_id)
            meeting_rows = cur.fetchall()
            
    with db_cursor() as cur:
        cur.execute("""
            SELECT 
                CONVERT(VARCHAR, al.timestamp, 120) AS timestamp_str,
                al.action,
                al.remarks,
                ISNULL(u.first_name,'') + ' ' + ISNULL(u.last_name,'') AS officer_name
            FROM TASK_ACTIVITY_LOG al
            LEFT JOIN dbo.auth_user u ON u.id = al.officer
            WHERE al.task_id = ?
            ORDER BY al.timestamp DESC
        """, task_id)
        history_rows = cur.fetchall()
        
    wb = build_excel_report(snap, meeting_rows, history_rows)
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"task_{task_id}_report.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/task-stats")
def get_task_stats():
    with db_cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'IN_PROGRESS' AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status IN ('ASSIGNED','PENDING') AND NOT (end_date < CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN end_date < CAST(GETDATE() AS DATE) AND status NOT IN ('COMPLETED','CANCELLED') THEN 1 ELSE 0 END) as overdue
            FROM TASK_MASTER
        """)
        r = cur.fetchone()
    return {
        "total_tasks": r[0] or 0,
        "completed": r[1] or 0,
        "in_progress": r[2] or 0,
        "pending": r[3] or 0,
        "overdue": r[4] or 0
    }


@router.get("/farmer-meetings/{task_id}")
def get_farmer_meetings(task_id: int):
    """
    Return per-farmer meeting details for a specific task.
    Shows exactly what the officer filled for each farmer: KCC yes/no + reason,
    canara, sangola, recovery, cane_registration, vehicle, tonnage, feedback, remark, etc.
    """
    with db_cursor() as cur:
        # Get the officer assigned to this task
        cur.execute("SELECT assigned_officer FROM TASK_MASTER WHERE task_id = ?", task_id)
        task_row = cur.fetchone()
        if not task_row:
            raise HTTPException(status_code=404, detail="Task not found")
        officer_id = task_row[0]

        # Get all farmers mapped to this task
        cur.execute("""
            SELECT
                tfm.farmer_id,
                ISNULL(m.NameE, 'Unknown') AS farmer_name,
                ISNULL(v.Village_NameE, '') AS village,
                tfm.status AS mapping_status
            FROM TASK_FARMER_MAPPING tfm
            LEFT JOIN dbo.TBL_MST_MASTER m ON m.code = tfm.farmer_id
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
            WHERE tfm.task_id = ?
        """, task_id)
        farmers = cur.fetchall()

        # Get meetings specific to THIS task (scoped by work_plan_id, not just officer)
        cur.execute("""
            SELECT
                fm.farmer_code,
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
                CONVERT(VARCHAR, fm.created_at, 106) AS meeting_date,
                fm.is_working_vehicle, fm.vehicle_working_reason
            FROM TbL_TRN_Farmer_Meeting fm
            WHERE fm.work_plan_id = ?
            ORDER BY fm.created_at DESC
        """, task_id)
        meetings = cur.fetchall()

    # Build a lookup: farmer_code -> latest meeting
    meeting_map = {}
    for m in meetings:
        fc = m[0]
        if fc not in meeting_map:  # keep latest (already sorted DESC)
            meeting_map[fc] = {
                "kcc": bool(m[1]) if m[1] is not None else None,
                "kcc_reason": m[2] or "",
                "canara_hnt": bool(m[3]) if m[3] is not None else None,
                "canara_reason": m[4] or "",
                "sangola_hnt": bool(m[5]) if m[5] is not None else None,
                "sangola_reason": m[6] or "",
                "cane_registration": bool(m[7]) if m[7] is not None else None,
                "cane_registration_remark": m[8] or "",
                "recovery": bool(m[9]) if m[9] is not None else None,
                "recovery_reason": m[10] or "",
                "vehicle_agreement": bool(m[11]) if m[11] is not None else None,
                "vehicle_reason": m[12] or "",
                "expected_tonnage": float(m[13]) if m[13] is not None else 0,
                "cane_development": m[14] or "",
                "feedback": m[15] or "",
                "remark": m[16] or "",
                "meeting_date": m[17] or "",
                "is_working_vehicle": bool(m[18]) if m[18] is not None else None,
                "vehicle_working_reason": m[19] or "",
            }

    results = []
    for f in farmers:
        fid, fname, fvillage, fstatus = f
        meeting = meeting_map.get(fid)
        entry = {
            "farmer_code": fid,
            "farmer_name": fname,
            "village": fvillage,
            "mapping_status": fstatus or "PENDING",
            "has_meeting": meeting is not None,
        }
        if meeting:
            entry.update(meeting)
        else:
            # No meeting data for this farmer
            entry.update({
                "kcc": None, "kcc_reason": "",
                "canara_hnt": None, "canara_reason": "",
                "sangola_hnt": None, "sangola_reason": "",
                "cane_registration": None, "cane_registration_remark": "",
                "recovery": None, "recovery_reason": "",
                "vehicle_agreement": None, "vehicle_reason": "",
                "expected_tonnage": 0, "cane_development": "",
                "feedback": "", "remark": "", "meeting_date": "",
                "is_working_vehicle": None, "vehicle_working_reason": "",
            })
        results.append(entry)

    return results


@router.get("/campaign-analytics")
def get_campaign_analytics():
    with db_cursor() as cur:
        cur.execute("""
            SELECT 
                ISNULL(v.Village_NameE, 'Unknown') AS village,
                COUNT(m.meeting_id) AS total_meetings,
                SUM(CASE WHEN m.kcc = 1 THEN 1 ELSE 0 END) AS kcc_yes,
                SUM(CASE WHEN m.canara_hnt = 1 THEN 1 ELSE 0 END) AS canara_hnt_yes,
                SUM(CASE WHEN m.sangola_hnt = 1 THEN 1 ELSE 0 END) AS sangola_hnt_yes,
                SUM(CASE WHEN m.cane_registration = 1 THEN 1 ELSE 0 END) AS cane_reg_yes,
                SUM(CASE WHEN m.recovery = 1 THEN 1 ELSE 0 END) AS recovery_yes,
                SUM(CASE WHEN m.vehicle_agreement = 1 THEN 1 ELSE 0 END) AS vehicle_yes,
                SUM(ISNULL(m.expected_tonnage, 0)) AS total_tonnage
            FROM TbL_TRN_Farmer_Meeting m
            LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            GROUP BY v.Village_NameE
            ORDER BY total_tonnage DESC
        """)
        rows = cur.fetchall()
        
    return [
        {
            "village": r[0],
            "total_meetings": r[1],
            "kcc_yes": r[2] or 0,
            "canara_hnt_yes": r[3] or 0,
            "sangola_hnt_yes": r[4] or 0,
            "cane_reg_yes": r[5] or 0,
            "recovery_yes": r[6] or 0,
            "vehicle_yes": r[7] or 0,
            "total_tonnage": float(r[8]) if r[8] is not None else 0.0
        }
        for r in rows
    ]


