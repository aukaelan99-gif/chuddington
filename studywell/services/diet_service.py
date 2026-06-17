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
    return {
        "protein": round(protein, 1),
        "carbs": round(carbs, 1),
        "fat": round(fat, 1),
        "calories": calories,
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
) -> FoodItem:
    grams = max(1.0, float(base_grams))
    protein_g = max(0.0, float(protein_g))
    carbs_g = max(0.0, float(carbs_g))
    fat_g = max(0.0, float(fat_g))
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
) -> None:
    item = await db.get(FoodItem, food_id)
    if not item or item.user_id != user_id:
        return
    grams = max(1.0, float(base_grams))
    protein_g = max(0.0, float(protein_g))
    carbs_g = max(0.0, float(carbs_g))
    fat_g = max(0.0, float(fat_g))
    calories = int(round(protein_g * 4 + carbs_g * 4 + fat_g * 9))
    item.name = name.strip()
    item.category = (category or "other").strip().lower()
    item.base_grams = grams
    item.serving_desc = f"{int(grams)}g"
    item.calories = calories
    item.protein_g = protein_g
    item.carbs_g = carbs_g
    item.fat_g = fat_g
    await db.commit()


async def delete_custom_food(db: AsyncSession, food_id: str, user_id: str) -> None:
    item = await db.get(FoodItem, food_id)
    if item and item.user_id == user_id:
        await db.delete(item)
        await db.commit()


def _compute_scaled_macros(base_grams: float, grams: float, calories: int, protein: float, carbs: float, fat: float) -> dict:
    safe_base = max(1.0, float(base_grams))
    factor = max(0.0, float(grams)) / safe_base
    return {
        "calories": int(round(float(calories) * factor)),
        "protein_g": round(float(protein) * factor, 1),
        "carbs_g": round(float(carbs) * factor, 1),
        "fat_g": round(float(fat) * factor, 1),
    }


def _item_from_snapshot(item: SavedMealItem) -> dict:
    scaled = _compute_scaled_macros(
        item.base_grams_snapshot,
        item.grams,
        item.calories_snapshot,
        item.protein_snapshot,
        item.carbs_snapshot,
        item.fat_snapshot,
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
        "is_stale": True,
    }


def _item_from_food(item: SavedMealItem, food: FoodItem) -> dict:
    scaled = _compute_scaled_macros(
        food.base_grams,
        item.grams,
        food.calories,
        food.protein_g,
        food.carbs_g,
        food.fat_g,
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
        "grams": item.grams,
        "calories": scaled["calories"],
        "protein_g": scaled["protein_g"],
        "carbs_g": scaled["carbs_g"],
        "fat_g": scaled["fat_g"],
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
