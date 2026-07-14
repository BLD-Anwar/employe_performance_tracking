import os
from typing import Any, Dict, Generator, List

import pyodbc

# Ensure .env is loaded before any env reads
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # dotenv is optional; if not installed, rely on process environment
    pass


PHASE1_REQUIRED_VARS = {
    "PHASE1_DB_SERVER": "PHASE1_DB_SERVER not found",
    "PHASE1_DB_NAME": "PHASE1_DB_NAME not found",
}


def _validate_env() -> None:
    for k, msg in PHASE1_REQUIRED_VARS.items():
        if not os.getenv(k):
            raise RuntimeError(msg)


def _parse_bool(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def _select_driver() -> str:
    # Prefer PHASE1_DB_DRIVER if present (keeps existing behavior if you already had it)
    driver = os.getenv("PHASE1_DB_DRIVER")
    if driver:
        return driver

    # Otherwise detect installed SQL Server ODBC drivers
    drivers = []
    try:
        drivers = list(pyodbc.drivers())
    except Exception:
        drivers = []

    sql_server_drivers = [d for d in drivers if "SQL Server" in d]
    if sql_server_drivers:
        return sql_server_drivers[0]

    # Fall back to the original default, but only after detection attempt
    return "ODBC Driver 17 for SQL Server"


def _build_connection_string_parts() -> Dict[str, str]:
    _validate_env()

    server = os.getenv("PHASE1_DB_SERVER")
    database = os.getenv("PHASE1_DB_NAME")
    trusted = os.getenv("PHASE1_DB_TRUSTED", "yes")
    user = os.getenv("PHASE1_DB_USER", "")
    password = os.getenv("PHASE1_DB_PASSWORD", "")

    trusted_bool = _parse_bool(trusted)
    driver = _select_driver()

    # Trusted connection toggle
    trusted_token = "yes" if trusted_bool else "no"

    # Security toggle
    # If using Trusted Connection, still commonly safe to trust server certificate in dev.
    # If not trusting, omit TrustServerCertificate.
    trust_server_cert_part = "TrustServerCertificate=yes;" if trusted_bool else ""

    # If user+password are provided, include them; otherwise rely on Trusted_Connection.
    # (Even if PHASE1_DB_USER/PASSWORD are empty, it's acceptable to keep Trusted_Connection.)
    if user and password and not trusted_bool:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate={'yes' if trusted_bool else 'no'};{trust_server_cert_part}"
        )
    else:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection={trusted_token};"
            f"{trust_server_cert_part}"
        )

    return {
        "server": server,
        "database": database,
        "driver": driver,
        "trusted": str(trusted_bool),
        "conn_str": conn_str,
    }


def build_phase1_connection_string() -> Dict[str, str]:
    return _build_connection_string_parts()


def get_db_conn() -> pyodbc.Connection:
    parts = build_phase1_connection_string()
    return pyodbc.connect(parts["conn_str"], autocommit=True, timeout=5)


def get_db() -> Generator[pyodbc.Connection, None, None]:
    """FastAPI dependency that yields a DB connection."""
    conn = get_db_conn()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _mask_conn_str(conn_str: str) -> str:
    # Mask common credentials tokens
    masked = conn_str
    for key in ["PWD=", "UID=", "Password=", "User="]:
        # Basic masking without assuming exact format; keep simple.
        masked = masked.replace(key, f"{key.split('=')[0]}=***")

    # Ensure TrustServerCertificate token doesn't get removed; leave it as-is
    return masked


def masked_connection_diagnostics() -> Dict[str, str]:
    parts = build_phase1_connection_string()
    return {
        "server": parts["server"],
        "database": parts["database"],
        "driver": parts["driver"],
        "trusted": parts["trusted"],
        "connection_string": _mask_conn_str(parts["conn_str"]),
    }


def fetch_test_1() -> Any:
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 as test")
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def odbc_drivers() -> List[str]:
    try:
        return list(pyodbc.drivers())
    except Exception:
        return []


from contextlib import contextmanager

@contextmanager
def db_cursor():
    parts = build_phase1_connection_string()
    conn = pyodbc.connect(parts["conn_str"], autocommit=False, timeout=5)
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def rows_to_list(cursor, rows) -> list:
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in rows]




