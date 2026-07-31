"""Command-line entry point.

Wires the three layers together: fetch (`client`) -> parse (`transform`) ->
summarise (`aggregate`) -> print. Registered as the `ns-api-project` console
script in pyproject.toml.
"""

import click

from ns_api_project.aggregate import stats_by_category
from ns_api_project.client import get_departures
from ns_api_project.transform import parse_departures


@click.command()
@click.option("--station", default="UT", help="Station code, e.g. UT, ASD, RTD.")
# envvar keeps the key off the command line (and out of shell history);
# `--api-key` stays available as an explicit override.
@click.option("--api-key", envvar="NS_API_KEY", required=True)
def main(station: str, api_key: str) -> None:
    """Print delay statistics per train category for one station."""
    departures = parse_departures(get_departures(station, api_key))
    for s in stats_by_category(departures):
        # Fixed-width columns so consecutive rows line up in a terminal.
        click.echo(
            f"{s.train_category:<5} n={s.departures:<3} "
            f"avg={s.avg_delay_minutes:>5.1f}m max={s.max_delay_minutes:>5.1f}m "
            f"cancelled={s.cancelled} track_changes={s.track_changes}"
        )