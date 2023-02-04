import asyncio
import os
import discord
import json
import aiofiles
import typing
from datetime import datetime, timedelta

from discord import app_commands
from discord.ext import commands, tasks
from random import randint, shuffle
from functools import reduce

intents = discord.Intents.all()
client = commands.Bot(command_prefix='/', description='get swole', intents=intents, help_command=None)
channel_name = 'the-iron-temple-test' if os.getenv('DEVELOPMENT') else 'the-iron-temple'
strong = {}
current_day = 0
initialized = False

schedule_hour = 9 if os.getenv('DEVELOPMENT') else 14  # UTC
server_start = datetime.now()

with open('token.txt') as token_file:
    token = token_file.read()

with open('log.json', 'r') as log_r:
    log = json.load(log_r)
    strong = log['strong']
    current_day = log['day']


def schedule(start, target):
    return (start + timedelta(
        days=int(start.hour >= target))).replace(
        hour=target, minute=0)


def add_pushups(member, n):
    strong[member]['pushups'] += n
    strong[member]['weekly'] = strong[member]['alltime'] = strong[member]['pushups']


async def update_log():
    async with aiofiles.open('log.json', 'w') as log_w:
        await log_w.write(json.dumps({'day': current_day, 'strong': strong}, indent=2))


async def update_interval():
    now = datetime.now()
    if not strong:
        return
    undrafted = reduce(lambda x, y: int(not strong[y]['drafted']) + x, strong, 0)
    if not undrafted:
        return
    daily_pushups.change_interval(
        minutes=(schedule(now, (schedule_hour + 12) % 24) - now).total_seconds() / undrafted / 60)
    print(daily_pushups.minutes, undrafted)


@tasks.loop(minutes=1)
async def daily_pushups():
    if not len(strong) or daily_pushups.current_loop == 0:
        return

    members = [x for x in list(strong.keys()) if not strong[x]['drafted']]
    if not len(members):
        return

    shuffle(members)
    member = members[0]
    n = randint(20, 30)
    add_pushups(member, n)
    strong[member]['drafted'] = True
    await update_log()

    user = discord.utils.get(
        client.users,
        name=''.join(member[:-5]),
        discriminator=''.join(member[-4::]))

    channel = discord.utils.get(client.get_all_channels(), name=channel_name)
    await channel.send(f'{user.mention} drop and give me {n} pushups')
    await update_interval()
    print(daily_pushups.minutes)


@tasks.loop(hours=24)
async def daily_reset():
    global current_day

    current_day += 1
    if len(strong) == 0:
        return

    if current_day == 7:
        for member in strong:
            member['weekly'] = member['pushups']

    print('test')
    channel = discord.utils.get(client.get_all_channels(), name=channel_name)
    interval = 'weekly' if current_day == 7 else 'pushups'
    sorted_strong = dict(sorted(strong.items(), key=lambda item: item[1][interval], reverse=True))
    await channel.send(f'--**{interval} Reset**--\n' +
                       '\n'.join([f'**{k}**' + ': ' +
                                  str(sorted_strong[k][interval])
                                  for k in sorted_strong]))
    for member in strong:
        strong[member]['rolls'] += 1
        add_pushups(member, 0)
        strong[member]['pushups'] = 0
        strong[member]['drafted'] = False

    await update_log()


@daily_reset.before_loop
async def init_loop():
    await asyncio.sleep((schedule(server_start, schedule_hour) - server_start).total_seconds())
    daily_pushups.start()


@client.tree.command()
async def pushups(ctx, target: discord.Member = None):
    """get pushups or use a roll for someone else"""
    if not target:
        if str(ctx.user) in strong:
            n = randint(25, 75)
            await ctx.response.send_message(f'drop and give me {n} pushups')
            add_pushups(str(ctx.user), n)
            await update_log()
        else:
            await ctx.response.send_message('you are not yet a disciple of the iron temple')
    else:
        if str(target) in strong and str(ctx.user) in strong \
                and strong[str(ctx.user)]['rolls'] > 0:
            n = randint(10, 30)
            add_pushups(str(target), n)
            strong[str(ctx.user)]['rolls'] -= 1
            await ctx.response.send_message(f'{target.mention} drop and give me {n} pushups')
            await update_log()
        else:
            await ctx.response.send_message('user is not a disciple of the iron temple\n'
                                            'or you are out of rolls')


@client.tree.command()
async def signup(ctx):
    """sign up to become a disciple of the iron temple"""
    if str(ctx.user) not in strong:
        await ctx.response.send_message(f'{ctx.user.mention} welcome to the iron temple')
        strong[str(ctx.user)] = {'rolls': 1,
                                 'pushups': 0,
                                 'weekly': 0,
                                 'alltime': 0,
                                 'drafted': False}
        await update_log()
        await update_interval()
    else:
        await ctx.response.send_message('you are already a member of the iron temple')


@client.tree.command()
async def remove(ctx):
    """turn your back on the iron temple"""
    if str(ctx.user) in strong:
        await ctx.response.send_message(f"{str(ctx.user.mention)} doesn't even lift anymore")
        del strong[str(ctx.user)]
        await update_log()
        await update_interval()


@client.tree.command()
async def leaderboard(ctx, interval: str = 'pushups'):
    """display a daily (default), weekly, or alltime leaderboard of temple members"""
    if not len(strong):
        await ctx.response.send_message('no disciples to display')
    else:
        try:
            titles = {'pushups': 'Daily', 'weekly': 'Weekly', 'alltime': 'Alltime'}
            sorted_strong = dict(sorted(strong.items(), key=lambda item: item[1][interval], reverse=True))
            await ctx.response.send_message(f'--**{titles[interval]} Leaderboard**--\n' +
                                            '\n'.join([f'**{k}**' + ': ' +
                                                       str(sorted_strong[k][interval])
                                                       for k in sorted_strong]))
        except KeyError as error:
            await ctx.response.send_message('options are weekly or alltime', ephemeral=True)


@leaderboard.autocomplete('interval')
async def leaderboard_autocomplete(
        interaction: discord.Interaction,
        current: str) -> typing.List[app_commands.Choice[str]]:
    intervals = ['weekly', 'alltime']
    return [
        app_commands.Choice(name=interval, value=interval)
        for interval in intervals if current in interval
    ]


@client.tree.command()
async def rolls(ctx):
    """display number of rolls the user has left"""
    await ctx.response.send_message(f"you have {strong[str(ctx.user)]['rolls']} rolls remaining (+1 per day)")


@client.tree.command()
async def help(ctx):
    """get some help"""
    await ctx.response.send_message('--**Welcome to the Iron Temple**--\n\n'
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


@client.tree.command()
async def test(ctx, interval: str = 'pushups'):
    """testing purposes only"""
    sorted_strong = dict(sorted(strong.items(), key=lambda item: item[1][interval], reverse=True))
    await ctx.response.send_message(f'--**{"Weekly" if interval == "weekly" else "Daily"} Reset**--\n' +
                                    '\n'.join([f'**{k}**' + ': ' +
                                               str(sorted_strong[k][interval])
                                               for k in sorted_strong]))


@client.event
async def on_ready():
    global initialized
    if initialized:
        return

    await client.tree.sync()
    daily_reset.start()
    print(client.guilds)
    initialized = True


client.run(token)
