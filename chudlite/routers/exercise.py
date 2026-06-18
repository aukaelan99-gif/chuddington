from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from database import get_session
from models import DailyGoals, ExerciseCatalog, ExerciseType, MuscleGroup
from services import workout_service
from templates_config import templates
from auth_deps import get_current_user, User

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def exercise_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    today = date.today()
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    exercise_goal = goals.exercise_minutes if goals else 30
    weekly_total = await workout_service.get_weekly_total_minutes(db, user.id)
    streak = await workout_service.get_streak_days(db, user.id)
    muscle_dist = await workout_service.get_muscle_distribution_last_7(db, user.id)

    dist_labels = [k.replace("_", " ").title() for k in muscle_dist.keys()]
    dist_values = list(muscle_dist.values())
    return templates.TemplateResponse(
        request,
        "exercise.html",
        {
            "today": today,
            "exercise_goal": exercise_goal,
            "weekly_total": weekly_total,
            "streak": streak,
            "dist_labels": dist_labels,
            "dist_values": dist_values,
            "username": user.username,
        },
    )


@router.post("/goal")
async def update_exercise_goal(
    exercise_minutes: int = Form(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    value = max(5, min(exercise_minutes, 300))
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    if goals:
        goals.exercise_minutes = value
    else:
        import uuid
        goals = DailyGoals(id=str(uuid.uuid4()), user_id=user.id, exercise_minutes=value)
        db.add(goals)
    await db.commit()
    return RedirectResponse(url="/exercise", status_code=303)


@router.post("/custom")
async def add_custom_exercise(
    name: str = Form(...),
    exercise_type: ExerciseType = Form(...),
    muscle_group: MuscleGroup = Form(MuscleGroup.other),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _ = user
    clean_name = (name or "").strip()[:100]
    if not clean_name:
        return RedirectResponse(url="/exercise", status_code=303)

    r = await db.execute(select(ExerciseCatalog).where(ExerciseCatalog.name == clean_name))
    ex = r.scalar_one_or_none()
    if ex:
        ex.exercise_type = exercise_type
        ex.muscle_group = muscle_group
    else:
        db.add(
            ExerciseCatalog(
                name=clean_name,
                exercise_type=exercise_type,
                muscle_group=muscle_group,
            )
        )
    await db.commit()
    return RedirectResponse(url="/exercise", status_code=303)

