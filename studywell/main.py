from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db
from routers import dashboard, study, exercise, diet, insights, settings, workout

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="StudyWell", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(dashboard.router)
app.include_router(study.router, prefix="/study")
app.include_router(exercise.router, prefix="/exercise")
app.include_router(diet.router, prefix="/diet")
app.include_router(insights.router, prefix="/insights")
app.include_router(settings.router, prefix="/settings")
app.include_router(workout.router, prefix="/workout")
