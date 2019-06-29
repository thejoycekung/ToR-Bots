import datetime
import sys

import discord

import passwords_and_tokens

client = discord.Client()
fingerbit = None


@client.event
async def on_ready():
    global fingerbit

    fingerbit = client.get_channel(428212915473219604)

    message = " ".join(sys.argv[1:])

    await fingerbit.send(
        "<@&428212811290771477>",
        embed=discord.Embed(
            title="Message:",
            description=message,
            colour=0xFF0000,
            timestamp=datetime.datetime.now(),
        ),
    )
    await client.close()


client.run(passwords_and_tokens.discord_token)
