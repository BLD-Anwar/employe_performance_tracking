"""
routers/meeting.py  –  Farmer Meeting data capture endpoints
Handles the officer's farmer meeting form submissions
(TbL_TRN_Farmer_Meeting table).

Pipeline:
  1. Officer selects a farmer from their assigned task list.
  2. Officer fills the full meeting form (KCC, HNT, tonnage, GPS, photo, etc.).
  3. Data is saved to TbL_TRN_Farmer_Meeting.
  4. Manager can fetch all meetings or meetings for a specific task/officer.
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Depends
from database import db_cursor, rows_to_list
from pydantic import BaseModel
from typing import Optional
import os, uuid
from auth import require_role

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


# ── Models ──────────────────────────────────────────────────────────────────
class FarmerMeetingSubmission(BaseModel):
    work_plan_id: Optional[int] = None
    farmer_code: int
    employee_id: int

    # KCC
    kcc: Optional[bool] = None
    kcc_reason: Optional[str] = None

    # Canara HNT
    canara_hnt: Optional[bool] = None
    canara_reason: Optional[str] = None

    # Sangola HNT
    sangola_hnt: Optional[bool] = None
    sangola_reason: Optional[str] = None

    # Cane Registration
    cane_registration: Optional[bool] = None
    cane_registration_remark: Optional[str] = None

    # Recovery
    recovery: Optional[bool] = None
    recovery_reason: Optional[str] = None

    # Expected Tonnage
    expected_tonnage: Optional[float] = None

    # Vehicle Agreement
    vehicle_agreement: Optional[bool] = None
    vehicle_reason: Optional[str] = None
    is_working_vehicle: Optional[bool] = None
    vehicle_working_reason: Optional[str] = None

    # Cane Development
    cane_development: Optional[str] = None

    # Farmer Feedback
    feedback: Optional[str] = None

    # Photo (path — uploaded separately or base64)
    photo_path: Optional[str] = None

    # General Remark
    remark: Optional[str] = None

    # GPS
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location: Optional[str] = None

    # OTP
    otp_id: Optional[int] = None
    otp_verified: bool = False
    otp_verified_at: Optional[str] = None

    # Audit
    created_by: int


# ── POST: Submit a new farmer meeting ──────────────────────────────────────
@router.post("", dependencies=[Depends(require_role("manager"))])
def create_farmer_meeting(body: FarmerMeetingSubmission):
    """Officer submits a farmer meeting record."""
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO TbL_TRN_Farmer_Meeting (
                work_plan_id, farmer_code, employee_id,
                kcc, kcc_reason,
                canara_hnt, canara_reason,
                sangola_hnt, sangola_reason,
                cane_registration, cane_registration_remark,
                recovery, recovery_reason,
                expected_tonnage,
                vehicle_agreement, vehicle_reason,
                is_working_vehicle, vehicle_working_reason,
                cane_development,
                feedback,
                photo_path,
                remark,
                latitude, longitude, location,
                otp_id, otp_verified, otp_verified_at,
                created_by
            )
            OUTPUT INSERTED.meeting_id
            VALUES (
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?,
                ?, ?,
                ?, ?,
                ?,
                ?,
                ?,
                ?,
                ?, ?, ?,
                ?, ?, ?,
                ?
            )
        """,
            body.work_plan_id, body.farmer_code, body.employee_id,
            1 if body.kcc else (0 if body.kcc is not None else None), body.kcc_reason,
            1 if body.canara_hnt else (0 if body.canara_hnt is not None else None), body.canara_reason,
            1 if body.sangola_hnt else (0 if body.sangola_hnt is not None else None), body.sangola_reason,
            1 if body.cane_registration else (0 if body.cane_registration is not None else None), body.cane_registration_remark,
            1 if body.recovery else (0 if body.recovery is not None else None), body.recovery_reason,
            body.expected_tonnage,
            1 if body.vehicle_agreement else (0 if body.vehicle_agreement is not None else None), body.vehicle_reason,
            1 if body.is_working_vehicle else (0 if body.is_working_vehicle is not None else None), body.vehicle_working_reason,
            body.cane_development,
            body.feedback,
            body.photo_path,
            body.remark,
            body.latitude, body.longitude, body.location,
            body.otp_id,
            1 if body.otp_verified else 0,
            body.otp_verified_at,
            body.created_by,
        )

        new_id = cur.fetchone()[0]

    return {"ok": True, "meeting_id": int(new_id), "message": "Farmer meeting saved successfully"}


# ── POST: Upload a meeting photo ──────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "uploads", "meetings")

