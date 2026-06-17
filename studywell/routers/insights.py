import json
from datetime import date
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import StudySession, ExerciseEntry, MealEntry
from services import analytics_service
from templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def insights_page(request: Request, db: AsyncSession = Depends(get_session)):
    score = await analytics_service.get_wellbeing_score(db)
    chart_data = await analytics_service.get_chart_datasets(db)
    return templates.TemplateResponse(
        request, "insights.html", {"score": score, "chart_data": chart_data}
    )


@router.get("/export")
async def export_data(db: AsyncSession = Depends(get_session)):
    def serial(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError

    sessions = (await db.execute(select(StudySession))).scalars().all()
    exercise = (await db.execute(select(ExerciseEntry))).scalars().all()
    meals = (await db.execute(select(MealEntry))).scalars().all()

    payload = {
        "study": [s.__dict__ for s in sessions],
        "exercise": [e.__dict__ for e in exercise],
        "diet": [m.__dict__ for m in meals],
    }
    for lst in payload.values():
        for row in lst:
            row.pop("_sa_instance_state", None)

    return JSONResponse(
        content=json.loads(json.dumps(payload, default=serial)),
        headers={"Content-Disposition": "attachment; filename=studywell_export.json"},
    )
