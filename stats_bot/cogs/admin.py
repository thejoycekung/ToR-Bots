# Some imports are for the globals in eval
import ast
import contextlib
import datetime
import inspect
import io
import logging
import platform
import socket
import textwrap
import time
import traceback

import asyncpg  # noqa: F401
import discord
import praw
from discord.ext import commands

from .. import passwords_and_tokens
from ..utils.permissions import is_owner

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent=passwords_and_tokens.user_agent,
)


cogload = time.time()


class Administration(commands.Cog, command_attrs={"hidden": True}):
    async def cog_check(self, ctx):
        return is_owner(ctx)

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        bootup = self.bot.get_channel(428_212_915_473_219_604)

        if bootup is not None:
            await bootup.send(
                "<@&428212811290771477>",
                embed=discord.Embed(
                    title="StatsBot Booted",
                    description=(
                        f"Booted in {round(time.time() - cogload)}s on hostname "
                        f"{socket.gethostname()}"
                    ),
                    colour=0x00FF00,
                    timestamp=datetime.datetime.now(),
                ),
            )

        servers = len(self.bot.guilds)
        users = len(set(self.bot.get_all_members()))
        plural = "s" if servers > 1 else ""

        logging.info(
            "=====================\n"
            f"Logged in as {self.bot.user.name} (ID: {self.bot.user.id}). Connected to"
            f" {servers} server{plural} | Connected to {users} users.\n"
            f"--------------\n"
            f"Current Discord.py Version: {discord.__version__} | "
            f"Current Python Version: {platform.python_version()}\n"
            f"--------------\n"
            f"Use this link to invite me: "
            f"https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}"
            "&scope=bot&permissions=8\n"
            f"====================="
        )

    @commands.command(hidden=True)
    async def load(self, ctx, extension_name: str):
        """Loads an extension."""

        try:
            self.bot.load_extension(extension_name)
        except (AttributeError, ImportError):
            await ctx.send(f"```py\n{traceback.format_exc()}\n```")
            return
        await ctx.send(f"{extension_name} loaded.")

    @commands.command(hidden=True)
    async def unload(self, ctx, extension_name: str):
        """Unloads an extension."""

        self.bot.unload_extension(extension_name)
        await ctx.send(f"{extension_name} unloaded.")

    @commands.command(hidden=True, aliases=["e"])
    async def eval(self, ctx, *, code: str):
        """Evaluates code."""

        if code.startswith("```") and code.endswith("```"):
            code = code.strip("```")
            code_casefold = code.casefold()
            if code_casefold.startswith("python"):
                code = code[6:]
            elif code_casefold.startswith("py"):
                code = code[2:]

        elif code.startswith("`") and code.endswith("`"):
            code = code.strip("`")

        indented_code = textwrap.indent(code, "  ")
        code_with_wrapper = f"async def _eval_wrapper():\n{indented_code}"

        python = "```py\n{}\n```"
        result = None

        environment = {
            "author": ctx.message.author,
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.message.channel,
            "guild": ctx.message.guild,
            "message": ctx.message,
            "server": ctx.message.guild,
        }

        environment.update(globals())

        return_value = eval_wrapper = None
        try:
            ast_tree = ast.parse(code_with_wrapper)

            # The first element should always be the _eval_wrapper definition
            # It also has it's own body.
            statements = ast_tree.body[0].body
            multi_line = len(statements) > 1 or "body" in statements[0]._fields

            # "compile" if multiple statements
            if multi_line:
                exec(code_with_wrapper, environment)
                eval_wrapper = environment["_eval_wrapper"]

            # Capture stdout
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                if multi_line:
                    return_value = await eval_wrapper()
                else:
                    coroutine = False
                    if code.startswith("await "):
                        code = code[6:]
                        coroutine = True
                    return_value = eval(code, environment)
                    if inspect.isawaitable(return_value) or coroutine is True:
                        return_value = await return_value

            result = stdout.getvalue() if return_value is None else return_value
            stdout.close()
        except Exception:
            result = traceback.format_exc()

        empty_result = python.format("")
        result_truncated = "\n[*result truncated*]"

        limit = 2000 - len(result_truncated) - len(empty_result)

        result = str(result)
        result = result[:limit]
        result = python.format(result)

        if len(result) >= 2000 - len(result_truncated):
            result += result_truncated

        if result is not None and result != "":
            await ctx.send(result)


def setup(bot):
    bot.add_cog(Administration(bot))
