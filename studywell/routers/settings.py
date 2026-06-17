from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import DailyGoals, StudySession, ExerciseEntry, MealEntry, WaterLog, FoodItem, SavedMeal, Workout
from schemas import DailyGoalsUpdate
from templates_config import templates
from auth_deps import get_current_user, User
from services import auth_service
from services import chulk_avatar_service

router = APIRouter()


def _coalesce(value, default):
    return default if value is None else value

THEME_OPTIONS = [
    ("classic", "Classic Indigo (Current Default)"),
    ("retro", "Retro White Green"),
    ("twilight", "Twilight"),
    ("purple", "Purple"),
    ("violet", "Violet"),
    ("dark", "Dark Theme"),
    ("winter", "Winter White Blue"),
    ("spring", "Spring White Green"),
]
ALLOWED_THEMES = {key for key, _label in THEME_OPTIONS}
DEFAULT_THEME = "classic"

@router.get("/", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    message = request.query_params.get("message")
    error = request.query_params.get("error")
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()
    needs_commit = False

    if not goals:
        goals = DailyGoals(
            study_minutes=120,
            exercise_minutes=30,
            water_glasses=8,
            protein_target=150,
            carbs_target=250,
            fat_target=70,
            calorie_target=2000,
        )
    else:
        goals.study_minutes = _coalesce(goals.study_minutes, 120)
        goals.exercise_minutes = _coalesce(goals.exercise_minutes, 30)
        goals.water_glasses = _coalesce(goals.water_glasses, 8)
        goals.protein_target = _coalesce(goals.protein_target, 150)
        goals.carbs_target = _coalesce(goals.carbs_target, 250)
        goals.fat_target = _coalesce(goals.fat_target, 70)
        needs_commit = True

    if goals.calorie_target is None:
        goals.calorie_target = int((goals.protein_target * 4) + (goals.carbs_target * 4) + (goals.fat_target * 9))
        needs_commit = True

    if needs_commit and goals.user_id:
        await db.commit()

    avatar_files = chulk_avatar_service.list_chulk_avatar_files()
    selected_avatar = chulk_avatar_service.sanitize_chulk_avatar_choice(user.chulk_avatar_file, avatar_files)
    selected_theme = request.cookies.get("site_theme", DEFAULT_THEME)
    if selected_theme not in ALLOWED_THEMES:
        selected_theme = DEFAULT_THEME

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "goals": goals,
            "username": user.username,
            "message": message,
            "error": error,
            "chulk_avatar_files": avatar_files,
            "selected_chulk_avatar": selected_avatar,
            "selected_chulk_avatar_url": chulk_avatar_service.build_chulk_avatar_url(selected_avatar),
            "theme_options": THEME_OPTIONS,
            "selected_theme": selected_theme,
        },
    )


@router.post("/")
async def update_settings(
    study_minutes: int = Form(120),
    exercise_minutes: int = Form(30),
    water_glasses: int = Form(8),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(DailyGoals).where(DailyGoals.user_id == user.id))
    goals = r.scalar_one_or_none()

    protein_target = _coalesce(goals.protein_target, 150) if goals else 150
    carbs_target = _coalesce(goals.carbs_target, 250) if goals else 250
    fat_target = _coalesce(goals.fat_target, 70) if goals else 70
    auto_calorie_target = int((protein_target * 4) + (carbs_target * 4) + (fat_target * 9))

    data = DailyGoalsUpdate(
        study_minutes=study_minutes,
        calorie_target=auto_calorie_target,
        exercise_minutes=exercise_minutes,
        water_glasses=water_glasses,
    )

    if goals:
        goals.study_minutes = data.study_minutes
        goals.calorie_target = data.calorie_target
        goals.exercise_minutes = data.exercise_minutes
        goals.water_glasses = data.water_glasses
    else:
        import uuid
        goals = DailyGoals(
            id=str(uuid.uuid4()),
            user_id=user.id,
            study_minutes=data.study_minutes,
            calorie_target=data.calorie_target,
            exercise_minutes=data.exercise_minutes,
            water_glasses=data.water_glasses,
        )
        db.add(goals)
    await db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/password")
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    current_password = current_password.strip()
    new_password = new_password.strip()
    new_password_confirm = new_password_confirm.strip()

    if not auth_service.verify_password(current_password, user.password_hash):
        return RedirectResponse(url="/settings?error=wrong_current_password", status_code=303)
    if len(new_password) < 6:
        return RedirectResponse(url="/settings?error=password_too_short", status_code=303)
    if new_password != new_password_confirm:
        return RedirectResponse(url="/settings?error=password_mismatch", status_code=303)
    if auth_service.verify_password(new_password, user.password_hash):
        return RedirectResponse(url="/settings?error=password_unchanged", status_code=303)

    user.password_hash = auth_service.hash_password(new_password)
    await db.commit()
    return RedirectResponse(url="/settings?message=password_updated", status_code=303)


@router.post("/chulk-avatar")
async def update_chulk_avatar(
    avatar_file: str = Form(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    avatar_files = chulk_avatar_service.list_chulk_avatar_files()
    selected_avatar = chulk_avatar_service.sanitize_chulk_avatar_choice(avatar_file.strip(), avatar_files)
    user.chulk_avatar_file = selected_avatar
    await db.commit()
    return RedirectResponse(url="/settings?message=avatar_updated", status_code=303)


@router.post("/theme")
async def update_theme(
    theme: str = Form(DEFAULT_THEME),
):
    selected_theme = (theme or "").strip().lower()
    if selected_theme not in ALLOWED_THEMES:
        return RedirectResponse(url="/settings?error=invalid_theme", status_code=303)

    response = RedirectResponse(url="/settings?message=theme_updated", status_code=303)
    response.set_cookie(
        key="site_theme",
        value=selected_theme,
        max_age=60 * 60 * 24 * 365,
        samesite="lax",
        httponly=False,
    )
    return response


@router.post("/delete-account")
async def delete_account(
    request: Request,
    password: str = Form(...),
    confirm_username: str = Form(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if confirm_username.strip() != user.username:
        return RedirectResponse(url="/settings?error=username_confirm_mismatch", status_code=303)
    if not auth_service.verify_password(password, user.password_hash):
        return RedirectResponse(url="/settings?error=wrong_password", status_code=303)

    # Remove user-owned rows before deleting user record.
    await db.execute(delete(StudySession).where(StudySession.user_id == user.id))
    await db.execute(delete(ExerciseEntry).where(ExerciseEntry.user_id == user.id))
    await db.execute(delete(MealEntry).where(MealEntry.user_id == user.id))
    await db.execute(delete(WaterLog).where(WaterLog.user_id == user.id))
    await db.execute(delete(DailyGoals).where(DailyGoals.user_id == user.id))
    await db.execute(delete(FoodItem).where(FoodItem.user_id == user.id))
    await db.execute(delete(SavedMeal).where(SavedMeal.user_id == user.id))

    workouts = (await db.execute(select(Workout).where(Workout.user_id == user.id))).scalars().all()
    for workout in workouts:
        await db.delete(workout)

    await db.delete(user)
    await db.commit()

    request.session.clear()
    return RedirectResponse(url="/register", status_code=303)
