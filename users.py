from werkzeug.security import check_password_hash, generate_password_hash
from flask import session
import db


def register(username, password, is_head=0):
    password_hash = generate_password_hash(password)
    try:
        sql = "INSERT INTO users (username, password_hash, is_head) VALUES (?, ?, ?)"
        return db.execute(sql, [username, password_hash, is_head])
    except Exception:
        return None


def login(username, password):
    sql = "SELECT id, password_hash, is_head FROM users WHERE username = ?"
    result = db.query(sql, [username])
    if not result:
        return False
    user = result[0]
    if not check_password_hash(user["password_hash"], password):
        return False
    session["user_id"] = user["id"]
    session["username"] = username
    session["is_head"] = user["is_head"]
    return True


def logout():
    session.clear()


def get_user():
    if "user_id" not in session:
        return None
    sql = "SELECT id, username, is_head, apartment FROM users WHERE id = ?"
    result = db.query(sql, [session["user_id"]])
    return result[0] if result else None


def require_login():
    return "user_id" in session


def require_head():
    return session.get("is_head") == 1


# For stats:
def get_user_by_id(user_id):
    sql = """SELECT id, username, is_head, apartment
             FROM users WHERE id = ?"""
    result = db.query(sql, [user_id])
    return result[0] if result else None


def get_user_stats(user_id):
    sql = """SELECT COUNT(b.id) AS total_bookings,
                    SUM(b.is_recurring) AS recurring_bookings,
                    COUNT(DISTINCT s.space_id) AS spaces_used
             FROM bookings b, slots s
             WHERE b.user_id = ? AND b.slot_id = s.id"""
    result = db.query(sql, [user_id])
    return result[0] if result else None


def get_all_users():
    sql = "SELECT id, username, is_head, apartment FROM users ORDER BY id"
    return db.query(sql)


def update_apartment(user_id, apartment):
    sql = "UPDATE users SET apartment = ? WHERE id = ?"
    db.execute(sql, [apartment, user_id])
