from __future__ import annotations

import sqlite3
from pathlib import Path

from game_collector.models import GameSnapshot
from game_collector.reviews import ensure_review_schema

SCHEMA = """
CREATE TABLE IF NOT EXISTS game_snapshots (
    collected_date TEXT NOT NULL,
    rank INTEGER NOT NULL CHECK(rank > 0),
    app_id TEXT NOT NULL,
    title TEXT NOT NULL,
    developer TEXT,
    genre TEXT,
    score REAL,
    ratings INTEGER,
    reviews INTEGER,
    installs TEXT,
    min_installs INTEGER,
    real_installs INTEGER,
    updated_at TEXT,
    icon_url TEXT,
    offers_iap INTEGER,
    price REAL,
    source_url TEXT,
    PRIMARY KEY (collected_date, app_id),
    UNIQUE (collected_date, rank)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_date_rank
ON game_snapshots(collected_date, rank);
"""

COLUMNS = tuple(GameSnapshot.__dataclass_fields__)


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    ensure_review_schema(connection)
    return connection


def save_snapshots(connection: sqlite3.Connection, snapshots: list[GameSnapshot]) -> None:
    if not snapshots:
        return
    placeholders = ", ".join("?" for _ in COLUMNS)
    update_clause = ", ".join(
        f"{column}=excluded.{column}" for column in COLUMNS if column not in {"collected_date", "app_id"}
    )
    sql = (
        f"INSERT INTO game_snapshots ({', '.join(COLUMNS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(collected_date, app_id) DO UPDATE SET {update_clause}"
    )
    rows = []
    for snapshot in snapshots:
        data = snapshot.to_dict()
        data["offers_iap"] = None if data["offers_iap"] is None else int(data["offers_iap"])
        rows.append(tuple(data[column] for column in COLUMNS))
    with connection:
        connection.executemany(sql, rows)


def available_dates(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT DISTINCT collected_date FROM game_snapshots ORDER BY collected_date DESC"
    ).fetchall()
    return [row["collected_date"] for row in rows]


def load_snapshot(connection: sqlite3.Connection, snapshot_date: str) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM game_snapshots WHERE collected_date=? ORDER BY rank", (snapshot_date,)
    ).fetchall()
    return [dict(row) for row in rows]
