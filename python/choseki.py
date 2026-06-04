from datetime import datetime
from tidegravity import solve_point_corr
from scipy.signal import argrelmax, argrelmin
import numpy as np
import pandas as pd

lat = 35.689556
lon = 139.691722
alt = 0
t0 = datetime(1990, 12, 31, 0, 0, 0)

# 15秒ごと・4年分
days = 14610
seconds_per_day = 24 * 60 * 60
total_seconds = days * seconds_per_day
n = total_seconds // 15

result_df = solve_point_corr(lat, lon, alt, t0, n=n, increment="15s")

g0 = result_df.g0  # pandas Series想定
gx = g0.index      # datetime index想定

# --- JSTへ変換（重要） ---
# もしUTCならここで変換
gx_jst = pd.to_datetime(gx).tz_localize("UTC").tz_convert("Asia/Tokyo")

g0 = pd.Series(g0.values, index=gx_jst)

# --- 日単位で最大・最小・差 ---
daily_max = g0.resample("D").max()
daily_min = g0.resample("D").min()
daily_diff = daily_max - daily_min

# 出力用DataFrame
out_df = pd.DataFrame({
    "date": daily_max.index.date,
    "max": daily_max.values,
    "min": daily_min.values,
    "diff": daily_diff.values
})

# CSV出力
out_df.to_csv("daily_extrema_jst.csv", index=False, encoding="utf-8")

print("→ daily_extrema_jst.csv に保存しました")
