import datetime

import asyncpg

from .. import passwords_and_tokens

pool = None


def get_connection(*, timeout=None):
    if pool is None:
        raise RuntimeError("Pool is closed or was never created!")

    return pool.acquire(timeout=timeout)


async def create_pool():
    global pool
    pool = await asyncpg.create_pool(
        host=passwords_and_tokens.sql_ip,
        user=passwords_and_tokens.sql_user,
        password=passwords_and_tokens.sql_password,
        database="torstats",
        port=5432,
    )


async def close_pool():
    await pool.close()


async def get_flair_count(reddit_name, discord_id):
    async with get_connection() as connection:
        row = await connection.fetchrow(
            "SELECT valid, official_gamma_count FROM transcribers WHERE name = $1",
            reddit_name,
        )

        if len(row) < 1:
            await add_user(reddit_name, discord_id)
            return

        if row["valid"] is False or row["official_gamma_count"] is None:
            return

    return row["official_gamma_count"]


async def get_last_x_hours(reddit_name, hours=24):
    async with get_connection() as connection:
        gamma_records = await connection.fetch(
            "SELECT old_gamma, new_gamma FROM gammas WHERE transcriber = $1 "
            "AND time >= NOW() - $2::INTERVAL ORDER BY time DESC",
            reddit_name,
            datetime.timedelta(hours=hours),
        )

    if gamma_records is not None and len(gamma_records) >= 1:
        return gamma_records[0]["new_gamma"] - gamma_records[-1]["old_gamma"]
    else:
        return 0


async def get_total_gammas():
    async with get_connection() as connection:
        gamma_count = await connection.fetchval(
            "SELECT SUM(official_gamma_count) AS gamma_count FROM transcribers"
        )

    return gamma_count


async def gammas():
    async with get_connection() as connection:
        gammas = await connection.fetch(
            (
                "SELECT name, official_gamma_count FROM transcribers "
                "WHERE NOT official_gamma_count IS NULL"
            )
        )

    return gammas


async def fetch_official_gamma_count(user):
    async with get_connection() as connection:
        gamma_count = await connection.fetchval(
            "SELECT official_gamma_count FROM transcribers WHERE name = $1", user
        )

    return gamma_count


async def kumas():
    return await fetch_official_gamma_count("KumaLumaJuma")


async def fetch_stats(name):
    async with get_connection() as connection:
        stats = await connection.fetchrow(
            (
                "SELECT counted_comments, official_gamma_count, "
                "COUNT(comment_id) as comment_count, "
                "SUM(LENGTH(content)) as total_length, "
                "COALESCE(SUM(upvotes), 0) as upvotes, "
                "COALESCE(SUM(good_bot), 0) as good_bot, "
                "COALESCE(SUM(bad_bot), 0) as bad_bot, "
                "COALESCE(SUM(good_human), 0) as good_human, "
                "COALESCE(SUM(bad_human), 0) as bad_human, "
                "valid FROM transcribers LEFT OUTER JOIN transcriptions ON name = "
                "transcriber WHERE name = $1 GROUP BY name"
            ),
            name,
        )

    return stats


async def info():
    async with get_connection() as connection:
        row = await connection.fetchrow(
            "SELECT most_recent, least_recent, difference, running FROM info;"
        )

    return row


async def fetch_all_stats():
    async with get_connection() as connection:
        all_stats = await connection.fetchrow(
            "SELECT COUNT(comment_id) AS comment_count, "
            "SUM(LENGTH(content)) AS total_length, "
            "SUM(upvotes) AS upvotes, "
            "SUM(good_bot) AS good_bot, "
            "SUM(bad_bot) AS bad_bot, "
            "SUM(good_human) AS good_human, "
            "SUM(bad_human) AS bad_human FROM transcriptions;"
        )

    return all_stats


async def get_new_flairs(last_time):
    async with get_connection() as connection:
        flairs = await connection.fetch(
            (
                "SELECT transcribers.name, gammas.old_gamma, gammas.new_gamma, "
                "transcribers.discord_id FROM new_gammas "
                "INNER JOIN transcribers ON name = transcriber "
                "WHERE EXTRACT(epoch from time) > $1 ORDER BY TIME"
            ),
            last_time,
        )

    return flairs


async def add_user(user, discord_id):
    async with get_connection() as connection:
        await connection.execute(
            "INSERT INTO transcribers (name, discord_id) VALUES ($1, $2) "
            "ON CONFLICT DO NOTHING",
            user,
            discord_id,
        )


async def get_transcriptions(name):
    async with get_connection() as connection:
        comment_ids = await connection.fetchval(
            "SELECT comment_id FROM transcriptions WHERE transcriber = $1", name
        )

    return comment_ids


async def find_comments(text, name=None):
    async with get_connection() as connection:
        if name is not None:
            comments = await connection.fetch(
                "SELECT comment_id, content, permalink FROM transcriptions "
                "WHERE transcriber = $1 AND content LIKE $2",
                name,
                f"%{text}%",
            )
        else:
            comments = await connection.fetch(
                "SELECT comment_id, content, permalink FROM transcriptions "
                f"WHERE content LIKE $1 %{text}%"
            )

    return [comment.values() for comment in comments]
