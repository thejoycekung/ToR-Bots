import html
import typing

import discord
import praw
from discord.ext import commands

from .. import passwords_and_tokens
from ..helpers import add_user, database_reader, get_redditor_name
from ..utils.converters import Redditor
from ..utils.paginator import ToRPaginator

no_entries = "No entries were returned for your query."

client_session = None

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent="Lornebot 0.0.1",
    check_for_async=False
)

gamma_ranks = {
    "initiate": 1,
    "green": 50,
    "teal": 100,
    "purple": 250,
    "gold": 500,
    "diamond": 1000,
    "ruby": 2500,
    "topaz": 5000,
    "jade": 10000,
}


def minutes_to_human_readable(minutes):
    days, hours = divmod(minutes, 60 * 24)
    hours, minutes = divmod(hours, 60)
    units = []

    if days != 0:
        days_string = "days" if days != 1 else "day"
        units.append(f"{days} {days_string}")

    if hours != 0:
        hours_string = "hours" if hours != 1 else "hour"
        units.append(f"{hours} {hours_string}")

    if minutes != 0:
        minutes_string = "minutes" if minutes != 1 else "minute"
        units.append(f"{minutes} {minutes_string}")

    if len(units) == 3:
        days, hours, minutes = units
        return f"{days}, {hours}, and {minutes}"
    elif len(units) == 2:
        return units[0] + " and " + units[1]
    else:
        return units[0]


