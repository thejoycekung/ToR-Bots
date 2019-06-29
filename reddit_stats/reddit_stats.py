import asyncio
import datetime
import logging
import traceback

import discord
import praw
import prawcore

import database
import passwords_and_tokens

client = discord.Client()

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent="Lornebot 0.0.1",
)

tor = reddit.subreddit("TranscribersOfReddit")

with open("ignored_users.txt", "r") as stream:
    ignored_users = [line.strip().casefold() for line in stream]


def is_transcription(comment):
    created_utc = comment.created_utc

    created = datetime.datetime.utcfromtimestamp(created_utc).date()

    if created > datetime.date(2018, 11, 20):
        body = comment.body
        return "www.reddit.com/r/TranscribersOfReddit" in body and "&#32;" in body
    else:
        # For legacy transcriptions.
        body = comment.body.lower()
        return (
            "human" in body
            and "content" in body
            and "volunteer" in body
            and "transcriber" in body
            and "r/TranscribersOfReddit/wiki/index" in body
        )


batch_one_hundred = (
    "Reddit's API doesn't support fetching more than 100 comments in a single request."
)


async def analyze_all_users(limit=100, from_newest=False, prioritize_new=True):
    if limit > 100:
        raise UserWarning(batch_one_hundred)

    async with database.get_connection() as connection:
        transcribers = await connection.fetch(
            "SELECT name FROM transcribers ORDER BY name ASC;"
        )

    for transcriber in transcribers:
        await analyze_user(transcriber["name"], limit, from_newest, prioritize_new)


