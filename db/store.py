"""
CRUD operations for Learn Agent's SQLite database.
"""

import sqlite3
import json
import os
from pathlib import Path


def get_db_path() -> str:
    """Resolve DB path from env or default."""
    db_path = os.getenv("DATABASE_PATH", "data/learn-agent.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    from db.schema import SCHEMA_SQL
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


# ── Topics ──

def create_topic(name: str, description: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO topics (name, description) VALUES (?, ?)",
        (name, description)
    )
    conn.commit()
    topic_id = cur.lastrowid
    conn.close()
    return topic_id


def get_topic(topic_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_topic() -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM topics WHERE status = 'active' ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Ladder ──

def set_ladder(topic_id: int, levels: list[dict]) -> None:
    """Replace ladder for a topic. `levels` is a list of {level_num, name, concepts, milestone}."""
    conn = get_conn()
    conn.execute("DELETE FROM ladder_levels WHERE topic_id = ?", (topic_id,))
    for lv in levels:
        conn.execute(
            "INSERT INTO ladder_levels (topic_id, level_num, name, concepts, milestone, status) "
            "VALUES (?, ?, ?, ?, ?, 'locked')",
            (topic_id, lv["level_num"], lv["name"],
             json.dumps(lv.get("concepts", []), ensure_ascii=False),
             lv.get("milestone", ""))
        )
    # Unlock first level
    conn.execute(
        "UPDATE ladder_levels SET status = 'active' "
        "WHERE topic_id = ? AND level_num = 1", (topic_id,)
    )
    conn.commit()
    conn.close()


def get_ladder(topic_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM ladder_levels WHERE topic_id = ? ORDER BY level_num",
        (topic_id,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["concepts"] = json.loads(d.get("concepts", "[]"))
        result.append(d)
    return result


# ── Context (for injection into system prompt) ──

def get_learning_context(topic_id: int) -> dict:
    """Build a context dict summarizing everything the agent needs to know
    about the user's current learning state."""
    conn = get_conn()

    topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
    if not topic:
        conn.close()
        return {}

    ladder = conn.execute(
        "SELECT * FROM ladder_levels WHERE topic_id = ? ORDER BY level_num",
        (topic_id,)
    ).fetchall()

    # Find current active level
    active_level = None
    for lv in ladder:
        if lv["status"] == "active":
            active_level = dict(lv)
            active_level["concepts"] = json.loads(lv["concepts"] or "[]")
            break

    # Recent exam gaps
    gaps = conn.execute(
        "SELECT question, gap_analysis FROM exam_records "
        "WHERE topic_id = ? AND gap_analysis IS NOT NULL "
        "ORDER BY created_at DESC LIMIT 3",
        (topic_id,)
    ).fetchall()

    # Due reviews
    due = conn.execute(
        "SELECT concept FROM review_queue "
        "WHERE topic_id = ? AND next_review <= datetime('now')",
        (topic_id,)
    ).fetchall()

    conn.close()

    return {
        "topic_name": topic["name"],
        "topic_status": topic["status"],
        "active_level": active_level,
        "ladder": [
            {
                "level_num": lv["level_num"],
                "name": lv["name"],
                "status": lv["status"],
                "concepts": json.loads(lv["concepts"] or "[]"),
            }
            for lv in ladder
        ],
        "recent_gaps": [dict(g) for g in gaps],
        "due_reviews": [d["concept"] for d in due],
    }
