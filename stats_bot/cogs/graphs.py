import typing

import discord
from discord.ext import commands

from ..helpers import plots
from ..helpers import get_redditor_name, redditor_or_author
from ..utils.converters import Date, Redditor

NO_HISTORY_AVAILABLE = (
    f"I can't find any transcriptions for them, sorry! "
    "They may have no transcriptions or I may not have found their transcriptions yet."
)

NO_HISTORY_AVAILABLE_FOR_YOU = (
    "I can't find any transcriptions for you, sorry! "
    "I'm probably still searching for your transcriptions or you may not have done any."
)

NO_HISTORY_AVAILABLE_FOR_SOMEONE = (
    "I can't find any transcriptions for someone you listed, sorry! "
    "They may not have any transcriptions or I may still be searching for "
    "their transcriptions."
)

NO_TRANSCRIPTIONS_DURING_TIME = (
    "It doesn't look like you did any transcriptions during that time. Try widening "
    "the times to a period of time where you did 2 or more transcriptions."
)


class GraphCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def history(
        self,
        ctx,
        redditors: commands.Greedy[Redditor] = None,
        start: typing.Optional[Date] = None,
        end: typing.Optional[Date] = None,
    ):
        single_user = redditors is None or len(redditors) < 2
        if single_user is True:
            username = await redditor_or_author(ctx, redditors[0])

            history_plot = await plots.plot_history(username, start, end, False)
        else:
            usernames = [redditor.name for redditor in redditors]
            history_plot = await plots.plot_multi_history(usernames, start, end)

        if history_plot is None:
            if start is not None or end is not None:
                await ctx.send(NO_TRANSCRIPTIONS_DURING_TIME)
            else:
                author = get_redditor_name(ctx.message.author.display_name)
                if single_user is True:
                    if username.casefold() == author.casefold():
                        await ctx.send(NO_HISTORY_AVAILABLE_FOR_YOU)
                    else:
                        await ctx.send(NO_HISTORY_AVAILABLE)
                else:
                    await ctx.send(NO_HISTORY_AVAILABLE_FOR_SOMEONE)
        else:
            await ctx.send(file=discord.File(history_plot, "history_plot.png"))

    @commands.command()
    async def context_history(
        self,
        ctx,
        redditor: typing.Optional[Redditor] = None,
        start: typing.Optional[Date] = None,
        end: typing.Optional[Date] = None,
    ):
        name = await redditor_or_author(ctx, redditor)
        context_history_plot = await plots.plot_history(name, start, end, True)

        if context_history_plot is None:
            if start is not None or end is not None:
                await ctx.send(NO_TRANSCRIPTIONS_DURING_TIME)
            else:
                await ctx.send(NO_HISTORY_AVAILABLE)
        else:
            await ctx.send(
                file=discord.File(context_history_plot, "context_history_plot.png")
            )

    @commands.command()
    async def all_history(self, ctx, start: Date = None, end: Date = None):
        all_history_plot = await plots.plot_all_history(start, end)
        if not all_history_plot:
            await ctx.send("No history avaliable, sorry!")

        else:
            await ctx.send(file=discord.File(all_history_plot, "all_history_plot.png"))

    @commands.command()
    async def distribution(self, ctx):
        distribution_plot = await plots.plot_distribution()
        if distribution_plot is None:
            await ctx.send("No distribution available, sorry!")
        else:
            await ctx.send(
                file=discord.File(distribution_plot, "distribution_plot.png")
            )

    @commands.command()
    async def rate(
        self,
        ctx,
        redditor: typing.Optional[Redditor] = None,
        start: typing.Optional[Date] = None,
        end: typing.Optional[Date] = None,
    ):
        username = await redditor_or_author(ctx, redditor)

        rate_plot = await plots.plot_rate(username, start, end)
        if rate_plot is None:
            author = get_redditor_name(ctx.message.author.display_name)
            if username.casefold() == author.casefold():
                await ctx.send(NO_HISTORY_AVAILABLE_FOR_YOU)
            else:
                await ctx.send(NO_HISTORY_AVAILABLE)
        else:
            await ctx.send(file=discord.File(rate_plot, "rate_plot.png"))

    @commands.command()
    async def all_rate(self, ctx):
        all_rate_plot = await plots.plot_all_rate()
        if all_rate_plot is None:
            await ctx.send(NO_HISTORY_AVAILABLE)
        else:
            await ctx.send(file=discord.File(all_rate_plot, "all_rate_plot.png"))


def setup(bot):
    bot.add_cog(GraphCommands(bot))
