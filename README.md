# StudyWell — Student Wellness Tracker
Hackathon | SDG 3 | FastAPI + SQLite + Jinja2 + HTMX | Python-majority codebase

---

## Agent Instructions — Workout Feature

This section is written for an AI coding agent implementing the **Guided Workout Session** feature.

### Overview
A "Start Workout" button on `/exercise` launches a new guided workout session at `/workout/{id}`. Users search for exercises, add them to the session, then log sets. Three exercise types are supported:

| Type | Fields per set |
|---|---|
| `weighted` | reps + weight (kg) + optional duration (min) |
| `bodyweight` | reps + optional duration (min) |
| `cardio` | duration (min) only |

### New DB Models (add to `models.py`)
```python
class ExerciseType(str, enum.Enum):
    weighted   = "weighted"
    bodyweight = "bodyweight"
    cardio     = "cardio"

class Workout(Base):
    __tablename__ = "workouts"
    id:        Mapped[str]  = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name:      Mapped[str | None] = mapped_column(String(100), nullable=True)
    date:      Mapped[date] = mapped_column(Date)
    finished:  Mapped[bool] = mapped_column(default=False)
    exercises: Mapped[list["WorkoutExercise"]] = relationship(back_populates="workout", cascade="all, delete-orphan")

class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    id:            Mapped[str]          = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workout_id:    Mapped[str]          = mapped_column(ForeignKey("workouts.id"))
    name:          Mapped[str]          = mapped_column(String(100))
    exercise_type: Mapped[ExerciseType] = mapped_column(SAEnum(ExerciseType))
    order:         Mapped[int]          = mapped_column(Integer, default=0)
    workout:       Mapped["Workout"]    = relationship(back_populates="exercises")
    sets:          Mapped[list["WorkoutSet"]] = relationship(back_populates="exercise", cascade="all, delete-orphan")

class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    id:               Mapped[str]        = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exercise_id:      Mapped[str]        = mapped_column(ForeignKey("workout_exercises.id"))
    set_number:       Mapped[int]        = mapped_column(Integer)
    reps:             Mapped[int | None] = mapped_column(Integer,  nullable=True)
    weight_kg:        Mapped[float|None] = mapped_column(Float,    nullable=True)
    duration_minutes: Mapped[float|None] = mapped_column(Float,    nullable=True)
    exercise:         Mapped["WorkoutExercise"] = relationship(back_populates="sets")
```

### New Files
```
studywell/
├── routers/workout.py          # GET/POST /workout
├── services/workout_service.py
├── templates/workout.html
└── templates/partials/
    ├── workout_exercise_block.html   # one exercise card with set table + add-set form
    └── workout_set_row.html          # single <tr> for a logged set
```

### Routes (`routers/workout.py`)

| Method | Path | Action |
|---|---|---|
| POST | `/workout/new` | Create Workout row, redirect to GET /workout/{id} |
| GET  | `/workout/{id}` | Render workout session page |
| POST | `/workout/{id}/add-exercise` | Add WorkoutExercise, return HTMX partial `workout_exercise_block.html` |
| GET  | `/workout/search` | Return JSON list of exercise name suggestions matching `?q=` |
| POST | `/workout/{id}/exercise/{ex_id}/add-set` | Append WorkoutSet, return HTMX partial `workout_set_row.html` |
| POST | `/workout/{id}/finish` | Set `finished=True`, redirect to `/exercise` |

### Exercise Search (`GET /workout/search?q=`)
- Filter the `EXERCISE_LIBRARY` constant (list of dicts with `name` and `type`) by substring match on `q`.
- Return JSON: `[{"name": "Bench Press", "type": "weighted"}, ...]`
- HTMX on the frontend sends `hx-get="/workout/search"` on keyup with `hx-trigger="keyup changed delay:200ms"` and renders a dropdown of results.

