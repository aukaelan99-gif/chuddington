from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from database import get_session
from schemas import StudySessionCreate
from services import study_service
from templates_config import templates
from auth_deps import get_current_user, User

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def study_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    today = date.today()
    sessions = await study_service.get_sessions_by_date(db, today, user.id)
    weekly_minutes = await study_service.get_daily_minutes_last_7(db, user.id)
    weekly_hours = [round(m / 60, 2) for m in weekly_minutes]
    labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]
    return templates.TemplateResponse(
        request,
        "study.html",
        {
            "sessions": sessions,
            "today": today,
            "weekly_hours": weekly_hours,
            "labels": labels,
            "username": user.username,
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def add_session(
    request: Request,
    subject: str = Form(...),
    duration_minutes: int = Form(...),
    notes: str = Form(None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    data = StudySessionCreate(subject=subject, duration_minutes=duration_minutes, notes=notes)
    session = await study_service.create_session(db, data, date.today(), user.id)
    return templates.TemplateResponse(
        request, "partials/study_row.html", {"session": session}
    )
