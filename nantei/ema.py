import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, ScalarFormatter, NullLocator
import time
from metpy.calc import wet_bulb_temperature
from metpy.units import units
from siphon.simplewebservice.wyoming import WyomingUpperAir
import os


def plot_sounding(station_id, station_name, dt):
    print(f"Processing station {station_id} {station_name} at {dt}")

    try:
        df = WyomingUpperAir.request_data(dt, station_id)
        if df.empty:
            print(f"No data for station {station_id} at {dt}")
            return
    except Exception as e:
        print(f"Failed to get data: {e}")
        return

    # --- 基本データ ---
    p  = df['pressure'].values * units.hPa
    T  = df['temperature'].values * units.degC
    Td = df['dewpoint'].values * units.degC

    # --- 風（Wyoming は kt）---
    u = df['u_wind'].values * units.knots
    v = df['v_wind'].values * units.knots

    # --- 湿球温度 ---
    Tw = wet_bulb_temperature(p, T, Td)

    # --- 図 ---
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.plot(T,  p, color='red',  label='Temperature')
    ax.plot(Tw, p, color='blue', label='Wet-bulb Temperature')

    # ========= 風の矢羽根（左端） =========
    x_barb = np.full_like(p.magnitude, -18.0)  # 左端に固定
    ax.barbs(
        x_barb,
        p,
        u.to('m/s').m*2.0,
        v.to('m/s').m*2.0,
        length=5,
        linewidth=0.6,
        barbcolor='black'
    )

    # --- 軸設定 ---
    title = f"{dt.strftime('%Y-%m-%d %H:%M UTC')} - {station_name} ({station_id})"
    fig.suptitle(title, fontsize=15)

    ax.set_xlabel('Temperature (°C)')
    ax.set_ylabel('Pressure (hPa)')
    ax.invert_yaxis()
    ax.set_yscale('log')

    yticks = np.arange(1000, 699, -25)
    ax.set_ylim(1020, 680)
    ax.yaxis.set_major_locator(FixedLocator(yticks))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(ScalarFormatter())

    ax.set_xlim(-10, 10)
    ax.set_xticks(np.arange(-20, 11, 1))
    ax.minorticks_off()

    ax.grid(True, which='both', linestyle=':')
    ax.legend(loc='best')

    plt.tight_layout(rect=[0, 0, 1, 1])

    # --- 出力 ---
    output_dir = "Data"
    os.makedirs(output_dir, exist_ok=True)

    fname = f"{station_id}_{dt.strftime('%Y%m%d%H')}.png"
    out_path = os.path.join(output_dir, fname)
    plt.savefig(out_path, dpi=150)
    plt.close()
    #time.sleep(30)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    station_id = 47646
    station_name = "Tateno"

    # ===== 時刻指定 =====
    start_dt = datetime.datetime(2022, 1, 5, 12, tzinfo=datetime.UTC)
    end_dt   = datetime.datetime(2022, 1, 7, 12, tzinfo=datetime.UTC)

    dt = start_dt
    while dt <= end_dt:
        plot_sounding(station_id, station_name, dt)
        dt += datetime.timedelta(hours=12)
