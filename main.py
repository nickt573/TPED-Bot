import discord
from discord.ext import commands
import discord.ext.tasks as task_module
import logging
from dotenv import load_dotenv
import os
import re
import asyncio
from database import init_db, add_entry, get_random, get_by_link, delete_entry, get_by_entry, delete_db, idx2week, week2idx
from scraper import parse_park
from tasks import get_tasks, get_pie, get_pie_message, reminder_due_today, IDs
from datetime import time, datetime
from config import load_config, save_config
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
BOTCOMMAND = 1454957233627594874 # bot commands channel
TASKS = 1541832182895611986 # eboard task announcement channel
ME = 699427677383294986 # Nick T. user ID
EBOARD_ROLE = 1434308646237634701 # E-Board role

EVERYONE_CHANNEL = 1541832182895611986
ROLE_CHANNELS = {
    "PRESIDENT": 1544472006739628114,
    "VICE PRESIDENT": 1544472042663841823,
    "TREASURER": 1544472084871127151,
    "SECRETARY": 1544472123211522159,
    "MR CHAIR": 1544472572291448902,
    "EVENTS CHAIR": 1544472196557312040,
    "PR CHAIRS": 1544472698355327096,
    "C&P CHAIRS": 1544473238955098203,
    "FUNDRAISING CHAIR": 1544472975267340308,
    "PDEV CHAIR": 1544473030040883312,
}

# Task reminder configurations
task_day = 2 # 2 --> Wednesday
task_hour = 16 # 4PM
task_minute = 0
task_enabled = False

# Competition team reminder configurations
COMPS = {
    "rec": {"name": "Rec", "role": 1552764400841265292, "channel": 1552763957054541905, "day": None, "hour": None, "minute": None},
    "rep_new": {"name": "Rep New", "role": 1552764595662360707, "channel": 1555013490144448553, "day": None, "hour": None, "minute": None},
    "rep_cont": {"name": "Rep Cont", "role": 1552764492876877975, "channel": 1555013393226932234, "day": None, "hour": None, "minute": None},
}
COMP_DAY_OF_HOUR = 12 # day-of reminder goes out at 12:00
comps_enabled = False
comps_sent = set() # (team, reminder type, date) so a reminder never goes out twice
scheduled_messages = [] # [{"time": ISO datetime, "message": str}]

# Load saved settings (config.json) over the defaults above
saved = load_config()
discussion_time = saved.get("discussion_time", discussion_time)
disc_enabled = saved.get("disc_enabled", disc_enabled)
task_day = saved.get("task_day", task_day)
task_hour = saved.get("task_hour", task_hour)
task_minute = saved.get("task_minute", task_minute)
task_enabled = saved.get("task_enabled", task_enabled)
comps_enabled = saved.get("comps_enabled", comps_enabled)
for key, meeting in saved.get("comps", {}).items():
    if key in COMPS:
        COMPS[key].update({k: meeting.get(k) for k in ("day", "hour", "minute")})
scheduled_messages = saved.get("scheduled", [])

def save_settings():
    save_config({
        "discussion_time": discussion_time,
        "disc_enabled": disc_enabled,
        "task_day": task_day,
        "task_hour": task_hour,
        "task_minute": task_minute,
        "task_enabled": task_enabled,
        "comps_enabled": comps_enabled,
        "comps": {key: {k: team[k] for k in ("day", "hour", "minute")} for key, team in COMPS.items()},
        "scheduled": scheduled_messages,
    })

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

# Init/Bot Info
@bot.event
async def on_ready():
    channel = bot.get_channel(BOTCOMMAND)
    await channel.send("Beep Boop")
    if not send.is_running():
        send.start()
    if not task_scheduler.is_running():
        task_scheduler.start()
    if not comp_scheduler.is_running():
        comp_scheduler.start()
    restore_scheduled()

