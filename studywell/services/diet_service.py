from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import MealEntry, WaterLog
from schemas import MealEntryCreate
import uuid


async def create_meal(db: AsyncSession, data: MealEntryCreate, today: date) -> MealEntry:
    m = MealEntry(
        id=str(uuid.uuid4()),
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


async def get_meals_by_date(db: AsyncSession, d: date) -> list[MealEntry]:
    r = await db.execute(select(MealEntry).where(MealEntry.date == d))
    return r.scalars().all()


async def get_daily_calories_last_7(db: AsyncSession) -> list[int]:
    today = date.today()
    out = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        r = await db.execute(
            select(func.sum(MealEntry.calories)).where(MealEntry.date == day)
        )
        out.append(r.scalar() or 0)
    return out


async def get_water_today(db: AsyncSession) -> int:
    today = date.today()
    r = await db.execute(select(WaterLog).where(WaterLog.date == today))
    log = r.scalar_one_or_none()
    return log.glasses if log else 0


async def upsert_water(db: AsyncSession, glasses: int) -> WaterLog:
    today = date.today()
    r = await db.execute(select(WaterLog).where(WaterLog.date == today))
    log = r.scalar_one_or_none()
    if log:
        log.glasses = glasses
    else:
        log = WaterLog(id=str(uuid.uuid4()), glasses=glasses, date=today)
        db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_macro_totals(db: AsyncSession, d: date) -> dict:
    r = await db.execute(select(MealEntry).where(MealEntry.date == d))
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
