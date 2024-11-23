import numpy as np
import matplotlib.pyplot as plt

# 定数
g = 9.8  # 重力加速度 (m/s^2)
cp = 1005  # 空気の比熱 (J/(kg*K))
Lv = 2.5e6  # 蒸発潜熱 (J/kg)
Rv = 461  # 水蒸気のガス定数 (J/(kg*K))
Rd = 287  # 乾燥空気のガス定数 (J/(kg*K))
rho_air = 1.2  # 空気の密度 (kg/m^3)
k = 0.01  # 熱伝導率 (W/(m*K))
D_v = 2.5e-5  # 水蒸気の拡散係数 (m^2/s)
dt = 1  # 時間ステップ (秒)
dz = 0.01  # 鉛直分解能 (m)
time_steps = 3600 # シミュレーションの総時間 (秒)
layers = 100  # 鉛直層の数
T_water = 40  # 水の温度 (℃)
T_air_init = 20  # 空気の初期温度 (℃)
qv_air_init = 0.0  # 空気の初期水蒸気量 (kg/kg)
p_surface = 100000  # 地表気圧 (Pa)

# 初期条件
T_air = np.full(layers, T_air_init, dtype=float)  # 空気の温度プロファイル (°C)
qv_air = np.full(layers, qv_air_init, dtype=float)  # 水蒸気量プロファイル (kg/kg)

# 出力用の保存
T_air_history = []
qv_air_history = []
theta_e_history = []

# 飽和水蒸気量の計算関数 (Clausius-Clapeyron式)
def calc_qv_sat(T):
    """温度から飽和水蒸気量を計算"""
    T_k = T + 273.15  # 絶対温度 (K)
    e_sat = 6.112 * np.exp((17.67 * T) / (T + 243.5)) * 100  # 飽和水蒸気圧 (Pa)
    return 0.622 * e_sat / (p_surface - e_sat)

# 相当温位の計算関数
def calc_theta_e(T, qv, p=p_surface):
    """温度 (°C), 水蒸気量 (kg/kg), 圧力 (Pa) から相当温位を計算"""
    T_k = T + 273.15  # 絶対温度 (K)
    theta = T_k * (100000 / p) ** (Rd / cp)  # ポテンシャル温度
    LCL_term = np.exp((Lv * qv) / (cp * T_k))  # 潜熱効果
    return theta * LCL_term

# シミュレーションループ
for t in range(int(time_steps / dt)):
    # 温度勾配による熱伝導
    dT_dz = np.gradient(T_air, dz)
    heat_flux = -k * dT_dz
    dT_dt = -np.gradient(heat_flux, dz) / (rho_air * cp)
    
    # 蒸発による水蒸気移動
    dqv_dz = np.gradient(qv_air, dz)
    vapor_flux = -D_v * dqv_dz
    dqv_dt = -np.gradient(vapor_flux, dz)
    
    # 最下層での水蒸気と熱の供給（境界条件）
    qv_sat_surface = calc_qv_sat(T_air[0])  # 現在の地表温度に基づく飽和水蒸気量
    heat_flux_surface = k * (T_water - T_air[0]) / dz
    vapor_flux_surface = D_v * (qv_sat_surface - qv_air[0]) / dz
    
    dT_dt[0] += heat_flux_surface / (rho_air * cp)
    dqv_dt[0] += vapor_flux_surface

    # 温度と水蒸気の更新
    T_air += dT_dt * dt
    qv_air += dqv_dt * dt

    # 対流の計算
    theta = T_air + 273.15  # 仮想温位 (簡略化)
    unstable_layers = np.where(np.diff(theta) < 0)#[0]  # 不安定層の検出

    for layer in reversed(unstable_layers):
        # 温度と水蒸気の鉛直混合
        avg_T = (T_air[layer] + T_air[layer + 1]) / 2
        avg_qv = (qv_air[layer] + qv_air[layer + 1]) / 2
        T_air[layer] = T_air[layer + 1] = avg_T
        qv_air[layer] = qv_air[layer + 1] = avg_qv
        
    # 相当温位を計算
    theta_e = calc_theta_e(T_air, qv_air)

    # 出力保存
    T_air_history.append(T_air.copy())
    qv_air_history.append(qv_air.copy())
    theta_e_history.append(theta_e.copy())

# 結果のプロット
time = np.arange(0, time_steps, dt)
z = np.arange(0, layers * dz, dz)

plt.figure(figsize=(18, 6))
plt.subplot(1, 3, 1)
plt.contourf(time, z, np.array(T_air_history).T, cmap='coolwarm')
plt.colorbar(label='Temperature (°C)')
plt.xlabel('Time (s)')
plt.ylabel('Height (m)')
plt.title('Temperature Profile')

plt.subplot(1, 3, 2)
plt.contourf(time, z, np.array(qv_air_history).T, cmap='Blues')
plt.colorbar(label='Water Vapor (kg/kg)')
plt.xlabel('Time (s)')
plt.ylabel('Height (m)')
plt.title('Water Vapor Profile')

plt.subplot(1, 3, 3)
plt.contourf(time, z, np.array(theta_e_history).T, cmap='viridis')
plt.colorbar(label='Equivalent Potential Temperature (K)')
plt.xlabel('Time (s)')
plt.ylabel('Height (m)')
plt.title('Equivalent Potential Temperature Profile')

plt.tight_layout()
plt.show()
