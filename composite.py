import time
from datetime import datetime
import numpy as np
import pandas as pd
import xarray as xr
import dask
from dask.diagnostics import ProgressBar
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# ============================================================
# 設定
# ============================================================

ZARR = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"

LAT = slice(60, 15)
LON = slice(100, 180)

CLIM_YEARS = range(2011, 2026)
CLIM_OFFSETS = (-3, 0, 3)

ALPHA = 0.05
USE_FDR = False
N_THREADS = 32

# Trueなら、読み込み済みデータをグループごとに検定・作図
# Falseでも全グループを処理するが、全グループの結果を出力する
dask.config.set(scheduler="threads", num_workers=N_THREADS)

# ============================================================
# 4グループの日時（すべて00 UTC）
# ============================================================

GROUP_DATES = {
    "yui": """
    20260906 20260830 20260814 20260811 20260809 20260705
    20260620 20260524 20260523 20260211 20260208 20260207
    20251220 20251214 20251124 20251116 20251115 20251019
    20250920 20250915 20250816 20250719 20250629 20250511
    20250406 20250405 20250330 20250125 20250111 20241228
    20241117 20241110 20241014 20240922 20240915 20240815
    20240518 20240420 20240310 20240309 20240224 20231223
    20231216 20231123 20231029 20231014 20230910 20230717
    20230520 20230503 20230429 20230401 20230312 20221228
    20221218 20221210 20221202 20220821 20220313 20211211
    20210704 20200215 20200103 20191214 20191124 20190815
    20190519 20190518 20190504 20190503 20190331 20190323
    20190309 20181222 20180909 20180815 20180725 20180708
    20180602 20180512 20180415 20180408 20180318 20180225
    20171009 20170815 20170812 20170730 20170726 20170226
    20161120 20160820 20160814 20160710 20160709 20160619
    20150906 20150705 20150329 20150325 20140920 20140914
    20140622 20140215 20140209 20140208 20130526 20130519
    20130506 20120815 20120714 20111119 20101116 20101015
    20091103
    """.split(),

    "ino": """
    20251130 20251129 20250706 20241103 20241102 20240204
    20231202 20231029 20231028 20221001 20211205 20211017
    20190629 20190628 20180707 20180701 20171202 20170715
    20170701 20161120 20161105 20161009 20160610 20160605
    20160604 20160110 20151226 20151212 20151202 20151107
    20151031 20151025 20151018 20151011 20150801 20150412
    20141207 20141129 20141122 20141102 20140510
    """.split(),

    "kao": """
    20260504 20260321 20260301 20260214 20250809 20250803
    20250503 20241208 20241110 20241103 20241020 20240825
    20240824 20240811 20240810 20240720 20240623 20240503
    20240114 20231225 20230924 20230902 20230223 20221126
    20220925 20220904 20220806 20220515 20220327 20210220
    20200224 20191228 20191221 20191103 20190810 20190601
    20190526 20190519 20190324 20181229 20181222 20181209
    20181103 20180804 20180429 20180428 20180421 20120805
    20101230 20101125 20100529
    """.split(),

    "mik": """
    20260816 20260614 20260517 20260510 20260419 20260110
    20251011 20241207 20240811 20240715 20240421 20240317
    20240113 20231111 20231022 20231015 20230521 20230219
    20221015 20221008 20220416 20210321 20200105 20191104
    20191005 20190811 20190804 20190728 20190727 20190210
    20190203 20190202 20190126 20181020 20180930 20180917
    20180902 20180819 20180818 20180617 20180310 20180304
    20180303 20180224 20180217 20171126 20171125 20171118
    20171112 20171111 20171103 20171014 20170812 20170624
    20170617 20170528 20170527 20170507 20170506 20170504
    20170503 20161203 20161126 20161120 20161119 20161112
    20161103 20161023 20161022 20161016 20161015 20161010
    20160903 20160109
    """.split(),
}

# ============================================================
# 共通関数
# ============================================================

START_TIME = time.time()


def log(message):
    elapsed = time.time() - START_TIME
    print(f"[経過 {elapsed:8.1f} 秒] {message}", flush=True)


