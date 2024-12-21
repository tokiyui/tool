import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# テレビとラジオのベースURL
tv_base_url = "https://www.tvkingdom.jp/schedulesBySearch.action?stationPlatformId=0&condition.keyword="
radio_base_url = "https://api.radiko.jp/v3/api/program/search?key={}&filter=&start_day=&end_day=&region_id=&cul_area_id=JP13&page_idx=0&uid=72e7122114d9432aa3e976c0a3a7b8a4&row_limit=12&app_id=pc&cur_area_id=JP13&action_id=0"

# 検索キーワード
keywords = ["超ときめき宣伝部", "辻野かなみ", "杏ジュリア", "坂井仁香", "小泉遥香", "菅田愛貴", "吉川ひより", "藤本ばんび", "小高サラ", "パブりん"]

# テレビとラジオの結果を保存する辞書
tv_programs = defaultdict(lambda: {"time": "", "keywords": set()})
radio_programs = defaultdict(lambda: {"start_time": "", "stations": set(), "keywords": set()})

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
                time = time_elem.contents[0].strip().replace(' ', '').replace('  ', '')
            else:
                continue

            # 辞書に追加（既存の場合はキーワードを追加）
            tv_programs[title]["time"] = time
            tv_programs[title]["keywords"].add(keyword)
    else:
        print(f"No data found for keyword (TV): {keyword}")

# ラジオの情報を取得
for keyword in keywords:
    url = radio_base_url.format(keyword)
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        if "data" in data:
            for program in data["data"]:
                start_time = program.get("start_time")
                program_name = program.get("title")
                station = program.get("station_id")

                # 辞書に追加（既存の場合はキーワードと局を追加）
                radio_programs[program_name]["start_time"] = start_time
                radio_programs[program_name]["stations"].add(station)
                radio_programs[program_name]["keywords"].add(keyword)
    else:
        print(f"No data found for keyword (Radio): {keyword}")

# メール内容を作成
email_content = "=== テレビ番組 ===\n"
for title, info in sorted(tv_programs.items(), key=lambda x: x[1]["time"]):
    email_content += f"タイトル: {title}\n"
    email_content += f"時間: {info['time']}\n"
    email_content += f"キーワード: {', '.join(info['keywords'])}\n"
    email_content += "-" * 40 + "\n"

email_content += "\n=== ラジオ番組 ===\n"
for program_name, info in sorted(radio_programs.items(), key=lambda x: x[1]["start_time"]):
    email_content += f"番組名: {program_name}\n"
    email_content += f"放送開始: {info['start_time']}\n"
    email_content += f"局: {', '.join(info['stations'])}\n"
    email_content += f"キーワード: {', '.join(info['keywords'])}\n"
    email_content += "-" * 40 + "\n"

# Gmailの設定
your_email = "your_email@gmail.com"
your_password = "your_app_password"

# メールを送信
try:
    msg = MIMEMultipart()
    msg["From"] = your_email
    msg["To"] = your_email
    msg["Subject"] = "テレビとラジオの番組情報"

    # メール本文を追加
    msg.attach(MIMEText(email_content, "plain"))

    # SMTPサーバーに接続して送信
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(your_email, your_password)
        server.sendmail(your_email, your_email, msg.as_string())

    print("メールを送信しました！")
except Exception as e:
    print(f"メールの送信中にエラーが発生しました: {e}")
