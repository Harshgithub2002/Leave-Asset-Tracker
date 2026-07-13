from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
import json
import os
from datetime import datetime, date, timedelta

app = Flask(__name__)

app.secret_key = "secretkey123"

USER_FILE = "users.json"
REQUEST_FILE = "requests.json"

if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump([], f)

if not os.path.exists(REQUEST_FILE):
    with open(REQUEST_FILE, "w") as f:
        json.dump([], f)


# ==============================
# PASSWORD VALIDATION
# ==============================

def is_valid_password(password):
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,12}$"

    return re.match(pattern, password)

def load_users():
    with open(USER_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)


def load_requests():
    try:
        with open(REQUEST_FILE, "r") as f:

            content = f.read().strip()

            if not content:
                return []

            return json.loads(content)

    except:
        return []


def save_requests(data):
    with open(REQUEST_FILE, "w") as f:
        json.dump(data, f, indent=4)


@app.route("/")
def home():
    return redirect(url_for("login"))


# ==============================
# APPLY REQUEST
# ==============================

@app.route("/apply_request", methods=["POST"])
def apply_request():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    username = session["username"]
    users = load_users()

    current_user = next(
        (u for u in users if u["username"] == username),
        None
    )

    if not current_user:
        return redirect(url_for("user_dashboard"))

    required_fields = [
        "employee_id",
        "desk_number",
        "pc_ptag",
        "monitor_ptag",
        "skillset",
        "certification"
    ]

    for field in required_fields:
        if not str(current_user.get(field, "")).strip():
            flash(f"Missing Profile Field: {field}")
            return redirect(url_for("user_dashboard"))

    team = session.get("team")
    users = load_users()
    current_user = next(
        (u for u in users if u["username"] == username),
        None
    )
    required_fields = [
        "employee_id",
        "desk_number",
        "pc_ptag",
        "monitor_ptag",
        "skillset",
        "experience",
        "certification",
        "employee_photo",
        "resume"
    ]
    for field in required_fields:
        if not current_user.get(field):
            flash(
                "Please complete your Profile before applying Leave/WFH."
            )
            return redirect(url_for("user_dashboard"))
    request_type = request.form.get("request_type")

    leave_type = request.form.get("leave_type")

    from_date = request.form.get("from_date")

    to_date = request.form.get("to_date")

    reason = request.form.get("reason")
    all_requests = load_requests()

    if not from_date or not to_date:
        flash("Please select both From Date and To Date!")

        return redirect(url_for("user_dashboard"))

    from_date_obj = datetime.strptime(
        from_date,
        "%Y-%m-%d"
    ).date()

    to_date_obj = datetime.strptime(
        to_date,
        "%Y-%m-%d"
    ).date()

    today = datetime.now().date()

    if to_date_obj < from_date_obj:
        flash("To Date cannot be earlier than From Date!")

        return redirect(url_for("user_dashboard"))

    current_year = today.year

    current_month = today.month

    previous_month_last_date = date(
        current_year,
        current_month,
        1
    ) - timedelta(days=1)

    previous_month_last_week = (
            previous_month_last_date - timedelta(days=6)
    )

    if current_month == 12:

        next_month_last_date = date(
            current_year + 1,
            2,
            1
        ) - timedelta(days=1)

    else:

        if current_month + 2 > 12:

            next_month_last_date = date(
                current_year + 1,
                1,
                1
            ) - timedelta(days=1)

        else:

            next_month_last_date = date(
                current_year,
                current_month + 2,
                1
            ) - timedelta(days=1)

    if (
            from_date_obj < previous_month_last_week
            or
            to_date_obj > next_month_last_date
    ):
        flash(
            "Leave can be applied only from last month last week to next month!"
        )

        return redirect(url_for("user_dashboard"))

    leave_days = 0

    current = from_date_obj

    while current <= to_date_obj:

        if current.weekday() not in [5, 6]:
            leave_days += 1

        current += timedelta(days=1)

    long_leave = leave_days >= 3

    status = "Pending"

    notification = ""

    if request_type == "WFH":

        auto_approved_days = []

        manager_approval_days = []

        current_day = from_date_obj

        while current_day <= to_date_obj:

            if current_day.weekday() not in [5, 6]:

                if current_day.weekday() in [1, 4]:

                    auto_approved_days.append(
                        current_day.strftime("%d-%m-%Y")
                    )

                else:

                    manager_approval_days.append(
                        current_day.strftime("%d-%m-%Y")
                    )

            current_day += timedelta(days=1)

        # Tuesday & Friday only
        if len(auto_approved_days) > 0 and len(manager_approval_days) == 0:

            status = "Accepted"

            notification = (
                    "WFH Auto Approved (" +
                    ", ".join(auto_approved_days) +
                    ")"
            )

        # Monday / Wednesday / Thursday only
        elif len(manager_approval_days) > 0 and len(auto_approved_days) == 0:

            status = "Pending"

            notification = (
                    "Manager Approval Required (" +
                    ", ".join(manager_approval_days) +
                    ")"
            )

        # Mixed request (Monday + Tuesday, Wednesday + Friday etc.)
        elif len(manager_approval_days) > 0 and len(auto_approved_days) > 0:

            status = "Pending"

            notification = (
                    "Auto Approved: " +
                    ", ".join(auto_approved_days) +
                    " | Manager Approval Required: " +
                    ", ".join(manager_approval_days)
            )

    # =====================================
    # WEEKLY OFFICE / WFH VALIDATION
    # =====================================

    week_start = from_date_obj - timedelta(days=from_date_obj.weekday())
    week_end = week_start + timedelta(days=4)  # Monday-Friday

    office_days = 5
    wfh_days = 0
    leave_days_week = 0

    # Existing requests of same user
    for req in all_requests:

        if req["username"] != username:
            continue

        # Ignore rejected requests
        if req.get("status") == "Rejected":
            continue

        req_from = datetime.strptime(
            req["from_date"],
            "%Y-%m-%d"
        ).date()

        req_to = datetime.strptime(
            req["to_date"],
            "%Y-%m-%d"
        ).date()

        current_day = req_from

        while current_day <= req_to:

            if (
                    week_start <= current_day <= week_end and
                    current_day.weekday() < 5
            ):

                if req["request_type"] == "WFH":
                    wfh_days += 1

                elif req["request_type"] == "Leave":
                    leave_days_week += 1

            current_day += timedelta(days=1)

    # New request counts
    current_day = from_date_obj

    while current_day <= to_date_obj:

        if (
                week_start <= current_day <= week_end and
                current_day.weekday() < 5
        ):

            if request_type == "WFH":
                wfh_days += 1

            elif request_type == "Leave":
                leave_days_week += 1

        current_day += timedelta(days=1)

    # ==========================================
    # WEEKLY ATTENDANCE POLICY VALIDATION
    # ==========================================

    office_days = 5 - wfh_days - leave_days_week

    # ==========================================
    # 5 DAYS LEAVE
    # ==========================================

    if leave_days_week == 5 and wfh_days == 0:
        status = "Pending"

        notification = "5 Days Leave - Admin Approval Required"

    # --------------------------------------------------
    # Rule 1
    # Office = 3
    # WFH = 2
    # Leave = 0
    # APPROVED
    # --------------------------------------------------

    if office_days == 3 and wfh_days == 2 and leave_days_week == 0:

        if request_type == "WFH":
            if from_date_obj.weekday() in [1, 4]:
                status = "Accepted"
                notification = "WFH Auto Approved"
            else:
                status = "Pending"
                notification = "Manager Approval Required"

    # --------------------------------------------------
    # Rule 2
    # Office = 2
    # WFH = 2
    # Leave = 1
    # APPROVED
    # --------------------------------------------------

    elif office_days == 2 and wfh_days == 2 and leave_days_week == 1:

        if request_type == "WFH":
            if from_date_obj.weekday() in [1, 4]:
                status = "Accepted"
                notification = "WFH Auto Approved"
            else:
                status = "Pending"
                notification = "Manager Approval Required"

    # --------------------------------------------------
    # Rule 3
    # Office =2
    # WFH =3
    # Leave =0
    # REJECT
    # --------------------------------------------------

    elif office_days == 2 and wfh_days == 3 and leave_days_week == 0:

        flash(
            "WFH request cannot be approved. Maximum allowed WFH days per week is 2. Employees must attend the office for at least 3 days whenever no leave is taken."
        )

        return redirect(url_for("user_dashboard"))

    # --------------------------------------------------
    # Rule 4
    # Office =0
    # WFH =2
    # Leave =3
    # REJECT
    # --------------------------------------------------

    elif office_days == 0 and wfh_days == 2 and leave_days_week == 3:

        flash(
            "Request cannot be approved. Employees must maintain sufficient office attendance. Combination of 3 leave days and 2 WFH days violates company policy."
        )

        return redirect(url_for("user_dashboard"))

    # --------------------------------------------------
    # Rule 5
    # Office =2
    # WFH =0
    # Leave =3
    # APPROVED
    # --------------------------------------------------

    elif office_days == 2 and wfh_days == 0 and leave_days_week == 3:

        status = "Pending"

    # --------------------------------------------------
    # Rule 6
    # More than 2 WFH
    # --------------------------------------------------

    elif wfh_days > 2:

        flash(
            "Maximum of 2 WFH days is allowed in a week. Please choose Office attendance or Leave for the remaining day."
        )

        return redirect(url_for("user_dashboard"))

    # --------------------------------------------------
    # Rule 7
    # Office <2 and Leave <3
    # --------------------------------------------------

    elif office_days < 2 and leave_days_week < 3:

        flash(
            "Office attendance requirement is not met. Employees must attend office for the minimum required number of days."
        )

        return redirect(url_for("user_dashboard"))

    # --------------------------------------------------
    # Rule 8
    # Invalid Combination
    # --------------------------------------------------

    allowed_patterns = [

        (3, 2, 0),  # Standard
        (2, 2, 1),  # One Leave
        (2, 0, 3),  # Three Leaves
        (0, 0, 5),  # Five Days Leave (Admin Approval)

        # Partial week requests (remaining days assumed Office)
        (4, 1, 0),
        (4, 0, 1),

        (3, 1, 1),
        (3, 0, 2),

        (4, 0, 0),
        (5, 0, 0)
    ]

    current_pattern = (
        office_days,
        wfh_days,
        leave_days_week
    )

    if current_pattern not in allowed_patterns:
        flash(
            "Selected attendance combination does not comply with company attendance policy. Please review your Leave/WFH request."
        )

        return redirect(url_for("user_dashboard"))
    # CHECK FOR DUPLICATE DATE APPLICATIONS

    for req in all_requests:

        if req["username"] != username:
            continue

        existing_from = datetime.strptime(
            req["from_date"],
            "%Y-%m-%d"
        ).date()

        existing_to = datetime.strptime(
            req["to_date"],
            "%Y-%m-%d"
        ).date()

        # Check overlap between old request and new request

        if (
                from_date_obj <= existing_to and
                to_date_obj >= existing_from
        ):
            flash(
                f"You have already applied Leave/WFH between "
                f"{existing_from.strftime('%d-%m-%Y')} and "
                f"{existing_to.strftime('%d-%m-%Y')}"
            )

            return redirect(url_for("user_dashboard"))
            current_date += timedelta(days=1)

    new_request = {

        "username": username,

        "team": team,

        "request_type": request_type,

        "leave_type": leave_type if leave_type else "WFH",

        "from_date": from_date,

        "to_date": to_date,

        "reason": reason,

        "status": status,

        "leave_days": leave_days,

        "long_leave": long_leave,

        "notification": notification,

        "notification_seen": True
    }

    all_requests.append(new_request)

    save_requests(all_requests)

    if request_type == "WFH":

        if status == "Accepted":
            flash("WFH request auto-approved successfully!")

        else:
            flash("WFH request submitted successfully and sent for Manager/Admin approval.")

    else:

        flash("Leave request submitted successfully!")

    return redirect(url_for("user_dashboard"))