def parse(s):
    return pd.Timestamp(
        f"{s[:4]}-{s[4:6]}-{s[6:8]} 00:00:00"
    )


def window_keys(t):
    base = t.normalize()
    return [
        (
            (base + pd.Timedelta(days=k)).month,
            (base + pd.Timedelta(days=k)).day,
            t.hour,
        )
        for k in CLIM_OFFSETS
    ]


def key_indices(key, tidx):
    m, d, h = key
    ts = []

    for y in CLIM_YEARS:
        try:
            ts.append(pd.Timestamp(year=y, month=m, day=d, hour=h))
        except ValueError:
            # 2月29日など、存在しない日付
            continue

    idx = tidx.get_indexer(ts)
    return idx[idx >= 0]


def fdr_mask(p, alpha):
    flat = p.ravel()
    ok = np.isfinite(flat)
    pv = flat[ok]

    order = np.argsort(pv)
    passed = pv[order] <= (
        alpha * np.arange(1, len(pv) + 1) / len(pv)
    )

    out = np.zeros(len(pv), dtype=bool)

    if passed.any():
        last = np.max(np.where(passed)[0])
        out[order[:last + 1]] = True

    res = np.zeros_like(flat, dtype=bool)
    res[ok] = out
    return res.reshape(p.shape)


# ============================================================
# データ読み込み
# ============================================================

def load_all(ds, valid_by_group, tidx):
    # 全グループの日時をまとめ、重複を除去
    all_dates = sorted({
        s
        for dates in valid_by_group.values()
        for s in dates
    })

    log("=" * 65)
    log("データ読み込み開始")
    log(f"グループ数: {len(valid_by_group)}")
    log(f"実況データのユニーク日時数: {len(all_dates)}")
    for name, dates in valid_by_group.items():
        log(f"  {name}: {len(dates)} 件")

    vars_ = {
        "z500": (
            ds["geopotential"]
            .sel(level=500, latitude=LAT, longitude=LON)
            / 9.80665
        ),
        "msl": (
            ds["mean_sea_level_pressure"]
            .sel(latitude=LAT, longitude=LON)
            / 100.0
        ),
    }

    # --------------------------------------------------------
    # 1. 実況データ
    # --------------------------------------------------------
    log("[1/3] 実況データの読み込みを開始")

    t0 = time.time()

    obs_tasks = {}
    for i, s in enumerate(all_dates, 1):
        log(f"  実況データをタスク登録: {i}/{len(all_dates)} {s}")

        idx = tidx.get_loc(parse(s))

        for name, da in vars_.items():
            obs_tasks[(name, s)] = da.isel(time=idx)

    log(f"実況データの計算開始: {len(obs_tasks)} 枚")

    with ProgressBar():
        obs = dask.compute(obs_tasks)[0]

    log(
        f"[1/3] 実況データ完了: {len(obs)} 枚、"
        f"{time.time() - t0:.1f} 秒"
    )

    # --------------------------------------------------------
    # 2. 気候値
    # --------------------------------------------------------
    log("[2/3] 気候値の読み込みを開始")

    keys = sorted({
        k
        for s in all_dates
        for k in window_keys(parse(s))
    })

    key_idx = {
        k: key_indices(k, tidx)
        for k in keys
    }

    n_reads = sum(
        len(key_idx[k]) for k in keys
    ) * len(vars_)

    log(f"気候値キー数: {len(keys)}")
    log(f"気候値の読み込み対象: 最大 {n_reads} 枚")

    clim_tasks = {}

    for i, k in enumerate(keys, 1):
        m, d, h = k
        log(
            f"  気候値タスク登録: {i}/{len(keys)} "
            f"{m:02d}-{d:02d} {h:02d}UTC"
        )

        idx = key_idx[k]

        for name, da in vars_.items():
            if len(idx) == 0:
                log(f"  WARNING: 気候値データなし: {name}, {k}")
                continue

            clim_tasks[(name, k)] = (
                da.isel(time=idx).mean("time")
            )

    log(f"気候値の計算開始: {len(clim_tasks)} 個")

    with ProgressBar():
        clim = dask.compute(clim_tasks)[0]

    log(
        f"[2/3] 気候値完了: {len(clim)} 個、"
        f"累計 {time.time() - START_TIME:.1f} 秒"
    )

    return obs, clim


