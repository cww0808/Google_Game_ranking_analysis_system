from game_collector.database import connect, load_snapshot, save_snapshots
from game_collector.models import GameSnapshot


def test_snapshot_upsert(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as connection:
        save_snapshots(
            connection,
            [GameSnapshot("2026-06-25", 1, "com.example.game", "Example", score=4.1)],
        )
        save_snapshots(
            connection,
            [GameSnapshot("2026-06-25", 1, "com.example.game", "Example", score=4.5)],
        )
        rows = load_snapshot(connection, "2026-06-25")

    assert len(rows) == 1
    assert rows[0]["score"] == 4.5
