from datetime import date, timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models import MealEntry, WaterLog, FoodItem, SavedMeal, SavedMealItem, MealType
from schemas import MealEntryCreate
import uuid


async def create_meal(db: AsyncSession, data: MealEntryCreate, today: date, user_id: str) -> MealEntry:
    m = MealEntry(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=data.name,
        meal_type=data.meal_type,
        calories=data.calories,
        protein_g=data.protein_g,
        carbs_g=data.carbs_g,
        fat_g=data.fat_g,
        vitamin_a_mcg=data.vitamin_a_mcg,
        vitamin_c_mg=data.vitamin_c_mg,
        vitamin_d_mcg=data.vitamin_d_mcg,
        vitamin_b12_mcg=data.vitamin_b12_mcg,
        calcium_mg=data.calcium_mg,
        iron_mg=data.iron_mg,
        potassium_mg=data.potassium_mg,
        date=today,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


async def delete_meal(db: AsyncSession, meal_id: str, user_id: str) -> None:
    meal = await db.get(MealEntry, meal_id)
    if meal and meal.user_id == user_id:
        await db.delete(meal)
        await db.commit()


async def update_meal(
    db: AsyncSession,
    meal_id: str,
    user_id: str,
    name: str,
    meal_type: MealType,
    calories: int,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    vitamin_a_mcg: float | None,
    vitamin_c_mg: float | None,
    vitamin_d_mcg: float | None,
    vitamin_b12_mcg: float | None,
    calcium_mg: float | None,
    iron_mg: float | None,
    potassium_mg: float | None,
    meal_date: date,
) -> bool:
    meal = await db.get(MealEntry, meal_id)
    if not meal or meal.user_id != user_id:
        return False

    meal.name = name.strip()[:100] or meal.name
    meal.meal_type = meal_type
    meal.calories = max(0, min(int(calories), 5000))
    meal.protein_g = max(0.0, min(float(protein_g), 500.0))
    meal.carbs_g = max(0.0, min(float(carbs_g), 500.0))
    meal.fat_g = max(0.0, min(float(fat_g), 500.0))
    if vitamin_a_mcg is not None:
        meal.vitamin_a_mcg = max(0.0, min(float(vitamin_a_mcg), 50000.0))
    if vitamin_c_mg is not None:
        meal.vitamin_c_mg = max(0.0, min(float(vitamin_c_mg), 10000.0))
    if vitamin_d_mcg is not None:
        meal.vitamin_d_mcg = max(0.0, min(float(vitamin_d_mcg), 1000.0))
    if vitamin_b12_mcg is not None:
        meal.vitamin_b12_mcg = max(0.0, min(float(vitamin_b12_mcg), 1000.0))
    if calcium_mg is not None:
        meal.calcium_mg = max(0.0, min(float(calcium_mg), 10000.0))
    if iron_mg is not None:
        meal.iron_mg = max(0.0, min(float(iron_mg), 1000.0))
    if potassium_mg is not None:
        meal.potassium_mg = max(0.0, min(float(potassium_mg), 20000.0))
    meal.date = meal_date

    await db.commit()
    return True


async def get_meals_by_date(db: AsyncSession, d: date, user_id: str) -> list[MealEntry]:
    r = await db.execute(
        select(MealEntry).where(MealEntry.date == d, MealEntry.user_id == user_id)
    )
    return r.scalars().all()


async def get_recent_meals(db: AsyncSession, user_id: str, limit: int = 50) -> list[MealEntry]:
    r = await db.execute(
        select(MealEntry)
        .where(MealEntry.user_id == user_id)
        .order_by(MealEntry.date.desc(), MealEntry.id.desc())
        .limit(limit)
    )
    return r.scalars().all()


async def get_daily_calories_last_7(db: AsyncSession, user_id: str) -> list[int]:
    today = date.today()
    out = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        r = await db.execute(
            select(func.sum(MealEntry.calories)).where(
                MealEntry.date == day, MealEntry.user_id == user_id
            )
        )
        out.append(r.scalar() or 0)
    return out


async def get_water_today(db: AsyncSession, user_id: str) -> int:
    today = date.today()
    r = await db.execute(
        select(WaterLog).where(WaterLog.date == today, WaterLog.user_id == user_id)
    )
    log = r.scalar_one_or_none()
    return log.glasses if log else 0


async def upsert_water(db: AsyncSession, glasses: int, user_id: str) -> WaterLog:
    today = date.today()
    r = await db.execute(
        select(WaterLog).where(WaterLog.date == today, WaterLog.user_id == user_id)
    )
    log = r.scalar_one_or_none()
    if log:
        log.glasses = glasses
    else:
        log = WaterLog(id=str(uuid.uuid4()), user_id=user_id, glasses=glasses, date=today)
        db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_macro_totals(db: AsyncSession, d: date, user_id: str) -> dict:
    r = await db.execute(
        select(MealEntry).where(MealEntry.date == d, MealEntry.user_id == user_id)
    )
    meals = r.scalars().all()
    protein = sum(m.protein_g or 0 for m in meals)
    carbs = sum(m.carbs_g or 0 for m in meals)
    fat = sum(m.fat_g or 0 for m in meals)
    calories = sum(m.calories for m in meals)
    vitamin_a_mcg = sum(m.vitamin_a_mcg or 0 for m in meals)
    vitamin_c_mg = sum(m.vitamin_c_mg or 0 for m in meals)
    vitamin_d_mcg = sum(m.vitamin_d_mcg or 0 for m in meals)
    vitamin_b12_mcg = sum(m.vitamin_b12_mcg or 0 for m in meals)
    calcium_mg = sum(m.calcium_mg or 0 for m in meals)
    iron_mg = sum(m.iron_mg or 0 for m in meals)
    potassium_mg = sum(m.potassium_mg or 0 for m in meals)
    return {
        "protein": round(protein, 1),
        "carbs": round(carbs, 1),
        "fat": round(fat, 1),
        "calories": calories,
        "vitamin_a_mcg": round(vitamin_a_mcg, 1),
        "vitamin_c_mg": round(vitamin_c_mg, 1),
        "vitamin_d_mcg": round(vitamin_d_mcg, 2),
        "vitamin_b12_mcg": round(vitamin_b12_mcg, 2),
        "calcium_mg": round(calcium_mg, 1),
        "iron_mg": round(iron_mg, 2),
        "potassium_mg": round(potassium_mg, 1),
    }


async def search_food_items(db: AsyncSession, q: str, user_id: str, category: str = "all") -> list[dict]:
    q = q.strip().lower()
    stmt = select(FoodItem).where(
        or_(FoodItem.user_id.is_(None), FoodItem.user_id == user_id)
    )
    if q:
        stmt = stmt.where(func.lower(FoodItem.name).contains(q))
    if category and category != "all":
        stmt = stmt.where(FoodItem.category == category)
    stmt = stmt.order_by(FoodItem.name.asc()).limit(25)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "base_grams": r.base_grams,
            "serving_desc": r.serving_desc,
            "calories": r.calories,
            "protein_g": r.protein_g,
            "carbs_g": r.carbs_g,
            "fat_g": r.fat_g,
            "vitamin_a_mcg": r.vitamin_a_mcg,
            "vitamin_c_mg": r.vitamin_c_mg,
            "vitamin_d_mcg": r.vitamin_d_mcg,
            "vitamin_b12_mcg": r.vitamin_b12_mcg,
            "calcium_mg": r.calcium_mg,
            "iron_mg": r.iron_mg,
            "potassium_mg": r.potassium_mg,
            "is_custom": r.user_id is not None,
        }
        for r in rows
    ]


