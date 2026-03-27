#!/usr/bin/env python3
"""
Migrate JSON data to Postgres database.
Run this once to populate your database with data from local JSON files.

Usage:
    python migrate_to_postgres.py
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env file")
    exit(1)

# Connect to database
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("Creating tables...")

# Create tables
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(200) UNIQUE,
    password VARCHAR(200),
    role VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS teams (
    id VARCHAR(50) PRIMARY KEY,
    team_name VARCHAR(200),
    manager_id VARCHAR(50),
    description TEXT
);

CREATE TABLE IF NOT EXISTS employees (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200),
    email VARCHAR(200),
    designation VARCHAR(100),
    team_id VARCHAR(50),
    status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(50) PRIMARY KEY,
    project_name VARCHAR(300),
    case_code VARCHAR(100),
    team_id VARCHAR(50),
    manager_id VARCHAR(50),
    requestor VARCHAR(200),
    billing_region VARCHAR(100),
    type_of_project VARCHAR(100),
    team_classification_main VARCHAR(100),
    team_classification_1 VARCHAR(100),
    team_classification_2 VARCHAR(100),
    status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS billing_entries (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(50),
    project_name VARCHAR(300),
    case_code VARCHAR(100),
    date DATE,
    billing_amount NUMERIC(10, 2),
    billable_ftes NUMERIC(5, 2),
    project_type VARCHAR(100),
    manager_id VARCHAR(50),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS staffing_entries (
    id VARCHAR(50) PRIMARY KEY,
    employee_id VARCHAR(50),
    project_id VARCHAR(50),
    project_name VARCHAR(300),
    date DATE,
    hours NUMERIC(5, 2),
    staffing_type VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS billing_rates (
    id VARCHAR(50) PRIMARY KEY,
    employee_id VARCHAR(50),
    designation VARCHAR(100),
    rate_per_day NUMERIC(10, 2)
);

CREATE TABLE IF NOT EXISTS cost_rates (
    id VARCHAR(50) PRIMARY KEY,
    employee_id VARCHAR(50),
    designation VARCHAR(100),
    cost_per_day NUMERIC(10, 2)
);

CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(50) PRIMARY KEY,
    report_name VARCHAR(200),
    created_at TIMESTAMP,
    data JSONB
);

CREATE TABLE IF NOT EXISTS dropdown_options (
    id SERIAL PRIMARY KEY,
    data JSONB
);

CREATE TABLE IF NOT EXISTS insync_employee_orders (
    id SERIAL PRIMARY KEY,
    data JSONB
);
""")

conn.commit()
print("✓ Tables created")

# Load and insert data
def load_json(filename):
    filepath = f"data/{filename}"
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [] if filename != 'dropdown_options.json' and filename != 'insync_employee_orders.json' else {}

print("\nMigrating data...")

# Users
users = load_json("users.json")
if users:
    execute_values(cur, """
        INSERT INTO users (id, username, first_name, last_name, email, password, role)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            email = EXCLUDED.email,
            password = EXCLUDED.password,
            role = EXCLUDED.role
    """, [(u['id'], u.get('username'), u.get('first_name'), u.get('last_name'), 
           u.get('email'), u.get('password'), u.get('role')) for u in users])
    print(f"✓ Migrated {len(users)} users")

# Teams
teams = load_json("teams.json")
if teams:
    execute_values(cur, """
        INSERT INTO teams (id, team_name, manager_id, description)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            team_name = EXCLUDED.team_name,
            manager_id = EXCLUDED.manager_id,
            description = EXCLUDED.description
    """, [(t['id'], t.get('team_name'), t.get('manager_id'), t.get('description')) for t in teams])
    print(f"✓ Migrated {len(teams)} teams")

# Employees
employees = load_json("employees.json")
if employees:
    execute_values(cur, """
        INSERT INTO employees (id, name, email, designation, team_id, status)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            designation = EXCLUDED.designation,
            team_id = EXCLUDED.team_id,
            status = EXCLUDED.status
    """, [(e['id'], e.get('name'), e.get('email'), e.get('designation'), 
           e.get('team_id'), e.get('status')) for e in employees])
    print(f"✓ Migrated {len(employees)} employees")

