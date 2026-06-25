from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GameSnapshot:
    collected_date: str
    rank: int
    app_id: str
    title: str
    developer: str | None = None
    genre: str | None = None
    score: float | None = None
    ratings: int | None = None
    reviews: int | None = None
    installs: str | None = None
    min_installs: int | None = None
    real_installs: int | None = None
    updated_at: str | None = None
    icon_url: str | None = None
    offers_iap: bool | None = None
    price: float | None = None
    source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