async def create_custom_food(
    db: AsyncSession,
    user_id: str,
    name: str,
    category: str,
    base_grams: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    vitamin_a_mcg: float,
    vitamin_c_mg: float,
    vitamin_d_mcg: float,
    vitamin_b12_mcg: float,
    calcium_mg: float,
    iron_mg: float,
    potassium_mg: float,
) -> FoodItem:
    grams = max(1.0, float(base_grams))
    protein_g = max(0.0, float(protein_g))
    carbs_g = max(0.0, float(carbs_g))
    fat_g = max(0.0, float(fat_g))
    vitamin_a_mcg = max(0.0, float(vitamin_a_mcg))
    vitamin_c_mg = max(0.0, float(vitamin_c_mg))
    vitamin_d_mcg = max(0.0, float(vitamin_d_mcg))
    vitamin_b12_mcg = max(0.0, float(vitamin_b12_mcg))
    calcium_mg = max(0.0, float(calcium_mg))
    iron_mg = max(0.0, float(iron_mg))
    potassium_mg = max(0.0, float(potassium_mg))
    calories = int(round(protein_g * 4 + carbs_g * 4 + fat_g * 9))
    item = FoodItem(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name.strip(),
        category=(category or "other").strip().lower(),
        base_grams=grams,
        serving_desc=f"{int(grams)}g",
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        vitamin_a_mcg=vitamin_a_mcg,
        vitamin_c_mg=vitamin_c_mg,
        vitamin_d_mcg=vitamin_d_mcg,
        vitamin_b12_mcg=vitamin_b12_mcg,
        calcium_mg=calcium_mg,
        iron_mg=iron_mg,
        potassium_mg=potassium_mg,
    )
    db.add(item)
    await db.commit()
    return item


