import math
import csv
from datetime import datetime, timedelta, timezone
import numpy as np
from skyfield.api import load, wgs84
from skyfield import almanac

# =====================
# 定数（Cコード準拠）
# =====================
LONGITUDE = 139.7
LATITUDE  = 35.7
TZ = timezone(timedelta(hours=9))

# =====================
# Skyfield 初期化
# =====================
ts = load.timescale()
eph = load("de440s.bsp")
eph2 = load('de421.bsp')
earth = eph["earth"]
sun   = eph["sun"]
moon  = eph["moon"]
mercury = eph2['mercury']
venus   = eph2['venus']
mars    = eph2['mars']
jupiter = eph2['jupiter barycenter']
saturn  = eph2['saturn barycenter']
observer = wgs84.latlon(LATITUDE, LONGITUDE)

# =====================
# 補助関数
# =====================
def ra_dec_hms_dms(ra, dec):
    ra_h = int(ra.hours)
    ra_m = (ra.hours - ra_h) * 60
    dec_d = int(dec.degrees)
    dec_m = abs(dec.degrees - dec_d) * 60
    return ra_h, ra_m, dec_d, dec_m

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

def youbi(dt):
    return ["日","月","火","水","木","金","土"][dt.weekday() + 1 if dt.weekday() < 6 else 0]

def moon_age(t):
    phase = almanac.moon_phase(eph, t).degrees
    return phase / 12.1908

def zodiac(lon):
    signs = ["牡羊座","牡牛座","双子座","蟹座","獅子座","乙女座",
             "天秤座","蠍座","射手座","山羊座","水瓶座","魚座"]
    return signs[int(lon // 30) % 12]

# =====================
# 日出・日没・月出・月没
# =====================
def rise_set(body, date):
    t0 = ts.from_datetime(date.replace(hour=0))
    t1 = ts.from_datetime(date.replace(hour=23, minute=59))
    f = almanac.risings_and_settings(eph, body, observer)
    times, events = almanac.find_discrete(t0, t1, f)

    rise = set_ = None
    for t, e in zip(times, events):
        if e == 1 and rise is None:
            rise = t
        if e == 0 and set_ is None:
            set_ = t

    def fmt(t):
        if t is None:
            return "--:--"
        lt = t.astimezone(TZ)
        return f"{lt.hour}:{lt.minute:02d}"

    return fmt(rise), fmt(set_)

# =====================
# メイン処理
# =====================
def generate(year):
    with open(f"{year}.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "西暦","月","日","曜",
            "太陽黄経","太陽距離",
            "月黄経","月黄緯","月距離",
            "位相角","輝面比",
            "太陽赤経","太陽赤緯",
            "月赤経","月赤緯",
            "月齢",
            "日出","日没","月出","月没",
            "月星座","危険度",
            "水星黄経","金星黄経","火星黄経","木星黄経","土星黄経",
            "水星赤経","水星赤緯",
            "金星赤経","金星赤緯",
            "火星赤経","火星赤緯",
            "木星赤経","木星赤緯",
            "土星赤経","土星赤緯"
        ])

        for month in range(1, 13):
            for day in range(1, 32):
                try:
                    dt = datetime(year, month, day, tzinfo=TZ)
                except ValueError:
                    continue

                t = ts.from_datetime(dt)

                ast_s = (earth + observer).at(t).observe(sun).apparent()
                ast_m = (earth + observer).at(t).observe(moon).apparent()

                lon_s, lat_s, dist_s = ast_s.ecliptic_latlon()
                lon_m, lat_m, dist_m = ast_m.ecliptic_latlon()

                ra_s, dec_s, _ = ast_s.radec()
                ra_m, dec_m, _ = ast_m.radec()

                ra_sh, ra_sm, dec_sd, dec_sm = ra_dec_hms_dms(ra_s, dec_s)
                ra_mh, ra_mm, dec_md, dec_mm = ra_dec_hms_dms(ra_m, dec_m)

                phase = almanac.moon_phase(eph, t).degrees
                illum = (1 - math.cos(math.radians(phase))) * 50

                sun_r, sun_s = rise_set(sun, dt)
                moon_r, moon_s = rise_set(moon, dt)

                danger = int(min(10, illum / 5))

                # === 惑星 ===
                planets = [mercury, venus, mars, jupiter, saturn]
                lon_p = []
                ra_p = []
                dec_p = []

                for p in planets:
                    ast = (earth + observer).at(t).observe(p).apparent()
                    lon, _, _ = ast.ecliptic_latlon()
                    ra, dec, _ = ast.radec()
                    lon_p.append(lon.degrees)
                    ra_p.append(ra.hours * 15)
                    dec_p.append(dec.degrees)

                writer.writerow([
                    year, month, day, youbi(dt),
                    f"{lon_s.degrees:7.3f}", f"{dist_s.au:.6f}",
                    f"{lon_m.degrees:7.3f}", f"{lat_m.degrees:+1.4f}", f"{dist_m.km:.0f}",
                    f"{phase:7.3f}", f"{illum:6.2f}",
                    f"{ra_sh:2d}h{ra_sm:4.1f}m", f"{dec_sd:+3d}°{dec_sm:2.0f}’",
                    f"{ra_mh:2d}h{ra_mm:4.1f}m", f"{dec_md:+3d}°{dec_mm:2.0f}’",
                    f"{moon_age(t):4.1f}",
                    sun_r, sun_s, moon_r, moon_s,
                    zodiac(lon_m.degrees), danger,
                    *[f"{x:7.3f}" for x in lon_p],
                    fmt_ra(ra_p[0]), fmt_dec(dec_p[0]),
                    fmt_ra(ra_p[1]), fmt_dec(dec_p[1]),
                    fmt_ra(ra_p[2]), fmt_dec(dec_p[2]),
                    fmt_ra(ra_p[3]), fmt_dec(dec_p[3]),
                    fmt_ra(ra_p[4]), fmt_dec(dec_p[4]),
                ])

# =====================
# 実行
# =====================
year = int(input("put in year "))
generate(year)
