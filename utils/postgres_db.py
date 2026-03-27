import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from typing import Any, List, Dict

def _use_postgres() -> bool:
    """Check if we should use Postgres"""
    return os.getenv("JSON_DB_BACKEND") == "postgres"

def get_db_connection():
    """Get database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL not set in environment variables")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

# Users
def get_users() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return users

def save_users(users: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Delete all and re-insert (simple approach)
    cur.execute("DELETE FROM users")
    if users:
        execute_values(cur, """
            INSERT INTO users (id, username, first_name, last_name, email, password, role)
            VALUES %s
        """, [(u['id'], u.get('username'), u.get('first_name'), u.get('last_name'),
               u.get('email'), u.get('password'), u.get('role')) for u in users])
    
    conn.commit()
    cur.close()
    conn.close()

# Teams
def get_teams() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM teams")
    teams = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return teams

def save_teams(teams: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM teams")
    if teams:
        execute_values(cur, """
            INSERT INTO teams (id, team_name, manager_id, description)
            VALUES %s
        """, [(t['id'], t.get('team_name'), t.get('manager_id'), t.get('description')) for t in teams])
    conn.commit()
    cur.close()
    conn.close()

# Employees  
def get_employees() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees")
    employees = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return employees

def save_employees(employees: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM employees")
    if employees:
        execute_values(cur, """
            INSERT INTO employees (id, name, email, designation, team_id, status)
            VALUES %s
        """, [(e['id'], e.get('name'), e.get('email'), e.get('designation'),
               e.get('team_id'), e.get('status')) for e in employees])
    conn.commit()
    cur.close()
    conn.close()

# Projects
def get_projects() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects")
    projects = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return projects

def save_projects(projects: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM projects")
    if projects:
        execute_values(cur, """
            INSERT INTO projects (id, project_name, case_code, team_id, manager_id, requestor,
                                 billing_region, type_of_project, team_classification_main,
                                 team_classification_1, team_classification_2, status)
            VALUES %s
        """, [(p['id'], p.get('project_name'), p.get('case_code'), p.get('team_id'),
               p.get('manager_id'), p.get('requestor'), p.get('billing_region'),
               p.get('type_of_project'), p.get('team_classification_main'),
               p.get('team_classification_1'), p.get('team_classification_2'),
               p.get('status')) for p in projects])
    conn.commit()
    cur.close()
    conn.close()

# Billing entries
def get_billing_entries() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM billing_entries ORDER BY date DESC")
    entries = [dict(row) for row in cur.fetchall()]
    # Convert date to string
    for e in entries:
        if e.get('date'):
            e['date'] = str(e['date'])
        if e.get('billing_amount'):
            e['billing_amount'] = float(e['billing_amount'])
        if e.get('billable_ftes'):
            e['billable_ftes'] = float(e['billable_ftes'])
    cur.close()
    conn.close()
    return entries

def save_billing_entries(entries: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM billing_entries")
    if entries:
        execute_values(cur, """
            INSERT INTO billing_entries (id, project_id, project_name, case_code, date,
                                         billing_amount, billable_ftes, project_type, manager_id, notes)
            VALUES %s
        """, [(e['id'], e.get('project_id'), e.get('project_name'), e.get('case_code'),
               e.get('date'), e.get('billing_amount'), e.get('billable_ftes'),
               e.get('project_type'), e.get('manager_id'), e.get('notes')) for e in entries])
    conn.commit()
    cur.close()
    conn.close()

# Staffing entries
def get_staffing_entries() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM staffing_entries ORDER BY date DESC")
    entries = [dict(row) for row in cur.fetchall()]
    # Convert date to string and hours to float
    for e in entries:
        if e.get('date'):
            e['date'] = str(e['date'])
        if e.get('hours'):
            e['hours'] = float(e['hours'])
    cur.close()
    conn.close()
    return entries

def save_staffing_entries(entries: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM staffing_entries")
    if entries:
        execute_values(cur, """
            INSERT INTO staffing_entries (id, employee_id, project_id, project_name, date, hours, staffing_type)
            VALUES %s
        """, [(e['id'], e.get('employee_id'), e.get('project_id'), e.get('project_name'),
               e.get('date'), e.get('hours'), e.get('staffing_type')) for e in entries])
    conn.commit()
    cur.close()
    conn.close()

# Billing rates
def get_billing_rates() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM billing_rates")
    rates = [dict(row) for row in cur.fetchall()]
    for r in rates:
        if r.get('rate_per_day'):
            r['rate_per_day'] = float(r['rate_per_day'])
    cur.close()
    conn.close()
    return rates

def save_billing_rates(rates: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM billing_rates")
    if rates:
        execute_values(cur, """
            INSERT INTO billing_rates (id, employee_id, designation, rate_per_day)
            VALUES %s
        """, [(r['id'], r.get('employee_id'), r.get('designation'), r.get('rate_per_day')) for r in rates])
    conn.commit()
    cur.close()
    conn.close()

# Cost rates
def get_cost_rates() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cost_rates")
    rates = [dict(row) for row in cur.fetchall()]
    for r in rates:
        if r.get('cost_per_day'):
            r['cost_per_day'] = float(r['cost_per_day'])
    cur.close()
    conn.close()
    return rates

def save_cost_rates(rates: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM cost_rates")
    if rates:
        execute_values(cur, """
            INSERT INTO cost_rates (id, employee_id, designation, cost_per_day)
            VALUES %s
        """, [(r['id'], r.get('employee_id'), r.get('designation'), r.get('cost_per_day')) for r in rates])
    conn.commit()
    cur.close()
    conn.close()

# Reports
def get_reports() -> List[Dict]:
    if not _use_postgres():
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports")
    reports = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return reports

def save_reports(reports: List[Dict]):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM reports")
    if reports:
        execute_values(cur, """
            INSERT INTO reports (id, report_name, created_at, data)
            VALUES %s
        """, [(r['id'], r.get('report_name'), r.get('created_at'), json.dumps(r)) for r in reports])
    conn.commit()
    cur.close()
    conn.close()

# Dropdown options (stored as JSONB)
def get_dropdown_options() -> Dict:
    if not _use_postgres():
        return {}
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT data FROM dropdown_options LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row['data']) if row else {}

def save_dropdown_options(options: Dict):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM dropdown_options")
    cur.execute("INSERT INTO dropdown_options (data) VALUES (%s)", (json.dumps(options),))
    conn.commit()
    cur.close()
    conn.close()

# Insync employee orders (stored as JSONB)
def get_insync_employee_orders() -> Dict:
    if not _use_postgres():
        return {}
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT data FROM insync_employee_orders LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row['data']) if row else {}

def save_insync_employee_orders(orders: Dict):
    if not _use_postgres():
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM insync_employee_orders")
    cur.execute("INSERT INTO insync_employee_orders (data) VALUES (%s)", (json.dumps(orders),))
    conn.commit()
    cur.close()
    conn.close()