@router.post("/upload-photo", dependencies=[Depends(require_role("manager"))])
async def upload_meeting_photo(file: UploadFile = File(...), user_id: int = Query(...)):
    """Upload a photo for a farmer meeting. Returns the saved file path."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only image files allowed")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5MB")

    filename = f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    # Return the relative URL path for the photo
    return {"ok": True, "photo_path": f"/uploads/meetings/{filename}"}


# ── GET: Meetings for the logged-in officer ────────────────────────────────
@router.get("/my/{employee_id}")
def get_my_meetings(
    employee_id: int,
    skip: int = Query(default=0),
    limit: int = Query(default=50),
    payload: dict = Depends(require_role("officer", "manager")),
):
    if payload.get("role") != "manager" and payload.get("user_id") != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")
    """Fetch all meetings submitted by this officer."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                m.meeting_id,
                m.farmer_code,
                ISNULL(f.NameE, '') AS farmer_name,
                ISNULL(v.Village_NameE, '') AS village,
                m.kcc, m.canara_hnt, m.sangola_hnt,
                m.cane_registration, m.recovery,
                m.expected_tonnage,
                m.vehicle_agreement, m.is_working_vehicle,
                m.otp_verified,
                CONVERT(VARCHAR, m.created_at, 23) AS created_date,
                CONVERT(VARCHAR, m.created_at, 108) AS created_time,
                m.latitude, m.longitude, m.location,
                m.remark,
                m.work_plan_id
            FROM TbL_TRN_Farmer_Meeting m
            LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            WHERE m.employee_id = ?
            ORDER BY m.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, employee_id, skip, limit)
        rows = cur.fetchall()
        cols = [col[0] for col in cur.description]

    return [dict(zip(cols, row)) for row in rows]


# ── GET: Single meeting detail ─────────────────────────────────────────────
@router.get("/{meeting_id}", dependencies=[Depends(require_role("manager"))])
def get_meeting_detail(meeting_id: int):
    """Get full detail of a single meeting record."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                m.*,
                ISNULL(f.NameE, '') AS farmer_name,
                ISNULL(f.MobileNumber, '') AS farmer_mobile,
                ISNULL(v.Village_NameE, '') AS village_name
            FROM TbL_TRN_Farmer_Meeting m
            LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            WHERE m.meeting_id = ?
        """, meeting_id)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Meeting not found")
        cols = [col[0] for col in cur.description]

    return dict(zip(cols, row))


# ── GET: All meetings (for manager view) ───────────────────────────────────
@router.get("", dependencies=[Depends(require_role("manager"))])
def get_all_meetings(
    employee_id: Optional[int] = Query(default=None),
    farmer_code: Optional[int] = Query(default=None),
    skip: int = Query(default=0),
    limit: int = Query(default=50),
):
    """Manager endpoint: list all meetings, optionally filtered."""
    with db_cursor() as cur:
        where_clauses = []
        params = []

        if employee_id is not None:
            where_clauses.append("m.employee_id = ?")
            params.append(employee_id)
        if farmer_code is not None:
            where_clauses.append("m.farmer_code = ?")
            params.append(farmer_code)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cur.execute(f"""
            SELECT
                m.meeting_id,
                m.farmer_code,
                ISNULL(f.NameE, '') AS farmer_name,
                ISNULL(v.Village_NameE, '') AS village,
                m.employee_id,
                ISNULL(u.first_name + ' ' + u.last_name, u.username) AS officer_name,
                m.kcc, m.canara_hnt, m.sangola_hnt,
                m.cane_registration, m.recovery,
                m.expected_tonnage,
                m.vehicle_agreement, m.is_working_vehicle,
                m.otp_verified,
                CONVERT(VARCHAR, m.created_at, 23) AS created_date,
                m.latitude, m.longitude, m.location,
                m.remark,
                m.work_plan_id
            FROM TbL_TRN_Farmer_Meeting m
            LEFT JOIN dbo.TBL_MST_MASTER f ON f.code = m.farmer_code
            LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = f.Village_code
            LEFT JOIN dbo.auth_user u ON u.id = m.employee_id
            {where_sql}
            ORDER BY m.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, *params, skip, limit)
        rows = cur.fetchall()
        cols = [col[0] for col in cur.description]

    return [dict(zip(cols, row)) for row in rows]


# ── GET: Check if meeting already exists for a farmer+employee combo ───────
@router.get("/check/{employee_id}/{farmer_code}")
def check_existing_meeting(
    employee_id: int,
    farmer_code: int,
    payload: dict = Depends(require_role("officer", "manager")),
):
    if payload.get("role") != "manager" and payload.get("user_id") != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")
    """Check if a meeting record already exists for this farmer by this officer."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT meeting_id, CONVERT(VARCHAR, created_at, 23) AS created_date
            FROM TbL_TRN_Farmer_Meeting
            WHERE employee_id = ? AND farmer_code = ?
            ORDER BY created_at DESC
        """, employee_id, farmer_code)
        rows = cur.fetchall()

    if rows:
        return {"exists": True, "count": len(rows), "last_meeting_id": rows[0][0], "last_date": rows[0][1]}
    return {"exists": False, "count": 0}