async def get_custom_foods(db: AsyncSession, user_id: str) -> list[FoodItem]:
    r = await db.execute(
        select(FoodItem).where(FoodItem.user_id == user_id).order_by(FoodItem.name.asc())
    )
    return r.scalars().all()


async def update_custom_food(
    db: AsyncSession,
    food_id: str,
    user_id: str,
    name: str,
    category: str,
    base_grams: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    vitamin_a_mcg: float,
    vitamin_c_mg: float,
    vitamin_d_mcg: float,
    vitamin_b12_mcg: float,
    calcium_mg: float,
    iron_mg: float,
    potassium_mg: float,
) -> None:
    item = await db.get(FoodItem, food_id)
    if not item or item.user_id != user_id:
        return
    grams = max(1.0, float(base_grams))
    protein_g = max(0.0, float(protein_g))
    carbs_g = max(0.0, float(carbs_g))
    fat_g = max(0.0, float(fat_g))
    vitamin_a_mcg = max(0.0, float(vitamin_a_mcg))
    vitamin_c_mg = max(0.0, float(vitamin_c_mg))
    vitamin_d_mcg = max(0.0, float(vitamin_d_mcg))
    vitamin_b12_mcg = max(0.0, float(vitamin_b12_mcg))
    calcium_mg = max(0.0, float(calcium_mg))
    iron_mg = max(0.0, float(iron_mg))
    potassium_mg = max(0.0, float(potassium_mg))
    calories = int(round(protein_g * 4 + carbs_g * 4 + fat_g * 9))
    item.name = name.strip()
    item.category = (category or "other").strip().lower()
    item.base_grams = grams
    item.serving_desc = f"{int(grams)}g"
    item.calories = calories
    item.protein_g = protein_g
    item.carbs_g = carbs_g
    item.fat_g = fat_g
    item.vitamin_a_mcg = vitamin_a_mcg
    item.vitamin_c_mg = vitamin_c_mg
    item.vitamin_d_mcg = vitamin_d_mcg
    item.vitamin_b12_mcg = vitamin_b12_mcg
    item.calcium_mg = calcium_mg
    item.iron_mg = iron_mg
    item.potassium_mg = potassium_mg
    await db.commit()


