from datetime import date
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import StudySession, MealEntry, Workout
from services import analytics_service
from templates_config import templates
from auth_deps import get_current_user, User

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def insights_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    score = await analytics_service.get_wellbeing_score(db, user.id)
    chart_data = await analytics_service.get_chart_datasets(db, user.id)
    return templates.TemplateResponse(
        request, "insights.html", {"score": score, "chart_data": chart_data, "username": user.username}
    )
