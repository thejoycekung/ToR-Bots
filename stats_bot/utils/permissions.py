BOT_OWNERS = [
    256084554375364613,
    193053876692189184,
    379578965175828482,
    133642107259846657,
]


def is_owner(ctx):
    return ctx.message.author.id in BOT_OWNERS
