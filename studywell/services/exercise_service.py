from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import ExerciseEntry
from schemas import ExerciseEntryCreate
import uuid


async def create_entry(db: AsyncSession, data: ExerciseEntryCreate, today: date) -> ExerciseEntry:
    e = ExerciseEntry(
        id=str(uuid.uuid4()),
        activity=data.activity,
        duration_minutes=data.duration_minutes,
        intensity=data.intensity,
        date=today,
    )
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return e


async def get_entries_by_date(db: AsyncSession, d: date) -> list[ExerciseEntry]:
    r = await db.execute(select(ExerciseEntry).where(ExerciseEntry.date == d))
    return r.scalars().all()


async def get_daily_minutes_last_7(db: AsyncSession) -> list[int]:
    today = date.today()
    out = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        r = await db.execute(
            select(func.sum(ExerciseEntry.duration_minutes)).where(ExerciseEntry.date == day)
        )
        out.append(r.scalar() or 0)
    return out


async def get_weekly_total(db: AsyncSession) -> int:
    since = date.today() - timedelta(days=6)
    r = await db.execute(
        select(func.sum(ExerciseEntry.duration_minutes)).where(ExerciseEntry.date >= since)
    )
    return r.scalar() or 0


async def get_streak(db: AsyncSession) -> int:
    today = date.today()
    streak = 0
    for offset in range(0, 30):
        day = today - timedelta(days=offset)
        r = await db.execute(
            select(func.sum(ExerciseEntry.duration_minutes)).where(ExerciseEntry.date == day)
        )
        total = r.scalar() or 0
        if total > 0:
            streak += 1
        else:
            break
    return streak
