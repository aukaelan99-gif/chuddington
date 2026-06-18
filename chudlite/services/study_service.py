from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import StudySession
from schemas import StudySessionCreate
import uuid


async def create_session(db: AsyncSession, data: StudySessionCreate, today: date, user_id: str) -> StudySession:
    s = StudySession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        subject=data.subject,
        duration_minutes=data.duration_minutes,
        notes=data.notes,
        date=today,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def get_sessions_by_date(db: AsyncSession, d: date, user_id: str) -> list[StudySession]:
    r = await db.execute(
        select(StudySession).where(StudySession.date == d, StudySession.user_id == user_id)
    )
    return r.scalars().all()


async def get_daily_minutes_last_7(db: AsyncSession, user_id: str) -> list[int]:
    today = date.today()
    out = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        r = await db.execute(
            select(func.sum(StudySession.duration_minutes)).where(
                StudySession.date == day, StudySession.user_id == user_id
            )
        )
        out.append(r.scalar() or 0)
    return out


async def get_weekly_hours_by_subject(db: AsyncSession, user_id: str) -> dict[str, float]:
    since = date.today() - timedelta(days=6)
    r = await db.execute(
        select(StudySession.subject, func.sum(StudySession.duration_minutes))
        .where(StudySession.date >= since, StudySession.user_id == user_id)
        .group_by(StudySession.subject)
    )
    return {row[0]: round(row[1] / 60, 2) for row in r.all()}
