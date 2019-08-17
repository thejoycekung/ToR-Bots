import datetime
import re

import praw
import prawcore
from discord.ext import commands

from .. import passwords_and_tokens
from ..helpers import get_redditor_name

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent=passwords_and_tokens.user_agent,
)


class Redditor(commands.Converter):
    async def convert(self, ctx: commands.Context, username: str):
        # Regex taken directly from the source of discord.py the rest of the
        # user id conversion is inspired from it.
        # See discord.py/discord/ext/commands/converter.py L117
        match = re.match(r"<@!?([0-9]+)>$", username)
        if match is not None:
            user_id = int(match.group(1))
            member = ctx.guild.get_member(user_id)
            username = get_redditor_name(member.display_name)
        else:
            # Full member name recognition shouldn't be supported.
            if username.startswith("/u/"):
                username = username[3:]
            elif username.startswith("u/"):
                username = username[2:]

        user = reddit.redditor(username)

        try:
            next(user.comments.new(limit=1))
        except (StopIteration, prawcore.exceptions.PrawcoreException):
            raise commands.BadArgument("Redditor is either invalid or has no comments.")

        return user


class Date(commands.Converter):
    async def convert(self, ctx, date: str):
        try:
            return datetime.datetime.strptime(date, r"%Y-%m-%d").date()
        except ValueError as exception:
            raise commands.BadArgument("Date is not valid.") from exception
