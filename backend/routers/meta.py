from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
import pyodbc

from backend.database import get_db

router = APIRouter(prefix="/meta", tags=["meta"])


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
        item = {cols[i]: r[i] for i in range(len(cols))}
        out.append(item)
    return out


@router.get("/tables")
def tables(
    include_schemas: Optional[str] = Query(
        default=None,
        description="Comma-separated schema names to include. Example: dbo,staging",
    ),
    contains: Optional[str] = Query(
        default=None,
        description="Filter tables whose name contains this substring (case-insensitive).",
    ),
    conn: pyodbc.Connection = Depends(get_db),
):
    # Use INFORMATION_SCHEMA for portability and sys.* to include PK/FK later.
    schema_list = None
    if include_schemas:
        schema_list = [s.strip() for s in include_schemas.split(",") if s.strip()]

    sql = """
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    """

    params: List[Any] = []

    if schema_list:
        placeholders = ",".join(["?" for _ in schema_list])
        sql += f" AND TABLE_SCHEMA IN ({placeholders})"
        params.extend(schema_list)

    if contains:
        sql += " AND TABLE_NAME LIKE ?"
        params.append(f"%{contains}%")

    sql += " ORDER BY TABLE_SCHEMA, TABLE_NAME"

    rows = _fetchall(conn, sql, params if params else None)
    return {"tables": rows, "count": len(rows)}


@router.get("/table/{table_name}")
def table_detail(
    table_name: str,
    schema: Optional[str] = Query(default=None, description="Optional schema. If omitted, searches all schemas."),
    conn: pyodbc.Connection = Depends(get_db),
):
    # 1) Columns
    sql_cols = """
    SELECT
        c.TABLE_SCHEMA,
        c.TABLE_NAME,
        c.COLUMN_NAME,
        c.ORDINAL_POSITION,
        c.DATA_TYPE,
        c.CHARACTER_MAXIMUM_LENGTH,
        c.NUMERIC_PRECISION,
        c.NUMERIC_SCALE,
        c.IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS c
    WHERE c.TABLE_NAME = ?
    """
    params: List[Any] = [table_name]

    if schema:
        sql_cols += " AND c.TABLE_SCHEMA = ?"
        params.append(schema)

    sql_cols += " ORDER BY c.TABLE_SCHEMA, c.ORDINAL_POSITION"

    columns = _fetchall(conn, sql_cols, params)

    if not columns:
        raise HTTPException(status_code=404, detail=f"No columns found for table '{table_name}'")

    # 2) Primary keys
    sql_pk = """
    SELECT
        tc.TABLE_SCHEMA,
        tc.TABLE_NAME,
        kcu.COLUMN_NAME,
        tc.CONSTRAINT_NAME
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
    WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        AND tc.TABLE_NAME = ?
    """
    pk_params: List[Any] = [table_name]
    if schema:
        sql_pk += " AND tc.TABLE_SCHEMA = ?"
        pk_params.append(schema)

    primary_keys = _fetchall(conn, sql_pk, pk_params)

    # 3) Foreign keys (relationships)
    sql_fk = """
    SELECT
        fk.TABLE_SCHEMA AS FK_TABLE_SCHEMA,
        fk.TABLE_NAME AS FK_TABLE_NAME,
        fk.CONSTRAINT_NAME AS FK_CONSTRAINT_NAME,
        fkc.COLUMN_NAME AS FK_COLUMN_NAME,
        pk.TABLE_SCHEMA AS PK_TABLE_SCHEMA,
        pk.TABLE_NAME AS PK_TABLE_NAME,
        pkc.COLUMN_NAME AS PK_COLUMN_NAME
    FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
    INNER JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS fk
        ON rc.CONSTRAINT_NAME = fk.CONSTRAINT_NAME
        AND rc.CONSTRAINT_SCHEMA = fk.CONSTRAINT_SCHEMA
    INNER JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS pk
        ON rc.UNIQUE_CONSTRAINT_NAME = pk.CONSTRAINT_NAME
        AND rc.UNIQUE_CONSTRAINT_SCHEMA = pk.CONSTRAINT_SCHEMA
    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fkc
        ON fkc.CONSTRAINT_NAME = fk.CONSTRAINT_NAME
        AND fkc.CONSTRAINT_SCHEMA = fk.CONSTRAINT_SCHEMA
    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pkc
        ON pkc.CONSTRAINT_NAME = pk.CONSTRAINT_NAME
        AND pkc.CONSTRAINT_SCHEMA = pk.CONSTRAINT_SCHEMA
        AND pkc.ORDINAL_POSITION = fkc.ORDINAL_POSITION
    WHERE fk.TABLE_NAME = ?
    """

    fk_params: List[Any] = [table_name]
    if schema:
        sql_fk += " AND fk.TABLE_SCHEMA = ?"
        fk_params.append(schema)

    foreign_keys = _fetchall(conn, sql_fk, fk_params)

    return {
        "table": table_name,
        "columns": columns,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys,
    }


@router.get("/relationships")
def relationships(
    conn: pyodbc.Connection = Depends(get_db),
    contains_table: Optional[str] = Query(default=None, description="Filter to FK/PK tables containing substring"),
    schema: Optional[str] = Query(default=None, description="Optional schema filter for both sides"),
):
    # More complete relationship view using sys.foreign_key_*.
    sql = """
    SELECT
        OBJECT_SCHEMA_NAME(fk.parent_object_id) AS fk_schema,
        OBJECT_NAME(fk.parent_object_id) AS fk_table,
        COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS fk_column,
        OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS pk_schema,
        OBJECT_NAME(fk.referenced_object_id) AS pk_table,
        COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS pk_column,
        fk.name AS fk_name
    FROM sys.foreign_keys fk
    INNER JOIN sys.foreign_key_columns fkc
        ON fk.object_id = fkc.constraint_object_id
    """

    params: List[Any] = []

    if schema:
        sql += " WHERE (OBJECT_SCHEMA_NAME(fk.parent_object_id) = ? AND OBJECT_SCHEMA_NAME(fk.referenced_object_id) = ?)"
        params.extend([schema, schema])

    if contains_table:
        # Apply LIKE filters without knowing which side is which.
        # Use parentheses to keep logic sound.
        if " WHERE " in sql.upper():
            sql += " AND (OBJECT_NAME(fk.parent_object_id) LIKE ? OR OBJECT_NAME(fk.referenced_object_id) LIKE ?)"
        else:
            sql += " WHERE (OBJECT_NAME(fk.parent_object_id) LIKE ? OR OBJECT_NAME(fk.referenced_object_id) LIKE ?)"
        like = f"%{contains_table}%"
        params.extend([like, like])

    sql += " ORDER BY fk_schema, fk_table, fk_column"

    rels = _fetchall(conn, sql, params if params else None)
    return {"relationships": rels, "count": len(rels)}