async def delete_custom_food(db: AsyncSession, food_id: str, user_id: str) -> None:
    item = await db.get(FoodItem, food_id)
    if item and item.user_id == user_id:
        await db.delete(item)
        await db.commit()


def _compute_scaled_nutrition(base_grams: float, grams: float, calories: int, protein: float, carbs: float, fat: float, vitamin_a_mcg: float, vitamin_c_mg: float, vitamin_d_mcg: float, vitamin_b12_mcg: float, calcium_mg: float, iron_mg: float, potassium_mg: float) -> dict:
    safe_base = max(1.0, float(base_grams))
    factor = max(0.0, float(grams)) / safe_base
    return {
        "calories": int(round(float(calories) * factor)),
        "protein_g": round(float(protein) * factor, 1),
        "carbs_g": round(float(carbs) * factor, 1),
        "fat_g": round(float(fat) * factor, 1),
        "vitamin_a_mcg": round(float(vitamin_a_mcg) * factor, 1),
        "vitamin_c_mg": round(float(vitamin_c_mg) * factor, 1),
        "vitamin_d_mcg": round(float(vitamin_d_mcg) * factor, 2),
        "vitamin_b12_mcg": round(float(vitamin_b12_mcg) * factor, 2),
        "calcium_mg": round(float(calcium_mg) * factor, 1),
        "iron_mg": round(float(iron_mg) * factor, 2),
        "potassium_mg": round(float(potassium_mg) * factor, 1),
    }


def _item_from_snapshot(item: SavedMealItem) -> dict:
    scaled = _compute_scaled_nutrition(
        item.base_grams_snapshot,
        item.grams,
        item.calories_snapshot,
        item.protein_snapshot,
        item.carbs_snapshot,
        item.fat_snapshot,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    )
    return {
        "saved_item_id": item.id,
        "food_item_id": item.food_item_id,
        "name": item.name_snapshot,
        "category": item.category_snapshot,
        "base_grams": item.base_grams_snapshot,
        "base_calories": item.calories_snapshot,
        "base_protein_g": item.protein_snapshot,
        "base_carbs_g": item.carbs_snapshot,
        "base_fat_g": item.fat_snapshot,
        "grams": item.grams,
        "calories": scaled["calories"],
        "protein_g": scaled["protein_g"],
        "carbs_g": scaled["carbs_g"],
        "fat_g": scaled["fat_g"],
        "vitamin_a_mcg": scaled["vitamin_a_mcg"],
        "vitamin_c_mg": scaled["vitamin_c_mg"],
        "vitamin_d_mcg": scaled["vitamin_d_mcg"],
        "vitamin_b12_mcg": scaled["vitamin_b12_mcg"],
        "calcium_mg": scaled["calcium_mg"],
        "iron_mg": scaled["iron_mg"],
        "potassium_mg": scaled["potassium_mg"],
        "is_stale": True,
    }


def _item_from_food(item: SavedMealItem, food: FoodItem) -> dict:
    scaled = _compute_scaled_nutrition(
        food.base_grams,
        item.grams,
        food.calories,
        food.protein_g,
        food.carbs_g,
        food.fat_g,
        food.vitamin_a_mcg,
        food.vitamin_c_mg,
        food.vitamin_d_mcg,
        food.vitamin_b12_mcg,
        food.calcium_mg,
        food.iron_mg,
        food.potassium_mg,
    )
    return {
        "saved_item_id": item.id,
        "food_item_id": food.id,
        "name": food.name,
        "category": food.category,
        "base_grams": food.base_grams,
        "base_calories": food.calories,
        "base_protein_g": food.protein_g,
        "base_carbs_g": food.carbs_g,
        "base_fat_g": food.fat_g,
        "base_vitamin_a_mcg": food.vitamin_a_mcg,
        "base_vitamin_c_mg": food.vitamin_c_mg,
        "base_vitamin_d_mcg": food.vitamin_d_mcg,
        "base_vitamin_b12_mcg": food.vitamin_b12_mcg,
        "base_calcium_mg": food.calcium_mg,
        "base_iron_mg": food.iron_mg,
        "base_potassium_mg": food.potassium_mg,
        "grams": item.grams,
        "calories": scaled["calories"],
        "protein_g": scaled["protein_g"],
        "carbs_g": scaled["carbs_g"],
        "fat_g": scaled["fat_g"],
        "vitamin_a_mcg": scaled["vitamin_a_mcg"],
        "vitamin_c_mg": scaled["vitamin_c_mg"],
        "vitamin_d_mcg": scaled["vitamin_d_mcg"],
        "vitamin_b12_mcg": scaled["vitamin_b12_mcg"],
        "calcium_mg": scaled["calcium_mg"],
        "iron_mg": scaled["iron_mg"],
        "potassium_mg": scaled["potassium_mg"],
        "is_stale": False,
    }


