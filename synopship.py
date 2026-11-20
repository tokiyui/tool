# 事前に: pip install xarray netCDF4 pandas requests
import io
import math
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import requests
import xarray as xr

# ============================================================
# 設定
# ============================================================
YEAR, MONTH = 1995, 8
TARGET = pd.Timestamp("1995-08-15 03:00")
WINDOW = pd.Timedelta(minutes=30)   # 00UTCの前後何分まで許容するか

RUN_SYNOP = True                    # 地上観測(気象通報の地点, NOAA ISD)
RUN_SHIP = True                     # 船舶(ICOADS)

# --- SYNOP ---
POS_WARN_KM = 50                    # ISD観測所の位置が一覧とこれ以上ずれたら「要確認」
MAX_WORKERS = 8

# --- 船舶 ---
LAT_MIN, LAT_MAX = 15, 55           # 北緯(南緯は負)
LON_MIN, LON_MAX = 115, 165         # 東経0〜360で指定
SHIP_PT = {5}                       # 船舶のプラットフォーム種別(PT)。実データでPT=5が呼出符号+雲量ありで船と判断
LOCAL_FILE = None                   # 手動で落としたICOADSのNetCDFを使うなら例: "ICOADS_R3.0.0_1993-08.nc"
SLP_MIN, SLP_MAX = 870, 1090        # 海面気圧の妥当範囲(hPa)。外れた値は欠測扱い

# --- 出力 ---
OUT_CSV = "weather_19930806_00utc.csv"            # 風向・風力・天気・気圧・気温(地上+船舶)
DETAIL_CSV = "weather_19930806_00utc_detail.csv"  # 確認用
REPORT_CSV = "weather_19930806_00utc_report.csv"  # 取得できなかった地上観測地点

