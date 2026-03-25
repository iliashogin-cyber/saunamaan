import db


def get_announcements(limit=None):
    sql = """SELECT a.id, a.title, a.content, a.created_at, a.updated_at,
                    u.username, u.id AS user_id
             FROM announcements a, users u
             WHERE a.user_id = u.id
             ORDER BY a.created_at DESC"""
    if limit:
        sql += f" LIMIT {int(limit)}"
    return db.query(sql)


def get_announcement(announcement_id):
    sql = """SELECT a.id, a.title, a.content, a.created_at, a.updated_at,
                    u.username, u.id AS user_id
             FROM announcements a, users u
             WHERE a.id = ? AND a.user_id = u.id"""
    result = db.query(sql, [announcement_id])
    return result[0] if result else None


def add_announcement(user_id, title, content):
    sql = """INSERT INTO announcements (user_id, title, content)
             VALUES (?, ?, ?)"""
    return db.execute(sql, [user_id, title, content])


def update_announcement(announcement_id, title, content):
    sql = """UPDATE announcements
             SET title = ?, content = ?,
                 updated_at = datetime('now')
             WHERE id = ?"""
    db.execute(sql, [title, content, announcement_id])


def delete_announcement(announcement_id):
    db.execute("DELETE FROM announcement_reactions WHERE announcement_id = ?",
               [announcement_id])
    db.execute("DELETE FROM announcements WHERE id = ?", [announcement_id])


def get_reactions(announcement_id):
    sql = """SELECT emoji, COUNT(*) AS count
             FROM announcement_reactions
             WHERE announcement_id = ?
             GROUP BY emoji
             ORDER BY count DESC"""
    return db.query(sql, [announcement_id])


def get_user_reaction(announcement_id, user_id):
    sql = """SELECT emoji FROM announcement_reactions
             WHERE announcement_id = ? AND user_id = ?"""
    result = db.query(sql, [announcement_id, user_id])
    return result[0]["emoji"] if result else None


def toggle_reaction(announcement_id, user_id, emoji):
    existing = get_user_reaction(announcement_id, user_id)
    if existing == emoji:
        db.execute("""DELETE FROM announcement_reactions
                      WHERE announcement_id = ? AND user_id = ?""",
                   [announcement_id, user_id])
    else:
        db.execute("""INSERT INTO announcement_reactions
                         (announcement_id, user_id, emoji)
                      VALUES (?, ?, ?)
                      ON CONFLICT(announcement_id, user_id)
                      DO UPDATE SET emoji = excluded.emoji""",
                   [announcement_id, user_id, emoji])
