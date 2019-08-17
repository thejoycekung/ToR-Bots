import re

from discord import commands

from ..utils import Redditor


async def redditor_or_author(ctx: commands.Context, name):
    if name is None:
        return redditor_from_user(ctx.message.author.display_name)

    return get_redditor_name(name)


async def redditor_from_user(ctx: commands.Context, name=None):
    """Uses the Redditor converter to validate a username."""

    name = get_redditor_name(name)

    try:
        await Redditor().convert(ctx, name)
    except commands.BadArgument:
        return

    return name


def get_redditor_name(name):
    """Extracts a redditor's name from nicknames.
    After /u/ everything up until whitespace or a comma or pipe character is the name.
    The Transcribers of Reddit discord rules enforces this name scheme.
    """

    return re.match("^(?:/u/)([^\s|]*)", name).group(1)
