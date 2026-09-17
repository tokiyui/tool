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
            subprocess.run(cmd + ["--break-system-packages"], check=True)
        elif result.returncode != 0:
            raise RuntimeError(result.stderr)
        return importlib.import_module(module_name)


_ensure_package("skyfield")
from skyfield.api import load, wgs84, Star
from skyfield import almanac

try:
    skyfield_data = _ensure_package("skyfield_data", "skyfield-data")
    _HAS_SKYFIELD_DATA = True
except Exception:
    _HAS_SKYFIELD_DATA = False
    print("情報: skyfield-data が使えないため、初回実行時に de421.bsp をダウンロードします(要ネット接続)。")

try:
    _ensure_package("japanize_matplotlib")
except Exception:
    print("警告: 日本語フォントの自動設定(japanize-matplotlib)に失敗しました。文字化けする場合があります。")

plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# ユーザー設定
# ============================================================
OBS_DATE = "2026-09-16"                       # 観測日 (日本時間, "YYYY-MM-DD")
LAT, LON, HEIGHT = 35.6812, 139.7671, 20        # 緯度, 経度, 標高[m] (東京駅付近)
LOCATION_NAME = "東京"
WINDOW_HALF_WIDTH_DEG = 45                      # 方位角の表示幅(中心 ± この角度)
ALT_MIN, ALT_MAX = 0, 60                        # 表示する高度の範囲(地平線より下は表示しない)
STAR_CATALOG_MAG_LIMIT = 6.0
STAR_MAG_LIMIT = 4.0
STAR_LABEL_MAG_LIMIT = 1.5
MOON_ICON_RADIUS = 2.0                          # 月アイコンの見た目の大きさ(度)

try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()

STAR_CSV = os.path.join(SCRIPT_DIR, "stars_mag6.csv")
LINES_CSV = os.path.join(SCRIPT_DIR, "constellation_lines.csv")
SAVE_PATH_EAST = os.path.join(SCRIPT_DIR, "twilight_east.png")
SAVE_PATH_WEST = os.path.join(SCRIPT_DIR, "twilight_west.png")

HYG_URL = "https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv"
CONSTELLATION_URL = "https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/modern_st/index.json"
# ============================================================

PLANETS = {
    "水星":   {"name": "mercury",            "color": "#b5b5b5", "size": 60},
    "金星":   {"name": "venus",              "color": "#f2d98d", "size": 110},
    "火星":   {"name": "mars",               "color": "#e2734a", "size": 75},
    "木星":   {"name": "jupiter barycenter", "color": "#e0b784", "size": 110},
    "土星":   {"name": "saturn barycenter",  "color": "#d8c98a", "size": 90},
}

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
# 2. 薄明時刻の計算
# ============================================================
def twilight_times(date_str, eph, topos, tz):
    """指定日(その日の00:00〜翌日00:00, tz基準)について、
    朝の天文薄明開始時刻(夜→天文薄明)と、夕方の天文薄明終了時刻(天文薄明→夜)を返す。
    見つからない場合は None を返す(白夜・極夜等、極端な緯度でまれに発生)。
    """
    d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
    ts = load.timescale()
    t0 = ts.from_datetime(d)
    t1 = ts.from_datetime(d + timedelta(days=1))
    f = almanac.dark_twilight_day(eph, topos)
    times, events = almanac.find_discrete(t0, t1, f)

    morning_begin, evening_end = None, None
    for ti, e in zip(times, events):
        local = ti.astimezone(tz)
        if e == 1 and local.hour < 12 and morning_begin is None:
            morning_begin = ti
        if e == 0 and local.hour >= 12:
            evening_end = ti
    return morning_begin, evening_end


# ============================================================
# 3. 描画のヘルパー
# ============================================================
def position_angle(alt1_deg, az1_deg, alt2_deg, az2_deg):
    """地平座標系での点1から点2への位置角(rad)。
    高度の増加方向を基準(北に相当)、方位角の増加方向(東に相当)へ回転する角度。
    """
    a1, a2 = np.deg2rad(alt1_deg), np.deg2rad(alt2_deg)
    daz = np.deg2rad(az2_deg - az1_deg)
    y = np.cos(a2) * np.sin(daz)
    x = np.cos(a1) * np.sin(a2) - np.sin(a1) * np.cos(a2) * np.cos(daz)
    return np.arctan2(y, x)


def moon_base_shape(k, radius, n=300):
    """輝面比kから月アイコンの明部の輪郭を作る(ローカル座標: 太陽方向=+x基準)。"""
    y = np.linspace(-radius, radius, n)
    x_limb = np.sqrt(np.clip(radius ** 2 - y ** 2, 0, None))
    cosE = 1 - 2 * k
    x_term = cosE * x_limb
    xs = np.concatenate([x_limb, x_term[::-1]])
    ys = np.concatenate([y, y[::-1]])
    return xs, ys


