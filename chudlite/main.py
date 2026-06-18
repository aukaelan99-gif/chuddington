from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from database import init_db
from auth_deps import LoginRequired
from routers import dashboard, study, exercise, diet, insights, settings, workout
from routers import auth as auth_router

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Chudlite™", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="chudlite-secret-change-in-prod-2026", https_only=False)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.exception_handler(LoginRequired)
async def login_redirect_handler(request: Request, exc: LoginRequired):
    return RedirectResponse(url="/login", status_code=302)


app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(study.router, prefix="/study")
app.include_router(exercise.router, prefix="/exercise")
app.include_router(diet.router, prefix="/diet")
app.include_router(insights.router, prefix="/insights")
app.include_router(settings.router, prefix="/settings")
app.include_router(workout.router, prefix="/workout")
