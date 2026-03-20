from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_USER_EMAIL = "demo@tfgpharma.com"
DEFAULT_USER_ROLE = "Analista"
DEFAULT_USER_COMPANY = "TFG Pharma"


def _database_path() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    db_dir = project_root / "data" / "app_data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "pharma_users.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_database_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    return conn


def init_user_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                company TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                theme TEXT NOT NULL DEFAULT 'Dark',
                accent TEXT NOT NULL DEFAULT 'Cyan',
                font TEXT NOT NULL DEFAULT 'Moderna',
                base_font_size INTEGER NOT NULL DEFAULT 16,
                notifications INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )


def get_or_create_default_user(default_name: str) -> dict[str, Any]:
    init_user_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, email, full_name, role, company FROM users WHERE email = ?",
            (DEFAULT_USER_EMAIL,),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO users (email, full_name, role, company)
                VALUES (?, ?, ?, ?)
                """,
                (DEFAULT_USER_EMAIL, default_name, DEFAULT_USER_ROLE, DEFAULT_USER_COMPANY),
            )
            user_id = conn.execute("SELECT last_insert_rowid() AS user_id").fetchone()["user_id"]
            conn.execute(
                """
                INSERT OR IGNORE INTO user_preferences (user_id)
                VALUES (?)
                """,
                (user_id,),
            )
            conn.execute(
                """
                INSERT INTO user_activity_log (user_id, action, details)
                VALUES (?, ?, ?)
                """,
                (user_id, "User initialized", "Creacion de usuario demo"),
            )
            row = conn.execute(
                "SELECT id, email, full_name, role, company FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        else:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_preferences (user_id)
                VALUES (?)
                """,
                (row["id"],),
            )

    return dict(row)


def load_user_preferences(user_id: int) -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT theme, accent, font, base_font_size, notifications
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return {
            "theme": "Dark",
            "accent": "Cyan",
            "font": "Moderna",
            "base_font_size": 16,
            "notifications": True,
        }

    return {
        "theme": row["theme"],
        "accent": row["accent"],
        "font": row["font"],
        "base_font_size": int(row["base_font_size"]),
        "notifications": bool(row["notifications"]),
    }


def save_user_profile(user_id: int, full_name: str, email: str, role: str, company: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE users
            SET full_name = ?, email = ?, role = ?, company = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (full_name.strip(), email.strip(), role.strip(), company.strip(), user_id),
        )


def save_user_preferences(
    user_id: int,
    theme: str,
    accent: str,
    font: str,
    base_font_size: int,
    notifications: bool,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (user_id, theme, accent, font, base_font_size, notifications, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                theme = excluded.theme,
                accent = excluded.accent,
                font = excluded.font,
                base_font_size = excluded.base_font_size,
                notifications = excluded.notifications,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, theme, accent, font, int(base_font_size), int(bool(notifications))),
        )


def log_user_activity(user_id: int, action: str, details: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_activity_log (user_id, action, details)
            VALUES (?, ?, ?)
            """,
            (user_id, action.strip(), details.strip()),
        )


def get_recent_activity(user_id: int, limit: int = 8) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT action, details, created_at
            FROM user_activity_log
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [dict(row) for row in rows]