# ============================================================
# 偏差計算
# ============================================================

def anomalies(obs, clim, name, dates):
    out = []

    for i, s in enumerate(dates, 1):
        log(
            f"  偏差計算 {name}: {i}/{len(dates)} "
            f"日時={s}"
        )

        keys = window_keys(parse(s))
        missing = [
            k for k in keys
            if (name, k) not in clim
        ]

        if missing:
            log(
                f"  WARNING: 気候値不足のためスキップ: "
                f"{s}, keys={missing}"
            )
            continue

        c = sum(
            clim[(name, k)] for k in keys
        ) / len(keys)

        anomaly = (
            obs[(name, s)] - c
        ).drop_vars("time", errors="ignore")

        out.append(anomaly)

    return out


# ============================================================
# 合成平均・有意性検定
# ============================================================

def composite_test(anoms, group_name, var_name):
    if len(anoms) < 3:
        raise RuntimeError(
            f"{group_name}/{var_name}: "
            f"検定に使える日時が3件未満です (N={len(anoms)})"
        )

    log(
        f"  {group_name}/{var_name}: "
        f"合成計算開始 (N={len(anoms)})"
    )

    arr = xr.concat(anoms, dim="case")

    mean = arr.mean("case")

    log(
        f"  {group_name}/{var_name}: "
        "t検定を実行中（全格子点）"
    )

    _, p = stats.ttest_1samp(
        arr.values,
        0.0,
        axis=0,
        nan_policy="omit",
    )

    sig = (
        fdr_mask(p, ALPHA)
        if USE_FDR
        else (p < ALPHA)
    )

    sig_da = xr.DataArray(
        sig,
        coords=mean.coords,
        dims=mean.dims,
    )

    log(
        f"  {group_name}/{var_name}: "
        f"合成・検定完了、有意格子点数={int(sig.sum())}"
    )

    return mean, sig_da


# ============================================================
# 作図
# ============================================================

