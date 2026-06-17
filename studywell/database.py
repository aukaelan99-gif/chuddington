from pathlib import Path
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from models import Base, ExerciseCatalog, ExerciseType, MuscleGroup

DATABASE_URL = f"sqlite+aiosqlite:///{Path(__file__).parent / 'studywell.db'}"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        cols = await conn.execute(text("PRAGMA table_info(workout_exercises)"))
        names = {row[1] for row in cols.fetchall()}
        if "muscle_group" not in names:
            await conn.execute(
                text("ALTER TABLE workout_exercises ADD COLUMN muscle_group VARCHAR(20) DEFAULT 'other'")
            )

        workout_cols = await conn.execute(text("PRAGMA table_info(workouts)"))
        workout_names = {row[1] for row in workout_cols.fetchall()}
        if "duration_minutes" not in workout_names:
            await conn.execute(text("ALTER TABLE workouts ADD COLUMN duration_minutes REAL"))

    await seed_exercise_catalog()


async def seed_exercise_catalog() -> None:
    seed_data = [
        ("Bench Press", ExerciseType.weighted, MuscleGroup.chest),
        ("Incline Dumbbell Press", ExerciseType.weighted, MuscleGroup.chest),
        ("Push-Up", ExerciseType.bodyweight, MuscleGroup.chest),
        ("Barbell Row", ExerciseType.weighted, MuscleGroup.back),
        ("Pull-Up", ExerciseType.bodyweight, MuscleGroup.back),
        ("Lat Pulldown", ExerciseType.weighted, MuscleGroup.back),
        ("Overhead Press", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Lateral Raise", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Rear Delt Fly", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Dumbbell Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Hammer Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Tricep Pushdown", ExerciseType.weighted, MuscleGroup.triceps),
        ("Dip", ExerciseType.bodyweight, MuscleGroup.triceps),
        ("Squat", ExerciseType.weighted, MuscleGroup.quads),
        ("Leg Press", ExerciseType.weighted, MuscleGroup.quads),
        ("Lunge", ExerciseType.bodyweight, MuscleGroup.quads),
        ("Romanian Deadlift", ExerciseType.weighted, MuscleGroup.hamstrings),
        ("Leg Curl", ExerciseType.weighted, MuscleGroup.hamstrings),
        ("Hip Thrust", ExerciseType.weighted, MuscleGroup.glutes),
        ("Glute Bridge", ExerciseType.bodyweight, MuscleGroup.glutes),
        ("Plank", ExerciseType.bodyweight, MuscleGroup.core),
        ("Sit-Up", ExerciseType.bodyweight, MuscleGroup.core),
        ("Hanging Leg Raise", ExerciseType.bodyweight, MuscleGroup.core),
        ("Calf Raise", ExerciseType.weighted, MuscleGroup.calves),
        ("Farmer Carry", ExerciseType.weighted, MuscleGroup.forearms),
        ("Burpee", ExerciseType.bodyweight, MuscleGroup.full_body),
        ("Deadlift", ExerciseType.weighted, MuscleGroup.full_body),
        ("Running", ExerciseType.cardio, MuscleGroup.cardio),
        ("Cycling", ExerciseType.cardio, MuscleGroup.cardio),
        ("Rowing Machine", ExerciseType.cardio, MuscleGroup.cardio),
        ("Jump Rope", ExerciseType.cardio, MuscleGroup.cardio),
        ("Swimming", ExerciseType.cardio, MuscleGroup.cardio),
        ("Elliptical", ExerciseType.cardio, MuscleGroup.cardio),
        ("Stair Climber", ExerciseType.cardio, MuscleGroup.cardio),
    ]

    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count(ExerciseCatalog.id)))
        if (count or 0) > 0:
            return
        for name, ex_type, muscle in seed_data:
            session.add(
                ExerciseCatalog(name=name, exercise_type=ex_type, muscle_group=muscle)
            )
        await session.commit()


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
