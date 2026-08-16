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



def test_korean_keyword_normalization_merges_particles_and_aliases():
    from game_collector.insights import _tokens

    tokens = _tokens("광고 광고가 광고를 게임이 게임은 게임을 재밌어요 재미있어요 재밋어요 튕겨요 팅김 오류 에러")

    assert tokens.count("광고") == 3
    assert "게임" not in tokens
    assert tokens.count("재미") >= 3
    assert tokens.count("튕김") >= 2
    assert tokens.count("버그") >= 2



def test_review_keyword_summary_returns_game_issue_top3(tmp_path):
    path = tmp_path / "reviews_top3.jsonl"
    rows = [
        {
            "collectedAt": "2026-07-02T00:00:00Z",
            "rank": 1,
            "appId": "game.top3",
            "gameTitle": "Top3 Game",
            "reviewId": "review-ad-1",
            "reviewerKey": "user-ad-1",
            "identityMethod": "public_profile_token_hash",
            "userName": "u1",
            "score": 1,
            "reviewText": "광고가 너무 많아요",
        },
        {
            "collectedAt": "2026-07-02T00:00:00Z",
            "rank": 1,
            "appId": "game.top3",
            "gameTitle": "Top3 Game",
            "reviewId": "review-ad-2",
            "reviewerKey": "user-ad-2",
            "identityMethod": "public_profile_token_hash",
            "userName": "u2",
            "score": 1,
            "reviewText": "광고를 계속 봐야 합니다",
        },
        {
            "collectedAt": "2026-07-02T00:00:00Z",
            "rank": 1,
            "appId": "game.top3",
            "gameTitle": "Top3 Game",
            "reviewId": "review-bug",
            "reviewerKey": "user-bug",
            "identityMethod": "public_profile_token_hash",
            "userName": "u3",
            "score": 1,
            "reviewText": "버그 때문에 튕김",
        },
        {
            "collectedAt": "2026-07-02T00:00:00Z",
            "rank": 1,
            "appId": "game.top3",
            "gameTitle": "Top3 Game",
            "reviewId": "review-pay",
            "reviewerKey": "user-pay",
            "identityMethod": "public_profile_token_hash",
            "userName": "u4",
            "score": 2,
            "reviewText": "과금 유도가 심합니다",
        },
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    with connect(tmp_path / "test.db") as connection:
        import_review_jsonl(connection, path)
        summary = review_keyword_summary(connection)

    ranked = [row for row in summary["game_issue_rank_rows"] if row["title"] == "Top3 Game"][0]
    assert ranked["issue_1"] == "광고"
    assert ranked["issue_1_count"] == 2
    assert ranked["issue_2"] in {"과금/결제", "버그/오류"}
    assert ranked["issue_3"] in {"과금/결제", "버그/오류"}
