import datetime

import praw
import prawcore
from discord.ext import commands

from .. import passwords_and_tokens
from ..helpers import get_redditor_name

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent="Lornebot 0.0.1",
    check_for_async=False
)


class Redditor(commands.Converter):
    async def convert(self, ctx: commands.Context, username: str):
        name = get_redditor_name(username)
        user = reddit.redditor(name)

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
