import requests
from collections import defaultdict
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import pytz
import os

# =========================
# Google Calendar API
# =========================
SERVICE_ACCOUNT_FILE = json.loads(os.environ["TokisenCalendar"])

SCOPES = ["https://www.googleapis.com/auth/calendar"]

CALENDAR_ID = (
    "67578b234641c2147039ad93ec542661ad13fcfa1be66bfac6fbc80e11075973"
    "@group.calendar.google.com"
)

credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

service = build("calendar", "v3", credentials=credentials)

# =========================
# 日付
# =========================
base_date = datetime.now()

start_date = (base_date - timedelta(weeks=2)).strftime("%Y-%m-%d")
end_date = (base_date + timedelta(weeks=2)).strftime("%Y-%m-%d")

# =========================
# API
# =========================
TV_API_URL = "https://tvguide.myjcom.jp/api/mypage/get_searchresult/"

# =========================
# メンバー
# =========================
tv_members = [
    {"name": "超ときめき♡宣伝部", "originId": 314516},
    {"name": "辻野かなみ", "originId": 329636},
    {"name": "杏ジュリア", "originId": 376931},
    {"name": "坂井仁香", "originId": 323277},
    {"name": "小泉遥香", "originId": 327309},
    {"name": "菅田愛貴", "originId": 367005},
    {"name": "吉川ひより", "originId": 329639},
]

radio_members = [
    {"name": "超ときめき♡宣伝部", "person_id": 36347},
    {"name": "辻野かなみ", "person_id": 37521},
    {"name": "杏ジュリア", "person_id": 58704},
    {"name": "坂井仁香", "person_id": 37519},
    {"name": "小泉遥香", "person_id": 66284},
    {"name": "菅田愛貴", "person_id": 37530},
    {"name": "吉川ひより", "person_id": 36598},
]

# =========================
# 番組データ（重要修正）
# =========================
tv_programs = defaultdict(lambda: {
    "title": "",
    "start_time": "",
    "end_time": "",
    "stations": set(),
    "members": set(),
})

radio_programs = defaultdict(lambda: {
    "title": "",
    "start_time": "",
    "end_time": "",
    "stations": set(),
    "members": set(),
    "url": ""
})

# =========================
# ISO変換
# =========================
def convert_to_iso8601(timestr):
    now = datetime.now(pytz.timezone("Asia/Tokyo"))

    parsed_dt = datetime.strptime(timestr, "%m/%d %H:%M%z")

    month_diff = parsed_dt.month - now.month

    if month_diff >= 2:
        year = now.year - 1
    elif month_diff <= -2:
        year = now.year + 1
    else:
        year = now.year

    parsed_dt = parsed_dt.replace(year=year)

    return parsed_dt.isoformat()

# =========================
# Google Calendar
# =========================
def get_existing_events():
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    existing = []
    for e in events_result.get("items", []):
        if "dateTime" in e["start"]:
            existing.append({
                "summary": e["summary"],
                "start": e["start"]["dateTime"],
            })
    return existing


def add_event_to_calendar(summary, description, start_time, end_time):

    existing = get_existing_events()

    for e in existing:
        if e["summary"] == summary and e["start"] == start_time:
            print(f"既存イベント: {summary}")
            return

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": "Asia/Tokyo"},
        "end": {"dateTime": end_time, "timeZone": "Asia/Tokyo"},
    }

    created = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event
    ).execute()

    print(f"追加: {summary} ({created.get('htmlLink')})")

# =========================
# TV取得（修正版）
# =========================
for member in tv_members:

    payload = {
        "originId": member["originId"],
        "offset": 0,
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://tvguide.myjcom.jp/",
    }

    r = requests.post(TV_API_URL, data=payload, headers=headers, timeout=30)

    if r.status_code != 200:
        continue

    data = r.json()

    programs = data.get("body", {}).get("value", [])

    for p in programs:

        title = p.get("title", "不明")
        station = p.get("channel_name", "不明")

        start_raw = p.get("start_date", {}).get("date", "")

        try:
            start_dt = datetime.strptime(start_raw, "%Y-%m-%d %H:%M:%S.%f")
            air_time = int(p.get("air_time", 0))
            end_dt = start_dt + timedelta(minutes=air_time)

            start_time = start_dt.strftime("%m/%d %H:%M") + "+09:00"
            end_time = end_dt.strftime("%m/%d %H:%M") + "+09:00"

        except:
            continue

        key = f"{title}_{start_time}"

        tv_programs[key]["title"] = title
        tv_programs[key]["start_time"] = start_time
        tv_programs[key]["end_time"] = end_time
        tv_programs[key]["stations"].add(station)
        tv_programs[key]["members"].add(member["name"])

# =========================
# RADIO取得（完全修正）
# =========================
for member in radio_members:

    url = (
        "https://api.radiko.jp/program/api/v1/programs"
        f"?person_id={member['person_id']}"
        f"&start_at_gte={start_date}T05:00:00%2B09:00"
        f"&start_at_lt={end_date}T05:00:00%2B09:00"
    )

    r = requests.get(url)

    if r.status_code != 200:
        continue

    try:
        data = r.json()
    except:
        continue

    for p in data.get("data", []):

        title = p.get("title", "不明")
        start_time = p.get("start_at", "")
        end_time = p.get("end_at", "")
        station = p.get("station_name", "")
        link = p.get("url", "")

        key = f"{title}_{start_time}"

        radio_programs[key]["title"] = title
        radio_programs[key]["start_time"] = start_time
        radio_programs[key]["end_time"] = end_time
        radio_programs[key]["stations"].add(station)
        radio_programs[key]["members"].add(member["name"])
        radio_programs[key]["url"] = link

# =========================
# カレンダー追加
# =========================
for _, info in tv_programs.items():

    add_event_to_calendar(
        f"【テレビ】{info['title']}",
        f"局: {', '.join(info['stations'])} 出演: {', '.join(sorted(info['members']))}",
        convert_to_iso8601(info["start_time"]),
        convert_to_iso8601(info["end_time"])
    )

for _, info in radio_programs.items():

    add_event_to_calendar(
        f"【ラジオ】{info['title']}",
        f"局: {', '.join(info['stations'])} 出演: {', '.join(sorted(info['members']))} URL: {info['url']}",
        info["start_time"],
        info["end_time"]
    )