def rotate(xs, ys, angle_rad):
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return xs * c - ys * s, xs * s + ys * c


def draw_moon(ax, x_moon, y_moon, k, rotation_angle, radius=MOON_ICON_RADIUS):
    ax.add_patch(plt.Circle((x_moon, y_moon), radius, color="#20202f", zorder=6))
    xs, ys = moon_base_shape(k, radius)
    xs, ys = rotate(xs, ys, rotation_angle)
    ax.fill(xs + x_moon, ys + y_moon, color="#fdf6d8", zorder=7)
    ax.add_patch(plt.Circle((x_moon, y_moon), radius, fill=False, color="#999", lw=1.0, zorder=8))


def label_offset(dist=9):
    return 0, dist  # マーカーの少し上にラベルを置く(帯状チャートでは単純な上寄せで十分)


COMPASS_JA = {
    0: "北", 22.5: "北北東", 45: "北東", 67.5: "東北東", 90: "東",
    112.5: "東南東", 135: "南東", 157.5: "南南東", 180: "南",
    202.5: "南南西", 225: "南西", 247.5: "西南西", 270: "西",
    292.5: "西北西", 315: "北西", 337.5: "北北西",
}


def draw_strip_chart(ax, eph, ts, t, tokyo, sun, moon, center_az, title,
                      hips, ras, decs, mags, names_ja, edges, hip_to_idx):
    az_lo, az_hi = center_az - WINDOW_HALF_WIDTH_DEG, center_az + WINDOW_HALF_WIDTH_DEG

    ax.set_facecolor("#0b0b22")
    ax.set_xlim(az_lo, az_hi)
    ax.set_ylim(ALT_MIN, ALT_MAX)
    ax.set_aspect("equal")

    # 地平線(下端)を強調
    ax.axhline(0, color="#dfe3ff", lw=2.2, zorder=1)

    # 高度の目盛線
    for a in range(0, ALT_MAX + 1, 10):
        ax.axhline(a, color="gray", alpha=0.25, lw=0.6, zorder=1)
        ax.text(az_lo, a, f"{a}°", color="#aaaacc", fontsize=7, ha="right", va="center")

    # 方位角の目盛線・ラベル(22.5°刻みの主要方位)
    tick = round(az_lo / 22.5) * 22.5
    while tick <= az_hi:
        if az_lo <= tick <= az_hi:
            ax.axvline(tick, color="gray", alpha=0.25, lw=0.6, zorder=1)
            label = COMPASS_JA.get(tick % 360, f"{tick:.0f}°")
            ax.text(tick, -4, label, color="white", fontsize=10,
                    ha="center", va="top", clip_on=False)
        tick += 22.5

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    def in_window(az):
        return az_lo <= az <= az_hi

    def topocentric_altaz(body):
        alt, az, _ = tokyo.at(t).observe(body).apparent().altaz()
        return alt.degrees, az.degrees

    # ---- 星座線 ----
    star_field = Star(ra_hours=ras, dec_degrees=decs)
    s_alt, s_az, _ = tokyo.at(t).observe(star_field).apparent().altaz()
    s_alt_deg, s_az_deg = s_alt.degrees, s_az.degrees
    for hip1, hip2 in edges:
        i1, i2 = hip_to_idx.get(hip1), hip_to_idx.get(hip2)
        if i1 is None or i2 is None:
            continue
        if not (in_window(s_az_deg[i1]) and in_window(s_az_deg[i2])):
            continue
        if s_alt_deg[i1] < ALT_MIN or s_alt_deg[i2] < ALT_MIN:
            continue
        ax.plot([s_az_deg[i1], s_az_deg[i2]], [s_alt_deg[i1], s_alt_deg[i2]],
                color="#4a6fa5", alpha=0.5, lw=0.9, zorder=2)

    # ---- 恒星 ----
    show_mask = mags <= STAR_MAG_LIMIT
    for i in np.where(show_mask)[0]:
        if not in_window(s_az_deg[i]) or s_alt_deg[i] < ALT_MIN:
            continue
        size = float(np.clip((7.0 - mags[i]) ** 2 * 1.1, 2.0, 90.0))
        ax.scatter([s_az_deg[i]], [s_alt_deg[i]], s=size, color="#f5f6ff",
                   edgecolor="none", zorder=3, alpha=0.95)
        if names_ja[i] and mags[i] <= STAR_LABEL_MAG_LIMIT:
            dx, dy = label_offset(7)
            ax.annotate(names_ja[i], (s_az_deg[i], s_alt_deg[i]), textcoords="offset points",
                        xytext=(dx, dy), color="#e3e6ff", fontsize=8, ha="center", va="bottom",
                        path_effects=[pe.withStroke(linewidth=1.8, foreground="#0b0b22")])

    # 太陽はこれらの時刻では常に地平線下(高度-18°)のため描画しない。
    # ただし月の位置角(向き)の計算には太陽の位置が必要なので取得だけしておく。
    sun_alt, sun_az = topocentric_altaz(sun)

    # ---- 惑星 ----
    for jp_name, style in PLANETS.items():
        alt, az = topocentric_altaz(eph[style["name"]])
        if alt > ALT_MIN and in_window(az):
            ax.scatter([az], [alt], s=style["size"], color=style["color"],
                       edgecolor="white", linewidth=0.5, zorder=5)
            ax.annotate(jp_name, (az, alt), textcoords="offset points", xytext=label_offset(13),
                        color="white", fontsize=9, ha="center", va="bottom",
                        path_effects=[pe.withStroke(linewidth=2, foreground="#0b0b22")])

    # ---- 月 ----
    moon_alt, moon_az = topocentric_altaz(moon)
    if moon_alt > ALT_MIN and in_window(moon_az):
        geo_sun = eph["earth"].at(t).observe(sun).apparent()
        geo_moon = eph["earth"].at(t).observe(moon).apparent()
        elongation_deg = geo_sun.separation_from(geo_moon).degrees
        k = (1 - np.cos(np.deg2rad(elongation_deg))) / 2

        pa = position_angle(moon_alt, moon_az, sun_alt, sun_az)
        rotation_angle = np.pi / 2 - pa  # このチャートは高度=上, 方位角=右 なので単純な回転で良い

        draw_moon(ax, moon_az, moon_alt, k, rotation_angle)
        ax.annotate("月", (moon_az, moon_alt), textcoords="offset points",
                    xytext=(0, MOON_ICON_RADIUS + 8), color="white", fontsize=10,
                    ha="center", va="bottom",
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="#0b0b22")])

    ax.set_title(title, color="white", fontsize=13, pad=10)