@bot.command()
@commands.has_role("E-Board")
async def help(ctx):
    minute_message = f"{task_minute:02d}"
    # Split in two: Discord rejects messages over 2000 characters
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
* Use !mass_add [park] to add a park and all of its rides in one command. Duplicate entries will not be added.
* Use !pull to force pull an entry. This should typically only be used for testing or for manually changing the discussion early. The actual "!pull" message will be deleted to hide this.
* Use !delete [content] to remove an entry. Spelling must be exact. Use !wipe to delete the entire database. This CANNOT be undone!
''')
    await ctx.send(
f'''
**Task Reminders**
* Tasks with a due date are announced the day before that date. Tasks without a specific date are announced the day before the meeting day (currently {idx2week[task_day]}).
* Reminders are sent at {task_hour}:{minute_message}.
* Use !tasks to announce ALL incomplete E-Board tasks.
* Use !set_task_time [day] [24-hour time] to change the meeting day and reminder time. Use !get_task_time to see what it is currently set to.
* Use !enable_tasks or !disable_tasks to enable/disable automatic task reminders.
* Comp teams are reminded the day before their meeting at the meeting time, and again at 12:00 the day of.
* Use !set_rec, !set_rep_new, or !set_rep_cont [day] [24-hour time] to set each team's meeting. Use !get_comps to see them.
* Use !enable_comps or !disable_comps to enable/disable comp team reminders.

**Reminder Scheduling:**
* Use !schedule YYYY-MM-DD HH:MM [message] with the time in 24-hour time to schedule a reminder message.


