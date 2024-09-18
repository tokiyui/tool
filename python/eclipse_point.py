from skyfield.api import Topos, load
from pytz import timezone
import numpy as np
import math

# 初期時刻設定
ts = load.timescale()
t = ts.utc(2035, 9, 1, 23, 0, range(0, 21000))
tz = timezone('Asia/Tokyo')

# 太陽・月・地球
eph = load('de421.bsp')
sun, moon, earth = eph['sun'], eph['moon'], eph['earth']

# 観測地設定
osaka = earth + Topos('34.6914 N', '135.4917 E')

# 太陽・月の位置計算
sun_app = osaka.at(t).observe(sun).apparent()
moon_app = osaka.at(t).observe(moon).apparent()

# 太陽・月の見かけの大きさ計算
r_sun = 696000
sun_dist = sun_app.distance().km
sun_rad = np.arctan2(r_sun, sun_dist)

r_moon = 1737
moon_dist = moon_app.distance().km
moon_rad = np.arctan2(r_moon, moon_dist)

# 太陽・月の角距離の計算
app_sep = sun_app.separation_from(moon_app).radians
diff_lon = (moon_app.radec()[0]._degrees - sun_app.radec()[0]._degrees)
diff_lat = (moon_app.radec()[1]._degrees - sun_app.radec()[1]._degrees)

# 食分の計算
percent_eclipse = (sun_rad + moon_rad - app_sep) / (sun_rad * 2)
    
# 食の最大の検索	
max_i = np.argmax(percent_eclipse)

#print('食の最大:', t[max_i].astimezone(tz).strftime('%H:%M:%S'), 'JST')
#print('最大食分: {0:.3f}'.format(percent_eclipse[max_i]))
max = 'Max: ' + t[max_i].astimezone(tz).strftime('%H:%M:%S') + ' JST (max precent: {0:.3f}'.format(percent_eclipse[max_i]) + ')'

# 円の中心座標
center_x = 0.5
center_y = 0.5

# 太陽の半径（ラジアンから度に変換）
sun_rad_deg = np.degrees(sun_rad[max_i])

# 太陽の円を描画
sun_circle = plt.Circle((center_x, center_y), sun_rad_deg, color='orange', fill=True)
plt.gca().add_artist(sun_circle)

# 左にずれる量と上にずれる量
diff_lon = diff_lon[max_i]
diff_lat = diff_lat[max_i]

# 月の半径（ラジアンから度に変換）
moon_rad_deg = np.degrees(moon_rad[max_i])

# 月の円を描画
moon_circle = plt.Circle((center_x - diff_lon, center_y + diff_lat), moon_rad_deg, color='gray', fill=True)
plt.gca().add_artist(moon_circle)

# 軸を非表示にする
plt.axis('off')

# 縦横比を1:1に設定
plt.gca().set_aspect('equal', adjustable='box')

plt.title('2035 Sep 2 - Total eclipse at Tokyo')

# 欠け始めと食の終わりの検索
eclipse = False

for ti, pi in zip(t, percent_eclipse):
    if pi > 0 :
        if eclipse == False:
            #print('欠け始め:', ti.astimezone(tz).strftime('%H:%M:%S'), 'JST')
            start = 'Start: ' + ti.astimezone(tz).strftime('%H:%M:%S') + ' JST'
            eclipse = True
    else :
        if eclipse == True:
            #print('食の終わり:', ti.astimezone(tz).strftime('%H:%M:%S'), 'JST')
            end = 'End: ' + ti.astimezone(tz).strftime('%H:%M:%S') + ' JST'
            eclipse = False

plt.text(0.125,0.95,max)
plt.text(0.125,0.9,start)
plt.text(0.525,0.9,end)