### Exercise Library constant (in `workout_service.py`)
```python
EXERCISE_LIBRARY = [
    {"name": "Bench Press",       "type": "weighted"},
    {"name": "Squat",             "type": "weighted"},
    {"name": "Deadlift",          "type": "weighted"},
    {"name": "Overhead Press",    "type": "weighted"},
    {"name": "Barbell Row",       "type": "weighted"},
    {"name": "Dumbbell Curl",     "type": "weighted"},
    {"name": "Tricep Pushdown",   "type": "weighted"},
    {"name": "Leg Press",         "type": "weighted"},
    {"name": "Lateral Raise",     "type": "weighted"},
    {"name": "Pull-Up",           "type": "bodyweight"},
    {"name": "Push-Up",           "type": "bodyweight"},
    {"name": "Dip",               "type": "bodyweight"},
    {"name": "Chin-Up",           "type": "bodyweight"},
    {"name": "Plank",             "type": "bodyweight"},
    {"name": "Sit-Up",            "type": "bodyweight"},
    {"name": "Burpee",            "type": "bodyweight"},
    {"name": "Lunge",             "type": "bodyweight"},
    {"name": "Running",           "type": "cardio"},
    {"name": "Cycling",           "type": "cardio"},
    {"name": "Rowing Machine",    "type": "cardio"},
    {"name": "Jump Rope",         "type": "cardio"},
    {"name": "Swimming",          "type": "cardio"},
    {"name": "Elliptical",        "type": "cardio"},
    {"name": "Stair Climber",     "type": "cardio"},
]
```

### Schemas (add to `schemas.py`)
```python
class AddExerciseForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    exercise_type: ExerciseType

class AddSetForm(BaseModel):
    reps: int | None = Field(default=None, ge=1, le=999)
    weight_kg: float | None = Field(default=None, ge=0, le=1000)
    duration_minutes: float | None = Field(default=None, ge=0, le=600)
```

### `workout.html` page layout
- Header: workout name (editable inline) + "Finish Workout" button (posts to `/workout/{id}/finish`)
- Exercise search bar: text input with HTMX live search dropdown showing suggestions from `/workout/search?q=`
  - Each suggestion is a clickable row that fills a hidden form and triggers `POST /workout/{id}/add-exercise`
  - Form fields: `name` (text), `exercise_type` (hidden, auto-filled from suggestion)
  - User can also type a custom name and manually pick the type via a select
- For each WorkoutExercise already added: render `workout_exercise_block.html`
- Each block shows: exercise name, type badge, table of sets logged so far, add-set form at bottom

### `workout_exercise_block.html` layout
- Exercise name + type badge (colour-coded: blue=weighted, green=bodyweight, orange=cardio)
- Set table columns depend on type:
  - weighted:   Set # | Reps | Weight (kg) | Duration (optional) | ✓
  - bodyweight: Set # | Reps | Duration (optional) | ✓
  - cardio:     Set # | Duration (min) | ✓
- Add-set form below table, posts to `/workout/{id}/exercise/{ex_id}/add-set`
  - HTMX: `hx-target="#sets-{ex_id}"` `hx-swap="beforeend"` returns `workout_set_row.html`
- "Bodyweight" checkbox for weighted exercises (sets weight_kg = 0, hides weight field)

### Add-set form fields by type
- **weighted**: reps (number), weight_kg (number, disabled if bodyweight checkbox ticked), duration_minutes (optional number)
- **bodyweight**: reps (number), duration_minutes (optional number)  
- **cardio**: duration_minutes (number, required)

### `workout_service.py` functions
```python
async def create_workout(db, name, today) -> Workout
async def get_workout(db, workout_id) -> Workout  # with exercises + sets eagerly loaded
async def add_exercise(db, workout_id, name, exercise_type, order) -> WorkoutExercise
async def add_set(db, exercise_id, reps, weight_kg, duration_minutes, set_number) -> WorkoutSet
async def finish_workout(db, workout_id) -> None
async def get_recent_workouts(db, limit=5) -> list[Workout]
```

