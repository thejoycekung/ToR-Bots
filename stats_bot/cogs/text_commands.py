import html
import math
import typing

import discord
import praw
from discord.ext import buttons, commands

from .. import passwords_and_tokens
from ..helpers import add_user, database_reader, get_redditor_name
from ..utils.converters import Redditor


class WherePaginator(buttons.Paginator):
    async def _paginate(self, ctx: commands.Context):
        # This is a copy and paste from the buttons.py source code.
        # The only relevant change is adding the footer.
        if not self.entries and not self.extra_pages:
            raise AttributeError(
                "You must provide at least one entry or page for pagination."
            )

        if self.entries:
            self.entries = [self.formatting(entry) for entry in self.entries]
            entries = list(self.chunker())
        else:
            entries = []

        entry_count = len(self.entries)
        for i, chunk in enumerate(entries):
            if self.use_embed is False:
                self._pages.append(self.joiner.join(chunk))
            else:
                pages = math.ceil(entry_count / self.length) + len(self.extra_pages)
                plural = "ies" if entry_count != 1 else "y"

                embed = discord.Embed(
                    title=self.title,
                    description=self.joiner.join(chunk),
                    colour=self.colour,
                )

                embed.set_footer(
                    text=f"Page {i+1}/{pages} ({entry_count} entr{plural})"
                )

                if self.thumbnail:
                    embed.set_thumbnail(url=self.thumbnail)

                self._pages.append(embed)

        self._pages = self._pages + self.extra_pages

        if isinstance(self._pages[0], discord.Embed):
            self.page = await ctx.send(embed=self._pages[0])
        else:
            self.page = await ctx.send(self._pages[0])

        self._session_task = ctx.bot.loop.create_task(self._session(ctx))

    async def cancel(self, ctx):
        try:
            await self.page.clear_reactions()
        except discord.Forbidden:
            for button in self._buttons:
                try:
                    await self.page.remove_reaction(button, self.ctx.bot)
                except discord.HTTPException:
                    pass

        embed = self.page.embed
        embed.set_footer(text=f"{embed.footer} Session Cancelled.")

        await self.page.edit(embed=embed)

        self._cancelled = True
        self._session_task.cancel()


client_session = None

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent="Lornebot 0.0.1",
)

gamma_ranks = {
    "initiate": 1,
    "green": 51,
    "teal": 101,
    "purple": 251,
    "gold": 501,
    "diamond": 1001,
    "ruby": 2501,
}


def minutes_to_human_readable(minutes):
    days, hours = divmod(minutes, 60 * 24)
    hours, minutes = divmod(hours, 60)
    human_readable = []

    if days != 0:
        days_string = "days" if days != 1 else "day"
        human_readable.append(f"{days} {days_string}")

    if hours != 0:
        hours_string = "hours" if hours != 1 else "hour"
        human_readable.append(f"{hours} {hours_string}")

    if minutes != 0:
        minutes_string = "minutes" if minutes != 1 else "minute"
        human_readable.append(f"{minutes} {minutes_string}")

    if len(human_readable) == 3:
        human_readable[-1] = "and " + human_readable[-1]
        return ", ".join(human_readable)
    elif len(human_readable) == 2:
        return " and ".join(human_readable)
    else:
        return human_readable[0]


class TextCommands(commands.Cog):
    """Commands accessible to anyone."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["torstats", "transcriptions", "stats"])
    async def tor_stats(self, ctx, redditor: Redditor = None):
        user_redditor_name = get_redditor_name(ctx.message.author.display_name)
        name = user_redditor_name if redditor is None else redditor.name

        stats = await database_reader.fetch_stats(name)

        if stats is None or len(stats) != 10:
            if redditor is None or redditor == user_redditor_name:
                await ctx.send("I'm working on adding you!")
                await add_user(name, ctx.message.author.id)
            else:
                await ctx.send("I don't know that user, sorry!")
                await add_user(name, None)

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
            if redditor is None or redditor == user_redditor_name:
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
            "your" if redditor is None or redditor == user_redditor_name else "their"
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

        embed = discord.Embed(title=f"Stats for /u/{name}", description=stats)
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
                    and ("done" in reply.body.lower())
                    or ("deno" in reply.body.lower())
                ):
                    return reply
                if len(reply.replies):
                    return get_nested_done_comment(reply)

        def get_done_comment(submission):
            for comment in submission.comments:
                if not comment.author:
                    continue
                if comment.author.name == "transcribot":
                    continue
                if comment.author.name == "transcribersofreddit":
                    c = get_nested_done_comment(comment)
                    if c:
                        return c
                    continue
                if ("done" in comment.body.lower()) or ("deno" in comment.body.lower()):
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

    @commands.command()
    async def gammas(self, ctx, context=3):
        if context > 10:
            await ctx.send(
                "To prevent spam you can't get context larger than 10 users."
            )
            return

        leaderboard = []
        redditor = get_redditor_name(ctx.message.author.display_name)

        all_gammas = await database_reader.gammas()

        # Sort by gamma count
        sorted_gammas = sorted(
            all_gammas, key=lambda item: item["official_gamma_count"], reverse=True
        )
        sorted_names = [item["name"].casefold() for item in sorted_gammas]

        all_gamma_count = sum(item["official_gamma_count"] for item in all_gammas)

        user_exists = redditor.casefold() in sorted_names
        user_index = None
        user_in_leaderboard = False

        top_leaderboard_size = 5

        if user_exists is True:
            user_index = sorted_names.index(redditor.casefold())
            user_in_leaderboard = user_index <= top_leaderboard_size

        if user_in_leaderboard is True:
            # Pad the main leaderboard size if the user is in it.
            top_leaderboard_size += top_leaderboard_size - user_index

        max_size = len(all_gammas)
        top_leaderboard_size = min(top_leaderboard_size, max_size)

        for i, (name, official_gamma) in enumerate(
            sorted_gammas[:top_leaderboard_size]
        ):
            escaped_name = discord.utils.escape_markdown(name)
            user_row = f"{i + 1}. {escaped_name}: {official_gamma}"

            if name == redditor:
                user_row = f"**{user_row}**"

            leaderboard.append(user_row)

        if user_exists is True and user_in_leaderboard is False:
            offset = user_index - top_leaderboard_size
            if offset > context:
                leaderboard.append("\n...\n")

            # Clamp between the max leaderboard size and the max total size.
            start_index = min(max(user_index - context, top_leaderboard_size), max_size)
            end_index = min(user_index + context, max_size)
            for i, (name, official_gamma) in enumerate(
                sorted_gammas[start_index:end_index]
            ):
                escaped_name = discord.utils.escape_markdown(name)
                user_row = f"{start_index + i + 1}. {escaped_name}: {official_gamma}"

                if name == redditor:
                    user_row = f"**{user_row}**"

                leaderboard.append(user_row)

        leaderboard.append(f"\nSum of all transcriptions: {all_gamma_count} Γ")

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

        paginator = WherePaginator(
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

        paginator = WherePaginator(
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

        if hours != 24:
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
        elif transcription_count > 300:
            progress = (
                f"`{stop_overflowed_progress}` - please stop, you've done "
                f"{transcription_count} transcriptions in 24 hours. "
                "That's too many transcriptions in 24 hours."
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

        index = content.find(looking_for.lower())
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
