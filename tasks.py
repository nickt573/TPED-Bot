import gspread
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
import os

IDs = {
    "PRESIDENT": 928901718161391677,
    "VICE PRESIDENT": 343055950229405696,
    "TREASURER": 232914628177297408,
    "SECRETARY": 460826614368960512,
    "HISTORIAN": 699427677383294986,
    "EVENTS COORDINATOR": 1389031753766666371,
    "PUBLIC RELATIONS 0": 764647197438246942, # Suta
    "PUBLIC RELATIONS 1": 699288806129664061 # Grace
}

class Task:
    def __init__(self, title, due_date, task_type, status):
        self.title = title
        self.due_date = due_date   # date or None
        self.task_type = task_type # specific or weekly
        self.status = status

worksheets = None




def init_tasks():
    try:
        SCOPES = [os.getenv("SCOPES")]
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
        JSON_PATH = os.path.join(BASE_DIR, os.getenv("JSON")) 
        creds = Credentials.from_service_account_file(
            JSON_PATH,
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(
            os.getenv("TASK_DOC")
        )
        global worksheets
        worksheets = spreadsheet.worksheets()
    except Exception as e:
        print(f"Failed to parse tasks sheet, {e}")

def get_pie(sp_tasks, wk_tasks):
    pie = {}

    init_tasks()
    ws = worksheets[8]
    role = ws.title

    try:
        rows = ws.get_all_values()
    except Exception as e:
        print(f"Failed to read tab {role}: {e}")
        return {}

    if not rows or len(rows) < 2 or role != "🥧":
        print("Tab is empty or has no data rows.")
        return {}

    row = rows[1]
    for r, k in zip(row[:7], IDs.keys()):
        pie[k] = int(r)
        if k == "PUBLIC RELATIONS 0":
            pie["PUBLIC RELATIONS 1"] = int(r)

    rv = {}

    # Use union of keys so we don’t miss any roles
    all_roles = set(sp_tasks) | set(wk_tasks) | set(pie)

    for role in all_roles:
        sp_len = len(sp_tasks.get(role, []))
        wk_len = len(wk_tasks.get(role, []))
        pie_val = pie.get(role, 0)

        rv[role] = pie_val + sp_len + wk_len

    return rv

def get_tasks():
    sp_tasks = {}
    wk_tasks = {}
    init_tasks()
    for ws in worksheets[1:8]:
        role = ws.title
        try:
            rows = ws.get_all_values()
        except Exception as e:
            print(f"Failed to read tab {role}: {e}")
            continue
        if not rows or len(rows) < 2:
            print("Tab is empty or has no data rows.")
            continue

        # PR roles
        if role == "PUBLIC RELATIONS":
            specific_tasks_0= []
            specific_tasks_1 = []
            weekly_tasks_0 = []
            weekly_tasks_1 = []

            for row in rows[2:]:
                while len(row) < 7:
                    row.append("")
                specific_title_0 = row[0].strip()
                specific_title_1 = row[1].strip()
                if not specific_title_1:
                    specific_title_1 = specific_title_0
                due_date = row[2].strip()
                if due_date == "--":
                    due_date = None
                sp_status = row[3].strip()
                weekly_title_0 = row[4].strip()
                weekly_title_1 = row[5].strip()
                if not weekly_title_1:
                    weekly_title_1 = weekly_title_0
                wk_status = row[6].strip()
                # PR 0 specific and weekly tasks
                if specific_title_0 and specific_title_0 != "--" and sp_status not in {"COMPLETED", "DISMISSED"}:
                    specific_tasks_0.append(
                        Task(
                            title=specific_title_0,
                            due_date=due_date,
                            task_type="specific",
                            status=sp_status
                        )
                )
                if weekly_title_0 and weekly_title_0 != "--" and wk_status not in {"COMPLETED", "DISMISSED"}:
                    weekly_tasks_0.append(
                        Task(
                            title=weekly_title_0,
                            due_date=None,
                            task_type="weekly",
                            status=wk_status
                        )
                )
                # PR 1 specific and weekly tasks
                if specific_title_1 and specific_title_1 != "--" and sp_status not in {"COMPLETED", "DISMISSED"}:
                    specific_tasks_1.append(
                        Task(
                            title=specific_title_1,
                            due_date=due_date,
                            task_type="specific",
                            status=sp_status
                        )
                )
                if weekly_title_1 and weekly_title_1 != "--" and wk_status not in {"COMPLETED", "DISMISSED"}:
                    weekly_tasks_1.append(
                        Task(
                            title=weekly_title_1,
                            due_date=None,
                            task_type="weekly",
                            status=wk_status
                        )
                ) 
            sp_tasks["PUBLIC RELATIONS 0"] = specific_tasks_0
            wk_tasks["PUBLIC RELATIONS 0"] = weekly_tasks_0
            sp_tasks["PUBLIC RELATIONS 1"] = specific_tasks_1
            wk_tasks["PUBLIC RELATIONS 1"] = weekly_tasks_1
        else:
            # Rest of team tasks
            specific_tasks = []
            weekly_tasks = []
            for row in rows[1:]:
                while len(row) < 5:
                    row.append("")
                specific_title = row[0].strip()
                due_date = row[1].strip()
                if due_date == "--":
                    due_date = None
                weekly_title = row[3].strip()

                # Specific task
                status = row[2].strip()
                if specific_title and status not in {"COMPLETED", "DISMISSED"}:
                    specific_tasks.append(
                        Task(
                            title=specific_title,
                            due_date=due_date,
                            task_type="specific",
                            status=status
                        )
                    )
                # Weekly task
                status = row[4].strip()
                if weekly_title and status not in {"COMPLETED", "DISMISSED"}:
                    weekly_tasks.append(
                        Task(
                            title=weekly_title,
                            due_date=None,
                            task_type="weekly",
                            status=status
                        )
                    )
                sp_tasks[role] = specific_tasks
                wk_tasks[role] = weekly_tasks
    return sp_tasks, wk_tasks

def parse_day_of(date_str):
    if date_str == "--":
        return None
    try:
        month_str, day_str = date_str.strip().split("/")
        month = int(month_str)
        day = int(day_str)
    except Exception:
        return None

    today = datetime.now(ZoneInfo("America/New_York")).date()
    year = today.year
    try:
        target = date(year, month, day)
    except Exception:
        return None

    # If this year's date already passed, use next year
    if target < today:
        target = date(year + 1, month, day)
    return target


def parse_day_before(date_str):
    date = parse_day_of(date_str)
    if date is None:
        return None
    return date - timedelta(days=1)
    
def get_pie_message():
    import random
    warnings = [
        "Better finish those tasks… or I hope you like pie in the face",
        "Let me know how the pie tastes",
        "You’ve earned yourself dessert… it’s coming at you, full speed",
        "Tasks unfinished = face-full of pie",
        "Hope you enjoy whipped cream in your hair",
        "Procrastination smells like pie… soon, you’ll taste it too",
        "Some people chase success… you apparently chase pie",
        "Warning: Ignoring tasks may lead to severe pastry consequences",
        "A friendly reminder: the pie has your name on it",
        "Tasks pending? Pie incoming. I hope you like pumpkin",
        "You can’t outrun the pie, but you can try finishing your work",
        "Pro tip: finishing tasks reduces your pie exposure",
        "This is your official warning: pies are literal",
        "Face it: the pie knows your to-do list better than you do",
        "If you ignore your tasks, the pie will introduce itself personally",
        "Some deadlines bring stress. Yours bring pie",
        "I hope you like your desserts cold… because they’re coming soon",
        "You’ve got three strikes… the pie doesn’t forget",
        "Completing work keeps pies off your face. You choose",
        "Finish your tasks or the pie finishes you",
        "Your face has been scheduled for dessert",
        "Completion is optional; pie is guaranteed",
        "The pastry of justice awaits the negligent",
        "Tasks avoided are pies deployed"
    ]
    return random.choice(warnings)