### Wire-up checklist
- [ ] Add `ExerciseType`, `Workout`, `WorkoutExercise`, `WorkoutSet` to `models.py`
- [ ] Add `ForeignKey` import to `models.py`
- [ ] Add `relationship` import to `models.py`
- [ ] Add `AddExerciseForm`, `AddSetForm` to `schemas.py`
- [ ] Create `services/workout_service.py`
- [ ] Create `routers/workout.py`
- [ ] Register router in `main.py`: `app.include_router(workout.router, prefix="/workout")`
- [ ] Add `workout` to `routers/__init__.py`
- [ ] Add "Start Workout" button to `exercise.html` (posts to `/workout/new`)
- [ ] Add `/workout` link to nav in `base.html`
- [ ] Create `templates/workout.html`
- [ ] Create `templates/partials/workout_exercise_block.html`
- [ ] Create `templates/partials/workout_set_row.html`

---

## Stack
| Layer | Tool |
|---|---|
| Web framework | FastAPI (async) |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 async |
| Database | SQLite via aiosqlite |
| Templates | Jinja2 |
| Dynamic UI | HTMX (CDN) |
| Charts | Chart.js (CDN, data injected by Jinja2) |
| Styling | Tailwind CSS (CDN Play) |
| Server | Uvicorn |

JS is limited to: Pomodoro timer (~30 lines) + Chart.js init (~10 lines/chart). All logic is Python.

---

## File Structure
```
studywell/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── routers/
│   ├── __init__.py
│   ├── dashboard.py      # GET /
│   ├── study.py          # GET/POST /study
│   ├── exercise.py       # GET/POST /exercise
│   ├── diet.py           # GET/POST /diet
│   └── insights.py       # GET /insights, GET /insights/export
├── services/
│   ├── __init__.py
│   ├── study_service.py
│   ├── exercise_service.py
│   ├── diet_service.py
│   └── analytics_service.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── study.html
│   ├── exercise.html
│   ├── diet.html
│   ├── insights.html
│   └── partials/
│       ├── study_row.html
│       ├── exercise_row.html
│       ├── meal_row.html
│       └── daily_summary.html
├── static/               # empty — CDN only
├── studywell.db          # auto-created
├── requirements.txt
└── README.md
```

---

## requirements.txt
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.20.0
pydantic>=2.7.0
jinja2>=3.1.4
python-multipart>=0.0.9
```

---

## models.py
```python
import uuid, enum
from datetime import date
from sqlalchemy import String, Integer, Float, Date, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass

class MealType(str, enum.Enum):
    breakfast="breakfast"; lunch="lunch"; dinner="dinner"; snack="snack"

class Intensity(str, enum.Enum):
    low="low"; medium="medium"; high="high"

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
```

---

## schemas.py
```python
from pydantic import BaseModel, Field, field_validator
from models import MealType, Intensity

class StudySessionCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=50)
    duration_minutes: int = Field(ge=1, le=720)
    notes: str | None = Field(default=None, max_length=500)
    @field_validator("subject")
    @classmethod
    def strip_subject(cls, v: str) -> str: return v.strip()

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
```

---

## database.py
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from models import Base

DATABASE_URL = "sqlite+aiosqlite:///./studywell.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

---

## main.py
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db
from routers import dashboard, study, exercise, diet, insights

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="StudyWell", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(dashboard.router)
app.include_router(study.router, prefix="/study")
app.include_router(exercise.router, prefix="/exercise")
app.include_router(diet.router, prefix="/diet")
app.include_router(insights.router, prefix="/insights")
```

---

## Services

