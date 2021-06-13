import datetime
import io
from stats_bot.ranks import RANK_LIST, get_valid_ranks
import typing

import matplotlib
import matplotlib.pyplot as plot
import matplotlib.ticker

import praw

from . import database_reader
from ..helpers import text_color

matplotlib.use("AGG")

async def plot_all_history(
    start: typing.Union[datetime.date, str] = None,
    end: typing.Union[datetime.date, str] = None,
):
    date_format = r"%Y-%m-%d"
    if isinstance(start, str):
        start = datetime.datetime.strptime(start, date_format).date()

    if start is None:
        start = datetime.date.min
    else:
        # Adjusted for exclusive range.
        start -= datetime.timedelta(days=1)

    if isinstance(end, str):
        end = datetime.datetime.strptime(end, date_format).date()

    if end is None:
        end = datetime.date.max
    else:
        # Adjusted for exclusive range.
        end += datetime.timedelta(days=1)

    async with database_reader.get_connection() as connection:
        rows = await connection.fetch(
            """
            SELECT
                DATE(time) AS day,
                SUM(gamma) AS gamma_count
            FROM new_gammas WHERE time BETWEEN $1 AND $2
            GROUP BY DATE(time) ORDER BY DATE(time) ASC;
            """,
            start,
            end,
        )

    if rows is None or len(rows) < 2:
        return

    days = []
    gamma_counts = []

    for row in rows:
        days.append(row["day"])
        gamma_counts.append(row["gamma_count"])

    plot.plot(days, gamma_counts, color=text_color)

    plot.xlabel("Time")
    plot.ylabel("Gammas")
    plot.xticks(rotation=90)
    plot.title("Server Gamma History")

    plot.gcf().subplots_adjust(bottom=0.3)

    all_history_plot = io.BytesIO()
    plot.savefig(all_history_plot, format="png")
    plot.clf()

    all_history_plot.seek(0)

    return all_history_plot


async def plot_multi_history(
    redditors: typing.List[typing.Union[str, praw.models.Redditor]],
    start: typing.Union[datetime.date, str] = None,
    end: typing.Union[datetime.date, str] = None,
    whole=False,
):
    date_format = r"%Y-%m-%d"
    if isinstance(start, str):
        start = datetime.datetime.strptime(start, date_format).date()

    if start is None:
        start = datetime.date.min
    else:
        # Adjusted for exclusive range.
        start -= datetime.timedelta(days=1)

    if isinstance(end, str):
        end = datetime.datetime.strptime(end, date_format).date()

    if end is None:
        end = datetime.date.max
    else:
        # Adjusted for exclusive range.
        end += datetime.timedelta(days=1)

    most = 0
    cols = ["black", "green", "red", "teal", "purple", "gold", "deeppink", "orangered", "forestgreen", "royalblue"]

    for i, redditor in enumerate(redditors):
        if isinstance(redditor, praw.models.Redditor):
            name = redditor.name
        else:
            name = redditor

        async with database_reader.get_connection() as connection:
            rows = await connection.fetch(
                """
                SELECT
                    DATE(time) AS date,
                    SUM(new_gamma - old_gamma) AS gamma_count
                FROM gammas WHERE transcriber = $1 AND time BETWEEN $2 AND $3
                GROUP BY DATE(TIME)
                ORDER BY DATE(time) ASC;
                """,
                name,
                start,
                end,
            )

        if rows is None or len(rows) < 2:
            return

        times = []
        values = []

        total_gamma = 0
        for row in rows:
            total_gamma += row["gamma_count"]

            times.append(row["date"])
            values.append(total_gamma)

        if values[-1] > most:
            most = values[-1]

        plot.plot(times, values, color=cols[i % len(cols)])

    ranks_to_plot = RANK_LIST if whole else get_valid_ranks(most)

    for rank in ranks_to_plot:
        plot.axhline(y=rank.lower_bound, color=rank.color)

    plot.xlabel("Time")
    plot.ylabel("Gammas")
    plot.xticks(rotation=90)
    plot.title("Multi-gamma history")
    plot.legend(redditors)

    plot.gcf().subplots_adjust(bottom=0.3)

    multi_history_plot = io.BytesIO()
    plot.savefig(multi_history_plot, format="png")
    plot.clf()

    multi_history_plot.seek(0)

    return multi_history_plot


async def plot_distribution():
    async with database_reader.get_connection() as connection:
        rows = await connection.fetch(
            (
                """
                SELECT
                    official_gamma_count
                FROM transcribers
                WHERE official_gamma_count IS NOT NULL AND official_gamma_count > 0;
                """
            )
        )

    if rows is None or len(rows) < 2:
        return

    # A log scale looks better
    gammas = [row["official_gamma_count"] for row in rows]

    gammas.sort()

    plot.title("Gamma distribution")
    figure, axes = plot.subplots(1, 1)

    plot.semilogy(range(len(gammas)), gammas)

    # Rotate labels 90^o
    axes.xaxis.set_tick_params(labelrotation=90.0)

    # Don't cut off date
    plot.gcf().subplots_adjust(bottom=0.22)

    plot.xlabel("Cumulated Transcribers")
    plot.ylabel("Transcriptions")

    axes.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())

    gammas_plot = io.BytesIO()
    plot.savefig(gammas_plot, format="png")
    plot.clf()

    gammas_plot.seek(0)

    return gammas_plot


