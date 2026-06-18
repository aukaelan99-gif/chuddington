from pydantic import BaseModel, Field, field_validator
from models import MealType, Intensity, ExerciseType, MuscleGroup


class StudySessionCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=50)
    duration_minutes: int = Field(ge=1, le=720)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("subject")
    @classmethod
    def strip_subject(cls, v: str) -> str:
        return v.strip()


class ExerciseEntryCreate(BaseModel):
    activity: str = Field(min_length=1, max_length=100)
    duration_minutes: int = Field(ge=1, le=600)
    intensity: Intensity


class MealEntryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    meal_type: MealType
    calories: int = Field(ge=0, le=5000)
    protein_g: float | None = Field(default=None, ge=0, le=500)
    carbs_g: float | None = Field(default=None, ge=0, le=500)
    fat_g: float | None = Field(default=None, ge=0, le=500)


class WaterUpdate(BaseModel):
    glasses: int = Field(ge=0, le=20)


class DailyGoalsUpdate(BaseModel):
    study_minutes: int = Field(ge=15, le=720, default=120)
    calorie_target: int = Field(ge=500, le=5000, default=2000)
    exercise_minutes: int = Field(ge=5, le=300, default=30)
    water_glasses: int = Field(ge=1, le=20, default=8)


class AddExerciseForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    exercise_type: ExerciseType
    muscle_group: MuscleGroup = Field(default=MuscleGroup.other)


class AddSetForm(BaseModel):
    reps: int | None = Field(default=None, ge=1, le=999)
    weight_kg: float | None = Field(default=None, ge=0, le=1000)
    duration_minutes: float | None = Field(default=None, ge=0, le=600)
    distance_km: float | None = Field(default=None, ge=0, le=200)
