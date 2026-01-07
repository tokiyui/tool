import math
import csv
from datetime import datetime, timezone, timedelta

import numpy as np
from skyfield.api import load, wgs84
from skyfield import almanac

# =========================
# 定数（Cコード準拠）
# =========================
LONGITUDE = 139.7
LATITUDE  = 35.7
TZ = timezone(timedelta(hours=9))

DATES_Y = [2026,2026,2027]
DATES_M = [1,12,12]
DATES_D = [1,31,31]

# =========================
# Skyfield 初期化
# =========================
ts = load.timescale()
eph = load('de421.bsp')

earth = eph['earth']
sun   = eph['sun']
moon  = eph['moon']
mercury = eph['mercury']
venus   = eph['venus']
mars    = eph['mars']
jupiter = eph['jupiter barycenter']
saturn  = eph['saturn barycenter']

# ★ 重要：observerを分離
topos = wgs84.latlon(LATITUDE, LONGITUDE)   # 日出没用
observer = earth + topos                    # 天体観測用

# =========================
# 補助関数
# =========================
def hms_deg(alpha_deg):
    h = int(alpha_deg // 15)
    m = (alpha_deg - h * 15) * 4
    return h, m

def dms_deg(delta_deg):
    d = int(delta_deg)
    m = int(abs(delta_deg - d) * 60)
    return d, m

def fmt_ra(ra):
    h, m = hms_deg(ra)
    return f"{h:2d}h{m:4.1f}m"

def fmt_dec(dec):
    d, dm = dms_deg(dec)
    return f"{d:+3d}°{dm:2d}’"

def fmt_time(t):
    if t is None:
        return "--:--"
    return f"{t.hour:02d}:{t.minute:02d}"

# =========================
# 出力
# =========================
with open("output.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow([
        "西暦","月","日",
        "太陽黄経","太陽距離",
        "月黄経","月黄緯","月距離",
        "位相角",
        "太陽赤経","太陽赤緯",
        "月赤経","月赤緯",
        "月齢",
        "日出","日没","月出","月没",
        "水星黄経","金星黄経","火星黄経","木星黄経","土星黄経",
        "水星赤経","水星赤緯",
        "金星赤経","金星赤緯",
        "火星赤経","火星赤緯",
        "木星赤経","木星赤緯",
        "土星赤経","土星赤緯"
    ])

    for y, m, d in zip(DATES_Y, DATES_M, DATES_D):
        dt = datetime(y, m, d, 9, 0, tzinfo=TZ)
        t = ts.from_datetime(dt)

        # === 太陽・月 ===
        ast_s = observer.at(t).observe(sun).apparent()
        ast_m = observer.at(t).observe(moon).apparent()

        lon_s, lat_s, dist_s = ast_s.ecliptic_latlon()
        lon_m, lat_m, dist_m = ast_m.ecliptic_latlon()

        ra_s, dec_s, _ = ast_s.radec()
        ra_m, dec_m, _ = ast_m.radec()

        phase = (lon_m.degrees - lon_s.degrees) % 360
        moon_age = phase / 12.1908

        # === 出没（★ topos を使う） ===
        t0 = ts.from_datetime(datetime(y, m, d, 0, tzinfo=TZ))
        t1 = ts.from_datetime(datetime(y, m, d, 23, 59, tzinfo=TZ))

        sr_t, sr_f = almanac.find_discrete(
            t0, t1, almanac.sunrise_sunset(eph, topos)
        )
        mr_t, mr_f = almanac.find_discrete(
            t0, t1, almanac.risings_and_settings(eph, moon, topos)
        )

        sunrise = sunset = moonrise = moonset = None
        for ti, ev in zip(sr_t, sr_f):
            if ev == 1:
                sunrise = ti.utc_datetime().astimezone(TZ)
            else:
                sunset  = ti.utc_datetime().astimezone(TZ)

        for ti, ev in zip(mr_t, mr_f):
            if ev == 1:
                moonrise = ti.utc_datetime().astimezone(TZ)
            else:
                moonset  = ti.utc_datetime().astimezone(TZ)

        # === 惑星 ===
        planets = [mercury, venus, mars, jupiter, saturn]
        lon_p = []
        ra_p = []
        dec_p = []

        for p in planets:
            ast = observer.at(t).observe(p).apparent()
            lon, _, _ = ast.ecliptic_latlon()
            ra, dec, _ = ast.radec()
            lon_p.append(lon.degrees)
            ra_p.append(ra.hours * 15)
            dec_p.append(dec.degrees)

        writer.writerow([
            y, m, d,
            f"{lon_s.degrees:7.3f}", dist_s.au,
            f"{lon_m.degrees:7.3f}", f"{lat_m.degrees:+1.4f}", dist_m.km,
            f"{phase:7.3f}",
            fmt_ra(ra_s.hours * 15), fmt_dec(dec_s.degrees),
            fmt_ra(ra_m.hours * 15), fmt_dec(dec_m.degrees),
            f"{moon_age:4.1f}",
            fmt_time(sunrise), fmt_time(sunset),
            fmt_time(moonrise), fmt_time(moonset),
            *[f"{x:7.3f}" for x in lon_p],
            fmt_ra(ra_p[0]), fmt_dec(dec_p[0]),
            fmt_ra(ra_p[1]), fmt_dec(dec_p[1]),
            fmt_ra(ra_p[2]), fmt_dec(dec_p[2]),
            fmt_ra(ra_p[3]), fmt_dec(dec_p[3]),
            fmt_ra(ra_p[4]), fmt_dec(dec_p[4]),
        ])

