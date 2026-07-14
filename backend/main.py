import traceback
import sys
import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

# Ensure backend directory is in sys.path so nested relative-like imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import verify_token

from database import (
    build_phase1_connection_string,
    fetch_test_1,
    odbc_drivers,
    masked_connection_diagnostics,
)

# Import all routers
from routers.meta            import router as meta_router
from routers.auth            import router as auth_router
from routers.dashboard       import router as dashboard_router
from routers.officers        import router as officers_router
from routers.tasks           import router as tasks_router
from routers.performance     import router as performance_router
from routers.reports         import router as reports_router
from routers.settings        import router as settings_router
from routers.employee        import router as employee_router
from routers.meeting         import router as meeting_router
from routers.farmer_tracking import router as farmer_tracking_router

def _startup_log_db_config():
    try:
        diag = masked_connection_diagnostics()
        print("[db-startup] server:", diag.get("server"))
        print("[db-startup] database:", diag.get("database"))
        print("[db-startup] trusted:", diag.get("trusted"))
        print("[db-startup] driver:", diag.get("driver"))
    except Exception as e:
        print("[db-startup-error]", str(e))


app = FastAPI(title="AgriPulse Unified API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith(".html") or "/manager/" in path or "/employee/" in path:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.on_event("startup")
def on_startup():
    _startup_log_db_config()


@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "AgriPulse Unified API", "version": "3.0.0"}


@app.get("/test-db")
def test_db(credentials: dict = Depends(verify_token)):
    if credentials.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Forbidden: Manager access required")
    try:
        fetch_test_1()
        return {"status": "connected"}
    except Exception as e:
        print("[test-db-error] Database connection failed:")
        traceback.print_exc()
        return {"status": "error", "detail": "Database connection failed"}


# @app.get("/debug/db")
# def debug_db():
#     try:
#         parts = build_phase1_connection_string()
#         return {
#             "server": parts["server"],
#             "database": parts["database"],
#             "driver": parts["driver"],
#             "env_loaded": True,
#         }
#     except Exception:
#         return {
#             "server": None,
#             "database": None,
#             "driver": None,
#             "env_loaded": False,
#         }
# 
# 
# @app.get("/debug/odbc")
# def debug_odbc():
#     return {"drivers": odbc_drivers()}
# 
# 
# @app.get("/debug/env")
# def debug_env():
#     return {
#         "PHASE1_DB_SERVER": os.getenv("PHASE1_DB_SERVER"),
#         "PHASE1_DB_NAME": os.getenv("PHASE1_DB_NAME"),
#         "PHASE1_DB_TRUSTED": os.getenv("PHASE1_DB_TRUSTED"),
#     }


# Include all routers
app.include_router(meta_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(officers_router)
app.include_router(tasks_router)
app.include_router(performance_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(employee_router)
app.include_router(meeting_router)
app.include_router(farmer_tracking_router)


# ── Serve frontend static files ─────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(FRONTEND_DIR):
    # Mount shared assets (JS, CSS)
    assets_dir = os.path.join(FRONTEND_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Mount uploads directory for meeting photos etc.
    uploads_dir = os.path.join(FRONTEND_DIR, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    # Mount manager pages
    manager_dir = os.path.join(FRONTEND_DIR, "manager")
    if os.path.exists(manager_dir):
        app.mount("/manager", StaticFiles(directory=manager_dir, html=True), name="manager")

    # Mount employee pages
    employee_dir = os.path.join(FRONTEND_DIR, "employee")
    if os.path.exists(employee_dir):
        app.mount("/employee", StaticFiles(directory=employee_dir, html=True), name="employee")

    # Root → Unified login page
    @app.get("/")
    def root():
        return RedirectResponse(url="/login.html")

    @app.get("/manager")
    def manager_root():
        return RedirectResponse(url="/manager/login.html")

    @app.get("/employee")
    def employee_root():
        return RedirectResponse(url="/employee/login.html")

    @app.get("/login")
    @app.get("/login.html")
    def serve_login():
        return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))