async def analyze_user(user, limit=100, from_newest=False, prioritize_new=True):
    if limit > 100:
        raise UserWarning(batch_one_hundred)

    if user in (None, ""):
        logging.info("A user to be analyzed must be passed.")
        return

    if user.casefold() in ignored_users:
        logging.info(f"/u/{user} ignored")
        return

    redditor = reddit.redditor(user)

    new_user = False
    async with database.get_connection() as connection:
        redditor_id = None
        try:
            redditor_id = getattr(redditor, "id")
            first_comment = next(redditor.comments.new(limit=1))
        except (prawcore.exceptions.PrawcoreException, AttributeError, StopIteration):
            if redditor_id is None:
                logging.info(f"/u/{user} is not a valid redditor.")
                await connection.execute(
                    "UPDATE transcribers SET valid = FALSE WHERE name = $1", user
                )
            else:
                logging.info(f"/u/{user} has no comments, cannot fetch their stats.")
            return

        logging.info(f"Getting stats for /u/{user}")

        transcriber = await connection.fetchrow(
            "SELECT start_comment, end_comment, reference_comment, forwards, valid "
            "FROM transcribers WHERE name = $1",
            user,
        )

        new_user = transcriber is None

        if new_user is True:
            logging.info(f"New user: /u/{user}")
            await connection.execute(
                "INSERT INTO transcribers (name) VALUES ($1)", user
            )
            start_comment = end_comment = reference_comment = forwards, valid = None
        else:
            start_comment, end_comment, reference_comment, forwards, valid = (
                transcriber.values()
            )

        # If the user has gotten through all of these checks, they're valid.
        if valid is False or valid is None:
            await connection.execute(
                "UPDATE transcribers SET valid = TRUE WHERE name = $1", user
            )

        if reference_comment is not None:
            await update_gamma_count(user)

        if first_comment == start_comment:
            if forwards is True:
                logging.info(f"/u/{user} has no unchecked comments")
                return
        elif prioritize_new is True and forwards is True:
            forwards = True

        if start_comment is None:
            await connection.execute(
                "UPDATE transcribers SET start_comment = $1, end_comment = $1, "
                "forwards = FALSE WHERE name = $2",
                first_comment.id,
                user,
            )
            start_comment = end_comment = first_comment.id

            # The range is [start_comment, end_comment]; exclusive.
            # So the first comment has to be checked.
            if is_transcription(first_comment):
                return_value = await add_transcription(
                    user, first_comment, connection=connection
                )
            elif is_reference_comment(first_comment):
                reference_comment = first_comment.id
                logging.info(f"Setting reference comment to {reference_comment}")
                await connection.execute(
                    "UPDATE transcribers SET reference_comment = $1 WHERE name = $2",
                    reference_comment,
                    user,
                )
                await update_gamma_count(user)

        params = {}
        if forwards is True:
            if start_comment is not None:
                params = {"before": f"t1_{start_comment}"}
            else:
                params = {"after": f"t1_{first_comment}"}
                forwards = False
        else:
            if end_comment is not None:
                params = {"after": f"t1_{end_comment}"}
            else:
                params = {"after": f"t1_{first_comment}"}

        # Passing limit in the signature is overridden by the params argument
        params.update({"limit": limit, "type": "comments"})

        comment = start_comment if forwards is True else end_comment

        up_to = f"up to {limit} " if limit is not None else ""
        direction = "forwards" if forwards is True else "backwards"
        comment_with_id = (
            f" starting at comment with id: {comment}" if comment is not None else ""
        )

        logging.info(
            f"Fetching {up_to}comments for /u/{user} reading {direction}"
            f"{comment_with_id}."
        )
        try:
            comments = list(redditor.comments.new(params=params))
        except prawcore.exceptions.PrawcoreException:
            logging.warn(
                f"Exception {traceback.format_exc()}\n Setting /u/{user} to invalid"
            )

            await connection.execute(
                "UPDATE transcribers SET valid = FALSE WHERE name = $1", user
            )
            return

        reddit_comments = [reddit.comment(comment.id) for comment in comments]
        comment_count = len(reddit_comments)

        end_reached = f"Reached the end of /u/{user}'s comments."
        newest_reached = f"Reached /u/{user}'s newest comment."
        none_to_read = "No comments to read."
        if comment_count == 0:
            if forwards is True:
                logging.info(newest_reached)
                logging.info(none_to_read)
            else:
                logging.info(end_reached)
                logging.info(none_to_read)
                await connection.execute(
                    "UPDATE transcribers SET forwards = TRUE WHERE name = $1", user
                )
            return

        logging.info(f"Reading {comment_count} comments for /u/{user}.")

        transcriptions = 0
        new_transcriptions = 0
        for comment in reddit_comments:
            if is_transcription(comment):
                return_value = await add_transcription(
                    user, first_comment, connection=connection
                )

                transcriptions += 1
                if return_value != "INSERT 0 0":
                    new_transcriptions += 1
            elif (
                reference_comment is None
                and comment.subreddit == tor
                and comment.author_flair_text is not None
            ):
                reference_comment = comment.id
                logging.info(f"Setting reference comment to {reference_comment}")
                await connection.execute(
                    "UPDATE transcribers SET reference_comment = $1 WHERE name = $2",
                    reference_comment,
                    user,
                )
                await update_gamma_count(user)

        await connection.execute(
            "UPDATE transcribers SET counted_comments = counted_comments + $1 "
            "WHERE name = $2",
            comment_count,
            user,
        )

        s = "s" if transcriptions != 0 else ""
        new_s = "s" if new_transcriptions != 0 else ""
        logging.info(
            f"Found {transcriptions} total transcription{s}. "
            f"Added {new_transcriptions} new transcription{new_s}."
        )

        first_checked_comment = reddit_comments[0].id
        last_checked_comment = reddit_comments[-1].id

        if comment_count < limit:
            if forwards is True:
                logging.info(newest_reached)
            else:
                logging.info(end_reached)
                await connection.execute(
                    "UPDATE transcribers SET forwards = TRUE WHERE name = $1", user
                )
            return

        logging.info(
            f"Reached comment with id {last_checked_comment} "
            f"from {first_checked_comment}"
        )

        if forwards is True:
            await connection.execute(
                "UPDATE transcribers SET start_comment = $1 WHERE name = $2",
                last_checked_comment,
                user,
            )
        else:
            await connection.execute(
                "UPDATE transcribers SET end_comment = $1 WHERE name = $2",
                last_checked_comment,
                user,
            )

    logging.info(f"Done checking /u/{user}")


def is_reference_comment(comment):
    flair = comment.author_flair_text
    if comment.subreddit != tor or flair is None:
        return

    gamma = flair.split(" ")[0]

    try:
        int(gamma)
    except ValueError:
        return False
    else:
        return True


async def add_transcription(user, comment, connection=None):
    statement = (
        "INSERT INTO transcriptions "
        "(comment_id, transcriber, content, subreddit, found, created) "
        "VALUES ($1, $2, $3, $4, NOW(), $5) ON CONFLICT DO NOTHING"
    )
    arguments = (
        comment.id,
        user,
        comment.body,
        comment.subreddit.id,
        datetime.datetime.fromtimestamp(comment.created),
    )
    if connection is None:
        async with database.get_connection() as connection:
            return await connection.execute(statement, *arguments)
    else:
        return await connection.execute(statement, *arguments)