# ==============================
# SAVE PROFILE
# ==============================

@app.route("/save_profile", methods=["POST"])
def save_profile():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    users = load_users()

    username = session.get("username")

    employee_id = request.form.get("employee_id")

    desk_number = request.form.get("desk_number")

    pc_ptag = request.form.get("pc_ptag").strip()
    monitor_ptag = request.form.get("monitor_ptag").strip()

    employee_id = employee_id.strip()
    desk_number = desk_number.strip()

    # ==========================================
    # DUPLICATE CHECK
    # ==========================================

    for user in users:

        # Skip current logged-in user
        if user["username"] == username:
            continue

        if user.get("employee_id", "").strip().lower() == employee_id.lower():
            flash("Employee ID already exists.")

            return redirect(url_for("user_dashboard"))

        if user.get("desk_number", "").strip().lower() == desk_number.lower():
            flash("Desk Number already exists.")

            return redirect(url_for("user_dashboard"))

        if user.get("pc_ptag", "").strip().lower() == pc_ptag.lower():
            flash("PC PTag already exists.")
            return redirect(url_for("user_dashboard"))

        if user.get("monitor_ptag", "").strip().lower() == monitor_ptag.lower():
            flash("Monitor PTag already exists.")
            return redirect(url_for("user_dashboard"))

    if len(employee_id) > 5:
        flash("Employee ID cannot exceed 5 characters")
        return redirect(url_for("user_dashboard"))

    if len(desk_number) > 8:
        flash("Desk Number cannot exceed 8 characters")
        return redirect(url_for("user_dashboard"))

    if len(pc_ptag) > 9:
        flash("PC PTag cannot exceed 9 characters")
        return redirect(url_for("user_dashboard"))

    if len(monitor_ptag) > 9:
        flash("Monitor PTag cannot exceed 9 characters")
        return redirect(url_for("user_dashboard"))

    if not pc_ptag.isalnum():
        flash("PC PTag should contain only letters and numbers")
        return redirect(url_for("user_dashboard"))

    if not monitor_ptag.isalnum():
        flash("Monitor PTag should contain only letters and numbers")
        return redirect(url_for("user_dashboard"))

    skillset = request.form.get("skillset")

    certification = request.form.get("certification")

    pattern = r'^[A-Za-z0-9+#.\-\s]+(,\s*[A-Za-z0-9+#.\-\s]+)*$'

    if not re.fullmatch(pattern, skillset):
        flash("Invalid Skillset format.")
        return redirect(url_for("user_dashboard"))

    if not re.fullmatch(pattern, certification):
        flash("Invalid Certification format.")
        return redirect(url_for("user_dashboard"))

    experience = request.form.get("experience")

    resume_file = request.files.get("resume")

    photo_file = request.files.get("employee_photo")

    certificate_files = request.files.getlist("certificates")

    os.makedirs("static/uploads/photos", exist_ok=True)

    os.makedirs("static/uploads/resumes", exist_ok=True)

    os.makedirs("static/uploads/certificates", exist_ok=True)

    for user in users:

        if user["username"] == username:

            user["employee_id"] = employee_id

            user["desk_number"] = desk_number

            user["pc_ptag"] = pc_ptag

            user["monitor_ptag"] = monitor_ptag

            user.setdefault("pc_working", "W")

            user.setdefault("monitor_working", "W")

            user.setdefault("desk_availability", "A")

            user["skillset"] = skillset

            user["experience"] = experience

            user["certification"] = certification

            # SAVE PHOTO
            if photo_file and photo_file.filename != "":
                photo_filename = (
                        username + "_" + photo_file.filename
                )

                photo_path = os.path.join(
                    "static/uploads/photos",
                    photo_filename
                )

                photo_file.save(photo_path)

                user["employee_photo"] = photo_filename

            # SAVE RESUME
            if resume_file and resume_file.filename != "":
                resume_filename = (
                        username + "_" + resume_file.filename
                )

                resume_path = os.path.join(
                    "static/uploads/resumes",
                    resume_filename
                )

                resume_file.save(resume_path)

                user["resume"] = resume_filename

            certificate_names = user.get("certificate_files", [])

            # Existing uploaded certificates
            certificate_names = user.get("certificate_files", [])

            for cert in certificate_files:

                if cert and cert.filename.strip() != "":

                    filename = username + "_" + cert.filename

                    cert.save(
                        os.path.join(
                            "static/uploads/certificates",
                            filename
                        )
                    )

                    duplicate = False

                    # Check whether this file already exists
                    for c in certificate_names:

                        if isinstance(c, dict):

                            if c["file"] == filename:
                                duplicate = True
                                break

                        else:

                            if c == filename:
                                duplicate = True
                                break

                    # Add only if it is a new certificate
                    if not duplicate:
                        certificate_names.append({

                            "file": filename,

                            "status": "Pending"

                        })

            # Save old + new certificates
            user["certificate_files"] = certificate_names

    save_users(users)

    flash("Profile Saved Successfully")

    return redirect(url_for("user_dashboard"))


# ==============================
# SIGNUP
# ===========================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":

        users = load_users()

        username = request.form["username"].strip()

        password = request.form["password"]

        team = request.form["team"]

        # PASSWORD VALIDATION

        if not is_valid_password(password):
            flash(
                "Password must be 8-12 characters and contain at least 1 uppercase letter, 1 lowercase letter and 1 special character."
            )

            return redirect(url_for("signup"))

        # CHECK DUPLICATE USERNAME

        for user in users:

            if user["username"].strip().lower() == username.strip().lower():
                flash("User already exists")

                return redirect(url_for("signup"))

        users.append({

            "username": username,
            "password": password,
            "team": team,

            "employee_id": "",
            "desk_number": "",
            "pc_ptag": "",
            "monitor_ptag": "",
            "skillset": "",
            "experience": "",
            "certification": "",
            "employee_photo": "",
            "resume": "",
            "pc_working": "W",
            "monitor_working": "W",
            "desk_availability": "A",
            "certificate_files": []


        })

        save_users(users)

        flash("Sign up Successful")

        return redirect(url_for("login"))

    return render_template("signup.html")

# ==============================
# LOGIN
# ==============================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        session.clear()

        username = request.form["username"]

        password = request.form["password"]

        # ADMIN LOGIN

        if username == "admin":

            if password == "admin123":

                session["role"] = "admin"

                session["username"] = "admin"

                session["admin_login_success"] = True

                flash("Admin Login Successful")

                return redirect(url_for("admin_dashboard"))

            else:

                flash("Invalid Password")

                return redirect(url_for("login"))

        # USER LOGIN

        users = load_users()

        user_found = False

        for user in users:

            if user["username"] == username:

                user_found = True

                if user["password"] == password:

                    session["role"] = "user"

                    session["username"] = username

                    session["team"] = user["team"]

                    flash("Login Successful")

                    return redirect(url_for("user_dashboard"))

                else:

                    flash("Invalid Password")

                    return redirect(url_for("login"))

        if not user_found:

            flash("Invalid Username")

            return redirect(url_for("login"))

    return render_template("login.html")

# ==============================
# USER DASHBOARD
# ==============================

@app.route("/user")
def user_dashboard():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    username = session.get("username")

    all_requests = [

        r for r in load_requests()

        if r["username"] == username

    ][::-1]
    # ==========================
    # DASHBOARD COUNTS
    # ==========================

    total_wfh = sum(
        1 for r in all_requests
        if r["request_type"] == "WFH"
    )

    total_leave = sum(
        1 for r in all_requests
        if r["request_type"] == "Leave"
    )

    approved_wfh = sum(
        1 for r in all_requests
        if r["request_type"] == "WFH"
        and r["status"] == "Accepted"
    )

    approved_leave = sum(
        1 for r in all_requests
        if r["request_type"] == "Leave"
        and r["status"] == "Accepted"
    )

    rejected_wfh = sum(
        1 for r in all_requests
        if r["request_type"] == "WFH"
        and r["status"] == "Rejected"
    )

    rejected_leave = sum(
        1 for r in all_requests
        if r["request_type"] == "Leave"
        and r["status"] == "Rejected"
    )

    approved_total = approved_wfh + approved_leave
    rejected_total = rejected_wfh + rejected_leave


    users = load_users()

    profile = None

    for user in users:

        if user["username"] == username:
            profile = user

            break

    return render_template(

        "user_dashboard.html",

        username=username,

        requests=all_requests,

        today=date.today().isoformat(),

        profile=profile,

        total_wfh = total_wfh,
        total_leave = total_leave,

        approved_wfh = approved_wfh,
        approved_leave = approved_leave,

        rejected_wfh = rejected_wfh,
        rejected_leave = rejected_leave,

        approved_total = approved_total,
        rejected_total = rejected_total

    )


