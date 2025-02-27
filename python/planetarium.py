from skyfield.api import load, Topos, Star
from skyfield.data import hipparcos
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from matplotlib.patches import Circle, Wedge
import math

# 観測地点（北緯35度、東経140度）
location = Topos(latitude_degrees=35.0, longitude_degrees=140.0)

# 時刻設定（1995年8月15日21時 JST = UTC+9）
uts = datetime(1995, 8, 15, 23, 0, tzinfo=timezone(timedelta(hours=9)))
ts = load.timescale()
t = ts.from_datetime(uts)

# 天体データのロード
eph = load('de421.bsp')  # 惑星データ
stars = load.open(hipparcos.URL)  # 恒星データ
hipparcos_data = hipparcos.load_dataframe(stars)

# 4等星以上の恒星のみ選択
hipparcos_data = hipparcos_data[hipparcos_data['magnitude'] <= 4.0]

# 惑星リスト
planets = ['mercury', 'venus', 'mars', 'jupiter barycenter', 'saturn barycenter']

# 惑星ごとの色設定
planet_colors = {
    'mercury': 'gray',
    'venus': 'orange',
    'mars': 'red',
    'jupiter barycenter': 'brown',
    'saturn barycenter': 'gold'
}

# 観測地点からの視線ベクトル
earth = eph['earth']
observer = earth + location

# 観測地点から見た天体の座標を計算
def get_alt_az(idx):
    star = Star.from_dataframe(hipparcos_data.loc[idx])
    astro = observer.at(t).observe(star).apparent()
    alt, az, _ = astro.altaz()
    return alt.degrees, az.degrees

# 恒星の座標を計算
altitudes, azimuths, sizes = [], [], []
for idx in hipparcos_data.index:
    alt, az = get_alt_az(idx)
    if alt > 0:  # 地平線より上の星のみ表示
        altitudes.append(alt)
        azimuths.append(az)
        mag = hipparcos_data.loc[idx, 'magnitude']
        sizes.append(5 * (4.0 - mag))  # 明るいほど大きく描画

# 惑星の座標を計算
planet_positions = {}
for planet in planets:
    astro = observer.at(t).observe(eph[planet]).apparent()
    alt, az, _ = astro.altaz()
    if alt.degrees > 0:
        planet_positions[planet] = (alt.degrees, az.degrees)

# 月の座標と満ち欠けを計算
astro_moon = observer.at(t).observe(eph['moon']).apparent()
alt_moon, az_moon, _ = astro_moon.altaz()
phase_angle = observer.at(t).observe(eph['sun']).apparent().phase_angle(eph['moon'])
illumination = (1 + np.cos(phase_angle.radians)) / 2  # 照らされた割合

# 星空をプロット
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})
ax.set_theta_zero_location('N')  # 北を上に
ax.set_theta_direction(1)  # 時計回り

# 恒星をプロット
ax.scatter(np.radians(azimuths), 90 - np.array(altitudes), s=sizes, color='white')

# 惑星をプロット
for planet, (alt, az) in planet_positions.items():
    color = planet_colors.get(planet, 'yellow')  # デフォルトは黄色
    ax.scatter(np.radians(az), 90 - alt, s=50, label=planet.capitalize(), color=color)

# 月の満ち欠けを考慮した描画
if alt_moon.degrees > 0:
    moon_x, moon_y = np.radians(az_moon.degrees), 90 - alt_moon.degrees
    moon_size = 6  # 相対サイズ調整
    if illumination < 0.5:
        angle = 180  # 満ち欠けの方向
    else:
        angle = 0  # 満月方向
    ax.scatter([moon_x], [moon_y], color="yellow", s=100)  # 月をプロット(満ち欠けは未実装)

# 月の描画
ax.legend()
ax.set_facecolor('black')
ax.set_ylim(0, 90)
ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
ax.set_yticklabels([])
plt.title(f'Sky at 1995-08-15 21:00 JST (35N, 135E)')
plt.show()
