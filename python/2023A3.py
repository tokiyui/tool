from skyfield.api import load
from skyfield.data import mpc
from skyfield.constants import GM_SUN_Pitjeva_2005_km3_s2 as GM_SUN
import math
from skyfield import almanac
from skyfield.api import load, wgs84
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
 
MONTH_NAMES = '0 Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
 
with load.open(mpc.COMET_URL) as f:
    comets = mpc.load_comets_dataframe(f)
 
comets = (comets.sort_values('reference').groupby('designation', as_index=False).last().set_index('designation', drop=False))
 
ts = load.timescale()
eph = load('de421.bsp')
sun, earth = eph['sun'], eph['earth']
observer = wgs84.latlon(+35.0, 135.0)
print(f"   Date   ,       Ra      ,        Dec      ,  Mag")
 
# 7月1日から12月31日までの日付を作成
start_date = ts.utc(2024, 9, 17)
end_date = ts.utc(2024, 10, 21)
date = start_date

# 指定された期間内の日付ごとに位置を計算し、表示
while date < end_date:
    t_str = date.utc_strftime('%Y-%m-%d')
    comet = sun + mpc.comet_orbit(comets.loc['C/2023 A3 (Tsuchinshan-ATLAS)'], ts, GM_SUN)
    ra, dec, distance = earth.at(date).observe(comet).radec()
    dist_e = earth.at(date).observe(comet).distance().au
    dist_s = sun.at(date).observe(comet).distance().au
    mag = 4.5 + 5.0 * math.log10(dist_e) + 10.0 *  math.log10(dist_s)
    print(f"{t_str}, {ra}, {dec}, {mag:+0.2f}")
    date = ts.tt_jd(date.tt + 1)
 
offset_x, offset_y = 10, 8
 
f = almanac.sunrise_sunset(eph, observer)
t, y = almanac.find_discrete(start_date, end_date, f)
sunsets = (y == 0)
t = t[sunsets]
 
year, month, day, hour, minute, second = t.utc
month = month.astype(int)
day = day.astype(int)
 
apparent = (earth + observer).at(t).observe(comet).apparent()
alt, az, distance = apparent.altaz()
x, y = az.degrees, alt.degrees
 
dist_e = earth.at(t).observe(comet).distance().au
dist_s = sun.at(t).observe(comet).distance().au
m = 4.5 + 5.0 * np.log10(dist_e) + 10.0 * np.log10(dist_s)
size = np.where(m < 2.0, 20 * (2.0 - m), 0)

fig, ax = plt.subplots(figsize=[9, 3])
ax.plot(x, y, c='#fff6', zorder=1)
ax.scatter(x, y, size, 'white', edgecolor='black', linewidth=0.25, zorder=2)
 
for i in np.flatnonzero(day):
    dx = x[i] - x[i-1]
    dy = y[i] - y[i-1]
    length = np.sqrt(dx*dx + dy*dy)
    dx /= length
    dy /= length 
    xytext = offset_x*dy, - offset_y*dx
 
    if day[i] in (1, 6, 11, 16, 21, 26):
        ax.annotate(day[i], (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=xytext, size=8)
        name = MONTH_NAMES[month[i]]
        ax.annotate(name, (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=2.2 * np.array(xytext))
 
points = 'N NE E SE S SW W NW'.split()
for i, name in enumerate(points):
    xy = 45 * i, 1
    ax.annotate(name, xy, c='white', ha='center', size=12, weight='bold')
 
ax.set(
    aspect=1.0,
    title='C/2023 A3 (Tsuchinshan-ATLAS) at sunset',
    xlabel='Azimuth (°)',
    ylabel='Altitude (°)',
    xlim=(195, 300),
    ylim=(0, 50),
    xticks=np.arange(210, 300, 15),
)
 
sky = LinearSegmentedColormap.from_list('sky', ['black', 'blue'])
extent = ax.get_xlim() + ax.get_ylim()
ax.imshow([[0,0], [1,1]], cmap=sky, interpolation='bicubic', extent=extent)
 
fig.savefig('evening_chart.png')
 
f = almanac.sunrise_sunset(eph, observer)
t, y = almanac.find_discrete(start_date, end_date, f)
sunrises = (y == 1)
t = t[sunrises]
 
year, month, day, hour, minute, second = t.utc
month = month.astype(int)
day = day.astype(int)
 
apparent = (earth + observer).at(t).observe(comet).apparent()
alt, az, distance = apparent.altaz()
x, y = az.degrees, alt.degrees
 
dist_e = earth.at(t).observe(comet).distance().au
dist_s = sun.at(t).observe(comet).distance().au
m = 4.5 + 5.0 * np.log10(dist_e) + 10.0 * np.log10(dist_s)
size = np.where(m < 2.0, 20 * (2.0 - m), 0)

fig, bx = plt.subplots(figsize=[9, 3])
bx.plot(x, y, c='#fff6', zorder=1)
bx.scatter(x, y, size, 'white', edgecolor='black', linewidth=0.25, zorder=2)
 
for i in np.flatnonzero(day):
    dx = x[i] - x[i-1]
    dy = y[i] - y[i-1]
    length = np.sqrt(dx*dx + dy*dy)
    dx /= length
    dy /= length 
    xytext = offset_x*dy, - offset_y*dx
 
    if day[i] in (1, 6, 11, 16, 20, 26):
        bx.annotate(day[i], (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=xytext, size=8)
        name = MONTH_NAMES[month[i]]
        bx.annotate(name, (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=2.2 * np.array(xytext))
 
points = 'N NE E SE S SW W NW'.split()
for i, name in enumerate(points):
    xy = 45 * i, 1
    bx.annotate(name, xy, c='white', ha='center', size=12, weight='bold')
 
bx.set(
    aspect=1.0,
    title='C/2023 A3 (Tsuchinshan-ATLAS) at sunrise',
    xlabel='Azimuth (°)',
    ylabel='Altitude (°)',
    xlim=(60, 165),
    ylim=(0, 50),
    xticks=np.arange(75, 165, 15),
)
 
sky = LinearSegmentedColormap.from_list('sky', ['black', 'blue'])
extent = bx.get_xlim() + bx.get_ylim()
bx.imshow([[0,0], [1,1]], cmap=sky, interpolation='bicubic', extent=extent)
 
fig.savefig('morning_chart.png')
