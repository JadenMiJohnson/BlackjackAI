import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = "users.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def register_user(username: str, password: str) -> dict:
    if not username or not password:
        return {"success": False, "error": "Username and password are required"}
    if len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters"}
    if len(password) < 4:
        return {"success": False, "error": "Password must be at least 4 characters"}

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return {"success": False, "error": "Username already taken"}
        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def login_user(username: str, password: str) -> dict:
    if not username or not password:
        return {"success": False, "error": "Username and password are required"}

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not user:
            return {"success": False, "error": "Invalid username or password"}
        if not check_password_hash(user["password_hash"], password):
            return {"success": False, "error": "Invalid username or password"}
        return {"success": True, "user_id": user["id"], "username": user["username"]}
    finally:
        conn.close()


init_db()
