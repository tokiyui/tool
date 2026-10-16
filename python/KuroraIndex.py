import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import netCDF4
import pandas as pd
from metpy.units import units
import metpy.calc as mpcalc
from matplotlib.colors import ListedColormap, BoundaryNorm
import os
import requests

# =========================
# 日付指定(YYYYMMDDHH JST)
# =========================
date = "2025053112"

yyyy = date[:4]
mm = date[4:6]
dd = date[6:8]
hh = date[8:10]

# =========================
# 時刻設定
# =========================
base_time_jst = pd.Timestamp(f"{yyyy}-{mm}-{dd} {hh}:00", tz="Asia/Tokyo")
base_time_utc = base_time_jst.tz_convert("UTC").tz_localize(None)

filename = f"{mm}{dd}.nc"

url = f"https://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/netcdf/MSM-P/{yyyy}/{filename}"

if not os.path.exists(filename):

    print("Downloading:", url)

    r = requests.get(url, verify=False, stream=True)

    if r.status_code != 200:
        raise RuntimeError("Download failed")

    with open(filename, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    print("Saved:", filename)

# =========================
# データ読み込み
# =========================
ds = xr.open_dataset(filename, engine="netcdf4")

T = ds["temp"].sel(time=base_time_utc, method="nearest").values * units.kelvin
RH = ds["rh"].sel(time=base_time_utc, method="nearest").values * units.percent
p = (ds["p"].values * 100.0) * units.pascal

lat = ds["lat"].values
lon = ds["lon"].values

ny, nx = lat.size, lon.size

result = np.full((ny, nx), np.nan)
diffmax_map = np.full((ny, nx), np.nan)

count = {}

# =========================
# 各格子計算
# =========================
for j in range(ny):
    for i in range(nx):

        Tcol = T[:, j, i]
        RHcol = RH[:, j, i]

        if np.any(np.isnan(Tcol)):
            continue

        tempC = Tcol.to("degC").m

        if tempC.min() > -10 or tempC.max() < -20:
            continue

        order = np.argsort(tempC)
        
        T_s = Tcol[order]
        RH_s = RHcol[order]
        p_s = p[order]
        tempC_s = tempC[order]

        Td_s = mpcalc.dewpoint_from_relative_humidity(T_s, RH_s)
        thetae_s = mpcalc.equivalent_potential_temperature(p_s, T_s, Td_s)
        thetaes_s = mpcalc.saturation_equivalent_potential_temperature(p_s, T_s)

        mask_m10 = tempC_s > -10
        if not np.any(mask_m10):
            continue

        thetae_max = np.nanmax(thetae_s.m[mask_m10])
        idx_thetae_max = np.nanargmax(np.where(mask_m10, thetae_s.m, -np.inf))

        count[idx_thetae_max] = count.get(idx_thetae_max, 0) + 1

        temp_thetae_max = tempC_s[idx_thetae_max]
        thetaes_m20 = np.interp(-20, tempC_s, thetaes_s.m)

        layer_mask = ((tempC_s <= temp_thetae_max) & (tempC_s >= -20))
        if not np.any(layer_mask):
            continue

        diff_theta = thetaes_s.m[layer_mask] - thetae_s.m[layer_mask]
        diff_max = np.nanmax(diff_theta)

        result[j, i] = thetae_max - thetaes_m20 - diff_max 

# =========================
# 雷データ
# =========================

th_time_jst = base_time_jst + pd.Timedelta(hours=1)

url = (
    "https://weather.kakutyoutakaki.com/thander/get_th_json.php"
    f"?year={th_time_jst.year}"
    f"&month={th_time_jst.month}"
    f"&day={th_time_jst.day}"
    f"&hour={th_time_jst.hour}"
    f"&min=00&kikan=1"
)

th_json = requests.get(url).json()

lons_th = []
lats_th = []

for key in th_json["maindata"]:
    for feat in th_json["maindata"][key]["features"]:
        lon_pt, lat_pt = feat["geometry"]["coordinates"]
        lons_th.append(lon_pt)
        lats_th.append(lat_pt)

# =========================
# 描画
# =========================

proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(9,7))
ax = plt.axes(projection=proj)
ax.set_extent([135,142,33,38], crs=proj)

levels = [-1000, -3, 0, 1000]
cmap = ListedColormap(["white", "yellow", "red"])
norm = BoundaryNorm(levels, cmap.N)
pcm = ax.contourf(lon, lat, result, levels=levels, cmap=cmap, norm=norm, transform=proj)

ax.scatter(
    lons_th,
    lats_th,
    marker="x",
    s=40,
    linewidths=1.2,
    color="black",
    transform=proj,
    zorder=10
)

ax.coastlines(resolution="10m")
ax.add_feature(cfeature.BORDERS, linewidth=0.5)
ax.gridlines(draw_labels=True)

cb = plt.colorbar(pcm, ax=ax, shrink=0.8)
cb.set_label("θe instability index")

ax.set_title(f"{base_time_jst.strftime('%Y/%m/%d %H:%M JST')}")

plt.show()
print(count)
