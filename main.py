import discord
from discord.ext import commands
import discord.ext.tasks as task_module
import logging
from dotenv import load_dotenv
import os
import asyncio
from database import init_db, add_entry, get_random, get_by_link, delete_entry, get_by_entry, delete_db, idx2week, week2idx
from datetime import time, datetime
from zoneinfo import ZoneInfo

# Environment
load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# Discussion configurations
init_db()
discussion_time = 2 * 24 # --> 2 days
disc_enabled = False

# Channel constants
CHANNEL = 1428598017656619100 # general chat
ECHANNEL = 1434310637936447488 # eboard general chat
ANNOUNCE = 1434239578457509958 # announcement chat
EANNOUNCE = 1434589025158824130 # eboard announcement chat
ME = 699427677383294986 # Nick T. user ID

# Task reminder configurations
task_day = 2 # 2 --> Wednesday
task_hour = 16 # 4PM
task_minute = 0
task_enabled = False

# Permissions and handlers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(BASE_DIR, 'discord.log')
handler = logging.FileHandler(filename=log_path, encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.polls = True
intents.bans = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# INIT/INFO
@bot.event
async def on_ready():
    if not send.is_running():
        send.start()
    if not task_scheduler.is_running():
        task_scheduler.start()

@bot.event
async def on_member_join(member):
    pass

@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.command()
@commands.has_role("E-Board")
async def help(ctx):
    global task_minute
    global discussion_time
    global task_hour
    global task_day
    minute_message = str(task_minute)
    if task_minute < 10:
        minute_message = "0" + minute_message
    await ctx.send(
f'''
**Industry Discussion:**
* Every {discussion_time / 24} day(s) I will randomly select an entry to stimulate discussion. 
* Use !set_disc_time [days] to update this interval. Use !get_disc_time to see the currently set interval.
* Use !enable_disc or !disable_disc to enable/disable automatic discussion.
* Use !add [content], [category], [optional link] to add to the database.
        
        *Content*: The actual ride name, trivia fact, manufacturer, ride element, etc.
        
        *Category*: Any of the following: park, manufacturer, ride, element, model, trivia, or discussion. Do not diverge from this list.
        
        *Link*: Optional link, but extremely recommended. Use RCDB.com for links.   
* Use !pull to force pull an entry. This should typcially only be used for testing or for manually changing the discussion early. The original !pull message will be deleted to hide this.
* Use !delete [content] to remove an entry if there is a duplicate for example. Spelling must be exact. Use !wipe to delete the entire database. This CANNOT be undone!

**Reminder Scheduling:**
* Use !schedule YYYY-MM-DD HH:MM [message] with the time in 24-hour time to schedule a reminder message.
    

**E-Board Task Reminders**
* Every {idx2week[task_day]} at {task_hour}:{minute_message}, I will automatically remind E-Board members of their incomplete weekly tasks and tasks due the next day.
* Additional daily reminders will be sent at {task_hour}:{minute_message} the day before a task is due.
* Use !tasks to announce ALL incomplete E-Board tasks, including ones with more than 1 day of time remaining. 
* Use !set_task_time [day] [24-hour time] to change the weekly reminders. Use !get_task_time to see what it is currently set to. 
* Use !enable_tasks or !disable_tasks to enable/disable automatic task reminders.

Only members with the E-Board flair will be able to use any of the bot commands, including !help
''')

# Roller coaster Database Management
@bot.command()
@commands.has_role("E-Board")
async def add(ctx, *, message):
    message = [m.strip() for m in message.split(',')]
    content = message[0]
    category = message[1].lower()
    author_id = ctx.author.id
    if len(message) > 2:
        link = message[2]
    else:
        link = None
    confirm = f"CONFIRM: You are adding `{content}` as `{category}`"
    entry = get_by_entry(content)
    # dblink = get_by_link(link) // Obsolete --> Allowing multiple entries with same link
    if entry:
        await ctx.send(f"{content} already exists")
        return
    if link:
        confirm += f" with link {link}"
    confirm += "? `[yes/no]`"
    await ctx.send(confirm)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower().strip() in ["yes", "no"]
    try:
        response = await bot.wait_for("message", check=check, timeout=15)
    except asyncio.TimeoutError:
        await ctx.send("Confirmation timed out. Entry not added.")
        return
    if response.content.lower() == "yes":
        add_entry(content, category, author_id, link)
        await ctx.send("Entry added")
    else:
        await ctx.send("Entry cancelled.")

@bot.command()
@commands.has_role("E-Board")
async def pull(ctx):
    await ctx.message.delete()
    content = get_random()
    if content:
        category = content['category']
        if category != 'discussion' and category != 'trivia':
            category = category.capitalize()
            category += ' discussion'
        else:
            category = category.capitalize()
        message = f"**{category}:** {content['content']}"
        if content['link']:
            message += f" {content['link']}"
        await ctx.send(message)
    else:
        await ctx.send("Database empty")

@task_module.loop(hours=discussion_time)
async def send():
    channel = bot.get_channel(CHANNEL)
    if channel and disc_enabled:
        content = get_random()
        if content:
            msg = f"**{content['category'].capitalize()} discussion:** {content['content']}"
            if content['link']:
                msg += f" {content['link']}"
            await channel.send(msg)

@bot.command()
@commands.has_role("E-Board")
async def get_disc_time(ctx):
    global discussion_time
    reminder = f"Current interval is {discussion_time / 24} day(s). Use !set_disc_time [interval] to change this."
    if not disc_enabled:
        reminder += " Note that task reminders are currently disabled."
    await ctx.send(reminder)

@bot.command()
@commands.has_role("E-Board")
async def set_disc_time(ctx, *, message):
    try:
        days = float(message)
    except ValueError:
        await ctx.send("Please specify an integer timeframe in days. For example, !set_disc_time 3")
        return
    global discussion_time
    discussion_time = days * 24
    send.change_interval(hours=discussion_time)
    reminder = f"Interval has been updated to {discussion_time / 24} day(s)."
    if not disc_enabled:
        reminder += " Note that task reminders are currently disabled."
    await ctx.send(reminder)

'''@bot.command()
@commands.has_role("E-Board")
async def status(ctx):
    global disc_enabled
    if(disc_enabled):
        await ctx.send("Discussion is currently enabled")
    else:
        await ctx.send("Discussion is currently disabled")'''

@bot.command()
@commands.has_role("E-Board")
async def disable_disc(ctx):
    global disc_enabled
    disc_enabled = False
    await ctx.send("Discussion disabled")

@bot.command()
@commands.has_role("E-Board")
async def enable_disc(ctx):
    global disc_enabled
    disc_enabled = True
    await ctx.send("Discussion enabled")

@bot.command()
@commands.has_role("E-Board")
async def delete(ctx, *, message):
    message = message.strip()
    content = get_by_entry(message, True)
    if not content:
        await ctx.send(f"`{message}` does not exist in the database.")
        return
    confirmation_message = f"`{content['content']}`, `{content['category']}`"
    if(content['link']):
        confirmation_message += f", {content['link']}"
    await ctx.send(f"CONFIRM: You are deleting {confirmation_message}. This cannot be undone `[yes/no]`")
    def check(m):
        return (
            m.author == ctx.author
            and m.channel == ctx.channel
            and m.content.lower().strip() in ["yes", "no"]
        )
    try:
        response = await bot.wait_for("message", check=check, timeout=15)
    except asyncio.TimeoutError:
        await ctx.send("Confirmation timed out. Entry not deleted.")
        return
    if response.content.lower() == "yes":
        delete_entry(message)
        await ctx.send(f"`{content['content']}` has been deleted.")
    else:
        await ctx.send("Deletion cancelled.")

@bot.command()
@commands.has_role("E-Board")
async def wipe(ctx):
    await ctx.send("**WARNING:** You are about to delete ALL entries. This cannot be undone. Type `yes` to confirm.")
    def check(m):
        return (
            m.author == ctx.author
            and m.channel == ctx.channel
            and m.content.lower().strip() in ["yes", "no"]
        )
    try:
        response = await bot.wait_for("message", check=check, timeout=30)
    except asyncio.TimeoutError:
        await ctx.send("Confirmation timed out. No entries were deleted.")
        return
    if response.content.lower().strip() == "yes":
        delete_db()
        await ctx.send("All entries have been deleted.")
    else:
        await ctx.send("Deletion cancelled.")

# Puppet Communication
async def send_to_channel(ctx, message, target_channel_id):
    if ctx.guild is not None:
        return
    if ctx.author.id != ME:
        return

    channel = bot.get_channel(target_channel_id)
    if channel is not None:
        await channel.send(message)

@bot.command()
async def say(ctx, *, message):
    await send_to_channel(ctx, message, CHANNEL)

@bot.command()
async def esay(ctx, *, message):
    await send_to_channel(ctx, message, ECHANNEL)

@bot.command()
@commands.has_role("E-Board")
async def announce(ctx, *, message):
    channel = bot.get_channel(ANNOUNCE)
    if channel:
        await channel.send(message)

# Scheduling and Reminders
@bot.command()
@commands.has_role("E-Board")
async def schedule(ctx, date: str, time: str, *, message):
    # "2026-02-25 18:30 Hi" for example
    try:
        target_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        target_dt = target_dt.replace(tzinfo=ZoneInfo("America/New_York"))
    except ValueError:
        await ctx.send("Invalid format. Use: YYYY-MM-DD HH:MM")
        return
    now = datetime.now(ZoneInfo("America/New_York"))
    delay = (target_dt - now).total_seconds()
    if delay <= 0:
        await ctx.send("That time is in the past.")
        return
    
    await ctx.send("Event successfully scheduled")
    await asyncio.sleep(delay)

    channel = bot.get_channel(EANNOUNCE)
    if channel:
        await channel.send(message)

# E-Board Tasks
'''
Desired task sequencing:
1. Specific tasks get announced a day before they're due
2. Weekly tasks get announced at the set time before E-Board meeting. 
3. !tasks gets all with pie message included
'''
from tasks import get_tasks, get_pie, get_pie_message, parse_day_before, IDs

@bot.command()
@commands.has_role("E-Board")
async def tasks(ctx):
    channel = bot.get_channel(EANNOUNCE)
    sp_tasks, wk_tasks = get_tasks()
    if channel:
        for role in IDs:
            mention = f"<@{IDs[role]}>" # Make sure to add @ in production
            lines = []
            if role in sp_tasks:
                for task in sp_tasks[role]:
                    if task.due_date:
                        lines.append(
                                f"• **{task.title}** — Due: {task.due_date} — Status: {task.status}"
                            )
                    else:
                        lines.append(
                                f"• **{task.title}** — Status: {task.status}"
                            )
            if role in wk_tasks:
                for task in wk_tasks[role]:
                    if task.due_date:
                        lines.append(
                                f"• **{task.title}** — Due: {task.due_date} — Status: {task.status}"
                            )
                    else:
                        lines.append(
                                f"• **{task.title}** — Status: {task.status}"
                            )
            if lines:
                message_content = mention + "\n" + "\n".join(lines)
                if get_pie(sp_tasks, wk_tasks)[role] >= 3:
                    pie_message = "🥧" + get_pie_message() + "🥧"
                    message_content += "\n" + pie_message
                await channel.send(message_content)

# For reminders of weekly tasks before EBoard
@task_module.loop(time=time(hour=task_hour, minute=task_minute, tzinfo=ZoneInfo("America/New_York")))
async def task_scheduler():
    if not task_enabled:
        return
    now = datetime.now(ZoneInfo("America/New_York"))
    today = now.date()
    channel = bot.get_channel(EANNOUNCE)
    if channel:
        sp_tasks, wk_tasks = get_tasks()
        for role in IDs:
            mention = f"<@{IDs[role]}>" # Make sure to add @ in production
            sp_lines = []
            wk_lines = []
            if now.weekday() == task_day:
                if role in wk_tasks:
                    for task in wk_tasks[role]:
                        if task.due_date:
                            wk_lines.append(
                                    f"• **{task.title}** — Due: {task.due_date} — Status: {task.status}"
                                )
                        else:
                            wk_lines.append(
                                    f"• **{task.title}** — Status: {task.status}"
                                )
            if role in sp_tasks:
                    for task in sp_tasks[role]:
                        target = parse_day_before(task.due_date)
                        if target is not None and target == today:
                            sp_lines.append(
                                    f"• **{task.title}** — Due: {task.due_date} — Status: {task.status}"
                                )
            lines = sp_lines + wk_lines
            if lines:
                message = mention + "\n" + "\n".join(lines)
                await channel.send(message)

@bot.command()
@commands.has_role("E-Board")
async def get_task_time(ctx):
    minute_message = str(task_minute)
    if task_minute < 10:
        minute_message = "0" + minute_message
    enabled_message = "enabled" if task_enabled else "disabled"
    await ctx.send(f"Automatic reminders are currently {enabled_message}. Current weekly task reminder time is set to {idx2week[task_day]}. All task reminders will be announced daily at {task_hour}:{minute_message}. Use !set_task_time [day] [24-hour time] to change this.")

@bot.command()
@commands.has_role("E-Board")
async def set_task_time(ctx, *, message):
    import re

    VALID_DAYS = {
        "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday", "Sunday"
    }

    parts = message.strip().split()
    if len(parts) != 2:
        await ctx.send("Format: !set_task_time [day] [24-hour time]")
        return
    day, time_str = parts
    if day not in week2idx:
        await ctx.send("Invalid weekday. Must be capitalized (e.g., Wednesday).")
        return
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", time_str)
    if not match:
        await ctx.send("Time must be 24-hour HH:MM (e.g., 17:30).")
        return
    
    global task_day, task_hour, task_minute
    task_day = week2idx[day]
    task_hour = int(match.group(1))
    task_minute = int(match.group(2))
    minute_message = str(task_minute)
    if task_minute < 10:
        minute_message = "0" + minute_message

    new_time = time(
        hour=task_hour,
        minute=task_minute,
        tzinfo=ZoneInfo("America/New_York")
    )
    task_scheduler.change_interval(time=new_time)
    
    reminder = f"Automatic weekly task reminder time is set to {idx2week[task_day]}. All task reminders will be announced daily at {task_hour}:{minute_message}."
    if not task_enabled:
        reminder += " Note that task reminders are currently disabled."
    await ctx.send(reminder)
@bot.command()
@commands.has_role("E-Board")
async def enable_tasks(ctx):
    global task_enabled 
    task_enabled = True
    minute_message = str(task_minute)
    if task_minute < 10:
        minute_message = "0" + minute_message
    await ctx.send(f"Automatic weekly task reminders are now enabled for {idx2week[task_day]}. All task reminders will be announced daily at {task_hour}:{minute_message}.")

@bot.command()
@commands.has_role("E-Board")
async def disable_tasks(ctx):
    global task_enabled 
    task_enabled = False
    await ctx.send(f"Automatic task remidners are now disabled.")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)