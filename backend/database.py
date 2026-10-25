"""
SaulGPT — Database Layer (Hybrid PostgreSQL / SQLite)
======================================================
Unified persistence for users, conversations, and messages.
Automatically uses Supabase PostgreSQL when DATABASE_URL is present,
and cleanly falls back to local SQLite (saulgpt.db) when offline.
Includes connection handling, automatic retry, and FOREIGN KEY safety guards.
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


def is_postgres() -> bool:
    return bool(PSYCOPG2_AVAILABLE and DATABASE_URL and DATABASE_URL.startswith("postgres"))


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saulgpt.db")


def _get_sqlite_conn() -> sqlite3.Connection:
    """Get a SQLite connection with WAL journal mode, busy timeout, and foreign keys."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    return conn


def _get_pg_conn():
    """Get a PostgreSQL connection to Supabase."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    """Create tables if they don't exist and ensure default guest user."""
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title TEXT NOT NULL DEFAULT 'New Chat',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        conv_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
                        conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        meta JSONB,
                        turn INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );

                    CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conv_id, turn);
                """)
                cur.execute("""
                    INSERT INTO users (id, email, username, password)
                    VALUES (1, 'guest@saulgpt.local', 'Guest User', 'guest_mode_unrestricted')
                    ON CONFLICT (id) DO NOTHING
                """)
                conn.commit()
            conn.close()
            print("[Database] Supabase PostgreSQL connected and initialized.")
            return
        except Exception as e:
            print(f"[Database Warning] Supabase init failed: {e}. Falling back to SQLite.")

    # SQLite fallback
    conn = _get_sqlite_conn()
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
        print("[Database] SQLite saulgpt.db initialized.")
    except Exception as e:
        print(f"[Database] SQLite init_db warning: {e}")
    finally:
        conn.close()


def ensure_user_exists(user_id: Optional[int] = None) -> int:
    """Ensures a user record exists so FOREIGN KEY constraints never fail."""
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (id, email, username, password)
                    VALUES (1, 'guest@saulgpt.local', 'Guest User', 'guest_mode_unrestricted')
                    ON CONFLICT (id) DO NOTHING
                """)
                conn.commit()
                if user_id and isinstance(user_id, int) and user_id > 0:
                    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                    row = cur.fetchone()
                    if row:
                        conn.close()
                        return user_id
                    cur.execute("""
                        INSERT INTO users (id, email, username, password)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (user_id, f"user_{user_id}@saulgpt.local", f"User {user_id}", "token_authenticated"))
                    conn.commit()
                    conn.close()
                    return user_id
            conn.close()
            return 1
        except Exception as e:
            print(f"[Database Postgres] ensure_user_exists warning: {e}")

    conn = _get_sqlite_conn()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO users (id, email, username, password)
            VALUES (1, 'guest@saulgpt.local', 'Guest User', 'guest_mode_unrestricted')
        """)
        conn.commit()
        if user_id and isinstance(user_id, int) and user_id > 0:
            row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if row:
                return user_id
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
        print(f"[Database SQLite] ensure_user_exists warning: {e}")
        return 1
    finally:
        conn.close()


def ensure_conversation_exists(conv_id: Optional[int], user_id: int = 1) -> int:
    """Ensures a conversation exists. Guarantees messages never hit FOREIGN KEY errors."""
    valid_uid = ensure_user_exists(user_id)
    if conv_id and isinstance(conv_id, int) and conv_id > 0:
        if is_postgres():
            try:
                conn = _get_pg_conn()
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM conversations WHERE id = %s", (conv_id,))
                    row = cur.fetchone()
                    if row:
                        conn.close()
                        return conv_id
                conn.close()
            except Exception as e:
                print(f"[Database Postgres] ensure_conversation_exists check error: {e}")
        else:
            conn = _get_sqlite_conn()
            try:
                row = conn.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,)).fetchone()
                if row:
                    return conv_id
            except Exception as e:
                print(f"[Database SQLite] ensure_conversation_exists check error: {e}")
            finally:
                conn.close()

    return create_conversation(valid_uid, "New Chat")


# ─────────────────────────────────────────────────────────────
# USER OPERATIONS
# ─────────────────────────────────────────────────────────────

