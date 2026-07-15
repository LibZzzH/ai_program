"""
FastAPI 入口 — 将业务逻辑层暴露为 REST API。
与 Streamlit 表现层共享全部 Service + DAO 代码，零重复。
"""

from datetime import date, datetime
import os
import secrets
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from utils.db import init_db, get_current_user_id
from utils.config import _parse_time_str
from services.task_manager import (
    create_task, start_task, complete_task, edit_task, remove_task,
    get_today_tasks, get_all_tasks, get_category_stats, move_up, move_down
)
from services.calibration import (
    calibrate_all_tasks_with_info, get_category_expansion_ratio, get_engine
)
from services.roast_generator import generate_daily_review, generate_ai_daily_review
from services.calendar_service import CalendarService
from services.auth import (
    get_user, get_user_stats, create_user, list_users, update_user, delete_user
)
from dao.settings_dao import get_setting, set_setting

init_db()


API_TOKEN = os.getenv("API_TOKEN", "").strip()
API_CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "API_CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="时间感知幻觉破除器 API",
    description="任务管理、时间校准、毒舌复盘 — 全部 RESTful",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path == "/api/health":
        return await call_next(request)

    if not API_TOKEN:
        return JSONResponse(
            status_code=503,
            content={"detail": "API_TOKEN is not configured"},
        )

    auth_header = request.headers.get("authorization", "")
    bearer_token = auth_header.removeprefix("Bearer ").strip()
    header_token = request.headers.get("x-api-token", "").strip()
    if not (
        secrets.compare_digest(bearer_token, API_TOKEN)
        or secrets.compare_digest(header_token, API_TOKEN)
    ):
        return JSONResponse(status_code=401, content={"detail": "Invalid API token"})

    return await call_next(request)


class TaskCreate(BaseModel):
    category: str
    description: str
    estimated_minutes: int
    created_date: Optional[str] = None


