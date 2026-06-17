from datetime import date
import json

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_deps import User, get_current_user
from database import get_session
from models import DailyGoals, MealType
from schemas import MealEntryCreate
from services import diet_service
from templates_config import templates

router = APIRouter()


async def _build_diet_summary_context(db: AsyncSession, user_id: str, today: date) -> dict:
    macros = await diet_service.get_macro_totals(db, today, user_id)

    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user_id))
    goals = r.scalar_one_or_none()
    protein_target = goals.protein_target if goals else 150
    carbs_target = goals.carbs_target if goals else 250
    fat_target = goals.fat_target if goals else 70
    calorie_target = protein_target * 4 + carbs_target * 4 + fat_target * 9
    calorie_pct = min(100, round(macros["calories"] / max(calorie_target, 1) * 100))
    total_macros = macros["protein"] + macros["carbs"] + macros["fat"]

    return {
        "macros": macros,
        "protein_target": protein_target,
        "carbs_target": carbs_target,
        "fat_target": fat_target,
        "calorie_target": calorie_target,
        "calorie_pct": calorie_pct,
        "total_macros": total_macros,
    }


@router.get("/", response_class=HTMLResponse)
async def diet_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    today = date.today()
    meals = await diet_service.get_meals_by_date(db, today, user.id)
    saved_meals = await diet_service.get_recent_meals(db, user.id, limit=50)
    saved_meal_templates = await diet_service.get_saved_meal_templates(db, user.id)
    summary = await _build_diet_summary_context(db, user.id, today)
    water = await diet_service.get_water_today(db, user.id)
    custom_foods = await diet_service.get_custom_foods(db, user.id)

    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    water_glasses = goals.water_glasses if goals else 8

    return templates.TemplateResponse(
        request,
        "diet.html",
        {
            "meals": meals,
            "saved_meals": saved_meals,
            **summary,
            "water": water,
            "water_goal": water_glasses,
            "today": today,
            "meal_types": [t.value for t in MealType],
            "custom_foods": custom_foods,
            "saved_meal_templates": saved_meal_templates,
            "username": user.username,
        },
    )


