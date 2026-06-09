import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import time

# =========================
# フォント設定
# =========================
plt.rcParams["font.style"] = "normal"
plt.rcParams["mathtext.default"] = "regular"

# =========================
# 設定
# =========================
lon = 140.0
latitudes = np.arange(22, 48, 0.5)

# H/L 探索範囲
time_search = 6
lat_search = 4

base_url = "https://historical-forecast-api.open-meteo.com/v1/forecast"

models = [
    ("jma_gsm", "GSM"),
    ("ncep_aigfs025", "AIGFS"),
    ("gfs_global", "NCEP"),
    ("ecmwf_ifs025", "ECMWF"),
    ("ecmwf_aifs025_single", "AIFS"),
]

# =========================
# 1次元移動平均
# =========================
def running_mean_1d(data, half_window):

    out = np.zeros_like(data, dtype=float)

    for i in range(len(data)):
        s = max(0, i - half_window)
        e = min(len(data), i + half_window + 1)
        out[i] = np.mean(data[s:e])

    return out

# =========================
# MSLP 平滑化
# =========================
def smooth_pressure(pressure, half_window=12, max_diff=1.0):

    smooth = running_mean_1d(pressure, half_window)
    corrected = smooth.copy()
    diff = pressure - smooth

    mask_pos = diff > max_diff
    corrected[mask_pos] = pressure[mask_pos] - max_diff

    mask_neg = diff < -max_diff
    corrected[mask_neg] = pressure[mask_neg] + max_diff

    return corrected

# =========================
# 2次元5点平滑化
# =========================
def smooth_5point(data):

    ny, nx = data.shape
    out = np.zeros_like(data, dtype=float)

    for i in range(ny):
        for j in range(nx):

            vals = [data[i, j]]

            if i > 0:
                vals.append(data[i - 1, j])

            if i < ny - 1:
                vals.append(data[i + 1, j])

            if j > 0:
                vals.append(data[i, j - 1])

            if j < nx - 1:
                vals.append(data[i, j + 1])

            out[i, j] = np.mean(vals)

    return out

for model_id, model_name in models:

    print(f"\n===== {model_name} =====")

    # =========================
    # データ取得
    # =========================
    all_pressure = []
    all_temp850 = []
    all_z500 = []

    times = None

    for lat in latitudes:

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": (
                "pressure_msl,"
                "temperature_850hPa,"
                "geopotential_height_500hPa"
            ),
            #"models": "ecmwf_ifs025",
            "models": model_id,
            "timezone": "Asia/Tokyo",
            "forecast_days": 10
        }

        print(f"{model_name} Downloading lat={lat:.2f}")

        for retry in range(5):
            try:
                r = requests.get(base_url, params=params, timeout=120)
                data = r.json()
                break

            except Exception as e:
                time.sleep(30)

        else:
            raise RuntimeError(f"Failed to download lat={lat:.2f}")

        if times is None:
            times = [datetime.fromisoformat(t) for t in data["hourly"]["time"]]

        pressure = np.array(data["hourly"]["pressure_msl"], dtype=float)
        temp850 = np.array(data["hourly"]["temperature_850hPa"], dtype=float)
        z500 = np.array(data["hourly"]["geopotential_height_500hPa"], dtype=float)

        # =========================
        # 地上気圧平滑化
        # =========================
        pressure_corr = smooth_pressure(pressure, half_window=12, max_diff=2.0)

        # =========================
        # Z500 前後12h平均
        # =========================
        z500_t = running_mean_1d(z500, 12)

        all_pressure.append(pressure_corr)
        all_temp850.append(temp850)
        all_z500.append(z500_t)

    # =========================
    # [lat, time]
    # =========================
    pressure_array = np.array(all_pressure)
    temp850_array = np.array(all_temp850)
    z500_array = np.array(all_z500)

    # =========================
    # 緯度方向平均
    # =========================
    pressure_smoothed = np.zeros_like(pressure_array)
    temp850_smoothed = np.zeros_like(temp850_array)
    z500_smoothed = np.zeros_like(z500_array)

    for i in range(len(latitudes)):

        s = max(0, i - 2)
        e = min(len(latitudes), i + 2)

        pressure_smoothed[i] = np.mean(pressure_array[s:e], axis=0) #pressure_array
        temp850_smoothed[i] = np.mean(temp850_array[s:e], axis=0) #temp850_array
        z500_smoothed[i] = np.mean(z500_array[s:e], axis=0)

    # =========================
    # H/L 探索
    # =========================
    highs = []
    lows = []

    ny, nx = pressure_smoothed.shape

    for j in range(nx):
        for i in range(ny):

            val = pressure_smoothed[i, j]

            ys = max(0, i - lat_search)
            ye = min(ny, i + lat_search + 1)
            xs = max(0, j - time_search)
            xe = min(nx, j + time_search + 1)

            local = pressure_smoothed[ys:ye, xs:xe]

            local_max = np.max(local)
            local_min = np.min(local)

            # 高気圧
            if val == local_max:
                if 25 <= latitudes[i] <= 45:
                    highs.append((j, i, val))

            # 低気圧
            if val == local_min:
                if 25 <= latitudes[i] <= 45:
                    lows.append((j, i, val))

    # 描画
    fig, ax = plt.subplots(figsize=(24, 6))
    X, Y = np.meshgrid(times, latitudes)

    # 850hPa気温
    temp_levels = np.arange(-12, 24.1, 3)
    cf = ax.contourf(X, Y, temp850_smoothed, levels=temp_levels, cmap="turbo", extend="both")

    # 海面気圧
    mslp_levels = np.arange(960, 1041, 2)
    cs = ax.contour(X, Y, pressure_smoothed, levels=mslp_levels, colors="black", linewidths=0.8)
    clabels1 = ax.clabel(cs, fmt="%d", fontsize=18)

    for txt in clabels1:
        txt.set_rotation(0)
        txt.set_fontstyle("normal")

    # Z500
    z500_levels = np.arange(5100, 6001, 60)
    z500_cs = ax.contour(X, Y, z500_smoothed, levels=z500_levels, colors="white", linewidths=3)
    clabels2 = ax.clabel(z500_cs, fmt="%d", fontsize=18)

    for txt in clabels2:
        txt.set_rotation(0)
        txt.set_fontstyle("normal")

    # =========================
    # H/L スタンプ
    # =========================
    for j, i, val in highs:
        ax.text(times[j], latitudes[i], "H", color="blue", fontsize=18, fontweight="bold", ha="center", va="center", clip_on=True)

    for j, i, val in lows:
        ax.text(times[j], latitudes[i], "L", color="red", fontsize=18, fontweight="bold", ha="center", va="center", clip_on=True)

    # =========================
    # 軸設定
    # =========================
    ax.set_ylabel("Latitude")
    ax.set_xlabel("Date")
    ax.set_ylim(25, 45)

    # 左ほど未来
    ax.invert_xaxis()

    # 日付表示
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())

    # ラベル
    for label in ax.get_xticklabels():
        label.set_rotation(0)
        label.set_fontstyle("normal")

    for label in ax.get_yticklabels():
        label.set_fontstyle("normal")

    # カラーバー
    cbar = plt.colorbar(cf)
    cbar.set_label("850 hPa Temperature (°C)")

    for label in cbar.ax.get_yticklabels():
        label.set_fontstyle("normal")

    # タイトル
    ax.set_title(f"{model_name} Time-Latitude Section (Smoothed MSLP, T850, Z500) at {lon:.0f}E")

    plt.tight_layout()
    plt.savefig(f"weekly/time_latitude_{model_name}.png", dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Saved: time_latitude_{model_name}.png")
