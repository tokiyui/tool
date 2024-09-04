import requests
from bs4 import BeautifulSoup

url1 = 'https://www.eventernote.com/actors/2618/events?limit=2000'
url2 = 'https://www.eventernote.com/actors/2890/events?limit=2000'

def get_event_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    events = soup.find_all('li', class_='clearfix')
    
    data = []
    for event in events:
        date_elem = event.find('p', class_=lambda value: value and value.startswith('day'))
        if date_elem:
            date_str = date_elem.text.strip()
            date_info = date_str.split()
            year = date_info[0][:4]
            month = date_info[0][5:7]
            day = date_info[0][8:10]
            weekday = date_info[1][1]

            start_time_elem = event.find('span', class_='s')
            start_time = start_time_elem.text.strip().split()[3] if start_time_elem else '--:--'
        else:
            year = month = day = weekday = start_time = 'Date information not available'

        title_elem = event.find('h4')
        title = title_elem.text.strip() if title_elem else 'Title not available'

        venue_elem = event.find('div', class_='place')
        venue = venue_elem.text.strip().replace('会場:', '').strip() if venue_elem else 'Venue not available'
        
        data.append((year, month, day, weekday, start_time, title, venue))
    
    return data

data1 = get_event_data(url1)
data2 = get_event_data(url2)

# 共通する行を表示
for event_data in data1:
    if event_data in data2:
        print(','.join(event_data))
