import os
import csv
import json
import datetime
from database import db_cursor

# Base directory for storing static report files
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")


def get_dynamic_status(status: str, end_date) -> str:
    """Helper to calculate status on the fly based on current date."""
    if not end_date:
        return status

    if isinstance(end_date, str):
        try:
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            try:
                end_date = datetime.datetime.strptime(end_date.split()[0], "%Y-%m-%d").date()
            except ValueError:
                return status
    elif isinstance(end_date, datetime.datetime):
        end_date = end_date.date()
    elif isinstance(end_date, datetime.date):
        pass
    else:
        return status

    today = datetime.date.today()
    if end_date < today and status not in ('COMPLETED', 'CANCELLED', 'OVERDUE'):
        return 'OVERDUE'
    return status


def compute_grade(score):
    """Return letter grade based on score."""
    if score >= 95:
        return "A+"
    elif score >= 85:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 45:
        return "D"
    else:
        return "F"


def compute_officer_rankings():
    """
    Compute a ranking of all officers based on their meeting KPI scores.
    Returns dict: {officer_id: {"rank": int, "total": int, "score": float}}
    """
    with db_cursor() as cur:
        # Get all officers who have tasks assigned
        cur.execute("""
            SELECT DISTINCT tm.assigned_officer
            FROM TASK_MASTER tm
            WHERE tm.assigned_officer IS NOT NULL
        """)
        officer_ids = [r[0] for r in cur.fetchall()]

    if not officer_ids:
        return {}

    scores = {}
    for oid in officer_ids:
        with db_cursor() as cur:
            # Farmer count for this officer
            cur.execute("""
                SELECT COUNT(DISTINCT tfm.farmer_id)
                FROM TASK_FARMER_MAPPING tfm
                JOIN TASK_MASTER tm ON tm.task_id = tfm.task_id
                WHERE tm.assigned_officer = ?
            """, oid)
            farmer_count = cur.fetchone()[0] or 0

            # Meeting KPIs
            cur.execute("""
                SELECT
                    COUNT(*) AS total_meetings,
                    SUM(CASE WHEN kcc = 1 THEN 1 ELSE 0 END) AS kcc_yes,
                    SUM(CASE WHEN cane_registration = 1 THEN 1 ELSE 0 END) AS cane_reg_yes,
                    SUM(CASE WHEN recovery = 1 THEN 1 ELSE 0 END) AS recovery_yes
                FROM TbL_TRN_Farmer_Meeting
                WHERE employee_id = ?
            """, oid)
            mk = cur.fetchone()

        total_meetings = mk[0] or 0
        if total_meetings > 0:
            kcc_pct = round((mk[1] or 0) / total_meetings * 100, 2)
            cane_reg_pct = round((mk[2] or 0) / total_meetings * 100, 2)
            recovery_pct = round((mk[3] or 0) / total_meetings * 100, 2)
        else:
            kcc_pct = cane_reg_pct = recovery_pct = 0

        meetings_pct = min(round(total_meetings / farmer_count * 100, 2), 100) if farmer_count > 0 else 0
        crushing_pct = cane_reg_pct  # proxy

        # Weighted: 40% Crushing + 20% Recovery + 20% Meetings + 20% KCC
        calc_score = round(crushing_pct * 0.4 + recovery_pct * 0.2 + meetings_pct * 0.2 + kcc_pct * 0.2, 2)
        scores[oid] = calc_score

    # Sort by score descending to assign ranks
    sorted_officers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    total = len(sorted_officers)
    rankings = {}
    for rank_idx, (oid, score) in enumerate(sorted_officers, start=1):
        rankings[oid] = {"rank": rank_idx, "total": total, "score": score}

    return rankings


