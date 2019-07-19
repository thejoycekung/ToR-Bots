import math

import discord
from discord.ext import buttons, commands


class ToRPaginator(buttons.Paginator):
    async def _paginate(self, ctx: commands.Context):
        # This is a copy and paste from the buttons.py source code.
        # The only relevant change is adding the footer.
        if not self.entries and not self.extra_pages:
            raise AttributeError(
                "You must provide at least one entry or page for pagination."
            )

        if self.entries:
            self.entries = [self.formatting(entry) for entry in self.entries]
            entries = list(self.chunker())
        else:
            entries = []

        entry_count = len(self.entries)
        for i, chunk in enumerate(entries):
            if self.use_embed is False:
                self._pages.append(self.joiner.join(chunk))
            else:
                pages = math.ceil(entry_count / self.length) + len(self.extra_pages)
                plural = "ies" if entry_count != 1 else "y"

                embed = discord.Embed(
                    title=self.title,
                    description=self.joiner.join(chunk),
                    colour=self.colour,
                )

                embed.set_footer(
                    text=f"Page {i+1}/{pages} ({entry_count} entr{plural})"
                )

                if self.thumbnail:
                    embed.set_thumbnail(url=self.thumbnail)

                self._pages.append(embed)

        self._pages = self._pages + self.extra_pages

        if isinstance(self._pages[0], discord.Embed):
            self.page = await ctx.send(embed=self._pages[0])
        else:
            self.page = await ctx.send(self._pages[0])

        self._session_task = ctx.bot.loop.create_task(self._session(ctx))

    async def cancel(self, ctx):
        try:
            await self.page.clear_reactions()
        except discord.Forbidden:
            for button in self._buttons:
                try:
                    await self.page.remove_reaction(button, self.ctx.bot)
                except discord.HTTPException:
                    pass

        embed = self.page.embeds[0]
        embed.set_footer(text=f"{embed.footer.text} Session Cancelled.")

        await self.page.edit(embed=embed)

        self._cancelled = True
        self._session_task.cancel()
