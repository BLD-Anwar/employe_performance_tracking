from __future__ import annotations

from typing import Any, Dict, List, Optional

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Path

from backend.database import get_db

router = APIRouter(prefix="/employee", tags=["employee"])


def _fetchall(conn: pyodbc.Connection, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)

    cols = [d[0] for d in (cur.description or [])]
    rows = cur.fetchall() if cur.rowcount != -1 else cur.fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({cols[i]: r[i] for i in range(len(cols))})
    return out


def _resolve_header_pk_and_row_fk(conn: pyodbc.Connection) -> Dict[str, str]:
    """Reuse the same join-resolution strategy as backend/routers/tasks.py.

    Resolves:
    - header_pk: PK column on TBL_TRN_DAILY_WORKPLAN
    - row_fk: FK column on TBL_ROW_DAILY_WORKPLAN referencing that PK

    Uses INFORMATION_SCHEMA metadata (best-effort, avoids schema redesign).
    """

    header_cols = _get_table_columns(conn, "TBL_TRN_DAILY_WORKPLAN")
    row_cols = _get_table_columns(conn, "TBL_ROW_DAILY_WORKPLAN")
    header_set = set(header_cols)
    row_set = set(row_cols)

    pk_rows = _fetchall(
        conn,
        """
        SELECT k.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE k
            ON tc.CONSTRAINT_NAME = k.CONSTRAINT_NAME
            AND tc.TABLE_SCHEMA = k.TABLE_SCHEMA
        WHERE tc.TABLE_NAME = 'TBL_TRN_DAILY_WORKPLAN'
          AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        """,
    )

    header_pk_candidates = [r["COLUMN_NAME"] for r in pk_rows if r.get("COLUMN_NAME")]

    common_header_pk = ["id", "workplan_id", "plan_id", "daily_workplan_id", "trn_daily_workplan_id"]
    header_pk = None
    for cand in common_header_pk:
        if cand in header_set:
            header_pk = cand
            break

    if not header_pk and header_pk_candidates:
        for cand in header_pk_candidates:
            if cand in header_set:
                header_pk = cand
                break

    if not header_pk:
        raise HTTPException(
            status_code=500,
            detail="Cannot resolve TBL_TRN_DAILY_WORKPLAN primary key column",
        )

    fk_rows = _fetchall(
        conn,
        """
        SELECT
            ku.COLUMN_NAME AS FK_COLUMN_NAME,
            ku2.TABLE_NAME AS REFERENCED_TABLE_NAME,
            ku2.COLUMN_NAME AS REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
        INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
            ON ku.CONSTRAINT_CATALOG = rc.CONSTRAINT_CATALOG
           AND ku.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
           AND ku.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
        INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku2
            ON ku2.CONSTRAINT_CATALOG = rc.UNIQUE_CONSTRAINT_CATALOG
           AND ku2.CONSTRAINT_SCHEMA = rc.UNIQUE_CONSTRAINT_SCHEMA
           AND ku2.CONSTRAINT_NAME = rc.UNIQUE_CONSTRAINT_NAME
           AND ku2.ORDINAL_POSITION = ku.ORDINAL_POSITION
        WHERE ku.TABLE_NAME = 'TBL_ROW_DAILY_WORKPLAN'
        """,
    )

    fk_candidate = None
    for r in fk_rows:
        if (
            r.get("REFERENCED_TABLE_NAME") == "TBL_TRN_DAILY_WORKPLAN"
            and r.get("REFERENCED_COLUMN_NAME") == header_pk
            and r.get("FK_COLUMN_NAME") in row_set
        ):
            fk_candidate = r["FK_COLUMN_NAME"]
            break

    if not fk_candidate:
        patterns = [
            "plan_id",
            "workplan_id",
            "daily_workplan_id",
            "trn_daily_workplan_id",
            "TBL_TRN_DAILY_WORKPLAN_ID",
            "tbl_trn_daily_workplan_id",
            header_pk,
            "TRN_DAILY_WORKPLAN_ID",
            "work_plan_id",
        ]
        for cand in patterns:
            if cand in row_set:
                fk_candidate = cand
                break

    if not fk_candidate:
        raise HTTPException(
            status_code=500,
            detail="Cannot resolve TBL_ROW_DAILY_WORKPLAN foreign key column to header PK",
        )

    return {"header_pk": header_pk, "row_fk": fk_candidate}


