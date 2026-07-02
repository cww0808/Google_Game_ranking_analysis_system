from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from game_collector.insights import (  # noqa: E402
    build_weekly_report,
    developer_summary,
    genre_summary,
    latest_snapshot,
    list_snapshots,
    rank_movements,
    review_keyword_summary,
    survival_rows,
)


DEFAULT_DB = ROOT / "data" / "google_play_games.db"


@st.cache_data(show_spinner=False)
def read_sql(db_path: str, query: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(db_path) as connection:
        return pd.read_sql_query(query, connection, params=params)


@st.cache_data(show_spinner=False)
def load_insights(db_path: str, snapshot: str) -> dict:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        previous = None
        snapshots = list_snapshots(connection)
        if snapshot in snapshots:
            idx = snapshots.index(snapshot)
            previous = snapshots[idx - 1] if idx > 0 else None
        return {
            "latest": latest_snapshot(connection),
            "snapshots": snapshots,
            "movements": pd.DataFrame(rank_movements(connection, snapshot, previous)),
            "survival": pd.DataFrame(survival_rows(connection)),
            "developers": pd.DataFrame(developer_summary(connection, snapshot)),
            "genres": pd.DataFrame(genre_summary(connection, snapshot)),
            "keywords": review_keyword_summary(connection, limit=80),
            "weekly_markdown": build_weekly_report(connection, days=7, end_snapshot=snapshot),
        }


st.set_page_config(page_title="Google Play 게임 메타 분석", layout="wide")
st.title("Google Play 게임 메타 분석 대시보드")

db_path = st.sidebar.text_input("SQLite DB 경로", str(DEFAULT_DB))
if not Path(db_path).exists():
    st.error(f"DB 파일을 찾을 수 없습니다: {db_path}")
    st.stop()

with sqlite3.connect(db_path) as connection:
    connection.row_factory = sqlite3.Row
    snapshots = list_snapshots(connection)

if not snapshots:
    st.warning("수집된 스냅샷이 없습니다.")
    st.stop()

snapshot = st.sidebar.selectbox("분석 스냅샷", snapshots[::-1], index=0)
data = load_insights(db_path, snapshot)

overview_df = read_sql(
    db_path,
    """
    SELECT COUNT(DISTINCT collected_date) AS snapshots,
           COUNT(*) AS snapshot_rows,
           COUNT(DISTINCT app_id) AS unique_games
    FROM game_snapshots
    """,
)
reviews_df = read_sql(
    db_path,
    "SELECT COUNT(*) AS reviews, COUNT(DISTINCT reviewer_key) AS reviewers FROM game_reviews",
)
current_df = read_sql(
    db_path,
    "SELECT rank, developer, title, app_id, genre, score, ratings, installs FROM game_snapshots WHERE collected_date=? ORDER BY rank",
    (snapshot,),
)

metric_cols = st.columns(5)
metric_cols[0].metric("수집 회차", int(overview_df.loc[0, "snapshots"]))
metric_cols[1].metric("고유 게임", int(overview_df.loc[0, "unique_games"]))
metric_cols[2].metric("리뷰", f"{int(reviews_df.loc[0, 'reviews']):,}")
metric_cols[3].metric("리뷰어", f"{int(reviews_df.loc[0, 'reviewers']):,}")
metric_cols[4].metric("현재 TOP100", len(current_df))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["랭킹 변화", "게임 상세", "개발사/장르", "리뷰 키워드", "생존력/주간 리포트"])

with tab1:
    st.subheader("현재 TOP 100")
    st.dataframe(current_df, use_container_width=True, hide_index=True)
    st.subheader("직전 수집 대비 변동")
    movements = data["movements"]
    if not movements.empty:
        status = st.multiselect("구분 필터", sorted(movements["status"].dropna().unique()), default=list(sorted(movements["status"].dropna().unique())))
        filtered = movements[movements["status"].isin(status)]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info("변동 데이터가 없습니다.")

with tab2:
    st.subheader("게임별 순위 추이")
    games = read_sql(db_path, "SELECT DISTINCT title, app_id FROM game_snapshots ORDER BY title")
    selected = st.selectbox("게임 선택", games["title"].tolist())
    app_id = games.loc[games["title"] == selected, "app_id"].iloc[0]
    history = read_sql(
        db_path,
        "SELECT collected_date, rank, score, ratings, developer, genre FROM game_snapshots WHERE app_id=? ORDER BY collected_date",
        (app_id,),
    )
    st.line_chart(history.set_index("collected_date")["rank"])
    st.caption("순위는 낮을수록 좋습니다. 차트 축은 Streamlit 기본 방향입니다.")
    st.dataframe(history, use_container_width=True, hide_index=True)
    reviews = read_sql(
        db_path,
        "SELECT review_date, score, user_name_at_review, review_text FROM game_reviews WHERE app_id=? ORDER BY review_date DESC LIMIT 200",
        (app_id,),
    )
    st.subheader("최근 리뷰 샘플")
    st.dataframe(reviews, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("개발사 현황")
    st.dataframe(data["developers"], use_container_width=True, hide_index=True)
    st.subheader("장르 현황")
    st.dataframe(data["genres"], use_container_width=True, hide_index=True)
    if not data["genres"].empty:
        st.bar_chart(data["genres"].set_index("genre")["games"])

with tab4:
    keyword_rows = pd.DataFrame(data["keywords"]["top_keywords"], columns=["keyword", "count"])
    issue_rows = pd.DataFrame(data["keywords"]["issue_rows"])
    st.subheader("리뷰 주요 키워드")
    st.dataframe(keyword_rows, use_container_width=True, hide_index=True)
    if not keyword_rows.empty:
        st.bar_chart(keyword_rows.head(30).set_index("keyword")["count"])
    st.subheader("게임별 주요 이슈")
    st.dataframe(issue_rows, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("게임 생존력")
    survival = data["survival"]
    st.dataframe(survival, use_container_width=True, hide_index=True)
    st.subheader("주간 리포트 미리보기")
    st.markdown(data["weekly_markdown"])
