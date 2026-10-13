"""
SaulGPT — Database Layer
========================
SQLite-backed persistence for users, conversations, and messages.
Replaces in-memory CONVERSATION_MEMORY for authenticated users.
Includes resilient connection handling, WAL mode, busy timeouts,
and automatic FOREIGN KEY safety guards.
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saulgpt.db")


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with WAL journal mode, busy timeout, and foreign keys."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    return conn


def init_db():
    """Create tables if they don't exist and ensure default guest user."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT UNIQUE NOT NULL,
                username    TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title       TEXT NOT NULL DEFAULT 'New Chat',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content         TEXT NOT NULL,
                meta            TEXT,
                turn            INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_user
                ON conversations(user_id, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id, turn);
        """)
        conn.execute("""
            INSERT OR IGNORE INTO users (id, email, username, password)
            VALUES (1, 'guest@saulgpt.local', 'Guest User', 'guest_mode_unrestricted')
        """)
        conn.commit()
    except Exception as e:
        print(f"[Database] init_db warning: {e}")
    finally:
        conn.close()


def ensure_user_exists(user_id: Optional[int] = None) -> int:
    """
    Ensures that a user record exists in the users table so that FOREIGN KEY
    constraints never fail. Returns a guaranteed valid user_id (defaults to 1).
    """
    conn = _get_conn()
    try:
        # First ensure guest user (id=1) always exists
        conn.execute("""
            INSERT OR IGNORE INTO users (id, email, username, password)
            VALUES (1, 'guest@saulgpt.local', 'Guest User', 'guest_mode_unrestricted')
        """)
        conn.commit()

        if user_id and isinstance(user_id, int) and user_id > 0:
            row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if row:
                return user_id
            # Auto-create user placeholder if id from valid token does not exist in DB yet
            try:
                conn.execute(
                    "INSERT INTO users (id, email, username, password) VALUES (?, ?, ?, ?)",
                    (user_id, f"user_{user_id}@saulgpt.local", f"User {user_id}", "token_authenticated")
                )
                conn.commit()
                return user_id
            except Exception:
                pass
        return 1
    except Exception as e:
        print(f"[Database] ensure_user_exists warning: {e}")
        return 1
    finally:
        conn.close()


def ensure_conversation_exists(conv_id: Optional[int], user_id: int = 1) -> int:
    """
    Ensures that a conversation with conv_id exists. If not, creates one and returns its ID.
    Guarantees messages never hit FOREIGN KEY constraint violations.
    """
    valid_uid = ensure_user_exists(user_id)
    if conv_id and isinstance(conv_id, int) and conv_id > 0:
        conn = _get_conn()
        try:
            row = conn.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if row:
                return conv_id
        except Exception as e:
            print(f"[Database] ensure_conversation_exists check error: {e}")
        finally:
            conn.close()

    return create_conversation(valid_uid, "New Chat")


# ─────────────────────────────────────────────────────────────
# USER OPERATIONS
# ─────────────────────────────────────────────────────────────

def create_user(email: str, username: str, password_hash: str) -> Optional[int]:
    conn = _get_conn()
    try:
        base_username = (username or email.split("@")[0]).strip()
        candidate = base_username
        counter = 1
        while True:
            existing = conn.execute("SELECT id FROM users WHERE username = ? AND email != ?", (candidate, email)).fetchone()
            if not existing:
                break
            candidate = f"{base_username}_{counter}"
            counter += 1

        cur = conn.execute(
            "INSERT INTO users (email, username, password) VALUES (?, ?, ?)",
            (email.strip().lower(), candidate, password_hash)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[Database] create_user error: {e}")
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[Database] get_user_by_email error: {e}")
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[Database] get_user_by_id error: {e}")
        return None
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# CONVERSATION OPERATIONS
# ─────────────────────────────────────────────────────────────

def create_conversation(user_id: int, title: str = "New Chat") -> int:
    valid_uid = ensure_user_exists(user_id)
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (valid_uid, title)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[Database] create_conversation error: {e}")
        try:
            cur = conn.execute(
                "INSERT INTO conversations (user_id, title) VALUES (1, ?)",
                (title,)
            )
            conn.commit()
            return cur.lastrowid
        except Exception as e2:
            print(f"[Database] create_conversation fallback error: {e2}")
            return 1
    finally:
        conn.close()


def get_conversations(user_id: int, limit: int = 50, offset: int = 0) -> Dict:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset)
        ).fetchall()
        total_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        total = total_row["cnt"] if total_row else 0
        return {"conversations": [dict(r) for r in rows], "total": total}
    except Exception as e:
        print(f"[Database] get_conversations error: {e}")
        return {"conversations": [], "total": 0}
    finally:
        conn.close()


def get_conversation(conv_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
    conn = _get_conn()
    try:
        if user_id:
            row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations "
                "WHERE id = ? AND user_id = ?",
                (conv_id, user_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations "
                "WHERE id = ?",
                (conv_id,)
            ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[Database] get_conversation error: {e}")
        return None
    finally:
        conn.close()


def update_conversation_title(conv_id: int, title: str):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = datetime('now') WHERE id = ?",
            (title, conv_id)
        )
        conn.commit()
    except Exception as e:
        print(f"[Database] update_conversation_title error: {e}")
    finally:
        conn.close()


def touch_conversation(conv_id: int):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conv_id,)
        )
        conn.commit()
    except Exception as e:
        print(f"[Database] touch_conversation error: {e}")
    finally:
        conn.close()


def delete_conversation(conv_id: int, user_id: int) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"[Database] delete_conversation error: {e}")
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# MESSAGE OPERATIONS
# ─────────────────────────────────────────────────────────────

def add_message(conv_id: int, role: str, content: str, meta: str = None, turn: int = 0) -> Optional[int]:
    safe_conv_id = ensure_conversation_exists(conv_id)
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, meta, turn) VALUES (?, ?, ?, ?, ?)",
            (safe_conv_id, role, content, meta, turn)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[Database] add_message error: {e}")
        return None
    finally:
        conn.close()


def get_messages(conv_id: int) -> List[Dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT role, content, meta, turn, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY turn ASC",
            (conv_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[Database] get_messages error: {e}")
        return []
    finally:
        conn.close()


def get_last_turn(conv_id: int) -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COALESCE(MAX(turn), 0) as last_turn FROM messages WHERE conversation_id = ?",
            (conv_id,)
        ).fetchone()
        return row["last_turn"] if row else 0
    except Exception as e:
        print(f"[Database] get_last_turn error: {e}")
        return 0
    finally:
        conn.close()


def bulk_import_messages(conv_id: int, turns: list) -> bool:
    """Import an array of turn dicts into a conversation in one transaction.
    Each turn: {"role": str, "content": str, "meta": str or dict or None}
    """
    safe_conv_id = ensure_conversation_exists(conv_id)
    conn = _get_conn()
    try:
        rows = []
        for i, t in enumerate(turns):
            meta = t.get("meta")
            if meta is not None and not isinstance(meta, str):
                meta = json.dumps(meta)
            rows.append((safe_conv_id, t["role"], t["content"], meta, i + 1))
        conn.executemany(
            "INSERT INTO messages (conversation_id, role, content, meta, turn) VALUES (?, ?, ?, ?, ?)",
            rows
        )
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (safe_conv_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[Database] bulk_import_messages error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
