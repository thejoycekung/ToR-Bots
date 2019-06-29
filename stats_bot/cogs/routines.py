import logging
import os

import discord.utils
import praw
from discord.ext import commands, tasks

from .. import passwords_and_tokens
from ..helpers import database_reader, add_user
from ..utils.permissions import is_owner

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent="Lornebot 0.0.1",
)

data_directory = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "data"))
leaderboard_path = os.path.join(data_directory, "leaderboard.txt")


async def refresh_leaderboard_internal(ctx):
    leaderboard_message = "**Leaderboard**\n\n"
    count = 0

    gammas = await database_reader.gammas()
    for name, flair in sorted(gammas, key=lambda x: x[1], reverse=True)[:50]:
        count += 1
        sanitized_name = discord.utils.escape_markdown(name)
        leaderboard_message += f"{count}. {sanitized_name}: {flair}\n"

    leaderboard_message += "\n*This Message will be refreshed to always be up-to-date*"

    try:
        with open(leaderboard_path, "r") as data:
            for i, message in enumerate(data):
                invalid_snowflake = (
                    "In leaderboard.text "
                    f"line {i+1} contains an invalid invalid message snowflake."
                )
                message = message.strip()
                if message != "":
                    if message.isdigit() is False:
                        logging.warn(invalid_snowflake)
                        continue

                    try:
                        message = int(message)
                    except ValueError:
                        logging.warn(invalid_snowflake)
                        continue

                    message = await ctx.fetch_message(message)

                    await message.edit(content=leaderboard_message)
    except FileNotFoundError:
        # Create file
        open(leaderboard_path, "a").close()


async def reset_leaderboard_internal():
    # Clears the file
    try:
        open(leaderboard_path, "w").close()
    except FileNotFoundError:
        open(leaderboard_path, "a").close()


class RoutineCog(commands.Cog, command_attrs={"hidden": True}):
    async def cog_check(self, ctx):
        return is_owner(ctx)

    def __init__(self, bot):
        self.bot = bot
        self.refresh_leaderboard_loop.start()

    def cog_unload(self):
        self.refresh_leaderboard_loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        TOR = 318_873_523_579_781_132
        BOT_COMMANDS = 372_168_291_617_079_296
        GAMMA_CHANNEL = 387_401_723_943_059_460

        self.gamma_channel = self.bot.get_channel(GAMMA_CHANNEL)
        self.bot_commands = self.bot.get_channel(BOT_COMMANDS)
        self.tor_guild = self.bot.get_guild(TOR)

        await self._add_members()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        logging.info(
            (
                f"Member joined, name: {member.display_name} id: {member.id}\n"
                "Adding them to database."
            )
        )
        await add_user(member.display_name, member.id)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.display_name == after.display_name:
            return

        logging.info(
            (
                f"Member with id: {before.id} changed their nickname "
                f"from {before.display_name} to {after.display_name}. "
                "Adding new name to database."
            )
        )
        await add_user(after.display_name, after.id)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.name == after.name:
            return

        logging.info(
            (
                f"User with id: {before.id} changed their username "
                f"from {before.name} to {after.name}. "
                "Adding new name to database."
            )
        )
        await add_user(after.name, after.id)

    @commands.command(hidden=True)
    async def add_all_members(self, ctx):
        message = await ctx.send("Adding all members in ToR to database...")

        await self._add_members()
        await message.edit(content="Added all members to database!")

    async def _add_members(self):
        logging.info("Adding ToR members to database...")

        if self.tor_guild is None:
            logging.info("Could not find guild.")
            return

        members = set(self.tor_guild.members)

        for member in members:
            await add_user(member.display_name, member.id)

        logging.info("Finished adding users.")

    @tasks.loop(seconds=60.0)
    async def refresh_leaderboard_loop(ctx):
        await refresh_leaderboard_internal(ctx)

    @commands.command()
    async def reset_leaderboard(self, ctx):
        message = await ctx.send("Resetting leaderboard...")
        await reset_leaderboard_internal()
        await message.edit(content="Reset leaderboard.")

    @commands.command()
    async def restart(self, ctx):
        await ctx.send("Restarting StatsBot")
        await self.bot.close()

    @commands.command()
    async def post_leaderboard(self, ctx):
        with open(leaderboard_path, "a") as data:
            message = await ctx.send("Waiting for refresh...")
            data.write(f"{message.id}\n")

        await refresh_leaderboard_internal(ctx)
        await ctx.send("Done!")

    @commands.command()
    async def set_leaderboard(self, ctx, *, message: discord.Message):
        with open(leaderboard_path, "a") as leaderboard_file:
            leaderboard_file.write(str(message.id))

        await ctx.send("Set leaderboard.")

    @set_leaderboard.error
    async def set_leaderboard_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("That isn't a valid message...")

    @commands.command()
    async def refresh_leaderboard(self, ctx):
        message = await ctx.send("Refreshing leaderboard...")

        await refresh_leaderboard_internal(ctx)

        await message.edit(content="Refreshed leaderboard.")


def setup(bot):
    bot.add_cog(RoutineCog(bot))
