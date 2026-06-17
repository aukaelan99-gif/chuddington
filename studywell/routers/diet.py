from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from database import get_session
from schemas import MealEntryCreate
from services import diet_service
from models import MealType, DailyGoals
from templates_config import templates
from auth_deps import get_current_user, User

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def diet_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    today = date.today()
    meals = await diet_service.get_meals_by_date(db, today, user.id)
    macros = await diet_service.get_macro_totals(db, today, user.id)
    water = await diet_service.get_water_today(db, user.id)
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    calorie_target = goals.calorie_target if goals else 2000
    water_glasses = goals.water_glasses if goals else 8

    meals_by_type = {t.value: [m for m in meals if m.meal_type == t] for t in MealType}
    calorie_pct = min(100, round(macros["calories"] / max(calorie_target, 1) * 100))
    total_macros = macros["protein"] + macros["carbs"] + macros["fat"]

    return templates.TemplateResponse(
        request,
        "diet.html",
        {
            "meals": meals,
            "meals_by_type": meals_by_type,
            "macros": macros,
            "water": water,
            "water_goal": water_glasses,
            "calorie_target": calorie_target,
            "calorie_pct": calorie_pct,
            "today": today,
            "total_macros": total_macros,
            "meal_types": [t.value for t in MealType],
            "username": user.username,
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def add_meal(
    request: Request,
    name: str = Form(...),
    meal_type: MealType = Form(...),
    calories: int = Form(...),
    protein_g: float = Form(None),
    carbs_g: float = Form(None),
    fat_g: float = Form(None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    data = MealEntryCreate(
        name=name,
        meal_type=meal_type,
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
    )
    meal = await diet_service.create_meal(db, data, date.today(), user.id)
    return templates.TemplateResponse(
        request, "partials/meal_row.html", {"meal": meal}
    )


@router.post("/water", response_class=HTMLResponse)
async def update_water(
    request: Request,
    glasses: int = Form(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    log = await diet_service.upsert_water(db, max(0, min(glasses, 20)), user.id)
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    water_glasses = goals.water_glasses if goals else 8
    return templates.TemplateResponse(
        request, "partials/water_widget.html", {"water": log.glasses, "water_goal": water_glasses}
    )

