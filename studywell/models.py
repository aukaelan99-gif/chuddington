import uuid, enum
from datetime import date
from sqlalchemy import String, Integer, Float, Date, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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


class ExerciseType(str, enum.Enum):
    weighted   = "weighted"
    bodyweight = "bodyweight"
    cardio     = "cardio"


class Workout(Base):
    __tablename__ = "workouts"
    id:       Mapped[str]      = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name:     Mapped[str | None] = mapped_column(String(100), nullable=True)
    date:     Mapped[date]     = mapped_column(Date)
    finished: Mapped[bool]     = mapped_column(Boolean, default=False)
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", order_by="WorkoutExercise.order"
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    id:            Mapped[str]          = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workout_id:    Mapped[str]          = mapped_column(ForeignKey("workouts.id"))
    name:          Mapped[str]          = mapped_column(String(100))
    exercise_type: Mapped[ExerciseType] = mapped_column(SAEnum(ExerciseType))
    order:         Mapped[int]          = mapped_column(Integer, default=0)
    workout:       Mapped["Workout"]    = relationship(back_populates="exercises")
    sets:          Mapped[list["WorkoutSet"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan", order_by="WorkoutSet.set_number"
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    id:               Mapped[str]         = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exercise_id:      Mapped[str]         = mapped_column(ForeignKey("workout_exercises.id"))
    set_number:       Mapped[int]         = mapped_column(Integer)
    reps:             Mapped[int | None]  = mapped_column(Integer, nullable=True)
    weight_kg:        Mapped[float | None] = mapped_column(Float,  nullable=True)
    duration_minutes: Mapped[float | None] = mapped_column(Float,  nullable=True)
    exercise:         Mapped["WorkoutExercise"] = relationship(back_populates="sets")
