from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REVIEW_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviewers (
    reviewer_key TEXT PRIMARY KEY,
    latest_user_name TEXT,
    latest_user_image TEXT,
    identity_method TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_reviews (
    review_id TEXT PRIMARY KEY,
    app_id TEXT NOT NULL,
    game_title TEXT NOT NULL,
    ranking_at_collection INTEGER,
    reviewer_key TEXT NOT NULL,
    user_name_at_review TEXT,
    user_image_at_review TEXT,
    score INTEGER,
    review_text TEXT,
    review_date TEXT,
    thumbs_up INTEGER NOT NULL DEFAULT 0,
    app_version TEXT,
    reply_text TEXT,
    reply_date TEXT,
    review_url TEXT,
    collected_at TEXT NOT NULL,
    FOREIGN KEY (reviewer_key) REFERENCES reviewers(reviewer_key)
);

CREATE INDEX IF NOT EXISTS idx_reviews_game_title ON game_reviews(game_title);
CREATE INDEX IF NOT EXISTS idx_reviews_app_id ON game_reviews(app_id);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewer ON game_reviews(reviewer_key);
CREATE INDEX IF NOT EXISTS idx_reviews_date ON game_reviews(review_date);
"""


def ensure_review_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(REVIEW_SCHEMA)


def import_review_jsonl(connection: sqlite3.Connection, path: str | Path) -> tuple[int, int]:
    ensure_review_schema(connection)
    reviewer_count = 0
    review_count = 0
    with Path(path).open(encoding="utf-8") as stream, connection:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            connection.execute(
                """
                INSERT INTO reviewers (
                    reviewer_key, latest_user_name, latest_user_image, identity_method,
                    first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(reviewer_key) DO UPDATE SET
                    latest_user_name=excluded.latest_user_name,
                    latest_user_image=excluded.latest_user_image,
                    last_seen_at=MAX(reviewers.last_seen_at, excluded.last_seen_at)
                """,
                (
                    row["reviewerKey"],
                    row.get("userName"),
                    row.get("userImage"),
                    row["identityMethod"],
                    row["collectedAt"],
                    row["collectedAt"],
                ),
            )
            reviewer_count += 1
            before = connection.total_changes
            connection.execute(
                """
                INSERT INTO game_reviews (
                    review_id, app_id, game_title, ranking_at_collection, reviewer_key,
                    user_name_at_review, user_image_at_review, score, review_text,
                    review_date, thumbs_up, app_version, reply_text, reply_date,
                    review_url, collected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET
                    game_title=excluded.game_title,
                    ranking_at_collection=excluded.ranking_at_collection,
                    reviewer_key=excluded.reviewer_key,
                    user_name_at_review=excluded.user_name_at_review,
                    user_image_at_review=excluded.user_image_at_review,
                    score=excluded.score,
                    review_text=excluded.review_text,
                    review_date=excluded.review_date,
                    thumbs_up=excluded.thumbs_up,
                    app_version=excluded.app_version,
                    reply_text=excluded.reply_text,
                    reply_date=excluded.reply_date,
                    review_url=excluded.review_url,
                    collected_at=excluded.collected_at
                """,
                (
                    row["reviewId"],
                    row["appId"],
                    row["gameTitle"],
                    row.get("rank"),
                    row["reviewerKey"],
                    row.get("userName"),
                    row.get("userImage"),
                    row.get("score"),
                    row.get("reviewText"),
                    row.get("reviewDate"),
                    row.get("thumbsUp", 0),
                    row.get("appVersion"),
                    row.get("replyText"),
                    row.get("replyDate"),
                    row.get("reviewUrl"),
                    row["collectedAt"],
                ),
            )
            if connection.total_changes > before:
                review_count += 1
    unique_reviewers = connection.execute("SELECT COUNT(*) FROM reviewers").fetchone()[0]
    return unique_reviewers, review_count
