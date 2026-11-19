#!/usr/bin/env python3
"""
ERA5(Google ARCO-ERA5 Zarr)の海面更正気圧から低気圧を検出・追跡し、
爆弾低気圧と南岸低気圧のリストをCSVで出力する。

  pip install "zarr>=3" gcsfs dask xarray scipy pandas scikit-image trackpy

任意に決めている値は下の4つだけ。それ以外は定義(気象庁の爆弾低気圧の定義など)で決まる。
"""
import numpy as np
import pandas as pd
import xarray as xr
import trackpy as tp
from scipy import ndimage
from skimage.morphology import h_minima

# ============ 任意に決めている値(これだけ) ============
GRID_DEG = 1.0          # 解析格子 [度]
H_MIN_HPA = 0.5         # 低気圧とみなす最小の深さ [hPa] (天気図の等圧線間隔4hPaに相当)
MAX_SPEED_KMH = 100.0   # 低気圧の最大移動速度 [km/h] (6時間後の対応付けの探索半径)
NANGAN_MAX_KM = 500.0   # 南岸低気圧: 東京の経度を通過するとき、東京より南に何km以内か
# =====================================================

# 以下は定数(データ・定義で決まるもの)
URL = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
START, END = "2025-07-01 00:00", "2026-06-30 18:00"
STEP_H = 3                                  # 6時間ごと
LAT_N, LAT_S, LON_W, LON_E = 50, 20, 120, 150
TOKYO_LAT, TOKYO_LON = 36, 140
R_EARTH = 6371.0
KM_PER_DEG = np.pi * R_EARTH / 180


def load_mslp():
    ds = xr.open_zarr(URL, storage_options={"token": "anon"})
    stride = int(round(GRID_DEG / 0.25))
    da = (ds["mean_sea_level_pressure"]
          .sel(time=slice(START, END))
          .isel(time=slice(None, None, STEP_H))
          .sel(latitude=slice(LAT_N, LAT_S), longitude=slice(LON_W, LON_E))
          .isel(latitude=slice(None, None, stride), longitude=slice(None, None, stride)))
    print(f"loading {dict(da.sizes)} ... (数GBの読み込み)")
    return (da / 100.0).compute()  # Pa -> hPa


def detect(slp, lat, lon):
    """深さH_MIN_HPA以上の極小(h-minima)を低気圧中心とする。領域の縁は除く。"""
    z = np.round(slp * 10).astype(np.int32)                       # 0.1hPa単位
    mask = h_minima(z, int(round(H_MIN_HPA * 10)), footprint=np.ones((3, 3)))
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        return []
    pos = ndimage.minimum_position(z, lab, index=range(1, n + 1))
    ny, nx = slp.shape
    return [(lat[i], lon[j], slp[i, j]) for i, j in pos
            if 0 < i < ny - 1 and 0 < j < nx - 1]


def build_tracks(da):
    lat, lon = da["latitude"].to_numpy(), da["longitude"].to_numpy()
    times = pd.to_datetime(da["time"].to_numpy())
    rows = []
    for k, t in enumerate(times):
        for la, lo, p in detect(da.isel(time=k).to_numpy(), lat, lon):
            rows.append(dict(frame=k, time=t, lat=float(la), lon=float(lo), p=float(p)))
    df = pd.DataFrame(rows)
    # 球面上の3次元直交座標(km)で距離を測る(投影による任意性を避ける)
    phi, lam = np.radians(df["lat"]), np.radians(df["lon"])
    df["x"] = R_EARTH * np.cos(phi) * np.cos(lam)
    df["y"] = R_EARTH * np.cos(phi) * np.sin(lam)
    df["z"] = R_EARTH * np.sin(phi)
    tp.quiet()
    tr = tp.link(df, search_range=MAX_SPEED_KMH * STEP_H,
                 pos_columns=["x", "y", "z"], t_column="frame")
    tr = tr.rename(columns={"particle": "track_id"})
    return tr.sort_values(["track_id", "time"]).reset_index(drop=True)


