from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from database import get_session
from schemas import ExerciseEntryCreate
from services import exercise_service
from models import Intensity
from templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def exercise_page(request: Request, db: AsyncSession = Depends(get_session)):
    today = date.today()
    entries = await exercise_service.get_entries_by_date(db, today)
    weekly_minutes = await exercise_service.get_daily_minutes_last_7(db)
    weekly_total = await exercise_service.get_weekly_total(db)
    streak = await exercise_service.get_streak(db)
    labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]
    return templates.TemplateResponse(
        request,
        "exercise.html",
        {
            "entries": entries,
            "today": today,
            "weekly_minutes": weekly_minutes,
            "weekly_total": weekly_total,
            "streak": streak,
            "labels": labels,
            "intensities": [i.value for i in Intensity],
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def add_entry(
    request: Request,
    activity: str = Form(...),
    duration_minutes: int = Form(...),
    intensity: Intensity = Form(...),
    db: AsyncSession = Depends(get_session),
):
    data = ExerciseEntryCreate(
        activity=activity, duration_minutes=duration_minutes, intensity=intensity
    )
    entry = await exercise_service.create_entry(db, data, date.today())
    return templates.TemplateResponse(
        request, "partials/exercise_row.html", {"entry": entry}
    )
