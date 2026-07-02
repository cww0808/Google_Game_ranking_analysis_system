from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]{2,}")
STOPWORDS = {
    "게임", "진짜", "너무", "정말", "그냥", "계속", "하고", "하면", "해서", "근데", "있어요", "합니다",
    "그리고", "하지만", "이거", "저도", "제가", "없는", "있는", "좋아요", "같아요", "입니다", "ㅋㅋ",
    "the", "and", "for", "this", "that", "with", "game", "good", "very",
}

ISSUE_KEYWORDS = {
    "광고": ["광고", "ads", "ad"],
    "과금/결제": ["과금", "결제", "현질", "유료", "돈", "구매", "환불", "뽑기", "가챠"],
    "버그/오류": ["버그", "오류", "에러", "렉", "튕김", "튕겨", "멈춤", "먹통", "접속", "로딩", "다운"],
    "난이도/밸런스": ["어려", "난이도", "밸런스", "사기", "매칭", "억까", "불가능"],
    "조작/UX": ["조작", "터치", "불편", "UI", "ux", "컨트롤", "화면"],
    "업데이트": ["업데이트", "패치", "너프", "버프", "바뀌", "변경"],
}

POSITIVE_KEYWORDS = ["재밌", "재미", "좋", "추천", "최고", "귀엽", "간단", "만족", "힐링", "중독"]
NEGATIVE_KEYWORDS = ["별로", "최악", "짜증", "삭제", "싫", "노잼", "불편", "화남", "망겜", "실망"]