# Projects
projects = load_json("projects.json")
if projects:
    execute_values(cur, """
        INSERT INTO projects (id, project_name, case_code, team_id, manager_id, requestor, 
                             billing_region, type_of_project, team_classification_main,
                             team_classification_1, team_classification_2, status)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            project_name = EXCLUDED.project_name,
            case_code = EXCLUDED.case_code,
            team_id = EXCLUDED.team_id,
            manager_id = EXCLUDED.manager_id,
            requestor = EXCLUDED.requestor,
            billing_region = EXCLUDED.billing_region,
            type_of_project = EXCLUDED.type_of_project,
            team_classification_main = EXCLUDED.team_classification_main,
            team_classification_1 = EXCLUDED.team_classification_1,
            team_classification_2 = EXCLUDED.team_classification_2,
            status = EXCLUDED.status
    """, [(p['id'], p.get('project_name'), p.get('case_code'), p.get('team_id'),
           p.get('manager_id'), p.get('requestor'), p.get('billing_region'),
           p.get('type_of_project'), p.get('team_classification_main'),
           p.get('team_classification_1'), p.get('team_classification_2'),
           p.get('status')) for p in projects])
    print(f"✓ Migrated {len(projects)} projects")

# Billing Entries
billing_entries = load_json("billing_entries.json")
if billing_entries:
    execute_values(cur, """
        INSERT INTO billing_entries (id, project_id, project_name, case_code, date, 
                                     billing_amount, billable_ftes, project_type, manager_id, notes)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            project_id = EXCLUDED.project_id,
            project_name = EXCLUDED.project_name,
            case_code = EXCLUDED.case_code,
            date = EXCLUDED.date,
            billing_amount = EXCLUDED.billing_amount,
            billable_ftes = EXCLUDED.billable_ftes,
            project_type = EXCLUDED.project_type,
            manager_id = EXCLUDED.manager_id,
            notes = EXCLUDED.notes
    """, [(b['id'], b.get('project_id'), b.get('project_name'), b.get('case_code'),
           b.get('date'), b.get('billing_amount'), b.get('billable_ftes'),
           b.get('project_type'), b.get('manager_id'), b.get('notes')) for b in billing_entries])
    print(f"✓ Migrated {len(billing_entries)} billing entries")

# Staffing Entries
staffing_entries = load_json("staffing_entries.json")
if staffing_entries:
    execute_values(cur, """
        INSERT INTO staffing_entries (id, employee_id, project_id, project_name, date, hours, staffing_type)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            employee_id = EXCLUDED.employee_id,
            project_id = EXCLUDED.project_id,
            project_name = EXCLUDED.project_name,
            date = EXCLUDED.date,
            hours = EXCLUDED.hours,
            staffing_type = EXCLUDED.staffing_type
    """, [(s['id'], s.get('employee_id'), s.get('project_id'), s.get('project_name'),
           s.get('date'), s.get('hours'), s.get('staffing_type')) for s in staffing_entries])
    print(f"✓ Migrated {len(staffing_entries)} staffing entries")

# Billing & Cost Rates
billing_rates = load_json("billing_rates.json")
if billing_rates:
    execute_values(cur, """
        INSERT INTO billing_rates (id, employee_id, designation, rate_per_day)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            employee_id = EXCLUDED.employee_id,
            designation = EXCLUDED.designation,
            rate_per_day = EXCLUDED.rate_per_day
    """, [(r['id'], r.get('employee_id'), r.get('designation'), r.get('rate_per_day')) for r in billing_rates])
    print(f"✓ Migrated {len(billing_rates)} billing rates")

cost_rates = load_json("cost_rates.json")
if cost_rates:
    execute_values(cur, """
        INSERT INTO cost_rates (id, employee_id, designation, cost_per_day)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            employee_id = EXCLUDED.employee_id,
            designation = EXCLUDED.designation,
            cost_per_day = EXCLUDED.cost_per_day
    """, [(r['id'], r.get('employee_id'), r.get('designation'), r.get('cost_per_day')) for r in cost_rates])
    print(f"✓ Migrated {len(cost_rates)} cost rates")

# Reports (JSONB)
reports = load_json("reports.json")
if reports:
    execute_values(cur, """
        INSERT INTO reports (id, report_name, created_at, data)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            report_name = EXCLUDED.report_name,
            created_at = EXCLUDED.created_at,
            data = EXCLUDED.data
    """, [(r['id'], r.get('report_name'), r.get('created_at'), json.dumps(r)) for r in reports])
    print(f"✓ Migrated {len(reports)} reports")

# Dropdown options (store as JSONB)
dropdown_options = load_json("dropdown_options.json")
if dropdown_options:
    cur.execute("DELETE FROM dropdown_options")
    cur.execute("INSERT INTO dropdown_options (data) VALUES (%s)", (json.dumps(dropdown_options),))
    print(f"✓ Migrated dropdown options")

# Insync employee orders (store as JSONB)
insync_orders = load_json("insync_employee_orders.json")
if insync_orders:
    cur.execute("DELETE FROM insync_employee_orders")
    cur.execute("INSERT INTO insync_employee_orders (data) VALUES (%s)", (json.dumps(insync_orders),))
    print(f"✓ Migrated insync employee orders")

conn.commit()
cur.close()
conn.close()

print("\n✅ Migration complete!")
print("Your data is now in Postgres. Next step: update your app to use Postgres.")