def jst(t):
    return t + pd.Timedelta(hours=9)


def bomb_table(tracks):
    """気象庁の定義: 24時間で 24hPa x sin(φ)/sin(60°) 以上低下 (φは24時間の平均緯度)"""
    rows, d24 = [], pd.Timedelta(hours=24)
    for tid, g in tracks.groupby("track_id"):
        g = g.set_index("time")
        p0 = g["p"].reindex(g.index - d24).to_numpy()
        la0 = g["lat"].reindex(g.index - d24).to_numpy()
        dp = p0 - g["p"].to_numpy()
        phi = np.radians((la0 + g["lat"].to_numpy()) / 2)
        with np.errstate(invalid="ignore", divide="ignore"):
            idx = dp / 24.0 * np.sin(np.radians(60)) / np.sin(phi)   # 1以上で爆弾低気圧
        if not np.isfinite(idx).any():
            continue
        k = int(np.nanargmax(idx))
        if idx[k] < 1.0:
            continue
        t_end = g.index[k]
        rows.append(dict(
            track_id=tid, start_utc=g.index[0], end_utc=g.index[-1],
            max_deepening_end_utc=t_end, max_deepening_end_jst=jst(t_end),
            dp_24h_hPa=round(float(dp[k]), 1), bomb_index=round(float(idx[k]), 2),
            lat_at_end=round(float(g["lat"].iloc[k]), 2),
            lon_at_end=round(float(g["lon"].iloc[k]), 2),
            min_p_hPa=round(float(g["p"].min()), 1), min_p_time_utc=g["p"].idxmin()))
    return pd.DataFrame(rows).sort_values("max_deepening_end_utc") if rows else pd.DataFrame()


def nangan_table(tracks):
    """東京の経度を西から東へ通過し、その地点が東京より南でNANGAN_MAX_KM以内の低気圧"""
    rows = []
    for tid, g in tracks.groupby("track_id"):
        g = g.set_index("time")
        t, lo, la, p = g.index.to_list(), g["lon"].to_numpy(), g["lat"].to_numpy(), g["p"].to_numpy()
        for i in range(len(g) - 1):
            if lo[i] < TOKYO_LON <= lo[i + 1]:
                w = (TOKYO_LON - lo[i]) / (lo[i + 1] - lo[i])
                lat_x = la[i] + (la[i + 1] - la[i]) * w
                south_km = (TOKYO_LAT - lat_x) * KM_PER_DEG
                if 0 < south_km <= NANGAN_MAX_KM:
                    t_x = t[i] + (t[i + 1] - t[i]) * w
                    rows.append(dict(
                        track_id=tid, start_utc=g.index[0], end_utc=g.index[-1],
                        pass_time_jst=jst(t_x).floor("h"),
                        lat_at_tokyo_lon=round(float(lat_x), 2),
                        km_south_of_tokyo=round(float(south_km)),
                        p_at_tokyo_lon_hPa=round(float(p[i] + (p[i + 1] - p[i]) * w), 1),
                        min_p_hPa=round(float(g["p"].min()), 1)))
                break
    return pd.DataFrame(rows).sort_values("pass_time_jst") if rows else pd.DataFrame()


def main():
    da = load_mslp()
    tracks = build_tracks(da)
    print(f"{tracks['track_id'].nunique()} tracks")
    tracks.drop(columns=["x", "y", "z"]).to_csv("cyclone_tracks.csv", index=False)
    bomb = bomb_table(tracks)
    bomb.to_csv("bomb_cyclones.csv", index=False)
    print(f"爆弾低気圧: {len(bomb)} 件 -> bomb_cyclones.csv")
    nk = nangan_table(tracks)
    nk.to_csv("nangan_cyclones.csv", index=False)
    print(f"南岸低気圧: {len(nk)} 件 -> nangan_cyclones.csv")


if __name__ == "__main__":
    main()