async def plot_rate(
    name_or_redditor: typing.Union[str, praw.models.Redditor],
    start: typing.Union[datetime.date, str] = None,
    end: typing.Union[datetime.date, str] = None,
    whole=False,
):
    if isinstance(name_or_redditor, praw.models.Redditor):
        name = name_or_redditor.name
    else:
        name = name_or_redditor

    date_format = r"%Y-%m-%d"
    if isinstance(start, str):
        start = datetime.datetime.strptime(start, date_format).date()

    if start is None:
        start = datetime.date.min
    else:
        # Adjusted for exclusive range.
        start -= datetime.timedelta(days=1)

    if isinstance(end, str):
        end = datetime.datetime.strptime(end, date_format).date()

    if end is None:
        end = datetime.date.max
    else:
        # Adjusted for exclusive range.
        end += datetime.timedelta(days=1)

    async with database_reader.get_connection() as connection:
        rows = await connection.fetch(
            """
            SELECT
                DATE(time) AS date,
                SUM(new_gamma - old_gamma) AS gamma_count
            FROM gammas
            WHERE transcriber = $1 AND time BETWEEN $2 AND $3
            GROUP BY DATE(TIME) ORDER BY DATE(time) ASC;
            """,
            name,
            start,
            end,
        )

    if rows is None or len(rows) < 2:
        return

    times = []
    values = []
    for row in rows:
        times.append(row["date"])
        values.append(row["gamma_count"])

    plot.plot(times, values, color=text_color)

    plot.xlabel("Time")
    plot.ylabel("Gammas / Day")
    plot.title(f"Gamma gain rate of /u/{name}")

    plot.xticks(rotation=90)
    plot.gcf().subplots_adjust(bottom=0.3)

    rate_plot = io.BytesIO()
    plot.savefig(rate_plot, format="png")
    plot.clf()

    rate_plot.seek(0)

    return rate_plot


async def plot_all_rate():
    async with database_reader.get_connection() as connection:
        rows = await connection.fetch(
            """
            SELECT
                DATE(time) AS date,
                SUM(new_gamma - old_gamma) AS gamma_count
            FROM gammas
            WHERE old_gamma IS NOT NULL
            GROUP BY DATE(time) ORDER BY DATE(time) ASC;
            """
        )

    if rows is None or len(rows) < 2:
        return

    rates = []
    dates = []

    for row in rows:
        rates.append(row["gamma_count"])
        dates.append(row["date"])

    # Create new subplot because some functions only work on subplots
    figure, axes = plot.subplots(1, 1)

    # Make histogram
    axes.bar(dates, height=rates)

    # Rotate labels 90^o
    axes.xaxis.set_tick_params(labelrotation=90.0)

    # Don't cut off date
    plot.gcf().subplots_adjust(bottom=0.22)

    # Standard code
    plot.xlabel("Time")
    plot.ylabel("Gammas / Day")
    plot.title("Gamma gain rate of the whole server")

    rate_plot = io.BytesIO()
    plot.savefig(rate_plot, format="png")
    plot.clf()

    rate_plot.seek(0)

    return rate_plot


async def plot_history(
    name_or_redditor: typing.Union[str, praw.models.Redditor],
    start: typing.Union[datetime.date, str] = None,
    end: typing.Union[datetime.date, str] = None,
    whole=False,
):
    if isinstance(name_or_redditor, praw.models.Redditor):
        name = name_or_redditor.name
    else:
        name = name_or_redditor

    date_format = r"%Y-%m-%d"
    if isinstance(start, str):
        start = datetime.datetime.strptime(start, date_format).date()

    if start is None:
        start = datetime.date.min
    else:
        # Adjusted for exclusive range.
        start -= datetime.timedelta(days=1)

    if isinstance(end, str):
        end = datetime.datetime.strptime(end, date_format).date()

    if end is None:
        end = datetime.date.max
    else:
        # Adjusted for exclusive range.
        end += datetime.timedelta(days=1)

    async with database_reader.get_connection() as connection:
        rows = await connection.fetch(
            """
            SELECT
                DATE(time) AS date,
                SUM(new_gamma - old_gamma) AS gamma_count
            FROM gammas
            WHERE transcriber = $1 AND time BETWEEN $2 AND $3
            GROUP BY DATE(TIME) ORDER BY DATE(time) ASC;
            """,
            name,
            start,
            end,
        )

    if rows is None or len(rows) < 2:
        return

    times = []
    values = []

    total_gamma = 0
    for row in rows:
        total_gamma += row["gamma_count"]

        times.append(row["date"])
        values.append(total_gamma)

    plot.plot(times, values, color=text_color)
    last = values[-1]

    ranks_to_plot = RANK_LIST if whole else get_valid_ranks(last)

    for rank in ranks_to_plot:
        plot.axhline(y=rank.lower_bound, color=rank.color)

    plot.xlabel("Time")
    plot.ylabel("Gammas")
    plot.xticks(rotation=90)
    plot.gcf().subplots_adjust(bottom=0.3)
    plot.title(f"Gamma history of /u/{name}")

    history_plot = io.BytesIO()
    plot.savefig(history_plot, format="png")
    plot.clf()

    history_plot.seek(0)

    return history_plot
