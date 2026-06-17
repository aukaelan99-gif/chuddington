import uuid, enum
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Date, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id:            Mapped[str]      = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username:      Mapped[str]      = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str]      = mapped_column(String(200), nullable=False)
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(50))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ExerciseEntry(Base):
    __tablename__ = "exercise_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    activity: Mapped[str] = mapped_column(String(100))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    intensity: Mapped[Intensity] = mapped_column(SAEnum(Intensity))
    date: Mapped[date] = mapped_column(Date)


class MealEntry(Base):
    __tablename__ = "meal_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
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
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    glasses: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)


class DailyGoals(Base):
    __tablename__ = "daily_goals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True, index=True)
    study_minutes: Mapped[int] = mapped_column(Integer, default=120)
    calorie_target: Mapped[int] = mapped_column(Integer, default=2000)
    exercise_minutes: Mapped[int] = mapped_column(Integer, default=30)
    water_glasses: Mapped[int] = mapped_column(Integer, default=8)


class ExerciseType(str, enum.Enum):
    weighted   = "weighted"
    bodyweight = "bodyweight"
    cardio     = "cardio"


class MuscleGroup(str, enum.Enum):
    chest = "chest"
    back = "back"
    shoulders = "shoulders"
    biceps = "biceps"
    triceps = "triceps"
    quads = "quads"
    hamstrings = "hamstrings"
    glutes = "glutes"
    core = "core"
    full_body = "full_body"
    cardio = "cardio"
    calves = "calves"
    forearms = "forearms"
    other = "other"


class ExerciseCatalog(Base):
    __tablename__ = "exercise_catalog"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True)
    exercise_type: Mapped[ExerciseType] = mapped_column(SAEnum(ExerciseType))
    muscle_group: Mapped[MuscleGroup] = mapped_column(SAEnum(MuscleGroup), default=MuscleGroup.other)


class Workout(Base):
    __tablename__ = "workouts"
    id:       Mapped[str]      = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:  Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name:     Mapped[str | None] = mapped_column(String(100), nullable=True)
    date:     Mapped[date]     = mapped_column(Date)
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    muscle_group:  Mapped[MuscleGroup]  = mapped_column(SAEnum(MuscleGroup), default=MuscleGroup.other)
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
