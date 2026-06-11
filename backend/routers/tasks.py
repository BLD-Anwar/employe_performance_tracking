from __future__ import annotations

from typing import Any, Dict, List, Optional

import pyodbc
from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


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


def _fetch_one(conn: pyodbc.Connection, sql: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)
    cols = [d[0] for d in (cur.description or [])]
    row = cur.fetchone()
    if not row:
        return None
    return {cols[i]: row[i] for i in range(len(cols))}


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


@router.get("/work-types")
def get_work_types(conn: pyodbc.Connection = Depends(get_db)):
    # Static mapping per requirement: purpose_of_work -> id,name
    sql = "SELECT id, name FROM purpose_of_work ORDER BY name"
    rows = _fetchall(conn, sql)
    return {"work_types": rows, "count": len(rows)}



@router.get("")
def list_tasks():
    # Not used; keep route clear.
    return {"status": "ok"}



def _resolve_header_pk_and_row_fk(conn: pyodbc.Connection) -> Dict[str, str]:
    """Best-effort schema resolution for join between header and row.

    Required fix: do NOT assume SCOPE_IDENTITY() == plan_id.
    We detect: (1) header primary key column, (2) row FK column that references it.

    Uses INFORMATION_SCHEMA. Avoids heavy multi-phase discovery.
    """

    header_cols = _get_table_columns(conn, "TBL_TRN_DAILY_WORKPLAN")
    row_cols = _get_table_columns(conn, "TBL_ROW_DAILY_WORKPLAN")
    header_set = set(header_cols)
    row_set = set(row_cols)

    # 1) Detect header PK candidates via INFORMATION_SCHEMA constraints.
    #    (We still keep fallback based on common names if PK query returns nothing.)
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
        # If PK exists, prefer the first PK column that also exists in our schema list.
        for cand in header_pk_candidates:
            if cand in header_set:
                header_pk = cand
                break

    if not header_pk:
        raise HTTPException(
            status_code=500,
            detail="Cannot resolve TBL_TRN_DAILY_WORKPLAN primary key column",
        )

    # 2) Detect row FK referencing the resolved header PK.
    #    Try INFORMATION_SCHEMA referential constraints; fall back to common FK name patterns.
    # NOTE:
    # The original query referenced columns/aliases that are not consistent across SQL Server versions.
    # In particular, the executed SELECT can end up trying to read a non-existent metadata column named
    # TABLE_NAME on the wrong alias (leading to: "Invalid column name 'TABLE_NAME'").
    #
    # Use INFORMATION_SCHEMA.KEY_COLUMN_USAGE for both sides of the referential constraint instead.
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
        # Common patterns that often link row->header pk.
        patterns = [
            "plan_id",
            "workplan_id",
            "daily_workplan_id",
            "trn_daily_workplan_id",
            "TBL_TRN_DAILY_WORKPLAN_ID",
            "tbl_trn_daily_workplan_id",
            header_pk,  # sometimes the column name equals the referenced pk name
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


@router.get("/list")
def get_tasks_list(conn: pyodbc.Connection = Depends(get_db)):
    pkfk = _resolve_header_pk_and_row_fk(conn)
    join_header_key = pkfk["header_pk"]
    join_row_key = pkfk["row_fk"]

    sql = f"""
        SELECT h.*, r.*
        FROM TBL_TRN_DAILY_WORKPLAN h
        INNER JOIN TBL_ROW_DAILY_WORKPLAN r
            ON r.{join_row_key} = h.{join_header_key}
        ORDER BY h.{join_header_key} DESC
    """
    rows = _fetchall(conn, sql)
    return {"count": len(rows), "tasks": rows, "join": pkfk}



@router.post("/create")
def create_task(payload: Dict[str, Any], conn: pyodbc.Connection = Depends(get_db)):
    """Create assignment.

    Fixes:
    - Remove assumption that SCOPE_IDENTITY() equals plan_id.
    - Detect header PK + row FK and use those columns consistently.

    Expected payload (best-effort; validated against existing columns at runtime):
    - emp_code: str
    - work_date / task_date: optional
    - work_type_id OR purpose_of_work_id OR work_type: required
    - farmer_id (optional)
    - qty/quantity (optional)
    - notes/remark (optional)
    """

    pkfk = _resolve_header_pk_and_row_fk(conn)
    header_pk = pkfk["header_pk"]
    row_fk = pkfk["row_fk"]

    header_cols = set(_get_table_columns(conn, "TBL_TRN_DAILY_WORKPLAN"))
    row_cols = set(_get_table_columns(conn, "TBL_ROW_DAILY_WORKPLAN"))

    emp_col = next((c for c in ["emp_code", "employee_code", "EMP_CODE"] if c in header_cols), None)
    if not emp_col:
        raise HTTPException(status_code=500, detail="Cannot find emp_code column in TBL_TRN_DAILY_WORKPLAN")

    # Date column optional
    date_col = next((c for c in ["task_date", "workplan_date", "date", "WORK_DATE", "TASK_DATE"] if c in header_cols), None)
    date_value = payload.get("work_date") or payload.get("task_date")

    # Insert header without explicitly setting header_pk (assume identity).
    # This returns the identity value of the header row.
    header_insert_cols: List[str] = [emp_col]
    header_params: List[Any] = [payload.get("emp_code")]

    if date_col and date_value is not None:
        header_insert_cols.append(date_col)
        header_params.append(date_value)

    placeholders = ",".join(["?" for _ in header_insert_cols])
    cols_sql = ",".join(header_insert_cols)

    sql_insert_header = (
        f"INSERT INTO TBL_TRN_DAILY_WORKPLAN ({cols_sql}) VALUES ({placeholders}); "
        "SELECT CAST(SCOPE_IDENTITY() AS bigint) AS new_id"
    )

    # Execute INSERT; then immediately query the identity.
    # This avoids pyodbc/ODBC driver quirks where INSERT...SELECT can be treated as non-query.
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO TBL_TRN_DAILY_WORKPLAN ({cols_sql}) VALUES ({placeholders})",
        header_params,
    )
    row = cur.execute("SELECT CAST(SCOPE_IDENTITY() AS bigint) AS new_id").fetchone()
    new_id_row = {"new_id": row[0]} if row else None


    if not new_id_row or "new_id" not in new_id_row:
        raise HTTPException(status_code=500, detail="Failed to create workplan header")

    new_header_pk = new_id_row["new_id"]

    # work type id column
    # In this schema, TBL_ROW_DAILY_WORKPLAN appears to store the selected work type as work_id.
    work_type_col = next(
        (
            c
            for c in [
                "purpose_of_work_id",
                "work_type_id",
                "work_type",
                "purpose_of_work",
                "PURPOSE_OF_WORK_ID",
                "work_id",
                "WORK_ID",
            ]
            if c in row_cols
        ),
        None,
    )
    if not work_type_col:
        raise HTTPException(
            status_code=500,
            detail="Cannot find work type column in TBL_ROW_DAILY_WORKPLAN (expected work_id/purpose_of_work_id/work_type_id)",
        )

    work_type_value = (
        payload.get("work_type_id")
        or payload.get("purpose_of_work_id")
        or payload.get("work_type")
        or payload.get("work_id")
    )

    if work_type_value is None:
        raise HTTPException(status_code=400, detail="Missing required field: work_type_id/purpose_of_work_id/work_type")

    row_insert_cols: List[str] = [row_fk, work_type_col]
    row_params: List[Any] = [new_header_pk, work_type_value]


    # optional farmer id
    if "farmer_id" in row_cols and payload.get("farmer_id") is not None:
        row_insert_cols.append("farmer_id")
        row_params.append(payload.get("farmer_id"))

    # optional quantity
    qty_col = next((c for c in ["qty", "quantity", "QTY", "QUANTITY"] if c in row_cols), None)
    if qty_col and payload.get("qty") is not None:
        row_insert_cols.append(qty_col)
        row_params.append(payload.get("qty"))
    elif qty_col and payload.get("quantity") is not None:
        row_insert_cols.append(qty_col)
        row_params.append(payload.get("quantity"))

    # optional notes
    notes_col = next((c for c in ["notes", "remark", "remarks", "note", "REMARK"] if c in row_cols), None)
    if notes_col and payload.get("notes") is not None:
        row_insert_cols.append(notes_col)
        row_params.append(payload.get("notes"))
    elif notes_col and payload.get("remark") is not None:
        row_insert_cols.append(notes_col)
        row_params.append(payload.get("remark"))

    placeholders_row = ",".join(["?" for _ in row_insert_cols])
    cols_sql_row = ",".join(row_insert_cols)

    sql_insert_row = f"INSERT INTO TBL_ROW_DAILY_WORKPLAN ({cols_sql_row}) VALUES ({placeholders_row})"

    cur = conn.cursor()
    cur.execute(sql_insert_row, row_params)

    return {"created": True, "workplan_id": new_header_pk, "row_count": 1}