Only members with the E-Board flair will be able to use any of the bot commands, including !help
''')

# Roller Coaster Database Management
async def await_confirmation(ctx, timeout=15):
    def check(m):
        return (
            m.author == ctx.author
            and m.channel == ctx.channel
            and m.content.lower().strip() in ["yes", "no"]
        )
    try:
        response = await bot.wait_for("message", check=check, timeout=timeout)
    except asyncio.TimeoutError:
        return None
    return response.content.lower().strip() == "yes"

async def add_function(ctx, message, mass=False):
    content, category, link = message
    confirm = f"CONFIRM: You are adding `{content}` as `{category}`"
    
    if not link:
        content_entry = get_by_entry(content) 
        if content_entry:
            await ctx.send(f"{content} already exists")
            return
    else:
         confirm += f" with link {link}"
    link_entry = get_by_link(link, True)
    if link_entry and category != "trivia" and link_entry["category"] != "trivia":
        await ctx.send(f"{content} already exists")
        return
    
    confirm += "? `[yes/no]`"
    if not mass:
        await ctx.send(confirm)

    author_id = ctx.author.id
    if mass:
        add_entry(content, category, author_id, link)
        return
    
    confirmed = await await_confirmation(ctx)
    if confirmed is None:
        await ctx.send("Confirmation timed out. Entry not added.")
        return
    if confirmed:
        add_entry(content, category, author_id, link)
        await ctx.send("Entry added")
    else:
        await ctx.send("Entry cancelled.")

def parse_message(message):
    try:
        parts = [m.strip() for m in message.split(',')]
        content = parts[0]
        category = parts[1].lower()
        link = parts[2] if len(parts) > 2 else None
        return (content, category, link)
    except:
        return None

@bot.command()
@commands.has_role("E-Board")
async def add(ctx, *, message):
    content = parse_message(message)
    if not content:
        await ctx.send("Formatting: !add [content], [category], [optional link]")
        return
    await add_function(ctx, content)

@bot.command()
@commands.has_role("E-Board")
async def mass_add(ctx, *, message):
    result = parse_park(message)
    if not result:
        await ctx.send("Could not find park")
        return
    
    await ctx.send("You are about to add the following entries:")

    formatted = "\n".join(
        f"• **{name}**, {category}, {link or 'no link'}"
        for name, category, link in result
    )
    embed = discord.Embed(
        description=formatted,
        color=discord.Color.orange()
    )
    embed.set_footer(text="Confirm with yes/no")
    await ctx.send(embed=embed)

    confirmed = await await_confirmation(ctx)
    if confirmed is None:
        await ctx.send("Confirmation timed out. Entries not added.")
        return
    if confirmed:
        for item in result:
            await add_function(ctx, item, mass=True)
        await ctx.send("New entries successfully added")
    else:
        await ctx.send("Mass adding cancelled.")

def format_entry(content):
    category = content['category']
    if category != 'discussion' and category != 'trivia':
        label = category.capitalize() + ' discussion'
    else:
        label = category.capitalize()
    message = f"**{label}:** {content['content']}"
    if content['link']:
        message += f" {content['link']}"
    return message

@bot.command()
@commands.has_role("E-Board")
async def pull(ctx):
    await ctx.message.delete()
    content = get_random()
    if content:
        await ctx.send(format_entry(content))
    else:
        await ctx.send("Database empty")

@task_module.loop(hours=discussion_time)
async def send():
    channel = bot.get_channel(CHANNEL)
    if channel and disc_enabled:
        content = get_random()
        if content:
            await channel.send(format_entry(content))

@bot.command()
@commands.has_role("E-Board")
async def get_disc_time(ctx):
    global discussion_time
    reminder = f"Current interval is {discussion_time / 24} day(s). Use !set_disc_time [interval] to change this."
    if not disc_enabled:
        reminder += " Note that automatic discussion is currently disabled."
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
    save_settings()
    reminder = f"Interval has been updated to {discussion_time / 24} day(s)."
    if not disc_enabled:
        reminder += " Note that automatic discussion is currently disabled."
    await ctx.send(reminder)

@bot.command()
@commands.has_role("E-Board")
async def disable_disc(ctx):
    global disc_enabled
    disc_enabled = False
    save_settings()
    await ctx.send("Discussion disabled")

@bot.command()
@commands.has_role("E-Board")
async def enable_disc(ctx):
    global disc_enabled
    disc_enabled = True
    save_settings()
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
    confirmed = await await_confirmation(ctx)
    if confirmed is None:
        await ctx.send("Confirmation timed out. Entry not deleted.")
        return
    if confirmed:
        delete_entry(message)
        await ctx.send(f"`{content['content']}` has been deleted.")
    else:
        await ctx.send("Deletion cancelled.")

@bot.command()
@commands.has_role("E-Board")
async def wipe(ctx):
    await ctx.send("**WARNING:** You are about to delete ALL entries. This cannot be undone. Type `yes` to confirm.")
    confirmed = await await_confirmation(ctx, timeout=30)
    if confirmed is None:
        await ctx.send("Confirmation timed out. No entries were deleted.")
        return
    if confirmed:
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
    
    entry = {"time": target_dt.isoformat(), "message": message}
    scheduled_messages.append(entry)
    save_settings()
    await ctx.send("Event successfully scheduled")
    asyncio.create_task(run_scheduled(entry))

async def run_scheduled(entry):
    target_dt = datetime.fromisoformat(entry["time"])
    delay = (target_dt - datetime.now(ZoneInfo("America/New_York"))).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    if entry not in scheduled_messages:
        return
    channel = bot.get_channel(EANNOUNCE)
    if channel:
        await channel.send(entry["message"])
    scheduled_messages.remove(entry)
    save_settings()

restored = False
def restore_scheduled():
    # Restart saved reminders after a reboot. Any that came due while the bot was down are sent right away.
    global restored
    if restored:
        return
    restored = True
    for entry in list(scheduled_messages):
        asyncio.create_task(run_scheduled(entry))



# E-Board Tasks
'''
Reminder protocol:
1. A task with a due date is reminded the day before that date.
2. A task without a date (Next Meeting, ASAP, --, weekly) is reminded the day before the meeting day.
3. EVERYONE tab tasks mention the E-Board role and hide status.
4. !tasks lists all incomplete tasks with pie messages included.
'''

def format_task(task, show_status=True):
    line = f"• **{task.title}**"
    if task.due_date:
        line += f" — Due: {task.due_date}"
    if show_status:
        line += f" — Status: {task.status}"
    return line

async def announce_tasks(role_tasks, everyone_tasks, pie):
    if everyone_tasks and EBOARD_ROLE:
        channel = bot.get_channel(EVERYONE_CHANNEL)
        if channel:
            message_content = "\n".join(format_task(task, show_status=False) for task in everyone_tasks)
            embed = discord.Embed(description=message_content, color=discord.Color.gold())
            await channel.send(content=f"<@&{EBOARD_ROLE}>", embed=embed)
    for role in IDs:
        tasklist = role_tasks.get(role, [])
        if not tasklist:
            continue
        channel = bot.get_channel(ROLE_CHANNELS.get(role, TASKS))
        if not channel:
            continue
        message_content = "\n".join(format_task(task) for task in tasklist)
        if pie.get(role, 0) >= 3:
            message_content += "\n" + "🥧" + get_pie_message() + "🥧"
        embed = discord.Embed(description=message_content, color=discord.Color.gold())
        mentions = " ".join(f"<@{user_id}>" for user_id in IDs[role])
        await channel.send(content=mentions, embed=embed)

@bot.command()
@commands.has_role("E-Board")
async def tasks(ctx):
    role_tasks, everyone_tasks = get_tasks()
    pie = get_pie(role_tasks)
    await announce_tasks(role_tasks, everyone_tasks, pie)

@task_module.loop(time=time(hour=task_hour, minute=task_minute, tzinfo=ZoneInfo("America/New_York")))
async def task_scheduler():
    if not task_enabled:
        return
    role_tasks, everyone_tasks = get_tasks()
    pie = get_pie(role_tasks)
    due_role = {role: [task for task in tasklist if reminder_due_today(task, task_day)]
                for role, tasklist in role_tasks.items()}
    due_everyone = [task for task in everyone_tasks if reminder_due_today(task, task_day)]
    await announce_tasks(due_role, due_everyone, pie)

@bot.command()
@commands.has_role("E-Board")
async def get_task_time(ctx):
    minute_message = f"{task_minute:02d}"
    enabled_message = "enabled" if task_enabled else "disabled"
    await ctx.send(f"Automatic reminders are currently {enabled_message}. The meeting day is set to {idx2week[task_day]}; undated tasks are reminded the day before it and dated tasks the day before their due date. Reminders are sent at {task_hour}:{minute_message}. Use !set_task_time [day] [24-hour time] to change the meeting day and reminder time.")

@bot.command()
@commands.has_role("E-Board")
async def set_task_time(ctx, *, message):
    parts = message.strip().split()
    if len(parts) != 2:
        await ctx.send("Format: !set_task_time [day] [24-hour time]")
        return
    day, time_str = parts
    day = day.strip().title()
    if day not in week2idx:
        await ctx.send("Invalid weekday. Use a day name like Wednesday.")
        return
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", time_str)
    if not match:
        await ctx.send("Time must be 24-hour HH:MM (e.g., 17:30).")
        return
    
    global task_day, task_hour, task_minute
    task_day = week2idx[day]
    task_hour = int(match.group(1))
    task_minute = int(match.group(2))
    minute_message = f"{task_minute:02d}"

    new_time = time(
        hour=task_hour,
        minute=task_minute,
        tzinfo=ZoneInfo("America/New_York")
    )
    task_scheduler.change_interval(time=new_time)
    save_settings()
    if task_scheduler.is_running():
        task_scheduler.restart()

    reminder = f"Meeting day is set to {idx2week[task_day]}. Reminders are sent at {task_hour}:{minute_message}."
    if not task_enabled:
        reminder += " Note that task reminders are currently disabled."
    await ctx.send(reminder)
@bot.command()
@commands.has_role("E-Board")
async def enable_tasks(ctx):
    global task_enabled 
    task_enabled = True
    save_settings()
    minute_message = f"{task_minute:02d}"
    await ctx.send(f"Automatic task reminders are now enabled. Meeting day is {idx2week[task_day]} and reminders are sent at {task_hour}:{minute_message}.")

@bot.command()
@commands.has_role("E-Board")
async def disable_tasks(ctx):
    global task_enabled 
    task_enabled = False
    save_settings()
    await ctx.send("Automatic task reminders are now disabled.")

# Competition Team Reminders
def format_12hr(hour, minute):
    suffix = "AM" if hour < 12 else "PM"
    return f"{hour % 12 or 12}:{minute:02d} {suffix}"

def comp_summary(key):
    team = COMPS[key]
    if team["day"] is None:
        return f"{team['name']}: not set"
    return f"{team['name']}: {idx2week[team['day']]} at {format_12hr(team['hour'], team['minute'])}"

async def set_comp(ctx, key, message):
    command = f"!set_{key}"
    parts = message.strip().split() if message else []
    if len(parts) != 2:
        await ctx.send(f"Format: {command} [day] [24-hour time]")
        return
    day, time_str = parts
    day = day.strip().title()
    if day not in week2idx:
        await ctx.send("Invalid weekday. Use a day name like Wednesday.")
        return
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", time_str)
    if not match:
        await ctx.send("Time must be 24-hour HH:MM (e.g., 17:30).")
        return

    team = COMPS[key]
    team["day"] = week2idx[day]
    team["hour"] = int(match.group(1))
    team["minute"] = int(match.group(2))
    save_settings()

    reply = f"{comp_summary(key)}."
    if team["hour"] < COMP_DAY_OF_HOUR or (team["hour"] == COMP_DAY_OF_HOUR and team["minute"] == 0):
        reply += " Since the meeting is at or before 12:00, only the day-before reminder will be sent."
    if not comps_enabled:
        reply += " Note that competition team reminders are currently disabled."
    await ctx.send(reply)

@bot.command()
@commands.has_role("E-Board")
async def set_rec(ctx, *, message=""):
    await set_comp(ctx, "rec", message)

@bot.command()
@commands.has_role("E-Board")
async def set_rep_new(ctx, *, message=""):
    await set_comp(ctx, "rep_new", message)

@bot.command()
@commands.has_role("E-Board")
async def set_rep_cont(ctx, *, message=""):
    await set_comp(ctx, "rep_cont", message)

@bot.command()
@commands.has_role("E-Board")
async def get_comps(ctx):
    enabled_message = "enabled" if comps_enabled else "disabled"
    lines = "\n".join(f"* {comp_summary(key)}" for key in COMPS)
    await ctx.send(f"Competition team reminders are currently {enabled_message}.\n{lines}")

@bot.command()
@commands.has_role("E-Board")
async def enable_comps(ctx):
    global comps_enabled
    comps_enabled = True
    save_settings()
    await ctx.send("Competition team reminders are now enabled.")

@bot.command()
@commands.has_role("E-Board")
async def disable_comps(ctx):
    global comps_enabled
    comps_enabled = False
    save_settings()
    await ctx.send("Competition team reminders are now disabled.")

async def send_comp_reminder(key, when):
    team = COMPS[key]
    channel = bot.get_channel(team["channel"])
    if not channel:
        return
    meeting_time = format_12hr(team["hour"], team["minute"])
    await channel.send(f"<@&{team['role']}> just a reminder we are meeting {when} at {meeting_time}")

@task_module.loop(seconds=30)
async def comp_scheduler():
    if not comps_enabled:
        return
    now = datetime.now(ZoneInfo("America/New_York"))
    today = now.weekday()
    tomorrow = (today + 1) % 7
    for key, team in COMPS.items():
        if team["day"] is None:
            continue
        meeting_minutes = team["hour"] * 60 + team["minute"]
        now_minutes = now.hour * 60 + now.minute

        # Day before, at the meeting time
        if team["day"] == tomorrow and now_minutes == meeting_minutes:
            sent_key = (key, "before", now.date())
            if sent_key not in comps_sent:
                comps_sent.add(sent_key)
                await send_comp_reminder(key, "tomorrow")

        # Day of, at 12:00 (only if the meeting is after noon)
        if team["day"] == today and now_minutes == COMP_DAY_OF_HOUR * 60 and meeting_minutes > COMP_DAY_OF_HOUR * 60:
            sent_key = (key, "today", now.date())
            if sent_key not in comps_sent:
                comps_sent.add(sent_key)
                await send_comp_reminder(key, "today")

    # Forget old entries so the set doesn't grow forever
    comps_sent.difference_update({k for k in comps_sent if k[2] < now.date()})

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
