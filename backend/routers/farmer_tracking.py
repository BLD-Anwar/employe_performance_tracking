"""
routers/farmer_tracking.py  –  Farmer Visit Tracking Analytics
Provides attendance breakdown (attended vs remaining) by geographic hierarchy.

Endpoints:
  GET /api/farmer-tracking/summary   – Summary + hierarchical breakdown
  GET /api/farmer-tracking/farmers   – Farmer list filtered by status/location
  GET /api/farmer-tracking/export    – CSV download of farmer list
"""
from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from database import db_cursor
from auth import require_role
from datetime import date, timedelta
from typing import Optional
import io, csv

router = APIRouter(
    prefix="/api/farmer-tracking",
    tags=["farmer-tracking"],
    dependencies=[Depends(require_role("manager"))],
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _date_cutoff(range_: str) -> date:
    """Return the start date for the given range."""
    today = date.today()
    if range_ == "day":
        return today
    if range_ == "week":
        return today - timedelta(days=6)
    # month
    return today - timedelta(days=29)


def _range_label(range_: str) -> str:
    today = date.today()
    if range_ == "day":
        return f"Today ({today.strftime('%d %b %Y')})"
    if range_ == "week":
        start = today - timedelta(days=6)
        return f"This Week ({start.strftime('%d %b')} – {today.strftime('%d %b %Y')})"
    start = today - timedelta(days=29)
    return f"This Month ({start.strftime('%d %b')} – {today.strftime('%d %b %Y')})"


def _fetch_all_farmers_with_visits(cutoff: date):
    """
    Fetch all farmers with their geographic names and visit count
    for meetings on or after `cutoff`.
    Returns list of dicts.
    """
    sql = """
        SELECT
            m.code             AS farmer_id,
            ISNULL(m.NameE, '') AS farmer_name,
            ISNULL(m.MobileNumber, '') AS mobile,
            ISNULL(t.Taluka_NameE, '') AS taluka,
            ISNULL(v.Village_NameE, '') AS village,
            ISNULL(s.Subvillage_NameE, '') AS sub_village,
            COUNT(mtg.meeting_id) AS visit_count,
            MAX(CONVERT(VARCHAR, mtg.created_at, 23)) AS last_visit_date
        FROM dbo.TBL_MST_MASTER m
        LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
        LEFT JOIN dbo.TBl_mst_taluka t ON t.Taluka_Code = m.Talula_Code
        LEFT JOIN dbo.Tbl_mst_sub_village s ON s.Subvillage_code = m.Subvillage_code
        LEFT JOIN dbo.TbL_TRN_Farmer_Meeting mtg
            ON mtg.farmer_code = m.code
            AND CAST(mtg.created_at AS DATE) >= ?
        GROUP BY
            m.code, m.NameE, m.MobileNumber,
            t.Taluka_NameE, v.Village_NameE, s.Subvillage_NameE
    """
    with db_cursor() as cur:
        cur.execute(sql, cutoff.strftime('%Y-%m-%d'))
        rows = cur.fetchall()

    return [
        {
            "farmer_id": r[0],
            "farmer_name": (r[1] or "").strip() or f"Farmer #{r[0]}",
            "mobile": r[2] or "",
            "taluka": r[3] or "",
            "village": r[4] or "",
            "sub_village": r[5] or "",
            "visit_count": r[6] or 0,
            "last_visit_date": r[7] or "",
        }
        for r in rows
    ]


def _build_hierarchy(farmers: list) -> list:
    """
    Build district → village → sub_village hierarchy from flat farmer list.
    Returns list of district dicts with nested village and sub_village breakdowns.
    """
    # Group by taluka
    talukas: dict = {}
    for f in farmers:
        t = f["taluka"] or "Unknown District"
        v = f["village"] or "Unknown Village"
        sv = f["sub_village"] or "Unknown Sub-Village"

        if t not in talukas:
            talukas[t] = {}
        if v not in talukas[t]:
            talukas[t][v] = {}
        if sv not in talukas[t][v]:
            talukas[t][v][sv] = {"total": 0, "attended": 0}

        talukas[t][v][sv]["total"] += 1
        if f["visit_count"] > 0:
            talukas[t][v][sv]["attended"] += 1

    # Build structured list
    result = []
    for taluka_name, villages in sorted(talukas.items()):
        district_total = 0
        district_attended = 0
        village_list = []

        for village_name, sub_villages in sorted(villages.items()):
            village_total = 0
            village_attended = 0
            sv_list = []

            for sv_name, counts in sorted(sub_villages.items()):
                sv_total = counts["total"]
                sv_attended = counts["attended"]
                village_total += sv_total
                village_attended += sv_attended
                sv_list.append({
                    "name": sv_name,
                    "total": sv_total,
                    "attended": sv_attended,
                    "remaining": sv_total - sv_attended,
                    "attendance_pct": round(sv_attended / sv_total * 100, 1) if sv_total else 0.0,
                })

            village_list.append({
                "name": village_name,
                "total": village_total,
                "attended": village_attended,
                "remaining": village_total - village_attended,
                "attendance_pct": round(village_attended / village_total * 100, 1) if village_total else 0.0,
                "sub_villages": sv_list,
            })

            district_total += village_total
            district_attended += village_attended

        result.append({
            "name": taluka_name,
            "total": district_total,
            "attended": district_attended,
            "remaining": district_total - district_attended,
            "attendance_pct": round(district_attended / district_total * 100, 1) if district_total else 0.0,
            "villages": village_list,
        })

    return result


def _apply_filters(
    farmers: list,
    status: Optional[str],
    taluka: Optional[str],
    village: Optional[str],
    sub_village: Optional[str],
    search: Optional[str],
) -> list:
    """Filter a flat farmer list by status, location, and search term."""
    result = []
    search_lower = (search or "").lower()

    for f in farmers:
        # Status filter
        if status == "attended" and f["visit_count"] == 0:
            continue
        if status == "remaining" and f["visit_count"] > 0:
            continue

        # Geographic filters
        if taluka and f["taluka"].lower() != taluka.lower():
            continue
        if village and f["village"].lower() != village.lower():
            continue
        if sub_village and f["sub_village"].lower() != sub_village.lower():
            continue

        # Search filter
        if search_lower:
            if (
                search_lower not in f["farmer_name"].lower()
                and search_lower not in str(f["farmer_id"])
            ):
                continue

        result.append(f)

    return result


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_tracking_summary(range_: str = Query(default="week", alias="range")):
    """
    Returns overall attendance summary + full geographic breakdown.
    range: day | week | month
    """
    if range_ not in ("day", "week", "month"):
        range_ = "week"

    cutoff = _date_cutoff(range_)
    farmers = _fetch_all_farmers_with_visits(cutoff)

    total = len(farmers)
    attended = sum(1 for f in farmers if f["visit_count"] > 0)
    remaining = total - attended
    pct = round(attended / total * 100, 1) if total else 0.0

    hierarchy = _build_hierarchy(farmers)

    return {
        "range": range_,
        "range_label": _range_label(range_),
        "total_farmers": total,
        "attended": attended,
        "remaining": remaining,
        "attendance_pct": pct,
        "by_district": hierarchy,
    }


@router.get("/farmers")
def get_tracking_farmers(
    range_: str = Query(default="week", alias="range"),
    status: Optional[str] = Query(default=None),         # "attended" | "remaining"
    taluka: Optional[str] = Query(default=None),
    village: Optional[str] = Query(default=None),
    sub_village: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    """
    Returns paginated farmer list filtered by visit status and/or geography.
    status: attended | remaining | (omit for all)
    """
    if range_ not in ("day", "week", "month"):
        range_ = "week"

    cutoff = _date_cutoff(range_)
    farmers = _fetch_all_farmers_with_visits(cutoff)
    filtered = _apply_filters(farmers, status, taluka, village, sub_village, search)

    # Sort: remaining first (no visits), then by name
    filtered.sort(key=lambda f: (f["visit_count"] > 0, f["farmer_name"]))

    return [
        {
            "id": f["farmer_id"],
            "name": f["farmer_name"],
            "mobile": f["mobile"],
            "taluka": f["taluka"],
            "village": f["village"],
            "sub_village": f["sub_village"],
            "visit_count": f["visit_count"],
            "last_visit_date": f["last_visit_date"],
            "status": "attended" if f["visit_count"] > 0 else "remaining",
        }
        for f in filtered
    ]


@router.get("/export")
def export_farmers_csv(
    range_: str = Query(default="week", alias="range"),
    status: Optional[str] = Query(default=None),
    taluka: Optional[str] = Query(default=None),
    village: Optional[str] = Query(default=None),
    sub_village: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    """
    Download filtered farmer list as a CSV file.
    status: attended | remaining | (omit for all)
    """
    if range_ not in ("day", "week", "month"):
        range_ = "week"

    cutoff = _date_cutoff(range_)
    farmers = _fetch_all_farmers_with_visits(cutoff)
    filtered = _apply_filters(farmers, status, taluka, village, sub_village, search)
    filtered.sort(key=lambda f: (f["visit_count"] > 0, f["farmer_name"]))

    # Build CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Farmer Code", "Name", "Mobile",
        "Taluka", "Village", "Sub-Village",
        "Visit Count", "Last Visit Date", "Status",
    ])
    for f in filtered:
        writer.writerow([
            f["farmer_id"],
            f["farmer_name"],
            f["mobile"],
            f["taluka"],
            f["village"],
            f["sub_village"],
            f["visit_count"],
            f["last_visit_date"],
            "Attended" if f["visit_count"] > 0 else "Remaining",
        ])

    output.seek(0)

    # Build filename
    scope_parts = []
    if taluka:
        scope_parts.append(taluka)
    if village:
        scope_parts.append(village)
    if status:
        scope_parts.append(status)
    scope_parts.append(range_)
    filename = "farmers_" + "_".join(scope_parts).replace(" ", "_") + ".csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
