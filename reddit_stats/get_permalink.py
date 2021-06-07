import asyncio
import praw
import logging
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

import database
import passwords_and_tokens

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent="Lornebot 0.0.1",
    check_for_async=False
)


async def main():
    await database.create_pool()

    async with database.get_connection() as connection:
        rows = await connection.fetch(
            """
            SELECT
                comment_id
            FROM transcriptions
            WHERE permalink IS NULL;
            """
        )

        if rows is None:
            return

        comment_ids = [row["comment_id"] for row in rows]

        for comment_id in comment_ids:
            comment = reddit.comment(comment_id)

            try:
                permalink = comment.permalink
            except ValueError:
                logging.info(
                    f"Comment {comment_id} skipped because it has no permalink"
                )
                continue

            await connection.execute(
                """
                UPDATE transcriptions
                    SET permalink = $1
                WHERE comment_id = $2
                """,
                permalink,
                comment_id,
            )


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(main())
