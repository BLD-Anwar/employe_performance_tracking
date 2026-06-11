"""DEPRECATED.

This module is kept for backward compatibility only.
All active SQL Server connectivity must use backend/database.py (PHASE1_*).
"""

import os
from typing import Generator

import pyodbc
from fastapi import Depends


# Intentionally leave existing implementation untouched.


def _build_connection_string() -> str:
    """Build SQL Server connection string from environment variables.


    Expected env vars (use any combination):
    - DB_SERVER
    - DB_NAME
    - DB_USER
    - DB_PASSWORD
    - DB_DRIVER (optional, default: ODBC Driver 17 for SQL Server)
    - DB_TRUST_CERT (optional: true/false)

    If DB_USER/DB_PASSWORD are not provided, uses Windows auth style connection
    via Trusted_Connection.
    """

    server = os.getenv("DB_SERVER")
    db_name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    trust_cert = os.getenv("DB_TRUST_CERT", "false").lower() in {"1", "true", "yes"}

    if not server or not db_name:
        raise RuntimeError(
            "Missing required database env vars: DB_SERVER and DB_NAME"
        )

    trust_part = ";TrustServerCertificate=yes" if trust_cert else ""

    if user and password:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={db_name};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate={'yes' if trust_cert else 'no'}{trust_part}"
        )

    # Fallback to Trusted Connection (Windows auth)
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={db_name};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate={'yes' if trust_cert else 'no'}{trust_part}"
    )


def get_connection() -> pyodbc.Connection:
    """Create a new DB connection."""
    conn_str = _build_connection_string()
    # autocommit=False for transactional integrity.
    return pyodbc.connect(conn_str, autocommit=False)


def get_db() -> Generator[pyodbc.Connection, None, None]:
    """FastAPI dependency that yields a DB connection."""
    conn = get_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass

