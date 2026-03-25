from flask import Flask, render_template, request, redirect, session
from datetime import date, timedelta
import secrets
import calendar
import config
import db
import users
import slots as slot_service
import bookings as booking_service
import announcements as ann_service


app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.teardown_appcontext(db.close_connection)


@app.before_request
def ensure_csrf():
    if "user_id" in session and "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)


def check_csrf():
    if request.form.get("csrf_token") != session.get("csrf_token"):
        return False
    return True


# ── Index ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    spaces = slot_service.get_spaces()
    announcements = ann_service.get_announcements(limit=3)
    return render_template("index.html", spaces=spaces,
                           announcements=announcements)

# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        session["csrf_token"] = secrets.token_hex(16)
        return render_template("register.html")

    if not check_csrf():
        return render_template("register.html", error="Invalid request.")

    username = request.form["username"].strip()
    password = request.form["password"].strip()
    password2 = request.form["password2"].strip()

    if not username or len(username) > 12:
        return render_template("register.html",
                               error="Username must be 1-12 characters.")
    if len(password) < 8:
        return render_template("register.html",
                               error="Password must be at least 8 characters.")
    if password != password2:
        return render_template("register.html",
                               error="Passwords do not match.")

    user_id = users.register(username, password)
    if not user_id:
        return render_template("register.html",
                               error="Username already taken.")

    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        session["csrf_token"] = secrets.token_hex(16)
        return render_template("login.html")

    if not check_csrf():
        return render_template("login.html", error="Invalid request.")

    username = request.form["username"]
    password = request.form["password"]

    if not users.login(username, password):
        return render_template("login.html",
                               error="Wrong username or password.")

    session["csrf_token"] = secrets.token_hex(16)
    return redirect("/")


@app.route("/logout")
def logout():
    users.logout()
    return redirect("/")


# ── Space calendar ────────────────────────────────────────────────────────────


@app.route("/spaces/<int:space_id>/calendar")
def space_calendar(space_id):
    if not users.require_login():
        return redirect("/login")

    space = slot_service.get_space(space_id)
    if not space:
        return redirect("/")

    view = request.args.get("view", "week")
    selected_slot_id = request.args.get("selected", type=int)
    today = date.today()

    selected_slot_data = None
    if selected_slot_id:
        selected_slot_data = slot_service.get_slot(selected_slot_id)

    if view == "week":
        week_str = request.args.get(
            "week", str(today - timedelta(days=today.weekday()))
        )
        try:
            monday = date.fromisoformat(week_str)
            monday = monday - timedelta(days=monday.weekday())
        except ValueError:
            monday = today - timedelta(days=today.weekday())

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        week_days = []
        for i in range(7):
            d = monday + timedelta(days=i)
            day_slots = slot_service.get_day_slots(space_id, str(d))
            week_days.append({
                "name": day_names[i],
                "date": d,
                "date_str": str(d),
                "is_today": d == today,
                "is_past": d < today,
                "slots": day_slots
            })

        return render_template("space_calendar.html",
                               space=space,
                               view="week",
                               week_days=week_days,
                               monday_str=str(monday),
                               prev_monday=str(monday - timedelta(days=7)),
                               next_monday=str(monday + timedelta(days=7)),
                               today=today,
                               selected_slot_id=selected_slot_id,
                               selected_slot_data=selected_slot_data)

    # month view
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    if month < 1:
        month = 12
        year -= 1
    if month > 12:
        month = 1
        year += 1

    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    day_status = slot_service.get_month_day_status(space_id, year, month)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template("space_calendar.html",
                           space=space,
                           view="month",
                           cal=cal,
                           year=year,
                           month=month,
                           month_name=month_name,
                           today=today,
                           day_status=day_status,
                           prev_month=prev_month,
                           prev_year=prev_year,
                           next_month=next_month,
                           next_year=next_year,
                           selected_slot_id=selected_slot_id,
                           selected_slot_data=selected_slot_data)


# ── Space & Availability Management (head users) ──────────────────────────────

@app.route("/admin/availability")
def availability():
    if not users.require_head():
        return redirect("/")
    spaces = slot_service.get_spaces()
    return render_template("availability.html", spaces=spaces,
                           selected_space=None, templates=[],
                           week_days=[], today=date.today())