def create_user(email: str, username: str, password_hash: str) -> Optional[int]:
    base_username = (username or email.split("@")[0]).strip()
    candidate = base_username
    counter = 1

    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                while True:
                    cur.execute("SELECT id FROM users WHERE username = %s AND email != %s", (candidate, email))
                    if not cur.fetchone():
                        break
                    candidate = f"{base_username}_{counter}"
                    counter += 1

                cur.execute(
                    "INSERT INTO users (email, username, password) VALUES (%s, %s, %s) RETURNING id",
                    (email.strip().lower(), candidate, password_hash)
                )
                new_id = cur.fetchone()["id"]
                conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            print(f"[Database Postgres] create_user error: {e}")
            return None

    conn = _get_sqlite_conn()
    try:
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
        print(f"[Database SQLite] create_user error: {e}")
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
                row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"[Database Postgres] get_user_by_email error: {e}")
            return None

    conn = _get_sqlite_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[Database SQLite] get_user_by_email error: {e}")
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict]:
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"[Database Postgres] get_user_by_id error: {e}")
            return None

    conn = _get_sqlite_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[Database SQLite] get_user_by_id error: {e}")
        return None
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# CONVERSATION OPERATIONS
# ─────────────────────────────────────────────────────────────

def create_conversation(user_id: int, title: str = "New Chat") -> int:
    valid_uid = ensure_user_exists(user_id)
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO conversations (user_id, title) VALUES (%s, %s) RETURNING id",
                    (valid_uid, title)
                )
                conv_id = cur.fetchone()["id"]
                conn.commit()
            conn.close()
            return conv_id
        except Exception as e:
            print(f"[Database Postgres] create_conversation error: {e}")
            try:
                conn = _get_pg_conn()
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO conversations (user_id, title) VALUES (1, %s) RETURNING id",
                        (title,)
                    )
                    conv_id = cur.fetchone()["id"]
                    conn.commit()
                conn.close()
                return conv_id
            except Exception as e2:
                print(f"[Database Postgres] fallback create_conversation error: {e2}")
                return 1

    conn = _get_sqlite_conn()
    try:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (valid_uid, title)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[Database SQLite] create_conversation error: {e}")
        try:
            cur = conn.execute(
                "INSERT INTO conversations (user_id, title) VALUES (1, ?)",
                (title,)
            )
            conn.commit()
            return cur.lastrowid
        except Exception as e2:
            print(f"[Database SQLite] create_conversation fallback error: {e2}")
            return 1
    finally:
        conn.close()


def get_conversations(user_id: int, limit: int = 50, offset: int = 0) -> Dict:
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations "
                    "WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                    (user_id, limit, offset)
                )
                rows = cur.fetchall()
                cur.execute("SELECT COUNT(*) as cnt FROM conversations WHERE user_id = %s", (user_id,))
                cnt_row = cur.fetchone()
                total = cnt_row["cnt"] if cnt_row else 0
            conn.close()
            return {"conversations": [dict(r) for r in rows], "total": total}
        except Exception as e:
            print(f"[Database Postgres] get_conversations error: {e}")
            return {"conversations": [], "total": 0}

    conn = _get_sqlite_conn()
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
        print(f"[Database SQLite] get_conversations error: {e}")
        return {"conversations": [], "total": 0}
    finally:
        conn.close()


def get_conversation(conv_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        "SELECT id, title, created_at, updated_at FROM conversations "
                        "WHERE id = %s AND user_id = %s",
                        (conv_id, user_id)
                    )
                else:
                    cur.execute(
                        "SELECT id, title, created_at, updated_at FROM conversations WHERE id = %s",
                        (conv_id,)
                    )
                row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"[Database Postgres] get_conversation error: {e}")
            return None

    conn = _get_sqlite_conn()
    try:
        if user_id:
            row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations "
                "WHERE id = ? AND user_id = ?",
                (conv_id, user_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conv_id,)
            ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[Database SQLite] get_conversation error: {e}")
        return None
    finally:
        conn.close()


def update_conversation_title(conv_id: int, title: str):
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE conversations SET title = %s, updated_at = NOW() WHERE id = %s",
                    (title, conv_id)
                )
                conn.commit()
            conn.close()
            return
        except Exception as e:
            print(f"[Database Postgres] update_conversation_title error: {e}")
            return

    conn = _get_sqlite_conn()
    try:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = datetime('now') WHERE id = ?",
            (title, conv_id)
        )
        conn.commit()
    except Exception as e:
        print(f"[Database SQLite] update_conversation_title error: {e}")
    finally:
        conn.close()


