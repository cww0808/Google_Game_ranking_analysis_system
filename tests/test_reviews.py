import json

from game_collector.database import connect
from game_collector.reviews import import_review_jsonl


def test_same_reviewer_key_can_have_multiple_reviews(tmp_path):
    path = tmp_path / "reviews.jsonl"
    rows = [
        {
            "collectedAt": "2026-06-25T00:00:00Z",
            "rank": 1,
            "appId": "game.a",
            "gameTitle": "Game A",
            "reviewId": "review-1",
            "reviewerKey": "user-key",
            "identityMethod": "public_profile_token_hash",
            "userName": "same name",
            "reviewText": "first",
        },
        {
            "collectedAt": "2026-06-25T00:00:00Z",
            "rank": 2,
            "appId": "game.b",
            "gameTitle": "Game B",
            "reviewId": "review-2",
            "reviewerKey": "user-key",
            "identityMethod": "public_profile_token_hash",
            "userName": "same name",
            "reviewText": "second",
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    with connect(tmp_path / "test.db") as connection:
        reviewers, _ = import_review_jsonl(connection, path)
        review_count = connection.execute("SELECT COUNT(*) FROM game_reviews").fetchone()[0]

    assert reviewers == 1
    assert review_count == 2
