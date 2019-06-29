import re
from . import database_reader


def get_redditor_name(name):
    """Extracts a redditor's name from nicknames.
    Ignores /u/ or u/ and then reads up to a space, comma or a pipe character.
    """
    return re.match("^(?:/u/|u/)?([^\s|]*)", name).group(1)


async def add_user(user, user_snowflake):
    await database_reader.add_user(get_redditor_name(user), user_snowflake)