def generate_task_report(task_id: int, manager_id: int = 1):
    """
    Gathers data for a task, creates REPORT_MASTER & REPORT_DETAILS records,
    generates a detailed CSV snapshot with grades, rankings, trends, missed farmers.
    """
    with db_cursor() as cur:
        # 1. Fetch Task Header Details
        cur.execute("""
            SELECT 
                t.task_id, t.task_name, t.work_type, t.assigned_officer, 
                t.priority, t.start_date, t.end_date, t.status, t.remarks, t.created_at,
                ISNULL(u.first_name, '') + ' ' + ISNULL(u.last_name, '') AS officer_name,
                u.username AS officer_code,
                ISNULL(t.schedule_type, 'WEEKLY') AS schedule_type
            FROM TASK_MASTER t
            LEFT JOIN dbo.auth_user u ON u.id = t.assigned_officer
            WHERE t.task_id = ?
        """, task_id)
        task_row = cur.fetchone()
        if not task_row:
            print(f"Task ID {task_id} not found.")
            return None

        task_id = task_row[0]
        task_name = task_row[1]
        work_type = task_row[2]
        officer_id = task_row[3]
        priority = task_row[4]
        start_date = task_row[5]
        end_date = task_row[6]
        raw_status = task_row[7]
        remarks = task_row[8]
        created_at = task_row[9]
        officer_name = (task_row[10] or "").strip() or "Unknown"
        officer_code = task_row[11] or ""
        schedule_type = task_row[12] or "WEEKLY"

        dynamic_status = get_dynamic_status(raw_status, end_date)

        # 2. Fetch Mapped Farmers & details
        cur.execute("""
            SELECT 
                r.farmer_id,
                ISNULL(m.NameE, 'Unknown') AS farmer_name,
                ISNULL(v.Village_NameE, '') AS village,
                ISNULL(t_loc.Taluka_NameE, '') AS taluka,
                ISNULL(m.MobileNumber, '') AS mobile,
                r.status AS mapping_status
            FROM TASK_FARMER_MAPPING r
            LEFT JOIN dbo.TBL_MST_MASTER m ON m.code = r.farmer_id
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
            LEFT JOIN dbo.TBl_mst_taluka t_loc ON t_loc.Taluka_Code = m.Talula_Code
            WHERE r.task_id = ?
        """, task_id)
        farmer_rows = cur.fetchall()

        farmers_list = []
        completed_farmers = 0
        pending_farmers = 0
        unique_villages = set()
        assigned_farmer_ids = set()

        for fr in farmer_rows:
            f_id, f_name, f_village, f_taluka, f_mobile, f_status = fr
            assigned_farmer_ids.add(f_id)
            farmers_list.append({
                "farmer_id": f_id,
                "name": f_name or "Unknown",
                "village": f_village,
                "taluka": f_taluka,
                "mobile": str(f_mobile) if f_mobile else "",
                "status": f_status
            })
            if f_status == 'COMPLETED':
                completed_farmers += 1
            else:
                pending_farmers += 1
            if f_village:
                unique_villages.add(f_village)

        farmer_count = len(farmers_list)
        village_count = len(unique_villages)
        completion_rate = round((completed_farmers / farmer_count * 100), 2) if farmer_count > 0 else 0.0

        # 3. Meeting KPIs from TbL_TRN_Farmer_Meeting for this officer
        cur.execute("""
            SELECT
                COUNT(*) AS total_meetings,
                SUM(CASE WHEN kcc = 1 THEN 1 ELSE 0 END) AS kcc_yes,
                SUM(CASE WHEN canara_hnt = 1 THEN 1 ELSE 0 END) AS canara_yes,
                SUM(CASE WHEN sangola_hnt = 1 THEN 1 ELSE 0 END) AS sangola_yes,
                SUM(CASE WHEN cane_registration = 1 THEN 1 ELSE 0 END) AS cane_reg_yes,
                SUM(CASE WHEN recovery = 1 THEN 1 ELSE 0 END) AS recovery_yes,
                SUM(CASE WHEN vehicle_agreement = 1 THEN 1 ELSE 0 END) AS vehicle_yes
            FROM TbL_TRN_Farmer_Meeting
            WHERE employee_id = ?
        """, officer_id)
        mk = cur.fetchone()

        total_meetings = mk[0] or 0
        kcc_pct = round((mk[1] or 0) / total_meetings * 100, 2) if total_meetings else 0
        canara_pct = round((mk[2] or 0) / total_meetings * 100, 2) if total_meetings else 0
        sangola_pct = round((mk[3] or 0) / total_meetings * 100, 2) if total_meetings else 0
        cane_reg_pct = round((mk[4] or 0) / total_meetings * 100, 2) if total_meetings else 0
        recovery_pct = round((mk[5] or 0) / total_meetings * 100, 2) if total_meetings else 0
        vehicle_pct = round((mk[6] or 0) / total_meetings * 100, 2) if total_meetings else 0

        meetings_coverage_pct = min(round(total_meetings / farmer_count * 100, 2), 100) if farmer_count > 0 else 0
        crushing_pct = cane_reg_pct  # proxy

        # Weighted score: 40% Crushing + 20% Recovery + 20% Meetings + 20% KCC
        calculated_score = round(
            crushing_pct * 0.4 + recovery_pct * 0.2 + meetings_coverage_pct * 0.2 + kcc_pct * 0.2, 2
        )
        grade = compute_grade(calculated_score)

        # 4. Missed Farmers — assigned farmers without any meeting
        cur.execute("""
            SELECT DISTINCT farmer_code FROM TbL_TRN_Farmer_Meeting WHERE employee_id = ?
        """, officer_id)
        met_farmer_ids = set(r[0] for r in cur.fetchall())
        missed_farmers = []
        for f in farmers_list:
            if f["farmer_id"] not in met_farmer_ids:
                missed_farmers.append({
                    "farmer_id": f["farmer_id"],
                    "name": f["name"],
                    "village": f["village"]
                })

        # 5. Previous period score (from the last REPORT_DETAILS for this officer)
        cur.execute("""
            SELECT TOP 1 calculated_score
            FROM REPORT_DETAILS rd
            JOIN REPORT_MASTER rm ON rm.report_id = rd.report_id
            WHERE rd.officer_id = ? AND rd.calculated_score IS NOT NULL
            ORDER BY rm.generated_date DESC
        """, officer_id)
        prev_row = cur.fetchone()
        prev_score = float(prev_row[0]) if prev_row and prev_row[0] is not None else None
        score_trend = round(calculated_score - prev_score, 2) if prev_score is not None else None

    # 6. Officer Rankings
    rankings = compute_officer_rankings()
    rank_info = rankings.get(officer_id, {"rank": 0, "total": 0, "score": 0})

    # 7. Build snapshot JSON
    snapshot_data = {
        "task": {
            "task_id": task_id,
            "task_name": task_name,
            "work_type": work_type,
            "priority": priority,
            "start_date": str(start_date) if start_date else "",
            "end_date": str(end_date) if end_date else "",
            "status": dynamic_status,
            "schedule_type": schedule_type,
            "remarks": remarks or "",
            "officer_name": officer_name,
            "officer_code": officer_code
        },
        "farmers": farmers_list,
        "metrics": {
            "farmer_count": farmer_count,
            "village_count": village_count,
            "completed_farmers": completed_farmers,
            "pending_farmers": pending_farmers,
            "completion_rate": completion_rate
        },
        "kpis": {
            "kcc_pct": kcc_pct,
            "canara_pct": canara_pct,
            "sangola_pct": sangola_pct,
            "cane_reg_pct": cane_reg_pct,
            "recovery_pct": recovery_pct,
            "vehicle_pct": vehicle_pct,
            "meetings_coverage_pct": meetings_coverage_pct,
            "crushing_pct": crushing_pct,
            "calculated_score": calculated_score,
            "grade": grade,
        },
        "ranking": {
            "rank": rank_info["rank"],
            "total_officers": rank_info["total"],
        },
        "trend": {
            "prev_score": prev_score,
            "current_score": calculated_score,
            "change": score_trend,
        },
        "missed_farmers": missed_farmers,
    }
    snapshot_json = json.dumps(snapshot_data)

    # 8. Create CSV file
    now = datetime.datetime.now()
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    relative_path = os.path.join(year_str, month_str, f"task_{task_id}_report.csv")
    absolute_dir = os.path.join(REPORTS_DIR, year_str, month_str)
    os.makedirs(absolute_dir, exist_ok=True)
    absolute_filepath = os.path.join(absolute_dir, f"task_{task_id}_report.csv")

    with open(absolute_filepath, mode="w", newline="", encoding="utf-8") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["=== SRI SRI SUGAR — TASK PERFORMANCE REPORT ==="])
        writer.writerow([])
        writer.writerow(["Task ID", task_id])
        writer.writerow(["Task Name", task_name])
        writer.writerow(["Work Type", work_type])
        writer.writerow(["Schedule", schedule_type])
        writer.writerow(["Priority", priority])
        writer.writerow(["Assigned Officer", f"{officer_name} ({officer_code})"])
        writer.writerow(["Start Date", start_date])
        writer.writerow(["End Date", end_date])
        writer.writerow(["Task Status", dynamic_status])
        writer.writerow([])
        writer.writerow(["=== PERFORMANCE SUMMARY ==="])
        writer.writerow(["Performance Score", f"{calculated_score}%"])
        writer.writerow(["Performance Grade", grade])
        writer.writerow(["Officer Rank", f"#{rank_info['rank']} of {rank_info['total']}"])
        if score_trend is not None:
            trend_str = f"+{score_trend}%" if score_trend >= 0 else f"{score_trend}%"
            writer.writerow(["Score Trend vs Previous", trend_str])
        writer.writerow([])
        writer.writerow(["=== KPI BREAKDOWN ==="])
        writer.writerow(["KCC Compliance", f"{kcc_pct}%"])
        writer.writerow(["Canara HNT", f"{canara_pct}%"])
        writer.writerow(["Sangola HNT", f"{sangola_pct}%"])
        writer.writerow(["Cane Registration", f"{cane_reg_pct}%"])
        writer.writerow(["Recovery", f"{recovery_pct}%"])
        writer.writerow(["Vehicle Agreement", f"{vehicle_pct}%"])
        writer.writerow(["Farmer Meeting Coverage", f"{meetings_coverage_pct}%"])
        writer.writerow([])
        writer.writerow(["=== FARMER COMPLETION ==="])
        writer.writerow(["Total Farmers", farmer_count])
        writer.writerow(["Completed", completed_farmers])
        writer.writerow(["Pending", pending_farmers])
        writer.writerow(["Completion Rate", f"{completion_rate}%"])
        writer.writerow([])
        writer.writerow(["=== ASSIGNED FARMERS ==="])
        writer.writerow(["Farmer Code", "Farmer Name", "Taluka", "Village", "Mobile", "Visit Status"])
        for f in farmers_list:
            writer.writerow([f["farmer_id"], f["name"], f["taluka"], f["village"], f["mobile"], f["status"]])
        if missed_farmers:
            writer.writerow([])
            writer.writerow(["=== MISSED FARMERS (Not Visited) ==="])
            writer.writerow(["Farmer Code", "Farmer Name", "Village"])
            for mf in missed_farmers:
                writer.writerow([mf["farmer_id"], mf["name"], mf["village"]])

    # 9. Insert into DB
    with db_cursor() as cur:
        report_type = f"{work_type or schedule_type} Performance Report"

        cur.execute("""
            INSERT INTO REPORT_MASTER (task_id, report_type, generated_by, status, file_path)
            OUTPUT INSERTED.report_id
            VALUES (?, ?, ?, 'COMPLETE', ?)
        """, task_id, report_type, manager_id, relative_path.replace("\\", "/"))

        report_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO REPORT_DETAILS (
                report_id, officer_id, farmer_count, village_count, completion_rate,
                report_status, task_status, assigned_date, end_date, 
                completed_farmers, pending_farmers, generated_snapshot_json, remarks,
                performance_grade, calculated_score, officer_rank, total_officers,
                kcc_pct, canara_pct, sangola_pct, cane_reg_pct, recovery_pct,
                vehicle_pct, meetings_coverage_pct, prev_score, score_trend,
                missed_farmers_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        report_id, officer_id, farmer_count, village_count, completion_rate,
        'COMPLETE', dynamic_status, start_date, end_date,
        completed_farmers, pending_farmers, snapshot_json, remarks,
        grade, calculated_score, rank_info["rank"], rank_info["total"],
        kcc_pct, canara_pct, sangola_pct, cane_reg_pct, recovery_pct,
        vehicle_pct, meetings_coverage_pct, prev_score, score_trend,
        json.dumps(missed_farmers))

    print(f"Report ID {report_id} generated — Grade: {grade}, Score: {calculated_score}%, Rank: #{rank_info['rank']}/{rank_info['total']}")
    return report_id


def check_and_generate_eligible_reports(manager_id: int = 1):
    """
    Scans for tasks that are either completed OR past their end date (overdue),
    checks if they have a generated report in REPORT_MASTER, and if not, generates it.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT t.task_id
            FROM TASK_MASTER t
            LEFT JOIN REPORT_MASTER r ON r.task_id = t.task_id
            WHERE r.report_id IS NULL
              AND (
                  t.status = 'COMPLETED'
                  OR (t.end_date < CAST(GETDATE() AS DATE) AND t.status NOT IN ('COMPLETED', 'CANCELLED'))
              )
        """)
        rows = cur.fetchall()

    task_ids = [r[0] for r in rows]
    generated = 0
    for tid in task_ids:
        try:
            result = generate_task_report(tid, manager_id)
            if result:
                generated += 1
        except Exception as e:
            print(f"Failed to generate report for Task ID {tid}: {e}")

    print(f"Auto-generation complete: {generated} new reports from {len(task_ids)} eligible tasks")
    return generated
