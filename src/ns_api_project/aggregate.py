from collections import defaultdict
from dataclasses import dataclass
from statistics import mean

from ns_api_project.transform import Departure


@dataclass(frozen=True)
class CategoryStats:
    train_category: str
    departures: int
    cancelled: int
    track_changes: int
    avg_delay_minutes: float
    max_delay_minutes: float


def stats_by_category(departures: list[Departure]) -> list[CategoryStats]:
    grouped: dict[str, list[Departure]] = defaultdict(list)
    for d in departures:
        grouped[d.train_category].append(d)

    return sorted(
        (
            CategoryStats(
                train_category=category,
                departures=len(items),
                cancelled=sum(d.cancelled for d in items),
                track_changes=sum(d.track_changed for d in items),
                avg_delay_minutes=round(mean(d.delay_minutes for d in items), 1),
                max_delay_minutes=max(d.delay_minutes for d in items),
            )
            for category, items in grouped.items()
        ),
        key=lambda s: s.avg_delay_minutes,
        reverse=True,
    )