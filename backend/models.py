"""
models.py  –  Pydantic request/response models for AgriPulse API
"""
from pydantic import BaseModel
from typing import Optional, List


# ── Auth ────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class SessionUser(BaseModel):
    id: int
    username: str
    name: str
    role: str   # "manager" | "officer"
    access_token: Optional[str] = None


# ── Officers ────────────────────────────────────────────────────────────────
class OfficerOut(BaseModel):
    id: int
    name: str
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_staff: bool
    is_blocked: bool
    joined: Optional[str] = None
    last_login: Optional[str] = None
    activities: int = 0
    total_assigned: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    pending_tasks: int = 0
    overdue_tasks: int = 0
    farmers_assigned: int = 0

class BlockRequest(BaseModel):
    is_blocked: bool


# ── Dashboard ───────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    overdue_tasks: int
    period_label: str

class WeekPoint(BaseModel):
    week_label: str
    count: int
    is_peak: bool

class WorkTypePoint(BaseModel):
    label: str
    count: int
    pct: float


class OfficerDashboardProfile(BaseModel):
    id: int
    name: str
    username: str
    email: Optional[str] = None
    role: str
    status: str
    initials: str
    joined: Optional[str] = None
    last_login: Optional[str] = None
    region: str = "—"
    department: str = "Field Operations"
    is_blocked: bool = False


class OfficerDashboardStats(BaseModel):
    total_tasks: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    pending_tasks: int = 0
    overdue_tasks: int = 0
    farmers_assigned: int = 0
    villages_count: int = 0
    activities_count: int = 0
    completion_score: int = 0


class OfficerDashboardTask(BaseModel):
    task_id: int
    task_name: str
    work_type: str
    status: str
    start_date: str
    end_date: str
    village: str
    farmer_count: int = 0
    completion_pct: int = 0
    month: Optional[int] = None
    week: Optional[int] = None


class OfficerDashboardActivity(BaseModel):
    id: int
    task_name: str
    work_type: str
    village: str
    action: str
    date: str
    remarks: Optional[str] = None


class OfficerDashboardAlert(BaseModel):
    type: str
    message: str
    created_at: Optional[str] = None


class OfficerDashboardInsight(BaseModel):
    content: str


class OfficerWorkTypeStat(BaseModel):
    work_type_id: Optional[int] = None
    label: str
    task_count: int = 0
    tasks_completed: int = 0
    tasks_remaining: int = 0
    farmers_total: int = 0
    farmers_completed: int = 0
    farmers_remaining: int = 0
    completion_pct: float = 0.0
    is_master: bool = True


class OfficerDashboardResponse(BaseModel):
    profile: OfficerDashboardProfile
    stats: OfficerDashboardStats
    work_type_stats: List[OfficerWorkTypeStat] = []
    work_types: List[WorkTypePoint] = []
    weekly: List[WeekPoint] = []
    tasks: List[OfficerDashboardTask] = []
    activities: List[OfficerDashboardActivity] = []
    alerts: List[OfficerDashboardAlert] = []
    insights: List[OfficerDashboardInsight] = []
    day_activity: List[int] = []


class TopOfficer(BaseModel):
    rank: int
    name: str
    tasks: int

class RecentActivity(BaseModel):
    task: str
    work_type: str
    village: str
    date: str
    officer: str


# ── Settings ────────────────────────────────────────────────────────────────
class ProfileUpdate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# ── Reports ─────────────────────────────────────────────────────────────────
class TaskStats(BaseModel):
    total_tasks: int = 0
    completed: int = 0
    in_progress: int = 0
    pending: int = 0
    overdue: int = 0