# ============================================================
# 気象通報の地点一覧(現在の放送地点)
# 出典: ww5.et.tiki.ne.jp/~snowdolphin/weatherdata/station-list.html
# (番号, 副通報, WMO番号, 地点名, 北緯度, 北緯分, 東経度, 東経分)
# ============================================================
STATIONS = [
    ("01", "", "47918", "石垣島", 24, 19.9, 124, 9.8),
    ("02", "", "47936", "那覇", 26, 12.2, 127, 41.3),
    ("03", "", "47945", "南大東島", 25, 49.7, 131, 13.5),
    ("04", "", "47909", "名瀬", 28, 22.6, 129, 29.9),
    ("05", "", "47827", "鹿児島", 31, 33.1, 130, 33.1),
    ("06", "", "47843", "福江", 32, 41.6, 128, 49.5),
    ("07", "", "47800", "厳原", 34, 11.7, 129, 17.6),
    ("08", "", "47898", "清水(足摺岬)", 32, 43.1, 133, 0.7),
    ("09", "", "47899", "室戸岬", 33, 14.9, 134, 10.8),
    ("10", "", "47887", "松山", 33, 50.4, 132, 46.8),
    ("11", "", "47755", "浜田", 34, 53.6, 132, 4.4),
    ("12", "", "47740", "西郷", 36, 12.1, 133, 20.2),
    ("13", "", "47772", "大阪", 34, 40.7, 135, 31.3),
    ("14", "", "47778", "潮岬", 33, 26.9, 135, 45.8),
    ("15", "", "47678", "八丈島", 33, 6.1, 139, 47.3),
    ("16", "", "47675", "大島", 34, 44.8, 139, 21.9),
    ("17", "", "47655", "御前崎", 34, 36.1, 138, 12.9),
    ("18", "", "47648", "銚子", 35, 44.2, 140, 51.6),
    ("19", "", "47624", "前橋", 36, 24.1, 139, 3.8),
    ("20", "", "47598", "小名浜", 36, 56.6, 140, 54.4),
    ("21", "", "47600", "輪島", 37, 23.4, 136, 53.9),
    ("22", "", "47602", "相川", 38, 1.5, 138, 14.5),
    ("23", "", "47590", "仙台", 38, 15.5, 140, 54.0),
    ("24", "", "47585", "宮古", 39, 38.7, 141, 58.1),
    ("25", "", "47582", "秋田", 39, 42.9, 140, 6.2),
    ("26", "", "47430", "函館", 41, 48.8, 140, 45.4),
    ("27", "", "47426", "浦河", 42, 9.5, 142, 46.8),
    ("28", "", "47420", "根室", 43, 19.7, 145, 35.4),
    ("29", "", "47401", "稚内", 45, 24.8, 141, 41.0),
    ("30", "", "32098", "ポロナイスク", 49, 13, 143, 6),
    ("30", "*", "32061", "アレクサンドロフスク", 50, 54, 142, 10),
    ("31", "", "32215", "セベロクリリスク", 50, 41, 156, 8),
    ("31", "*", "32594", "オゼルナヤ", 51, 29, 156, 29),
    ("33", "", "31735", "ハバロフスク", 48, 31, 135, 10),
    ("34", "", "31959", "ルドナヤプリスタニ", 44, 22, 135, 51),
    ("35", "", "31977", "ウラジオストク", 43, 16, 132, 3),
    ("36", "", "47108", "ソウル", 37, 33, 126, 48),
    ("36", "*", "47112", "仁川", 37, 29, 126, 38),
    ("37", "", "47115", "鬱陵島", 37, 29, 130, 54),
    ("37", "*", "47138", "浦項", 36, 2, 129, 23),
    ("38", "", "47159", "釜山", 35, 6, 129, 2),
    ("39", "", "47165", "木浦", 34, 47, 126, 23),
    ("40", "", "47184", "済州島", 33, 31, 126, 32),
    ("41", "", "58968", "台北", 25, 2, 121, 31),
    ("42", "", "59559", "恒春", 22, 0, 120, 45),
    ("42", "*", "59158", "台中", 24, 9, 120, 41),
    ("43", "", "54161", "長春", 43, 54, 125, 13),
    ("44", "", "54511", "北京", 39, 56, 116, 17),
    ("45", "", "54662", "大連", 38, 54, 121, 38),
    ("46", "", "54857", "青島", 36, 4, 120, 20),
    ("47", "", "58362", "上海", 31, 24, 121, 28),
    ("48", "", "57494", "武漢", 30, 37, 114, 8),
    ("49", "", "59134", "アモイ", 24, 29, 118, 5),
    ("50", "", "45007", "香港", 22, 20, 114, 11),
    ("51", "", "98135", "バスコ", 20, 27, 121, 58),
    ("51", "*", "98223", "ラワーグ", 18, 11, 120, 32),
    ("52", "", "98425", "マニラ", 14, 35, 120, 59),
    ("53", "", "47971", "父島", 27, 5.0, 142, 11.0),
    ("54", "", "47991", "南鳥島", 24, 18.0, 153, 58.0),
    ("55", "", "47639", "富士山", 35, 21.6, 138, 43.6),
    ("-", "", "98429", "ニノイアキノ国際空港", 14, 31, 121, 0),
]

# ============================================================
# 共通の変換ロジック
# ============================================================
DIR16 = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
         "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]


