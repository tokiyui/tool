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
from scipy.ndimage import gaussian_filter
import matplotlib.colors as mcolors

# ========================
# 設定
# ========================
START  = "2022-01-05 12:00"
END    = "2022-01-07 12:00"
EXTENT = [136, 142, 33, 38]
OUTDIR = "Data"
os.makedirs(OUTDIR, exist_ok=True)
 
LON_MIN, LON_MAX, LAT_MIN, LAT_MAX = EXTENT
 
# ========================
# 時刻列
# ========================
start = dt.datetime.fromisoformat(START)
end   = dt.datetime.fromisoformat(END)
 
times = []
t = start
while t <= end:
    times.append(t)
    t += dt.timedelta(hours=3)
 
dates = sorted({t.strftime("%Y/%m%d") for t in times})
 
# ========================
# MSM-S surface
# ========================
base_sfc = "https://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/netcdf/MSM-S"
files_sfc = []
 
for d in dates:
    y, md = d.split("/")
    fn = f"S2-{md}.nc"
    url = f"{base_sfc}/{y}/{md}.nc"
    if not os.path.exists(fn):
        r = requests.get(url)
        r.raise_for_status()
        open(fn, "wb").write(r.content)
    files_sfc.append(fn)
 
# combine="nested" + data_vars="minimal" で time と ref_time を壊さない
ds_sfc = xr.open_mfdataset(
    files_sfc,
    combine="nested",
    concat_dim="time",
    data_vars="minimal",
)
 
# ref_time が残っている場合は drop して time だけに
if "ref_time" in ds_sfc.dims:
    ds_sfc = ds_sfc.mean(dim="ref_time")
 
# ========================
# MSM-S r1h
# ========================
base_r1h = "https://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/netcdf/MSM-S/r1h"
files_r1h = []
 
for d in dates:
    y, md = d.split("/")
    fn = f"R2-{md}.nc"
    url = f"{base_r1h}/{y}/{md}.nc"
    if not os.path.exists(fn):
        r = requests.get(url)
        r.raise_for_status()
        open(fn, "wb").write(r.content)
    files_r1h.append(fn)
 
ds_r1h = xr.open_mfdataset(
    files_r1h,
    combine="by_coords",
    join="outer"
)
 
# ========================
# 描画設定
# ========================
temp_levels = np.array([-6, -3, -2, -1, 0, 1, 2, 3])
proj = ccrs.PlateCarree()
pref = cfeature.NaturalEarthFeature(
    "cultural", "admin_1_states_provinces_lines", "10m", facecolor="none"
)
 
# ========================
# メインループ
# ========================
for t in times:
 
    # --- MSM-S surface ---
    da = (
        ds_sfc
        .sel(time=t, method="nearest")
        .sel(lon=slice(LON_MIN, LON_MAX),
             lat=slice(LAT_MAX, LAT_MIN))
        .squeeze()
    )
 
    T  = da["temp"].metpy.quantify()
    RH = da["rh"].metpy.quantify()
    U  = da["u"].metpy.quantify()
    V  = da["v"].metpy.quantify()
    P  = da["psea"].metpy.quantify()
 
    Td = mpcalc.dewpoint_from_relative_humidity(T, RH)
    Tw = mpcalc.wet_bulb_temperature(P, T, Td)
 
    T_C  = T.metpy.convert_units("degC").values
    Tw_C = Tw.metpy.convert_units("degC").values
    U_ms = U.metpy.convert_units("m/s").values
    V_ms = V.metpy.convert_units("m/s").values
    P_hPa= P.metpy.convert_units("hPa").values
 
    # --- 描画 ---
 
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=proj)
    ax.set_extent(EXTENT)
    ax.add_feature(pref, linewidth=0.6)
    ax.coastlines("10m", linewidth=0.8)

    norm = mcolors.TwoSlopeNorm(
        vmin=min(temp_levels),
        vcenter=0.0,
        vmax=max(temp_levels)
    )

    cf = ax.contourf(
        da.lon, da.lat, T_C,
        levels=temp_levels,
        cmap="coolwarm",
        norm=norm,
        extend="both",
        transform=proj,
        zorder=1
    )
 
    ax.contour(
        da.lon, da.lat, Tw_C,
        levels=[1], colors="yellow", linewidths=2
    )
 
    ax.barbs(
        da.lon.values[::4], da.lat.values[::4],
        U_ms[::4, ::4]*2, V_ms[::4, ::4]*2,
        length=5
    )
 
    plt.colorbar(cf, ax=ax, label="Temperature (°C)")
    ax.set_title(f"{t:%Y-%m-%d %HZ} Surface")
    plt.savefig(f"{OUTDIR}/{t:%Y%m%d%H}_surf.png", dpi=150, bbox_inches="tight")
    plt.close()
 
    # --- MSM-S r1h ---
    da_p = (
        ds_r1h
        .sel(time=t, method="nearest")
        .sel(lon=slice(LON_MIN, LON_MAX),
             lat=slice(LAT_MAX, LAT_MIN))
        .squeeze()
    )
 
    PR = da_p["r1h"].values
 
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=proj)
    ax.set_extent(EXTENT)
    ax.add_feature(pref, linewidth=0.6)
    ax.coastlines("10m", linewidth=0.8)
 
    levels = [0, 1, 3, 5, 10, 15, 20]
    norm = mcolors.BoundaryNorm(levels, ncolors=plt.get_cmap("Blues").N)

    cf = ax.contourf(
        da_p.lon,
        da_p.lat,
        PR - 0.01,
        levels=levels,
        cmap="Blues",
        norm=norm,
        extend="max"
    )
 
    ax.contour(
        da.lon, da.lat, gaussian_filter(P_hPa, sigma=2.0),
        levels=np.arange(960, 1040, 1),
        colors="black", linewidths=2
    )
 
    ax.barbs(
        da.lon.values[::4], da.lat.values[::4],
        U_ms[::4, ::4]*2, V_ms[::4, ::4]*2,
        length=5
    )

    cbar = plt.colorbar(cf, ax=ax, label="Precipitation(mm/1h)")
    ax.set_title(f"{t:%Y-%m-%d %HZ} Precip")
    plt.savefig(f"{OUTDIR}/{t:%Y%m%d%H}_pres.png", dpi=150, bbox_inches="tight")
    plt.close()
 
    print("saved:", t)
