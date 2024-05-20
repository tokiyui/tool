from skyfield.api import Star, Topos, load
from pytz import timezone
import numpy as np
import matplotlib.pyplot as plt
import numpy.ma as ma
import matplotlib.dates as mdates
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from skyfield.data import hipparcos

with load.open(hipparcos.URL) as f:
    df = hipparcos.load_dataframe(f)

star = Star.from_dataframe(df.loc[65474])
 
# 初期時刻設定
ts = load.timescale()
t = ts.utc(2024, 8, 10, 10, 30, range(0, 9000, 5)) #2024-08-10:Spica食
tz = timezone('Asia/Tokyo')

# 月位置の読み込み
eph = load('de440s.bsp')
moon, earth = eph['moon'], eph['earth']
 
# 観測地設定（範囲内の格子点生成）
grid_points = []
latitudes = np.arange(20, 50, 0.5)
longitudes = np.arange(120, 150, 0.5)
 
for lat in latitudes:
    for lon in longitudes:
        grid_points.append((lat, lon))
 
# 等値線図データの初期化
eclipse_start_data = np.empty((len(latitudes), len(longitudes)), dtype='datetime64[s]')
eclipse_start_data.fill(np.datetime64('NaT'))
eclipse_end_data = np.empty((len(latitudes), len(longitudes)), dtype='datetime64[s]')
eclipse_end_data.fill(np.datetime64('NaT'))
max_percent_eclipse = np.empty((len(latitudes), len(longitudes)))
 
# 観測地設定と計算
for i, lat in enumerate(latitudes):
    for j, lon in enumerate(longitudes):
        observer_location = earth + Topos(f'{lat} N', f'{lon} E')
 
        # 恒星・月の位置計算
        star_app = observer_location.at(t).observe(star).apparent()
        moon_app = observer_location.at(t).observe(moon).apparent()
 
        # 月の視半径の計算
        r_moon = 1737
        moon_dist = moon_app.distance().km
        moon_rad = np.arctan2(r_moon, moon_dist)
 
        # 恒星・月の角距離の計算
        app_sep = star_app.separation_from(moon_app).radians
 
        # 上記角距離と月の視半径の差
        percent_eclipse = moon_rad - app_sep
        max_percent_eclipse[i, j] = np.max(percent_eclipse)
 
        # 欠け始めと食の終わりの検索
        eclipse = False
        for ti, pi in zip(t, percent_eclipse):
            if pi > 0:
                if not eclipse:
                    alt, az, _ = observer_location.at(ti).observe(moon).apparent().altaz()
                    # UTC時間を使って変換
                    eclipse_start_data[i, j] = np.datetime64(ti.astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S'))
                    eclipse = True
            else:
                if eclipse:
                    alt, az, _ = observer_location.at(ti).observe(moon).apparent().altaz()
                    # UTC時間を使って変換
                    eclipse_end_data[i, j] = np.datetime64(ti.astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S'))
                    eclipse = False
 
# 2Dグリッドの作成
lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
 
# 文字列からdatetime64への変換
eclipse_start_data_array = np.array(eclipse_start_data, dtype='datetime64')
eclipse_end_data_array = np.array(eclipse_end_data, dtype='datetime64')
 
init = np.datetime64(ts.utc(2024, 8, 10).utc_datetime())

# プロット
plt.figure(figsize=(12, 8))
 
# 地図投影法の設定
ax = plt.axes(projection=ccrs.PlateCarree())
 
# 海岸線を追加
ax.add_feature(cfeature.COASTLINE)
ax.add_feature(cfeature.LAND, facecolor='green')
ax.add_feature(cfeature.OCEAN, facecolor='blue')

eclipse_start_data_seconds = (eclipse_start_data_array - init).astype('timedelta64[s]').astype(int)
eclipse_end_data_seconds = (eclipse_end_data_array - init).astype('timedelta64[s]').astype(int)

contour_set_s = plt.contour(lon_grid, lat_grid, eclipse_start_data_seconds, colors='black', levels=range(0, eclipse_start_data_seconds.max(), 300))
contour_set_e = plt.contour(lon_grid, lat_grid, eclipse_end_data_seconds, linestyles='dashed', colors='black', levels=range(0, eclipse_end_data_seconds.max(), 300))
plt.contour(lon_grid, lat_grid, max_percent_eclipse, levels=[0])
 
# 等値線に時刻ラベルを追加
plt.clabel(contour_set_s, inline=True, fmt=lambda x: mdates.num2date(x/86400.0).strftime('%H:%M'), fontsize=8, colors='black')
plt.clabel(contour_set_e, inline=True, fmt=lambda x: mdates.num2date(x/86400.0).strftime('%H:%M'), fontsize=8, colors='black')
 
plt.title('2024 Aug 10 - Spica occultation start(solid) and end(dashed) time(JST)')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.show()