class TextCommands(commands.Cog):
    """Commands accessible to anyone."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["torstats", "transcriptions", "stats"])
    async def tor_stats(self, ctx, redditor: Redditor = None):
        author = get_redditor_name(ctx.message.author.display_name)
        username = author if redditor is None else redditor.name

        stats = await database_reader.fetch_stats(username)

        if stats is None or len(stats) != 10:
            if redditor is None or username.casefold() == author.casefold():
                await ctx.send("I'm working on adding you!")
                await add_user(username, ctx.message.author.id)
            else:
                await ctx.send("I don't know that user, sorry!")
                await add_user(username, None)

            return

        (
            comment_count,
            official_gammas,
            transcription_count,
            character_count,
            upvotes,
            good_bot,
            bad_bot,
            good_human,
            bad_human,
            valid,
        ) = stats

        if valid is False:
            await ctx.send(
                "That user is invalid, tell Lornescri if you don't think so."
            )
            return
        elif transcription_count is None or transcription_count == 0:
            if redditor is None or username.casefold() == author.casefold():
                await ctx.send(
                    "I haven't found any transcriptions for you. "
                    "Have you transcribed anything?"
                )
            else:
                await ctx.send(
                    "I haven't found that user's transcriptions yet "
                    "or they may not have any."
                )
            return

        kumas = await database_reader.kumas()
        if kumas is not None and official_gammas is not None:
            KLJ = (
                f"{official_gammas / kumas:.2f} KLJ"
                if official_gammas / kumas >= 1
                else f"{1000 * official_gammas / kumas:.2f} mKLJ"
            )
        else:
            KLJ = "N/A KLJ"

        relation = (
            "your"
            if redditor is None or username.casefold() == author.casefold()
            else "their"
        )
        character_average = round(character_count / transcription_count, 2)
        upvote_average = round(upvotes / transcription_count, 2)
        good_bot_average = round(good_bot / transcription_count, 2)
        bad_bot_average = round(bad_bot / transcription_count, 2)
        good_human_average = round(good_human / transcription_count, 2)
        bad_human_average = round(bad_human / transcription_count, 2)
        stats = (
            f"*I counted {comment_count} of {relation} total comments*\n"
            f"**Official Γ count**: {official_gammas} (~ "
            f"{KLJ})\n"
            f"**Number of transcriptions I see**: {transcription_count}\n"
            f"**Total characters**: {character_count} "
            f"(*{character_average} per transc.*)\n"
            f"**Total upvotes**: {upvotes} (*{upvote_average} per transc.*)\n"
            f"**Good Bot**: {good_bot} (*{good_bot_average} per transc.*)\n"
            f"**Bad Bot**: {bad_bot} (*{bad_bot_average} per transc.*)\n"
            f"**Good Human**: {good_human} (*{good_human_average} per transc.*)\n"
            f"**Bad Human**: {bad_human} (*{bad_human_average} per transc.*)"
        )

        embed = discord.Embed(title=f"Stats for /u/{username}", description=stats)
        await ctx.send(embed=embed)

    async def find(self, source):
        p = reddit.submission(url=source)
        tor = reddit.subreddit("TranscribersOfReddit")
        archive = reddit.subreddit("tor_archive")
        for i in tor.search(
            p.subreddit.display_name + " | Image | " + p.title, limit=50
        ):
            s = reddit.submission(url=i.url)
            if s.id == p.id:
                return reddit.submission(url=i.url)
        for i in archive.search(
            p.subreddit.display_name + " | Image | " + p.title, limit=50
        ):
            s = reddit.submission(url=reddit.submission(url=i.url).url)
            if s.id == p.id:
                return reddit.submission(url=i.url)
        return None

    async def find_transcriber(self, tor_thread):
        def get_nested_done_comment(comment):
            for reply in comment.replies:
                if reply.author is None:
                    continue
                if (
                    (reply.author.name not in ["transcribot", "transcribersofreddit"])
                    and ("done" in reply.body.casefold())
                    or ("deno" in reply.body.casefold())
                ):
                    return reply
                if len(reply.replies):
                    return get_nested_done_comment(reply)

        def get_done_comment(submission):
            for comment in submission.comments:
                if comment.author is None:
                    continue
                elif comment.author.name.casefold() == "transcribot":
                    continue
                elif comment.author.name.casefold() == "transcribersofreddit":
                    comment = get_nested_done_comment(comment)
                    if comment is not None:
                        return comment
                    continue
                if ("done" in comment.body.casefold()) or (
                    "deno" in comment.body.casefold()
                ):
                    return comment
            return None

        comment = get_done_comment(tor_thread)
        if comment is not None:
            return comment.get("author")

    @commands.command()
    async def source(self, ctx, post_url):
        tor_thread = await self.find(post_url)
        if tor_thread is None:
            await ctx.send(
                "I couldn't find that :( I sometimes struggle with generically "
                "labelled submissions like me_irl"
            )
            return

        thread = tor_thread.title.split("|", 2)[2]

        embed = discord.Embed(title=thread, url=tor_thread.shortlink)

        embed.add_field(name="Flair", value=tor_thread.link_flair_text, inline=True)

        if tor_thread.link_flair_text == "Completed!":
            transcriber = await self.try_find_transcriber(tor_thread)
            if transcriber:
                embed.add_field(
                    name="Transcriber", value="/u/" + transcriber.name, inline=True
                )

        embed.add_field(name="ToR Thread", value=tor_thread.shortlink, inline=True)

        await ctx.send(embed=embed)

    @commands.command(aliases=["allstats"])
    async def all_stats(self, ctx):
        all_stats = await database_reader.fetch_all_stats()

        if all_stats is None:
            await ctx.send("Couldn't find any stats for the server :(")
            return

        transcriptions, character_count, upvotes, *rest = all_stats
        good_bot, bad_bot, good_human, bad_human = rest

        total_gammas = await database_reader.get_total_gammas()
        kumas = await database_reader.kumas()

        if kumas is not None:
            KLJ = round(total_gammas / kumas, 2)
        else:
            KLJ = "N/A"

        all_stats_description = (
            f"*Number of transcriptions I see: {transcriptions}*\n"
            f"**Total Γ count**: {total_gammas} (~ {KLJ} KLJ)\n"
            f"**Character count**: {character_count}\n"
            f"**Upvotes**: {upvotes}\n"
            f"**Good Bot**: {good_bot}\n"
            f"**Bad Bot**: {bad_bot}\n"
            f"**Good Human**: {good_human}\n"
            f"**Bad Human**: {bad_human}"
        )

        embed = discord.Embed(
            title="Stats for everyone on Discord", description=all_stats_description
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=["serverinfo"])
    async def server_info(self, ctx):
        await ctx.send("This is a good server with good persons")

    @commands.command(aliases=["leaderboard", "lb"])
    async def gammas(self, ctx, redditor: Redditor = None, context=3):
        if context > 10:
            await ctx.send(
                "To prevent spam you can't get context larger than 10 users."
            )
            return

        username = (
            redditor.name
            if redditor is not None
            else get_redditor_name(ctx.message.author.display_name)
        )
        leaderboard = []
        top_leaderboard_size = 5

        all_gammas = await database_reader.gammas()

        # Sort by gamma count
        sorted_gammas = sorted(
            all_gammas, key=lambda item: item["official_gamma_count"], reverse=True
        )

        all_gamma_count = sum(item["official_gamma_count"] for item in all_gammas)

        user_index = next(
            (
                i
                for i, item in enumerate(sorted_gammas)
                if item["name"].casefold() == username.casefold()
            ),
            None,
        )

        i = 0
        while i < top_leaderboard_size or (
            user_index is not None and i < user_index + context
        ):
            name, official_gamma = sorted_gammas[i]

            escaped_name = discord.utils.escape_markdown(name)
            user_row = f"{i + 1}. {escaped_name}: {official_gamma}"

            if name.casefold() == username.casefold():
                user_row = f"**{user_row}**"

            leaderboard.append(user_row)

            # Jump to user component.
            if (
                i == top_leaderboard_size
                and user_index is not None
                and user_index - context > top_leaderboard_size
            ):
                i = user_index - context
                leaderboard.append("\n...\n")

            i += 1

        leaderboard.append(f"\nSum of all transcriptions: {all_gamma_count}Γ")

        await ctx.send(
            embed=discord.Embed(title="Gammas", description="\n".join(leaderboard))
        )

    @commands.command(hidden=False)
    async def permalink(self, ctx, thread: str):
        await ctx.send(
            (
                "This command has been temporarily disabled due to a "
                "blocking code issue from rate limits."
            )
        )
        return

        await ctx.send("https://reddit.com" + reddit.comment(thread).permalink)

    @permalink.error
    async def permalink_error(self, ctx, error):
        await ctx.send(
            "That caused an error! Are you sure you provided a valid comment ID?"
        )

    @commands.command(hidden=True)
    async def goodbad(self, ctx):
        await ctx.send(
            f"This command is deprecated, you can use `{ctx.clean_prefix}torstats` now."
        )

    @commands.command(hidden=True)
    async def where(self, ctx, *, looking_for):

        redditor_name = get_redditor_name(ctx.message.author.display_name)
        comments = await database_reader.find_comments(looking_for, name=redditor_name)

        comments_context = find_entries(comments, looking_for)

        if len(comments_context) == 0:
            await ctx.send(no_entries)
            return

        paginator = ToRPaginator(
            title=f"Where `{looking_for}`",
            embed=True,
            entries=comments_context,
            length=5,
        )

        await paginator.start(ctx)

    @commands.command(hidden=True)
    async def all_where(self, ctx, *, looking_for):
        comments = await database_reader.find_comments(looking_for)

        comments_context = find_entries(comments, looking_for)

        if len(comments_context) == 0:
            await ctx.send(no_entries)
            return

        paginator = ToRPaginator(
            title=f"All where `{looking_for}`",
            embed=True,
            entries=comments_context,
            length=5,
        )

        await paginator.start(ctx)

    @commands.command()
    async def progress(
        self, ctx, redditor: typing.Optional[Redditor] = None, hours: int = 24
    ):
        """
        Returns your progress along the 100/24 way
        """

        if hours > 999:
            await ctx.send(f"I dunno ∞ in {hours} hours? You better do it now.")
            return

        name = (
            get_redditor_name(ctx.message.author.display_name)
            if redditor is None
            else redditor.name
        )

        imaginary_progress_bar = "###[iiiiiiiiii]"
        blank_progress_bar = "[----------]"
        full_progress = "[##########]"
        overflowed_progress = "[##########]####"
        moly_overflowed_progress = "[##########]#####"
        stop_overflowed_progress = "[##########]######"
        help_overflowed_progress = "[##########]######"
        witty_overflowed_progress = "[##########]#######"

        if hours == 0:
            await ctx.send(
                f"`{blank_progress_bar}` - What'd you expect? "
                "Virtual ~~particles~~ transcriptions?"
            )
            return
        elif hours < 0:
            await ctx.send(f"`{imaginary_progress_bar}` - How'd you manage that?")
            return

        transcription_count = await database_reader.get_last_x_hours(name, hours)
        bars = transcription_count // 10

        if transcription_count is None:
            await ctx.send(
                "Looks like something went wrong; I can't find your transcriptions."
            )
            return

        if transcription_count == 0:
            progress = (
                f"`{blank_progress_bar}` - You know exactly how many you've done, "
                "you slacker."
            )
        elif hours != 24:
            progress = (
                f"You've done {transcription_count} transcriptions "
                f"in the last {hours} hours!"
            )
        elif transcription_count < 100:
            progress_bar = f"[{'#' * bars}{'-' * (10 - bars)}]"

            progress = (
                f"`{progress_bar}` - You've done {transcription_count} transcriptions "
                f"in the last {hours} hours. Keep going, you can do it!"
            )
        elif transcription_count == 100:
            progress = (
                f"`{full_progress}` - The little one has only gone and done it! You've "
                "done 100 / 24 :D"
            )
        elif 100 < transcription_count < 200:
            progress = (
                f"`{overflowed_progress}` - holy hecc, you've done "
                f"{transcription_count} transcriptions in 24 hours :O. "
                "That's a lot of transcriptions in 24 hours."
            )
        elif 200 < transcription_count < 300:
            progress = (
                f"`{moly_overflowed_progress}` - holy moly hecc, you've done "
                f"{transcription_count} transcriptions in 24 hours :O! "
                "That's a ton of transcriptions in 24 hours."
            )
        elif 300 < transcription_count < 400:
            progress = (
                f"`{stop_overflowed_progress}` - please stop, you've done "
                f"{transcription_count} transcriptions in 24 hours. "
                "That's too many transcriptions in 24 hours."
            )
        elif 400 < transcription_count < 500:
            progress = (
                f"`{help_overflowed_progress}` - I think you need help, "
                f"you've done {transcription_count} transcriptions in 24 hours, "
                "that's just... so many transcriptions!"
            )
        else:
            progress = (
                f"`{witty_overflowed_progress}` - I'm running out of witty "
                "things to convey that this is really impressive and really concerning... "
                f"Seriously you've done {transcription_count} transcriptions in 24 hours."
            )

        await ctx.send(progress)

    @commands.command(aliases=["to"])
    async def until(self, ctx, future_gamma: str):
        if future_gamma.isdigit():
            try:
                future_gamma = int(future_gamma)
            except ValueError:
                await ctx.send("Please input a valid integer!")
                return
        else:
            rank = future_gamma.casefold()
            if rank not in gamma_ranks:
                await ctx.send("That's not a valid rank or number.")
                return

            future_gamma = gamma_ranks[rank]

        name = get_redditor_name(ctx.message.author.display_name)

        # The transcriptions are set over 48 hours to give more accurate results
        transcription_count = await database_reader.get_last_x_hours(name, 48)

        if transcription_count is None:
            await ctx.send("I don't know that user yet, sorry")
            return

        gamma = await database_reader.fetch_official_gamma_count(name)
        if gamma is None:
            await ctx.send("I can't find your gamma count, something isn't working...")
            return

        difference = future_gamma - gamma
        if difference <= 0:
            await ctx.send(
                "Please provide a gamma that's higher than your current count 😛"
            )
            return

        if difference > 100_000:
            return await ctx.send("Probably 30 years or something, idk")

        if transcription_count == 0:
            motivation = (
                "to get your butt into gear and start transcribing ;)"
                if ctx.message.author.id == "280001404020588544"  # is person jabba?
                else f"to get to Γ {future_gamma} "
                "(you haven't done any in the past 48 hours)"
            )

            await ctx.send(
                (
                    f"From your rate over the past 48 hours, I estimate that it will "
                    f"take you `∞ days, ∞ hours, ∞ minutes` {motivation}"
                )
            )
            return

        # turn from transcriptions per 48hr to per minute
        rate_per_minute = transcription_count / (2 * 24 * 60)

        minutes = round(difference / rate_per_minute)

        human_time = minutes_to_human_readable(minutes)

        await ctx.send(
            (
                f"From your rate over the past 48 hours, I estimate that it will take "
                f"you `{human_time}` to get from Γ{gamma} to Γ{future_gamma}"
            )
        )

    @commands.command(hidden=False)
    async def ping(self, ctx):
        await ctx.send("Pong!")


def find_entries(results, looking_for, offset=25):
    entries = []

    for i, (comment_id, content, permalink) in enumerate(results):
        content = content.casefold()

        index = content.find(looking_for.casefold())
        start = index - offset
        end = index + len(looking_for) + offset

        context = content[start:end]

        entries.append(
            f"{i+1}. https://reddit.com{html.unescape(permalink)}\n"
            f"```...{context}...```"
        )

    return entries


def setup(bot):
    bot.add_cog(TextCommands(bot))
