from datetime import date
import json
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import ExerciseType, MuscleGroup
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


@router.get("/search", response_class=HTMLResponse)
async def search_exercises(
    request: Request,
    q: str = "",
    muscle_group: str = "all",
    db: AsyncSession = Depends(get_session),
):
    results = await workout_service.search_exercises(db, q, muscle_group)
    return templates.TemplateResponse(
        request,
        "partials/workout_search_results.html",
        {"results": results},
    )


@router.get("/{workout_id}", response_class=HTMLResponse)
async def workout_page(request: Request, workout_id: str, db: AsyncSession = Depends(get_session)):
    workout = await workout_service.get_workout(db, workout_id)
    if not workout:
        return RedirectResponse(url="/exercise", status_code=303)
    return templates.TemplateResponse(request, "workout.html", {"workout": workout})


@router.post("/{workout_id}/add-exercise", response_class=HTMLResponse)
async def add_exercise(
    request: Request,
    workout_id: str,
    name: str = Form(...),
    exercise_type: ExerciseType = Form(...),
    muscle_group: MuscleGroup = Form(MuscleGroup.other),
    db: AsyncSession = Depends(get_session),
):
    workout = await workout_service.get_workout(db, workout_id)
    order = len(workout.exercises) if workout else 0
    ex = await workout_service.add_exercise(db, workout_id, name, exercise_type, muscle_group, order)
    return templates.TemplateResponse(
        request,
        "partials/workout_exercise_block.html",
        {"ex": ex, "workout_id": workout_id},
    )


@router.post("/{workout_id}/exercise/{ex_id}/plan-set", response_class=HTMLResponse)
async def plan_set(
    request: Request,
    workout_id: str,
    ex_id: str,
    db: AsyncSession = Depends(get_session),
):
    ex = await workout_service.get_workout_exercise(db, ex_id)
    s = await workout_service.create_planned_set(db, ex_id)
    return templates.TemplateResponse(
        request,
        "partials/workout_set_row.html",
        {"s": s, "ex": ex},
    )


@router.post("/{workout_id}/exercise/{ex_id}/set/{set_id}/save", response_class=HTMLResponse)
async def save_set(
    request: Request,
    workout_id: str,
    ex_id: str,
    set_id: str,
    reps: int = Form(None),
    weight_kg: float = Form(None),
    duration_minutes: float = Form(None),
    db: AsyncSession = Depends(get_session),
):
    s = await workout_service.update_set(db, set_id, reps, weight_kg, duration_minutes)
    ex = await workout_service.get_workout_exercise(db, ex_id)
    return templates.TemplateResponse(
        request,
        "partials/workout_set_row.html",
        {"s": s, "ex": ex},
    )


@router.post("/{workout_id}/exercise/{ex_id}/set/{set_id}/delete", response_class=HTMLResponse)
async def remove_set(
    request: Request,
    workout_id: str,
    ex_id: str,
    set_id: str,
    db: AsyncSession = Depends(get_session),
):
    ex = await workout_service.delete_set(db, ex_id, set_id)
    return templates.TemplateResponse(
        request,
        "partials/workout_set_rows.html",
        {"ex": ex, "workout_id": workout_id},
    )


@router.post("/{workout_id}/finish")
async def finish_workout(
    workout_id: str,
    sets_payload: str = Form("[]"),
    workout_minutes: float | None = Form(None),
    db: AsyncSession = Depends(get_session),
):
    try:
        payload = json.loads(sets_payload)
    except json.JSONDecodeError:
        payload = []
    await workout_service.finalize_workout_with_sets(db, workout_id, payload, workout_minutes)
    return RedirectResponse(url="/exercise", status_code=303)


@router.post("/{workout_id}/delete")
async def cancel_workout(workout_id: str, db: AsyncSession = Depends(get_session)):
    await workout_service.delete_workout(db, workout_id)
    return RedirectResponse(url="/exercise", status_code=303)
