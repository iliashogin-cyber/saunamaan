CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_head INTEGER NOT NULL DEFAULT 0,
    apartment TEXT
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE spaces (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    default_category_id INTEGER REFERENCES categories(id)
);

CREATE TABLE availability_templates (
    id INTEGER PRIMARY KEY,
    space_id INTEGER NOT NULL REFERENCES spaces(id),
    day_of_week INTEGER NOT NULL, 
    start_time TEXT NOT NULL,     -- "HH:MM" format
    end_time TEXT NOT NULL,       
    slot_duration INTEGER NOT NULL DEFAULT 60,
    valid_from TEXT NOT NULL,
    valid_until TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id)
);

CREATE TABLE slots (
    id INTEGER PRIMARY KEY,
    space_id INTEGER NOT NULL REFERENCES spaces(id),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    allows_recurring INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER REFERENCES users(id)
);

CREATE TABLE bookings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    slot_id INTEGER NOT NULL REFERENCES slots(id),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    is_recurring INTEGER NOT NULL DEFAULT 0,
    recurring_group_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);


CREATE TABLE announcements (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE TABLE announcement_reactions (
    id INTEGER PRIMARY KEY,
    announcement_id INTEGER NOT NULL REFERENCES announcements(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    emoji TEXT NOT NULL,
    UNIQUE(announcement_id, user_id)
);


CREATE UNIQUE INDEX idx_slots_unique ON slots(space_id, start_time);
CREATE INDEX idx_bookings_user ON bookings(user_id);
CREATE INDEX idx_bookings_slot ON bookings(slot_id);
CREATE INDEX idx_slots_start ON slots(start_time);
