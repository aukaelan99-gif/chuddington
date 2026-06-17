from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from database import get_session
from services import workout_service
from templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def exercise_page(request: Request, db: AsyncSession = Depends(get_session)):
    today = date.today()
    weekly_total = await workout_service.get_weekly_total_minutes(db)
    streak = await workout_service.get_streak_days(db)
    muscle_dist = await workout_service.get_muscle_distribution_last_7(db)

    dist_labels = [k.replace("_", " ").title() for k in muscle_dist.keys()]
    dist_values = list(muscle_dist.values())
    return templates.TemplateResponse(
        request,
        "exercise.html",
        {
            "today": today,
            "weekly_total": weekly_total,
            "streak": streak,
            "dist_labels": dist_labels,
            "dist_values": dist_values,
        },
    )
