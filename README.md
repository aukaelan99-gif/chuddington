# StudyWell

StudyWell is a student wellness app that brings study planning, fitness, nutrition, and progress tracking into one place.

## What the Program Does

- Tracks daily study sessions and totals toward your study goal.
- Logs exercise and supports guided workouts with exercise + set tracking.
- Tracks meals, macros, calories, and water intake.
- Shows dashboard and insights views so progress is easy to review.
- Includes a dedicated study calendar page for planning upcoming work.
- Includes Chulk AI study chat with named chat threads for better organization.
- Supports theme selection (including classic default) and Chulk avatar selection.
- Supports account auth flows (register, login, settings, logout).

## Main Features by Page

- Dashboard: daily summary cards, progress bars, and quick status.
- Study: session logging and study activity tracking.
- Calendar: separate planner page for study events.
- Chulk AI: chat assistant with renameable chat instances.
- Exercise + Workout: activity logging and guided workout sessions.
- Diet: meal logging, macro targets, saved meals, water widget.
- Insights: trend and summary views across wellness categories.
- Settings: goals, theme, avatar, and account preferences.

## Tech Stack

- FastAPI
- SQLAlchemy (async)
- SQLite (aiosqlite)
- Jinja2 templates
- HTMX
- Tailwind CSS (CDN)
- Chart.js

## Quick Start

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Run the app.
5. Open the browser.

Example:

```bash
git clone https://github.com/aukaelan99-gif/chuddington.git
cd chuddington/studywell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Then open:

- http://127.0.0.1:8001

## Project Structure

```text
studywell/
  main.py
  database.py
  models.py
  schemas.py
  routers/
  services/
  templates/
  static/
  requirements.txt
```

## Notes

- Local secrets should be configured via local files (see local_secrets example files in the project).
- The database file is created automatically when the app starts.
