import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import json
from requests.adapters import HTTPAdapter, Retry

# === 設定 ===
LEVELS = [950,925,900,850,800,700,600,500,400,300,250,200]
LAT, LON = 36.588, 136.633 
BASE_URL = "https://lab.weathermap.co.jp/MSMGPV_point/readGPV_past.php"
CACHE_DIR = "gpv_cache"
CSV_FILE = "msm_point.csv"

os.makedirs(CACHE_DIR, exist_ok=True)

# === リトライ付きセッション ===
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[500,502,503,504])
session.mount("https://", HTTPAdapter(max_retries=retries))

def fetch_gpv(date_str, level):
    """指定日付と等圧面のJSONを取得（キャッシュあり）"""
    fname = os.path.join(CACHE_DIR, f"{date_str}_{level}.json")
    if os.path.exists(fname):
        with open(fname, "r") as f:
            return json.load(f)

    url = f"{BASE_URL}?lev={level}&lat={LAT}&lon={LON}&ymd={date_str}"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        with open(fname, "w") as f:
            json.dump(data, f)
        return data
    except Exception as e:
        print(f"? fetch failed {date_str} lev={level}: {e}")
        return {}

def process_day(date_str):
    """1日分のデータをまとめて行リストにする"""
    all_levels = {}
    for lev in LEVELS:
        all_levels[lev] = fetch_gpv(date_str, lev)

    # どの時刻キーがあるか（UTC）
    if not all_levels[LEVELS[0]]:
        return []
    utc_times = [k for k in all_levels[LEVELS[0]].keys() if k.isdigit()]

    rows = []
    for utctime in utc_times:
        try:
            utc_dt = datetime.strptime(utctime, "%Y%m%d%H")
        except ValueError:
            continue
        jst_dt = utc_dt + timedelta(hours=9)

        row = {
            "date": jst_dt.strftime("%Y%m%d"),
            "hour": jst_dt.strftime("%H")
        }
        for lev in LEVELS:
            levdata = all_levels[lev].get(utctime, {})
            if "TMP" in levdata and "RH" in levdata:
                tmp_c = float(levdata["TMP"]) - 273.15
                rh = float(levdata["RH"])
                row[f"{lev}TMP"] = tmp_c
                row[f"{lev}RH"] = rh
            else:
                row[f"{lev}TMP"] = None
                row[f"{lev}RH"] = None
        rows.append(row)
    return rows

# === メイン処理 ===
start = datetime(2017,5,1)
end   = datetime(2025,9,30)

header_written = os.path.exists(CSV_FILE)

cur = start
while cur <= end:
    date_str = cur.strftime("%Y%m%d")
    rows = process_day(date_str)
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(CSV_FILE, mode="a", index=False, header=not header_written)
        header_written = True
    print(f"? done {date_str} ({len(rows)} rows)")
    cur += timedelta(days=1)

print("?? 全期間の処理が完了しました")

