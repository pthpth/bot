import re
import smtplib
import ssl
import discord
from discord.ext import commands
from pymongo import MongoClient
from discord.utils import get
from password import url, TOKEN, sender_email, password  # make variables in password.py to hold your credentials like

# email id,password and Discord Bot Token

# Setting up initial parameters for hosting the bot
intents = discord.Intents.default()
intents.members = True
client = discord.Client()
bot = commands.Bot(command_prefix="!", intents=intents)
cluster = MongoClient(url)
bot.remove_command("help")
# Connecting to the database on mongodb
db = cluster["Bot"]
verification_code = db["verify"]
user_data = db["user-data"]
temp_data = db["temp-data"]


@bot.event
async def on_ready():
    print("Connected")  # to make sure bot is connected to the server


# Function to give unverified role to member when he/she joins first
@bot.event
async def on_member_join(member):
    role = get(member.guild.roles, name="unverified")
    await member.add_roles(role)


# @bot.command(name="mutes")
# async def mutes(ctx):
#     muted = get(ctx.guild.roles, name="Muted")
#     chs = await ctx.guild.fetch_channels()
#     for x in chs:
#         await x.set_permissions(muted, read_messages=True, send_messages=False)


# function to add muted perms to newly created channels in future
@bot.event
async def on_guild_channel_create(channel):
    muted = get(channel.guild.roles, name="Muted")
    await channel.set_permissions(muted, read_messages=True, send_messages=False)


# command to announce some message in a target channel
@bot.command(name="announce")
async def announce(ctx, chn: discord.TextChannel, title: str, desc):
    if not get(ctx.guild.roles, name="moderator") in ctx.author.roles and not (
            get(ctx.guild.roles, name="admin") in ctx.author.roles):
        await ctx.send("This command can only be used by admins")
        return
    title = "**" + title + "**"
    embed = discord.Embed(
        title=title,
        description=desc
    )
    await chn.send(embed=embed)


# command to embed links in a target channel
@bot.command(name="embed")
async def announce(ctx, chn: discord.TextChannel, title: str, link: str):
    if not get(ctx.guild.roles, name="moderator") in ctx.author.roles and not (
            get(ctx.guild.roles, name="admin") in ctx.author.roles):
        await ctx.send("This command can only be used by admins")
        return
    title = "**" + title + "**"
    embed = discord.Embed(
        title=title,
        url=link
    )
    await chn.send(embed=embed)


# global data members
currentyear = 2020
branches = {
    "AA": "ECE",
    "A1": "CHEM",
    "A2": "CIVIL",
    "A3": "EEE",
    "A4": "MECH",
    "A5": "PHARM",
    "A7": "CSE",
    "A8": "ENI",
    "B1": "MSc.BIO",
    "B2": "MSc.CHEM",
    "B3": "MSc.ECO",
    "B4": "MSc.MATH",
    "B5": "MSc.PHY"
}


# command to mute members
@bot.command(name="mute")
async def mute(ctx, user: discord.User):
    if not get(ctx.guild.roles, name="moderator") in ctx.author.roles and not (
            get(ctx.guild.roles, name="admin") in ctx.author.roles):
        await ctx.send("This command can only be used by admins")
        return  # checking that only admin/mods can access this command
    user = await ctx.guild.fetch_member(user.id)
    role = get(ctx.guild.roles, name="Muted")
    await user.add_roles(role)


# verification code generator
def code_generator(id_user):
    s = str(id_user)
    code = s[0] + s[3] + s[6] + s[4]
    post = {"user": id_user, "code": code}
    verification_code.insert_one(post)
    return code


# command to make new roles
@bot.command(name="make-role")
async def make_role(ctx, name):
    if not get(ctx.guild.roles, name="moderator") in ctx.author.roles:
        await ctx.send("This command can only be used by admins")
        return  # checking is the calling user is admin/mod
    if get(ctx.guild.roles, name=name) is None:
        await ctx.guild.create_role(name=name)
    else:
        await ctx.send("Role already exits")  # checking if role with same name exists