### services/study_service.py
```python
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import StudySession
from schemas import StudySessionCreate
import uuid

async def create_session(db: AsyncSession, data: StudySessionCreate, today: date) -> StudySession:
    s = StudySession(id=str(uuid.uuid4()), subject=data.subject,
                     duration_minutes=data.duration_minutes, notes=data.notes, date=today)
    db.add(s); await db.commit(); await db.refresh(s)
    return s

async def get_sessions_by_date(db: AsyncSession, d: date) -> list[StudySession]:
    r = await db.execute(select(StudySession).where(StudySession.date == d))
    return r.scalars().all()

async def get_daily_minutes_last_7(db: AsyncSession) -> list[int]:
    today = date.today()
    out = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        r = await db.execute(select(func.sum(StudySession.duration_minutes)).where(StudySession.date == day))
        out.append(r.scalar() or 0)
    return out

async def get_weekly_hours_by_subject(db: AsyncSession) -> dict[str, float]:
    since = date.today() - timedelta(days=6)
    r = await db.execute(
        select(StudySession.subject, func.sum(StudySession.duration_minutes))
        .where(StudySession.date >= since).group_by(StudySession.subject))
    return {row[0]: round(row[1] / 60, 2) for row in r.all()}
```

Implement `exercise_service.py` and `diet_service.py` following the same async pattern (CRUD + 7-day daily totals + weekly aggregation).

### services/analytics_service.py
```python
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import StudySession, ExerciseEntry, MealEntry, DailyGoals

async def get_wellbeing_score(db: AsyncSession) -> float:
    today = date.today()
    goals = await db.get(DailyGoals, 1) or DailyGoals()
    study_m = (await db.execute(select(func.sum(StudySession.duration_minutes)).where(StudySession.date == today))).scalar() or 0
    ex_m    = (await db.execute(select(func.sum(ExerciseEntry.duration_minutes)).where(ExerciseEntry.date == today))).scalar() or 0
    cal     = (await db.execute(select(func.sum(MealEntry.calories)).where(MealEntry.date == today))).scalar() or 0
    s = min(study_m / goals.study_minutes, 1.0)
    e = min(ex_m / goals.exercise_minutes, 1.0)
    d = max(0.0, 1.0 - abs(cal - goals.calorie_target) / goals.calorie_target)
    return round((s * 0.40 + e * 0.35 + d * 0.25) * 100, 1)

async def get_chart_datasets(db: AsyncSession) -> dict:
    today = date.today()
    labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]
    study, exercise, calories = [], [], []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        s = (await db.execute(select(func.sum(StudySession.duration_minutes)).where(StudySession.date == day))).scalar() or 0
        e = (await db.execute(select(func.sum(ExerciseEntry.duration_minutes)).where(ExerciseEntry.date == day))).scalar() or 0
        c = (await db.execute(select(func.sum(MealEntry.calories)).where(MealEntry.date == day))).scalar() or 0
        study.append(round(s / 60, 2)); exercise.append(e); calories.append(c)
    return {"labels": labels, "study_hours": study, "exercise_mins": exercise, "calories": calories}
```

---

## Router Pattern (apply to all routers)

```python
# routers/study.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from database import get_session
from schemas import StudySessionCreate
from services import study_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def study_page(request: Request, db: AsyncSession = Depends(get_session)):
    today = date.today()
    sessions = await study_service.get_sessions_by_date(db, today)
    weekly_data = await study_service.get_daily_minutes_last_7(db)
    return templates.TemplateResponse("study.html", {
        "request": request, "sessions": sessions,
        "today": today, "weekly_minutes": weekly_data,
    })

@router.post("/add", response_class=HTMLResponse)
async def add_session(request: Request, subject: str = Form(...),
                      duration_minutes: int = Form(...), notes: str = Form(None),
                      db: AsyncSession = Depends(get_session)):
    data = StudySessionCreate(subject=subject, duration_minutes=duration_minutes, notes=notes)
    session = await study_service.create_session(db, data, date.today())
    # HTMX: return partial fragment only
    return templates.TemplateResponse("partials/study_row.html", {"request": request, "session": session})
```

---

## Templates

