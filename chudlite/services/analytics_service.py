from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import StudySession, MealEntry, DailyGoals, Workout


async def get_goals(db: AsyncSession, user_id: str) -> DailyGoals | None:
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user_id))
    return r.scalar_one_or_none()


async def get_wellbeing_score(db: AsyncSession, user_id: str) -> float:
    today = date.today()
    goals = await get_goals(db, user_id)
    study_goal = max((goals.study_minutes if goals else 120), 1)
    ex_goal = max((goals.exercise_minutes if goals else 30), 1)
    cal_goal = max((goals.calorie_target if goals else 2000), 1)
    study_m = (
        await db.execute(
            select(func.sum(StudySession.duration_minutes)).where(
                StudySession.date == today, StudySession.user_id == user_id
            )
        )
    ).scalar() or 0
    ex_m = (
        await db.execute(
            select(func.sum(Workout.duration_minutes)).where(
                Workout.date == today,
                Workout.finished == True,
                Workout.user_id == user_id,
            )
        )
    ).scalar() or 0
    cal = (
        await db.execute(
            select(func.sum(MealEntry.calories)).where(
                MealEntry.date == today, MealEntry.user_id == user_id
            )
        )
    ).scalar() or 0
    s = min(study_m / study_goal, 1.0)
    e = min(ex_m / ex_goal, 1.0)
    d = max(0.0, 1.0 - abs(cal - cal_goal) / cal_goal)
    return round((s * 0.40 + e * 0.35 + d * 0.25) * 100, 1)


async def get_chart_datasets(db: AsyncSession, user_id: str) -> dict:
    today = date.today()
    labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]
    study, exercise, calories = [], [], []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        s = (
            await db.execute(
                select(func.sum(StudySession.duration_minutes)).where(
                    StudySession.date == day, StudySession.user_id == user_id
                )
            )
        ).scalar() or 0
        e = (
            await db.execute(
                select(func.sum(Workout.duration_minutes)).where(
                    Workout.date == day,
                    Workout.finished == True,
                    Workout.user_id == user_id,
                )
            )
        ).scalar() or 0
        c = (
            await db.execute(
                select(func.sum(MealEntry.calories)).where(
                    MealEntry.date == day, MealEntry.user_id == user_id
                )
            )
        ).scalar() or 0
        study.append(round(s / 60, 2))
        exercise.append(e)
        calories.append(c)
    return {
        "labels": labels,
        "study_hours": study,
        "exercise_mins": exercise,
        "calories": calories,
    }
