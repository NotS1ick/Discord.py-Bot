import discord
import aiofiles
import asyncio
from discord.ext import commands

from discord.ext.commands import Converter, BadArgument


class MemberConverter(Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except BadArgument as e:
            if "Member" in str(e):
                await ctx.send("Please enter a valid user.")
                raise BadArgument("Member not found. Please mention a valid member.")
            else:
                raise e

class Admincog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.warnings = {}  
        self.bot.loop.create_task(self.load_warnings())

    async def load_warnings(self):
        tasks = []

        for guild in self.bot.guilds:
            try:
                async with aiofiles.open(f'{guild.id}.txt', mode='r') as file:
                    lines = await file.readlines()
                    for line in lines:
                        data = line.split(' ')
                        member_id = int(data[0])
                        admin_id = int(data[1])
                        reason = ' '.join(data[2:]).strip('\n')

                        if guild.id not in self.bot.warnings:
                            self.bot.warnings[guild.id] = {}

                        try:
                            if member_id not in self.bot.warnings[guild.id]:
                                self.bot.warnings[guild.id][member_id] = [0, []]

                            self.bot.warnings[guild.id][member_id][0] += 1
                            self.bot.warnings[guild.id][member_id][1].append((admin_id, reason))
                        except KeyError:
                            pass  
            except FileNotFoundError:
                pass

        await asyncio.gather(*tasks)

        
        self.bot.remove_command('pruge')
    
    def cog_unload(self):
        pass  

    
    @commands.command(name="pruge", hidden=True)
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount=11):
        amount = amount+1
        if amount > 101:
            await ctx.send('You cant delete more than 100 messages')
        else:
            await ctx.channel.purge(limit=amount)
            await ctx.send ('Messages have been cleared')

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: MemberConverter = None, *, reason=None):
        if member is None:
            await ctx.send("Please mention a valid member.")
            return

        if reason is None:
            await ctx.send("Please mention a valid reason")
            return

        try:
            await member.kick(reason=reason)
            await ctx.send(f'User {member.mention} has been kicked for {reason}')
        except discord.errors.Forbidden:
            await ctx.send("I don't have permission to kick members.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred during the kick: {e}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: MemberConverter = None, *, reason=None):
        if member is None:
            await ctx.send("Please mention a valid member.")
            return

        if reason is None:
            await ctx.send("Please mention a valid reason")
            return

        try:
            await member.ban(reason=reason)
            await ctx.send(f'User {member.mention} has been banned for {reason}')
        except discord.errors.Forbidden:
            await ctx.send("I don't have permission to ban members.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred during the ban: {e}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, member):
        if not member:
            return await ctx.send("Invalid argument. Please provide a valid username (e.g., `username`).")

        banned_users = [ban_entry async for ban_entry in ctx.guild.bans()]

        for ban_entry in banned_users:
            user = ban_entry.user

            if user.name == member:
                try:
                    await ctx.guild.unban(user)
                    await ctx.send(f'Unbanned {user.mention}')
                    return
                except discord.errors.Forbidden:
                    await ctx.send("I don't have permission to unban members.")
                    return
                except discord.HTTPException as e:
                    await ctx.send(f"An error occurred during the unban: {e}")
                    return

        await ctx.send("User not found in the ban list.")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member=None, *, reason=None):
        if member is None:
            return await ctx.send('The provided member could not be found. Please check your writing for mistakes.')
        
        if reason is None:
            return await ctx.send("Please provide a reason for the warning")
        
        guild = ctx.guild
        if guild.id not in self.bot.warnings:
            self.bot.warnings[guild.id] = {}
        if member.id not in self.bot.warnings[guild.id]:
            self.bot.warnings[guild.id][member.id] = [0, []]
        
        self.bot.warnings[guild.id][member.id][0] += 1
        self.bot.warnings[guild.id][member.id][1].append((ctx.author.id, reason))
        
        count = self.bot.warnings[guild.id][member.id][0]
        
        async with aiofiles.open(f'{guild.id}.txt', mode='a') as file:
            await file.write(f'{member.id} {ctx.author.id} {reason}\n')
            
        await ctx.send(f'{member.mention} has {count} {"warning" if count == 1 else "warnings"}.')

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warns(self, ctx, member: discord.Member = None):
        if member is None:
            return await ctx.send('The user you have provided does not exist.')

        embed = discord.Embed(title=f'Warnings for {member}', description='', colour=discord.Colour.purple())
        try:
            i = 1
            for admin_id, reason in self.bot.warnings.get(ctx.guild.id, {}).get(member.id, [0, []])[1]:
                admin = ctx.guild.get_member(admin_id)
                if admin is None:
                    admin_mention = f'<@{admin_id}>'  # Mention the admin using their ID
                else:
                    admin_mention = admin.mention

                embed.add_field(name=f'Warning {i}', value=f'Admin: {admin_mention}\nReason: {reason}', inline=False)
                i += 1

            # Set the thumbnail (user's avatar) to the right
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.set_thumbnail(url=member.default_avatar.url)

            # Ping the admin in the description
            admin_ping = f'<@{admin_id}>'

        except KeyError:  # no warnings
            embed.description = f'No warnings have been found for {member}'
        finally:
            await ctx.send(embed=embed)

    @commands.command(aliases=['warn_remove'])
    @commands.has_permissions(kick_members=True)
    async def rwarn(self, ctx, member: discord.Member=None, *, reason=None):
        if not member or not reason:
            return await ctx.send('Incorrect command syntax. Please use the command like this: `!rwarn @user reason`')
        
        guild = ctx.guild
        if guild.id not in self.bot.warnings:
            return await ctx.send("This member has no warnings")
        if member.id not in self.bot.warnings[guild.id]:
            return await ctx.send("This member has no warnings")
           
        warnings_list = self.bot.warnings[guild.id][member.id][1]
        new_warnings_list = [warning for warning in warnings_list if not (reason is not None and warning[1].lower() == reason.lower())]
        
        if len(new_warnings_list) < len(warnings_list):
            self.bot.warnings[guild.id][member.id][0] -= 1
            self.bot.warnings[guild.id][member.id][1] = new_warnings_list
        
        count = self.bot.warnings[guild.id][member.id][0]
        
        # Rewrite the file with the updated warnings list
        async with aiofiles.open(f'{guild.id}.txt', mode='w') as file:
            for member_id, warnings in self.bot.warnings[guild.id].items():
                for admin_id, reason in warnings[1]:
                    await file.write(f'{member_id} {admin_id} {reason}\n')
                    
        await ctx.send(f'{member.mention} now has {count} {"warning" if count == 1 else "warnings"}.')
        
def setup(bot):
    bot.add_cog(Admincog(bot))