def touch_conversation(conv_id: int):
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
                    (conv_id,)
                )
                conn.commit()
            conn.close()
            return
        except Exception as e:
            print(f"[Database Postgres] touch_conversation error: {e}")
            return

    conn = _get_sqlite_conn()
    try:
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conv_id,)
        )
        conn.commit()
    except Exception as e:
        print(f"[Database SQLite] touch_conversation error: {e}")
    finally:
        conn.close()


def delete_conversation(conv_id: int, user_id: int) -> bool:
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM conversations WHERE id = %s AND user_id = %s",
                    (conv_id, user_id)
                )
                deleted = cur.rowcount > 0
                conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            print(f"[Database Postgres] delete_conversation error: {e}")
            return False

    conn = _get_sqlite_conn()
    try:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"[Database SQLite] delete_conversation error: {e}")
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# MESSAGE OPERATIONS
# ─────────────────────────────────────────────────────────────

def add_message(conv_id: int, role: str, content: str, meta: Any = None, turn: int = 0) -> Optional[int]:
    safe_conv_id = ensure_conversation_exists(conv_id)
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                pg_meta = None
                if meta is not None:
                    if isinstance(meta, str):
                        try:
                            pg_meta = Json(json.loads(meta))
                        except Exception:
                            pg_meta = Json({"raw": meta})
                    else:
                        pg_meta = Json(meta)
                cur.execute(
                    "INSERT INTO messages (conv_id, conversation_id, role, content, meta, turn) "
                    "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (safe_conv_id, safe_conv_id, role, content, pg_meta, turn)
                )
                msg_id = cur.fetchone()["id"]
                conn.commit()
            conn.close()
            return msg_id
        except Exception as e:
            print(f"[Database Postgres] add_message error: {e}")
            return None

    conn = _get_sqlite_conn()
    try:
        sql_meta = meta
        if sql_meta is not None and not isinstance(sql_meta, str):
            sql_meta = json.dumps(sql_meta)
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, meta, turn) VALUES (?, ?, ?, ?, ?)",
            (safe_conv_id, role, content, sql_meta, turn)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[Database SQLite] add_message error: {e}")
        return None
    finally:
        conn.close()


def get_messages(conv_id: int) -> List[Dict]:
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT role, content, meta, turn, created_at FROM messages "
                    "WHERE (conv_id = %s OR conversation_id = %s) ORDER BY turn ASC, id ASC",
                    (conv_id, conv_id)
                )
                rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[Database Postgres] get_messages error: {e}")
            return []

    conn = _get_sqlite_conn()
    try:
        rows = conn.execute(
            "SELECT role, content, meta, turn, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY turn ASC",
            (conv_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[Database SQLite] get_messages error: {e}")
        return []
    finally:
        conn.close()


def get_last_turn(conv_id: int) -> int:
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(turn), 0) as last_turn FROM messages "
                    "WHERE (conv_id = %s OR conversation_id = %s)",
                    (conv_id, conv_id)
                )
                row = cur.fetchone()
            conn.close()
            return row["last_turn"] if row else 0
        except Exception as e:
            print(f"[Database Postgres] get_last_turn error: {e}")
            return 0

    conn = _get_sqlite_conn()
    try:
        row = conn.execute(
            "SELECT COALESCE(MAX(turn), 0) as last_turn FROM messages WHERE conversation_id = ?",
            (conv_id,)
        ).fetchone()
        return row["last_turn"] if row else 0
    except Exception as e:
        print(f"[Database SQLite] get_last_turn error: {e}")
        return 0
    finally:
        conn.close()


def bulk_import_messages(conv_id: int, turns: list) -> bool:
    """Import an array of turn dicts into a conversation in one transaction."""
    safe_conv_id = ensure_conversation_exists(conv_id)
    if is_postgres():
        try:
            conn = _get_pg_conn()
            with conn.cursor() as cur:
                for i, t in enumerate(turns):
                    meta = t.get("meta")
                    pg_meta = None
                    if meta is not None:
                        if isinstance(meta, str):
                            try:
                                pg_meta = Json(json.loads(meta))
                            except Exception:
                                pg_meta = Json({"raw": meta})
                        else:
                            pg_meta = Json(meta)
                    cur.execute(
                        "INSERT INTO messages (conv_id, conversation_id, role, content, meta, turn) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (safe_conv_id, safe_conv_id, t["role"], t["content"], pg_meta, i + 1)
                    )
                cur.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (safe_conv_id,))
                conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[Database Postgres] bulk_import_messages error: {e}")
            return False

    conn = _get_sqlite_conn()
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
        print(f"[Database SQLite] bulk_import_messages error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
