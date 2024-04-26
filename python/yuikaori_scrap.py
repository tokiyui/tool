import time
import requests
from bs4 import BeautifulSoup
 
# 出力ファイルのパス
output_file = 'output.txt'
 
# 出力ファイルを開き、内容をクリア
with open(output_file, 'w', encoding='utf-8') as output:
    pass
 
# URLの範囲を指定
for i in range(1, 5000):
    url = f'https://web.archive.org/web/20220815000000/http://www.ogurayui.jp/info/{i}/'
    print(f'Processing {url}')
    response = requests.get(url)
    time.sleep(15)
    # ステータスコードが200以外の場合はスキップ
    if response.status_code != 200:
        print(f'Skipping {url} - Status code: {response.status_code}')
        continue
    soup = BeautifulSoup(response.content, 'html.parser')
    content_div = soup.find('div', class_='content')
    if content_div:
        content = content_div.get_text(strip=True)
        with open(output_file, 'a', encoding='utf-8') as output:
            output.write(f'{url},{content}\n')

# URLの範囲を指定
for i in range(1, 3000):
    url = f'https://web.archive.org/web/20170630000000/http://www.yuikaori.info/info/{i}/'
    print(f'Processing {url}')
    response = requests.get(url)
    time.sleep(15)
    # ステータスコードが200以外の場合はスキップ
    if response.status_code != 200:
        print(f'Skipping {url} - Status code: {response.status_code}')
        continue
    soup = BeautifulSoup(response.content, 'html.parser')
    content_div = soup.find('div', class_='content')
    if content_div:
        content = content_div.get_text(strip=True)
        with open(output_file, 'a', encoding='utf-8') as output:
            output.write(f'{url},{content}\n')
 
print('Done!')
