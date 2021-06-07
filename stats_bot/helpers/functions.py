import re
from . import database_reader


def get_redditor_name(name):
    """Extracts a redditor's name from nicknames.
    Ignores /u/ or u/ and then reads up to a space, comma or a pipe character.
    """
    match = re.match("^(?:/u/|u/)?([^\s|]*)", name).group(1)
    print("Match for "+name+" is "+str(match));
    return match


async def add_user(user, user_snowflake):
    await database_reader.add_user(get_redditor_name(user), user_snowflake)
