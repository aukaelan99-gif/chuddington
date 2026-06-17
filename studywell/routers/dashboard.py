from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from database import get_session
from models import DailyGoals, StudySession, ExerciseEntry, MealEntry, WaterLog
from services import analytics_service
from templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_session)):
    today = date.today()
    goals = await db.get(DailyGoals, 1)
    study_minutes = goals.study_minutes if goals else 120
    exercise_minutes = goals.exercise_minutes if goals else 30
    calorie_target = goals.calorie_target if goals else 2000
    water_glasses = goals.water_glasses if goals else 8

    study_m = (
        await db.execute(
            select(func.sum(StudySession.duration_minutes)).where(StudySession.date == today)
        )
    ).scalar() or 0
    ex_m = (
        await db.execute(
            select(func.sum(ExerciseEntry.duration_minutes)).where(ExerciseEntry.date == today)
        )
    ).scalar() or 0
    cal = (
        await db.execute(
            select(func.sum(MealEntry.calories)).where(MealEntry.date == today)
        )
    ).scalar() or 0
    water_log = (
        await db.execute(select(WaterLog).where(WaterLog.date == today))
    ).scalar_one_or_none()
    water = water_log.glasses if water_log else 0

    score = await analytics_service.get_wellbeing_score(db)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "study_hours": round(study_m / 60, 1),
            "study_goal_hours": round(study_minutes / 60, 1),
            "study_pct": min(100, round(study_m / study_minutes * 100)),
            "exercise_mins": ex_m,
            "exercise_goal": exercise_minutes,
            "exercise_pct": min(100, round(ex_m / exercise_minutes * 100)),
            "calories": cal,
            "calorie_target": calorie_target,
            "calorie_pct": min(100, round(cal / calorie_target * 100)),
            "water": water,
            "water_goal": water_glasses,
            "water_pct": min(100, round(water / water_glasses * 100)),
            "score": score,
            "today": today,
        },
    )
