import passwords_and_tokens
import asyncpg


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