def dir16(deg):
    return DIR16[int((deg + 11.25) // 22.5) % 16]


def beaufort(ms):
    """気象庁風力階級(風速m/s -> 0〜12)"""
    for i, lim in enumerate([0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9,
                             17.2, 20.8, 24.5, 28.5, 32.7]):
        if ms < lim:
            return i
    return 12


def ww_to_weather(ww):
    """WMO現在天気符号(ww 00-99) -> 気象通報の天気。雲量で決める符号は None"""
    if ww is None:
        return None
    if ww in (4, 5, 10):
        return "煙霧"
    if ww in (6, 7, 8):
        return "ちり煙霧"
    if ww == 9 or 30 <= ww <= 35:
        return "砂じんあらし"
    if ww == 17:
        return "雷"
    if 36 <= ww <= 39:
        return "地ふぶき"
    if 41 <= ww <= 49:
        return "霧"
    if 50 <= ww <= 57:
        return "霧雨"
    if ww in (58, 59):
        return "雨"
    if ww in (64, 65, 67):
        return "雨強し"
    if 60 <= ww <= 67:
        return "雨"
    if ww in (68, 69):
        return "みぞれ"
    if ww in (74, 75):
        return "雪強し"
    if 70 <= ww <= 78:
        return "雪"
    if ww == 79:
        return "あられ"
    if 80 <= ww <= 82:
        return "にわか雨"
    if ww in (83, 84):
        return "みぞれ"
    if ww in (85, 86):
        return "にわか雪"
    if ww in (87, 88):
        return "あられ"
    if ww in (89, 90):
        return "ひょう"
    if ww == 91:
        return "雨"
    if ww == 92:
        return "雨強し"
    if ww == 93:
        return "雪"
    if ww == 94:
        return "雪強し"
    if ww in (95, 96):
        return "雷"
    if ww in (97, 98, 99):
        return "雷強し"
    return None  # 00-03, 11-16, 18-29, 40 など -> 雲量で判定


def cloud_to_weather(n):
    """全雲量(オクタ 0〜8, 9=空不明) -> 快晴/晴れ/くもり"""
    if n is None:
        return None
    if n in (0, 1):
        return "快晴"
    if 2 <= n <= 6:
        return "晴れ"
    if 7 <= n <= 9:
        return "くもり"
    return None


def num(x):
    return None if x is None or pd.isna(x) else float(x)


# ============================================================
# 地上観測(NOAA ISD)
# ============================================================
HIST_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
S3_BASE = "https://noaa-global-hourly-pds.s3.amazonaws.com"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
BAD_Q = {"2", "3", "6", "7"}  # ISDの品質フラグ: 疑わしい/誤り


def list_s3(prefix):
    keys, token = [], None
    while True:
        params = {"list-type": "2", "prefix": prefix}
        if token:
            params["continuation-token"] = token
        r = requests.get(S3_BASE + "/", params=params, timeout=60)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        keys += [e.text for e in root.findall("s:Contents/s:Key", NS)]
        if root.findtext("s:IsTruncated", namespaces=NS) == "true":
            token = root.findtext("s:NextContinuationToken", namespaces=NS)
        else:
            break
    return keys


def load_history():
    r = requests.get(HIST_URL, timeout=60)
    r.raise_for_status()
    h = pd.read_csv(io.StringIO(r.text), dtype=str)
    h["LAT"] = pd.to_numeric(h["LAT"], errors="coerce")
    h["LON"] = pd.to_numeric(h["LON"], errors="coerce")
    h["ID"] = h["USAF"] + h["WBAN"]
    h["WMO"] = h["USAF"].str[:5]  # 大半の観測所は USAF = WMO番号+1桁
    return h


def km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))


def first_field(s):
    """'値,品質,...' の値と品質を返す"""
    if pd.isna(s):
        return None, None
    parts = str(s).split(",")
    return parts[0], (parts[1] if len(parts) > 1 else None)


def isd_num(s, scale=10.0, missing=9999):
    v, q = first_field(s)
    if v is None or q in BAD_Q:
        return None
    try:
        n = int(v)
    except ValueError:
        return None
    return None if abs(n) == missing else n / scale


def isd_code(s):
    v, q = first_field(s)
    if v is None or q in BAD_Q:
        return None
    try:
        n = int(v)
    except ValueError:
        return None
    return None if n == 99 else n


