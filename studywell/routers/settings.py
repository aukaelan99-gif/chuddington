from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import DailyGoals
from schemas import DailyGoalsUpdate
from templates_config import templates
from auth_deps import get_current_user, User

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    if not goals:
        goals = DailyGoals()
    return templates.TemplateResponse(
        request, "settings.html", {"goals": goals, "username": user.username}
    )


@router.post("/")
async def update_settings(
    study_minutes: int = Form(120),
    calorie_target: int = Form(2000),
    exercise_minutes: int = Form(30),
    water_glasses: int = Form(8),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    data = DailyGoalsUpdate(
        study_minutes=study_minutes,
        calorie_target=calorie_target,
        exercise_minutes=exercise_minutes,
        water_glasses=water_glasses,
    )
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    if goals:
        goals.study_minutes = data.study_minutes
        goals.calorie_target = data.calorie_target
        goals.exercise_minutes = data.exercise_minutes
        goals.water_glasses = data.water_glasses
    else:
        import uuid
        goals = DailyGoals(
            id=str(uuid.uuid4()),
            user_id=user.id,
            study_minutes=data.study_minutes,
            calorie_target=data.calorie_target,
            exercise_minutes=data.exercise_minutes,
            water_glasses=data.water_glasses,
        )
        db.add(goals)
    await db.commit()
    return RedirectResponse(url="/", status_code=303)