async def _resolve_saved_meal(db: AsyncSession, meal: SavedMeal) -> dict:
    items_stmt = select(SavedMealItem).where(SavedMealItem.saved_meal_id == meal.id).order_by(SavedMealItem.order.asc())
    raw_items = (await db.execute(items_stmt)).scalars().all()
    food_ids = [i.food_item_id for i in raw_items if i.food_item_id]
    foods_by_id: dict[str, FoodItem] = {}
    if food_ids:
        foods = (await db.execute(select(FoodItem).where(FoodItem.id.in_(food_ids)))).scalars().all()
        foods_by_id = {f.id: f for f in foods}

    items: list[dict] = []
    for i in raw_items:
        linked_food = foods_by_id.get(i.food_item_id or "") if i.food_item_id else None
        if linked_food:
            items.append(_item_from_food(i, linked_food))
        else:
            items.append(_item_from_snapshot(i))

    totals = {
        "calories": sum(x["calories"] for x in items),
        "protein_g": round(sum(x["protein_g"] for x in items), 1),
        "carbs_g": round(sum(x["carbs_g"] for x in items), 1),
        "fat_g": round(sum(x["fat_g"] for x in items), 1),
        "vitamin_a_mcg": round(sum(x["vitamin_a_mcg"] for x in items), 1),
        "vitamin_c_mg": round(sum(x["vitamin_c_mg"] for x in items), 1),
        "vitamin_d_mcg": round(sum(x["vitamin_d_mcg"] for x in items), 2),
        "vitamin_b12_mcg": round(sum(x["vitamin_b12_mcg"] for x in items), 2),
        "calcium_mg": round(sum(x["calcium_mg"] for x in items), 1),
        "iron_mg": round(sum(x["iron_mg"] for x in items), 2),
        "potassium_mg": round(sum(x["potassium_mg"] for x in items), 1),
    }
    return {
        "id": meal.id,
        "name": meal.name,
        "meal_type": meal.meal_type,
        "created_at": meal.created_at,
        "items": items,
        "item_count": len(items),
        "totals": totals,
    }


async def create_saved_meal_template(
    db: AsyncSession,
    user_id: str,
    name: str,
    meal_type: MealType,
    items: list[dict],
) -> SavedMeal | None:
    if not items:
        return None

    clean_name = (name or "").strip()
    if not clean_name:
        return None

    saved = SavedMeal(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=clean_name,
        meal_type=meal_type,
    )
    db.add(saved)

    for idx, raw in enumerate(items):
        food_id = (raw.get("food_id") or "").strip() or None
        grams = max(1.0, float(raw.get("grams") or 100.0))
        base_grams = max(1.0, float(raw.get("base_grams") or 100.0))
        calories = int(max(0, round(float(raw.get("calories") or 0))))
        protein = max(0.0, float(raw.get("protein_g") or 0.0))
        carbs = max(0.0, float(raw.get("carbs_g") or 0.0))
        fat = max(0.0, float(raw.get("fat_g") or 0.0))

        if food_id and food_id.startswith("custom-temp-"):
            food_id = None

        db.add(
            SavedMealItem(
                id=str(uuid.uuid4()),
                saved_meal_id=saved.id,
                food_item_id=food_id,
                grams=grams,
                order=idx,
                name_snapshot=(raw.get("name") or "Food").strip()[:150],
                category_snapshot=(raw.get("category") or "other").strip().lower()[:50],
                base_grams_snapshot=base_grams,
                calories_snapshot=calories,
                protein_snapshot=protein,
                carbs_snapshot=carbs,
                fat_snapshot=fat,
            )
        )

    await db.commit()
    await db.refresh(saved)
    return saved


