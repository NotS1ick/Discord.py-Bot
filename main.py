import discord
import aiofiles
from discord.ext import commands
import os
from dotenv import load_dotenv
from cogs.admincog import Admincog
from cogs.music_cog import music_cog

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)
bot.warnings = {} # guild_id : {member_id: [count, [(admin_id, reason)]]}

bot.remove_command('help')

@bot.event
async def on_ready():
    for guild in bot.guilds:
        async with aiofiles.open(f'{guild.id}.txt', mode='a') as temp:
            pass

        bot.warnings[guild.id] = {}

        async with aiofiles.open(f'{guild.id}.txt', mode='r') as file:
            lines = await file.readlines()

        for line in lines:
            data = line.split() 
            member_id = int(data[0])
            admin_id = int(data[1])
            reason = ' '.join(data[2:]).strip("\n")

            try:
                bot.warnings[guild.id][member_id][0] += 1
                bot.warnings[guild.id][member_id][1].append((admin_id, reason))

            except KeyError:
                bot.warnings[guild.id][member_id] = [1, [(admin_id, reason)]]


    await bot.add_cog(Admincog(bot))
    await bot.add_cog(music_cog(bot))
    print(f'We have logged in as {bot.user}') 

@bot.event
async def on_guild_join(guild):
    bot.warnings[guild.id] = {}

@bot.command()
async def hello(ctx):
    await ctx.send("Hello, Im your lord and savior bots")

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! {0}'.format(round(bot.latency, 1)))

DISCORD_API_SECRET =  os.getenv('DISCORD_API_TOKEN')
bot.run(DISCORD_API_SECRET)
