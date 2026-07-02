from game_collector.database import connect, save_snapshots
from game_collector.insights import rank_movements, review_keyword_summary, survival_rows
from game_collector.models import GameSnapshot
from game_collector.reviews import import_review_jsonl

import json


def test_rank_movements_and_survival(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as connection:
        save_snapshots(
            connection,
            [
                GameSnapshot("2026-07-01_0600", 1, "a", "A", developer="Dev", genre="Puzzle"),
                GameSnapshot("2026-07-01_0600", 2, "b", "B", developer="Dev", genre="Puzzle"),
            ],
        )
        save_snapshots(
            connection,
            [
                GameSnapshot("2026-07-02_0600", 1, "b", "B", developer="Dev", genre="Puzzle"),
                GameSnapshot("2026-07-02_0600", 2, "c", "C", developer="New", genre="Arcade"),
            ],
        )
        movements = rank_movements(connection, "2026-07-02_0600", "2026-07-01_0600")
        survival = survival_rows(connection)

    assert any(row["app_id"] == "b" and row["status"] == "상승" for row in movements)
    assert any(row["app_id"] == "c" and row["status"] == "신규" for row in movements)
    assert any(row["app_id"] == "a" and row["status"] == "이탈" for row in movements)
    assert survival[0]["snapshots_seen"] >= 1


def test_review_keyword_summary_detects_issue_keywords(tmp_path):
    path = tmp_path / "reviews.jsonl"
    rows = [
        {
            "collectedAt": "2026-07-02T00:00:00Z",
            "rank": 1,
            "appId": "game.a",
            "gameTitle": "Game A",
            "reviewId": "review-1",
            "reviewerKey": "user-1",
            "identityMethod": "public_profile_token_hash",
            "userName": "u",
            "score": 1,
            "reviewText": "광고가 너무 많고 버그 때문에 튕김",
        }
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    with connect(tmp_path / "test.db") as connection:
        import_review_jsonl(connection, path)
        summary = review_keyword_summary(connection)

    issues = {(row["title"], row["issue"]) for row in summary["issue_rows"]}
    assert ("Game A", "광고") in issues
    assert ("Game A", "버그/오류") in issues