# ==============================
# ADMIN DASHBOARD
# ==============================

@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    requests_data = load_requests()

    users = load_users()

    pending_count = len([
        r for r in requests_data
        if r["status"] == "Pending"
    ])

    long_leave_requests = [
        r for r in requests_data
        if r.get("long_leave") == True
    ]

    return render_template(
        "admin_dashboard.html",
        pending_count=pending_count,
        requests=requests_data,
        users=users,
        long_leave_requests=long_leave_requests
    )

###############admin_reports##############
@app.route("/admin_reports")
def admin_reports():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    return render_template("admin_reports.html")


# ==============================
# ADMIN REQUESTS
# ==============================

@app.route("/admin_requests")
def admin_requests():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    requests_data = load_requests()

    pending_count = len([

        r for r in requests_data

        if r["status"] == "Pending"

    ])

    indexed_requests = list(enumerate(requests_data))[::-1]

    return render_template(

        "admin_requests.html",

        requests=indexed_requests,

        pending_count=pending_count

    )


# ==============================
# APPROVE / REJECT
# ==============================

@app.route("/update_request/<int:index>/<action>")
def update_request(index, action):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    requests_data = load_requests()

    if index < len(requests_data):

        request_item = requests_data[index]

        request_type = request_item["request_type"]

        if action == "accept":

            requests_data[index]["status"] = "Accepted"

            requests_data[index]["notification"] = (
                f"Your {request_type} Request is Accepted"
            )

            requests_data[index]["notification_seen"] = False

        elif action == "reject":

            requests_data[index]["status"] = "Rejected"

            requests_data[index]["notification"] = (
                f"Your {request_type} Request is Rejected"
            )

            requests_data[index]["notification_seen"] = False

        save_requests(requests_data)

    return redirect(url_for("admin_requests"))


