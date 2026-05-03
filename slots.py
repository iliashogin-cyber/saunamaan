from datetime import date, timedelta, datetime
import db


def get_all_slots():
    sql = """SELECT s.id, s.start_time, s.end_time, s.allows_recurring,
                    sp.name AS space_name, u.username AS created_by
             FROM slots s, spaces sp, users u
             WHERE s.space_id = sp.id AND s.created_by = u.id
             ORDER BY s.start_time"""
    return db.query(sql)


def get_slot(slot_id):
    sql = """SELECT s.id, s.start_time, s.end_time, s.space_id,
                    s.allows_recurring, s.description_text, sp.name AS space_name,
                    sp.default_category_id
             FROM slots s, spaces sp
             WHERE s.id = ? AND s.space_id = sp.id"""
    result = db.query(sql, [slot_id])
    return result[0] if result else None


def get_space(space_id):
    sql = """SELECT id, name, default_category_id
             FROM spaces WHERE id = ?"""
    result = db.query(sql, [space_id])
    return result[0] if result else None


def get_spaces():
    sql = "SELECT id, name, default_category_id FROM spaces ORDER BY id"
    return db.query(sql)


def add_space(name):
    category_id = db.execute(
        "INSERT INTO categories (name) VALUES (?)", [name]
    )
    return db.execute(
        "INSERT INTO spaces (name, default_category_id) VALUES (?, ?)",
        [name, category_id]
    )


def delete_slot(slot_id):
    sql = "DELETE FROM bookings WHERE slot_id = ?"
    db.execute(sql, [slot_id])
    sql = "DELETE FROM slots WHERE id = ?"
    db.execute(sql, [slot_id])


def delete_future_slots(space_id, from_date):
    sql = """DELETE FROM bookings WHERE slot_id IN (
                 SELECT id FROM slots
                 WHERE space_id = ? AND start_time >= ?)"""
    db.execute(sql, [space_id, from_date])
    sql = "DELETE FROM slots WHERE space_id = ? AND start_time >= ?"
    db.execute(sql, [space_id, from_date])


def get_day_slots(space_id, date_str):
    like = date_str + "%"
    sql = """SELECT s.id, s.start_time, s.end_time, s.allows_recurring, 
             s.description_text,
             b.id AS booking_id, u.username AS booked_by,
             b.is_recurring AS booking_recurring
             FROM slots s
             LEFT JOIN bookings b ON b.slot_id = s.id
             LEFT JOIN users u ON b.user_id = u.id
             WHERE s.space_id = ? AND s.start_time LIKE ?
             ORDER BY s.start_time"""
    return db.query(sql, [space_id, like])


def get_month_day_status(space_id, year, month):
    like = f"{year}-{month:02d}%"
    sql = """SELECT substr(s.start_time, 1, 10) AS slot_date,
                    COUNT(s.id) AS total_slots,
                    COUNT(b.id) AS booked_slots
             FROM slots s
             LEFT JOIN bookings b ON b.slot_id = s.id
             WHERE s.space_id = ? AND s.start_time LIKE ?
             GROUP BY slot_date"""
    result = db.query(sql, [space_id, like])
    status = {}
    for row in result:
        if row["booked_slots"] == 0:
            status[row["slot_date"]] = "available"
        elif row["booked_slots"] == row["total_slots"]:
            status[row["slot_date"]] = "full"
        else:
            status[row["slot_date"]] = "partial"
    return status


def get_templates(space_id):
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Every day"]
    sql = """SELECT t.id, t.day_of_week, t.start_time, t.end_time,
                    t.slot_duration, t.valid_from, t.valid_until, t.description_text
             FROM availability_templates t
             WHERE t.space_id = ?
             ORDER BY t.valid_from"""
    result = db.query(sql, [space_id])
    templates = []
    for row in result:
        templates.append({
            "id": row["id"],
            "day_name": day_names[row["day_of_week"]],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "slot_duration": row["slot_duration"],
            "valid_from": row["valid_from"],
            "valid_until": row["valid_until"],
            "description_text": row["description_text"] or "",
        })
    return templates


def delete_template(template_id):
    sql = "DELETE FROM availability_templates WHERE id = ?"
    db.execute(sql, [template_id])


def generate_slots(space_id, day_of_week, start_time, end_time,
                   slot_duration, valid_from, valid_until,
                   allows_recurring, created_by, description_text=""):
    day_of_week = int(day_of_week)
    slot_duration = int(slot_duration)
    allows_recurring = int(allows_recurring)

    db.execute("""
        INSERT INTO availability_templates
            (space_id, day_of_week, start_time, end_time,
             slot_duration, valid_from, valid_until, created_by, description_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [space_id, day_of_week, start_time, end_time,
          slot_duration, valid_from, valid_until, created_by, description_text])

    start_h, start_m = map(int, start_time.split(":"))
    end_h, end_m = map(int, end_time.split(":"))

    current = date.fromisoformat(valid_from)
    end_date = date.fromisoformat(valid_until)
    count = 0

    while current <= end_date:
        matches = (day_of_week == 7 or current.weekday() == day_of_week)
        if matches:
            slot_start = datetime(current.year, current.month,
                                  current.day, start_h, start_m)
            end_dt = datetime(current.year, current.month,
                              current.day, end_h, end_m)
            while slot_start < end_dt:
                slot_end = slot_start + timedelta(minutes=slot_duration)
                if slot_end > end_dt:
                    break
                db.execute("""
                    INSERT OR IGNORE INTO slots
                        (space_id, start_time, end_time,
                         allows_recurring, created_by, description_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [space_id,
                      slot_start.strftime("%Y-%m-%d %H:%M"),
                      slot_end.strftime("%Y-%m-%d %H:%M"),
                      allows_recurring,
                      created_by,
                      description_text])
                slot_start = slot_end
                count += 1
        current += timedelta(days=1)

    return count
