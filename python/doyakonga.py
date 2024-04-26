import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time

def scrape_tweet_content(url):
    # アーカイブURLを追加したURLを作成
    archive_url = f"https://web.archive.org/web/20221225063448/{url}"
    
    # リクエストのリトライとタイムアウト設定
    retries = 1
    time.sleep(3)
    for _ in range(retries):
        try:
            response = requests.get(archive_url, timeout=10)  # タイムアウトを10秒に設定
            response.raise_for_status()  # HTTPエラーチェック
            break  # 成功した場合はループを抜ける
        except requests.exceptions.RequestException as e:
            print(f"Error accessing URL: {e}")
            
    else:
        # リトライが失敗した場合
        print(f"Failed to access URL after {retries} retries.")
        return None
    
    # 正常なレスポンスが得られた場合は解析
    soup = BeautifulSoup(response.text, 'html.parser')
    meta_tag = soup.find("meta", property="og:description")
    print(url)
    if meta_tag:
        tweet_text = meta_tag['content']
        return tweet_text
    else:
        return None

def extract_twitter_id(url):
    # TwitterのツイートIDをURLから抽出する
    return url.split("/")[-1]

def convert_twitter_id_to_datetime(twitter_id):
    # Snowflake IDから投稿時刻を計算する
    twitter_id = int(twitter_id)  # 文字列から数値に変換
    timestamp_ms = ((twitter_id >> 22) + 1288834974657) / 1000
    return datetime.fromtimestamp(timestamp_ms)

def read_urls_from_file(file_path):
    # ファイルからURLのリストを読み込む
    urls = []
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith("https://twitter.com/"):
                urls.append(line)
    return urls

def write_to_csv(results, output_file):
    # 結果をCSVファイルに書き込む
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Original_URL', 'Converted_Datetime', 'Tweet_Content']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({'Original_URL': result[0], 'Converted_Datetime': result[1], 'Tweet_Content': result[2]})

def main():
    input_file_path = 'doya.txt'
    output_file_path = 'output.csv'

    urls = read_urls_from_file(input_file_path)

    results = []
    for url in urls:
        twitter_id = extract_twitter_id(url)
        try:
            tweet_datetime = convert_twitter_id_to_datetime(twitter_id)
            tweet_content = scrape_tweet_content(url)
            results.append((url, tweet_datetime, tweet_content))
        except Exception as e:
            print(f"Error processing URL {url}: {e}")

    write_to_csv(results, output_file_path)
    print(f"CSV file '{output_file_path}' has been created successfully.")

if __name__ == "__main__":
    main()
