from __future__ import annotations

import argparse

from game_collector.database import connect
from game_collector.reviews import import_review_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl")
    parser.add_argument("--db", default="data/google_play_games.db")
    args = parser.parse_args()
    with connect(args.db) as connection:
        reviewers, reviews = import_review_jsonl(connection, args.jsonl)
    print(f"Review rows processed: {reviews}")
    print(f"Unique reviewer keys in database: {reviewers}")


if __name__ == "__main__":
    main()
