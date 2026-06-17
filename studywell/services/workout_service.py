from datetime import date
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models import (
    Workout,
    WorkoutExercise,
    WorkoutSet,
    ExerciseType,
    ExerciseCatalog,
    MuscleGroup,
)
import uuid

async def search_exercises(db: AsyncSession, q: str) -> list[dict]:
    q = q.strip().lower()
    stmt = select(ExerciseCatalog).order_by(ExerciseCatalog.name.asc())
    if not q:
        stmt = stmt.limit(12)
    else:
        stmt = stmt.where(func.lower(ExerciseCatalog.name).contains(q)).limit(20)
    r = await db.execute(stmt)
    rows = r.scalars().all()
    return [
        {
            "name": row.name,
            "type": row.exercise_type.value,
            "muscle_group": row.muscle_group.value,
        }
        for row in rows
    ]


async def create_workout(db: AsyncSession, name: str | None, today: date) -> Workout:
    w = Workout(id=str(uuid.uuid4()), name=name or None, date=today, finished=False)
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


async def get_workout(db: AsyncSession, workout_id: str) -> Workout | None:
    r = await db.execute(
        select(Workout)
        .where(Workout.id == workout_id)
        .options(
            selectinload(Workout.exercises).selectinload(WorkoutExercise.sets)
        )
    )
    return r.scalar_one_or_none()


async def add_exercise(
    db: AsyncSession,
    workout_id: str,
    name: str,
    exercise_type: ExerciseType,
    muscle_group: MuscleGroup,
    order: int,
) -> WorkoutExercise:
    ex = WorkoutExercise(
        id=str(uuid.uuid4()),
        workout_id=workout_id,
        name=name,
        exercise_type=exercise_type,
        muscle_group=muscle_group,
        order=order,
    )
    db.add(ex)
    await db.commit()
    await db.refresh(ex)
    # load sets relationship
    r = await db.execute(
        select(WorkoutExercise)
        .where(WorkoutExercise.id == ex.id)
        .options(selectinload(WorkoutExercise.sets))
    )
    return r.scalar_one()


async def add_set(
    db: AsyncSession,
    exercise_id: str,
    set_number: int,
    reps: int | None,
    weight_kg: float | None,
    duration_minutes: float | None,
) -> WorkoutSet:
    s = WorkoutSet(
        id=str(uuid.uuid4()),
        exercise_id=exercise_id,
        set_number=set_number,
        reps=reps,
        weight_kg=weight_kg,
        duration_minutes=duration_minutes,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def get_workout_exercise(db: AsyncSession, ex_id: str) -> WorkoutExercise | None:
    r = await db.execute(
        select(WorkoutExercise)
        .where(WorkoutExercise.id == ex_id)
        .options(selectinload(WorkoutExercise.sets))
    )
    return r.scalar_one_or_none()


async def create_planned_set(db: AsyncSession, ex_id: str) -> WorkoutSet | None:
    ex = await get_workout_exercise(db, ex_id)
    if not ex:
        return None
    s = WorkoutSet(
        id=str(uuid.uuid4()),
        exercise_id=ex_id,
        set_number=len(ex.sets) + 1,
        reps=None,
        weight_kg=None,
        duration_minutes=None,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def update_set(
    db: AsyncSession,
    set_id: str,
    reps: int | None,
    weight_kg: float | None,
    duration_minutes: float | None,
) -> WorkoutSet | None:
    s = await db.get(WorkoutSet, set_id)
    if not s:
        return None
    s.reps = reps
    s.weight_kg = weight_kg
    s.duration_minutes = duration_minutes
    await db.commit()
    await db.refresh(s)
    return s


async def delete_set(db: AsyncSession, ex_id: str, set_id: str) -> WorkoutExercise | None:
    s = await db.get(WorkoutSet, set_id)
    if not s:
        return await get_workout_exercise(db, ex_id)
    await db.delete(s)
    await db.commit()

    ex = await get_workout_exercise(db, ex_id)
    if not ex:
        return None

    # Keep set numbers contiguous after deletion.
    for idx, row in enumerate(ex.sets, start=1):
        row.set_number = idx
    await db.commit()
    return await get_workout_exercise(db, ex_id)


async def finish_workout(db: AsyncSession, workout_id: str) -> None:
    w = await db.get(Workout, workout_id)
    if w:
        w.finished = True
        await db.commit()


async def get_recent_workouts(db: AsyncSession, limit: int = 5) -> list[Workout]:
    r = await db.execute(
        select(Workout)
        .where(Workout.finished == True)
        .order_by(Workout.date.desc())
        .limit(limit)
        .options(selectinload(Workout.exercises))
    )
    return r.scalars().all()


async def get_daily_minutes_last_7(db: AsyncSession) -> list[int]:
    from datetime import timedelta

    today = date.today()
    out: list[int] = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        r = await db.execute(
            select(func.sum(WorkoutSet.duration_minutes))
            .join(WorkoutExercise, WorkoutExercise.id == WorkoutSet.exercise_id)
            .join(Workout, Workout.id == WorkoutExercise.workout_id)
            .where(Workout.date == day, Workout.finished == True)
        )
        out.append(int(r.scalar() or 0))
    return out


async def get_weekly_total_minutes(db: AsyncSession) -> int:
    from datetime import timedelta

    since = date.today() - timedelta(days=6)
    r = await db.execute(
        select(func.sum(WorkoutSet.duration_minutes))
        .join(WorkoutExercise, WorkoutExercise.id == WorkoutSet.exercise_id)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .where(Workout.date >= since, Workout.finished == True)
    )
    return int(r.scalar() or 0)


async def get_streak_days(db: AsyncSession) -> int:
    from datetime import timedelta

    today = date.today()
    r = await db.execute(select(Workout.date).where(Workout.finished == True))
    days = {d for d in r.scalars().all()}
    streak = 0
    for offset in range(0, 365):
        day = today - timedelta(days=offset)
        if day in days:
            streak += 1
        else:
            break
    return streak


async def get_muscle_distribution_last_7(db: AsyncSession) -> dict[str, int]:
    from datetime import timedelta

    since = date.today() - timedelta(days=6)
    r = await db.execute(
        select(WorkoutExercise.muscle_group, func.count(WorkoutSet.id))
        .join(WorkoutSet, WorkoutSet.exercise_id == WorkoutExercise.id)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .where(Workout.date >= since, Workout.finished == True)
        .group_by(WorkoutExercise.muscle_group)
    )
    return {row[0].value if row[0] else "other": int(row[1]) for row in r.all()}
