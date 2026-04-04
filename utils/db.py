import os
import json
import psycopg2
import psycopg2.extras


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _fetch_all(table, order_by="id"):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT * FROM {table} ORDER BY {order_by}")
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def _save_all(table, rows, columns):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {table}")
            if rows:
                placeholders = ", ".join(["%s"] * len(columns))
                cols = ", ".join(columns)
                for row in rows:
                    values = []
                    for c in columns:
                        v = row.get(c)
                        if isinstance(v, (list, dict)):
                            v = json.dumps(v)
                        values.append(v)
                    cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)
            conn.commit()
    finally:
        conn.close()


USER_COLS = ["id", "email", "password", "first_name", "last_name", "role"]

def get_users():
    return _fetch_all("users")

def save_users(rows):
    _save_all("users", rows, USER_COLS)


TEAM_COLS = ["id", "team_name", "team_type", "team_classification_main",
             "team_classification_1", "team_classification_2", "manager_id",
             "ombudsperson_employee_id", "approved_headcount", "approved_annual_budget"]

def get_teams():
    rows = _fetch_all("teams")
    for r in rows:
        if isinstance(r.get("team_type"), str):
            try:
                r["team_type"] = json.loads(r["team_type"])
            except (json.JSONDecodeError, TypeError):
                r["team_type"] = []
    return rows

def save_teams(rows):
    _save_all("teams", rows, TEAM_COLS)


EMPLOYEE_COLS = ["id", "name", "employee_code", "gender", "designation", "team_id"]

def get_employees():
    return _fetch_all("employees")

def save_employees(rows):
    _save_all("employees", rows, EMPLOYEE_COLS)


PROJECT_COLS = ["id", "project_name", "project_type", "type_for_util",
                "billing_case_code", "client_case_code", "work_description",
                "product", "requestor", "nps_contact", "case_status", "nps_status",
                "case_manager_for_nps", "bcn_case_execution_location",
                "billed_to_end_client", "case_type", "office",
                "case_manager_principal", "client_name", "case_partner",
                "industry", "capability", "master_project_name", "date_of_request",
                "case_delivery_primary_location", "outside_bcn_location",
                "case_poc", "end_client_poc", "team_id", "region"]

def get_projects():
    return _fetch_all("projects")

def save_projects(rows):
    _save_all("projects", rows, PROJECT_COLS)


BILLING_ENTRY_COLS = ["id", "date", "manager_id", "project_id", "project_name",
                      "project_type", "case_code", "billable_ftes", "billing_amount",
                      "comments"]

def get_billing_entries():
    return _fetch_all("billing_entries")

def save_billing_entries(rows):
    _save_all("billing_entries", rows, BILLING_ENTRY_COLS)


STAFFING_ENTRY_COLS = ["id", "date", "manager_id", "employee_id", "staffing_type",
                       "project_id", "project_name", "team_id", "case_code",
                       "hours", "comments"]

def get_staffing_entries():
    return _fetch_all("staffing_entries")

def save_staffing_entries(rows):
    _save_all("staffing_entries", rows, STAFFING_ENTRY_COLS)


BILLING_RATE_COLS = ["id", "region", "project_type", "per_fte_rate"]

def get_billing_rates():
    return _fetch_all("billing_rates")

def save_billing_rates(rows):
    _save_all("billing_rates", rows, BILLING_RATE_COLS)


COST_RATE_COLS = ["id", "designation", "per_fte_rate"]

def get_cost_rates():
    return _fetch_all("cost_rates")

def save_cost_rates(rows):
    _save_all("cost_rates", rows, COST_RATE_COLS)


REPORT_COLS = ["id", "type", "month", "generated_on", "file_name"]

def get_reports():
    return _fetch_all("reports")

def save_reports(rows):
    _save_all("reports", rows, REPORT_COLS)


def get_dropdown_options():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT category, options FROM dropdown_options ORDER BY category")
            rows = cur.fetchall()
            result = {}
            for r in rows:
                opts = r["options"]
                if isinstance(opts, str):
                    try:
                        opts = json.loads(opts)
                    except (json.JSONDecodeError, TypeError):
                        opts = []
                result[r["category"]] = opts
            return result
    finally:
        conn.close()

def save_dropdown_options(data):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM dropdown_options")
            if isinstance(data, dict):
                for category, options in data.items():
                    cur.execute(
                        "INSERT INTO dropdown_options (category, options) VALUES (%s, %s)",
                        (category, json.dumps(options))
                    )
            conn.commit()
    finally:
        conn.close()


def get_insync_employee_orders():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT key, employee_ids FROM insync_employee_orders ORDER BY key")
            rows = cur.fetchall()
            result = {}
            for r in rows:
                ids = r["employee_ids"]
                if isinstance(ids, str):
                    try:
                        ids = json.loads(ids)
                    except (json.JSONDecodeError, TypeError):
                        ids = []
                result[r["key"]] = ids
            return result
    finally:
        conn.close()

def save_insync_employee_orders(data):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM insync_employee_orders")
            if isinstance(data, dict):
                for key, employee_ids in data.items():
                    cur.execute(
                        "INSERT INTO insync_employee_orders (key, employee_ids) VALUES (%s, %s)",
                        (key, json.dumps(employee_ids))
                    )
            conn.commit()
    finally:
        conn.close()


def seed_from_json(data_dir="data"):
    import glob
    mapping = {
        "users.json": (save_users, list),
        "teams.json": (save_teams, list),
        "employees.json": (save_employees, list),
        "projects.json": (save_projects, list),
        "billing_entries.json": (save_billing_entries, list),
        "staffing_entries.json": (save_staffing_entries, list),
        "billing_rates.json": (save_billing_rates, list),
        "cost_rates.json": (save_cost_rates, list),
        "reports.json": (save_reports, list),
        "dropdown_options.json": (save_dropdown_options, dict),
        "insync_employee_orders.json": (save_insync_employee_orders, dict),
    }

    for filename, (save_fn, expected_type) in mapping.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            save_fn(data)
            count = len(data) if isinstance(data, list) else len(data.keys())
            print(f"  Seeded {filename}: {count} records")
        else:
            print(f"  Skipped {filename}: file not found")
