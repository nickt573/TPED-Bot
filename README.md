TPED Bot is a custom-made Discord bot for Binghamton University's Theme Park Engineering and Design Club. The focus of the design is specifically for the members of this club, as many of the features are hard-coded to support this.

The functionality of the bot, as seen from the !help command, is as follows:

Industry Discussion:
Every 2 day(s) I will randomly select an entry to stimulate discussion.
Use !set_disc_time [days] to update this interval. Use !get_disc_time to see the currently set interval.
Use !enable_disc or !disable_disc to enable/disable automatic discussion.
Use !add [content], [category], [optional link] to add to the database.
      Content: The actual ride name, trivia fact, manufacturer, ride element, etc.
      Category: Any of the following: park, manufacturer, ride, element, model, trivia, or discussion. Do not diverge from this list.
      Link: Optional link, but extremely recommended. Use RCDB.com for links.
Use !pull to force pull an entry. This should typically only be used for testing or for manually changing the discussion early. The actual "!pull" message will be deleted to hide this.
Use !delete [content] to remove an entry. Spelling must be exact. Use !wipe to delete the entire database. This CANNOT be undone!

Reminder Scheduling:
Use !schedule YYYY-MM-DD HH:MM [message] with the time in 24-hour time to schedule a reminder message.

E-Board Task Reminders
Tasks with a due date are announced the day before that date. Tasks without a specific date are announced the day before the meeting day (default Wednesday). Reminders are sent at 16:00.
EVERYONE-tab tasks are announced to the E-Board role with status hidden.
Use !tasks to announce ALL incomplete E-Board tasks.
Use !set_task_time [day] [24-hour time] to change the meeting day and reminder time. Use !get_task_time to see what it is currently set to.
Use !enable_tasks or !disable_tasks to enable/disable automatic task reminders.

File System:
- changelog.md: Record of all of the changelogs
- main.py: Main execution of commands for the bot
- scraper.py, tasks.py: Helper files to port functions to main.py
- database.py, entries.db: Handles persistence