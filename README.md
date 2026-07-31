# lume-skincare-app
# Lumé, smart care for your natural glow

A web application that builds personalised skincare routines using AI.
Higher Diploma in Science in Computing, National College of Ireland. Final project.

## Current status (Sprint 1)
- User registration and login (passwords hashed)
- Skin profile: create, save, update (SQLite)
- Lilac / blush branded UI, mobile-first

## Coming in Sprint 2
- Product registration (catalogue + owned products)
- AI routine generation via the Anthropic Claude API
- View and save routines

## How to run
1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `python app.py`
3. Open http://127.0.0.1:5000 in your browser

## Project structure
- `app.py` — Flask routes and logic
- `database.py` — SQLite setup and data operations
- `templates/` — HTML pages (Jinja2)
- `static/css/` — stylesheet
- `test_app.py` — automated tests for Sprint 1
