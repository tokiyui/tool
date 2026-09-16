import os
import sys
import csv
import json
import subprocess
import importlib
import urllib.request
 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from datetime import datetime, timezone, timedelta
 
import warnings
warnings.filterwarnings("ignore")
 
 
# ============================================================
# 0. 必要なライブラリが無ければ自動インストール(Colab想定)
# ============================================================
def _ensure_package(module_name, pip_name=None):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        pip_name = pip_name or module_name
        print(f"'{pip_name}' が見つからないため pip でインストールします...")
        cmd = [sys.executable, "-m", "pip", "install", "-q", pip_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and "externally-managed-environment" in (result.stderr or ""):
            # Debian/Ubuntu系の一部環境向けフォールバック(Colabでは通常不要)
            subprocess.run(cmd + ["--break-system-packages"], check=True)
        elif result.returncode != 0:
            raise RuntimeError(result.stderr)
        return importlib.import_module(module_name)
 
 
_ensure_package("skyfield")
from skyfield.api import load, wgs84, Star
 
try:
    skyfield_data = _ensure_package("skyfield_data", "skyfield-data")
    _HAS_SKYFIELD_DATA = True
except Exception:
    _HAS_SKYFIELD_DATA = False
    print("情報: skyfield-data が使えないため、初回実行時に de421.bsp をダウンロードします(要ネット接続)。")
 
try:
    _ensure_package("japanize_matplotlib")  # 日本語フォントを自動設定してくれる
except Exception:
    print("警告: 日本語フォントの自動設定(japanize-matplotlib)に失敗しました。文字化けする場合があります。")
 
plt.rcParams["axes.unicode_minus"] = False
 
 
# ============================================================
# ユーザー設定
# ============================================================
OBS_DATETIME_JST = "1995-12-02 21:00:00"   # 観測日時 (日本時間, "YYYY-MM-DD HH:MM:SS")
LAT, LON, HEIGHT = 35.6812, 139.7671, 20     # 緯度, 経度, 標高[m] (東京駅付近)
LOCATION_NAME = "東京"                        # タイトルに表示する地点名
SHOW_SUN = True                               # 太陽も表示するか(薄明中のみ意味あり)
SHOW_CONSTELLATION_LINES = True               # 星座線を表示するか
STAR_CATALOG_MAG_LIMIT = 6.0                  # データとして保持しておく限界等級
STAR_MAG_LIMIT = 5.0                          # 実際に表示する恒星の限界等級
STAR_LABEL_MAG_LIMIT = 1.5                    # 名称を表示する恒星の限界等級(1等星)
MOON_ICON_RADIUS = 3.0                        # 月アイコンの見た目の大きさ(度)
 
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()  # Jupyter/Colab等、__file__が定義されない環境向けのフォールバック
 
STAR_CSV = os.path.join(SCRIPT_DIR, "stars_mag6.csv")
LINES_CSV = os.path.join(SCRIPT_DIR, "constellation_lines.csv")
SAVE_PATH = os.path.join(SCRIPT_DIR, "tokyo_sky_map.png")
 
# データ取得元(いずれもオープンデータ, GitHub上のraw)
HYG_URL = "https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv"
CONSTELLATION_URL = "https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/modern_st/index.json"
# ============================================================
 
# 表示する惑星と見た目の設定 (skyfield/de421 上の名前)
PLANETS = {
    "水星":   {"name": "mercury",            "color": "#b5b5b5", "size": 45},
    "金星":   {"name": "venus",              "color": "#f2d98d", "size": 90},
    "火星":   {"name": "mars",               "color": "#e2734a", "size": 60},
    "木星":   {"name": "jupiter barycenter", "color": "#e0b784", "size": 90},
    "土星":   {"name": "saturn barycenter",  "color": "#d8c98a", "size": 75},
    "天王星": {"name": "uranus barycenter",  "color": "#9fd8e0", "size": 40},
    "海王星": {"name": "neptune barycenter", "color": "#6f8fe0", "size": 40},
}
 
# 英語固有名 -> 日本語カタカナ名(主要な恒星のみ。1等星ラベル表示に使用)
NAME_JA = {
    "Sirius": "シリウス", "Canopus": "カノープス", "Rigil Kentaurus": "リギルケンタウルス",
    "Arcturus": "アークトゥルス", "Vega": "ベガ", "Capella": "カペラ", "Rigel": "リゲル",
    "Procyon": "プロキオン", "Betelgeuse": "ベテルギウス", "Achernar": "アケルナル",
    "Hadar": "ハダル", "Altair": "アルタイル", "Acrux": "アクルックス", "Aldebaran": "アルデバラン",
    "Antares": "アンタレス", "Spica": "スピカ", "Pollux": "ポルックス", "Fomalhaut": "フォーマルハウト",
    "Deneb": "デネブ", "Mimosa": "ミモザ", "Regulus": "レグルス", "Adhara": "アダーラ",
    "Castor": "カストル", "Shaula": "シャウラ", "Gacrux": "ガクルックス", "Bellatrix": "ベラトリックス",
    "Elnath": "エルナト", "Miaplacidus": "ミアプラキドゥス", "Alnilam": "アルニラム",
    "Alnair": "アルナイル", "Alnitak": "アルニタク", "Alioth": "アリオト", "Dubhe": "ドゥーベ",
    "Mirfak": "ミルファク", "Wezen": "ウェズン", "Sargas": "サーガス",
    "Kaus Australis": "カウスアウストラリス", "Avior": "アビオル", "Alkaid": "アルカイド",
    "Menkalinan": "メンカリナン", "Atria": "アトリア", "Alhena": "アルヘナ", "Peacock": "ピーコック",
    "Mirzam": "ミルザム", "Polaris": "北極星", "Alphard": "アルファルド", "Hamal": "ハマル",
    "Diphda": "ディフダ", "Nunki": "ヌンキ", "Mizar": "ミザール", "Kochab": "コカブ",
    "Saiph": "サイフ", "Rasalhague": "ラスアルハゲ", "Algol": "アルゴル", "Almach": "アルマク",
    "Denebola": "デネボラ", "Naos": "ナオス", "Suhail": "スハイル", "Alphecca": "アルフェッカ",
    "Mintaka": "ミンタカ", "Sadr": "サドル", "Eltanin": "エルタニン", "Schedar": "シェダル",
    "Caph": "カフ",
}
 
 
# ============================================================
# 1. 恒星・星座線データの取得(無ければダウンロードして生成)
# ============================================================
def _download(url, dest):
    print(f"ダウンロード中: {url}")
    urllib.request.urlretrieve(url, dest)
 
 
def _build_data_files():
    """HYG Database と Stellarium の星座線データから、必要な分だけを
    stars_mag6.csv / constellation_lines.csv として生成する。"""
    hyg_path = os.path.join(SCRIPT_DIR, "_hygdata_raw.csv")
    const_path = os.path.join(SCRIPT_DIR, "_constellationship_raw.json")
 
    if not os.path.exists(hyg_path):
        _download(HYG_URL, hyg_path)
    if not os.path.exists(const_path):
        _download(CONSTELLATION_URL, const_path)
 
    print("恒星データを処理中...")
    hip_all = {}
    with open(hyg_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            hip = row.get("hip", "")
            if not hip:
                continue
            try:
                ra = float(row["ra"]); dec = float(row["dec"]); mag = float(row["mag"])
            except ValueError:
                continue
            hip_all[int(hip)] = {"ra": ra, "dec": dec, "mag": mag, "proper": row.get("proper", "").strip()}
 
    with open(const_path, encoding="utf-8") as f:
        const_data = json.load(f)
 
    edges = set()
    for con in const_data["constellations"]:
        for path in con.get("lines", []):
            for a, b in zip(path[:-1], path[1:]):
                if a in hip_all and b in hip_all:
                    edges.add((min(a, b), max(a, b)))
 
    line_hips = {h for pair in edges for h in pair}
    out_hips = {h for h, d in hip_all.items() if d["mag"] <= STAR_CATALOG_MAG_LIMIT} | line_hips
 
    with open(STAR_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hip", "ra_h", "dec_deg", "mag", "name_ja"])
        for hip in sorted(out_hips):
            d = hip_all[hip]
            w.writerow([hip, f'{d["ra"]:.6f}', f'{d["dec"]:.6f}', f'{d["mag"]:.2f}',
                        NAME_JA.get(d["proper"], "")])
 
    with open(LINES_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hip1", "hip2"])
        for a, b in sorted(edges):
            w.writerow([a, b])
 
    # 元データ(大きいファイル)は不要なので削除
    for p in (hyg_path, const_path):
        try:
            os.remove(p)
        except OSError:
            pass
 
    print(f"生成しました: {STAR_CSV} ({len(out_hips)}星), {LINES_CSV} ({len(edges)}本)")
 
 
def load_star_catalog(path):
    hips, ras, decs, mags, names = [], [], [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            hips.append(int(row["hip"]))
            ras.append(float(row["ra_h"]))
            decs.append(float(row["dec_deg"]))
            mags.append(float(row["mag"]))
            names.append(row["name_ja"])
    return (np.array(hips), np.array(ras), np.array(decs), np.array(mags), names)
 
 
def load_constellation_lines(path):
    edges = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            edges.append((int(row["hip1"]), int(row["hip2"])))
    return edges
 
 
# ============================================================
# 2. 座標変換・描画のヘルパー
# ============================================================
def altaz_to_xy(alt_deg, az_deg):
    """高度・方位角(度)を、天頂中心の天球図用の(x, y)平面座標に変換する。
    r = 90 - 高度 (天頂=0, 地平線=90)
    画面は「見上げた空」の向き: 北=上, 東=左, 南=下, 西=右
      screen_angle = 90° + 方位角  (標準の数学角度: 反時計回りが正)
    """
    r = 90.0 - alt_deg
    ang = np.deg2rad(90.0 + az_deg)
    return r * np.cos(ang), r * np.sin(ang)
 
 
def position_angle(alt1_deg, az1_deg, alt2_deg, az2_deg):
    """地平座標系での点1から点2への位置角を返す(rad)。
    「高度の増加方向」を基準(北に相当)とし、「方位角の増加方向」(東に相当)へ
    回転する角度として定義する(天文学でのRA/Dec位置角の定義と同じ考え方)。
    """
    a1, a2 = np.deg2rad(alt1_deg), np.deg2rad(alt2_deg)
    daz = np.deg2rad(az2_deg - az1_deg)
    y = np.cos(a2) * np.sin(daz)
    x = np.cos(a1) * np.sin(a2) - np.sin(a1) * np.cos(a2) * np.cos(daz)
    return np.arctan2(y, x)
 
 
def moon_base_shape(k, radius, n=300):
    """輝面比kから、月アイコンの明部の輪郭を作る。
    このローカル座標系では「太陽の方向 = +x(右)」を常に基準とする。
    (実際の向きは呼び出し側で回転させて画面上の正しい方位に合わせる)
    """
    y = np.linspace(-radius, radius, n)
    x_limb = np.sqrt(np.clip(radius ** 2 - y ** 2, 0, None))
    cosE = 1 - 2 * k          # 離角のコサインに相当 (k=0→1, k=1→-1)
    x_term = cosE * x_limb    # 明暗境界線(ターミネーター)の形
    xs = np.concatenate([x_limb, x_term[::-1]])
    ys = np.concatenate([y, y[::-1]])
    return xs, ys
 
 
def label_offset(x, y, dist=8):
    """天体からラベルへのオフセット(points単位)を返す。
    中心からその天体へ向かう方向に対して垂直(接線)方向にずらすことで、
    同じ方位線上にある方位ラベルなどと重ならないようにしつつ、天体の近くに置く。
    """
    ang = np.arctan2(y, x) + np.pi / 2  # 接線方向(反時計回り側)
    return dist * np.cos(ang), dist * np.sin(ang)
 
 
def label_align(dx, dy):
    """オフセット方向(dx, dy)から、マーカーと重ならない ha/va を決める。"""
    ha = "left" if dx >= 0 else "right"
    va = "bottom" if dy >= 0 else "top"
    return ha, va
 
 
def rotate(xs, ys, angle_rad):
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return xs * c - ys * s, xs * s + ys * c
 
 
def draw_moon_on_sky(ax, x_moon, y_moon, k, rotation_angle, radius=MOON_ICON_RADIUS):
    """天球図上の実際の位置(x_moon, y_moon)に、正しい傾きで月を描画する"""
    ax.add_patch(plt.Circle((x_moon, y_moon), radius, color="#20202f", zorder=6))
    xs, ys = moon_base_shape(k, radius)
    xs, ys = rotate(xs, ys, rotation_angle)
    ax.fill(xs + x_moon, ys + y_moon, color="#fdf6d8", zorder=7)
    ax.add_patch(plt.Circle((x_moon, y_moon), radius, fill=False, color="#999", lw=1.0, zorder=8))
 
 
# ============================================================
# 3. メイン処理
# ============================================================
def main():
    if not (os.path.exists(STAR_CSV) and os.path.exists(LINES_CSV)):
        _build_data_files()
 
    # ---- Skyfield の準備 ----
    if _HAS_SKYFIELD_DATA:
        bsp_path = os.path.join(skyfield_data.get_skyfield_data_path(), "de421.bsp")
    else:
        bsp_path = "de421.bsp"  # skyfieldが自動でダウンロード(初回のみ、要インターネット接続)
    eph = load(bsp_path)
    ts = load.timescale()
 
    earth = eph["earth"]
    sun = eph["sun"]
    moon = eph["moon"]
 
    tokyo = earth + wgs84.latlon(LAT, LON, elevation_m=HEIGHT)
 
    jst = timezone(timedelta(hours=9))
    dt_jst = datetime.strptime(OBS_DATETIME_JST, "%Y-%m-%d %H:%M:%S").replace(tzinfo=jst)
    t = ts.from_datetime(dt_jst)
 
    def topocentric_altaz(body):
        alt, az, _ = tokyo.at(t).observe(body).apparent().altaz()
        return alt.degrees, az.degrees
 
    sun_alt, sun_az = topocentric_altaz(sun)
    moon_alt, moon_az = topocentric_altaz(moon)
 
    # 輝面比(地心座標での太陽・月の離角から算出。観測地による視差は無視できる精度)
    geo_sun = earth.at(t).observe(sun).apparent()
    geo_moon = earth.at(t).observe(moon).apparent()
    elongation_deg = geo_sun.separation_from(geo_moon).degrees
    k = (1 - np.cos(np.deg2rad(elongation_deg))) / 2
 
    # ---- 図の準備 ----
    fig, ax = plt.subplots(figsize=(9, 9))
    fig.patch.set_facecolor("#0b0b22")
    ax.set_facecolor("#0b0b22")
    ax.set_xlim(-108, 108)
    ax.set_ylim(-108, 108)
    ax.set_aspect("equal")
    ax.axis("off")
 
    # 地平線(高度0°の円)のみを目立つ線で描画(他の高度線は無し)
    ax.add_patch(plt.Circle((0, 0), 90, fill=False, color="#dfe3ff", alpha=0.9, lw=2.2, zorder=1))
 
    # 方位線(日本語のみ)
    for az_label, az_deg in [("北", 0), ("東", 90), ("南", 180), ("西", 270)]:
        x0, y0 = altaz_to_xy(90, az_deg)   # 天頂(中心)
        x1, y1 = altaz_to_xy(0, az_deg)    # 地平線
        ax.plot([x0, x1], [y0, y1], color="gray", alpha=0.4, lw=0.8, zorder=1)
        xl, yl = altaz_to_xy(-9, az_deg)
        ax.text(xl, yl, az_label, color="white", fontsize=14, ha="center", va="center", zorder=2,
                path_effects=[pe.withStroke(linewidth=3, foreground="#0b0b22")])
 
    # ---- 恒星の位置を一括計算(ベクトル化して高速化) ----
    hips, ras, decs, mags, names_ja = load_star_catalog(STAR_CSV)
    show_mask = mags <= STAR_MAG_LIMIT
    star_field = Star(ra_hours=ras, dec_degrees=decs)
    s_alt, s_az, _ = tokyo.at(t).observe(star_field).apparent().altaz()
    s_alt_deg, s_az_deg = s_alt.degrees, s_az.degrees
    hip_to_idx = {h: i for i, h in enumerate(hips)}
 
    # ---- 星座線(恒星より先に描いて、点の下に重なるようにする) ----
    if SHOW_CONSTELLATION_LINES:
        edges = load_constellation_lines(LINES_CSV)
        for hip1, hip2 in edges:
            i1, i2 = hip_to_idx.get(hip1), hip_to_idx.get(hip2)
            if i1 is None or i2 is None:
                continue
            if s_alt_deg[i1] <= 0 or s_alt_deg[i2] <= 0:
                continue  # 両端が地平線より上にある場合のみ描画
            x1, y1 = altaz_to_xy(s_alt_deg[i1], s_az_deg[i1])
            x2, y2 = altaz_to_xy(s_alt_deg[i2], s_az_deg[i2])
            ax.plot([x1, x2], [y1, y2], color="#4a6fa5", alpha=0.5, lw=0.9, zorder=2)
 
    # ---- 恒星本体 ----
    for i in np.where(show_mask & (s_alt_deg > 0))[0]:
        xst, yst = altaz_to_xy(s_alt_deg[i], s_az_deg[i])
        size = float(np.clip((7.0 - mags[i]) ** 2 * 1.1, 2.0, 90.0))
        ax.scatter([xst], [yst], s=size, color="#f5f6ff", edgecolor="none", zorder=3, alpha=0.95)
        if names_ja[i] and mags[i] <= STAR_LABEL_MAG_LIMIT:
            dx, dy = label_offset(xst, yst, dist=7)
            ha, va = label_align(dx, dy)
            ax.annotate(names_ja[i], (xst, yst), textcoords="offset points", xytext=(dx, dy),
                        color="#e3e6ff", fontsize=8, ha=ha, va=va,
                        path_effects=[pe.withStroke(linewidth=1.8, foreground="#0b0b22")])
 
    # ---- 太陽 ----
    if SHOW_SUN and sun_alt > -18:  # 天文薄明より明るい間は表示
        xs_, ys_ = altaz_to_xy(sun_alt, sun_az)
        ax.scatter([xs_], [ys_], s=320, color="#ffe066", edgecolor="#ffb300", zorder=5)
        dx, dy = label_offset(xs_, ys_, dist=7)
        ha, va = label_align(dx, dy)
        ax.annotate("太陽", (xs_, ys_), textcoords="offset points", xytext=(dx, dy),
                    color="white", fontsize=11, ha=ha, va=va,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="#0b0b22")])
 
    # ---- 惑星 ----
    for jp_name, style in PLANETS.items():
        alt, az = topocentric_altaz(eph[style["name"]])
        if alt > 0:  # 地平線より上のみ表示
            xp, yp = altaz_to_xy(alt, az)
            ax.scatter([xp], [yp], s=style["size"], color=style["color"],
                       edgecolor="white", linewidth=0.5, zorder=5)
            dx, dy = label_offset(xp, yp, dist=7)
            ha, va = label_align(dx, dy)
            ax.annotate(jp_name, (xp, yp), textcoords="offset points", xytext=(dx, dy),
                        color="white", fontsize=9, ha=ha, va=va,
                        path_effects=[pe.withStroke(linewidth=2, foreground="#0b0b22")])
 
    # ---- 月(実際の傾きを反映して天球図上に直接描画) ----
    moon_visible = moon_alt > -2
    if moon_visible:
        x_moon, y_moon = altaz_to_xy(moon_alt, moon_az)
 
        # 月から見た太陽の位置角(地平座標系: 天頂方向を基準に方位角増加方向へ回転)
        pa = position_angle(moon_alt, moon_az, sun_alt, sun_az)
        # 月から見た「天頂方向」の画面角度
        theta_zenith = np.arctan2(-y_moon, -x_moon)
        # 画面上での「太陽の方向」の角度 = 明部(太陽側)を向けるべき回転角
        rotation_angle = theta_zenith - pa
 
        draw_moon_on_sky(ax, x_moon, y_moon, k, rotation_angle)
        dx, dy = label_offset(x_moon, y_moon, dist=MOON_ICON_RADIUS + 8)
        ha, va = label_align(dx, dy)
        ax.annotate("月", (x_moon, y_moon), textcoords="offset points", xytext=(dx, dy),
                    color="white", fontsize=10, ha=ha, va=va,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="#0b0b22")])
 
    title_dt = dt_jst.strftime("%Y-%m-%d %H:%M")
    ax.set_title(f"{title_dt} @{LOCATION_NAME}", color="white", fontsize=16, pad=10)
 
    plt.tight_layout()
    plt.savefig(SAVE_PATH, dpi=150, facecolor=fig.get_facecolor())
    plt.show()

main()
