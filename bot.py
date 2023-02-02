import asyncio
import os
import discord
import json
import aiofiles
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from random import randint, shuffle
from functools import reduce

intents = discord.Intents.all()
client = commands.Bot(command_prefix='/', description='get swole', intents=intents, help_command=None)
channel_name = 'the-iron-temple-test' if os.getenv('DEVELOPMENT') else 'the-iron-temple'
strong = {}
initialized = False

schedule_hour = 9 if os.getenv('DEVELOPMENT') else 14  # UTC
server_start = datetime.now()


def schedule(start, target):
    return (start + timedelta(
        days=int(start.hour >= target))).replace(
        hour=target, minute=0)


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
    global assign_index
    if not len(strong):
        return

    members = [x for x in list(strong.keys()) if not strong[x]['drafted']]
    if not len(members):
        return

    shuffle(members)
    member = members[0]
    n = randint(20, 30)
    strong[member]['pushups'] += n
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
    global assign_index
    if len(strong) == 0:
        return

    print('test')
    channel = discord.utils.get(client.get_all_channels(), name=channel_name)
    sorted_strong = dict(sorted(strong.items(), key=lambda item: item[1]['pushups'], reverse=True))
    await channel.send('--**Daily Reset**--\n' +
                       '\n'.join([f'**{k}**' + ': ' +
                                  str(sorted_strong[k]['pushups'])
                                  for k in sorted_strong]))
    for member in strong:
        strong[member]['rolls'] += 1
        strong[member]['pushups'] = 0
        strong[member]['drafted'] = False

    await update_log()
    daily_pushups.change_interval(seconds=1)


@daily_reset.before_loop
async def init_loop():
    await asyncio.sleep((schedule(server_start, schedule_hour) - server_start).total_seconds())
    daily_pushups.start()


@client.command()
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
                                   'pushups': 0,
                                   'drafted': False}
        await update_log()
        await update_interval()
    else:
        await ctx.send('you are already a member of the iron temple')


@client.command()
async def remove(ctx):
    """turn your back on the iron temple"""
    if str(ctx.author) in strong:
        await ctx.send(f"{str(ctx.author.mention)} doesn't even lift anymore")
        del strong[str(ctx.author)]
        await update_log()
        await update_interval()


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


@client.command()
async def test(ctx):
    channel = discord.utils.get(client.get_all_channels(), name=channel_name)
    sorted_strong = dict(sorted(strong.items(), key=lambda item: item[1]['pushups'], reverse=True))
    await channel.send('--**Daily Reset**--\n' +
                       '\n'.join([f'**{k}**' + ': ' +
                                  str(sorted_strong[k]['pushups'])
                                  for k in sorted_strong]))


@client.event
async def on_ready():
    global initialized
    if initialized:
        return
    daily_reset.start()
    client.on_message = on_message
    print(client.guilds)
    initialized = True


client.run(token)
