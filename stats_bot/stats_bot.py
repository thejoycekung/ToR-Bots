import asyncio
import logging
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
import traceback

from discord.client import _cleanup_loop
from discord.ext import commands

from . import passwords_and_tokens
from .helpers import database_reader

description = """A bot to show your ToR stats on the discord."""

# this specifies what extensions to load when the bot starts up
startup_extensions = [
    "stats_bot.cogs.text_commands",
    "stats_bot.cogs.graphs",
    "stats_bot.cogs.admin",
    "stats_bot.cogs.reactions",
    "stats_bot.cogs.routines",
    "stats_bot.cogs.handlers",
]

bot = commands.Bot(command_prefix="!", description=description)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception:
            logging.warn("Failed to load extension due to exception:")
            traceback.print_exc()

    logging.getLogger().setLevel(logging.INFO)

    loop.run_until_complete(database_reader.create_pool())

    try:
        loop.run_until_complete(bot.start(passwords_and_tokens.discord_token))
    except KeyboardInterrupt:
        loop.run_until_complete(bot.logout())
    finally:
        loop.run_until_complete(database_reader.close_pool())

        _cleanup_loop(bot.loop)
        loop.close()
