import db


def get_all_bookings():
    sql = """SELECT b.id, b.is_recurring, b.recurring_group_id, b.created_at,
                    u.id AS user_id, u.username,
                    s.start_time, s.end_time,
                    sp.name AS space_name
             FROM bookings b, users u, slots s, spaces sp
             WHERE b.user_id = u.id
               AND b.slot_id = s.id
               AND s.space_id = sp.id
             ORDER BY s.start_time"""
    return db.query(sql)


def get_user_bookings(user_id):
    sql = """SELECT b.id, b.is_recurring, b.recurring_group_id, b.created_at,
                    s.start_time, s.end_time,
                    sp.name AS space_name
             FROM bookings b, slots s, spaces sp
             WHERE b.user_id = ?
               AND b.slot_id = s.id
               AND s.space_id = sp.id
             ORDER BY s.start_time"""
    return db.query(sql, [user_id])

def get_user_bookings_grouped(user_id):
    from datetime import datetime

    sql = """SELECT b.id, b.is_recurring, b.recurring_group_id,
                    b.created_at, s.start_time, s.end_time,
                    sp.name AS space_name
             FROM bookings b, slots s, spaces sp
             WHERE b.user_id = ?
               AND b.slot_id = s.id
               AND s.space_id = sp.id
             ORDER BY s.start_time"""
    rows = db.query(sql, [user_id])

    groups = {}
    singles = []

    for row in rows:
        if row["is_recurring"] and row["recurring_group_id"]:
            gid = row["recurring_group_id"]
            if gid not in groups:
                groups[gid] = {
                    "id": row["id"],
                    "group_id": gid,
                    "space_name": row["space_name"],
                    "time_start": row["start_time"][11:16],
                    "time_end": row["end_time"][11:16],
                    "day_of_week": datetime.fromisoformat(
                        row["start_time"]).strftime("%A"),
                    "valid_from": row["start_time"][:10],
                    "valid_until": row["start_time"][:10],
                    "is_recurring": True,
                    "count": 0
                }
            
            if row["start_time"][:10] > groups[gid]["valid_until"]:
                groups[gid]["valid_until"] = row["start_time"][:10]
            groups[gid]["count"] += 1
        else:
            singles.append({
                "id": row["id"],
                "group_id": None,
                "space_name": row["space_name"],
                "time_start": row["start_time"][11:16],
                "time_end": row["end_time"][11:16],
                "day_of_week": datetime.fromisoformat(
                    row["start_time"]).strftime("%A"),
                "date": row["start_time"][:10],
                "is_recurring": False,
                "count": 1
            })

    result = list(groups.values()) + singles
    result.sort(key=lambda x: x.get("date") or x.get("valid_from") or "")
    return result


def get_booking(booking_id):
    sql = """SELECT b.id, b.user_id, b.slot_id, b.category_id,
                    b.is_recurring, b.recurring_group_id,
                    s.start_time, s.end_time,
                    sp.name AS space_name, sp.id AS space_id,
                    u.username
             FROM bookings b, slots s, spaces sp, users u
             WHERE b.id = ?
               AND b.slot_id = s.id
               AND s.space_id = sp.id
               AND b.user_id = u.id"""
    result = db.query(sql, [booking_id])
    return result[0] if result else None


def slot_is_taken(slot_id):
    sql = "SELECT id FROM bookings WHERE slot_id = ?"
    return len(db.query(sql, [slot_id])) > 0


def add_booking(user_id, slot_id, category_id, is_recurring=0,
                recurring_group_id=None):
    sql = """INSERT INTO bookings
                 (user_id, slot_id, category_id, is_recurring, recurring_group_id)
             VALUES (?, ?, ?, ?, ?)"""
    return db.execute(sql, [user_id, slot_id, category_id,
                            is_recurring, recurring_group_id])


def add_recurring_bookings(user_id, slot_id, category_id):
    from datetime import datetime, date, timedelta

    base = db.query("""SELECT id, start_time, space_id, allows_recurring
                       FROM slots WHERE id = ?""", [slot_id])
    if not base:
        return 0
    base = base[0]

    if not base["allows_recurring"]:
        add_booking(user_id, slot_id, category_id, 0)
        return 1

    time_str = base["start_time"][11:16]         
    dow = datetime.fromisoformat(base["start_time"]).weekday() 

    today = date.today()
    until = today + timedelta(days=183)  # around 6 months...         

    sql = """SELECT s.id, s.start_time
             FROM slots s
             WHERE s.space_id = ?
               AND s.allows_recurring = 1
               AND substr(s.start_time, 12, 5) = ?
               AND date(s.start_time) >= date(?)
               AND date(s.start_time) <= date(?)
             ORDER BY s.start_time"""

    candidates = db.query(sql, [base["space_id"], time_str,
                                str(today), str(until)])

    # only matching weekday
    matching = [s for s in candidates
                if datetime.fromisoformat(s["start_time"]).weekday() == dow]

    if not matching:
        return 0
    
    result = db.query("SELECT MAX(recurring_group_id) AS mx FROM bookings")
    group_id = (result[0]["mx"] or 0) + 1

    booked = 0
    for slot in matching:
        taken = db.query("SELECT id FROM bookings WHERE slot_id = ?",
                         [slot["id"]])
        if not taken:
            db.execute("""INSERT INTO bookings
                             (user_id, slot_id, category_id,
                              is_recurring, recurring_group_id)
                          VALUES (?, ?, ?, 1, ?)""",
                       [user_id, slot["id"], category_id, group_id])
            booked += 1

    return booked


def delete_booking(booking_id):
    sql = "DELETE FROM bookings WHERE id = ?"
    db.execute(sql, [booking_id])


def delete_recurring_group(booking_id, user_id, from_now=True):
    """Cancel all future bookings in the same recurring group."""
    from datetime import datetime
    booking = get_booking(booking_id)
    if not booking or not booking["recurring_group_id"]:
        delete_booking(booking_id)
        return

    group_id = booking["recurring_group_id"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if from_now:
        sql = """DELETE FROM bookings
                 WHERE recurring_group_id = ?
                   AND user_id = ?
                   AND slot_id IN (
                       SELECT id FROM slots WHERE start_time >= ?
                   )"""
        db.execute(sql, [group_id, user_id, now])
    else:
        sql = """DELETE FROM bookings
                 WHERE recurring_group_id = ? AND user_id = ?"""
        db.execute(sql, [group_id, user_id])


def update_booking(booking_id, is_recurring):
    sql = "UPDATE bookings SET is_recurring = ? WHERE id = ?"
    db.execute(sql, [is_recurring, booking_id])
