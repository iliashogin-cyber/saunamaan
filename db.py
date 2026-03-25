import sqlite3
from flask import g
import config


def get_connection():
    if "db" not in g:
        g.db = sqlite3.connect(config.DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_connection(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def execute(sql, params=None):
    if params is None:
        params = []
    conn = get_connection()
    result = conn.execute(sql, params)
    conn.commit()
    return result.lastrowid


def query(sql, params=None):
    if params is None:
        params = []
    conn = get_connection()
    return conn.execute(sql, params).fetchall()
