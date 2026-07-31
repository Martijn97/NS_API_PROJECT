"""Summarise parsed departures into per-train-category statistics.

Like `transform`, this layer is pure: list of `Departure` in, list of
`CategoryStats` out.
"""

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean

from ns_api_project.transform import Departure


@dataclass(frozen=True)
class CategoryStats:
    """Aggregated punctuality numbers for one train category (IC, SPR, ...)."""

    train_category: str
    departures: int
    cancelled: int
    track_changes: int
    avg_delay_minutes: float
    max_delay_minutes: float


def stats_by_category(departures: list[Departure]) -> list[CategoryStats]:
    """Group departures by train category and compute stats per group.

    Returns:
        Stats sorted by average delay, worst first, so the CLI output leads with
        the category that is running least on time. An empty input yields [].
    """
    grouped: dict[str, list[Departure]] = defaultdict(list)
    for d in departures:
        grouped[d.train_category].append(d)

    # Only non-empty groups exist here, so mean()/max() can't hit a StatisticsError.
    return sorted(
        (
            CategoryStats(
                train_category=category,
                departures=len(items),
                # bool sums as 0/1, so these are plain counts.
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