@app.route("/admin/availability/<int:space_id>")
def availability_space(space_id):
    if not users.require_head():
        return redirect("/")

    spaces = slot_service.get_spaces()
    space = slot_service.get_space(space_id)
    if not space:
        return redirect("/admin/availability")

    today = date.today()
    week_str = request.args.get(
        "week", str(today - timedelta(days=today.weekday()))
    )
    try:
        monday = date.fromisoformat(week_str)
        monday = monday - timedelta(days=monday.weekday())
    except ValueError:
        monday = today - timedelta(days=today.weekday())

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    week_days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        day_slots = slot_service.get_day_slots(space_id, str(d))
        week_days.append({
            "name": day_names[i],
            "date": d,
            "date_str": str(d),
            "is_today": d == today,
            "slots": day_slots
        })

    templates = slot_service.get_templates(space_id)

    return render_template("availability.html",
                           spaces=spaces,
                           selected_space=space,
                           week_days=week_days,
                           monday_str=str(monday),
                           prev_monday=str(monday - timedelta(days=7)),
                           next_monday=str(monday + timedelta(days=7)),
                           templates=templates,
                           today=today)


@app.route("/admin/availability/<int:space_id>/generate", methods=["POST"])
def generate_availability(space_id):
    if not users.require_head():
        return redirect("/")
    if not check_csrf():
        return redirect("/admin/availability/" + str(space_id))

    day_of_week = request.form["day_of_week"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]
    slot_duration = request.form.get("slot_duration", 60)
    valid_from = request.form["valid_from"]
    valid_until = request.form["valid_until"]
    allows_recurring = 1 if request.form.get("allows_recurring") else 0

    if start_time >= end_time or valid_from > valid_until:
        return redirect("/admin/availability/" + str(space_id))

    slot_service.generate_slots(space_id, day_of_week, start_time,
                                end_time, slot_duration,
                                valid_from, valid_until,
                                allows_recurring,
                                session["user_id"])
    return redirect("/admin/availability/" + str(space_id))


@app.route("/admin/availability/template/<int:template_id>/delete",
           methods=["POST"])
def delete_template(template_id):
    if not users.require_head():
        return redirect("/")
    if not check_csrf():
        return redirect("/admin/availability")
    space_id = request.form.get("space_id")
    slot_service.delete_template(template_id)
    return redirect("/admin/availability/" + str(space_id))


@app.route("/admin/availability/<int:space_id>/delete_from", methods=["POST"])
def delete_from_date(space_id):
    if not users.require_head():
        return redirect("/")
    if not check_csrf():
        return redirect("/admin/availability/" + str(space_id))
    from_date = request.form["from_date"]
    slot_service.delete_future_slots(space_id, from_date)
    return redirect("/admin/availability/" + str(space_id))


@app.route("/admin/spaces/new", methods=["POST"])
def new_space():
    if not users.require_head():
        return redirect("/")
    if not check_csrf():
        return redirect("/admin/availability")
    name = request.form["name"].strip()
    if name and len(name) <= 50:
        slot_service.add_space(name)
    return redirect("/admin/availability")


# ── Spaces & Bookings ──────────────────────────────────────────────────────────────────

@app.route("/spaces")
def spaces():
    if not users.require_login():
        return redirect("/login")
    all_spaces = slot_service.get_spaces()
    return render_template("spaces.html", spaces=all_spaces)

@app.route("/bookings")
def list_bookings():
    if not users.require_login():
        return redirect("/login")
    if users.require_head():
        all_bookings = booking_service.get_all_bookings()
        return render_template("bookings.html",
                               bookings=all_bookings,
                               grouped=False)
    else:
        grouped = booking_service.get_user_bookings_grouped(session["user_id"])
        return render_template("bookings.html",
                               bookings=grouped,
                               grouped=True)


@app.route("/bookings/new/<int:slot_id>", methods=["POST"])
def new_booking(slot_id):
    if not users.require_login():
        return redirect("/login")
    if not check_csrf():
        return redirect("/")

    slot = slot_service.get_slot(slot_id)
    if not slot:
        return redirect("/")
    if booking_service.slot_is_taken(slot_id):
        return redirect("/spaces/" + str(slot["space_id"]) + "/calendar")

    category_id = slot["default_category_id"]
    is_recurring = 1 if request.form.get("is_recurring") else 0

    if is_recurring and slot["allows_recurring"]:
        count = booking_service.add_recurring_bookings(
            session["user_id"], slot_id, category_id
        )
    else:
        booking_service.add_booking(session["user_id"], slot_id,
                                    category_id, 0)

    return redirect("/bookings")


