import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math
import os
import json

# --- 定数 ---
TARGET_LON = 136.633
TARGET_LAT = 36.588
RADIUS_KM = 50
BASE_URL = "https://lab.weathermap.co.jp/SAT_RDR_LIDEN_api/v1/LIDEN"

# --- Haversine距離 (ベクトル化対応) ---
def haversine_np(lon, lat, lon0, lat0):
    R = 6371.0
    lon, lat = np.radians(lon), np.radians(lat)
    lon0, lat0 = math.radians(lon0), math.radians(lat0)
    dlon = lon - lon0
    dlat = lat - lat0
    a = np.sin(dlat/2)**2 + np.cos(lat0) * np.cos(lat) * np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

# --- データ取得（キャッシュ付き） ---
def fetch_liden(year, yyyymmdd, hhmm, cache_dir="liden_cache"):
    os.makedirs(cache_dir, exist_ok=True)
    fname = os.path.join(cache_dir, f"LIDEN_{yyyymmdd}-{hhmm}.json")
    if os.path.exists(fname):
        with open(fname, "r") as f:
            return json.load(f)
    url = f"{BASE_URL}/{year}/{yyyymmdd}/LIDEN_{yyyymmdd}-{hhmm}.json"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        with open(fname, "w") as f:
            json.dump(data, f)
        return data
    return []

# --- 判定処理 ---
def check_nearby(cur):
    yyyymmdd = cur.strftime("%Y%m%d")
    year = cur.strftime("%Y")

    # 前後3時間のデータを一括取得
    window_start = cur - timedelta(hours=3)
    window_end   = cur + timedelta(hours=3)

    all_points = []
    t = window_start
    while t <= window_end:
        hhmm = t.strftime("%H%M")
        data = fetch_liden(year, yyyymmdd, hhmm)
        if data:
            all_points.extend(data)
        t += timedelta(minutes=1)

    if not all_points:
        return 0

    arr = np.array(all_points)
    lon = arr[:,1].astype(float)
    lat = arr[:,2].astype(float)

    dist = haversine_np(lon, lat, TARGET_LON, TARGET_LAT)
    return int(np.any(dist <= RADIUS_KM))

# --- メイン処理 ---
results = []
start = datetime(2023, 6, 1, 9, 0)
end   = datetime(2025, 10, 1, 9, 0)

cur = start
while cur <= end:
    flag = check_nearby(cur)
    results.append([cur.strftime("%Y%m%d"), cur.strftime("%H"), flag])
    print(results[-1])
    cur += timedelta(hours=3)

# --- CSV出力 ---
df = pd.DataFrame(results, columns=["date","hour","flag"])
df.to_csv("liden_check.csv", index=False)

