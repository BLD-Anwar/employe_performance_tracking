import traceback

from fastapi import FastAPI

from backend.database import (
    build_phase1_connection_string,
    fetch_test_1,
    odbc_drivers,
    masked_connection_diagnostics,
)

from backend.routers.meta import router as meta_router



def _startup_log_db_config():
    try:
        diag = masked_connection_diagnostics()
        # Passwords are already masked in connection_string; don't print that unless you want full string.
        print("[db-startup] server:", diag.get("server"))
        print("[db-startup] database:", diag.get("database"))
        print("[db-startup] trusted:", diag.get("trusted"))
        print("[db-startup] driver:", diag.get("driver"))
    except Exception as e:
        # Fail loudly with clear env errors
        print("[db-startup-error]", str(e))




app = FastAPI(title="AgriPulse V2")


@app.on_event("startup")
def on_startup():
    _startup_log_db_config()



@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/test-db")
def test_db():
    try:
        fetch_test_1()
        return {"status": "connected"}
    except Exception as e:
        # Provide structured details for root-cause analysis
        details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "full_exception": traceback.format_exc(),
        }

        # If this is a pyodbc.Error, it may contain multiple arguments with SQLSTATE/native error
        try:
            import pyodbc  # local import to avoid hard dependency in module import

            if isinstance(e, pyodbc.Error):
                details["pyodbc_args"] = [str(arg) for arg in getattr(e, "args", ())]
        except Exception:
            pass

        return details



@app.get("/debug/db")
def debug_db():
    try:
        parts = build_phase1_connection_string()
        return {
            "server": parts["server"],
            "database": parts["database"],
            "driver": parts["driver"],
            "env_loaded": True,
        }
    except Exception:
        return {
            "server": None,
            "database": None,
            "driver": None,
            "env_loaded": False,
        }


@app.get("/debug/odbc")
def debug_odbc():
    return {"drivers": odbc_drivers()}


@app.get("/debug/env")
def debug_env():
    return {
        "PHASE1_DB_SERVER": None if "PHASE1_DB_SERVER" not in __import__("os").environ else __import__("os").environ.get("PHASE1_DB_SERVER"),
        "PHASE1_DB_NAME": None if "PHASE1_DB_NAME" not in __import__("os").environ else __import__("os").environ.get("PHASE1_DB_NAME"),
        "PHASE1_DB_TRUSTED": None if "PHASE1_DB_TRUSTED" not in __import__("os").environ else __import__("os").environ.get("PHASE1_DB_TRUSTED"),
    }


app.include_router(meta_router)

# Manager + Employee Sprint 2 routers (no auth/jwt changes)
from backend.routers.employee import router as employee_router
from backend.routers.tasks import router as tasks_router

app.include_router(employee_router)
app.include_router(tasks_router)






