from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models import Workout, WorkoutExercise, WorkoutSet, ExerciseType
import uuid

EXERCISE_LIBRARY = [
    {"name": "Bench Press",      "type": "weighted"},
    {"name": "Squat",            "type": "weighted"},
    {"name": "Deadlift",         "type": "weighted"},
    {"name": "Overhead Press",   "type": "weighted"},
    {"name": "Barbell Row",      "type": "weighted"},
    {"name": "Dumbbell Curl",    "type": "weighted"},
    {"name": "Tricep Pushdown",  "type": "weighted"},
    {"name": "Leg Press",        "type": "weighted"},
    {"name": "Lateral Raise",    "type": "weighted"},
    {"name": "Pull-Up",          "type": "bodyweight"},
    {"name": "Push-Up",          "type": "bodyweight"},
    {"name": "Dip",              "type": "bodyweight"},
    {"name": "Chin-Up",          "type": "bodyweight"},
    {"name": "Plank",            "type": "bodyweight"},
    {"name": "Sit-Up",           "type": "bodyweight"},
    {"name": "Burpee",           "type": "bodyweight"},
    {"name": "Lunge",            "type": "bodyweight"},
    {"name": "Running",          "type": "cardio"},
    {"name": "Cycling",          "type": "cardio"},
    {"name": "Rowing Machine",   "type": "cardio"},
    {"name": "Jump Rope",        "type": "cardio"},
    {"name": "Swimming",         "type": "cardio"},
    {"name": "Elliptical",       "type": "cardio"},
    {"name": "Stair Climber",    "type": "cardio"},
]


def search_exercises(q: str) -> list[dict]:
    q = q.strip().lower()
    if not q:
        return EXERCISE_LIBRARY[:10]
    return [e for e in EXERCISE_LIBRARY if q in e["name"].lower()]


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
    db: AsyncSession, workout_id: str, name: str, exercise_type: ExerciseType, order: int
) -> WorkoutExercise:
    ex = WorkoutExercise(
        id=str(uuid.uuid4()),
        workout_id=workout_id,
        name=name,
        exercise_type=exercise_type,
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
