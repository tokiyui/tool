import requests
from bs4 import BeautifulSoup

url = 'https://www.eventernote.com/actors/2618/events?limit=2000'

response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

events = soup.find_all('li', class_='clearfix')

with open('output.txt', 'w', encoding='utf-8') as file:
    file.write('Year,Month,Day,Weekday,Start Time,Event Name,Venue\n')  # ヘッダー行を書き込む
    for event in events:
        # 日付情報を取得
        date_elem = event.find('p', class_=lambda value: value and value.startswith('day'))
        if date_elem:
            date_str = date_elem.text.strip()
            date_info = date_str.split()
            year = date_info[0][:4]
            month = date_info[0][5:7]
            day = date_info[0][8:10]
            weekday = date_info[1][1]

            start_time_elem = event.find('span', class_='s')
            if start_time_elem:
                start_time = start_time_elem.text.strip().split()[3]  # 開演時刻のみ抽出
            else:
                start_time = '--:--'
        else:
            year = month = day = weekday = start_time = 'Date information not available'

        # イベント名を取得
        title_elem = event.find('h4')
        title = title_elem.text.strip() if title_elem else 'Title not available'

        # 会場を取得
        venue_elem = event.find('div', class_='place')
        venue = venue_elem.text.strip().replace('会場:', '').strip() if venue_elem else 'Venue not available'

        # データをコンソールに出力（デバッグ用）
        file.write(f'{year},{month},{day},{weekday},{start_time},{title},{venue}\n')
