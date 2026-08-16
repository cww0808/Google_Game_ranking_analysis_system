from __future__ import annotations

import argparse
from pathlib import Path

from game_collector.insights import write_weekly_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a weekly Google Play game meta-analysis report.")
    parser.add_argument("--db", default="data/google_play_games.db")
    parser.add_argument("--output", default=None)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--end-snapshot", default=None)
    args = parser.parse_args()

    output = args.output
    if output is None:
        suffix = args.end_snapshot or "latest"
        output = f"reports/weekly_meta_report_{suffix}.md"
    path = write_weekly_report(
        db_path=args.db,
        output_path=output,
        days=args.days,
        end_snapshot=args.end_snapshot,
    )
    print(Path(path))


if __name__ == "__main__":
    main()
