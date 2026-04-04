# BCN Sustainability (susadmin2)

## Overview
A Flask-based administrative and resource management platform for tracking projects, staffing, billing rates, and employee data. Features a multi-agent AI chat system powered by OpenAI GPT-4o-mini.

## Tech Stack
- **Backend:** Python 3.12 + Flask
- **AI:** OpenAI API (GPT-4o-mini) with 2-agent orchestration (Data Analyst + Consultant Formatter)
- **Database:** PostgreSQL (Replit managed, persists across deployments)
- **Templates:** Jinja2 server-side rendering
- **Reporting:** openpyxl for Excel exports
- **Production Server:** Gunicorn

## Project Structure
- `app.py` — Main Flask application (routes, RBAC, AI chat, Excel exports)
- `utils/db.py` — PostgreSQL database abstraction layer (get/save functions for all entities)
- `utils/json_db.py` — Legacy JSON file utilities (no longer used by app)
- `data/` — Original JSON seed data (used for initial database seeding only)
- `templates/` — Jinja2 HTML templates (admin_*, manager_*, director_*, base.html)
- `static/` — CSS, JavaScript, and image assets (logo, favicon)
- `uploads/` — File upload directory
- `requirements.txt` — Python dependencies

## Database
- **Engine:** PostgreSQL via `psycopg2-binary`
- **Tables:** users, teams, employees, projects, billing_entries, staffing_entries, billing_rates, cost_rates, reports, dropdown_options, insync_employee_orders
- **Connection:** Uses `DATABASE_URL` environment variable (auto-set by Replit)
- **Seeding:** Run `python3 -c "from utils.db import seed_from_json; seed_from_json('data')"` to import JSON data

## Running the App
- Development: `python app.py` (runs on 0.0.0.0:5000)
- Production: `gunicorn --bind=0.0.0.0:5000 --reuse-port --timeout=120 app:app`

## Environment Variables
- `DATABASE_URL` — PostgreSQL connection string (auto-configured)
- `OPENAI_API_KEY` — Required for the AI chat feature

## Key Features
- Role-based access control (Admin, Director, Manager)
- Project and staffing management
- Billing rate tracking
- AI-powered natural language queries over project data (2-agent system)
- Excel report generation ("Master Sheets")
- Admin backup download (exports database as ZIP of JSON files)
- Director view filters persist across page navigation (session-based)
