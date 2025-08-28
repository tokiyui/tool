import datetime
import numpy as np
import matplotlib.pyplot as plt
 
from metpy.calc import (potential_temperature, equivalent_potential_temperature,
                        saturation_equivalent_potential_temperature, lfc, el,
                        k_index, showalter_index, total_totals_index)
from metpy.units import units
from siphon.simplewebservice.wyoming import WyomingUpperAir
from scipy.interpolate import interp1d
import os
 
# 保存先作成
os.makedirs("Data/", exist_ok=True)
 
# 期間設定
start_dt = datetime.datetime(2025, 6, 1, 0)
end_dt   = datetime.datetime(2025, 8, 13, 12)
delta = datetime.timedelta(hours=12)
 
current_dt = start_dt
while current_dt <= end_dt:
    try:
        # データ取得
        df = WyomingUpperAir.request_data(current_dt, 47646)
 
        p = df['pressure'].values * units.hPa
        T = df['temperature'].values * units.degC
        Td = df['dewpoint'].values * units.degC
        z = df['height'].values * units.meter
 
        theta = potential_temperature(p, T)
        theta_e = equivalent_potential_temperature(p, T, Td)
        theta_es = saturation_equivalent_potential_temperature(p, T)
 
        k = k_index(p, T, Td)
        ssi = showalter_index(p, T, Td)
        tt = total_totals_index(p, T, Td)
 
        lfc_p, lfc_t = lfc(p, T, Td)
        el_p, el_t = el(p, T, Td)
 
        # 高度補間関数
        interp_func = interp1d(p.m, z.m, bounds_error=False, fill_value='extrapolate')
        lfc_height_m = interp_func(lfc_p.m) if lfc_p is not None else np.nan
        el_height_m = interp_func(el_p.m) if el_p is not None else np.nan
 
        # 500hPa 気温
        try:
            idx_500 = np.where(p.m >= 500)[0][-1]
            T500 = T[idx_500]
        except IndexError:
            T500 = np.nan * units.degC
 
        fig, ax = plt.subplots(figsize=(8, 10))
 
        ax.plot(theta, p, color='red', label='θ')
        ax.plot(theta_e, p, color='blue', label='θe')
        ax.plot(theta_es, p, color='green', label='θes')
 
        if lfc_p is not None:
            ax.axhline(lfc_p.m, color='orange', linestyle='--', label=f'LFC: {lfc_height_m:.0f} m')
        if el_p is not None:
            ax.axhline(el_p.m, color='purple', linestyle='--', label=f'EL: {el_height_m:.0f} m')
 
        title_center = f"{current_dt.strftime('%Y-%m-%d %H:%M UTC')} - Tateno (47646)"
        index_info = f"SSI: {ssi[0].magnitude:.1f}   K-Index: {k.magnitude:.1f}   Total Totals: {tt.magnitude:.1f}   500hPa T: {T500.magnitude:.1f} °C"
        fig.suptitle(title_center, x=0.5, y=0.98, ha='center', fontsize=16)
        fig.text(0.5, 0.955, index_info, ha='center', va='top', fontsize=12)
 
        ax.set_xlabel('Potential Temperature (K)')
        ax.set_ylabel('Pressure (hPa)')
        ax.invert_yaxis()
        ax.set_yscale('log')
        ax.set_xlim(250, 400)
        ax.set_ylim(1050, 200)
        ax.set_yticks(np.arange(1000, 150, -100))
        ax.get_yaxis().set_major_formatter(plt.ScalarFormatter())
 
        ax.grid(True, which='both', linestyle=':')
        ax.legend(loc='lower left')
        plt.tight_layout(rect=[0, 0, 1, 0.97])
 
        fname = f"Data/47646_{current_dt.strftime('%Y%m%d%H')}.png"
        plt.savefig(fname)
        plt.close()
        print(f"Saved to {fname}")
 
    except Exception as e:
        print(f"{current_dt} の処理中にエラー: {e}")
 
    current_dt += delta
