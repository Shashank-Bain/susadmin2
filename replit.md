# Sustainability Admin (susadmin2)

## Overview
A Flask-based administrative and resource management platform for tracking projects, staffing, billing rates, and employee data. Features a multi-agent AI chat system powered by OpenAI GPT-4o-mini.

## Tech Stack
- **Backend:** Python 3.12 + Flask
- **AI:** OpenAI API (GPT-4o-mini) with custom multi-agent orchestration
- **Data:** Flat-file JSON database (stored in `data/` directory)
- **Templates:** Jinja2 server-side rendering
- **Reporting:** openpyxl for Excel exports
- **Production Server:** Gunicorn

## Project Structure
- `app.py` — Main Flask application (routes, RBAC, AI chat, Excel exports)
- `data/` — JSON flat-file database (users, projects, employees, billing, staffing, etc.)
- `templates/` — Jinja2 HTML templates (admin_*, manager_*, director_*, base.html)
- `static/` — CSS and JavaScript assets
- `utils/json_db.py` — JSON database abstraction layer (atomic writes, backups)
- `uploads/` — File upload directory
- `requirements.txt` — Python dependencies

## Running the App
- Development: `python app.py` (runs on 0.0.0.0:5000)
- Production: `gunicorn --bind=0.0.0.0:5000 --reuse-port app:app`

## Environment Variables
- `OPENAI_API_KEY` — Required for the AI chat feature
- Other secrets managed via `.env` file (python-dotenv)

## Key Features
- Role-based access control (Admin, Director, Manager)
- Project and staffing management
- Billing rate tracking
- AI-powered natural language queries over project data
- Excel report generation ("Master Sheets")
- Vercel Blob Storage sync (optional)