@app.route("/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
def edit_booking(booking_id):
    if not users.require_login():
        return redirect("/login")

    booking = booking_service.get_booking(booking_id)
    if not booking:
        return redirect("/bookings")

    if not users.require_head() and booking["user_id"] != session["user_id"]:
        return redirect("/bookings")

    if request.method == "GET":
        return render_template("booking_edit.html", booking=booking)

    if not check_csrf():
        return redirect("/")

    is_recurring = 1 if request.form.get("is_recurring") else 0
    booking_service.update_booking(booking_id, is_recurring)
    return redirect("/bookings")


@app.route("/bookings/<int:booking_id>/delete", methods=["POST"])
def delete_booking(booking_id):
    if not users.require_login():
        return redirect("/login")

    booking = booking_service.get_booking(booking_id)
    if not booking:
        return redirect("/bookings")

    if not users.require_head() and booking["user_id"] != session["user_id"]:
        return redirect("/bookings")

    if not check_csrf():
        return redirect("/")

    cancel_series = request.form.get("cancel_series")
    if cancel_series and booking["is_recurring"]:
        booking_service.delete_recurring_group(booking_id,
                                               booking["user_id"],
                                               from_now=True)
    else:
        booking_service.delete_booking(booking_id)

    return redirect("/bookings")


# ── Announcements ─────────────────────────────────────────────────────────────

@app.route("/announcements")
def announcements():
    if not users.require_login():
        return redirect("/login")
    all_ann = ann_service.get_announcements()
    enriched = []
    for a in all_ann:
        reactions = ann_service.get_reactions(a["id"])
        user_reaction = ann_service.get_user_reaction(
            a["id"], session["user_id"]
        )
        enriched.append({**dict(a), "reactions": reactions,
                         "user_reaction": user_reaction})
    return render_template("announcements.html", announcements=enriched)


@app.route("/announcements/new", methods=["GET", "POST"])
def new_announcement():
    if not users.require_head():
        return redirect("/")
    if request.method == "GET":
        return render_template("announcement_new.html")

    if not check_csrf():
        return redirect("/")

    title = request.form["title"].strip()
    content = request.form["content"].strip()

    if not title or not content:
        return render_template("announcement_new.html",
                               error="Title and content are required.")
    if len(title) > 100:
        return render_template("announcement_new.html",
                               error="Title must be under 100 characters.")

    ann_service.add_announcement(session["user_id"], title, content)
    return redirect("/announcements")


@app.route("/announcements/<int:ann_id>/edit", methods=["GET", "POST"])
def edit_announcement(ann_id):
    if not users.require_head():
        return redirect("/")

    ann = ann_service.get_announcement(ann_id)
    if not ann:
        return redirect("/announcements")

    if request.method == "GET":
        return render_template("announcement_edit.html", ann=ann)

    if not check_csrf():
        return redirect("/")

    title = request.form["title"].strip()
    content = request.form["content"].strip()

    if not title or not content:
        return render_template("announcement_edit.html", ann=ann,
                               error="Title and content are required.")

    ann_service.update_announcement(ann_id, title, content)
    return redirect("/announcements")


@app.route("/announcements/<int:ann_id>/delete", methods=["POST"])
def delete_announcement(ann_id):
    if not users.require_head():
        return redirect("/")
    if not check_csrf():
        return redirect("/announcements")
    ann_service.delete_announcement(ann_id)
    return redirect("/announcements")


@app.route("/announcements/<int:ann_id>/react", methods=["POST"])
def react_announcement(ann_id):
    if not users.require_login():
        return redirect("/login")
    if not check_csrf():
        return redirect("/announcements")
    emoji = request.form.get("emoji", "")
    allowed = ["👍", "👎", "❤️", "😂", "😮", "👏", "🙏"]
    if emoji in allowed:
        ann_service.toggle_reaction(ann_id, session["user_id"], emoji)
    return redirect("/announcements")


# ── User profiles ─────────────────────────────────────────────────────────────

@app.route("/user/<int:user_id>")
def user_page(user_id):
    if not users.require_login():
        return redirect("/login")

    if not users.require_head() and session["user_id"] != user_id:
        return redirect("/")

    user = users.get_user_by_id(user_id)
    if not user:
        return redirect("/")

    stats = users.get_user_stats(user_id)
    user_bookings = booking_service.get_user_bookings(user_id)
    return render_template("user.html", user=user, stats=stats,
                           bookings=user_bookings)


@app.route("/user/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    if not users.require_login():
        return redirect("/login")

    if not users.require_head() and session["user_id"] != user_id:
        return redirect("/")

    user = users.get_user_by_id(user_id)
    if not user:
        return redirect("/")

    if request.method == "GET":
        return render_template("user_edit.html", user=user)

    if not check_csrf():
        return redirect("/")

    apartment = request.form["apartment"].strip()
    if len(apartment) > 20:
        return render_template("user_edit.html", user=user,
                               error="Apartment must be under 20 characters.")

    users.update_apartment(user_id, apartment)
    return redirect("/user/" + str(user_id))


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    if not users.require_head():
        return redirect("/")
    all_users = users.get_all_users()
    all_bookings = booking_service.get_all_bookings()
    return render_template("admin.html", users=all_users,
                           bookings=all_bookings)