@app.route("/approve_certificate/<username>/<filename>")
def approve_certificate(username, filename):
    users = load_users()

    for user in users:
        if user["username"] == username:

            for cert in user.get("certificate_files", []):

                if cert["file"] == filename:
                    cert["status"] = "Approved"

    save_users(users)

    return redirect(url_for("admin_dashboard"))


@app.route("/reject_certificate/<username>/<filename>")
def reject_certificate(username, filename):
    users = load_users()

    for user in users:
        if user["username"] == username:

            for cert in user.get("certificate_files", []):

                if cert["file"] == filename:
                    cert["status"] = "Rejected"

    save_users(users)

    return redirect(url_for("admin_dashboard"))

# ==============================
# ADMIN NOTIFICATIONS
# ==============================

@app.route("/admin_notifications")
def admin_notifications():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    requests_data = load_requests()

    pending_requests = [

        {"data": r, "index": i}

        for i, r in enumerate(requests_data)

        if r["status"] == "Pending"

    ]

    pending_count = len(pending_requests)

    return render_template(

        "admin_notifications.html",

        requests=pending_requests,

        pending_count=pending_count

    )


# ==============================
# ADMIN USERS
# ==============================

@app.route("/admin_users")
def admin_users():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    users = load_users()

    return render_template(

        "admin_users.html",

        users=users

    )


# ==============================
# UPDATE USER PROFILE (ADMIN)
# ==============================

@app.route("/update_user_profile", methods=["POST"])
def update_user_profile():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    username = request.form.get("username")

    users = load_users()

    for user in users:

        if user["username"] == username:
            user["desk_number"] = request.form.get("desk_number")

            user["pc_ptag"] = request.form.get("pc_ptag")

            user["monitor_ptag"] = request.form.get("monitor_ptag")

            user["pc_working"] = request.form.get("pc_working")

            user["monitor_working"] = request.form.get("monitor_working")

            user["desk_availability"] = request.form.get("desk_availability")

            break

    save_users(users)

    flash("User Profile Updated Successfully")

    return redirect(url_for("admin_users"))
# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():
    session.clear()

    flash("Logout Successful")

    return redirect(url_for("login"))

# ==============================
# MARK NOTIFICATIONS AS SEEN
# ==============================

@app.route("/mark_notifications_seen")
def mark_notifications_seen():

    if session.get("role") != "user":
        return ""

    username = session.get("username")

    requests_data = load_requests()

    for req in requests_data:

        if req["username"] == username:

            req["notification_seen"] = True

    save_requests(requests_data)

    return ""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)