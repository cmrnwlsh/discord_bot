import discord
import json
import aiofiles
from discord.ext import commands, tasks
from random import randint

intents = discord.Intents.all()
client = commands.Bot(command_prefix='/', description='get swole', intents=intents)
strong = {}

with open('token.txt') as token_file:
    token = token_file.read()

with open('log.json', 'r') as log_r:
    strong = json.load(log_r)


async def on_message(message):
    if str(message.channel) != 'the-iron-temple':
        return
    await client.process_commands(message)

client.on_message = on_message


async def update_log():
    async with aiofiles.open('log.json', 'w') as log_w:
        await log_w.write(json.dumps(strong, indent=2))


@tasks.loop(seconds=5)
async def scheduled_pushups():
    print('test')
    channel = discord.utils.get(client.get_all_channels(), name='the-iron-temple')
    string = ''
    for member in strong:
        user = discord.utils.get(
            client.users,
            name=''.join(member[:-5]),
            discriminator=''.join(member[-4::]))

        pushup_count = randint(10, 30)
        string += f'{user.mention} has been assigned {pushup_count} pushups\n'
        strong[member]['pushups'] += pushup_count

    await update_log()
    await channel.send(string)


@client.event
async def on_ready():
    scheduled_pushups.start()
    print(client.guilds)


@client.command()
async def pushups(ctx):
    if str(ctx.author) in strong:
        n = randint(25, 75)
        await ctx.send(f'drop and give me {n}')
        strong[str(ctx.author)]['pushups'] += n
        await update_log()
    else:
        await ctx.send('you are not yet a disciple of the iron temple')


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
async def leaderboard(ctx):
    if not len(strong):
        await ctx.send('no disciples to display')
    else:
        sorted_strong = dict(sorted(strong.items(), key=lambda item: not item[1]['pushups']))
        await ctx.send('\n'.join([k + ': ' + str(sorted_strong[k]['pushups']) for k in sorted_strong]))


client.run(token)
