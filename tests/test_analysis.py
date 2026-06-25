from game_collector.analysis import compare_snapshots


def test_compare_snapshots_detects_rank_changes_entries_and_exits():
    previous = [
        {"app_id": "a", "title": "A", "rank": 1, "genre": "RPG"},
        {"app_id": "b", "title": "B", "rank": 2, "genre": "Puzzle"},
        {"app_id": "c", "title": "C", "rank": 3, "genre": "RPG"},
    ]
    current = [
        {"app_id": "b", "title": "B", "rank": 1, "genre": "Puzzle"},
        {"app_id": "a", "title": "A", "rank": 2, "genre": "RPG"},
        {"app_id": "d", "title": "D", "rank": 3, "genre": "Action"},
    ]

    result = compare_snapshots(current, previous)

    assert result["risers"][0]["app_id"] == "b"
    assert result["risers"][0]["rank_change"] == 1
    assert result["fallers"][0]["app_id"] == "a"
    assert result["new_entries"][0]["app_id"] == "d"
    assert result["exits"][0]["app_id"] == "c"
