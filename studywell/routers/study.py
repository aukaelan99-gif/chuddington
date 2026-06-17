from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from database import get_session
from schemas import StudySessionCreate
from services import study_service
from templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def study_page(request: Request, db: AsyncSession = Depends(get_session)):
    today = date.today()
    sessions = await study_service.get_sessions_by_date(db, today)
    weekly_minutes = await study_service.get_daily_minutes_last_7(db)
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
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def add_session(
    request: Request,
    subject: str = Form(...),
    duration_minutes: int = Form(...),
    notes: str = Form(None),
    db: AsyncSession = Depends(get_session),
):
    data = StudySessionCreate(subject=subject, duration_minutes=duration_minutes, notes=notes)
    session = await study_service.create_session(db, data, date.today())
    return templates.TemplateResponse(
        request, "partials/study_row.html", {"session": session}
    )
