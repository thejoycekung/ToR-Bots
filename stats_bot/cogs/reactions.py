import os
import random

from discord.ext import commands

insults = None


def insult():
    if insults is None:
        get_insults()

    return (
        f"Thou {random.choice(insults[0])} {random.choice(insults[1])} "
        f"{random.choice(insults[2])}!"
    )


class ReactionsReactor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        content = message.content.casefold()

        if "good bot" in content:
            await message.add_reaction("\U0001F916")

        if "bad bot" in content:
            await message.add_reaction("\U0001F622")

        if "jarvin" in content:
            await message.add_reaction("\U0001F44D")

        if "toria" in content:
            await message.add_reaction("\U0001F618")

        if "send rudes" in content:
            await message.channel.send(insult())


def get_insults():
    insults = [[], [], []]

    # Pulls a list of insulting words from a series of files.

    data_directory = os.path.abspath(
        os.path.join(__file__, os.pardir, os.pardir, "data")
    )
    with open(os.path.join(data_directory, "insults1.txt"), "r") as insult1:
        for line in insult1:
            insults[0].append(line.strip())

    with open(os.path.join(data_directory, "insults2.txt"), "r") as insult2:
        for line in insult2:
            insults[1].append(line.strip())

    with open(os.path.join(data_directory, "insults3.txt"), "r") as insult3:
        for line in insult3:
            insults[2].append(line.strip())


def setup(bot):
    bot.add_cog(ReactionsReactor(bot))
