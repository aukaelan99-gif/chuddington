# Chudlite One-Page Speaker Script

## 0:00-0:30 | Opening
Hello judges, and thank you for your time.
We built Chudlite, a student wellness platform that combines study tracking, fitness, nutrition, hydration, and AI-assisted learning in one place.
Our core belief is simple: students perform better when productivity and wellness are managed together, not separately.

## 0:30-1:10 | Problem and Why It Matters
Students already use many tools, but those tools are fragmented.
One app tracks studying, another tracks workouts, another tracks food, and none connect the full daily picture.
That fragmentation creates friction, weakens consistency, and makes healthy habits harder to sustain.
Chudlite solves this by turning disconnected tasks into one clear, daily system.

## 1:10-1:50 | Architecture and Technology
Chudlite is built with FastAPI on the backend, using async routes for responsiveness.
Data is modeled with SQLAlchemy async ORM and stored in SQLite.
Pydantic handles validation and keeps inputs safe and predictable.
The frontend uses Jinja templates and HTMX so interactions feel dynamic without unnecessary frontend complexity.
Tailwind CSS supports consistent UI styling, and Chart.js powers trend visualizations in insights.

## 1:50-4:40 | Demo Walkthrough
I will now walk through the app as a new user.

First, the Dashboard gives a high-level view of progress and priorities for the day.

In Study, I can log sessions and keep momentum visible.
Then in Calendar, I can plan upcoming study events on a dedicated page.

Next is Chulk AI, our study assistant.
I can create chat threads and name them, which makes it practical to track subjects and revisit context later.

In Exercise, I can log activity, and in guided Workout mode I can add exercises and record set-level details.

In Diet, I can log meals and monitor calories and macros.
Hydration tracking is included so wellness data is not limited to food alone.

In Insights, I can review trends across study, exercise, and nutrition to make better daily decisions.

In Settings, I can personalize themes and avatar preferences, improving long-term usability and engagement.

## 4:40-5:10 | Why This Is Strong
What makes Chudlite strong is not one isolated feature.
It is the integration of multiple wellness dimensions into a single, coherent experience.
This is a real product architecture with modular routing, service separation, validation, and practical user flows.

## 5:10-5:30 | Closing
Chudlite addresses a real student problem with a complete and usable solution.
It helps people build better habits through visibility, structure, and low-friction tracking.
Thank you for reviewing our project.