# function to give right roles acc to branch and year after verification
async def give_roles(user: discord.Member, guild: discord.Guild):
    query = {"user": user.id}
    role = get(guild.roles, name="unverified")
    await user.remove_roles(role)
    role = get(guild.roles, name="bitsian")
    await user.add_roles(role)
    verification_code.delete_one(query)
    query = {"discid": user.id}
    data = temp_data.find_one_and_delete(query)
    id = data["id"]
    user_data.insert_one(data)  # saving the data of user in db
    year = "20" + id[2:4]
    branch = id[4:6]
    if id[4] == 'B':
        dualdegree = 1
        singledegree = 0
    else:
        singledegree = 1
        dualdegree = 0
    role = get(guild.roles, name=year)
    await user.add_roles(role)
    role = get(guild.roles, name=branches[branch])
    await user.add_roles(role)

    if currentyear - int(year) >= 4 or (currentyear - int(year) == 4 and singledegree == 1):
        role = get(guild.roles, name="Alumni")
        await user.add_roles(role)

    if singledegree == 1:
        role = get(guild.roles, name="single-degree")
        await user.add_roles(role)

    else:
        role = get(guild.roles, name="dual-degree")
        await user.add_roles(role)
        if currentyear - year > 0:
            role = get(guild.roles, name=branches[id[6] + id[7]])
            await user.add_roles(role)


# checking if user is verified and then giving roles
@bot.command(name="submit")
async def submit(ctx, code):
    if not ctx.channel.id == 775308388220796978:  # restricting the command to a single channel
        return  # limiting this command to only one channel is #verification channel
    query = {"user": ctx.author.id}
    if verification_code.count_documents(query) == 0:
        await ctx.send("First verify yourself")
    else:
        res = verification_code.find_one(query)
        if code == res["code"]:
            await ctx.send("You are verified!")
            await give_roles(ctx.author, ctx.guild)


# function to start the verification process
@bot.command(name="verify")
async def verify(ctx, id, *name):
    if not ctx.channel.id == 775308388220796978:
        return
    query = {"id": id}
    if user_data.count(query) > 0:
        if user_data.find_one(query)["discid"] == ctx.author.id:
            await ctx.send("You are already verified")
            await give_roles(ctx.author, ctx.guild)
        else:
            await ctx.send("Another user is already registered to this id. If there is some error contact admins")
        return
    if not re.search(r'[0-9]{4}(A([1-8]|A)|B[1-5])(TS|PS|(A([1-8]|A)))[0-9]{4}H',
                     id):  # regex function to check if BITS id is right or not
        await ctx.send("Enter valid ID")
        return
    if int(id[0:4]) == currentyear:
        if not (id[6:8] == "PS" or id[6:8] == "TS"):
            await ctx.send("Enter valid ID")
            return
    if not 2007 < int(id[0:4]) < 2021:
        await ctx.send("Enter valid ID")
        return
    name = " ".join(name)
    receiver_email = "f" + id[0:4] + id[8:12] + "@hyderabad.bits-pilani.ac.in"
    post = {"name": name, "branch-code": id[4] + id[5], "discid": ctx.author.id, "id": id}
    temp_data.insert_one(post)
    smtp_server = "smtp.gmail.com"
    port = 587
    context = ssl.create_default_context()
    message = """\
    Subject:Success

    Your verification code is:""" + code_generator(ctx.author.id)
    try:
        server = smtplib.SMTP(smtp_server, port)
        server.ehlo()
        server.starttls(context=context)
        server.login(sender_email, password)
        await ctx.send("Please check ur BITS mail inbox. Use the submit command to verify yourself")
        server.sendmail(sender_email, receiver_email, message)
    except Exception as e:
        print(e)
        await ctx.send("Some error occurred.Please try some time later")
    finally:
        server.quit()


# @bot.command(name="dual")
# async def dual(message, code):
#     if not re.search(r'A([1-8]|A)', code):
#         await message.send("Enter valid ID")
#
#     role = get(message.server.roles, name=branches[code])
#     await message.author.add_roles(role)
#

bot.run(TOKEN)
