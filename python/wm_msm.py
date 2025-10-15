import requests
import json
import csv
from datetime import datetime, timedelta
import time

# 開始・終了日
start_date = datetime(2020, 3, 31)
end_date = datetime(2025, 3, 30)

# 出力ファイル
csv_file = "msmgpv.csv"

# CSV ヘッダ
levels = ["surf", "925", "850", "700", "500"]
headers = ["date"]
for lv in levels:
    headers.extend([f"TMP_{lv}", f"RH_{lv}", f"U_{lv}", f"V_{lv}"])

rows = []

# 日付ループ
current = start_date
while current <= end_date:
    date_str = current.strftime("%Y%m%d")
    url = f"https://lab.weathermap.co.jp/MSMGPV_point/readGPV.php?amedas=40336&ini={date_str}00"
    print(f"{url}")

    try:
        # ブラウザ風ヘッダ
        headers_req = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "Referer": "https://lab.weathermap.co.jp/MSMGPV_point/"
        }

        resp = requests.get(url, headers=headers_req, timeout=30)  # タイムアウト延長
        resp.raise_for_status()

        text = resp.text.strip()

        # JSON部分のみ抽出
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start == -1 or json_end == -1:
            raise ValueError("JSON構造が見つかりません")
        json_text = text[json_start:json_end]

        data = json.loads(json_text)

        # キー "21" を取得
        record = data.get("21", {})
        row = [date_str]
        for lv in levels:
            lv_data = record.get(lv, {})
            tmp = lv_data.get("TMP", "")
            rh = lv_data.get("RH", "")
            u = lv_data.get("U", "")
            v = lv_data.get("V", "")
            row.extend([tmp, rh, u, v])

        rows.append(row)

    except Exception as e:
        print(f"{date_str} の取得失敗: {e}")
        row = [date_str] + [""] * (len(levels) * 4)
        rows.append(row)

    current += timedelta(days=1)
    
    # リクエスト間隔を空ける（1秒待機）
    time.sleep(1)

# CSV 出力
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(rows)

print(f"{csv_file} に保存しました")
