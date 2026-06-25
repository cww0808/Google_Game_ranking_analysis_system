from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(name="Malgun Gothic", bold=True, color="FFFFFF")
BODY_FONT = Font(name="Malgun Gothic", size=10)


def style_sheet(sheet, widths: dict[str, float], table_name: str) -> None:
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    for cell in sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center")
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = BODY_FONT
            cell.alignment = Alignment(vertical="top")
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    if sheet.max_row > 1:
        table = Table(displayName=table_name, ref=f"A1:{sheet.cell(1, sheet.max_column).column_letter}{sheet.max_row}")
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        sheet.add_table(table)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/google_play_games.db")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    connection = sqlite3.connect(args.db)
    connection.row_factory = sqlite3.Row

    workbook = Workbook()
    reviews_sheet = workbook.active
    reviews_sheet.title = "리뷰"
    users_sheet = workbook.create_sheet("사용자 관계")
    games_sheet = workbook.create_sheet("게임 요약")

    reviews_sheet.append(
        [
            "개발사", "게임명", "패키지명", "수집 당시 순위", "사용자 식별키",
            "닉네임", "별점", "평가글", "작성일", "도움 수", "앱 버전",
            "리뷰 ID", "프로필 이미지 URL", "식별 방식", "리뷰 URL",
        ]
    )
    review_rows = connection.execute(
        """
        SELECT
            gs.developer, gr.game_title, gr.app_id, gs.rank, gr.reviewer_key,
            gr.user_name_at_review, gr.score, gr.review_text, gr.review_date,
            gr.thumbs_up, gr.app_version, gr.review_id, gr.user_image_at_review,
            r.identity_method, gr.review_url
        FROM game_reviews gr
        JOIN reviewers r ON r.reviewer_key = gr.reviewer_key
        LEFT JOIN game_snapshots gs
          ON gs.app_id = gr.app_id AND gs.collected_date = ?
        ORDER BY COALESCE(gs.rank, 999), gr.review_date DESC
        """,
        (args.snapshot,),
    )
    for row in review_rows:
        reviews_sheet.append(list(row))

    users_sheet.append(
        [
            "사용자 식별키", "최근 닉네임", "식별 방식", "리뷰 수",
            "평가한 게임 수", "최초 리뷰일", "최근 리뷰일", "평가 게임 목록",
        ]
    )
    user_rows = connection.execute(
        """
        SELECT
            r.reviewer_key, r.latest_user_name, r.identity_method,
            COUNT(gr.review_id), COUNT(DISTINCT gr.app_id),
            MIN(gr.review_date), MAX(gr.review_date),
            GROUP_CONCAT(DISTINCT gr.game_title)
        FROM reviewers r
        JOIN game_reviews gr ON gr.reviewer_key = r.reviewer_key
        GROUP BY r.reviewer_key
        ORDER BY COUNT(gr.review_id) DESC, COUNT(DISTINCT gr.app_id) DESC
        """
    )
    for row in user_rows:
        users_sheet.append(list(row))

    games_sheet.append(
        [
            "순위", "개발사", "게임명", "패키지명", "수집 리뷰 수",
            "고유 사용자 수", "평균 별점", "1점 리뷰", "5점 리뷰",
        ]
    )
    game_rows = connection.execute(
        """
        SELECT
            gs.rank, gs.developer, gs.title, gs.app_id,
            COUNT(gr.review_id), COUNT(DISTINCT gr.reviewer_key),
            ROUND(AVG(gr.score), 2),
            SUM(CASE WHEN gr.score = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN gr.score = 5 THEN 1 ELSE 0 END)
        FROM game_snapshots gs
        LEFT JOIN game_reviews gr ON gr.app_id = gs.app_id
        WHERE gs.collected_date = ?
        GROUP BY gs.app_id, gs.rank, gs.developer, gs.title
        ORDER BY gs.rank
        """,
        (args.snapshot,),
    )
    for row in game_rows:
        games_sheet.append(list(row))

    style_sheet(
        reviews_sheet,
        {"A": 23, "B": 28, "C": 30, "D": 12, "E": 36, "F": 20, "G": 8, "H": 58, "I": 21, "J": 10, "K": 12, "L": 38, "M": 48, "N": 25, "O": 48},
        "ReviewsTable",
    )
    reviews_sheet.column_dimensions["H"].width = 58
    for cell in reviews_sheet["H"][1:]:
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    style_sheet(
        users_sheet,
        {"A": 36, "B": 20, "C": 25, "D": 10, "E": 14, "F": 21, "G": 21, "H": 65},
        "ReviewersTable",
    )
    users_sheet.conditional_formatting.add(
        f"D2:D{users_sheet.max_row}",
        DataBarRule(start_type="min", end_type="max", color="5B9BD5"),
    )

    style_sheet(
        games_sheet,
        {"A": 9, "B": 24, "C": 30, "D": 32, "E": 14, "F": 15, "G": 12, "H": 11, "I": 11},
        "GamesTable",
    )
    games_sheet.conditional_formatting.add(
        f"G2:G{games_sheet.max_row}",
        ColorScaleRule(
            start_type="min", start_color="F8696B",
            mid_type="percentile", mid_value=50, mid_color="FFEB84",
            end_type="max", end_color="63BE7B",
        ),
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    print(output)


if __name__ == "__main__":
    main()
