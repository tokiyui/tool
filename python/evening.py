import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
from matplotlib.colors import LinearSegmentedColormap
from skyfield import almanac
from skyfield.api import load, wgs84
 
# 天体暦データを読み込む
eph = load('de421.bsp')
earth, sun, moon = eph['earth'], eph['sun'], eph['moon']
observer = wgs84.latlon(+40.0, 0.0)
 
ts = load.timescale()
start, end = ts.utc(2040, 9, 1), ts.utc(2040, 9, 30)
 
# 日の入り時間を取得
f = almanac.sunrise_sunset(eph, observer)
t, y = almanac.find_discrete(start, end, f)
t = t[y == 0]  # 日没時刻のみ
 
# 月の位置データを取得
apparent = (earth + observer).at(t).observe(moon).apparent()
alt, az, _ = apparent.altaz()
x, y = az.degrees, alt.degrees
 
# 月の位相（輝いている割合）を計算する関数
def calculate_illuminated_fraction(phase_angle):
    return (1 + np.cos(np.radians(phase_angle))) / 2
 
def get_moon_phase(t):
    """月の位相角を計算し、輝いている部分の比率と影の方向を返す"""
    sun_pos = (earth + observer).at(t).observe(sun).position.au
    moon_pos = (earth + observer).at(t).observe(moon).position.au
 
    # 月と太陽の位置ベクトル間の角度を計算
    dot_product = np.dot(sun_pos, moon_pos)
    norm_sun = np.linalg.norm(sun_pos)
    norm_moon = np.linalg.norm(moon_pos)
    cos_angle = dot_product / (norm_sun * norm_moon)
    phase_angle = np.degrees(np.arccos(cos_angle))
 
    illuminated_fraction = calculate_illuminated_fraction(phase_angle)
 
    # 太陽の方位角を取得し、影の向きを計算
    sun_apparent = (earth + observer).at(t).observe(sun).apparent()
    _, sun_az, _ = sun_apparent.altaz()
    shadow_angle = sun_az.degrees + 180  # 太陽の反対側に影
 
    return phase_angle, illuminated_fraction, shadow_angle
 
# 図の作成
fig, ax = plt.subplots(figsize=[9, 5])
 
# 各時点で月を描画
moon_radius = 2.0
for i, time in enumerate(t):
    phase_angle, illuminated_fraction, shadow_angle = get_moon_phase(time)
    moon_x, moon_y = x[i], y[i]
 
    # 月の背景の円（満月の状態）
    moon_circle = plt.Circle((moon_x, moon_y), moon_radius, color='white', ec='black', lw=1, zorder=3)
    ax.add_artist(moon_circle)
 
    # 影の描画（Wedge を使用）
    shadow_start_angle = shadow_angle - 90
    shadow_extent = 180 if illuminated_fraction < 0.5 else -180
    shadow = Wedge((moon_x, moon_y), moon_radius, shadow_start_angle, shadow_start_angle + shadow_extent, color='black', zorder=4)
    ax.add_patch(shadow)
 
    # 日付ラベルを表示
    year, month, day, _, _, _ = time.utc
    ax.text(moon_x + 3, moon_y, f"{month}/{day}", fontsize=8, color="white", ha="left", va="center")
 
ax.set_aspect('equal')
ax.set(
    title='The sky at the end of twilight in September 2040',
    xlabel='Azimuth (°)',
    ylabel='Altitude (°)',
    xlim=(195, 300),
    ylim=(0, max(y) + 10.0),
    xticks=np.arange(210, 300, 15),
)
 
# 背景の空のグラデーション
sky = LinearSegmentedColormap.from_list('sky', ['black', 'blue'])
extent = ax.get_xlim() + ax.get_ylim()
ax.imshow([[0, 0], [1, 1]], cmap=sky, interpolation='bicubic', extent=extent)
 
plt.show()
 
