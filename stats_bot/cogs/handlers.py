import logging

from discord.ext import commands


class Handlers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx):
        logging.info(
            f"{ctx.author.display_name} ran {ctx.prefix}{ctx.invoked_with} "
            f"with message: {ctx.message.content}"
        )

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        logging.info(f"Finished running {ctx.prefix}{ctx.invoked_with}")


def setup(bot):
    bot.add_cog(Handlers(bot))
