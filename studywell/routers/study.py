from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from database import get_session
from models import CalendarEvent, EventType
from schemas import StudySessionCreate
from services import ai_tutor_service
from services import chulk_avatar_service
from services import curriculum_service
from services import study_service
from templates_config import templates
from auth_deps import get_current_user, User

router = APIRouter()


async def _build_study_chart_data(db: AsyncSession, user_id: str) -> dict[str, list[float] | list[str]]:
    today = date.today()
    weekly_minutes = await study_service.get_daily_minutes_last_7(db, user_id)
    weekly_hours = [round(m / 60, 2) for m in weekly_minutes]
    labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]
    return {"labels": labels, "weekly_hours": weekly_hours}

@router.get("/", response_class=HTMLResponse)
async def study_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    today = date.today()
    sessions = await study_service.get_sessions_by_date(db, today, user.id)
    chart_data = await _build_study_chart_data(db, user.id)
    return templates.TemplateResponse(
        request,
        "study.html",
        {
            "sessions": sessions,
            "today": today,
            "weekly_hours": chart_data["weekly_hours"],
            "labels": chart_data["labels"],
            "username": user.username,
        },
    )


@router.get("/chart-data")
async def study_chart_data(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return JSONResponse(await _build_study_chart_data(db, user.id))


@router.get("/ai", response_class=HTMLResponse)
async def study_ai_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    avatar_files = chulk_avatar_service.list_chulk_avatar_files()
    selected_avatar = chulk_avatar_service.sanitize_chulk_avatar_choice(user.chulk_avatar_file, avatar_files)
    return templates.TemplateResponse(
        request,
        "study_ai.html",
        {
            "username": user.username,
            "chulk_avatar_url": chulk_avatar_service.build_chulk_avatar_url(selected_avatar),
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def add_session(
    request: Request,
    subject: str = Form(...),
    duration_minutes: int = Form(...),
    notes: str = Form(None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    data = StudySessionCreate(subject=subject, duration_minutes=duration_minutes, notes=notes)
    session = await study_service.create_session(db, data, date.today(), user.id)
    response = templates.TemplateResponse(
        request, "partials/study_row.html", {"session": session}
    )
    response.headers["HX-Trigger"] = "study-session-added"
    return response


@router.post("/teach/create-session")
async def teach_create_session(
    subject: str = Form(...),
    duration_minutes: int = Form(25),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    clean_subject = (subject or "").strip()[:50]
    if not clean_subject:
        return JSONResponse({"error": "Subject is required."}, status_code=400)

    safe_minutes = max(5, min(int(duration_minutes), 240))
    clean_notes = (notes or "").strip()[:500] if notes else None
    data = StudySessionCreate(
        subject=clean_subject,
        duration_minutes=safe_minutes,
        notes=clean_notes,
    )
    session = await study_service.create_session(db, data, date.today(), user.id)
    return JSONResponse(
        {
            "ok": True,
            "id": session.id,
            "subject": session.subject,
            "duration_minutes": session.duration_minutes,
        }
    )


# ── Calendar ────────────────────────────────────────────────────────────────

@router.get("/calendar", response_class=HTMLResponse)
async def study_calendar_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request,
        "study_calendar.html",
        {
            "username": user.username,
        },
    )

@router.get("/calendar/events")
async def get_calendar_events(
    year: int = Query(...),
    month: int = Query(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end   = date(year, month, last_day)
    r = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == user.id)
        .where(CalendarEvent.event_date >= start)
        .where(CalendarEvent.event_date <= end)
        .order_by(CalendarEvent.event_date)
    )
    events = r.scalars().all()
    return JSONResponse([
        {
            "id":          e.id,
            "title":       e.title,
            "date":        e.event_date.isoformat(),
            "type":        e.event_type.value,
            "description": e.description or "",
        }
        for e in events
    ])


@router.post("/calendar/add")
async def add_calendar_event(
    title:       str        = Form(...),
    event_date:  str        = Form(...),
    event_type:  str        = Form("study"),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    parsed_date = date.fromisoformat(event_date)
    ev = CalendarEvent(
        user_id     = user.id,
        title       = title[:100],
        event_date  = parsed_date,
        event_type  = EventType(event_type),
        description = description[:300] if description else None,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return JSONResponse({
        "id":          ev.id,
        "title":       ev.title,
        "date":        ev.event_date.isoformat(),
        "type":        ev.event_type.value,
        "description": ev.description or "",
    })


@router.post("/calendar/{event_id}/delete")
async def delete_calendar_event(
    event_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ev = await db.get(CalendarEvent, event_id)
    if ev and ev.user_id == user.id:
        await db.delete(ev)
        await db.commit()
    return JSONResponse({"ok": True})


# ── Teach-the-Bot AI Chat ───────────────────────────────────────────────────

@router.get("/teach/subjects")
async def teach_subjects(
    curriculum: str = Query(""),
    user: User = Depends(get_current_user),
):
    # user dependency ensures auth for this endpoint, even though user is unused directly.
    _ = user
    subjects = await curriculum_service.get_subjects_for_curriculum(curriculum)
    return JSONResponse({"subjects": subjects})


@router.post("/teach/start")
async def teach_start(
    request: Request,
    instance_id: str = Form("default"),
    topic: str = Form(""),
    mode: str = Form("listen"),
    user: User = Depends(get_current_user),
):
    clean_instance = instance_id.strip() or "default"
    clean_topic = topic.strip()
    if not clean_topic:
        return JSONResponse({"error": "Please choose curriculum and subject first."}, status_code=400)

    history_key = f"teach_chat_histories_{user.id}"
    topic_key = f"teach_chat_topics_{user.id}"

    histories = request.session.get(history_key, {})
    topics = request.session.get(topic_key, {})
    if not isinstance(histories, dict):
        histories = {}
    if not isinstance(topics, dict):
        topics = {}

    # Starting an instance always resets that instance context.
    histories[clean_instance] = []
    topics[clean_instance] = clean_topic
    request.session[history_key] = histories
    request.session[topic_key] = topics

    clean_mode = mode.strip().lower() if isinstance(mode, str) else "listen"
    if clean_mode not in {"listen", "teacher"}:
        clean_mode = "listen"

    return JSONResponse({"ok": True, "instance_id": clean_instance, "topic": clean_topic, "mode": clean_mode})


@router.post("/teach/instance/delete")
async def teach_delete_instance(
    request: Request,
    instance_id: str = Form("default"),
    user: User = Depends(get_current_user),
):
    clean_instance = instance_id.strip() or "default"
    history_key = f"teach_chat_histories_{user.id}"
    topic_key = f"teach_chat_topics_{user.id}"

    histories = request.session.get(history_key, {})
    topics = request.session.get(topic_key, {})
    if not isinstance(histories, dict):
        histories = {}
    if not isinstance(topics, dict):
        topics = {}

    histories.pop(clean_instance, None)
    topics.pop(clean_instance, None)
    request.session[history_key] = histories
    request.session[topic_key] = topics

    return JSONResponse({"ok": True, "instance_id": clean_instance})


@router.post("/teach/chat")
async def teach_chat(
    request: Request,
    message: str = Form(...),
    topic: str = Form(""),
    mode: str = Form("listen"),
    instance_id: str = Form("default"),
    user: User = Depends(get_current_user),
):
    clean_message = message.strip()
    clean_topic = topic.strip()
    clean_instance = instance_id.strip() or "default"
    clean_mode = mode.strip().lower() if isinstance(mode, str) else "listen"
    if clean_mode not in {"listen", "teacher"}:
        clean_mode = "listen"
    if not clean_message:
        return JSONResponse({"error": "Message cannot be empty."}, status_code=400)
    if not clean_topic:
        return JSONResponse({"error": "Please set a study topic first."}, status_code=400)

    history_key = f"teach_chat_histories_{user.id}"
    histories = request.session.get(history_key, {})
    if not isinstance(histories, dict):
        histories = {}

    history = histories.get(clean_instance, [])
    if not isinstance(history, list):
        history = []

    ai_result = await ai_tutor_service.evaluate_teaching(
        topic=clean_topic,
        mode=clean_mode,
        user_message=clean_message,
        history=history,
    )

    assistant_summary = (
        f"Verdict: {ai_result.get('verdict', 'needs_work')}\n"
        f"Feedback: {ai_result.get('feedback', '')}\n"
        f"Reassurance: {ai_result.get('reassurance', '')}\n"
        f"Follow-up: {ai_result.get('follow_up_question', '')}\n"
        f"Resources: {', '.join(ai_result.get('resources', []))}"
    )

    history.append({"role": "user", "content": clean_message})
    history.append({"role": "assistant", "content": assistant_summary})
    histories[clean_instance] = history[-12:]
    request.session[history_key] = histories

    return JSONResponse(ai_result)