async def get_saved_meal_templates(db: AsyncSession, user_id: str) -> list[dict]:
    meals_stmt = (
        select(SavedMeal)
        .where(SavedMeal.user_id == user_id)
        .order_by(SavedMeal.created_at.desc(), SavedMeal.id.desc())
    )
    meals = (await db.execute(meals_stmt)).scalars().all()
    return [await _resolve_saved_meal(db, m) for m in meals]


async def get_saved_meal_template(db: AsyncSession, template_id: str, user_id: str) -> dict | None:
    saved = await db.get(SavedMeal, template_id)
    if not saved or saved.user_id != user_id:
        return None
    return await _resolve_saved_meal(db, saved)


async def apply_saved_meal_to_today(
    db: AsyncSession,
    template_id: str,
    user_id: str,
    override_meal_type: MealType | None = None,
) -> MealEntry | None:
    saved = await db.get(SavedMeal, template_id)
    if not saved or saved.user_id != user_id:
        return None

    resolved = await _resolve_saved_meal(db, saved)
    totals = resolved["totals"]
    meal = MealEntry(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=resolved["name"],
        meal_type=override_meal_type or saved.meal_type,
        calories=totals["calories"],
        protein_g=totals["protein_g"],
        carbs_g=totals["carbs_g"],
        fat_g=totals["fat_g"],
        vitamin_a_mcg=totals["vitamin_a_mcg"],
        vitamin_c_mg=totals["vitamin_c_mg"],
        vitamin_d_mcg=totals["vitamin_d_mcg"],
        vitamin_b12_mcg=totals["vitamin_b12_mcg"],
        calcium_mg=totals["calcium_mg"],
        iron_mg=totals["iron_mg"],
        potassium_mg=totals["potassium_mg"],
        date=date.today(),
    )
    db.add(meal)
    await db.commit()
    await db.refresh(meal)
    return meal


async def update_saved_meal_template(
    db: AsyncSession,
    template_id: str,
    user_id: str,
    name: str,
    meal_type: MealType,
    grams_by_item_id: dict[str, float],
) -> None:
    saved = await db.get(SavedMeal, template_id)
    if not saved or saved.user_id != user_id:
        return

    saved.name = (name or saved.name).strip()[:100] or saved.name
    saved.meal_type = meal_type

    items_stmt = select(SavedMealItem).where(SavedMealItem.saved_meal_id == template_id)
    items = (await db.execute(items_stmt)).scalars().all()
    for item in items:
        if item.id in grams_by_item_id:
            item.grams = max(1.0, float(grams_by_item_id[item.id]))

    await db.commit()


async def remove_saved_meal_item(db: AsyncSession, template_id: str, item_id: str, user_id: str) -> None:
    saved = await db.get(SavedMeal, template_id)
    if not saved or saved.user_id != user_id:
        return
    item = await db.get(SavedMealItem, item_id)
    if item and item.saved_meal_id == template_id:
        await db.delete(item)
        await db.commit()


async def delete_saved_meal_template(db: AsyncSession, template_id: str, user_id: str) -> None:
    saved = await db.get(SavedMeal, template_id)
    if saved and saved.user_id == user_id:
        await db.delete(saved)
        await db.commit()