def connect_readonly(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def list_snapshots(connection: sqlite3.Connection) -> list[str]:
    return [
        row["collected_date"]
        for row in connection.execute(
            "SELECT DISTINCT collected_date FROM game_snapshots ORDER BY collected_date"
        )
    ]


def latest_snapshot(connection: sqlite3.Connection) -> str | None:
    row = connection.execute("SELECT MAX(collected_date) AS snapshot FROM game_snapshots").fetchone()
    return row["snapshot"] if row and row["snapshot"] else None


def previous_snapshot(connection: sqlite3.Connection, snapshot: str) -> str | None:
    row = connection.execute(
        "SELECT MAX(collected_date) AS snapshot FROM game_snapshots WHERE collected_date < ?",
        (snapshot,),
    ).fetchone()
    return row["snapshot"] if row and row["snapshot"] else None


def rank_movements(
    connection: sqlite3.Connection,
    current_snapshot: str | None = None,
    base_snapshot: str | None = None,
) -> list[dict]:
    current_snapshot = current_snapshot or latest_snapshot(connection)
    if not current_snapshot:
        return []
    base_snapshot = base_snapshot or previous_snapshot(connection, current_snapshot)
    if not base_snapshot:
        rows = connection.execute(
            """
            SELECT '신규' AS status, rank AS current_rank, NULL AS previous_rank, NULL AS rank_change,
                   developer, title, app_id, genre, score, ratings, installs
            FROM game_snapshots
            WHERE collected_date = ?
            ORDER BY rank
            """,
            (current_snapshot,),
        ).fetchall()
        return [dict(row) for row in rows]

    rows = connection.execute(
        """
        WITH current AS (
            SELECT * FROM game_snapshots WHERE collected_date = ?
        ),
        previous AS (
            SELECT * FROM game_snapshots WHERE collected_date = ?
        )
        SELECT
            CASE
                WHEN c.app_id IS NULL THEN '이탈'
                WHEN p.app_id IS NULL THEN '신규'
                WHEN p.rank > c.rank THEN '상승'
                WHEN p.rank < c.rank THEN '하락'
                ELSE '유지'
            END AS status,
            c.rank AS current_rank,
            p.rank AS previous_rank,
            CASE WHEN c.rank IS NULL OR p.rank IS NULL THEN NULL ELSE p.rank - c.rank END AS rank_change,
            COALESCE(c.developer, p.developer) AS developer,
            COALESCE(c.title, p.title) AS title,
            COALESCE(c.app_id, p.app_id) AS app_id,
            COALESCE(c.genre, p.genre) AS genre,
            COALESCE(c.score, p.score) AS score,
            COALESCE(c.ratings, p.ratings) AS ratings,
            COALESCE(c.installs, p.installs) AS installs
        FROM current c
        LEFT JOIN previous p ON p.app_id = c.app_id
        UNION ALL
        SELECT
            '이탈' AS status,
            NULL AS current_rank,
            p.rank AS previous_rank,
            NULL AS rank_change,
            p.developer,
            p.title,
            p.app_id,
            p.genre,
            p.score,
            p.ratings,
            p.installs
        FROM previous p
        LEFT JOIN current c ON c.app_id = p.app_id
        WHERE c.app_id IS NULL
        """,
        (current_snapshot, base_snapshot),
    ).fetchall()
    order = {"상승": 0, "하락": 1, "신규": 2, "이탈": 3, "유지": 4}
    result = [dict(row) for row in rows]
    result.sort(
        key=lambda row: (
            order.get(row["status"], 9),
            -(row["rank_change"] or -999) if row["status"] == "상승" else (row["rank_change"] or 999),
            row["current_rank"] or 999,
            row["previous_rank"] or 999,
        )
    )
    return result


def survival_rows(connection: sqlite3.Connection) -> list[dict]:
    latest = latest_snapshot(connection)
    if not latest:
        return []
    current_ids = {
        row["app_id"]
        for row in connection.execute("SELECT app_id FROM game_snapshots WHERE collected_date = ?", (latest,))
    }
    ranks: dict[str, list[int]] = defaultdict(list)
    meta: dict[str, dict] = {}
    first_last: dict[str, list[str]] = {}
    for row in connection.execute(
        """
        SELECT app_id, title, developer, genre, collected_date, rank
        FROM game_snapshots
        ORDER BY app_id, collected_date
        """
    ):
        app_id = row["app_id"]
        ranks[app_id].append(row["rank"])
        meta.setdefault(app_id, {
            "app_id": app_id,
            "title": row["title"],
            "developer": row["developer"],
            "genre": row["genre"],
        })
        if app_id not in first_last:
            first_last[app_id] = [row["collected_date"], row["collected_date"]]
        else:
            first_last[app_id][1] = row["collected_date"]

    rows = []
    for app_id, values in ranks.items():
        avg_rank = mean(values)
        best_rank = min(values)
        worst_rank = max(values)
        snapshots_seen = len(values)
        survival_score = round((snapshots_seen * 2.0) + max(0, 101 - avg_rank) / 10 - (worst_rank - best_rank) / 20, 2)
        rows.append({
            **meta[app_id],
            "first_seen": first_last[app_id][0],
            "last_seen": first_last[app_id][1],
            "snapshots_seen": snapshots_seen,
            "best_rank": best_rank,
            "worst_rank": worst_rank,
            "avg_rank": round(avg_rank, 2),
            "rank_range": worst_rank - best_rank,
            "currently_top100": app_id in current_ids,
            "survival_score": survival_score,
        })
    rows.sort(key=lambda row: (-row["survival_score"], row["avg_rank"], row["title"]))
    return rows


def _tokens(text: str | None) -> list[str]:
    if not text:
        return []
    tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    return [token for token in tokens if token not in STOPWORDS and not token.isdigit()]


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def review_keyword_summary(connection: sqlite3.Connection, limit: int = 50) -> dict:
    token_counter: Counter[str] = Counter()
    game_issue_counts: dict[str, Counter[str]] = defaultdict(Counter)
    game_meta: dict[str, dict] = {}
    game_review_counts: Counter[str] = Counter()
    positive_reviews = 0
    negative_reviews = 0

    for row in connection.execute(
        """
        SELECT app_id, game_title, score, review_text
        FROM game_reviews
        WHERE review_text IS NOT NULL AND TRIM(review_text) <> ''
        """
    ):
        text = row["review_text"] or ""
        app_id = row["app_id"]
        token_counter.update(_tokens(text))
        game_review_counts[app_id] += 1
        game_meta.setdefault(app_id, {"app_id": app_id, "title": row["game_title"]})
        if (row["score"] or 0) >= 4 or _contains_any(text, POSITIVE_KEYWORDS):
            positive_reviews += 1
        if (row["score"] or 0) <= 2 or _contains_any(text, NEGATIVE_KEYWORDS):
            negative_reviews += 1
        for issue, keywords in ISSUE_KEYWORDS.items():
            if _contains_any(text, keywords):
                game_issue_counts[app_id][issue] += 1

    issue_rows = []
    for app_id, counter in game_issue_counts.items():
        total = game_review_counts[app_id]
        for issue, count in counter.items():
            issue_rows.append({
                **game_meta[app_id],
                "issue": issue,
                "count": count,
                "review_count": total,
                "issue_rate": round(count / total, 4) if total else 0,
            })
    issue_rows.sort(key=lambda row: (-row["count"], -row["issue_rate"], row["title"]))

    return {
        "top_keywords": token_counter.most_common(limit),
        "issue_rows": issue_rows[:limit],
        "positive_reviews": positive_reviews,
        "negative_reviews": negative_reviews,
        "review_count": sum(game_review_counts.values()),
    }


def developer_summary(connection: sqlite3.Connection, snapshot: str | None = None) -> list[dict]:
    snapshot = snapshot or latest_snapshot(connection)
    if not snapshot:
        return []
    rows = connection.execute(
        """
        SELECT developer,
               COUNT(*) AS games,
               MIN(rank) AS best_rank,
               ROUND(AVG(rank), 2) AS avg_rank,
               GROUP_CONCAT(title, ', ') AS games_list
        FROM game_snapshots
        WHERE collected_date = ?
        GROUP BY developer
        ORDER BY games DESC, best_rank ASC
        """,
        (snapshot,),
    ).fetchall()
    return [dict(row) for row in rows]


def genre_summary(connection: sqlite3.Connection, snapshot: str | None = None) -> list[dict]:
    snapshot = snapshot or latest_snapshot(connection)
    if not snapshot:
        return []
    rows = connection.execute(
        """
        SELECT COALESCE(genre, 'Unknown') AS genre,
               COUNT(*) AS games,
               MIN(rank) AS best_rank,
               ROUND(AVG(rank), 2) AS avg_rank,
               ROUND(AVG(score), 2) AS avg_score
        FROM game_snapshots
        WHERE collected_date = ?
        GROUP BY COALESCE(genre, 'Unknown')
        ORDER BY games DESC, best_rank ASC
        """,
        (snapshot,),
    ).fetchall()
    return [dict(row) for row in rows]


def _markdown_table(rows: list[dict], columns: list[tuple[str, str]], empty: str = "없음") -> str:
    if not rows:
        return empty
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(key, "") if row.get(key) is not None else "").replace("|", "\\|") for _, key in columns) + " |")
    return "\n".join([header, divider, *body])