def plot_anom(anom, sig, title, fname, levels, label):
    log(f"  作図開始: {fname}")

    fig = plt.figure(figsize=(8, 5.5))
    ax = plt.axes(projection=ccrs.PlateCarree())

    ax.set_extent(
        [100, 180, 15, 60],
        crs=ccrs.PlateCarree(),
    )

    cf = ax.contourf(
        anom.longitude,
        anom.latitude,
        anom,
        levels=levels,
        cmap="RdBu_r",
        extend="both",
        transform=ccrs.PlateCarree(),
    )

    cs = ax.contour(
        anom.longitude,
        anom.latitude,
        anom,
        levels=levels[::2],
        colors="k",
        linewidths=0.4,
        transform=ccrs.PlateCarree(),
    )

    ax.clabel(cs, fontsize=7, fmt="%g")

    if bool(sig.any()):
        ax.contourf(
            sig.longitude,
            sig.latitude,
            sig.astype(float),
            levels=[0.5, 1.5],
            colors="none",
            hatches=["...."],
            transform=ccrs.PlateCarree(),
        )

    ax.coastlines(linewidth=0.7)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3)

    gl = ax.gridlines(
        draw_labels=True,
        linewidth=0.3,
        color="gray",
        alpha=0.6,
    )
    gl.top_labels = False
    gl.right_labels = False

    plt.colorbar(
        cf,
        ax=ax,
        orientation="horizontal",
        pad=0.08,
        shrink=0.85,
        label=label,
    )

    ax.set_title(title, fontsize=10)

    fig.savefig(
        fname,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

    log(f"  作図完了: {fname}")


# ============================================================
# メイン処理
# ============================================================

def main():
    log("ERA5データセットを開いています")

    ds = xr.open_zarr(
        ZARR,
        chunks={},
        storage_options={"token": "anon"},
    )

    tidx = ds.get_index("time")

    log(f"ERA5期間: {tidx.min()} ～ {tidx.max()}")
    log(f"ERA5時刻数: {len(tidx)}")

    log(
        "geopotential chunksizes: "
        f"{dict(ds['geopotential'].chunksizes)}"
    )

    # グループごとに有効日時を判定
    valid_by_group = {}
    skipped_by_group = {}

    log("各グループの日時を確認します")

    for group, dates in GROUP_DATES.items():
        valid = []
        skipped = []

        for s in dates:
            try:
                t = parse(s)
            except (ValueError, TypeError):
                skipped.append((s, "日付形式不正"))
                continue

            if t in tidx:
                valid.append(s)
            else:
                skipped.append((s, "ERA5データなし"))

        # 重複日時を除去（順序は維持）
        valid = list(dict.fromkeys(valid))

        valid_by_group[group] = valid
        skipped_by_group[group] = skipped

        log(
            f"グループ {group}: "
            f"入力 {len(dates)} 件 / "
            f"有効 {len(valid)} 件 / "
            f"スキップ {len(skipped)} 件"
        )

        for s, reason in skipped:
            log(f"  skip: {group} {s} ({reason})")

        if len(valid) < 3:
            log(
                f"WARNING: {group} は有効日時が3件未満です。"
                "このグループの検定は実行できません。"
            )

    if not any(valid_by_group.values()):
        raise RuntimeError("全グループで有効な日時がありません")

    # 全グループで共通する実況・気候値を一度だけ読み込む
    obs, clim = load_all(ds, valid_by_group, tidx)

    # --------------------------------------------------------
    # グループ別に完全独立して解析
    # --------------------------------------------------------
    log("=" * 65)
    log("グループ別の合成解析を開始")

    for group, dates in valid_by_group.items():
        log("-" * 65)
        log(f"グループ {group}: 解析開始")
        log(f"使用予定日時数: {len(dates)}")

        if len(dates) < 3:
            log(f"グループ {group}: 日時数不足のためスキップ")
            continue

        for var_name in ("z500", "msl"):
            log(f"{group}: {var_name} の偏差を計算")

            anoms = anomalies(
                obs,
                clim,
                var_name,
                dates,
            )

            if len(anoms) < 3:
                log(
                    f"WARNING: {group}/{var_name}: "
                    f"偏差計算後のデータ数が不足 ({len(anoms)})"
                )
                continue

            mean, sig = composite_test(
                anoms,
                group,
                var_name,
            )

            n = len(anoms)

            sub = (
                f"clim {CLIM_YEARS.start}-"
                f"{CLIM_YEARS.stop - 1}, "
                f"offsets {list(CLIM_OFFSETS)}d / "
                f"t-test, "
                f"{'FDR' if USE_FDR else 'p'}"
                f"<{ALPHA}"
            )

            if var_name == "z500":
                fname = f"{group}_Z500_anom_composite.png"
                title = (
                    f"{group}: ERA5 Z500 anomaly "
                    f"composite (N={n})\n{sub}"
                )
                levels = np.arange(-60, 61, 5)
                label = "Z500 anomaly (gpm)"

            else:
                fname = f"{group}_Psea_anom_composite.png"
                title = (
                    f"{group}: ERA5 Psea anomaly "
                    f"composite (N={n})\n{sub}"
                )
                levels = np.arange(-8, 8.1, 1)
                label = "Psea anomaly (hPa)"

            plot_anom(
                mean,
                sig,
                title,
                fname,
                levels,
                label,
            )

            log(
                f"完了: {group}/{var_name}, "
                f"N={n}, 出力={fname}"
            )

        log(f"グループ {group}: 解析終了")

    # --------------------------------------------------------
    # 最終サマリー
    # --------------------------------------------------------
    log("=" * 65)
    log("すべての解析が終了しました")

    for group, dates in valid_by_group.items():
        log(
            f"  {group}: 有効日時 {len(dates)} 件、"
            f"スキップ {len(skipped_by_group[group])} 件"
        )

    log(f"総経過時間: {time.time() - START_TIME:.1f} 秒")
    log("出力画像は作業ディレクトリに保存されています")


if __name__ == "__main__":
    main()
