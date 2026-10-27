import json, os
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
DSN = os.getenv("DATABASE_URL", "")

SCHEMA = """
         CREATE TABLE IF NOT EXISTS query_log (
                                                  id        BIGSERIAL PRIMARY KEY,
                                                  asked_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
             question  TEXT NOT NULL,
             route     TEXT NOT NULL,
             answer    TEXT,
             seconds   REAL,
             sources   JSONB
             );
         CREATE INDEX IF NOT EXISTS idx_query_log_asked_at ON query_log (asked_at DESC);

         CREATE TABLE IF NOT EXISTS calendar_actions (
                                                         id          BIGSERIAL PRIMARY KEY,
                                                         created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
             title       TEXT NOT NULL,
             start_time  TIMESTAMPTZ NOT NULL,
             minutes     INT NOT NULL,
             status      TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled', 'failed')),
             link        TEXT
             );

         CREATE TABLE IF NOT EXISTS email_drafts (
                                                     id          BIGSERIAL PRIMARY KEY,
                                                     created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
             to_addr     TEXT NOT NULL,
             subject     TEXT NOT NULL
             );

         CREATE TABLE IF NOT EXISTS documents (
                                                  filename    TEXT PRIMARY KEY,
                                                  chunks      INT NOT NULL,
                                                  indexed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
             ); \
        """

def _exec(sql, params=None, fetch=False):
    """Run one statement. Never raises, so the app keeps working if the DB is down."""
    if not DSN:
        return None
    try:
        with psycopg.connect(DSN, connect_timeout=3, row_factory=dict_row) as conn:
            cur = conn.execute(sql, params)
            return cur.fetchall() if fetch else True
    except Exception as e:
        print(f"[db] {e}")
        return None

def init():
    return _exec(SCHEMA)

def log_query(question, route, answer, seconds, sources):
    _exec("INSERT INTO query_log (question, route, answer, seconds, sources) "
          "VALUES (%s, %s, %s, %s, %s::jsonb)",
          (question, route, answer, round(seconds, 2), json.dumps(sources)))

def log_event(title, start_iso, minutes, status, link=None):
    start = datetime.fromisoformat(start_iso).astimezone()
    _exec("INSERT INTO calendar_actions (title, start_time, minutes, status, link) "
          "VALUES (%s, %s, %s, %s, %s)", (title, start, minutes, status, link))

def log_draft(to_addr, subject):
    _exec("INSERT INTO email_drafts (to_addr, subject) VALUES (%s, %s)", (to_addr, subject))

def upsert_documents(counts):
    for name, n in counts.items():
        _exec("INSERT INTO documents (filename, chunks) VALUES (%s, %s) "
              "ON CONFLICT (filename) DO UPDATE SET chunks = EXCLUDED.chunks, indexed_at = now()",
              (name, n))
    _exec("DELETE FROM documents WHERE NOT (filename = ANY(%s))", (list(counts),))

def recent_queries(n=10):
    return _exec("SELECT to_char(asked_at, 'DD Mon HH24:MI') AS asked, route, question, seconds "
                 "FROM query_log ORDER BY asked_at DESC LIMIT %s", (n,), fetch=True) or []