def build_weekly_report(connection: sqlite3.Connection, days: int = 7, end_snapshot: str | None = None) -> str:
    snapshots = list_snapshots(connection)
    if not snapshots:
        return "# Google Play 게임 메타 분석 주간 리포트\n\n수집 데이터가 없습니다.\n"
    end_snapshot = end_snapshot or snapshots[-1]
    end_index = snapshots.index(end_snapshot)
    window = snapshots[max(0, end_index - (days * 2) + 1): end_index + 1]
    start_snapshot = window[0]
    movements = rank_movements(connection, end_snapshot, start_snapshot)
    survival = survival_rows(connection)
    keywords = review_keyword_summary(connection, limit=20)
    developers = developer_summary(connection, end_snapshot)[:10]
    genres = genre_summary(connection, end_snapshot)

    risers = [row for row in movements if row["status"] == "상승"][:10]
    fallers = [row for row in movements if row["status"] == "하락"][:10]
    new_entries = [row for row in movements if row["status"] == "신규"][:20]
    exits = [row for row in movements if row["status"] == "이탈"][:20]
    durable = survival[:15]
    issue_rows = keywords["issue_rows"][:15]
    top_keywords = [{"keyword": k, "count": v} for k, v in keywords["top_keywords"][:20]]

    lines = [
        f"# Google Play 게임 메타 분석 주간 리포트",
        "",
        f"- 분석 구간: `{start_snapshot}` → `{end_snapshot}`",
        f"- 비교 스냅샷 수: {len(window)}회",
        f"- 리뷰 분석 대상: {keywords['review_count']:,}건",
        f"- 긍정 후보 리뷰: {keywords['positive_reviews']:,}건",
        f"- 부정 후보 리뷰: {keywords['negative_reviews']:,}건",
        "",
        "## 1. 급상승 게임",
        "",
        _markdown_table(risers, [("변화", "rank_change"), ("현재", "current_rank"), ("이전", "previous_rank"), ("개발사", "developer"), ("게임", "title"), ("장르", "genre")]),
        "",
        "## 2. 급하락 게임",
        "",
        _markdown_table(fallers, [("변화", "rank_change"), ("현재", "current_rank"), ("이전", "previous_rank"), ("개발사", "developer"), ("게임", "title"), ("장르", "genre")]),
        "",
        "## 3. 신규 진입",
        "",
        _markdown_table(new_entries, [("현재", "current_rank"), ("개발사", "developer"), ("게임", "title"), ("장르", "genre")]),
        "",
        "## 4. 이탈",
        "",
        _markdown_table(exits, [("이전", "previous_rank"), ("개발사", "developer"), ("게임", "title"), ("장르", "genre")]),
        "",
        "## 5. 생존력 상위 게임",
        "",
        _markdown_table(durable, [("점수", "survival_score"), ("관측", "snapshots_seen"), ("최고", "best_rank"), ("평균", "avg_rank"), ("현재", "currently_top100"), ("개발사", "developer"), ("게임", "title")]),
        "",
        "## 6. 개발사 현황",
        "",
        _markdown_table(developers, [("개발사", "developer"), ("게임 수", "games"), ("최고 순위", "best_rank"), ("평균 순위", "avg_rank")]),
        "",
        "## 7. 장르 현황",
        "",
        _markdown_table(genres, [("장르", "genre"), ("게임 수", "games"), ("최고 순위", "best_rank"), ("평균 순위", "avg_rank"), ("평균 평점", "avg_score")]),
        "",
        "## 8. 리뷰 주요 키워드",
        "",
        _markdown_table(top_keywords, [("키워드", "keyword"), ("빈도", "count")]),
        "",
        "## 9. 게임별 주요 이슈",
        "",
        _markdown_table(issue_rows, [("이슈", "issue"), ("건수", "count"), ("비율", "issue_rate"), ("게임", "title")]),
        "",
    ]
    return "\n".join(lines)


def write_weekly_report(
    db_path: str | Path = "data/google_play_games.db",
    output_path: str | Path = "reports/weekly_meta_report.md",
    days: int = 7,
    end_snapshot: str | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with connect_readonly(db_path) as connection:
        report = build_weekly_report(connection, days=days, end_snapshot=end_snapshot)
    output.write_text(report, encoding="utf-8")
    return output
