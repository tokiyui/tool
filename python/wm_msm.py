import requests
import csv
from datetime import datetime, timedelta
 
# 開始・終了日
start_date = datetime(2025, 6, 1)
end_date = datetime(2025, 9, 30)
 
# 出力ファイル
csv_file = "msmgpv_tmp_rh.csv"
 
# CSV ヘッダ
levels = ["925", "850", "700", "500"]
headers = ["date"]
for lv in levels:
    headers.extend([f"TMP_{lv}", f"RH_{lv}"])
 
rows = []
 
# 日付ループ
current = start_date
while current <= end_date:
    date_str = current.strftime("%Y%m%d")
    url = f"https://lab.weathermap.co.jp/MSMGPV_point/readGPV.php?amedas=40336&ini={date_str}00"
   
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
 
        # キー "9" を取得
        record9 = data.get("9", {})
        row = [date_str]
 
        for lv in levels:
            lv_data = record9.get(lv, {})
            tmp = lv_data.get("TMP", "")
            rh = lv_data.get("RH", "")
            row.extend([tmp, rh])
 
        rows.append(row)
 
    except Exception as e:
        print(f"{date_str} の取得失敗: {e}")
        # 失敗した日は空欄で埋める
        row = [date_str] + [""] * (len(levels) * 2)
        rows.append(row)
 
    current += timedelta(days=1)
 
# CSV 出力
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(rows)
 
print(f"{csv_file} に保存しました")
