from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from game_collector.analysis import compare_snapshots
from game_collector.collector import collect_snapshots, discover_game_ids
from game_collector.database import available_dates, connect, load_snapshot, save_snapshots
from game_collector.report import write_markdown_report


def _read_package_file(path: str) -> list[str]:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        with source.open(encoding="utf-8-sig", newline="") as stream:
            rows = csv.DictReader(stream)
            return [row["app_id"].strip() for row in rows if row.get("app_id")]
    return [line.strip() for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(args: argparse.Namespace) -> int:
    snapshot_date = args.date or date.today().isoformat()
    app_ids = (
        _read_package_file(args.package_file)
        if args.package_file
        else discover_game_ids(args.country.upper(), args.lang, args.limit)
    )
    print(f"Discovered {len(app_ids)} game package IDs.")
    snapshots, failures = collect_snapshots(
        app_ids,
        collected_date=snapshot_date,
        country=args.country.lower(),
        lang=args.lang,
        delay_seconds=args.delay,
    )
    if not snapshots:
        print("Collection failed for every app.", file=sys.stderr)
        return 2

    with connect(args.db) as connection:
        save_snapshots(connection, snapshots)
        dates = available_dates(connection)
        current = load_snapshot(connection, snapshot_date)
        previous_date = next((item for item in dates if item < snapshot_date), None)
        previous = load_snapshot(connection, previous_date) if previous_date else []
        analysis = compare_snapshots(current, previous) if previous else None

    report_path = Path(args.reports) / f"{snapshot_date}.md"
    write_markdown_report(report_path, snapshot_date, previous_date, current, analysis)
    print(f"Saved {len(snapshots)} rows to {args.db}")
    print(f"Report: {report_path}")
    if failures:
        print(f"Warnings: {len(failures)} apps failed.", file=sys.stderr)
        for app_id, message in failures[:10]:
            print(f"  - {app_id}: {message}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect Korean Google Play game snapshots.")
    parser.add_argument("--country", default="KR")
    parser.add_argument("--lang", default="ko")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--date", help="Snapshot date in YYYY-MM-DD format")
    parser.add_argument("--db", default="data/google_play_games.db")
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--package-file", help="Optional TXT or CSV(app_id column) ranking input")
    return parser


def main() -> None:
    raise SystemExit(run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
