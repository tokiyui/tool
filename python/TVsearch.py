import requests
from bs4 import BeautifulSoup
import re

base_url = "https://www.tvkingdom.jp/schedulesBySearch.action?stationPlatformId=0&condition.keyword="

keywords = ["超ときめき宣伝部", "辻野かなみ", "杏ジュリア", "坂井仁香", "小泉遥香", "菅田愛貴", "吉川ひより", "藤本ばんび" ,"小高サラ", "パブりん"]
program_dict = {}

for keyword in keywords:
    url = base_url + keyword
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        programs = soup.find_all('div', class_='utileList')

        for program in programs:
            title_elem = program.find('a')
            if title_elem:
                title = title_elem.text.strip()
            else:
                continue  # タイトルが見つからない場合、次のkeywordに移る

            time_elem = program.find('p', class_='utileListProperty')
            if time_elem:
                time = time_elem.contents[0].strip().replace(' ', '').replace('  ', '')
            else:
                continue  # 時間が見つからない場合、次のkeywordに移る

            key = (title, time)

            if key not in program_dict:
                program_dict[key] = url
    else:
        print(f"No data found for keyword: {keyword}")

# 結果を出力
for key, url in program_dict.items():
    title, time = key
    print(f"{title}\n{time}\n")