@router.get("/manage", response_class=HTMLResponse)
async def manage_saved_diet_data(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    custom_foods = await diet_service.get_custom_foods(db, user.id)
    saved_meal_templates = await diet_service.get_saved_meal_templates(db, user.id)
    return templates.TemplateResponse(
        request,
        "diet_manage.html",
        {
            "custom_foods": custom_foods,
            "saved_meal_templates": saved_meal_templates,
            "meal_types": [t.value for t in MealType],
            "username": user.username,
        },
    )


@router.get("/saved-meals/manage", response_class=HTMLResponse)
async def manage_logged_meals_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    saved_meals = await diet_service.get_recent_meals(db, user.id, limit=100)
    message = request.query_params.get("message")
    return templates.TemplateResponse(
        request,
        "diet_saved_meals_manage.html",
        {
            "saved_meals": saved_meals,
            "meal_types": [t.value for t in MealType],
            "message": message,
            "username": user.username,
        },
    )


@router.post("/saved-meals/manage/{meal_id}/update")
async def update_logged_meal(
    meal_id: str,
    name: str = Form(...),
    meal_type: MealType = Form(...),
    date_value: date = Form(...),
    calories: int = Form(...),
    protein_g: float = Form(0.0),
    carbs_g: float = Form(0.0),
    fat_g: float = Form(0.0),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ok = await diet_service.update_meal(
        db,
        meal_id,
        user.id,
        name,
        meal_type,
        calories,
        protein_g,
        carbs_g,
        fat_g,
        date_value,
    )
    if not ok:
        return RedirectResponse(url="/diet/saved-meals/manage?message=not_found", status_code=303)
    return RedirectResponse(url="/diet/saved-meals/manage?message=updated", status_code=303)


@router.post("/saved-meals/manage/{meal_id}/delete")
async def delete_logged_meal_manage(
    meal_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await diet_service.delete_meal(db, meal_id, user.id)
    return RedirectResponse(url="/diet/saved-meals/manage?message=deleted", status_code=303)


@router.get("/summary", response_class=HTMLResponse)
async def diet_summary_fragment(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    summary = await _build_diet_summary_context(db, user.id, date.today())
    return templates.TemplateResponse(request, "partials/diet_summary.html", summary)


@router.get("/foods/search")
async def search_foods(
    q: str = "",
    category: str = "all",
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    results = await diet_service.search_food_items(db, q, user.id, category)
    return JSONResponse(results)


@router.post("/foods/custom", response_class=HTMLResponse)
async def add_custom_food(
    request: Request,
    name: str = Form(...),
    category: str = Form("other"),
    base_grams: float = Form(100.0),
    protein_g: float = Form(0.0),
    carbs_g: float = Form(0.0),
    fat_g: float = Form(0.0),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if name.strip():
        await diet_service.create_custom_food(
            db,
            user.id,
            name,
            category,
            base_grams,
            max(0.0, min(protein_g, 500.0)),
            max(0.0, min(carbs_g, 500.0)),
            max(0.0, min(fat_g, 500.0)),
        )

    custom_foods = await diet_service.get_custom_foods(db, user.id)
    return templates.TemplateResponse(
        request, "partials/custom_food_list.html", {"custom_foods": custom_foods}
    )


@router.post("/foods/custom/{food_id}/update", response_class=HTMLResponse)
async def update_custom_food(
    request: Request,
    food_id: str,
    name: str = Form(...),
    category: str = Form("other"),
    base_grams: float = Form(100.0),
    protein_g: float = Form(0.0),
    carbs_g: float = Form(0.0),
    fat_g: float = Form(0.0),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if name.strip():
        await diet_service.update_custom_food(
            db,
            food_id,
            user.id,
            name,
            category,
            base_grams,
            max(0.0, min(protein_g, 500.0)),
            max(0.0, min(carbs_g, 500.0)),
            max(0.0, min(fat_g, 500.0)),
        )

    custom_foods = await diet_service.get_custom_foods(db, user.id)
    return templates.TemplateResponse(
        request, "partials/custom_food_list.html", {"custom_foods": custom_foods}
    )


@router.post("/foods/custom/{food_id}/delete", response_class=HTMLResponse)
async def delete_custom_food(
    request: Request,
    food_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await diet_service.delete_custom_food(db, food_id, user.id)
    custom_foods = await diet_service.get_custom_foods(db, user.id)
    return templates.TemplateResponse(
        request, "partials/custom_food_list.html", {"custom_foods": custom_foods}
    )


@router.post("/saved-meals/create")
async def create_saved_meal_template(
    name: str = Form(...),
    meal_type: MealType = Form(...),
    items_json: str = Form("[]"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    try:
        items = json.loads(items_json)
    except json.JSONDecodeError:
        items = []

    if not isinstance(items, list):
        items = []

    await diet_service.create_saved_meal_template(db, user.id, name, meal_type, items)
    return JSONResponse({"ok": True})


@router.get("/saved-meals/{template_id}/json")
async def get_saved_meal_template_json(
    template_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    template = await diet_service.get_saved_meal_template(db, template_id, user.id)
    if not template:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse(jsonable_encoder(template))


@router.post("/saved-meals/{template_id}/add-today")
async def add_saved_meal_to_today(
    template_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    meal = await diet_service.apply_saved_meal_to_today(db, template_id, user.id)
    if not meal:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse({"ok": True})


@router.post("/manage/saved-meals/{template_id}/update")
async def update_saved_meal_template(
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    name = str(form.get("name") or "").strip()
    meal_type_raw = str(form.get("meal_type") or "breakfast").strip().lower()
    try:
        meal_type = MealType(meal_type_raw)
    except ValueError:
        meal_type = MealType.breakfast

    grams_by_item_id: dict[str, float] = {}
    for key, value in form.items():
        if key.startswith("grams_"):
            item_id = key.replace("grams_", "", 1)
            try:
                grams_by_item_id[item_id] = float(value)
            except (TypeError, ValueError):
                continue

    await diet_service.update_saved_meal_template(
        db,
        template_id,
        user.id,
        name,
        meal_type,
        grams_by_item_id,
    )
    return RedirectResponse(url="/diet/manage", status_code=303)


@router.post("/manage/saved-meals/{template_id}/items/{item_id}/delete")
async def delete_saved_meal_item(
    template_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await diet_service.remove_saved_meal_item(db, template_id, item_id, user.id)
    return RedirectResponse(url="/diet/manage", status_code=303)


@router.post("/manage/saved-meals/{template_id}/delete")
async def delete_saved_meal_template_manage(
    template_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await diet_service.delete_saved_meal_template(db, template_id, user.id)
    return RedirectResponse(url="/diet/manage", status_code=303)


@router.post("/manage/saved-meals/{template_id}/add-today")
async def add_saved_meal_to_today_manage(
    template_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await diet_service.apply_saved_meal_to_today(db, template_id, user.id)
    return RedirectResponse(url="/diet", status_code=303)


@router.post("/calorie-goal")
async def update_calorie_goal(
    calorie_target: int = Form(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    import uuid

    value = max(500, min(calorie_target, 10000))
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    if goals:
        goals.calorie_target = value
    else:
        goals = DailyGoals(id=str(uuid.uuid4()), user_id=user.id, calorie_target=value)
        db.add(goals)
    await db.commit()
    return RedirectResponse(url="/diet", status_code=303)


@router.post("/macro-goal")
async def update_macro_goal(
    protein_target: int = Form(...),
    carbs_target: int = Form(...),
    fat_target: int = Form(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    import uuid

    protein_val = max(0, min(protein_target, 600))
    carbs_val = max(0, min(carbs_target, 1000))
    fat_val = max(0, min(fat_target, 300))

    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    if goals:
        goals.protein_target = protein_val
        goals.carbs_target = carbs_val
        goals.fat_target = fat_val
        goals.calorie_target = protein_val * 4 + carbs_val * 4 + fat_val * 9
    else:
        goals = DailyGoals(
            id=str(uuid.uuid4()),
            user_id=user.id,
            protein_target=protein_val,
            carbs_target=carbs_val,
            fat_target=fat_val,
            calorie_target=protein_val * 4 + carbs_val * 4 + fat_val * 9,
        )
        db.add(goals)
    await db.commit()
    return RedirectResponse(url="/diet", status_code=303)


@router.post("/add", response_class=HTMLResponse)
async def add_meal(
    request: Request,
    name: str = Form(...),
    meal_type: MealType = Form(...),
    calories: int = Form(...),
    protein_g: float = Form(0.0),
    carbs_g: float = Form(0.0),
    fat_g: float = Form(0.0),
    items_json: str = Form("[]"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    clean_name = name.strip()
    if not clean_name:
        return HTMLResponse(content="", status_code=204)

    try:
        items = json.loads(items_json)
    except json.JSONDecodeError:
        items = []

    # If builder items are provided, trust computed totals coming from builder fields.
    if items and isinstance(items, list):
        calories = max(0, min(int(calories), 5000))
        protein_g = max(0.0, min(float(protein_g), 500.0))
        carbs_g = max(0.0, min(float(carbs_g), 500.0))
        fat_g = max(0.0, min(float(fat_g), 500.0))

    data = MealEntryCreate(
        name=clean_name,
        meal_type=meal_type,
        calories=calories,
        protein_g=protein_g or None,
        carbs_g=carbs_g or None,
        fat_g=fat_g or None,
    )
    meal = await diet_service.create_meal(db, data, date.today(), user.id)
    return templates.TemplateResponse(request, "partials/meal_row.html", {"meal": meal})


@router.post("/{meal_id}/delete", response_class=HTMLResponse)
async def delete_meal(
    request: Request,
    meal_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await diet_service.delete_meal(db, meal_id, user.id)
    return HTMLResponse(content="ok", status_code=200)


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
