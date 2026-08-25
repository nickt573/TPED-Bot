import gspread
import os
import random
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials

IDs = {
    "PRESIDENT": 928901718161391677,
    "VICE PRESIDENT": 343055950229405696,
    "TREASURER": 1428063807833378896,
    "SECRETARY": 460826614368960512,
    "MR CHAIR": 699427677383294986,
    "EVENTS CHAIR": 1389031753766666371,
    "PR CHAIRS 0": 764647197438246942, # Suta
    "PR CHAIRS 1": 699288806129664061, # Grace
    "C&P CHAIRS 0": 1387497255912734883,
    "C&P CHAIRS 1": 1466939482396819522, # Eliana
    "FUNDRAISING CHAIR": 1210769211828207676,
    "PDEV CHAIR": 1248104189427454003
}

SINGLE_TABS = {
    "PRESIDENT",
    "VICE PRESIDENT",
    "TREASURER",
    "SECRETARY",
    "MR CHAIR",
    "EVENTS CHAIR",
    "FUNDRAISING CHAIR",
    "PDEV CHAIR",
}

TWO_PERSON_TABS = {
    "PR CHAIRS": ("PR CHAIRS 0", "PR CHAIRS 1"),
    "C&P Chairs": ("C&P CHAIRS 0", "C&P CHAIRS 1"),
}

EVERYONE_TAB = "EVERYONE"
PIE_TAB = "🥧"

PIE_HEADER_TO_ROLES = {
    "president": ["PRESIDENT"],
    "vice president": ["VICE PRESIDENT"],
    "treasurer": ["TREASURER"],
    "secretary": ["SECRETARY"],
    "member relations": ["MR CHAIR"],
    "events chair": ["EVENTS CHAIR"],
    "public relations": ["PR CHAIRS 0", "PR CHAIRS 1"],
    "competitions and projects": ["C&P CHAIRS 0", "C&P CHAIRS 1"],
    "fundraising chair": ["FUNDRAISING CHAIR"],
    "professional development": ["PDEV CHAIR"],
}

DONE = {"COMPLETED", "DISMISSED"}
WEEKLY_DUE = "Next Meeting"
TZ = ZoneInfo("America/New_York")

class Task:
    def __init__(self, title, due_date, task_type, status):
        self.title = title
        self.due_date = due_date   # raw sheet string or None
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

def _make_task(title, due, status, task_type):
    title = title.strip()
    if not title or title == "--":
        return None
    if status.strip() in DONE:
        return None
    due = due.strip()
    if due in ("", "--"):
        due = None
    return Task(title, due, task_type, status.strip())

def _parse_single(rows):
    specifics = []
    weeklies = []
    for row in rows[1:]:
        while len(row) < 5:
            row.append("")
        specific = _make_task(row[0], row[1], row[2], "specific")
        if specific:
            specifics.append(specific)
        weekly = _make_task(row[3], WEEKLY_DUE, row[4], "weekly")
        if weekly:
            weeklies.append(weekly)
    return specifics + weeklies

def _parse_two_person(rows):
    sp_0, sp_1, wk_0, wk_1 = [], [], [], []
    for row in rows[2:]:
        while len(row) < 7:
            row.append("")
        due = row[2]
        sp_status = row[3]
        wk_status = row[6]
        for title, out in ((row[0], sp_0), (row[1], sp_1)):
            t = _make_task(title, due, sp_status, "specific")
            if t:
                out.append(t)
        for title, out in ((row[4], wk_0), (row[5], wk_1)):
            t = _make_task(title, WEEKLY_DUE, wk_status, "weekly")
            if t:
                out.append(t)
    return sp_0 + wk_0, sp_1 + wk_1

def get_tasks():
    role_tasks = {}
    everyone_tasks = []
    init_tasks()
    if not worksheets:
        return role_tasks, everyone_tasks
    for ws in worksheets:
        title = ws.title
        try:
            rows = ws.get_all_values()
        except Exception as e:
            print(f"Failed to read tab {title}: {e}")
            continue
        if not rows:
            continue
        if title == EVERYONE_TAB:
            everyone_tasks = _parse_single(rows)
        elif title in SINGLE_TABS:
            role_tasks[title] = _parse_single(rows)
        elif title in TWO_PERSON_TABS:
            key_0, key_1 = TWO_PERSON_TABS[title]
            role_tasks[key_0], role_tasks[key_1] = _parse_two_person(rows)
    return role_tasks, everyone_tasks

def get_pie(role_tasks):
    if worksheets is None:
        init_tasks()
    base = {}
    ws = None
    for w in (worksheets or []):
        if w.title == PIE_TAB:
            ws = w
            break
    if ws is not None:
        try:
            rows = ws.get_all_values()
        except Exception as e:
            print(f"Failed to read tab {PIE_TAB}: {e}")
            rows = []
        if len(rows) >= 2:
            headers, values = rows[0], rows[1]
            for i, header in enumerate(headers):
                roles = PIE_HEADER_TO_ROLES.get(header.strip().lower())
                if not roles:
                    continue
                value = values[i].strip() if i < len(values) else ""
                if value == "":
                    points = 0.0
                else:
                    try:
                        points = float(value)
                    except ValueError:
                        points = 3.0
                for role in roles:
                    base[role] = points
    rv = {}
    for role in set(role_tasks) | set(base):
        rv[role] = base.get(role, 0) + len(role_tasks.get(role, []))
    return rv

def parse_due_date(due):
    if not due:
        return None
    s = due.strip()
    if s in ("", "--"):
        return None
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        pass
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    today = datetime.now(TZ).date()
    try:
        month_str, day_str = s.split("/")
        target = date(today.year, int(month_str), int(day_str))
        if target < today:
            target = date(today.year + 1, int(month_str), int(day_str))
        return target
    except Exception:
        return None

def reminder_due_today(task, meeting_day):
    today = datetime.now(TZ).date()
    target = parse_due_date(task.due_date)
    if target is not None:
        return target - timedelta(days=1) == today
    return (today + timedelta(days=1)).weekday() == meeting_day

def get_pie_message():
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
