from __future__ import annotations

from collections import Counter


def compare_snapshots(current: list[dict], previous: list[dict]) -> dict:
    current_by_id = {row["app_id"]: row for row in current}
    previous_by_id = {row["app_id"]: row for row in previous}

    changes = []
    for app_id, row in current_by_id.items():
        old = previous_by_id.get(app_id)
        rank_change = None if old is None else old["rank"] - row["rank"]
        changes.append({**row, "previous_rank": old["rank"] if old else None, "rank_change": rank_change})

    new_entries = [row for row in changes if row["previous_rank"] is None]
    exits = [row for app_id, row in previous_by_id.items() if app_id not in current_by_id]
    risers = sorted(
        [row for row in changes if (row["rank_change"] or 0) > 0],
        key=lambda row: row["rank_change"],
        reverse=True,
    )
    fallers = sorted(
        [row for row in changes if (row["rank_change"] or 0) < 0],
        key=lambda row: row["rank_change"],
    )
    current_genres = Counter(row.get("genre") or "Unknown" for row in current)
    previous_genres = Counter(row.get("genre") or "Unknown" for row in previous)
    genres = [
        {
            "genre": genre,
            "current": current_genres[genre],
            "previous": previous_genres[genre],
            "change": current_genres[genre] - previous_genres[genre],
        }
        for genre in sorted(current_genres.keys() | previous_genres.keys())
    ]
    return {
        "changes": changes,
        "new_entries": new_entries,
        "exits": exits,
        "risers": risers,
        "fallers": fallers,
        "genres": genres,
    }
