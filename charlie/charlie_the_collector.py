import asyncio
import logging

import praw

import database
import passwords_and_tokens

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent="Lornebot 0.0.1",
)


async def analyze_transcription(transcription, refresh_retries=3):
    for i in range(refresh_retries):
        try:
            transcription.refresh()
        except Exception:
            continue
        else:
            if i != 0:
                logging.warning(
                    f"Error in refresh {i} times for transcription: {transcription.id}"
                )
            break
    else:
        logging.warning(
            f"Could not get information after {refresh_retries} refreshes "
            f"for transcription: {transcription.id}"
        )

        async with database.get_connection() as connection:
            await connection.execute(
                """
                UPDATE transcriptions
                    SET good_bot = 0,
                    bad_bot = 0,
                    good_human = 0,
                    bad_human = 0,
                    comment_count = 0,
                    upvotes = 0,
                    last_checked = NOW(),
                    error = true
                WHERE comment_id = $1;
                """,
                transcription.id,
            )
            return

    replies = transcription.replies
    if replies is None:
        logging.info(f"No replies to transcription: {transcription.id}")
        return

    replies.replace_more(0)

    comment_count = good_bot = bad_bot = good_human = bad_human = 0

    for comment in replies:
        comment_count += 1
        content = comment.body.casefold()
        if "good bot" in content:
            good_bot += 1

        if "bad bot" in content:
            bad_bot += 1

        if "good human" in content:
            good_human += 1

        if "bad human" in content:
            bad_human += 1

    logging.info(
        f"Stats for transcription {transcription.id}: "
        f"{good_bot} {bad_bot} {good_human} {bad_human} {comment_count} "
        f"{transcription.score}"
    )

    async with database.get_connection() as connection:
        await connection.execute(
            """
            UPDATE transcriptions
                SET good_bot = $1,
                bad_bot = $2,
                good_human = $3,
                bad_human = $4,
                comment_count = $5,
                upvotes = $6,
                last_checked = NOW(),
                error = FALSE
            WHERE comment_id = $7;
            """,
            good_bot,
            bad_bot,
            good_human,
            bad_human,
            comment_count,
            transcription.score,
            transcription.id,
        )


async def analyze_all_transcriptions():
    async with database.get_connection() as connection:
        transcriptions = await connection.fetch(
            """
            SELECT comment_id
            FROM transcriptions
            WHERE EXTRACT(epoch FROM NOW()) - EXTRACT(epoch FROM found) < (24 * 60 * 60)
                OR last_checked IS NULL OR good_bot IS NULL OR bad_bot IS NULL
                OR good_human IS NULL OR bad_human IS NULL
            ORDER BY last_checked ASC;
            """
        )

    if transcriptions is None:
        logging.info("There are no transcriptions to analyze.")
        return

    transcriptions = [reddit.comment(row["comment_id"]) for row in transcriptions]
    for transcription in transcriptions:
        logging.info(
            f"Analyzing /u/{transcription.author}'s transcription: {transcription.id}"
        )
        await analyze_transcription(transcription)


async def analyze_loop(timeout=60.0):
    await analyze_all_transcriptions()
    await asyncio.sleep(timeout)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(database.create_pool())

    try:
        while True:
            loop.run_until_complete(analyze_loop())
    finally:
        loop.run_until_complete(database.close_pool())
        loop.close()
