import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from skyfield import almanac
from skyfield.api import load, wgs84
from skyfield.magnitudelib import planetary_magnitude

MONTH_NAMES = '0 Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()

# Figure out the times of sunset over our range of dates.

eph = load('de421.bsp')
earth, sun, mercury, venus = eph['earth'], eph['sun'], eph['mercury'], eph['venus']
observer = wgs84.latlon(+40.0, 0.0)

yy = 2025
ts = load.timescale()
start, end = ts.utc(yy - 1, 12, 31), ts.utc(yy, 12, 31)

f = almanac.sunrise_sunset(eph, observer)
t, y = almanac.find_discrete(start, end, f)
sunrise = (y == 1)
sunsets = (y == 0)
s = t[sunrise]
t = t[sunsets]

year, month, day, hour, minute, second = t.utc
month = month.astype(int)
day = day.astype(int)

apparent = (earth + observer).at(s).observe(mercury).apparent()
alt, az, distance = apparent.altaz()
x, y = az.degrees, alt.degrees
m = planetary_magnitude(apparent)
size = 40 - 30 * (m - min(m)) / (max(m) - min(m))

fig, ax = plt.subplots(figsize=[6, 3])
ax.plot(x, y, c='#fff6', zorder=1)

fives = (day % 10 == 1) & (day < 30)
ax.scatter(x[fives], y[fives], size[fives], 'white', edgecolor='black', linewidth=0.25, zorder=2)

offset_x, offset_y = 10, 8

