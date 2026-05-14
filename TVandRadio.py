import requests
from collections import defaultdict
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import pytz
import os

# =========================
# Google Calendar API の認証情報
# =========================
SERVICE_ACCOUNT_FILE = json.loads(os.environ["TokisenCalendar"])

SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]

CALENDAR_ID = (
    "67578b234641c2147039ad93ec542661ad13fcfa1be66bfac6fbc80e11075973"
    "@group.calendar.google.com"
)

credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

service = build(
    "calendar",
    "v3",
    credentials=credentials
)

# =========================
# 日付設定
# =========================
base_date = datetime.now()

start_date = (
    base_date - timedelta(weeks=2)
).strftime("%Y-%m-%d")

end_date = (
    base_date + timedelta(weeks=2)
).strftime("%Y-%m-%d")

# =========================
# J:COM TV API
# =========================
TV_API_URL = (
    "https://tvguide.myjcom.jp/api/mypage/get_searchresult/"
)

# =========================
# TV出演者
# =========================
tv_members = [
    {
        "name": "超ときめき♡宣伝部",
        "originId": 314516,
    },
    {
        "name": "超ときめき宣伝部",
        "originId": 314516,
    },
    {
        "name": "辻野かなみ",
        "originId": 314516,
    },
    {
        "name": "杏ジュリア",
        "originId": 314516,
    },
    {
        "name": "坂井仁香",
        "originId": 314516,
    },
    {
        "name": "小泉遥香",
        "originId": 314516,
    },
    {
        "name": "菅田愛貴",
        "originId": 314516,
    },
    {
        "name": "吉川ひより",
        "originId": 314516,
    },
    {
        "name": "パブりん",
        "originId": 314516,
    },
]

# =========================
# ラジオ出演者
# =========================
radio_members = [
    {
        "name": "超ときめき宣伝部",
        "person_id": 36347,
    },
    {
        "name": "辻野かなみ",
        "person_id": 37521,
    },
    {
        "name": "杏ジュリア",
        "person_id": 58704,
    },
    {
        "name": "坂井仁香",
        "person_id": 37519,
    },
    {
        "name": "小泉遥香",
        "person_id": 66284,
    },
    {
        "name": "菅田愛貴",
        "person_id": 37530,
    },
    {
        "name": "吉川ひより",
        "person_id": 36598,
    },
]

# =========================
# 番組保存
# =========================
tv_programs = defaultdict(lambda: {
    "start_time": "",
    "end_time": "",
    "stations": set(),
    "members": set(),
})

radio_programs = defaultdict(lambda: {
    "start_time": "",
    "end_time": "",
    "stations": set(),
    "members": set(),
})

# =========================
# ISO8601変換
# =========================
def convert_to_iso8601(timestr):

    now = datetime.now(
        pytz.timezone("Asia/Tokyo")
    )

    parsed_dt = datetime.strptime(
        timestr,
        "%m/%d %H:%M%z"
    )

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
# 既存Googleカレンダー取得
# =========================
def get_existing_events():

    existing_events = []

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    for event in events_result.get("items", []):

        if "dateTime" not in event["start"]:
            continue

        existing_events.append({
            "summary": event["summary"],
            "start": event["start"]["dateTime"],
        })

    return existing_events

# =========================
# Googleカレンダー追加
# =========================
def add_event_to_calendar(
    summary,
    description,
    start_time,
    end_time
):

    existing_events = get_existing_events()

    for event in existing_events:

        if (
            event["summary"] == summary
            and event["start"] == start_time
        ):
            print(
                f"既存イベント: {summary}"
            )
            return

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_time,
            "timeZone": "Asia/Tokyo",
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "Asia/Tokyo",
        },
    }

    event = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event
    ).execute()

    print(
        f"イベント追加: "
        f"{summary} "
        f"({event.get('htmlLink')})"
    )