### templates/base.html
- Tailwind CSS CDN Play script tag in `<head>`
- HTMX CDN script tag in `<head>`
- Chart.js CDN script tag in `<head>`
- Nav bar with links: Dashboard `/`, Study `/study`, Exercise `/exercise`, Diet `/diet`, Insights `/insights`
- Mobile: bottom fixed nav. Desktop (md+): left sidebar.
- `{% block content %}{% endblock %}` in main body

### Page: dashboard.html
- Summary cards: study hours today, exercise mins today, calories today, water glasses
- Each card shows value vs. goal and a progress bar (% calculated in Python, passed as context)
- Wellbeing score badge
- Quick-add links to each tracker page

### Page: study.html
- Pomodoro timer (JS): 25 min focus / 5 min break, start/pause/reset buttons, auto-submits log form on focus session complete
- Manual log form (HTMX `hx-post="/study/add"` `hx-target="#session-list"` `hx-swap="afterbegin"`): fields: subject, duration_minutes, notes
- Table `#session-list` listing today's sessions (populated via `partials/study_row.html`)
- Bar chart: last 7 days study hours — `weekly_minutes` list injected by Jinja2 into Chart.js

### Page: exercise.html
- Log form (HTMX): activity (text), duration_minutes, intensity (select: low/medium/high)
- Today's exercise list (HTMX partial)
- Weekly total minutes and streak count (calculated in service, passed as context)
- Line chart: exercise minutes last 7 days

### Page: diet.html
- Log form (HTMX): name, meal_type (select), calories, protein_g, carbs_g, fat_g (optional)
- Meals grouped by type (breakfast/lunch/dinner/snack)
- Daily calorie total vs. target with progress bar
- Macro totals row: protein / carbs / fat
- Water counter: current glasses, +/- HTMX buttons posting to `/diet/water`
- Pie chart: macro distribution (protein/carbs/fat percentages)

### Page: insights.html
- 7-day overview: all three Chart.js charts (bar, line, bar) using `get_chart_datasets()` data
- Wellbeing score for today from `get_wellbeing_score()`
- Export button: `<a href="/insights/export">Download JSON</a>`

### HTMX Partials
- `partials/study_row.html` — single `<tr>` for a StudySession
- `partials/exercise_row.html` — single `<tr>` for an ExerciseEntry
- `partials/meal_row.html` — single `<tr>` for a MealEntry
- `partials/daily_summary.html` — summary cards fragment (re-fetched after any log)

---

## insights.py export route
```python
@router.get("/export")
async def export_data(db: AsyncSession = Depends(get_session)):
    from fastapi.responses import JSONResponse
    from sqlalchemy import select
    from models import StudySession, ExerciseEntry, MealEntry
    import json
    from datetime import date

    def serial(obj):
        if isinstance(obj, date): return obj.isoformat()
        raise TypeError

    sessions = (await db.execute(select(StudySession))).scalars().all()
    exercise = (await db.execute(select(ExerciseEntry))).scalars().all()
    meals    = (await db.execute(select(MealEntry))).scalars().all()

    payload = {
        "study":    [s.__dict__ for s in sessions],
        "exercise": [e.__dict__ for e in exercise],
        "diet":     [m.__dict__ for m in meals],
    }
    # strip SQLAlchemy internal key
    for lst in payload.values():
        for row in lst: row.pop("_sa_instance_state", None)

    return JSONResponse(content=json.loads(json.dumps(payload, default=serial)),
                        headers={"Content-Disposition": "attachment; filename=studywell_export.json"})
```

---

## Build Order
1. `models.py`
2. `schemas.py`
3. `database.py`
4. `main.py`
5. `services/` — all four service files
6. `routers/` — all five router files
7. `templates/base.html`
8. Page templates (dashboard → study → exercise → diet → insights)
9. Partial templates
10. Pomodoro JS block in `study.html`
11. Chart.js blocks in each page (data via Jinja2 `{{ weekly_minutes | tojson }}`)
12. Goal settings: GET/POST `/settings` to read/update `DailyGoals` row (id=1, upsert)

## Run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