def isd_wind(s):
    """WND -> (風向16方位 or 静穏/不明, 風力階級, 風向度, 風速m/s)"""
    if pd.isna(s):
        return "不明", None, None, None
    try:
        d, dq, typ, sp, sq = str(s).split(",")[:5]
    except ValueError:
        return "不明", None, None, None
    if sq in BAD_Q or sp == "9999":
        return "不明", None, None, None
    ms = int(sp) / 10.0
    force = beaufort(ms)
    if ms == 0 or typ == "C":
        return "静穏", force, None, ms
    if d == "999" or dq in BAD_Q:
        return "不明", force, None, ms
    return dir16(int(d)), force, int(d), ms


def isd_weather(row):
    """現在天気符号(MW1)があればそれ、無ければ雲量(GF1)から天気と根拠を返す"""
    ww = isd_code(row.get("MW1"))
    w = ww_to_weather(ww)
    if w:
        return w, f"現在天気符号 ww={ww}"
    cov = isd_code(row.get("GF1"))
    w = cloud_to_weather(cov)
    if w:
        return w, f"雲量コード={cov}"
    return "天気不明", "該当データなし"


def synop_fetch(job):
    """同じWMO番号のISD候補を順に試し、最初に00UTCの値が取れたものを採用"""
    meta = job["meta"]
    last_reason = "候補なし"
    for st in job["cands"]:
        key = f"{YEAR}/{st['ID']}.csv"
        info = {"ISD名": st["STATION NAME"], "ファイル": key}
        if meta["_lat"] is not None and pd.notna(st["LAT"]) and pd.notna(st["LON"]):
            d = km(meta["_lat"], meta["_lon"], st["LAT"], st["LON"])
            info["位置ずれ(km)"] = round(d, 1)
            info["位置確認"] = "要確認" if d > POS_WARN_KM else "OK"
        try:
            r = requests.get(f"{S3_BASE}/{key}", timeout=120)
            if r.status_code != 200:
                last_reason = f"HTTP {r.status_code}"
                continue
            if not r.text.lstrip().startswith('"STATION"'):
                last_reason = "CSVではない応答"
                continue
            df = pd.read_csv(io.StringIO(r.text), low_memory=False)
            df["DATE"] = pd.to_datetime(df["DATE"])
            sub = df[(df["DATE"] - TARGET).abs() <= WINDOW].copy()
            if sub.empty:
                last_reason = "00UTC前後の観測なし"
                continue
            sub["diff"] = (sub["DATE"] - TARGET).abs()
            row = sub.sort_values("diff").iloc[0]

            wdir, force, deg, ms = isd_wind(row.get("WND"))
            weather, basis = isd_weather(row)
            lat = meta["_lat"] if meta["_lat"] is not None else num(st["LAT"])
            lon = meta["_lon"] if meta["_lon"] is not None else num(st["LON"])
            return {
                "種別": "地上",
                "番号": meta["番号"] + meta["副通報"],
                "名称": meta["放送名"],
                "コード": meta["WMO"],
                "観測時刻(UTC)": row["DATE"],
                "緯度": None if lat is None else round(lat, 2),
                "経度": None if lon is None else round(lon, 2),
                "風向": wdir, "風力": force, "天気": weather,
                "気圧(hPa)": isd_num(row.get("SLP"), missing=99999),
                "気温(℃)": isd_num(row.get("TMP")),
                # 以下は確認用
                "風向(度)": deg, "風速(m/s)": ms, "天気の根拠": basis,
                "ISD名": info["ISD名"], "ファイル": info["ファイル"],
                "位置ずれ(km)": info.get("位置ずれ(km)"), "位置確認": info.get("位置確認"),
            }, None
        except Exception as e:
            last_reason = f"{type(e).__name__}: {e}"
    return None, {"番号": meta["番号"] + meta["副通報"], "名称": meta["放送名"],
                  "コード": meta["WMO"], "理由": last_reason}


