from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, send_file
from functools import wraps
from datetime import datetime, timedelta
from io import StringIO, BytesIO
import csv, os
from utils.json_db import load_json, save_json, upload_file_to_blob, download_blob_file

app = Flask(__name__)
app.secret_key = "change-this-in-production"

DATA_DIR = "data"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def data_path(name): return f"{DATA_DIR}/{name}"
def get_users(): return load_json(data_path("users.json"), [])
def get_teams(): return load_json(data_path("teams.json"), [])
def get_employees(): return load_json(data_path("employees.json"), [])
def get_projects(): return load_json(data_path("projects.json"), [])
def get_billing_rates(): return load_json(data_path("billing_rates.json"), [])
def get_cost_rates(): return load_json(data_path("cost_rates.json"), [])
def get_staffing_entries(): return load_json(data_path("staffing_entries.json"), [])
def get_billing_entries(): return load_json(data_path("billing_entries.json"), [])
def get_reports(): return load_json(data_path("reports.json"), [])
def get_director_metrics(): return load_json(data_path("director_metrics.json"), {})
def get_dropdown_options(): return load_json(data_path("dropdown_options.json"), {})

def save_staffing_entries(rows): save_json(data_path("staffing_entries.json"), rows)
def save_billing_entries(rows): save_json(data_path("billing_entries.json"), rows)
def save_projects(rows): save_json(data_path("projects.json"), rows)
def save_users(rows): save_json(data_path("users.json"), rows)
def save_teams(rows): save_json(data_path("teams.json"), rows)
def save_employees(rows): save_json(data_path("employees.json"), rows)
def save_billing_rates(rows): save_json(data_path("billing_rates.json"), rows)
def save_cost_rates(rows): save_json(data_path("cost_rates.json"), rows)
def save_reports(rows): save_json(data_path("reports.json"), rows)
def save_dropdown_options(rows): save_json(data_path("dropdown_options.json"), rows)

FULL_PROJECT_FIELDS = [
    "project_name","project_type","type_for_util","billing_case_code","client_case_code","work_description","product","requestor",
    "nps_contact","case_status","nps_status","case_manager_for_nps","bcn_case_execution_location",
    "billed_to_end_client","case_type","office","case_manager_principal","client_name","case_partner","industry","capability",
    "master_project_name","date_of_request","case_delivery_primary_location","outside_bcn_location","case_poc","end_client_poc","team_id"
]

def next_id(prefix, rows):
    max_num = 0
    for row in rows:
        value = row.get("id", "")
        if value.startswith(prefix):
            try: max_num = max(max_num, int(value.replace(prefix, "")))
            except ValueError: pass
    return f"{prefix}{max_num + 1:03d}"

