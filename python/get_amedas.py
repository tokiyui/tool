import datetime as dt
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from tqdm import tqdm
 
# 取得対象の地点リスト（茨城・千葉・埼玉・東京・神奈川の気象官署・特別地域気象観測所）
stations = [
    {"no": 40, "id": 47629},   # 水戸
    {"no": 40, "id": 47646},   # 土浦
    {"no": 43, "id": 47626},   # 熊谷
    {"no": 43, "id": 47641},   # 秩父
    {"no": 44, "id": 47662},   # 東京
    {"no": 45, "id": 47648},   # 横浜
    {"no": 45, "id": 47672},   # 小田原
    {"no": 45, "id": 47674},   # 三浦
    {"no": 45, "id": 47682},   # 海老名
    {"no": 46, "id": 47670}    # 銚子
]
 
# データ取得関数
def time2df(args):
    time, no, sid = args
    url = (
        f"https://www.data.jma.go.jp/stats/etrn/view"
        f"/hourly_s1.php?prec_no={no}&block_no={sid}"
        f"&year={time.year}&month={time.month}&day={time.day}&view=p1"
    )
    try:
        df = pd.read_html(url)[0]
    except Exception:
        return None  # 失敗時スキップ
    df.index = [
        dt.datetime(time.year, time.month, time.day) + dt.timedelta(hours=ii)
        for ii in range(1, 25)
    ]
    # 観測所情報を列に追加
    df["station_no"] = no
    df["station_id"] = sid
    return df
 
# 実行対象（全日付 × 全地点）のリストを作成
date_list = pd.date_range(start="2005-10-01", end="2025-09-30", freq="1D")
args_list = [(time, s["no"], s["id"]) for s in stations for time in date_list]
 
# 並行処理で一括取得
with ThreadPoolExecutor(max_workers=30) as executor:
    df_list = list(tqdm(executor.map(time2df, args_list), total=len(args_list)))
 
# None を除去して結合
df_all = pd.concat([df for df in df_list if df is not None], axis=0)
 
# カラム名を統一
df_all.columns = [
    "時", "現地気圧(hPa)", "海面気圧(hPa)",
    "降水量(mm/h)", "気温(℃)", "露点温度(℃)",
    "蒸気圧(hPa)", "湿度(%)", "風速(m/s)",
    "風向(°)", "日照時間(h)", "全天日射量(MJ/㎡)",
    "降雪(cm/h)", "積雪(cm)", "天気", "雲量",
    "視程(km)", "station_no", "station_id"
]
 
# "時" は index から復元できるので削除
df_all = df_all.drop("時", axis=1)
 
# ---- 降雪データのみ抽出 ----
df_all["降雪(cm/h)"] = pd.to_numeric(df_all["降雪(cm/h)"], errors="coerce")
df_snow = df_all[df_all["降雪(cm/h)"] > 0]
 
# CSV保存
df_snow.to_csv("multi_station_snow.csv")
