from __future__ import annotations

import html
import re
import time
from collections.abc import Callable
from datetime import date, datetime, timezone
from urllib.request import Request, urlopen

from game_collector.models import GameSnapshot

PLAY_CATEGORY_URL = "https://play.google.com/store/apps/category/GAME?hl={lang}&gl={country}"
APP_LINK_RE = re.compile(r"/store/apps/details\?id=([A-Za-z0-9._]+)")


class CollectionError(RuntimeError):
    pass


def discover_game_ids(
    country: str = "KR",
    lang: str = "ko",
    limit: int = 100,
    opener: Callable[..., object] = urlopen,
) -> list[str]:
    """Discover game package IDs in the order exposed by the public GAME page.

    Google does not expose a public ranking API. This adapter intentionally lives
    in one function so it can be replaced if the Play page structure changes.
    """
    url = PLAY_CATEGORY_URL.format(country=country, lang=lang)
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/126 Safari/537.36"
            ),
            "Accept-Language": f"{lang}-{country},{lang};q=0.9",
        },
    )
    try:
        response = opener(request, timeout=30)
        page = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise CollectionError(f"Google Play game page request failed: {exc}") from exc

    page = html.unescape(page).replace("\\u003d", "=").replace("\\u0026", "&")
    app_ids = list(dict.fromkeys(APP_LINK_RE.findall(page)))
    if not app_ids:
        raise CollectionError("No package IDs were found; Google Play markup may have changed.")
    return app_ids[:limit]


def _timestamp_to_iso(value: object) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()
    return str(value)


def collect_snapshots(
    app_ids: list[str],
    collected_date: str | None = None,
    country: str = "kr",
    lang: str = "ko",
    delay_seconds: float = 0.2,
    app_fetcher: Callable[..., dict] | None = None,
) -> tuple[list[GameSnapshot], list[tuple[str, str]]]:
    if app_fetcher is None:
        from google_play_scraper import app as app_fetcher

    snapshot_date = collected_date or date.today().isoformat()
    snapshots: list[GameSnapshot] = []
    failures: list[tuple[str, str]] = []

    for rank, app_id in enumerate(app_ids, start=1):
        try:
            item = app_fetcher(app_id, lang=lang, country=country)
            snapshots.append(
                GameSnapshot(
                    collected_date=snapshot_date,
                    rank=rank,
                    app_id=app_id,
                    title=item.get("title") or app_id,
                    developer=item.get("developer"),
                    genre=item.get("genre"),
                    score=item.get("score"),
                    ratings=item.get("ratings"),
                    reviews=item.get("reviews"),
                    installs=item.get("installs"),
                    min_installs=item.get("minInstalls"),
                    real_installs=item.get("realInstalls"),
                    updated_at=_timestamp_to_iso(item.get("updated")),
                    icon_url=item.get("icon"),
                    offers_iap=item.get("offersIAP"),
                    price=item.get("price"),
                    source_url=item.get("url"),
                )
            )
        except Exception as exc:
            failures.append((app_id, str(exc)))
        if delay_seconds > 0 and rank < len(app_ids):
            time.sleep(delay_seconds)

    return snapshots, failures