def collect_synop():
    print("=== 地上観測(NOAA ISD)===")
    h = load_history()
    avail = {k.split("/")[-1][:-4] for k in list_s3(f"{YEAR}/") if k.endswith(".csv")}
    h = h[h["ID"].isin(avail)]
    print(f"{YEAR}年のISDファイル: {len(avail)}件 / 履歴と一致: {h['ID'].nunique()}件")

    jobs, report = [], []
    for no, sub, wmo, name, ld, lm, od, om in STATIONS:
        meta = {"番号": no, "副通報": sub, "WMO": wmo, "放送名": name,
                "_lat": None if ld is None else ld + lm / 60,
                "_lon": None if od is None else od + om / 60}
        cands = h[h["WMO"] == wmo].drop_duplicates("ID")
        if cands.empty:
            report.append({"番号": no + sub, "名称": name, "コード": wmo,
                           "理由": "ISDの1993年に該当ファイルなし"})
        else:
            jobs.append({"meta": meta, "cands": [r for _, r in cands.iterrows()]})

    rows = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for f in as_completed([ex.submit(synop_fetch, j) for j in jobs]):
            res, miss = f.result()
            if res:
                rows.append(res)
            else:
                report.append(miss)
    rows.sort(key=lambda r: r["番号"])
    print(f"地上観測: 取得 {len(rows)}件 / 取得できず {len(report)}件")
    return rows, report


# ============================================================
# 船舶(ICOADS)
# ============================================================
BASE = "https://www.ncei.noaa.gov/data/international-comprehensive-ocean-atmosphere/v3/archive"
FNAME = f"ICOADS_R3.0.0_{YEAR}-{MONTH:02d}.nc"   # ローカル保存名(あればダウンロードを省略)
ROOTS = [f"{BASE}/nrt/monthly/"]                 # 1993年8月のNetCDFがあった場所
HEADERS = {"User-Agent": "Mozilla/5.0"}
FILE_EXT = re.compile(r"\.(nc|gz|bz2|zip|tar|tgz|txt|pdf|csv|xml|html?|Z|md5|json)$", re.I)


def list_dir(url):
    """ディレクトリ一覧ページのリンクを (URL, ディレクトリか) で返す"""
    try:
        r = requests.get(url, timeout=180, headers=HEADERS)
    except Exception as e:
        print(f"  取得失敗: {url} ({type(e).__name__}: {e})")
        return None
    if r.status_code != 200:
        print(f"  取得失敗: {url} (HTTP {r.status_code})")
        return None
    out = []
    for h in re.findall(r'href="([^"?#]+)"', r.text):
        if h.startswith(("/", "..", "http")):
            continue
        name = h.rstrip("/")
        is_dir = h.endswith("/") or not FILE_EXT.search(name)
        out.append((urljoin(url, name + ("/" if is_dir else "")), is_dir))
    return out


def discover():
    found = []
    for root in ROOTS:
        items = list_dir(root)
        if items is None:
            continue
        print(f"  走査: {root} ({len(items)}件)")
        for full, is_dir in items:
            name = full.rstrip("/").split("/")[-1]
            if not is_dir and re.search(rf"{YEAR}[-_]?{MONTH:02d}", name) and name.endswith(".nc"):
                found.append(full)
    return found


