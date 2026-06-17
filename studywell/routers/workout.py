from datetime import date
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import ExerciseType
from services import workout_service
from templates_config import templates

router = APIRouter()


@router.post("/new")
async def new_workout(
    name: str = Form(""),
    db: AsyncSession = Depends(get_session),
):
    workout = await workout_service.create_workout(db, name or None, date.today())
    return RedirectResponse(url=f"/workout/{workout.id}", status_code=303)


@router.get("/{workout_id}", response_class=HTMLResponse)
async def workout_page(request: Request, workout_id: str, db: AsyncSession = Depends(get_session)):
    workout = await workout_service.get_workout(db, workout_id)
    if not workout:
        return RedirectResponse(url="/exercise", status_code=303)
    return templates.TemplateResponse(request, "workout.html", {"workout": workout})


@router.get("/search", response_class=JSONResponse)
async def search_exercises(q: str = ""):
    results = workout_service.search_exercises(q)
    return JSONResponse(content=results)


@router.post("/{workout_id}/add-exercise", response_class=HTMLResponse)
async def add_exercise(
    request: Request,
    workout_id: str,
    name: str = Form(...),
    exercise_type: ExerciseType = Form(...),
    db: AsyncSession = Depends(get_session),
):
    workout = await workout_service.get_workout(db, workout_id)
    order = len(workout.exercises) if workout else 0
    ex = await workout_service.add_exercise(db, workout_id, name, exercise_type, order)
    return templates.TemplateResponse(
        request,
        "partials/workout_exercise_block.html",
        {"ex": ex, "workout_id": workout_id},
    )


@router.post("/{workout_id}/exercise/{ex_id}/add-set", response_class=HTMLResponse)
async def add_set(
    request: Request,
    workout_id: str,
    ex_id: str,
    reps: int = Form(None),
    weight_kg: float = Form(None),
    duration_minutes: float = Form(None),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from models import WorkoutExercise
    r = await db.execute(
        select(WorkoutExercise)
        .where(WorkoutExercise.id == ex_id)
        .options(selectinload(WorkoutExercise.sets))
    )
    ex = r.scalar_one_or_none()
    set_number = len(ex.sets) + 1 if ex else 1
    s = await workout_service.add_set(db, ex_id, set_number, reps, weight_kg, duration_minutes)
    return templates.TemplateResponse(
        request,
        "partials/workout_set_row.html",
        {"s": s, "ex": ex},
    )


@router.post("/{workout_id}/finish")
async def finish_workout(workout_id: str, db: AsyncSession = Depends(get_session)):
    await workout_service.finish_workout(db, workout_id)
    return RedirectResponse(url="/exercise", status_code=303)