# ============================================================
# 4. メイン処理
# ============================================================
def main():
    if not (os.path.exists(STAR_CSV) and os.path.exists(LINES_CSV)):
        _build_data_files()

    if _HAS_SKYFIELD_DATA:
        bsp_path = os.path.join(skyfield_data.get_skyfield_data_path(), "de421.bsp")
    else:
        bsp_path = "de421.bsp"
    eph = load(bsp_path)
    ts = load.timescale()

    earth = eph["earth"]
    sun = eph["sun"]
    moon = eph["moon"]
    topos = wgs84.latlon(LAT, LON, elevation_m=HEIGHT)
    tokyo = earth + topos

    jst = timezone(timedelta(hours=9))
    morning_begin, evening_end = twilight_times(OBS_DATE, eph, topos, jst)

    if morning_begin is None or evening_end is None:
        raise RuntimeError(
            "この日付・地点では天文薄明の開始/終了時刻が見つかりませんでした"
            "(高緯度地方で白夜・極夜に近い時期の可能性があります)。"
        )

    hips, ras, decs, mags, names_ja = load_star_catalog(STAR_CSV)
    edges = load_constellation_lines(LINES_CSV)
    hip_to_idx = {h: i for i, h in enumerate(hips)}

    mb_local = morning_begin.astimezone(jst)
    ee_local = evening_end.astimezone(jst)

    # ---- 東の空(朝, 天文薄明開始) ----
    fig1, ax1 = plt.subplots(figsize=(8, 7))
    fig1.patch.set_facecolor("#0b0b22")
    draw_strip_chart(
        ax1, eph, ts, morning_begin, tokyo, sun, moon, center_az=90,
        title=f"天文薄明開始 {mb_local.strftime('%Y-%m-%d %H:%M')} @{LOCATION_NAME}",
        hips=hips, ras=ras, decs=decs, mags=mags, names_ja=names_ja,
        edges=edges, hip_to_idx=hip_to_idx,
    )
    plt.tight_layout()
    plt.savefig(SAVE_PATH_EAST, dpi=150, facecolor=fig1.get_facecolor())
    plt.show()

    # ---- 西の空(夕, 天文薄明終了) ----
    fig2, ax2 = plt.subplots(figsize=(8, 7))
    fig2.patch.set_facecolor("#0b0b22")
    draw_strip_chart(
        ax2, eph, ts, evening_end, tokyo, sun, moon, center_az=270,
        title=f"天文薄明終了 {ee_local.strftime('%Y-%m-%d %H:%M')} @{LOCATION_NAME}",
        hips=hips, ras=ras, decs=decs, mags=mags, names_ja=names_ja,
        edges=edges, hip_to_idx=hip_to_idx,
    )
    plt.tight_layout()
    plt.savefig(SAVE_PATH_WEST, dpi=150, facecolor=fig2.get_facecolor())
    plt.show()

main()
