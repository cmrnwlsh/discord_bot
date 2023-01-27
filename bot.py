import asyncio
import os
import discord
import json
import aiofiles
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from random import randint

intents = discord.Intents.all()
client = commands.Bot(command_prefix='/', description='get swole', intents=intents, help_command=None)
channel_name = 'the-iron-temple-test' if os.getenv('DEVELOPMENT') else 'the-iron-temple'
strong = {}
iterator_lock = asyncio.Lock()
initialized = False

now = datetime.now()
start_hour = 14  # UTC
schedule = (now + timedelta(days=int(now.hour > start_hour)))\
           .replace(hour=start_hour, minute=0)


with open('token.txt') as token_file:
    token = token_file.read()

with open('log.json', 'r') as log_r:
    strong = json.load(log_r)


async def on_message(message):
    if str(message.channel.name) != channel_name:
        return
    await client.process_commands(message)


async def update_log():
    async with aiofiles.open('log.json', 'w') as log_w:
        await log_w.write(json.dumps(strong, indent=2))


def roll_pushups():
    i = 0
    members = list(strong.keys())

    @tasks.loop(seconds=3)
    async def inner_loop():
        nonlocal i
        if len(strong) == 0 or len(strong) == i:
            return
        channel = discord.utils.get(client.get_all_channels(), name=channel_name)
        member = members[i]
        n = randint(20, 30)
        strong[member]['pushups'] += n
        await update_log()

        user = discord.utils.get(
            client.users,
            name=''.join(member[:-5]),
            discriminator=''.join(member[-4::]))

        await channel.send(f'{user.mention} drop and give me {n} pushups')
        inner_loop.change_interval(minutes=(12*60)/len(members))
        print(inner_loop.minutes)
        async with iterator_lock:
            i += 1

    return inner_loop


@tasks.loop(hours=24)
async def daily_reset():
    if len(strong) == 0:
        return
    print('test')
    channel = discord.utils.get(client.get_all_channels(), name=channel_name)
    for member in strong:
        strong[member]['rolls'] += 1
        strong[member]['pushups'] = 0
        async with iterator_lock:
            roll_pushups.i = 0

    await update_log()
    await channel.send('Daily Reset')


@daily_reset.before_loop
async def init_loop():
    await asyncio.sleep((schedule - now).total_seconds())
    roll_pushups().start()


@ client.command()
async def pushups(ctx, *args):
    """get pushups or use a roll for someone else"""
    if len(args) == 0:
        if str(ctx.author) in strong:
            n = randint(25, 75)
            await ctx.send(f'drop and give me {n} pushups')
            strong[str(ctx.author)]['pushups'] += n
            await update_log()
        else:
            await ctx.send('you are not yet a disciple of the iron temple')
    else:
        target = discord.utils.get(client.get_all_members(), id=int(args[0][2:-1]))
        if str(target) in strong and str(ctx.author) in strong \
                and strong[str(ctx.author)]['rolls'] > 0:
            n = randint(10, 30)
            strong[str(target)]['pushups'] += n
            strong[str(ctx.author)]['rolls'] -= 1
            await ctx.send(f'{target.mention} drop and give me {n} pushups')
            await update_log()

        else:
            await ctx.send('user is not a disciple of the iron temple\n'
                           'or you are out of rolls')


@client.command()
async def signup(ctx):
    """sign up to become a disciple of the iron temple"""
    if str(ctx.author) not in strong:
        await ctx.send(f'{ctx.author.mention} welcome to the iron temple')
        strong[str(ctx.author)] = {'rolls': 1,
                                   'pushups': 0}
        await update_log()
    else:
        await ctx.send('you are already a member of the iron temple')


@client.command()
async def remove(ctx):
    """turn your back on the iron temple"""
    if str(ctx.author) in strong:
        await ctx.send(f"{str(ctx.author.mention)} doesn't even lift anymore")
        del strong[str(ctx.author)]
        await update_log()


@client.command()
async def leaderboard(ctx):
    """display a daily leaderboard of temple members"""
    if not len(strong):
        await ctx.send('no disciples to display')
    else:
        sorted_strong = dict(sorted(strong.items(), key=lambda item: item[1]['pushups'], reverse=True))
        await ctx.send('\n'.join([f'**{k}**' + ': ' + str(sorted_strong[k]['pushups']) for k in sorted_strong]))


@client.command()
async def rolls(ctx):
    """display number of rolls the user has left"""
    await ctx.send(f"you have {strong[str(ctx.author)]['rolls']} rolls remaining (+1 per day)")


@client.command()
async def help(ctx):
    await ctx.send('--**Welcome to the Iron Temple**--\n\n'
                   '**/help**: \n'
                   '    Display this list\n\n'
                   '**/signup**: \n'
                   '    Sign up for daily pushups\n\n'
                   '**/remove**: \n'
                   '    Do you even lift?\n\n'
                   '**/pushups** or **/pushups @someone**: \n'
                   '    Roll for pushups or gift them to others\n\n'
                   '**/leaderboard**: \n'
                   "    View today's pushups leaderboard\n\n"
                   '**/rolls**: \n'
                   '    Check the number of rolls you have remaining'
                   )


@client.event
async def on_ready():
    global initialized
    if initialized:
        return
    daily_reset.start()
    client.on_message = on_message
    print(client.guilds)
    print(now)
    initialized = True


client.run(token)
