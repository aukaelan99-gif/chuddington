import uuid, enum
from datetime import date
from sqlalchemy import String, Integer, Float, Date, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class Intensity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class StudySession(Base):
    __tablename__ = "study_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject: Mapped[str] = mapped_column(String(50))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ExerciseEntry(Base):
    __tablename__ = "exercise_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    activity: Mapped[str] = mapped_column(String(100))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    intensity: Mapped[Intensity] = mapped_column(SAEnum(Intensity))
    date: Mapped[date] = mapped_column(Date)


class MealEntry(Base):
    __tablename__ = "meal_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    meal_type: Mapped[MealType] = mapped_column(SAEnum(MealType))
    calories: Mapped[int] = mapped_column(Integer)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    date: Mapped[date] = mapped_column(Date)


class WaterLog(Base):
    __tablename__ = "water_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    glasses: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date, unique=True)


class DailyGoals(Base):
    __tablename__ = "daily_goals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    study_minutes: Mapped[int] = mapped_column(Integer, default=120)
    calorie_target: Mapped[int] = mapped_column(Integer, default=2000)
    exercise_minutes: Mapped[int] = mapped_column(Integer, default=30)
    water_glasses: Mapped[int] = mapped_column(Integer, default=8)