def find_user_by_email(email):
    for user in get_users():
        if user.get("email", "").lower() == email.lower():
            return user
    return None

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"): return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user: return redirect(url_for("login"))
            if user.get("role") not in allowed_roles:
                flash("You do not have access to that page.", "error")
                return redirect(url_for("route_by_role"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def can_edit_project(user, project):
    if not user or not project:
        return False
    if user.get("role") == "ADMIN":
        return True
    if user.get("role") == "MANAGER" and project.get("created_by") == user.get("id"):
        return True
    return False

def previous_working_day(date_str):
    current = datetime.strptime(date_str, "%Y-%m-%d").date() - timedelta(days=1)
    while current.weekday() > 4: current -= timedelta(days=1)
    return current.strftime("%Y-%m-%d")

def get_greeting():
    hour = datetime.now().hour
    if hour < 12: return "Good Morning"
    if hour < 17: return "Good Afternoon"
    return "Good Evening"

def derive_billing_rows(staffing_rows):
    projects = {p["id"]: p for p in get_projects()}
    rates = get_billing_rates()
    rate_map = {}
    for r in rates:
        rate_map[(r.get("region", "Global"), r.get("project_type", ""))] = float(r.get("per_fte_rate", 0))
    grouped = {}
    for row in staffing_rows:
        project_id = row.get("project_id", "")
        case_code = row.get("case_code", "")
        project = projects.get(project_id, {})
        project_name = row.get("project_name") or project.get("project_name", "")
        project_type = project.get("project_type", "Other CD/IP Codes")
        key = (project_id, project_name, project_type, case_code)
        grouped.setdefault(key, {"project_id": project_id, "project_name": project_name, "project_type": project_type, "case_code": case_code, "billable_ftes": 0, "billing_amount": 0, "comments": ""})
        grouped[key]["billable_ftes"] += float(row.get("hours", 0)) / 8.0
    output = []
    for item in grouped.values():
        rate = rate_map.get(("Global", item["project_type"]), 0)
        item["billable_ftes"] = round(item["billable_ftes"], 2)
        item["billing_amount"] = round(item["billable_ftes"] * rate, 2)
        output.append(item)
    return output

def build_master_sheet_rows():
    staffing = get_staffing_entries()
    employees = {e["id"]: e for e in get_employees()}
    teams = {t["id"]: t for t in get_teams()}
    projects = {p["id"]: p for p in get_projects()}
    managers = {u["id"]: u for u in get_users()}
    rows = []
    for item in staffing:
        emp = employees.get(item.get("employee_id", ""), {})
        proj = projects.get(item.get("project_id", ""), {})
        mgr = managers.get(item.get("manager_id", ""), {})
        team = teams.get(emp.get("team_id", ""), {})
        rows.append({
            "id": item.get("id"),
            "date": item.get("date"),
            "manager_id": item.get("manager_id"),
            "employee_id": item.get("employee_id"),
            "project_id": item.get("project_id"),
            "manager": f'{mgr.get("first_name","")} {mgr.get("last_name","")}'.strip(),
            "employee": emp.get("name", ""),
            "designation": emp.get("designation", ""),
            "team": team.get("team_name", ""),
            "staffing_type": item.get("staffing_type", ""),
            "project": proj.get("project_name", item.get("project_name","")),
            "case_code": item.get("case_code", ""),
            "hours": item.get("hours", 0),
            "comments": item.get("comments", "")
        })
    return rows

def find_by_id(rows, item_id):
    return next((r for r in rows if r.get("id") == item_id), None)

@app.context_processor
def inject_globals():
    return {"current_user": session.get("user"), "dropdowns": get_dropdown_options()}

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"): return redirect(url_for("route_by_role"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        user = find_user_by_email(email)
        if user and user.get("password") == password:
            session["user"] = {"id": user["id"], "email": user["email"], "first_name": user["first_name"], "last_name": user["last_name"], "role": user["role"]}
            return redirect(url_for("route_by_role"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/route-by-role")
@login_required
def route_by_role():
    role = session["user"]["role"]
    if role == "ADMIN": return redirect(url_for("admin_home"))
    if role == "DIRECTOR": return redirect(url_for("director_home"))
    return redirect(url_for("manager_home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = session["user"]
    if request.method == "POST":
        users = get_users()
        for item in users:
            if item["id"] == user["id"]:
                item["first_name"] = request.form.get("first_name", item["first_name"]).strip() or item["first_name"]
                item["last_name"] = request.form.get("last_name", item["last_name"]).strip() or item["last_name"]
                new_password = request.form.get("password", "").strip()
                if new_password: item["password"] = new_password
                user["first_name"] = item["first_name"]; user["last_name"] = item["last_name"]; session["user"] = user
                break
        save_users(users); flash("Profile updated.", "success"); return redirect(url_for("profile"))
    return render_template("profile.html")

@app.route("/admin")
@login_required
@roles_required("ADMIN")
def admin_home():
    stats = {"users": len(get_users()), "teams": len(get_teams()), "employees": len(get_employees()), "projects": len(get_projects())}
    return render_template("admin_home.html", stats=stats)

@app.route("/admin/master-sheet")
@login_required
@roles_required("ADMIN")
def admin_master_sheet():
    return render_template("admin_master_sheet.html", rows=build_master_sheet_rows())

@app.route("/admin/master-sheet/edit/<item_id>", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def admin_master_sheet_edit(item_id):
    staffing = get_staffing_entries()
    item = find_by_id(staffing, item_id)
    if not item: flash("Master sheet entry not found.", "error"); return redirect(url_for("admin_master_sheet"))
    if request.method == "POST":
        item["date"] = request.form.get("date", "").strip()
        item["manager_id"] = request.form.get("manager_id", "").strip()
        item["employee_id"] = request.form.get("employee_id", "").strip()
        item["project_id"] = request.form.get("project_id", "").strip()
        item["staffing_type"] = request.form.get("staffing_type", "").strip()
        item["case_code"] = request.form.get("case_code", "").strip()
        item["hours"] = float(request.form.get("hours", "0") or 0)
        item["comments"] = request.form.get("comments", "").strip()
        save_staffing_entries(staffing)
        flash("Master sheet entry updated.", "success")
        return redirect(url_for("admin_master_sheet"))
    return render_template("admin_master_sheet_edit.html", item=item, users=get_users(), employees=get_employees(), projects=get_projects(), staffing_options=get_dropdown_options().get("staffing_type", []))

@app.route("/admin/master-sheet/delete/<item_id>")
@login_required
@roles_required("ADMIN")
def admin_master_sheet_delete(item_id):
    save_staffing_entries([r for r in get_staffing_entries() if r.get("id") != item_id])
    flash("Master sheet entry deleted.", "success")
    return redirect(url_for("admin_master_sheet"))

@app.route("/admin/export/master-sheet.csv")
@login_required
@roles_required("ADMIN")
def export_master_sheet_csv():
    rows = build_master_sheet_rows()
    output = StringIO(); writer = csv.DictWriter(output, fieldnames=["id","date", "manager", "employee", "designation", "team", "staffing_type", "project", "case_code", "hours", "comments"])
    writer.writeheader(); writer.writerows(rows)
    mem = BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="master_sheet.csv")

# Keep existing routes behavior for other admin modules from current app by rendering existing templates and saving if present
@app.route("/admin/users")
@login_required
@roles_required("ADMIN")
def admin_users(): return render_template("admin_users.html", rows=get_users())

@app.route("/admin/users/edit/<item_id>", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def admin_users_edit(item_id):
    rows = get_users()
    item = find_by_id(rows, item_id)

    if not item:
        flash("User not found.", "error")
        return redirect(url_for("admin_users"))

    if request.method == "POST":
        item["first_name"] = request.form.get("first_name", "").strip()
        item["last_name"] = request.form.get("last_name", "").strip()
        item["email"] = request.form.get("email", "").strip()
        item["role"] = request.form.get("role", "MANAGER").strip()

        password = request.form.get("password", "").strip()
        if password:
            item["password"] = password

        save_users(rows)
        flash("User updated.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_edit.html", item=item)

@app.route("/admin/users/delete/<item_id>")
@login_required
@roles_required("ADMIN")
def admin_users_delete(item_id):
    save_users([r for r in get_users() if r.get("id") != item_id])
    flash("User deleted.", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/teams")
@login_required
@roles_required("ADMIN")
def admin_teams(): return render_template("admin_teams.html", rows=get_teams(), managers=[u for u in get_users() if u.get("role")=="MANAGER"], employees=get_employees())

@app.route("/admin/teams/edit/<item_id>", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def admin_teams_edit(item_id):
    rows = get_teams()
    item = find_by_id(rows, item_id)

    if not item:
        flash("Team not found.", "error")
        return redirect(url_for("admin_teams"))

    if request.method == "POST":
        item["team_name"] = request.form.get("team_name", "").strip()
        item["team_type"] = request.form.getlist("team_type")
        item["team_classification_main"] = request.form.get("team_classification_main", "").strip()
        item["team_classification_1"] = request.form.get("team_classification_1", "").strip()
        item["team_classification_2"] = request.form.get("team_classification_2", "").strip()
        item["manager_id"] = request.form.get("manager_id", "").strip()
        item["ombudsperson_employee_id"] = request.form.get("ombudsperson_employee_id", "").strip()

        save_teams(rows)
        flash("Team updated.", "success")
        return redirect(url_for("admin_teams"))

    return render_template(
        "admin_team_edit.html",
        item=item,
        managers=[u for u in get_users() if u.get("role") == "MANAGER"],
        employees=get_employees()
    )

@app.route("/admin/teams/delete/<item_id>")
@login_required
@roles_required("ADMIN")
def admin_teams_delete(item_id):
    save_teams([r for r in get_teams() if r.get("id") != item_id])
    flash("Team deleted.", "success")
    return redirect(url_for("admin_teams"))

@app.route("/admin/employees")
@login_required
@roles_required("ADMIN")
def admin_employees(): return render_template("admin_employees.html", rows=get_employees(), teams=get_teams())

@app.route("/admin/employees/edit/<item_id>", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def admin_employees_edit(item_id):
    rows = get_employees()
    item = find_by_id(rows, item_id)

    if not item:
        flash("Employee not found.", "error")
        return redirect(url_for("admin_employees"))

    if request.method == "POST":
        item["name"] = request.form.get("name", "").strip()
        item["employee_code"] = request.form.get("employee_code", "").strip()
        item["gender"] = request.form.get("gender", "").strip()
        item["designation"] = request.form.get("designation", "").strip()
        item["team_id"] = request.form.get("team_id", "").strip()

        save_employees(rows)
        flash("Employee updated.", "success")
        return redirect(url_for("admin_employees"))

    return render_template("admin_employee_edit.html", item=item, teams=get_teams())

@app.route("/admin/employees/delete/<item_id>")
@login_required
@roles_required("ADMIN")
def admin_employees_delete(item_id):
    save_employees([r for r in get_employees() if r.get("id") != item_id])
    flash("Employee deleted.", "success")
    return redirect(url_for("admin_employees"))

@app.route("/admin/projects")
@login_required
@roles_required("ADMIN")
def admin_projects(): return render_template("admin_projects.html", rows=get_projects(), teams=get_teams(), users=get_users())

@app.route("/admin/projects/edit/<item_id>", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def admin_projects_edit(item_id):
    rows = get_projects()
    item = find_by_id(rows, item_id)

    if not item:
        flash("Project not found.", "error")
        return redirect(url_for("admin_projects"))

    if request.method == "POST":
        for key in FULL_PROJECT_FIELDS:
            item[key] = request.form.get(key, "").strip()

        save_projects(rows)
        flash("Project updated.", "success")
        return redirect(url_for("admin_projects"))

    return render_template(
        "admin_project_edit.html",
        item=item,
        teams=get_teams(),
        users=get_users()
    )

@app.route("/admin/projects/delete/<item_id>")
@login_required
@roles_required("ADMIN")
def admin_projects_delete(item_id):
    save_projects([r for r in get_projects() if r.get("id") != item_id])
    flash("Project deleted.", "success")
    return redirect(url_for("admin_projects"))

@app.route("/admin/billing-rates")
@login_required
@roles_required("ADMIN")
def admin_billing_rates(): return render_template("admin_billing_rates.html", rows=get_billing_rates())

@app.route("/admin/billing-rates/edit/<item_id>", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def admin_billing_rates_edit(item_id):
    rows = get_billing_rates()
    item = find_by_id(rows, item_id)

    if not item:
        flash("Billing rate not found.", "error")
        return redirect(url_for("admin_billing_rates"))

    if request.method == "POST":
        item["region"] = request.form.get("region", "").strip()
        item["project_type"] = request.form.get("project_type", "").strip()
        item["per_fte_rate"] = request.form.get("per_fte_rate", "").strip() or "0"

        save_billing_rates(rows)
        flash("Billing rate updated.", "success")
        return redirect(url_for("admin_billing_rates"))

    return render_template("admin_billing_rate_edit.html", item=item)

@app.route("/admin/billing-rates/delete/<item_id>")
@login_required
@roles_required("ADMIN")
def admin_billing_rates_delete(item_id):
    save_billing_rates([r for r in get_billing_rates() if r.get("id") != item_id])
    flash("Billing rate deleted.", "success")
    return redirect(url_for("admin_billing_rates"))

@app.route("/admin/cost-rates")
@login_required
@roles_required("ADMIN")
def admin_cost_rates(): return render_template("admin_cost_rates.html", rows=get_cost_rates())

@app.route("/admin/cost-rates/edit/<item_id>", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def admin_cost_rates_edit(item_id):
    rows = get_cost_rates()
    item = find_by_id(rows, item_id)

    if not item:
        flash("Cost rate not found.", "error")
        return redirect(url_for("admin_cost_rates"))

    if request.method == "POST":
        item["designation"] = request.form.get("designation", "").strip()
        item["per_fte_rate"] = request.form.get("per_fte_rate", "").strip() or "0"

        save_cost_rates(rows)
        flash("Cost rate updated.", "success")
        return redirect(url_for("admin_cost_rates"))

    return render_template("admin_cost_rate_edit.html", item=item)

@app.route("/admin/cost-rates/delete/<item_id>")
@login_required
@roles_required("ADMIN")
def admin_cost_rates_delete(item_id):
    save_cost_rates([r for r in get_cost_rates() if r.get("id") != item_id])
    flash("Cost rate deleted.", "success")
    return redirect(url_for("admin_cost_rates"))

@app.route("/admin/reports")
@login_required
@roles_required("ADMIN")
def admin_reports(): return render_template("admin_reports.html", rows=get_reports())

@app.route("/admin/reports/delete/<item_id>")
@login_required
@roles_required("ADMIN")
def admin_reports_delete(item_id):
    save_reports([r for r in get_reports() if r.get("id") != item_id])
    flash("Report deleted.", "success")
    return redirect(url_for("admin_reports"))

@app.route("/admin/dropdown-options")
@login_required
@roles_required("ADMIN")
def admin_dropdown_options(): return render_template("admin_dropdown_options.html", options=get_dropdown_options())

@app.route("/admin/dropdown-options/delete", methods=["POST"])
@login_required
@roles_required("ADMIN")
def admin_dropdown_options_delete():
    options = get_dropdown_options()
    key = request.form.get("key", "").strip()
    value = request.form.get("value", "").strip()

    if key in options:
        options[key] = [v for v in options[key] if v != value]
        save_dropdown_options(options)
        flash("Option removed.", "success")

    return redirect(url_for("admin_dropdown_options"))

@app.route("/reports/download/<item_id>")
@login_required
def reports_download(item_id):
    item = next((r for r in get_reports() if r.get("id") == item_id), None)
    if not item: flash("Report not found.", "error"); return redirect(url_for("route_by_role"))
    stored = item.get("stored_file", "")
    if stored and os.path.exists(os.path.join(UPLOAD_DIR, stored)):
        return send_file(os.path.join(UPLOAD_DIR, stored), as_attachment=True, download_name=item.get("file_name") or stored)
    flash("Physical file not uploaded yet. This is still a placeholder metadata record.", "error")
    return redirect(request.referrer or url_for("route_by_role"))

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

def month_label(dt):
    return dt.strftime("%b %Y")

def money_fmt(value):
    return f"${value:,.0f}"

def pct_fmt(value):
    return f"{value:.0f}%"

def safe_float(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0

def working_days_in_month(year, month):
    if month == 12:
        next_month = datetime(year + 1, 1, 1).date()
    else:
        next_month = datetime(year, month + 1, 1).date()
    start = datetime(year, month, 1).date()
    days = 0
    current = start
    while current < next_month:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days

def get_available_reporting_months():
    staffing_entries = get_staffing_entries()
    billing_entries = get_billing_entries()

    month_set = set()

    for row in staffing_entries:
        dt = parse_date(row.get("date", ""))
        if dt:
            month_set.add((dt.year, dt.month))

    for row in billing_entries:
        dt = parse_date(row.get("date", ""))
        if dt:
            month_set.add((dt.year, dt.month))

    if not month_set:
        today = datetime.now().date()
        month_set.add((today.year, today.month))

    ordered = sorted(month_set)
    return [datetime(year, month, 1).strftime("%b %Y") for year, month in ordered]

def parse_selected_month(selected_month):
    try:
        dt = datetime.strptime(selected_month, "%b %Y")
        return dt.year, dt.month
    except Exception:
        today = datetime.now().date()
        return today.year, today.month

def build_director_metrics(selected_month):
    year, month = parse_selected_month(selected_month)

    employees = get_employees()
    teams = get_teams()
    users = get_users()
    projects = get_projects()
    staffing_entries = get_staffing_entries()
    billing_entries = get_billing_entries()
    cost_rates = get_cost_rates()

    project_map = {p["id"]: p for p in projects if p.get("id")}
    team_map = {t["id"]: t for t in teams if t.get("id")}
    user_map = {u["id"]: u for u in users if u.get("id")}
    employee_map = {e["id"]: e for e in employees if e.get("id")}

    cost_rate_map = {}
    for row in cost_rates:
        designation = (row.get("designation") or "").strip()
        cost_rate_map[designation] = safe_float(row.get("per_fte_rate", 0))

    # Current month filters
    month_staffing = []
    month_billing = []

    for row in staffing_entries:
        dt = parse_date(row.get("date", ""))
        if dt and dt.year == year and dt.month == month:
            month_staffing.append(row)

    for row in billing_entries:
        dt = parse_date(row.get("date", ""))
        if dt and dt.year == year and dt.month == month:
            month_billing.append(row)

    # Previous month for trend comparison
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    prev_month_staffing = []
    prev_month_billing = []

    for row in staffing_entries:
        dt = parse_date(row.get("date", ""))
        if dt and dt.year == prev_year and dt.month == prev_month:
            prev_month_staffing.append(row)

    for row in billing_entries:
        dt = parse_date(row.get("date", ""))
        if dt and dt.year == prev_year and dt.month == prev_month:
            prev_month_billing.append(row)

    # FTEs by average daily staffed hours in month
    current_days = sorted({r.get("date") for r in month_staffing if r.get("date")})
    prev_days = sorted({r.get("date") for r in prev_month_staffing if r.get("date")})

    total_ftes = 0.0
    if current_days:
        total_ftes = sum(
            sum(safe_float(r.get("hours", 0)) for r in month_staffing if r.get("date") == day) / 8.0
            for day in current_days
        ) / len(current_days)

    prev_total_ftes = 0.0
    if prev_days:
        prev_total_ftes = sum(
            sum(safe_float(r.get("hours", 0)) for r in prev_month_staffing if r.get("date") == day) / 8.0
            for day in prev_days
        ) / len(prev_days)

    fte_trend = f"{total_ftes - prev_total_ftes:+.1f}"

    total_billing = sum(safe_float(r.get("billing_amount", 0)) for r in month_billing)
    prev_total_billing = sum(safe_float(r.get("billing_amount", 0)) for r in prev_month_billing)
    billing_trend = money_fmt(total_billing - prev_total_billing)

    # Cost / recovery
    # Gross cost based on staffed hours and cost rate per designation
    gross_cost = 0.0
    for row in month_staffing:
        emp = employee_map.get(row.get("employee_id", ""), {})
        designation = emp.get("designation", "")
        per_fte_rate = cost_rate_map.get(designation, 0.0)
        gross_cost += (safe_float(row.get("hours", 0)) / 8.0) * per_fte_rate

    recovery_pct = (total_billing / gross_cost * 100.0) if gross_cost > 0 else 0.0

    # Gender ratio
    male_count = len([e for e in employees if (e.get("gender") or "").strip().lower() == "male"])
    female_count = len([e for e in employees if (e.get("gender") or "").strip().lower() == "female"])
    gender_ratio = f"{male_count}:{female_count}" if (male_count or female_count) else "-"
    total_gender_known = male_count + female_count
    female_share = pct_fmt((female_count / total_gender_known) * 100.0) if total_gender_known else "-"

    # NPS / CTSU currently unavailable in your live data model
    nps_value = "-"
    ctsu_value = "-"
    nps_trend = "-"
    ctsu_trend = "-"

    # Major clients by billing in selected month
    client_billing = {}
    client_projects = {}

    for row in month_billing:
        project = project_map.get(row.get("project_id", ""), {})
        client_name = (project.get("client_name") or "Unknown Client").strip() or "Unknown Client"
        project_name = project.get("project_name", row.get("project_name", ""))
        client_billing[client_name] = client_billing.get(client_name, 0.0) + safe_float(row.get("billing_amount", 0))
        client_projects.setdefault(client_name, set()).add(project_name)

    major_clients = []
    for client_name, amount in sorted(client_billing.items(), key=lambda x: x[1], reverse=True)[:5]:
        major_clients.append({
            "name": client_name,
            "projects": len([p for p in client_projects.get(client_name, set()) if p]),
            "billing": money_fmt(amount)
        })

    # Notes from live data
    notes = []
    notes.append(f"Billing for {selected_month} is {money_fmt(total_billing)}.")
    notes.append(f"Average staffed FTEs for {selected_month} is {total_ftes:.1f}.")
    notes.append(f"Recovery for {selected_month} is {pct_fmt(recovery_pct)} based on available cost rates.")
    if major_clients:
        notes.append(f"Top billed client this month is {major_clients[0]['name']} at {major_clients[0]['billing']}.")
    else:
        notes.append("No billed client work found for the selected month.")

    # Monthly trend across all available months
    available_months = get_available_reporting_months()
    monthly_trend = []

    for month_name in available_months:
        y, m = parse_selected_month(month_name)
        trend_staffing = [r for r in staffing_entries if (parse_date(r.get("date", "")) and parse_date(r.get("date", "")).year == y and parse_date(r.get("date", "")).month == m)]
        trend_billing = [r for r in billing_entries if (parse_date(r.get("date", "")) and parse_date(r.get("date", "")).year == y and parse_date(r.get("date", "")).month == m)]

        trend_days = sorted({r.get("date") for r in trend_staffing if r.get("date")})
        trend_ftes = 0.0
        if trend_days:
            trend_ftes = sum(
                sum(safe_float(r.get("hours", 0)) for r in trend_staffing if r.get("date") == day) / 8.0
                for day in trend_days
            ) / len(trend_days)

        trend_billing_total = sum(safe_float(r.get("billing_amount", 0)) for r in trend_billing)

        trend_cost = 0.0
        for row in trend_staffing:
            emp = employee_map.get(row.get("employee_id", ""), {})
            designation = emp.get("designation", "")
            per_fte_rate = cost_rate_map.get(designation, 0.0)
            trend_cost += (safe_float(row.get("hours", 0)) / 8.0) * per_fte_rate

        trend_recovery = (trend_billing_total / trend_cost * 100.0) if trend_cost > 0 else 0.0

        monthly_trend.append({
            "month": month_name,
            "ftes": f"{trend_ftes:.1f}",
            "billing": money_fmt(trend_billing_total),
            "recovery": pct_fmt(trend_recovery),
            "nps": "-",
            "ctsu": "-"
        })

    # Billing Summary
    # Split by team_name heuristics because your current schema has no formal business-unit flag
    gs_team_ids = {t["id"] for t in teams if "global sustainability" in (t.get("team_name", "").lower())}
    sr_team_ids = {t["id"] for t in teams if ("s&r" in t.get("team_name", "").lower() or "sustain" in t.get("team_name", "").lower())}

    def month_rows_for_team_ids(team_ids_subset):
        rows = []
        for month_name in available_months:
            y, m = parse_selected_month(month_name)

            m_staff = [
                r for r in staffing_entries
                if (
                    parse_date(r.get("date", "")) and
                    parse_date(r.get("date", "")).year == y and
                    parse_date(r.get("date", "")).month == m and
                    employee_map.get(r.get("employee_id", ""), {}).get("team_id", "") in team_ids_subset
                )
            ]

            m_bill = [
                r for r in billing_entries
                if (
                    parse_date(r.get("date", "")) and
                    parse_date(r.get("date", "")).year == y and
                    parse_date(r.get("date", "")).month == m and
                    project_map.get(r.get("project_id", ""), {}).get("team_id", "") in team_ids_subset
                )
            ]

            m_days = sorted({r.get("date") for r in m_staff if r.get("date")})
            avg_ftes = 0.0
            if m_days:
                avg_ftes = sum(
                    sum(safe_float(r.get("hours", 0)) for r in m_staff if r.get("date") == day) / 8.0
                    for day in m_days
                ) / len(m_days)

            rows.append({
                "month": month_name,
                "gs_headcount": f"{avg_ftes:.1f}",
                "billing": money_fmt(sum(safe_float(r.get("billing_amount", 0)) for r in m_bill))
            })
        return rows

    global_sustainability_rows = month_rows_for_team_ids(gs_team_ids)

    # S&R style table
    sr_rows = []
    for month_name in available_months:
        y, m = parse_selected_month(month_name)

        sr_staff = [
            r for r in staffing_entries
            if (
                parse_date(r.get("date", "")) and
                parse_date(r.get("date", "")).year == y and
                parse_date(r.get("date", "")).month == m and
                employee_map.get(r.get("employee_id", ""), {}).get("team_id", "") in sr_team_ids
            )
        ]

        sr_bill = [
            r for r in billing_entries
            if (
                parse_date(r.get("date", "")) and
                parse_date(r.get("date", "")).year == y and
                parse_date(r.get("date", "")).month == m and
                project_map.get(r.get("project_id", ""), {}).get("team_id", "") in sr_team_ids
            )
        ]

        sr_days = sorted({r.get("date") for r in sr_staff if r.get("date")})
        headcount = 0.0
        if sr_days:
            headcount = sum(
                sum(safe_float(r.get("hours", 0)) for r in sr_staff if r.get("date") == day) / 8.0
                for day in sr_days
            ) / len(sr_days)

        gross_cost_sr = 0.0
        for row in sr_staff:
            emp = employee_map.get(row.get("employee_id", ""), {})
            designation = emp.get("designation", "")
            per_fte_rate = cost_rate_map.get(designation, 0.0)
            gross_cost_sr += (safe_float(row.get("hours", 0)) / 8.0) * per_fte_rate

        total_recovery_sr = sum(safe_float(r.get("billing_amount", 0)) for r in sr_bill)
        recovery_pct_sr = (total_recovery_sr / gross_cost_sr * 100.0) if gross_cost_sr > 0 else 0.0
        client_work = total_recovery_sr
        internal_other = max(gross_cost_sr - total_recovery_sr, 0.0)
        working_days = working_days_in_month(y, m)

        sr_rows.append({
            "month": month_name,
            "headcount": f"{headcount:.1f}",
            "monthly_budget": money_fmt(gross_cost_sr),
            "working_days": working_days,
            "ftes_based_on_budget": f"{headcount:.1f}",
            "excess_ftes": "0.0",
            "cost_of_excess_ftes": money_fmt(0),
            "gross_cost": money_fmt(gross_cost_sr),
            "minimum_recovery_needed": money_fmt(gross_cost_sr),
            "retainer": money_fmt(0),
            "total_recovery": money_fmt(total_recovery_sr),
            "client_work": money_fmt(client_work),
            "internal_other": money_fmt(internal_other),
            "recovery_pct": pct_fmt(recovery_pct_sr),
            "client_recovery_pct": pct_fmt(recovery_pct_sr),
            "other_recovery_pct": pct_fmt(0),
            "net_cost_to_practice": money_fmt(max(gross_cost_sr - total_recovery_sr, 0.0)),
            "budget_variance": money_fmt(total_recovery_sr - gross_cost_sr)
        })

    # Martha summary from all teams
    martha_rows = []
    for month_name in available_months:
        y, m = parse_selected_month(month_name)

        m_staff = [
            r for r in staffing_entries
            if (
                parse_date(r.get("date", "")) and
                parse_date(r.get("date", "")).year == y and
                parse_date(r.get("date", "")).month == m
            )
        ]
        m_bill = [
            r for r in billing_entries
            if (
                parse_date(r.get("date", "")) and
                parse_date(r.get("date", "")).year == y and
                parse_date(r.get("date", "")).month == m
            )
        ]

        m_days = sorted({r.get("date") for r in m_staff if r.get("date")})
        avg_ftes = 0.0
        if m_days:
            avg_ftes = sum(
                sum(safe_float(r.get("hours", 0)) for r in m_staff if r.get("date") == day) / 8.0
                for day in m_days
            ) / len(m_days)

        gross_cost_all = 0.0
        for row in m_staff:
            emp = employee_map.get(row.get("employee_id", ""), {})
            designation = emp.get("designation", "")
            per_fte_rate = cost_rate_map.get(designation, 0.0)
            gross_cost_all += (safe_float(row.get("hours", 0)) / 8.0) * per_fte_rate

        billed_recovery = sum(safe_float(r.get("billing_amount", 0)) for r in m_bill)
        recovery_total_pct = (billed_recovery / gross_cost_all * 100.0) if gross_cost_all > 0 else 0.0

        client_hours = sum(
            safe_float(r.get("hours", 0))
            for r in m_staff
            if project_map.get(r.get("project_id", ""), {}).get("case_type", "").strip().lower() == "client"
        )
        total_hours = sum(safe_float(r.get("hours", 0)) for r in m_staff)
        client_pct = (client_hours / total_hours * 100.0) if total_hours > 0 else 0.0
        other_pct = 100.0 - client_pct if total_hours > 0 else 0.0

        martha_rows.append({
            "month": month_name,
            "ftes": f"{avg_ftes:.1f}",
            "gross_cost": money_fmt(gross_cost_all),
            "recovery_billed_work": money_fmt(billed_recovery),
            "net_cost_to_practice": money_fmt(max(gross_cost_all - billed_recovery, 0.0)),
            "total_recovery_pct": pct_fmt(recovery_total_pct),
            "client_codes_pct": pct_fmt(client_pct),
            "other_practice_ip_pct": pct_fmt(other_pct)
        })

    key_wins = []
    key_challenges = []
    action_items = []

    if total_billing > 0:
        key_wins.append(f"Recovered {money_fmt(total_billing)} in billed work in {selected_month}.")
    if recovery_pct >= 100:
        key_wins.append("Recovery exceeded gross cost for the selected month.")

    if gross_cost > total_billing:
        key_challenges.append(f"Net cost to practice is {money_fmt(gross_cost - total_billing)} for {selected_month}.")
    if not month_billing:
        key_challenges.append("No billing entries found for the selected month.")

    action_items.append("Review teams with low billed recovery against staffed cost.")
    action_items.append("Validate cost rates for all employee designations to improve recovery accuracy.")
    action_items.append("Add live NPS and CTSU source if those KPIs are required on the dashboard.")

    # Case billing tracker
    tracker_rows = []
    for row in month_billing:
        project = project_map.get(row.get("project_id", ""), {})
        team = team_map.get(project.get("team_id", ""), {})
        manager_name = ""
        if team.get("manager_id"):
            manager = user_map.get(team.get("manager_id"), {})
            manager_name = f"{manager.get('first_name', '')} {manager.get('last_name', '')}".strip()

        project_dates = [
            parse_date(s.get("date", ""))
            for s in staffing_entries
            if s.get("project_id") == row.get("project_id", "")
        ]
        project_dates = [d for d in project_dates if d]
        duration_days = 0
        if project_dates:
            duration_days = (max(project_dates) - min(project_dates)).days + 1

        tracker_rows.append({
            "month": selected_month,
            "project_type": project.get("project_type", row.get("project_type", "")),
            "for_util": project.get("type_for_util", ""),
            "team_classification_1": team.get("team_classification_1", ""),
            "team_classification_2": team.get("team_classification_2", ""),
            "project_name": project.get("project_name", row.get("project_name", "")),
            "case_code": row.get("case_code", ""),
            "stakeholder": project.get("requestor", ""),
            "region": project.get("office", "") or project.get("case_delivery_primary_location", ""),
            "duration_days": duration_days,
            "billed_amount": money_fmt(safe_float(row.get("billing_amount", 0))),
            "bcn_manager": manager_name
        })

    metrics = {
        "scorecard": {
            "total_ftes": f"{total_ftes:.1f}",
            "fte_trend": fte_trend,
            "total_billing": money_fmt(total_billing),
            "billing_trend": billing_trend,
            "recovery": pct_fmt(recovery_pct),
            "recovery_target": "100%",
            "gender_ratio": gender_ratio,
            "female_share": female_share,
            "nps": nps_value,
            "nps_trend": nps_trend,
            "ctsu": ctsu_value,
            "ctsu_trend": ctsu_trend,
            "major_clients": major_clients,
            "notes": notes,
            "monthly_trend": monthly_trend
        },
        "billing_summary": {
            "global_sustainability": {
                "approved_headcount": f"{len([e for e in employees if e.get('team_id') in gs_team_ids])}",
                "approved_annual_budget": money_fmt(sum(cost_rate_map.get(e.get("designation", ""), 0.0) * 12 for e in employees if e.get("team_id") in gs_team_ids)),
                "rows": global_sustainability_rows
            },
            "sr": {
                "approved_headcount": f"{len([e for e in employees if e.get('team_id') in sr_team_ids])}",
                "approved_annual_budget": money_fmt(sum(cost_rate_map.get(e.get("designation", ""), 0.0) * 12 for e in employees if e.get("team_id") in sr_team_ids)),
                "rows": sr_rows
            }
        },
        "martha_summary": {
            "rows": martha_rows,
            "key_wins": key_wins,
            "key_challenges": key_challenges,
            "action_items": action_items
        },
        "case_billing_tracker": {
            "rows": tracker_rows
        }
    }

    return metrics

@app.route("/director")
@app.route("/director/home")
@login_required
@roles_required("DIRECTOR")
def director_home():
    active_view = request.args.get("view", "scorecard")
    months = get_available_reporting_months()
    selected_month = request.args.get("month") or (months[-1] if months else datetime.now().strftime("%b %Y"))
    metrics = build_director_metrics(selected_month)

    return render_template(
        "director_home.html",
        metrics=metrics,
        selected_month=selected_month,
        months=months,
        active_view=active_view
    )


@app.route("/manager")
@app.route("/manager/home")
@login_required
@roles_required("MANAGER")
def manager_home():
    user = session["user"]

    teams = [t for t in get_teams() if t.get("manager_id") == user["id"]]
    billing_entries = get_billing_entries()
    staffing_entries = get_staffing_entries()
    employees = get_employees()
    projects = get_projects()

    employee_map = {e["id"]: e for e in employees}
    project_map = {p["id"]: p for p in projects}
    team_ids = {t["id"] for t in teams}

    today = datetime.now().date()
    current_year = today.year
    current_month = today.month

    manager_staffing = [s for s in staffing_entries if s.get("manager_id") == user["id"]]
    manager_billing = [b for b in billing_entries if b.get("manager_id") == user["id"]]

    # KPI calculations
    ytd_billing_value = 0.0
    for b in manager_billing:
        try:
            entry_date = datetime.strptime(b.get("date", ""), "%Y-%m-%d").date()
            if entry_date.year == current_year:
                ytd_billing_value += float(b.get("billing_amount", 0) or 0)
        except Exception:
            pass

    monthly_billing_value = 0.0
    for b in manager_billing:
        try:
            entry_date = datetime.strptime(b.get("date", ""), "%Y-%m-%d").date()
            if entry_date.year == current_year and entry_date.month == current_month:
                monthly_billing_value += float(b.get("billing_amount", 0) or 0)
        except Exception:
            pass

    monthly_staffing = []
    for s in manager_staffing:
        try:
            entry_date = datetime.strptime(s.get("date", ""), "%Y-%m-%d").date()
            if entry_date.year == current_year and entry_date.month == current_month:
                monthly_staffing.append(s)
        except Exception:
            pass

    working_days_with_entries = sorted({s.get("date") for s in monthly_staffing if s.get("date")})
    avg_ftes_value = 0.0
    if working_days_with_entries:
        daily_fte_totals = []
        for day in working_days_with_entries:
            day_hours = sum(float(s.get("hours", 0) or 0) for s in monthly_staffing if s.get("date") == day)
            daily_fte_totals.append(day_hours / 8.0)
        avg_ftes_value = sum(daily_fte_totals) / len(daily_fte_totals)

    manager_employee_ids = {
        e["id"] for e in employees
        if e.get("team_id") in team_ids
    }

    staffed_hours = sum(float(s.get("hours", 0) or 0) for s in monthly_staffing)

    month_start_for_util = today.replace(day=1)
    days_elapsed = [month_start_for_util + timedelta(days=i) for i in range((today - month_start_for_util).days + 1)]
    weekdays_elapsed = [d for d in days_elapsed if d.weekday() < 5]
    available_hours = len(manager_employee_ids) * len(weekdays_elapsed) * 8

    utilization_pct = 0.0
    if available_hours > 0:
        utilization_pct = (staffed_hours / available_hours) * 100

    def money_k(v):
        return f"${round(v/1000):.0f}K" if v >= 1000 else f"${v:,.0f}"

    kpis = [
        {"label": "Total YTD Manager Billing", "value": money_k(ytd_billing_value)},
        {"label": "Monthly Manager Billing", "value": money_k(monthly_billing_value)},
        {"label": "Avg FTEs", "value": f"{avg_ftes_value:.1f}"},
        {"label": "Utilization", "value": f"{utilization_pct:.0f}%"},
        {"label": "YTD NPS", "value": "-"},
        {"label": "YTD CTSU", "value": "-"},
    ]

    # Shared view controls
    active_view = request.args.get("view", "weekly").strip().lower()
    if active_view not in ["weekly", "monthly"]:
        active_view = "weekly"

    anchor_str = request.args.get("anchor", "").strip()
    try:
        anchor_date = datetime.strptime(anchor_str, "%Y-%m-%d").date() if anchor_str else today
    except ValueError:
        anchor_date = today

    if active_view == "weekly":
        period_start = anchor_date - timedelta(days=anchor_date.weekday())
        visible_dates = [period_start + timedelta(days=i) for i in range(5)]
        prev_anchor = period_start - timedelta(days=7)
        next_anchor = period_start + timedelta(days=7)
        period_label = f"{visible_dates[0].strftime('%d %b %Y')} - {visible_dates[-1].strftime('%d %b %Y')}"
    else:
        period_start = anchor_date.replace(day=1)
        if period_start.month == 12:
            next_month_start = period_start.replace(year=period_start.year + 1, month=1, day=1)
        else:
            next_month_start = period_start.replace(month=period_start.month + 1, day=1)

        period_end = next_month_start - timedelta(days=1)
        visible_dates = []
        cursor = period_start
        while cursor <= period_end:
            if cursor.weekday() < 5:
                visible_dates.append(cursor)
            cursor += timedelta(days=1)

        prev_anchor = (period_start - timedelta(days=1)).replace(day=1)
        next_anchor = next_month_start
        period_label = period_start.strftime("%B %Y")

    visible_date_strings = [d.strftime("%Y-%m-%d") for d in visible_dates]
    week_date_labels = [d.strftime("%d %b") for d in visible_dates]
    week_day_labels = [d.strftime("%a").upper() for d in visible_dates]

    manager_entries_in_range = [
        s for s in manager_staffing
        if s.get("date") in visible_date_strings
    ]

    # Employees manager has ever worked with
    all_employee_ids_worked_with = []
    seen_emp_ids = set()
    for s in manager_staffing:
        emp_id = s.get("employee_id")
        if emp_id and emp_id not in seen_emp_ids:
            seen_emp_ids.add(emp_id)
            all_employee_ids_worked_with.append(emp_id)

    # Include employees from manager teams too
    for e in employees:
        if e.get("team_id") in team_ids and e["id"] not in seen_emp_ids:
            seen_emp_ids.add(e["id"])
            all_employee_ids_worked_with.append(e["id"])

    active_employee_ids = []
    inactive_employee_ids = []
    active_seen = set()

    for s in manager_entries_in_range:
        emp_id = s.get("employee_id")
        if emp_id and emp_id in seen_emp_ids and emp_id not in active_seen:
            active_seen.add(emp_id)
            active_employee_ids.append(emp_id)

    for emp_id in all_employee_ids_worked_with:
        if emp_id not in active_seen:
            inactive_employee_ids.append(emp_id)

    ordered_employee_ids = active_employee_ids + inactive_employee_ids

    # Staffing matrix table
    staffing_rows = []
    for emp_id in ordered_employee_ids:
        emp = employee_map.get(emp_id)
        if not emp:
            continue

        row_cells = []
        has_any_value = False

        for date_str in visible_date_strings:
            matching = [
                s for s in manager_entries_in_range
                if s.get("employee_id") == emp_id and s.get("date") == date_str
            ]

            if not matching:
                row_cells.append("")
                continue

            cell_values = []
            for s in matching:
                if s.get("project_id") and s.get("project_id") in project_map:
                    label = project_map[s["project_id"]].get("project_name", "")
                elif s.get("project_name"):
                    label = s.get("project_name", "")
                else:
                    label = s.get("staffing_type", "")

                hours = float(s.get("hours", 0) or 0)
                display = f"{label} ({hours:g}h)" if label else f"{s.get('staffing_type', '')} ({hours:g}h)"

                if display not in cell_values:
                    cell_values.append(display)

            cell_text = ", ".join(cell_values)
            if cell_text:
                has_any_value = True
            row_cells.append(cell_text)

        staffing_rows.append({
            "employee_id": emp_id,
            "name": emp.get("name", ""),
            "designation": emp.get("designation", ""),
            "has_activity": has_any_value,
            "week": row_cells
        })

    # Gantt with multiple bar segments per contiguous date run
    gantt_rows = []

    for team in teams:
        team_employee_ids = {e["id"] for e in employees if e.get("team_id") == team["id"]}

        team_entries = [
            s for s in manager_entries_in_range
            if s.get("employee_id") in team_employee_ids
        ]

        grouped = {}
        for s in team_entries:
            if s.get("project_id") and s.get("project_id") in project_map:
                label = project_map[s["project_id"]].get("project_name", "")
            elif s.get("project_name"):
                label = s.get("project_name", "")
            else:
                label = s.get("staffing_type", "")

            if not label:
                continue

            grouped.setdefault(label, set()).add(s.get("date"))

        if not grouped:
            gantt_rows.append({
                "team_name": team.get("team_name", ""),
                "project_name": "No staffing entered",
                "segments": [],
                "is_empty": True
            })
            continue

        for project_name, date_set in grouped.items():
            sorted_indexes = sorted(
                visible_date_strings.index(d)
                for d in date_set
                if d in visible_date_strings
            )

            segments = []
            if sorted_indexes:
                start_idx = sorted_indexes[0]
                prev_idx = sorted_indexes[0]

                for idx in sorted_indexes[1:]:
                    if idx == prev_idx + 1:
                        prev_idx = idx
                    else:
                        segments.append({
                            "style": f"grid-column: {start_idx + 1} / span {(prev_idx - start_idx + 1)};"
                        })
                        start_idx = idx
                        prev_idx = idx

                segments.append({
                    "style": f"grid-column: {start_idx + 1} / span {(prev_idx - start_idx + 1)};"
                })

            gantt_rows.append({
                "team_name": team.get("team_name", ""),
                "project_name": project_name,
                "segments": segments,
                "is_empty": False
            })

    return render_template(
        "manager_home.html",
        kpis=kpis,
        teams=teams,
        gantt_rows=gantt_rows,
        staffing_rows=staffing_rows,
        week_day_labels=week_day_labels,
        week_date_labels=week_date_labels,
        visible_dates=visible_date_strings,
        period_label=period_label,
        active_view=active_view,
        prev_anchor=prev_anchor.strftime("%Y-%m-%d"),
        next_anchor=next_anchor.strftime("%Y-%m-%d"),
        current_anchor=anchor_date.strftime("%Y-%m-%d"),
        greeting=get_greeting(),
        employees=employees,
        projects=projects,
        reports=get_reports(),
        users=get_users(),
        all_teams=get_teams()
    )

@app.route("/manager/projects")
@login_required
@roles_required("MANAGER")
def manager_projects():
    user = session["user"]
    rows = [p for p in get_projects() if p.get("created_by") == user["id"]]
    return render_template("manager_projects.html", rows=rows, teams=get_teams(), users=get_users())

@app.route("/manager/projects/edit/<item_id>", methods=["GET", "POST"])
@login_required
@roles_required("MANAGER")
def manager_projects_edit(item_id):
    rows = get_projects()
    item = find_by_id(rows, item_id)

    if not item:
        flash("Project not found.", "error")
        return redirect(url_for("manager_projects"))

    if not can_edit_project(session.get("user"), item):
        flash("You do not have access to edit this project.", "error")
        return redirect(url_for("manager_projects"))

    if request.method == "POST":
        for key in FULL_PROJECT_FIELDS:
            item[key] = request.form.get(key, "").strip()

        save_projects(rows)
        flash("Project updated.", "success")
        return redirect(url_for("manager_projects"))

    return render_template(
        "manager_project_edit.html",
        item=item,
        teams=get_teams(),
        users=get_users()
    )

@app.route("/manager/projects/delete/<item_id>")
@login_required
@roles_required("MANAGER")
def manager_projects_delete(item_id):
    rows = get_projects()
    item = find_by_id(rows, item_id)

    if not item:
        flash("Project not found.", "error")
        return redirect(url_for("manager_projects"))

    if not can_edit_project(session.get("user"), item):
        flash("You do not have access to delete this project.", "error")
        return redirect(url_for("manager_projects"))

    save_projects([r for r in rows if r.get("id") != item_id])
    flash("Project deleted.", "success")
    return redirect(url_for("manager_projects"))

@app.route("/api/staffing/prefill")
@login_required
@roles_required("MANAGER")
def api_staffing_prefill():
    manager_id = session["user"]["id"]

    requested_date = request.args.get("date", "").strip()
    load_date = request.args.get("load_date", "").strip()

    # Opening modal should use current date by default.
    # Custom "Load From Date" can still override via load_date.
    target_date = load_date or requested_date or datetime.now().strftime("%Y-%m-%d")

    staffing = get_staffing_entries()
    billing = get_billing_entries()
    employees = {e["id"]: e for e in get_employees()}
    projects = {p["id"]: p for p in get_projects()}

    staffing_rows = []
    for item in staffing:
        if item.get("manager_id") == manager_id and item.get("date") == target_date:
            project = projects.get(item.get("project_id", ""), {})
            staffing_rows.append({
                "employee_id": item.get("employee_id", ""),
                "employee_name": employees.get(item.get("employee_id", ""), {}).get("name", ""),
                "staffing_type": item.get("staffing_type", ""),
                "project_id": item.get("project_id", ""),
                "project_name": project.get("project_name", item.get("project_name", "")),
                "case_code": item.get("case_code", ""),
                "hours": float(item.get("hours", 0) or 0),
                "comments": item.get("comments", "")
            })

    # IMPORTANT:
    # Return saved billing rows from database for that same date,
    # not re-derived rows, so user sees latest saved edits.
    billing_rows = []
    for item in billing:
        if item.get("manager_id") == manager_id and item.get("date") == target_date:
            billing_rows.append({
                "project_id": item.get("project_id", ""),
                "project_name": item.get("project_name", ""),
                "project_type": item.get("project_type", ""),
                "case_code": item.get("case_code", ""),
                "billable_ftes": float(item.get("billable_ftes", 0) or 0),
                "billing_amount": float(item.get("billing_amount", 0) or 0),
                "comments": item.get("comments", "")
            })

    # If staffing exists but billing does not yet exist for that date,
    # derive once as fallback.
    if staffing_rows and not billing_rows:
        billing_rows = derive_billing_rows(staffing_rows)

    return jsonify({
        "source_date": target_date,
        "rows": staffing_rows,
        "billing_rows": billing_rows
    })

@app.route("/api/staffing/save", methods=["POST"])
@login_required
@roles_required("MANAGER")
def api_staffing_save():
    payload = request.get_json(force=True)
    date = (payload.get("date") or "").strip()
    rows = payload.get("rows", [])
    billing_rows = payload.get("billing_rows", [])
    manager_id = session["user"]["id"]

    if not date:
        return jsonify({"ok": False, "message": "Date is required."}), 400

    # Replace staffing entries for this manager/date
    staffing = [
        r for r in get_staffing_entries()
        if not (r.get("manager_id") == manager_id and r.get("date") == date)
    ]

    for row in rows:
        staffing.append({
            "id": next_id("SE", staffing),
            "date": date,
            "manager_id": manager_id,
            "employee_id": row.get("employee_id", ""),
            "staffing_type": row.get("staffing_type", ""),
            "project_id": row.get("project_id", ""),
            "project_name": row.get("project_name", ""),
            "case_code": row.get("case_code", ""),
            "hours": float(row.get("hours", 0) or 0),
            "comments": row.get("comments", "")
        })

    save_staffing_entries(staffing)

    # Replace billing entries for this manager/date
    billing = [
        r for r in get_billing_entries()
        if not (r.get("manager_id") == manager_id and r.get("date") == date)
    ]

    for row in billing_rows:
        billing.append({
            "id": next_id("BE", billing),
            "date": date,
            "manager_id": manager_id,
            "project_id": row.get("project_id", ""),
            "project_name": row.get("project_name", ""),
            "project_type": row.get("project_type", ""),
            "case_code": row.get("case_code", ""),
            "billable_ftes": float(row.get("billable_ftes", 0) or 0),
            "billing_amount": float(row.get("billing_amount", 0) or 0),
            "comments": row.get("comments", "")
        })

    save_billing_entries(billing)

    return jsonify({"ok": True, "message": "Staffing and billing saved."})

@app.route("/api/staffing/derive-billing", methods=["POST"])
@login_required
@roles_required("MANAGER")
def api_staffing_derive_billing():
    payload = request.get_json(force=True); return jsonify({"billing_rows": derive_billing_rows(payload.get("rows", []))})

@app.route("/api/projects/create", methods=["POST"])
@login_required
@roles_required("MANAGER", "ADMIN")
def api_projects_create():
    rows = get_projects()
    item = {"id": next_id("P", rows)}

    for key in FULL_PROJECT_FIELDS:
        item[key] = request.form.get(key, "").strip()

    item["created_by"] = session["user"]["id"]

    rows.append(item)
    save_projects(rows)
    return jsonify({"ok": True, "project": item})

@app.route("/api/reports/insync/generate", methods=["POST"])
@login_required
def api_insync_generate():
    """Generate an Insync report for a given month."""
    payload = request.get_json(force=True)
    month = payload.get("month", "")
    
    if not month:
        return jsonify({"ok": False, "message": "Month is required"})
    
    # Check if report already exists for this month
    reports = get_reports()
    existing_report = next((r for r in reports if r.get("type") == "monthly_insync" and r.get("month") == month), None)
    
    try:
        # Generate the report file and upload to blob storage
        blob_pathname = generate_insync_report_file(month)
        
        if existing_report:
            # Replace the existing report
            report_id = existing_report["id"]
            # Update existing record (blob storage allows overwrite)
            existing_report["blob_pathname"] = blob_pathname
            existing_report["generated_on"] = datetime.now().isoformat()
            existing_report["file_name"] = f"insync_{month}.xlsx"
        else:
            # Create new report record
            report_id = next_id("RPT", reports)
            reports.append({
                "id": report_id,
                "type": "monthly_insync",
                "month": month,
                "generated_on": datetime.now().isoformat(),
                "file_name": f"insync_{month}.xlsx",
                "blob_pathname": blob_pathname
            })
        
        save_reports(reports)
        return jsonify({"ok": True, "message": "Report generated successfully", "report_id": report_id})
    
    except Exception as e:
        return jsonify({"ok": False, "message": f"Error generating report: {str(e)}"})

@app.route("/api/reports/insync/list")
@login_required
def api_insync_list():
    """Get all Insync reports sorted reverse chronologically by month."""
    reports = get_reports()
    insync_reports = [r for r in reports if r.get("type") == "monthly_insync"]
    
    # Sort reverse chronologically by month (so newer months first)
    insync_reports.sort(key=lambda x: x.get("month", ""), reverse=True)
    
    return jsonify({"ok": True, "reports": insync_reports})

@app.route("/api/reports/insync/download/<item_id>")
@login_required
def api_insync_download(item_id):
    """Download an Insync report file."""
    reports = get_reports()
    report = next((r for r in reports if r.get("id") == item_id and r.get("type") == "monthly_insync"), None)
    
    if not report:
        flash("Report not found.", "error")
        return redirect(url_for("route_by_role"))
    
    blob_pathname = report.get("blob_pathname", "")
    
    if not blob_pathname:
        flash("Report file path not found.", "error")
        return redirect(request.referrer or url_for("route_by_role"))
    
    # Download file from blob storage
    file_content = download_blob_file(blob_pathname)
    
    if file_content:
        # Send file from memory
        return send_file(
            BytesIO(file_content),
            as_attachment=True,
            download_name=report.get("file_name") or "report.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    flash("Report file not found in storage.", "error")
    return redirect(request.referrer or url_for("route_by_role"))

def generate_insync_report_file(month):
    """
    Generate an Insync report Excel file for the given month based on Insync.xlsx template.
    
    Args:
        month: Month string in format "YYYY-MM"
    
    Returns:
        The stored filename relative to UPLOAD_DIR
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        raise ImportError("openpyxl is required for generating Insync reports. Please install it.")
    
    # Define column headers matching Insync.xlsx structure
    headers = [
        "Cluster", "CoE", "BU (Dropdown)", "Team Code (Dropdown)", 
        "CoE Lead + Director (Dropdown)", "S/TM Manager (Dropdown)", 
        "Team Name for CTSU", "CTSU Ombudsperson", "Year", "Month", "Day", "Type", "Date",
        "Project Name (Dropdown)", "Billing Case code", "Client Case Code",
        "Work Description (Be specific and explanatory about the work tasks)",
        "Product (Dropdown)", "Requestor", "NPS Contact", 
        "Case Status (Dropdown)", "NPS Status (Dropdown)",
        "Case Manager against whom NPS will be reported", "BCN Case Execution Location",
        "Billed to end client as Fees/ Expense", "Case type", "Office",
        "Case Manager/ Principal", "Client name", "Case Partner",
        "Industry (Dropdown)", "Capability (Dropdown)", "Unique_Code",
        "Billed Team Size", "Actual Billing", "Potential Billing"
    ]
    
    # Get manager's team and employees
    user = session.get("user")
    if not user:
        raise ValueError("No user session found")
    
    teams = [t for t in get_teams() if t.get("manager_id") == user["id"]]
    team_ids = {t["id"] for t in teams}
    employees = [e for e in get_employees() if e.get("team_id") in team_ids]
    
    # Add employee columns to headers
    employee_headers = [f"{e.get('name', 'Unknown')} ({e.get('id', '')})" for e in employees]
    all_headers = headers + employee_headers
    
    # Get staffing entries for this month
    year, month_num = month.split("-")
    staffing_entries = get_staffing_entries()
    manager_entries = [
        s for s in staffing_entries 
        if s.get("manager_id") == user["id"] and s.get("date", "").startswith(month)
    ]
    
    # Group entries by date and project
    from collections import defaultdict
    entries_by_date_project = defaultdict(lambda: defaultdict(list))
    
    for entry in manager_entries:
        date = entry.get("date", "")
        project_name = entry.get("project_name", "")
        entries_by_date_project[date][project_name].append(entry)
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Insync {month}"
    
    # Write headers
    header_fill = PatternFill(start_color="1f2328", end_color="1f2328", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    
    for col_idx, header in enumerate(all_headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        # Set column widths
        if col_idx <= 13:
            ws.column_dimensions[cell.column_letter].width = 12
        elif col_idx <= 36:
            ws.column_dimensions[cell.column_letter].width = 15
        else:
            ws.column_dimensions[cell.column_letter].width = 18
    
    # Write data rows
    row_idx = 2
    projects = get_projects()
    project_map = {p["id"]: p for p in projects}
    
    for date in sorted(entries_by_date_project.keys()):
        for project_name, entries in entries_by_date_project[date].items():
            # Get project details
            project = None
            for entry in entries:
                if entry.get("project_id") and entry["project_id"] in project_map:
                    project = project_map[entry["project_id"]]
                    break
            
            # Parse date
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                year_val = date_obj.year
                month_val = date_obj.month
                day_val = date_obj.day
                weekday = date_obj.weekday()
                day_type = "Workday" if weekday < 5 else "Weekend"
            except:
                year_val, month_val, day_val, day_type = year, month_num, "", "Workday"
            
            # Get team info
            team = teams[0] if teams else {}
            
            # Write project metadata columns (1-36)
            ws.cell(row=row_idx, column=1).value = "Data & Tech"  # Cluster
            ws.cell(row=row_idx, column=2).value = "Sustainability"  # CoE
            ws.cell(row=row_idx, column=3).value = team.get("team_name", "")  # BU
            ws.cell(row=row_idx, column=4).value = team.get("team_name", "")  # Team Code
            ws.cell(row=row_idx, column=5).value = ""  # CoE Lead + Director
            ws.cell(row=row_idx, column=6).value = f"{user.get('first_name', '')} {user.get('last_name', '')}"  # Manager
            ws.cell(row=row_idx, column=7).value = team.get("team_name", "")  # Team Name for CTSU
            ws.cell(row=row_idx, column=8).value = ""  # CTSU Ombudsperson
            ws.cell(row=row_idx, column=9).value = year_val  # Year
            ws.cell(row=row_idx, column=10).value = month_val  # Month
            ws.cell(row=row_idx, column=11).value = day_val  # Day
            ws.cell(row=row_idx, column=12).value = day_type  # Type
            ws.cell(row=row_idx, column=13).value = date  # Date
            ws.cell(row=row_idx, column=14).value = project_name  # Project Name
            ws.cell(row=row_idx, column=15).value = project.get("billing_case_code", "") if project else ""  # Billing Case code
            ws.cell(row=row_idx, column=16).value = project.get("client_case_code", "") if project else ""  # Client Case Code
            ws.cell(row=row_idx, column=17).value = project.get("work_description", "") if project else ""  # Work Description
            ws.cell(row=row_idx, column=18).value = project.get("product", "") if project else ""  # Product
            ws.cell(row=row_idx, column=19).value = project.get("requestor", "") if project else ""  # Requestor
            ws.cell(row=row_idx, column=20).value = project.get("nps_contact", "") if project else ""  # NPS Contact
            ws.cell(row=row_idx, column=21).value = project.get("case_status", "") if project else ""  # Case Status
            ws.cell(row=row_idx, column=22).value = project.get("nps_status", "") if project else ""  # NPS Status
            ws.cell(row=row_idx, column=23).value = project.get("case_manager_for_nps", "") if project else ""  # Case Manager
            ws.cell(row=row_idx, column=24).value = project.get("bcn_case_execution_location", "") if project else ""  # BCN Location
            ws.cell(row=row_idx, column=25).value = project.get("billed_to_end_client", "") if project else ""  # Billed to end client
            ws.cell(row=row_idx, column=26).value = project.get("case_type", "") if project else ""  # Case type
            ws.cell(row=row_idx, column=27).value = project.get("office", "") if project else ""  # Office
            ws.cell(row=row_idx, column=28).value = project.get("case_manager_principal", "") if project else ""  # Case Manager/Principal
            ws.cell(row=row_idx, column=29).value = project.get("client_name", "") if project else ""  # Client name
            ws.cell(row=row_idx, column=30).value = project.get("case_partner", "") if project else ""  # Case Partner
            ws.cell(row=row_idx, column=31).value = project.get("industry", "") if project else ""  # Industry
            ws.cell(row=row_idx, column=32).value = project.get("capability", "") if project else ""  # Capability
            ws.cell(row=row_idx, column=33).value = ""  # Unique_Code
            
            # Calculate team size and billing
            team_size = len(set(e.get("employee_id") for e in entries if e.get("employee_id")))
            total_hours = sum(float(e.get("hours", 0) or 0) for e in entries)
            
            ws.cell(row=row_idx, column=34).value = team_size  # Billed Team Size
            ws.cell(row=row_idx, column=35).value = total_hours * 10  # Actual Billing (placeholder calculation)
            ws.cell(row=row_idx, column=36).value = ""  # Potential Billing
            
            # Write employee columns (37+)
            employee_map = {e["id"]: e for e in employees}
            for emp_idx, emp in enumerate(employees):
                col_idx = 37 + emp_idx
                # Find this employee's entry for this date/project
                emp_entry = next((e for e in entries if e.get("employee_id") == emp["id"]), None)
                
                if emp_entry:
                    hours = float(emp_entry.get("hours", 0) or 0)
                    staffing_type = emp_entry.get("staffing_type", "")
                    if hours > 0:
                        ws.cell(row=row_idx, column=col_idx).value = f"Regular Hours ({hours}h)"
                    elif staffing_type:
                        ws.cell(row=row_idx, column=col_idx).value = staffing_type
                    else:
                        ws.cell(row=row_idx, column=col_idx).value = ""
                else:
                    ws.cell(row=row_idx, column=col_idx).value = ""
            
            row_idx += 1
    
    # If no data, add a placeholder row
    if row_idx == 2:
        ws.cell(row=2, column=1).value = "No data for this month"
    
    # Freeze top row
    ws.freeze_panes = "A2"
    
    # Save the workbook to BytesIO (memory), then upload to blob storage
    filename = f"insync_{month}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    # Try simpler pathname without directory structure
    blob_pathname = f"report-{filename}"
    
    # Save to memory buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    file_content = buffer.read()
    
    # Debug: Log file size
    import sys
    print(f"Generated Excel file: {len(file_content)} bytes", file=sys.stderr)
    print(f"Blob pathname: {blob_pathname}", file=sys.stderr)
    
    # Upload to blob storage with a simpler content-type
    upload_file_to_blob(
        file_content,
        blob_pathname,
        content_type="application/octet-stream"
    )
    
    return blob_pathname

if __name__ == "__main__":
    app.run(debug=True)
