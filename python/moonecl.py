from skyfield.api import load
from pytz import timezone
import numpy as np

# 初期時刻設定
ts = load.timescale()
t = ts.utc(2025, 9, 7, 16, 0, range(0, 15000))
tz = timezone('Asia/Tokyo')

# 太陽・月・地球
eph = load('de421.bsp')
sun, moon, earth = eph['sun'], eph['moon'], eph['earth']

# 太陽・月の位置計算
sun_app = earth.at(t).observe(sun).apparent()
moon_app = earth.at(t).observe(moon).apparent()

# 太陽・月の見かけの大きさ計算
r_sun = 696000
sun_dist = sun_app.distance().km
sun_rad = np.arctan2(r_sun, sun_dist)

r_moon = 1737
moon_dist = moon_app.distance().km
moon_rad = np.arctan2(r_moon, moon_dist)

# 視差・本影の視半径計算
r_earth = 6378
parallax_sun = r_earth / sun_dist
parallax_moon = r_earth / moon_dist
umbra = (parallax_moon - sun_rad + parallax_sun) * 51/50

# 月・地球の本影の角距離の計算
app_sep = abs(sun_app.separation_from(moon_app).radians - np.deg2rad(180))
print(moon_rad)

# 食分の計算
percent_eclipse = (umbra + moon_rad - app_sep) / (moon_rad * 2)
    
# 食の最大の検索	
max_i = np.argmax(percent_eclipse)

# 太陽と月の天球上の位置を経度・緯度で取得
sun_ra, sun_dec, _ = sun_app.radec()  # 太陽のRAとDec
moon_ra, moon_dec, _ = moon_app.radec()  # 月のRAとDec

# 角度差の調整を行う関数
def adjust_angle(ra_diff):
    if ra_diff > 90:
        return ra_diff - 180
    elif ra_diff < -90:
        return ra_diff + 180
    else:
        return ra_diff

# 経度（RA）の差を計算
delta_ra = np.degrees(sun_ra.radians - moon_ra.radians)
# -180度から+180度の範囲に収める
delta_ra = np.vectorize(adjust_angle)(delta_ra)
print(delta_ra)

# 緯度（Dec）の差を計算
delta_dec = np.degrees(sun_dec.radians + moon_dec.radians)

# 食の最大の検索
max_i = np.argmax(percent_eclipse)

# 欠け始めと食の終わりの検索
eclipse = False
eclipse_times = []
for ti, pi in zip(t, percent_eclipse):
    if pi > 0:
        if eclipse == False:
            eclipse_times.append(f'Start: {ti.astimezone(tz).strftime("%H:%M:%S")} JST')
            eclipse = True
    else:
        if eclipse == True:
            eclipse_times.append(f' End: {ti.astimezone(tz).strftime("%H:%M:%S")} JST')
            eclipse = False

# 描画
plt.figure(figsize=(6, 6))
ax = plt.subplot(111, projection='rectilinear')

# x軸とy軸の表示範囲を調整して図の中心を (0, 0) にする
ax.set_xlim(-2, 2)
ax.set_ylim(-2, 2)

# 半径1の茶色い円
circle1 = plt.Circle((0, 0), 1, color='brown', alpha=0.5, label="Sun-Earth")
ax.add_artist(circle1)

# 1時間ごとに描画
for i in range(0, len(t), 3600):  # 1時間おきに処理
    ti = t[i]

    # Use the scalar values of delta_ra, delta_dec, moon_rad, and umbra at index i
    ra = delta_ra[i]  #  delta_ra's scalar value at index i
    dec = delta_dec[i]  #  delta_dec's scalar value at index i
    
    # Calculate the position and radius using scalar values
    circle_x = ra / umbra[i] 
    circle_y = dec / umbra[i]
    circle_radius = moon_rad[i] / umbra[i]

    # 描画 (角度差を反映)
    circle2 = plt.Circle((circle_x / 60.0, circle_y / 60.0), circle_radius, color='yellow', alpha=0.7)
    ax.add_artist(circle2)
    print(circle_x, circle_y)

    # 中心に時刻を描画 (時刻に "h" を追加)
    time_str = ti.astimezone(tz).strftime('%H') + "h"  # 時刻に "h" を追加
    ax.text(circle_x / 60.0, circle_y / 60.0, time_str, color='black', ha='center', va='center', fontsize=8)

# 食の最大、最大食分、欠け始めと食の終わりの情報を左上に表示
ax.text(0.32, 0.92, 
        f'Max: {t[max_i].astimezone(tz).strftime("%H:%M:%S")} JST ({percent_eclipse[max_i]:.2f})', 
        transform=ax.transAxes, fontsize=10, verticalalignment='bottom', horizontalalignment='left')

# 欠け始めと食の終わり
for i, eclipse_time in enumerate(eclipse_times):
    ax.text(0.36, 0.96 - 0.08 * i, eclipse_time, 
            transform=ax.transAxes, fontsize=10, verticalalignment='bottom', horizontalalignment='left')

 
# 軸非表示
ax.set_xticklabels([])  # x軸のラベルを消す
ax.set_yticklabels([])  # y軸のラベルを消す

# 表示
plt.title('2025-09-08 Total Moon Eclipse')
plt.show()
