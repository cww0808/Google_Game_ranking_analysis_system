from pathlib import Path


def _table(rows: list[dict], fields: list[tuple[str, str]], empty: str = "없음") -> str:
    if not rows:
        return empty
    header = "| " + " | ".join(label for label, _ in fields) + " |"
    divider = "| " + " | ".join("---" for _ in fields) + " |"
    body = [
        "| "
        + " | ".join(
            str(row.get(key, "") if row.get(key) is not None else "").replace("|", "\\|")
            for _, key in fields
        )
        + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def write_markdown_report(
    path: str | Path,
    current_date: str,
    previous_date: str | None,
    current: list[dict],
    analysis: dict | None,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 한국 Google Play 게임 수집 보고서 — {current_date}",
        "",
        f"- 수집 게임 수: {len(current)}",
        f"- 비교 기준일: {previous_date or '없음 (첫 수집)'}",
        "- 데이터 출처: Google Play 공개 페이지(비공식 수집)",
        "",
    ]
    if analysis:
        lines += [
            "## 급상승",
            "",
            _table(
                analysis["risers"][:10],
                [
                    ("개발사", "developer"),
                    ("게임", "title"),
                    ("현재", "rank"),
                    ("이전", "previous_rank"),
                    ("변화", "rank_change"),
                ],
            ),
            "",
            "## 급하락",
            "",
            _table(
                analysis["fallers"][:10],
                [
                    ("개발사", "developer"),
                    ("게임", "title"),
                    ("현재", "rank"),
                    ("이전", "previous_rank"),
                    ("변화", "rank_change"),
                ],
            ),
            "",
            "## 신규 진입",
            "",
            _table(
                analysis["new_entries"],
                [("순위", "rank"), ("개발사", "developer"), ("게임", "title"), ("장르", "genre")],
            ),
            "",
            "## 이탈",
            "",
            _table(
                analysis["exits"],
                [("이전 순위", "rank"), ("개발사", "developer"), ("게임", "title"), ("장르", "genre")],
            ),
            "",
            "## 장르 점유 변화",
            "",
            _table(
                analysis["genres"],
                [("장르", "genre"), ("오늘", "current"), ("이전", "previous"), ("변화", "change")],
            ),
            "",
        ]
    lines += [
        "## 현재 목록",
        "",
        _table(
            current,
            [
                ("순위", "rank"),
                ("개발사", "developer"),
                ("게임", "title"),
                ("장르", "genre"),
                ("평점", "score"),
                ("평가 수", "ratings"),
                ("설치 수", "installs"),
            ],
        ),
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
