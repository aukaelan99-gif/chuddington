from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import StudySession, ExerciseEntry, MealEntry, DailyGoals


async def get_wellbeing_score(db: AsyncSession) -> float:
    today = date.today()
    goals = await db.get(DailyGoals, 1)
    study_goal = goals.study_minutes if goals else 120
    ex_goal = goals.exercise_minutes if goals else 30
    cal_goal = goals.calorie_target if goals else 2000
    study_m = (
        await db.execute(
            select(func.sum(StudySession.duration_minutes)).where(StudySession.date == today)
        )
    ).scalar() or 0
    ex_m = (
        await db.execute(
            select(func.sum(ExerciseEntry.duration_minutes)).where(ExerciseEntry.date == today)
        )
    ).scalar() or 0
    cal = (
        await db.execute(
            select(func.sum(MealEntry.calories)).where(MealEntry.date == today)
        )
    ).scalar() or 0
    s = min(study_m / study_goal, 1.0)
    e = min(ex_m / ex_goal, 1.0)
    d = max(0.0, 1.0 - abs(cal - cal_goal) / cal_goal)
    return round((s * 0.40 + e * 0.35 + d * 0.25) * 100, 1)


async def get_chart_datasets(db: AsyncSession) -> dict:
    today = date.today()
    labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]
    study, exercise, calories = [], [], []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        s = (
            await db.execute(
                select(func.sum(StudySession.duration_minutes)).where(StudySession.date == day)
            )
        ).scalar() or 0
        e = (
            await db.execute(
                select(func.sum(ExerciseEntry.duration_minutes)).where(ExerciseEntry.date == day)
            )
        ).scalar() or 0
        c = (
            await db.execute(
                select(func.sum(MealEntry.calories)).where(MealEntry.date == day)
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
