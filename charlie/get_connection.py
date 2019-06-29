import asyncio
import asyncpg
import passwords_and_tokens

pool = None


def get_connection(*, timeout=None):
    global pool

    if pool is None:
        loop = asyncio.get_event_loop()
        pool = loop.run_until_complete(
            asyncpg.create_pool(
                host=passwords_and_tokens.sql_ip,
                user=passwords_and_tokens.sql_user,
                password=passwords_and_tokens.sql_password,
                database="torstats",
                port=5432,
            )
        )
    return pool.acquire(timeout)
