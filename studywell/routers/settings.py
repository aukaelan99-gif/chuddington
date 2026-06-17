from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import DailyGoals
from schemas import DailyGoalsUpdate
from templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_session)):
    goals = await db.get(DailyGoals, 1)
    if not goals:
        goals = DailyGoals()
    return templates.TemplateResponse(request, "settings.html", {"goals": goals})


@router.post("/")
async def update_settings(
    study_minutes: int = Form(120),
    calorie_target: int = Form(2000),
    exercise_minutes: int = Form(30),
    water_glasses: int = Form(8),
    db: AsyncSession = Depends(get_session),
):
    data = DailyGoalsUpdate(
        study_minutes=study_minutes,
        calorie_target=calorie_target,
        exercise_minutes=exercise_minutes,
        water_glasses=water_glasses,
    )
    goals = await db.get(DailyGoals, 1)
    if goals:
        goals.study_minutes = data.study_minutes
        goals.calorie_target = data.calorie_target
        goals.exercise_minutes = data.exercise_minutes
        goals.water_glasses = data.water_glasses
    else:
        goals = DailyGoals(
            id=1,
            study_minutes=data.study_minutes,
            calorie_target=data.calorie_target,
            exercise_minutes=data.exercise_minutes,
            water_glasses=data.water_glasses,
        )
        db.add(goals)
    await db.commit()
    return RedirectResponse(url="/", status_code=303)