class TaskEdit(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    estimated_minutes: Optional[int] = None


class TaskComplete(BaseModel):
    actual_minutes: Optional[int] = None


class CalendarEvent(BaseModel):
    title: str
    start_time: str
    end_time: str
    is_busy: bool = True


class UserCreate(BaseModel):
    user_id: str
    name: str = ""
    email: str = ""


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class SettingUpdate(BaseModel):
    value: str


def _get_user_id(user_id: Optional[str] = None) -> str:
    return user_id or get_current_user_id()


# ─── 任务 API ───
@app.post("/api/tasks")
def api_create_task(task: TaskCreate, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    create_task(task.category, task.description, task.estimated_minutes, task.created_date, user_id=uid)
    return {"ok": True}


@app.get("/api/tasks")
def api_list_tasks(user_id: Optional[str] = None, today_only: bool = False):
    uid = _get_user_id(user_id)
    tasks = get_today_tasks(uid) if today_only else get_all_tasks(uid)
    return {"tasks": tasks}


@app.put("/api/tasks/{task_id}/start")
def api_start_task(task_id: int, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    start_task(task_id, uid)
    return {"ok": True}


@app.put("/api/tasks/{task_id}/complete")
def api_complete_task(task_id: int, body: TaskComplete, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    complete_task(task_id, body.actual_minutes, uid)
    return {"ok": True}


@app.put("/api/tasks/{task_id}")
def api_edit_task(task_id: int, body: TaskEdit, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    edit_task(task_id, body.category, body.description, body.estimated_minutes, user_id=uid)
    return {"ok": True}


@app.delete("/api/tasks/{task_id}")
def api_delete_task(task_id: int, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    remove_task(task_id, uid)
    return {"ok": True}


@app.put("/api/tasks/{task_id}/move-up")
def api_move_up(task_id: int, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    move_up(task_id, uid)
    return {"ok": True}


@app.put("/api/tasks/{task_id}/move-down")
def api_move_down(task_id: int, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    move_down(task_id, uid)
    return {"ok": True}


# ─── 校准 API ───
@app.get("/api/calibration")
def api_calibrate(user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    tasks = get_today_tasks(uid)
    calibrated = calibrate_all_tasks_with_info(tasks, uid)
    return {"tasks": calibrated}


@app.get("/api/calibration/ratio")
def api_expansion_ratio(category: str, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    ratio = get_category_expansion_ratio(category, uid)
    return {"category": category, "expansion_ratio": ratio}


@app.get("/api/calibration/strategies")
def api_calibration_strategies(user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    engine = get_engine(uid)
    return engine.get_strategy_info()


@app.put("/api/calibration/strategy")
def api_set_calibration_strategy(strategy: str, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    engine = get_engine(uid)
    engine.strategy = strategy
    set_setting("calibration_strategy", strategy, uid)
    return {"ok": True, "strategy": strategy}


# ─── 复盘 API ───
@app.get("/api/review")
def api_review(user_id: Optional[str] = None, use_ai: bool = False):
    uid = _get_user_id(user_id)
    tasks = get_today_tasks(uid)
    if use_ai:
        comments = generate_ai_daily_review(tasks)
        if comments is None:
            comments = generate_daily_review(tasks)
    else:
        comments = generate_daily_review(tasks)
    return {"comments": comments}


# ─── 统计 API ───
@app.get("/api/stats/categories")
def api_category_stats(user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    return {"stats": get_category_stats(uid)}


@app.get("/api/stats/user")
def api_user_stats(user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    return get_user_stats(uid)


# ─── 日历 API ───
@app.post("/api/calendar/events")
def api_add_calendar_event(body: CalendarEvent, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    cs = CalendarService(uid)
    cs.add_event(body.title, body.start_time, body.end_time, is_busy=body.is_busy)
    return {"ok": True}


@app.get("/api/calendar/events")
def api_get_calendar_events(user_id: Optional[str] = None, dt: Optional[str] = None):
    uid = _get_user_id(user_id)
    cs = CalendarService(uid)
    target = date.fromisoformat(dt) if dt else date.today()
    return {"events": cs.get_events(target)}


@app.get("/api/calendar/available")
def api_available_slots(user_id: Optional[str] = None, dt: Optional[str] = None):
    uid = _get_user_id(user_id)
    cs = CalendarService(uid)
    target = date.fromisoformat(dt) if dt else date.today()
    work_start_h, work_start_m = _parse_time_str(get_setting("work_start_hour", "9:00", uid))
    work_end_h, work_end_m = _parse_time_str(get_setting("work_end_hour", "18:00", uid))
    lunch_start_h, lunch_start_m = _parse_time_str(get_setting("lunch_start_hour", "12:00", uid))
    lunch_end_h, lunch_end_m = _parse_time_str(get_setting("lunch_end_hour", "13:00", uid))
    slots = cs.get_available_slots(target, work_start_h, work_end_h, lunch_start_h, lunch_end_h,
                                   work_start_m, work_end_m, lunch_start_m, lunch_end_m)
    return {
        "available_slots": [
            {"start": s.isoformat(), "end": e.isoformat()} for s, e in slots
        ]
    }


@app.delete("/api/calendar/events/{event_id}")
def api_delete_calendar_event(event_id: int, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    cs = CalendarService(uid)
    cs.delete_event(event_id)
    return {"ok": True}


# ─── 用户 API ───
@app.post("/api/users")
def api_create_user(body: UserCreate):
    create_user(body.user_id, body.name, body.email)
    return {"ok": True}


@app.get("/api/users")
def api_list_users():
    return {"users": list_users()}


@app.get("/api/users/{user_id}")
def api_get_user(user_id: str):
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user.to_dict()


@app.put("/api/users/{user_id}")
def api_update_user(user_id: str, body: UserUpdate):
    update_user(user_id, body.name, body.email)
    return {"ok": True}


@app.delete("/api/users/{user_id}")
def api_delete_user(user_id: str):
    delete_user(user_id)
    return {"ok": True}


# ─── 设置 API ───
@app.get("/api/settings")
def api_get_settings(user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    from dao.settings_dao import get_all_settings
    return {"settings": get_all_settings(uid)}


@app.put("/api/settings/{key}")
def api_set_setting(key: str, body: SettingUpdate, user_id: Optional[str] = None):
    uid = _get_user_id(user_id)
    set_setting(key, body.value, uid)
    return {"ok": True}


# ─── 健康检查 ───
@app.get("/api/health")
def api_health():
    return {"status": "ok", "version": "1.0.0"}
