import discord
import json
import aiofiles
from discord.ext import commands
from random import randint

with open('token.txt') as token_file:
    token = token_file.read()

with open('log.json', 'r') as log_r:
    strong = json.load(log_r)

intents = discord.Intents.all()
client = commands.Bot(command_prefix='/', description='get swole', intents=intents)


async def on_message(message):
    if str(message.channel) != 'the-iron-temple':
        return
    await client.process_commands(message)


client.on_message = on_message


async def update_log():
    async with aiofiles.open('log.json', 'w') as log_w:
        await log_w.write(json.dumps(strong))


@client.event
async def on_ready():
    print(client.guilds)


@client.command()
async def pushups(ctx):
    if str(ctx.author) in strong:
        n = randint(25, 75)
        await ctx.send(f'drop and give me {n}')
        strong[str(ctx.author)]['pushups'] += n
        await update_log()
    else:
        ctx.send('you are not yet a disciple of the iron temple')


@client.command()
async def give_pushups(ctx, target: discord.User, number):
    """roll for a member to get pushups"""
    if str(target) in strong:
        strong[str(target)]['pushups'] += randint(10, 30)
        await update_log()

    else:
        await ctx.send('user is not a disciple of the iron temple')


@client.command()
async def signup(ctx):
    """sign up to become a disciple of the iron temple"""
    if str(ctx.author) not in strong:
        await ctx.send(f'{ctx.author.mention} welcome to the iron temple')
        strong[str(ctx.author)] = {'rolls': 1,
                                   'pushups': 0}
        await update_log()


@client.command()
async def remove(ctx):
    """turn your back on the iron temple"""
    if str(ctx.author) in strong:
        await ctx.send(f"{str(ctx.author.mention)} doesn't even lift anymore")
        del strong[str(ctx.author)]
        await update_log()


@client.command()
async def exe(ctx, cmd):
    await eval(cmd)


client.run(token)