def _get_table_columns(conn: pyodbc.Connection, table_name: str) -> List[str]:
    rows = _fetchall(
        conn,
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
        """,
        [table_name],
    )
    return [r["COLUMN_NAME"] for r in rows]


@router.get("/tasks/{emp_code}")
def get_employee_tasks(
    emp_code: str = Path(..., description="Employee code (emp_code)"),
    conn: pyodbc.Connection = Depends(get_db),
):


    """Employee view of assigned tasks.

    Uses the daily workplan assignment engine.
    Column mapping is derived dynamically at runtime based on available column names.
    """

    # Minimal, robust query: find candidate columns first.
    # We avoid broad schema discovery by only probing workplan table schemas.
    #
    # Expected typical columns (may vary by implementation):
    # - TBL_TRN_DAILY_WORKPLAN: id, emp_code, task_date, workplan_date, etc.
    # - TBL_ROW_DAILY_WORKPLAN: workplan_id (or trn_daily_workplan_id), purpose_of_work_id

    # Determine join key names by checking INFORMATION_SCHEMA for columns.
    # This is limited to the two required tables.
    workplan_cols = _fetchall(
        conn,
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'TBL_TRN_DAILY_WORKPLAN'
        """,
    )
    row_cols = _fetchall(
        conn,
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'TBL_ROW_DAILY_WORKPLAN'
        """,
    )

    workplan_colnames = {c["COLUMN_NAME"] for c in workplan_cols}
    row_colnames = {c["COLUMN_NAME"] for c in row_cols}

    # Choose assignment columns
    emp_col = None
    for cand in ["emp_code", "employee_code", "empCode", "EMP_CODE"]:
        if cand in workplan_colnames:
            emp_col = cand
            break
    if not emp_col:
        raise HTTPException(status_code=500, detail="Cannot find employee code column in TBL_TRN_DAILY_WORKPLAN")

    # Resolve join header/row relationship using the same helper/strategy as GET /tasks/list.
    pkfk = _resolve_header_pk_and_row_fk(conn)
    join_header_key = pkfk["header_pk"]
    join_row_key = pkfk["row_fk"]

    # Basic fields to return
    header_select_fields = []
    for cand in ["id", "task_date", "workplan_date", "date", "created_at", "createdon", "emp_code", emp_col]:
        if cand in workplan_colnames and cand not in header_select_fields:
            header_select_fields.append(cand)

    row_select_fields = []
    for cand in ["purpose_of_work_id", "purpose_of_work", "work_type_id", "work_type", "id", "notes", "remark", "qty", "quantity"]:
        if cand in row_colnames and cand not in row_select_fields:
            row_select_fields.append(cand)

    # Ensure at least one row field
    if not row_select_fields:
        row_select_fields = list(row_colnames)[:5]

    # Compose query
    header_fields_sql = ", ".join([f"h.{f}" for f in header_select_fields]) if header_select_fields else "h.*"
    row_fields_sql = ", ".join([f"r.{f} AS r_{f}" for f in row_select_fields])

    sql = f"""
        SELECT {header_fields_sql}, {row_fields_sql}
        FROM TBL_TRN_DAILY_WORKPLAN h
        INNER JOIN TBL_ROW_DAILY_WORKPLAN r
            ON r.{join_row_key} = h.{join_header_key}
        WHERE h.{emp_col} = ?
        ORDER BY h.{join_header_key}
    """

    rows = _fetchall(conn, sql, [emp_code])
    return {"emp_code": emp_code, "count": len(rows), "tasks": rows}



@router.post("/update-progress")
def update_progress(
    payload: Dict[str, Any],
    conn: pyodbc.Connection = Depends(get_db),
):
    """Update task progress.

    Confirmed schema columns (TBL_ROW_DAILY_WORKPLAN):
      - work_count  FLOAT  <- payload["progress"] or payload["work_count"]
      - status      FLOAT  <- payload["status"] (numeric only, e.g. 1.0)

    row identifier: payload["row_id"] | payload["workplan_row_id"] | payload["id"]
    """

    # Identify candidate identifiers
    row_id = payload.get("row_id") or payload.get("workplan_row_id") or payload.get("id")

    if row_id is None:
        raise HTTPException(status_code=400, detail="Missing required field: row_id/workplan_row_id/id")

    # Determine which columns exist
    row_cols = _fetchall(
        conn,
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'TBL_ROW_DAILY_WORKPLAN'
        """,
    )
    row_colnames = {c["COLUMN_NAME"] for c in row_cols}

    # MVP: map payload directly to confirmed schema columns (no dynamic discovery)
    # payload["work_count"] takes priority over payload["progress"] for the work_count column
    _wc_raw = payload.get("work_count") if payload.get("work_count") is not None else payload.get("progress")
    progress_col = None
    progress_value = None
    if _wc_raw is not None:
        try:
            progress_value = float(_wc_raw)
            progress_col = "work_count"
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="progress/work_count must be numeric")

    # status -> status FLOAT column; string values (e.g. "IN_PROGRESS") are rejected
    _st_raw = payload.get("status")
    status_col = None
    status_value = None
    if _st_raw is not None:
        try:
            status_value = float(_st_raw)
            status_col = "status"
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="status must be numeric (e.g. 1.0, 2.0)")

    if not progress_col and not status_col:
        raise HTTPException(status_code=400, detail="No updatable fields. Provide progress/work_count and/or status (numeric).")

    set_clauses = []
    params: List[Any] = []

    if progress_col:
        set_clauses.append(f"{progress_col} = ?")
        params.append(progress_value)

    if status_col:
        set_clauses.append(f"{status_col} = ?")
        params.append(status_value)

    # Row identifier column candidates.
    # If a primary key exists, prefer that.
    id_col = None

    # Prefer PK if resolvable
    pk_rows = _fetchall(
        conn,
        """
        SELECT k.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE k
            ON tc.CONSTRAINT_NAME = k.CONSTRAINT_NAME
            AND tc.TABLE_SCHEMA = k.TABLE_SCHEMA
        WHERE tc.TABLE_NAME = 'TBL_ROW_DAILY_WORKPLAN'
          AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        """,
    )
    pk_candidates = [r["COLUMN_NAME"] for r in pk_rows if r.get("COLUMN_NAME")]
    for cand in pk_candidates:
        if cand in row_colnames:
            id_col = cand
            break

    if not id_col:
        for cand in ["id", "row_id", "TBL_ROW_DAILY_WORKPLAN_ID"]:
            if cand in row_colnames:
                id_col = cand
                break

    if not id_col:
        raise HTTPException(status_code=500, detail="Cannot resolve row PK column for update-progress")

    params.append(row_id)

    sql = f"""
        UPDATE TBL_ROW_DAILY_WORKPLAN
        SET {', '.join(set_clauses)}
        WHERE {id_col} = ?
    """


    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        try:
            affected = cur.rowcount
        except Exception:
            affected = None
        return {"updated": True, "row_id": row_id, "affected": affected}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ---------------------------------------------------------------------------
# TEMPORARY DIAGNOSTIC ENDPOINTS — remove after debugging
# ---------------------------------------------------------------------------

