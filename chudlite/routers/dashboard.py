from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from database import get_session
from models import DailyGoals, StudySession, MealEntry, WaterLog, Workout
from services import analytics_service
from templates_config import templates
from auth_deps import get_current_user, User

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    today = date.today()
    goals = await analytics_service.get_goals(db, user.id)
    study_minutes = max((goals.study_minutes if goals else 120), 1)
    exercise_minutes = max((goals.exercise_minutes if goals else 30), 1)
    calorie_target = max((goals.calorie_target if goals else 2000), 1)
    water_glasses = max((goals.water_glasses if goals else 8), 1)

    study_m = (
        await db.execute(
            select(func.sum(StudySession.duration_minutes)).where(
                StudySession.date == today, StudySession.user_id == user.id
            )
        )
    ).scalar() or 0
    ex_m = (
        await db.execute(
            select(func.sum(Workout.duration_minutes)).where(
                Workout.date == today,
                Workout.finished == True,
                Workout.user_id == user.id,
            )
        )
    ).scalar() or 0
    cal = (
        await db.execute(
            select(func.sum(MealEntry.calories)).where(
                MealEntry.date == today, MealEntry.user_id == user.id
            )
        )
    ).scalar() or 0
    water_log = (
        await db.execute(
            select(WaterLog).where(WaterLog.date == today, WaterLog.user_id == user.id)
        )
    ).scalar_one_or_none()
    water = water_log.glasses if water_log else 0

    score = await analytics_service.get_wellbeing_score(db, user.id)

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
            "username": user.username,
        },
    )
