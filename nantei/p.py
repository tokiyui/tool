import os
import requests
import datetime as dt
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from metpy.units import units
import metpy.calc as mpcalc

# ========================
# 設定
# ========================
START  = "2022-01-05 12:00"
END    = "2022-01-07 12:00"
LEVELS = [850, 925, 950, 975]

# 描画・計算領域（lon_min, lon_max, lat_min, lat_max）
EXTENT = [136, 142, 33, 38]

OUTDIR = "Data"
os.makedirs(OUTDIR, exist_ok=True)

# ========================
# 時刻処理（UTC）
# ========================
start = dt.datetime.fromisoformat(START)
end   = dt.datetime.fromisoformat(END)

times = []
t = start
while t <= end:
    times.append(t)
    t += dt.timedelta(hours=3)

dates = sorted(set([t.strftime("%Y/%m%d") for t in times]))

# ========================
# MSM-P データ取得
# ========================
base = "http://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/netcdf/MSM-P"
files = []

for d in dates:
    y, md = d.split("/")
    url = f"{base}/{y}/{md}.nc"
    fname = md + ".nc"

    if not os.path.exists(fname):
        print("download:", url)
        r = requests.get(url)
        r.raise_for_status()
        with open(fname, "wb") as f:
            f.write(r.content)

    files.append(fname)

ds = xr.open_mfdataset(files, combine="by_coords")

# ========================
# 描画設定
# ========================
temp_levels = np.arange(-3, 4, 1)
proj = ccrs.PlateCarree()

pref = cfeature.NaturalEarthFeature(
    category="cultural",
    name="admin_1_states_provinces_lines",
    scale="10m",
    facecolor="none"
)

LON_MIN, LON_MAX, LAT_MIN, LAT_MAX = EXTENT

# ========================
# メインループ
# ========================
for t in times:
    for lev in LEVELS:

        # -------- 領域切り出し（最重要：高速化） --------
        da = ds.sel(
            time=t,
            p=lev,
            lon=slice(LON_MIN, LON_MAX),
            lat=slice(LAT_MAX, LAT_MIN)
        )

        # -------- 物理量 --------
        T  = da["temp"].metpy.quantify()
        U  = da["u"].metpy.quantify()
        V  = da["v"].metpy.quantify()
        RH = da["rh"].metpy.quantify()

        Td = mpcalc.dewpoint_from_relative_humidity(T, RH)
        Tw = mpcalc.wet_bulb_temperature(lev * units.hPa, T, Td)

        # -------- 単位変換（描画用） --------
        T_C  = T.metpy.convert_units("degC").values
        Tw_C = Tw.metpy.convert_units("degC").values
        U_ms = U.metpy.convert_units("m/s").values*2
        V_ms = V.metpy.convert_units("m/s").values*2

        # ========================
        # 描画
        # ========================
        fig = plt.figure(figsize=(8, 6))
        ax = plt.axes(projection=proj)

        ax.set_extent(EXTENT, crs=proj)

        ax.add_feature(pref, edgecolor="black", linewidth=0.6, zorder=5)
        ax.coastlines(resolution="10m", linewidth=0.8, zorder=5)

        # --- 気温 ---
        cf = ax.contourf(
            da.lon, da.lat, T_C,
            levels=temp_levels,
            cmap="coolwarm",
            extend="both",
            transform=proj,
            zorder=1
        )

        # --- 風（間引き） ---
        ax.barbs(
            da.lon.values[::2],
            da.lat.values[::2],
            U_ms[::2, ::2],
            V_ms[::2, ::2],
            length=5,
            transform=proj,
            zorder=4
        )

        '''
        # --- 湿球温度（実線） ---
        cs = ax.contour(
            da.lon, da.lat, Tw_C,
            levels=np.arange(-30, 31, 1),
            colors="black",
            linewidths=0.7,
            linestyles="solid",
            transform=proj,
            zorder=3
        )
        '''

        # +1℃ 太線
        ax.contour(
            da.lon, da.lat, Tw_C,
            levels=[1],
            colors="yellow",
            linewidths=2.0,
            linestyles="solid",
            transform=proj,
            zorder=4
        )

        ax.clabel(cs, fmt="%.0f", fontsize=8)

        ax.set_title(f"{t:%Y-%m-%d %HZ} {lev}hPa")
        plt.colorbar(cf, ax=ax, label="Temperature (°C)")

        # ========================
        # 保存
        # ========================
        outname = f"{OUTDIR}/{t:%Y%m%d%H}_{lev}.png"
        plt.savefig(outname, dpi=150, bbox_inches="tight")
        plt.close()

        print("saved:", outname)
