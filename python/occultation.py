import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from skyfield.api import Star, Topos, load
from skyfield.data import hipparcos
from datetime import datetime, timedelta
 
with load.open(hipparcos.URL) as f:
    df = hipparcos.load_dataframe(f)
 
star = Star.from_dataframe(df.loc[65474])
 
# 初期時刻設定
ts = load.timescale()
t0 = ts.utc(2024, 12, 24, 17, 30)
 
# 太陽・月・地球
eph = load('de421.bsp')
sun, moon, earth = eph['sun'], eph['moon'], eph['earth']
 
observer_location = earth + Topos('35.6914 N', '135.4917 E')
 
# 月と太陽の離角を計算
_, slon, _ = observer_location.at(t0).observe(sun).apparent().ecliptic_latlon()
_, mlon, _ = observer_location.at(t0).observe(moon).apparent().ecliptic_latlon()
moon_elong = (mlon.degrees - slon.degrees) % 360
 
# 描画領域を準備
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
 
# x, y, z軸の範囲設定
ax.set_xlim([-1., 1.])
ax.set_ylim([-1., 1.])
ax.set_zlim([-1., 1.])
 
# x, y, z軸や目盛を非表示に
ax.set_axis_off()
 
# 背景の x, y, z面を非表示に
ax.xaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
ax.yaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
ax.zaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
 
# 背面を灰色に
ax.set_facecolor('white')
 
# メッシュ状の球面 (u, v) を準備し、(x, y, z) 値を計算
u, v = np.mgrid[0:2*np.pi:50j, 0:np.pi:25j] # u:接線方向　v:動経方向
x = np.cos(u) * np.sin(v)
y = np.sin(u) * np.sin(v)
z = np.cos(v)
 
# メッシュの球面に貼りつける色を準備（半分だけ黄色に）
colors = np.zeros((50, 25, 3))
colors[:25, :, 0] = 1
colors[:25, :, 1] = 1
colors[:25, :, 2] = 0
 
# 球面をプロット
ax.plot_surface(x, y, z, facecolors=colors, shade=False)
ax.set_box_aspect([1, 1, 1])
 
ax.view_init(elev=0, azim=moon_elong - 90)
 
t = ts.utc(2024, 12, 24, 17, 30, range(0, 9000, 600))
 
# 恒星・月の位置計算
star_app = observer_location.at(t).observe(star).apparent().radec()
moon_app = observer_location.at(t).observe(moon).apparent().radec()
 
# 月の視半径の計算
r_moon = 1737
moon_dist = observer_location.at(t0).observe(moon).apparent().distance().km
moon_rad = np.arctan2(r_moon, moon_dist)
moon_deg = np.degrees(moon_rad)
 
# 恒星・月の角距離の計算
diff_lon = (star_app[0]._degrees - moon_app[0]._degrees) / moon_deg
diff_lat = (star_app[1]._degrees - moon_app[1]._degrees) / moon_deg
 
# 図の中での座標を設定
point_in_figure = np.array([np.ones_like(diff_lon), -diff_lon, diff_lat])

# azimuthの逆回転角度
azimuth_angle = moon_elong - 90
 
# ベクトルをazimuth_angleだけ逆回転させる
rotation_matrix = np.array([[np.cos(np.radians(azimuth_angle)), -np.sin(np.radians(azimuth_angle)), 0],
                            [np.sin(np.radians(azimuth_angle)), np.cos(np.radians(azimuth_angle)), 0],
                            [0, 0, 1]])
rotated_vec = np.dot(rotation_matrix, point_in_figure)

# 点をプロット
ax.scatter([rotated_vec[0]], [rotated_vec[1]], [rotated_vec[2]], color='lightgreen', s=50)

t_jst = [time.utc_datetime() + timedelta(hours=9) for time in t]
time_str = np.array([time.strftime('%H:%M') for time in t_jst])

for i in range(len(rotated_vec[0])):
    ax.text(rotated_vec[0][i]-0.8, rotated_vec[1][i], rotated_vec[2][i], time_str[i], color='gray', fontsize=12, zorder=10)

plt.title('2024 Dec 25 Spica occultation at Tokyo')

plt.show()