async def update_gamma_count(user: str):
    async with database.get_connection() as connection:
        reference_comment, old_gamma = await connection.fetchrow(
            "SELECT reference_comment, official_gamma_count FROM transcribers "
            "WHERE name = $1",
            user,
        )

        if reference_comment is None:
            logging.warn(f"Reference comment could not be found for /u/{user}")
            return

        reference_comment = reddit.comment(reference_comment)

        no_flair = False
        no_flair_message = (
            f"No flair on /u/{user}'s reference comment: {reference_comment}"
        )

        try:
            flair = reference_comment.author_flair_text
        except Exception:
            no_flair = True
        else:
            no_flair = flair == "" or flair is None

        if no_flair is True:
            if reference_comment is not None:
                await connection.execute(
                    "UPDATE transcribers SET reference_comment = NULL WHERE name = $1",
                    user,
                )

            logging.warn(no_flair_message)
            return

        try:
            official_gamma = int(flair.split(" ")[0])
        except ValueError:
            pass

        if old_gamma != official_gamma:
            if old_gamma is not None:
                logging.info(f"/u/{user} got from {old_gamma}Γ to {official_gamma}Γ")
            else:
                logging.info(
                    f"First gamma check for /u/{user} they have {official_gamma}Γ."
                )

            await connection.execute(
                "INSERT INTO new_gammas (transcriber, gamma, time) "
                "VALUES ($1, $2, NOW())",
                user,
                official_gamma,
            )

            await connection.execute(
                "UPDATE transcribers SET official_gamma_count = $1 WHERE name = $2",
                official_gamma,
                user,
            )

            await announce_gamma(user, old_gamma, official_gamma)
        elif old_gamma < official_gamma:
            logging.info(f"Old gamma is less than new gamma for /u/{user}")
        else:
            logging.info(f"/u/{user} has {official_gamma}Γ. It did not change.")


async def announce_gamma(user, before, after):
    async with database.get_connection() as connection:
        discord_id = await connection.fetchval(
            "SELECT discord_id FROM transcribers WHERE name = $1", user
        )

    if discord_id is not None:
        reference = f"<@{discord_id}>"
    else:
        reference = f"/u/{user}"

    gammas_channel = 387401723943059460

    # Bypasses some of the more tedious channel/guild object creation
    # and also guarantees that it'll work even if not in cache.
    if before is not None:
        await client.http.send_message(
            gammas_channel, f"{reference} got from {before}Γ to {after}Γ"
        )
    else:
        await client.http.send_message(
            gammas_channel, f"{reference} just got found! They have {after}Γ"
        )

    if before < 51 <= after:
        await client.http.send_message(
            gammas_channel, f"Congrats to {reference} for their green flair!"
        )
    elif before < 101 <= after:
        await client.http.send_message(
            gammas_channel, f"Teal flair? Not bad, {reference}!"
        )
    elif before < 251 <= after:
        await client.http.send_message(
            gammas_channel, f"{reference} got purple flair, amazing!"
        )
    elif before < 501 <= after:
        await client.http.send_message(
            gammas_channel,
            f"Give it up for the new owner of golden flair, {reference}!",
        )
    elif before < 1001 <= after:
        await client.http.send_message(
            gammas_channel, f"Holy guacamole, {reference} earned their diamond flair!"
        )
    elif before < 2501 <= after:
        await client.http.send_message(
            gammas_channel, f"Ruby flair! {reference}, that is absolutely amazing!"
        )
    elif before < 5000 <= after:
        await client.http.send_message(
            gammas_channel,
            f"We don't even have a flair name for this yet, {reference}! "
            "Congratulations for being one of the first.",
        )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    loop.run_until_complete(database.create_pool())

    logging.getLogger().setLevel(logging.INFO)

    try:
        loop.run_until_complete(client.login(passwords_and_tokens.discord_token))
        while True:
            loop.run_until_complete(analyze_all_users())
            logging.info("--- Round done ---")
            loop.run_until_complete(asyncio.sleep(60))
    finally:
        loop.run_until_complete(client.close())
        loop.run_until_complete(database.close_pool())
        loop.close()