def get_icoads_file():
    if LOCAL_FILE:
        return LOCAL_FILE
    if os.path.exists(FNAME):
        print("既存のファイルを使用:", FNAME)
        return FNAME
    print("NCEIのディレクトリから対象ファイルを探します...")
    found = discover()
    print("見つかったファイル:", *found, sep="\n   ")
    if not found:
        raise SystemExit("ICOADSのNetCDFが見つかりませんでした。手動で保存して LOCAL_FILE に指定してください。")
    url = sorted(found)[-1]  # 版(c日付)が複数あれば最新
    print("取得:", url)
    r = requests.get(url, stream=True, timeout=300, headers=HEADERS)
    r.raise_for_status()
    with open(FNAME, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    print("保存:", FNAME)
    return FNAME


def ship_wind(d, w):
    """(風向度, 風速m/s) -> (16方位 or 静穏/不明, 風力階級)"""
    w, d = num(w), num(d)
    if w is None:
        return "不明", None
    force = beaufort(w)
    if w == 0 or d == 361:             # IMMA: D=361 は静穏
        return "静穏", force
    if d is None or d < 0 or d > 360:  # 362=変動 など
        return "不明", force
    return dir16(d), force


def ship_weather(ww, n):
    ww, n = num(ww), num(n)
    w = ww_to_weather(None if ww is None else int(ww))
    if w:
        return w, f"現在天気符号 WW={int(ww)}"
    w = cloud_to_weather(None if n is None else int(n))
    if w:
        return w, f"全雲量 N={int(n)}"
    return "天気不明", "該当データなし"


def ship_slp(x):
    """海面気圧(hPa)。欠測や妥当範囲外は None"""
    x = num(x)
    return x if x is not None and SLP_MIN <= x <= SLP_MAX else None


def load_icoads(path):
    """変数: date(YYYYMMDD文字列, 日が99なら不明), HR, lat, lon, PT, ID, D, W, WW, SLP, AT, N"""
    ds = xr.open_dataset(path, decode_times=False, decode_timedelta=False)
    date = np.array([x.decode("ascii", "replace") for x in ds["date"].values])
    want = {(TARGET - pd.Timedelta(days=1)).strftime("%Y%m%d"), TARGET.strftime("%Y%m%d")}
    idx = np.where(np.isin(date, list(want)))[0]
    print(f"ファイル全体: {len(date)}件 / 対象日(前日含む): {len(idx)}件")

    data = {"date": date[idx]}
    for src, dst in {"HR": "HR", "lat": "LAT", "lon": "LON", "PT": "PT", "ID": "ID",
                     "D": "D", "W": "W", "WW": "WW", "SLP": "SLP", "AT": "AT", "N": "N",
                     "DUPS": "DUPS"}.items():
        if src in ds.variables:
            v = ds[src].values[idx]
            if v.dtype.kind == "S":
                v = np.array([x.decode("ascii", "replace") for x in v])
            data[dst] = v
        else:
            data[dst] = np.full(len(idx), np.nan)
    return pd.DataFrame(data)


def collect_ships():
    print("\n=== 船舶(ICOADS)===")
    df = load_icoads(get_icoads_file())
    df = df[df["HR"].between(0, 24)]   # 範囲外のHRで時刻計算がオーバーフローするのを防ぐ
    df["time"] = (pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
                  + pd.to_timedelta(df["HR"], unit="h"))
    df = df.dropna(subset=["time", "LAT", "LON"]).copy()  # 日や時刻が不明のものは除く
    df = df[(df["time"] - TARGET).abs() <= WINDOW]

    df["LON360"] = df["LON"] % 360
    df = df[df["LAT"].between(LAT_MIN, LAT_MAX) & df["LON360"].between(LON_MIN, LON_MAX)]
    print(f"00UTC前後・範囲内の全プラットフォーム: {len(df)}件")
    print("プラットフォーム種別(PT)の内訳:")
    print(df["PT"].value_counts(dropna=False).to_string())

    df = df[df["PT"].isin(SHIP_PT)].drop_duplicates()
    print(f"船舶(PT={sorted(SHIP_PT)})と判定: {len(df)}件 / うち海面気圧あり: {int(df['SLP'].notna().sum())}件")

    rows = []
    for _, r in df.iterrows():
        wdir, force = ship_wind(r["D"], r["W"])
        weather, basis = ship_weather(r["WW"], r["N"])
        lon = r["LON360"] if r["LON360"] <= 180 else r["LON360"] - 360  # 東経+/西経-
        rows.append({
            "種別": "船舶", "番号": "-",
            "名称": str(r["ID"]).strip() or "(不明)", "コード": "-",
            "観測時刻(UTC)": r["time"],
            "緯度": round(float(r["LAT"]), 2), "経度": round(float(lon), 2),
            "風向": wdir, "風力": force, "天気": weather,
            "気圧(hPa)": ship_slp(r["SLP"]),
            "気温(℃)": num(r["AT"]),
            # 以下は確認用
            "風向(度)": num(r["D"]), "風速(m/s)": num(r["W"]), "天気の根拠": basis,
            "PT": r["PT"], "DUPS": r["DUPS"], "WW": num(r["WW"]), "N": num(r["N"]),
            "SLP(生)": num(r["SLP"]),
        })
    rows.sort(key=lambda x: (x["緯度"], x["経度"]))
    print(f"船舶: 取得 {len(rows)}件")
    return rows


# ============================================================
# 出力
# ============================================================
MAIN_COLS = ["種別", "番号", "名称", "コード", "観測時刻(UTC)", "緯度", "経度",
             "風向", "風力", "天気", "気圧(hPa)", "気温(℃)"]


def show_table(df, title):
    """全件を表で画面に出す(欠測は '-')"""
    print(f"\n【{title}】{len(df)}件")
    if df.empty:
        print("  (なし)")
        return
    t = df[MAIN_COLS].copy()
    t["観測時刻(UTC)"] = t["観測時刻(UTC)"].map(lambda x: "-" if pd.isna(x) else x.strftime("%m-%d %H:%M"))
    t["風力"] = t["風力"].map(lambda x: "-" if pd.isna(x) else int(x))
    t["気圧(hPa)"] = t["気圧(hPa)"].map(lambda x: "-" if pd.isna(x) else f"{x:.1f}")
    t["気温(℃)"] = t["気温(℃)"].map(lambda x: "-" if pd.isna(x) else f"{x:.1f}")
    for c in ("緯度", "経度"):
        t[c] = t[c].map(lambda x: "-" if pd.isna(x) else f"{x:.2f}")
    print(t.to_string(index=False))
    print("欠測: "
          f"風向不明 {int((df['風向'] == '不明').sum())}件 / "
          f"風力なし {int(df['風力'].isna().sum())}件 / "
          f"天気不明 {int((df['天気'] == '天気不明').sum())}件 / "
          f"気圧なし {int(df['気圧(hPa)'].isna().sum())}件 / "
          f"気温なし {int(df['気温(℃)'].isna().sum())}件")


def main():
    synop_rows, report, ship_rows = [], [], []
    if RUN_SYNOP:
        synop_rows, report = collect_synop()
    if RUN_SHIP:
        ship_rows = collect_ships()

    synop = pd.DataFrame(synop_rows) if synop_rows else pd.DataFrame(columns=MAIN_COLS)
    ship = pd.DataFrame(ship_rows) if ship_rows else pd.DataFrame(columns=MAIN_COLS)
    allrows = pd.concat([synop, ship], ignore_index=True)

    if not allrows.empty:
        allrows[MAIN_COLS].to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
        allrows.to_csv(DETAIL_CSV, index=False, encoding="utf-8-sig")
    pd.DataFrame(report).to_csv(REPORT_CSV, index=False, encoding="utf-8-sig")

    print(f"\n出力: 地上 {len(synop)}件 + 船舶 {len(ship)}件 = {len(allrows)}件 -> {OUT_CSV}"
          f"(確認用: {DETAIL_CSV} / 取得できなかった地上観測: {REPORT_CSV})")

    show_table(synop, "地上観測(気象通報の地点)")
    if report:
        print("\n取得できなかった地上観測地点:")
        print(pd.DataFrame(report).to_string(index=False))
    if "位置確認" in synop.columns:
        warn = synop[synop["位置確認"] == "要確認"]
        if not warn.empty:
            print("\nISD観測所の位置が一覧とずれている地点(別の観測所の可能性):")
            print(warn[["名称", "コード", "ISD名", "位置ずれ(km)"]].to_string(index=False))
    show_table(ship, "船舶")
    return allrows


if __name__ == "__main__":
    result = main()
