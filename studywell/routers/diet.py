from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from database import get_session
from schemas import MealEntryCreate
from services import diet_service
from models import MealType, DailyGoals
from templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def diet_page(request: Request, db: AsyncSession = Depends(get_session)):
    today = date.today()
    meals = await diet_service.get_meals_by_date(db, today)
    macros = await diet_service.get_macro_totals(db, today)
    water = await diet_service.get_water_today(db)
    goals = await db.get(DailyGoals, 1)
    calorie_target = goals.calorie_target if goals else 2000
    water_glasses = goals.water_glasses if goals else 8

    meals_by_type = {t.value: [m for m in meals if m.meal_type == t] for t in MealType}
    calorie_pct = min(100, round(macros["calories"] / calorie_target * 100))
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
):
    data = MealEntryCreate(
        name=name,
        meal_type=meal_type,
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
    )
    meal = await diet_service.create_meal(db, data, date.today())
    return templates.TemplateResponse(
        request, "partials/meal_row.html", {"meal": meal}
    )


@router.post("/water", response_class=HTMLResponse)
async def update_water(
    request: Request,
    glasses: int = Form(...),
    db: AsyncSession = Depends(get_session),
):
    log = await diet_service.upsert_water(db, max(0, min(glasses, 20)))
    water_goal = (await db.get(DailyGoals, 1) or None)
    water_glasses = water_goal.water_glasses if water_goal else 8
    return templates.TemplateResponse(
        request, "partials/water_widget.html", {"water": log.glasses, "water_goal": water_glasses}
    )
