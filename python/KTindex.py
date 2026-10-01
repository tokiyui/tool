#当日MSM00によるKT-indexの予想図
import os
import requests
import pygrib
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import BoundaryNorm
from metpy.units import units
import metpy.calc as mpcalc
from cartopy.io import shapereader

# 初期時刻
year=2026
month=8
day=13
hour=0

filename=f"Z__C_RJTD_{year:04d}{month:02d}{day:02d}{hour:02d}0000_MSM_GPV_Rjp_L-pall_FH00-15_grib2.bin"
url=f"http://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/original/{year:04d}/{month:02d}/{day:02d}/{filename}"

if not os.path.exists(filename):
    r=requests.get(url,stream=True)
    r.raise_for_status()
    with open(filename,"wb") as f:
        for chunk in r.iter_content(1024*1024):
            if chunk:
                f.write(chunk)

# TOPO.MSM_5K
topo_file="TOPO.MSM_5K"
topo_url="http://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/original/etc/gpv_topo-merged/TOPO.MSM_5K"

if not os.path.exists(topo_file):
    r=requests.get(topo_url,stream=True)
    r.raise_for_status()
    with open(topo_file,"wb") as f:
        for chunk in r.iter_content(1024*1024):
            if chunk:
                f.write(chunk)

topo=np.fromfile(topo_file,dtype=">f4").reshape(505,481)

# カラーマップ
bounds=np.arange(0,7)
base=plt.get_cmap("turbo")
cmap=plt.cm.colors.ListedColormap(base(np.linspace(0.2,0.9,7)))
cmap.set_under(base(0.05))
cmap.set_over(base(1.0))
norm=BoundaryNorm(bounds,cmap.N)

forecast_hours=[0,3,6,9,12,15]
grbs=pygrib.open(filename)

# 気圧面格子とTOPO.MSM_5Kを対応
msg=grbs.select(name="Temperature",typeOfLevel="isobaricInhPa",level=500,forecastTime=0)[0]
lat0,lon0=msg.latlons()
topo_y=np.rint((47.6-lat0)/0.05).astype(int)
topo_x=np.rint((lon0-120.0)/0.0625).astype(int)
elevation=topo[topo_y,topo_x]
terrain_mask=elevation>=300

states=shapereader.natural_earth(
    resolution="10m",
    category="cultural",
    name="admin_1_states_provinces_lines"
)
prefectures=list(shapereader.Reader(states).geometries())

fig,axes=plt.subplots(
    2,3,
    figsize=(16,12),
    subplot_kw={"projection":ccrs.PlateCarree()}
)
axes=axes.ravel()

for ax,ft in zip(axes,forecast_hours):

    Plow=950
    Pmid=700
    Pupr=500

    Tlow=grbs.select(
        name="Temperature",
        typeOfLevel="isobaricInhPa",
        level=Plow,
        forecastTime=ft
    )[0].values*units.kelvin

    Tmid=grbs.select(
        name="Temperature",
        typeOfLevel="isobaricInhPa",
        level=Pmid,
        forecastTime=ft
    )[0].values*units.kelvin

    msg=grbs.select(
        name="Temperature",
        typeOfLevel="isobaricInhPa",
        level=Pupr,
        forecastTime=ft
    )[0]

    lat,lon=msg.latlons()
    Tupr=msg.values*units.kelvin

    RHlow=grbs.select(
        name="Relative humidity",
        typeOfLevel="isobaricInhPa",
        level=Plow,
        forecastTime=ft
    )[0].values*units.percent

    RHmid=grbs.select(
        name="Relative humidity",
        typeOfLevel="isobaricInhPa",
        level=Pmid,
        forecastTime=ft
    )[0].values*units.percent

    Tdlow=mpcalc.dewpoint_from_relative_humidity(Tlow,RHlow)
    Tdmid=mpcalc.dewpoint_from_relative_humidity(Tmid,RHmid)

    thetaelow=mpcalc.equivalent_potential_temperature(
        Plow*units.hPa,Tlow,Tdlow
    ).m

    thetaemid=mpcalc.equivalent_potential_temperature(
        Pmid*units.hPa,Tmid,Tdmid
    ).m

    thetaesmid=mpcalc.saturation_equivalent_potential_temperature(
        Pmid*units.hPa,Tmid
    ).m

    thetaesupr=mpcalc.saturation_equivalent_potential_temperature(
        Pupr*units.hPa,Tupr
    ).m

    field=thetaelow-thetaesupr-(thetaesmid-thetaemid)

    cf=ax.contourf(
        lon,lat,field,
        levels=bounds,
        cmap=cmap,
        norm=norm,
        extend="both",
        transform=ccrs.PlateCarree()
    )

    # 標高300m以上をグレー表示
    ax.contourf(
        lon,lat,terrain_mask,
        levels=[0.5,1.5],
        colors=["gray"],
        transform=ccrs.PlateCarree()
    )

    ax.set_extent([138,141,34.5,37.5])
    ax.coastlines("10m",linewidth=0.5)
    ax.add_feature(cfeature.BORDERS,linewidth=0.3)

    ax.add_geometries(
        prefectures,
        ccrs.PlateCarree(),
        edgecolor="black",
        facecolor="none",
        linewidth=0.25
    )

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"FT={ft:02d}",fontsize=12,pad=2)

fig.suptitle(
    f"Init {year:04d}/{month:02d}/{day:02d} {hour:02d} UTC",
    fontsize=18
)

fig.subplots_adjust(
    left=0.03,
    right=0.97,
    bottom=0.16,
    top=0.90,
    wspace=0.03,
    hspace=0.18
)

cbar=fig.colorbar(
    cf,
    ax=axes,
    orientation="horizontal",
    fraction=0.05,
    pad=0.08,
    aspect=50,
    ticks=bounds
)
cbar.set_label("K",fontsize=12)

plt.savefig(
    f"{year:04d}{month:02d}{day:02d}{hour:02d}_all.png",
    dpi=200,
    bbox_inches="tight"
)

plt.show()

grbs.close()