for i in np.flatnonzero(fives):
    if i == 0:
        continue

    dx = x[i] - x[i-1]
    dy = y[i] - y[i-1]
    length = np.sqrt(dx*dx + dy*dy)
    dx /= length
    dy /= length

    xytext = - offset_x*dy, offset_y*dx

    if day[i] == 1:
        name = MONTH_NAMES[month[i]]
        ax.annotate(name, (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=xytext)

points = 'N NE E SE S SW W NW'.split()
for i, name in enumerate(points):
    xy = 45 * i, 1
    ax.annotate(name, xy, c='white', ha='center', size=12, weight='bold')

ax.set(
    aspect=1.0,
    title=f'Mercury at sunrise for 40°N latitude, January {yy} – December {yy}',
    xlabel='Azimuth (°)',
    ylabel='Altitude (°)',
    xlim=(55, 155),
    ylim=(0, 25),
    xticks=np.arange(60, 165, 15),
)

sky = LinearSegmentedColormap.from_list('sky', ['black', 'blue'])
extent = ax.get_xlim() + ax.get_ylim()
ax.imshow([[0,0], [1,1]], cmap=sky, interpolation='bicubic', extent=extent)

fig.savefig('mercury_morning_chart.png')

apparent = (earth + observer).at(t).observe(mercury).apparent()
alt, az, distance = apparent.altaz()
x, y = az.degrees, alt.degrees
m = planetary_magnitude(apparent)
size = 40 - 30 * (m - min(m)) / (max(m) - min(m))

fig, ax = plt.subplots(figsize=[6, 3])
ax.plot(x, y, c='#fff6', zorder=1)

fives = (day % 10 == 1) & (day < 30)
ax.scatter(x[fives], y[fives], size[fives], 'white', edgecolor='black', linewidth=0.25, zorder=2)

offset_x, offset_y = 10, 8

for i in np.flatnonzero(fives):
    if i == 0:
        continue

    dx = x[i] - x[i-1]
    dy = y[i] - y[i-1]
    length = np.sqrt(dx*dx + dy*dy)
    dx /= length
    dy /= length

    xytext = - offset_x*dy, offset_y*dx

    if day[i] in (1, 11, 21):
        ax.annotate(day[i], (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=xytext, size=8)

    if day[i] == 1:
        name = MONTH_NAMES[month[i]]
        ax.annotate(name, (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=2.2 * np.array(xytext))

points = 'N NE E SE S SW W NW'.split()
for i, name in enumerate(points):
    xy = 45 * i, 1
    ax.annotate(name, xy, c='white', ha='center', size=12, weight='bold')

ax.set(
    aspect=1.0,
    title=f'Mercury at sunset for 40°N latitude, January {yy} – December {yy}',
    xlabel='Azimuth (°)',
    ylabel='Altitude (°)',
    xlim=(205, 305),
    ylim=(0, 25),
    xticks=np.arange(210, 315, 15),
)

sky = LinearSegmentedColormap.from_list('sky', ['black', 'blue'])
extent = ax.get_xlim() + ax.get_ylim()
ax.imshow([[0,0], [1,1]], cmap=sky, interpolation='bicubic', extent=extent)

fig.savefig('mercury_evening_chart.png')

apparent = (earth + observer).at(s).observe(venus).apparent()
alt, az, distance = apparent.altaz()
x, y = az.degrees, alt.degrees
m = planetary_magnitude(apparent)
size = 40 - 30 * (m - min(m)) / (max(m) - min(m))

fig, ax = plt.subplots(figsize=[9, 3])
ax.plot(x, y, c='#fff6', zorder=1)

fives = (day % 10 == 1) & (day < 30)
ax.scatter(x[fives], y[fives], size[fives], 'white', edgecolor='black', linewidth=0.25, zorder=2)

offset_x, offset_y = 10, 8

for i in np.flatnonzero(fives):
    if i == 0:
        continue

    dx = x[i] - x[i-1]
    dy = y[i] - y[i-1]
    length = np.sqrt(dx*dx + dy*dy)
    dx /= length
    dy /= length

    xytext = - offset_x*dy, offset_y*dx

    if day[i] in (1, 11, 21):
        ax.annotate(day[i], (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=xytext, size=8)

    if day[i] == 1:
        name = MONTH_NAMES[month[i]]
        ax.annotate(name, (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=2.2 * np.array(xytext))

points = 'N NE E SE S SW W NW'.split()
for i, name in enumerate(points):
    xy = 45 * i, 1
    ax.annotate(name, xy, c='white', ha='center', size=12, weight='bold')

ax.set(
    aspect=1.0,
    title=f'Venus at sunrise for 40°N latitude, January {yy} – December {yy}',
    xlabel='Azimuth (°)',
    ylabel='Altitude (°)',
    xlim=(50, 175),
    ylim=(0, 50),
    xticks=np.arange(60, 180, 15),
)

sky = LinearSegmentedColormap.from_list('sky', ['black', 'blue'])
extent = ax.get_xlim() + ax.get_ylim()
ax.imshow([[0,0], [1,1]], cmap=sky, interpolation='bicubic', extent=extent)

fig.savefig('venus_morning_chart.png')

apparent = (earth + observer).at(t).observe(venus).apparent()
alt, az, distance = apparent.altaz()
x, y = az.degrees, alt.degrees
m = planetary_magnitude(apparent)
size = 40 - 30 * (m - min(m)) / (max(m) - min(m))

fig, ax = plt.subplots(figsize=[9, 3])
ax.plot(x, y, c='#fff6', zorder=1)

fives = (day % 10 == 1) & (day < 30)
ax.scatter(x[fives], y[fives], size[fives], 'white', edgecolor='black', linewidth=0.25, zorder=2)

offset_x, offset_y = 10, 8

for i in np.flatnonzero(fives):
    if i == 0:
        continue

    dx = x[i] - x[i-1]
    dy = y[i] - y[i-1]
    length = np.sqrt(dx*dx + dy*dy)
    dx /= length
    dy /= length

    xytext = - offset_x*dy, offset_y*dx

    if day[i] in (1, 11, 21):
        ax.annotate(day[i], (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=xytext, size=8)

    if day[i] == 1:
        name = MONTH_NAMES[month[i]]
        ax.annotate(name, (x[i], y[i]), c='white', ha='center', va='center', textcoords='offset points', xytext=2.2 * np.array(xytext))

points = 'N NE E SE S SW W NW'.split()
for i, name in enumerate(points):
    xy = 45 * i, 1
    ax.annotate(name, xy, c='white', ha='center', size=12, weight='bold')

ax.set(
    aspect=1.0,
    title=f'Venus at sunset for 40°N latitude, January {yy} – December {yy}',
    xlabel='Azimuth (°)',
    ylabel='Altitude (°)',
    xlim=(185, 310),
    ylim=(0, 50),
    xticks=np.arange(195, 315, 15),
)

sky = LinearSegmentedColormap.from_list('sky', ['black', 'blue'])
extent = ax.get_xlim() + ax.get_ylim()
ax.imshow([[0,0], [1,1]], cmap=sky, interpolation='bicubic', extent=extent)

fig.savefig('venus_evening_chart.png')
