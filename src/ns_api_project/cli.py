import click

from ns_api_project.aggregate import stats_by_category
from ns_api_project.client import get_departures
from ns_api_project.transform import parse_departures


@click.command()
@click.option("--station", default="UT", help="Station code, e.g. UT, ASD, RTD.")
@click.option("--api-key", envvar="NS_API_KEY", required=True)
def main(station: str, api_key: str) -> None:
    departures = parse_departures(get_departures(station, api_key))
    for s in stats_by_category(departures):
        click.echo(
            f"{s.train_category:<5} n={s.departures:<3} "
            f"avg={s.avg_delay_minutes:>5.1f}m max={s.max_delay_minutes:>5.1f}m "
            f"cancelled={s.cancelled} track_changes={s.track_changes}"
        )