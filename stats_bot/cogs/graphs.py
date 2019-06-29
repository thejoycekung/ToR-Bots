import typing

import discord
from discord.ext import commands

from ..helpers import plots
from ..helpers import get_redditor_name
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
            name = (
                ctx.message.author.display_name
                if redditors is None
                else redditors[0].name
            )
            name = get_redditor_name(name)
            history_plot = await plots.plot_history(name, start, end, False)
        else:
            names = [redditor.name for redditor in redditors]
            history_plot = await plots.plot_multi_history(names, start, end)

        if history_plot is None:
            if start is not None or end is not None:
                await ctx.send(NO_TRANSCRIPTIONS_DURING_TIME)
            else:
                if single_user is True:
                    if name == ctx.message.author.display_name:
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
        name = (
            get_redditor_name(ctx.message.author.display_name)
            if redditor is None
            else redditor.name
        )
        context_history_plot = await plots.plot_history(
            get_redditor_name(name), start, end, True
        )

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
        name = ctx.message.author.display_name if redditor is None else redditor.name
        name = get_redditor_name(name)

        rate_plot = await plots.plot_rate(name, start, end)
        if rate_plot is None:
            if name == ctx.message.author.display_name:
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