# =========================
# TV情報取得
# =========================
for member in tv_members:

    member_name = member["name"]
    origin_id = member["originId"]

    print("====================================")
    print(f"TV取得: {member_name}")
    print(f"originId: {origin_id}")
    print("====================================")

    payload = {
        "originId": origin_id,
        "offset": 0,
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://tvguide.myjcom.jp/",
    }

    response = requests.post(
        TV_API_URL,
        data=payload,
        headers=headers,
        timeout=30,
    )

    print(
        f"HTTP Status: "
        f"{response.status_code}"
    )

    if response.status_code != 200:
        print("取得失敗")
        continue

    print("\n===== RAW RESPONSE TEXT =====\n")
    print(response.text)

    try:
        data = response.json()

    except Exception as e:
        print("JSON解析失敗")
        print(e)
        continue

    print("\n===== PRETTY JSON =====\n")
    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )
    )

    programs = (
        data
        .get("body", {})
        .get("value", [])
    )

    print(f"\n番組数: {len(programs)}")

    for program in programs:

        title = program.get(
            "title",
            "不明"
        )

        station = program.get(
            "channel_name",
            "不明"
        )

        start_raw = (
            program
            .get("start_date", {})
            .get("date", "")
        )

        start_time = ""
        end_time = ""

        try:

            start_dt = datetime.strptime(
                start_raw,
                "%Y-%m-%d %H:%M:%S.%f"
            )

            air_time = int(
                program.get("air_time", 0)
            )

            end_dt = (
                start_dt
                + timedelta(minutes=air_time)
            )

            start_time = (
                start_dt.strftime(
                    "%m/%d %H:%M"
                )
                + "+09:00"
            )

            end_time = (
                end_dt.strftime(
                    "%m/%d %H:%M"
                )
                + "+09:00"
            )

        except Exception as e:
            print("日時解析失敗")
            print(e)

        print("------------------------------------")
        print("タイトル:", title)
        print("局:", station)
        print("開始:", start_time)
        print("終了:", end_time)
        print("------------------------------------")

        tv_programs[title]["start_time"] = start_time
        tv_programs[title]["end_time"] = end_time
        tv_programs[title]["stations"].add(station)
        tv_programs[title]["members"].add(member_name)

# =========================
# Radiko API取得
# =========================
for member in radio_members:

    member_name = member["name"]
    person_id = member["person_id"]

    radiko_api_url = (
        "https://api.radiko.jp/program/api/v1/programs"
        f"?person_id={person_id}"
        f"&start_at_gte={start_date}T05:00:00%2B09:00"
        f"&start_at_lt={end_date}T05:00:00%2B09:00"
    )

    print("====================================")
    print(f"RADIO取得: {member_name}")
    print(f"person_id: {person_id}")
    print("====================================")

    response = requests.get(radiko_api_url)

    if response.status_code == 200:

        try:

            program_data = response.json()

            for program in program_data.get(
                "data",
                []
            ):

                title = program.get(
                    "title",
                    "不明"
                )

                start_time = program.get(
                    "start_at",
                    ""
                )

                end_time = program.get(
                    "end_at",
                    ""
                )

                station = program.get(
                    "station_name",
                    ""
                )

                url = program.get(
                    "url",
                    ""
                )

                unique_key = (
                    f"{title}_{start_time}"
                )

                radio_programs[unique_key] = {
                    "title": title,
                    "start_time": start_time,
                    "end_time": end_time,
                    "stations": {station},
                    "members": {member_name},
                    "url": url,
                }

                print("------------------------------------")
                print("タイトル:", title)
                print("局:", station)
                print("開始:", start_time)
                print("終了:", end_time)
                print("------------------------------------")

        except Exception as e:
            print(
                f"データ解析中にエラー: {e}"
            )

    else:
        print(
            "Radiko API取得失敗"
        )

# =========================
# TV番組一覧
# =========================
print(
    "\n\n================ "
    "TV PROGRAMS "
    "================\n"
)

for title, info in tv_programs.items():

    print("タイトル:", title)
    print("開始:", info["start_time"])
    print("終了:", info["end_time"])
    print(
        "局:",
        ", ".join(info["stations"])
    )
    print(
        "出演:",
        ", ".join(info["members"])
    )
    print()

# =========================
# RADIO番組一覧
# =========================
print(
    "\n\n================ "
    "RADIO PROGRAMS "
    "================\n"
)

for _, info in radio_programs.items():

    print("タイトル:", info["title"])
    print("開始:", info["start_time"])
    print("終了:", info["end_time"])
    print(
        "局:",
        ", ".join(info["stations"])
    )
    print(
        "出演:",
        ", ".join(info["members"])
    )
    print("URL:", info["url"])
    print()

# =========================
# TV番組をカレンダー追加
# =========================
for title, info in tv_programs.items():

    event_title = f"【テレビ】{title}"

    description = (
        f"局: {', '.join(info['stations'])}"
        f"　出演: {', '.join(info['members'])}"
    )

    start_time = convert_to_iso8601(
        info["start_time"]
    )

    end_time = convert_to_iso8601(
        info["end_time"]
    )

    if start_time and end_time:

        add_event_to_calendar(
            event_title,
            description,
            start_time,
            end_time
        )

# =========================
# ラジオ番組をカレンダー追加
# =========================
for _, info in radio_programs.items():

    event_title = (
        f"【ラジオ】{info['title']}"
    )

    description = (
        f"局: {', '.join(info['stations'])}"
        f"　出演: {', '.join(info['members'])}"
    )

    start_time = info["start_time"]
    end_time = info["end_time"]

    if start_time and end_time:

        add_event_to_calendar(
            event_title,
            description,
            start_time,
            end_time
        )
