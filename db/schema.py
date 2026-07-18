"""
SQLite schema for Learn Agent.

Tables:
  topics         — what the user is learning
  ladder_levels  — 5-level learning ladder per topic
  sessions       — learning sessions (plan execution)
  exam_records   — quiz results with gap analysis
  notes          — user's learning notes
  review_queue   — spaced repetition schedule
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS topics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'active',  -- active | paused | completed
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ladder_levels (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id     INTEGER NOT NULL REFERENCES topics(id),
    level_num    INTEGER NOT NULL CHECK (level_num BETWEEN 1 AND 5),
    name         TEXT NOT NULL,
    concepts     TEXT NOT NULL,  -- JSON array of concept strings
    milestone    TEXT NOT NULL,  -- "what you can do after this level"
    status       TEXT NOT NULL DEFAULT 'locked',  -- locked | active | completed
    completed_at TEXT,
    UNIQUE(topic_id, level_num)
);

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id    INTEGER NOT NULL REFERENCES topics(id),
    session_num INTEGER NOT NULL,
    objective   TEXT NOT NULL,
    concepts    TEXT,   -- JSON array
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending | active | completed
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(topic_id, session_num)
);

CREATE TABLE IF NOT EXISTS exam_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id     INTEGER NOT NULL REFERENCES topics(id),
    question     TEXT NOT NULL,
    user_answer  TEXT,
    score        INTEGER CHECK (score BETWEEN 1 AND 5),
    gap_analysis TEXT,   -- what the user didn't understand
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id       INTEGER REFERENCES topics(id),
    content        TEXT NOT NULL,
    tags           TEXT,  -- JSON array
    source_workflow TEXT, -- which workflow produced this note
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS review_queue (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id       INTEGER NOT NULL REFERENCES topics(id),
    concept        TEXT NOT NULL,
    last_reviewed  TEXT,
    next_review    TEXT NOT NULL,
    mastery_level  INTEGER NOT NULL DEFAULT 1,  -- 1–5
    review_count   INTEGER NOT NULL DEFAULT 0
);
"""
