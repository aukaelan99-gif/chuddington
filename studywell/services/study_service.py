from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import StudySession
from schemas import StudySessionCreate
import uuid


async def create_session(db: AsyncSession, data: StudySessionCreate, today: date) -> StudySession:
    s = StudySession(
        id=str(uuid.uuid4()),
        subject=data.subject,
        duration_minutes=data.duration_minutes,
        notes=data.notes,
        date=today,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def get_sessions_by_date(db: AsyncSession, d: date) -> list[StudySession]:
    r = await db.execute(select(StudySession).where(StudySession.date == d))
    return r.scalars().all()


async def get_daily_minutes_last_7(db: AsyncSession) -> list[int]:
    today = date.today()
    out = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        r = await db.execute(
            select(func.sum(StudySession.duration_minutes)).where(StudySession.date == day)
        )
        out.append(r.scalar() or 0)
    return out


async def get_weekly_hours_by_subject(db: AsyncSession) -> dict[str, float]:
    since = date.today() - timedelta(days=6)
    r = await db.execute(
        select(StudySession.subject, func.sum(StudySession.duration_minutes))
        .where(StudySession.date >= since)
        .group_by(StudySession.subject)
    )
    return {row[0]: round(row[1] / 60, 2) for row in r.all()}
