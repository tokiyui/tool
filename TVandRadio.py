import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import json
import re
import pytz
import os

# Google Calendar API の認証情報
SERVICE_ACCOUNT_FILE = json.loads(os.environ["TokisenCalendar"])
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "67578b234641c2147039ad93ec542661ad13fcfa1be66bfac6fbc80e11075973@group.calendar.google.com"

# 認証
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build("calendar", "v3", credentials=credentials)

# TVとRadikoのURL設定
tv_base_url = "https://www.tvkingdom.jp/schedulesBySearch.action?stationPlatformId=0&condition.keyword="
base_date = datetime.datetime.now()
start_date = (base_date - datetime.timedelta(weeks=2)).strftime("%Y-%m-%d")
end_date = (base_date + datetime.timedelta(weeks=2)).strftime("%Y-%m-%d")

# 検索キーワード
keywords = ["超ときめき♡宣伝部", "超ときめき宣伝部", "辻野かなみ", "杏ジュリア", "坂井仁香", "小泉遥香", "菅田愛貴", "吉川ひより", "パブりん"]
radioids = [36347, 37521, 58704, 37519, 66284, 37530, 36598]
radiomembers = ["超ときめき宣伝部", "辻野かなみ", "杏ジュリア", "坂井仁香", "小泉遥香", "菅田愛貴", "吉川ひより"]

# テレビ・ラジオの辞書
tv_programs = defaultdict(lambda: {"start_time": "", "end_time": "", "stations": set(), "members": set()})
radio_programs = defaultdict(lambda: {"start_time": "", "end_time": "", "stations": set(), "keywords": set()})

def convert_to_iso8601(timestr):
    # "4/15 7:05+09:00" のような文字列を、年を補って ISO8601 に変換する。
    now = datetime.datetime.now(pytz.timezone("Asia/Tokyo"))
    parsed_dt = datetime.datetime.strptime(timestr, "%m/%d %H:%M%z")  # 年なしでパース

    month_diff = parsed_dt.month - now.month

    if month_diff >= 2:
        year = now.year - 1  # 2ヶ月以上先 → 前年
    elif month_diff <= -2:
        year = now.year + 1  # 2ヶ月以上前 → 翌年
    else:
        year = now.year      # 近い月 → 今年

    parsed_dt = parsed_dt.replace(year=year)
    return parsed_dt.isoformat()

# 既存のGoogleカレンダーのイベントを取得
def get_existing_events():
    existing_events = []
    events_result = service.events().list(calendarId=CALENDAR_ID, maxResults=2500, singleEvents=True, orderBy="startTime").execute()

    for event in events_result.get("items", []):
        existing_events.append({
            "summary": event["summary"],
            "start": event["start"]["dateTime"],
        })
    return existing_events
# テレビの情報を取得
for keyword in keywords:
    url = tv_base_url + keyword
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        programs = soup.find_all('div', class_='utileList')

        for program in programs:
            title_elem = program.find('a')
            if title_elem:
                title = title_elem.text.strip()
            else:
                continue

            time_elem = program.find('p', class_='utileListProperty')
            if time_elem:
                time_str = time_elem.contents[0].strip().replace(' ', '').replace('  ', '')

                # 放送局名の取得 (分) の後の文字列を `<a href=` の前まで抽出
                station_match = re.search(r"\(\d+分\)\s*(.*?)\s*<a href=", str(time_elem))
                station_name = station_match.group(1).strip() if station_match else "不明"

                # 正規表現で開始時間と終了時間を抽出
                match = re.search(r"(\d{1,2}/\d{1,2})\([A-Za-z]{3}\)(\d{1,2}:\d{2})[～\-](\d{1,2}:\d{2})", time_str)

                if match:
                    date_part, start_time, end_time = match.groups()

                    # 開始時間と終了時間を辞書に追加
                    tv_programs[title]["start_time"] = f"{date_part} {start_time}+09:00"
                    tv_programs[title]["end_time"] = f"{date_part} {end_time}+09:00"
                    tv_programs[title]["stations"] = {station_name}
                    tv_programs[title]["members"].add(keyword)
                else:
                    print(f"時間情報解析失敗: {time_str}")
            else:
                continue
    else:
        print(f"No data found for keyword (TV): {keyword}")

# Radiko API からデータ取得
for radioid, member in zip(radioids, radiomembers):
    radiko_api_url = f"https://api.radiko.jp/program/api/v1/programs?person_id={radioid:d}&start_at_gte={start_date}T05:00:00%2B09:00&start_at_lt={end_date}T05:00:00%2B09:00"
    print(radioid)
    print(radiko_api_url)
    response = requests.get(radiko_api_url)
    if response.status_code == 200:
        try:
            program_data = response.json()
            for program in program_data.get("data", []):
                title = program.get("title", "不明")
                start_time = program.get("start_at", "")
                end_time = program.get("end_at", "")
                station = program.get("station_name", "")
                url = program.get("url", "")

                unique_key = f"{title}_{start_time}"
                radio_programs[unique_key] = {
                    "title": title,
                    "start_time": start_time,
                    "end_time": end_time,
                    "stations": {station},
                    "members": {member},
                    "url": url
                }
        except Exception as e:
            print(f"データ解析中にエラーが発生しました: {e}")
    else:
        print("Radiko APIのデータ取得に失敗しました")

# Googleカレンダーにイベントを追加
def add_event_to_calendar(summary, description, start_time, end_time):
    existing_events = get_existing_events()

    for event in existing_events:
        if event["summary"] == summary and event["start"] == start_time:
            print(f"イベント '{summary}' は既にカレンダーに存在します。")
            return

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": "Asia/Tokyo"},
        "end": {"dateTime": end_time, "timeZone": "Asia/Tokyo"},
    }
    event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    print(f"イベント追加: {summary} ({event.get('htmlLink')})")

# TV番組をカレンダーに追加
for title, info in tv_programs.items():
    event_title = f"【テレビ】{title}"
    description = f"局: {', '.join(info['stations'])}　出演: {', '.join(info['members'])}"
    start_time = convert_to_iso8601(info['start_time'])
    end_time = convert_to_iso8601(info['end_time'])

    if start_time and end_time:
        add_event_to_calendar(event_title, description, start_time, end_time)

# ラジオ番組をカレンダーに追加
for program_name, info in radio_programs.items():
    event_title = f"【ラジオ】{info['title']}"
    description = f"局: {', '.join(info['stations'])}　出演: {', '.join(info['members'])}"
    start_time = info['start_time']
    end_time = info['end_time']

    if start_time and end_time:
        add_event_to_calendar(event_title, description, start_time, end_time)
