import numpy as np
from scipy.interpolate import CubicSpline
from sklearn.metrics import mean_squared_error

# 補間の関数
def interpolate_data(A, B):
    x_A, y_A = A[:, 0], A[:, 1]
    x_B, y_B = B[:, 0], B[:, 1]

    # Aを元にスプライン補間 (Aのすべての値を使用)
    spline_A = CubicSpline(x_A, y_A)
    interpolated_B = spline_A(x_B)  # Bのすべての点で補間

    # Bを元にスプライン補間 (Bのすべての値を使用)
    spline_B = CubicSpline(x_B, y_B)
    interpolated_A = spline_B(x_A)  # Aのすべての点で補間

    return interpolated_A, interpolated_B

# RMSEの計算
def calculate_rmse(original_A, original_B, interpolated_A, interpolated_B):
    # AとBの値を合わせてRMSEを計算
    y_true = np.concatenate((original_A[:, 1], original_B[:, 1]))
    y_pred = np.concatenate((interpolated_A, interpolated_B))

    return np.sqrt(mean_squared_error(y_true, y_pred))

# 繰り返し処理
def process_data(data, threshold=1):
    # 奇数番目をA、偶数番目をBに分割
    A = data[0::2]
    B = data[1::2]

    rmse = float('inf')
    iterations = 0

    while rmse > threshold:
        iterations += 1

        # Aを基にBの補間値を求め、Bを基にAの補間値を求める
        interpolated_A, interpolated_B = interpolate_data(A, B)

        # Aの最初の要素は補間せずそのまま使用
        interpolated_A[0] = A[0, 1]

        # 最後の要素の処理
        if len(data) % 2 == 0:  # 元データが偶数個の場合
            interpolated_B[-1] = B[-1, 1]
        else:  # 元データが奇数個の場合
            interpolated_A[-1] = A[-1, 1]

        # RMSEを計算
        rmse = calculate_rmse(A, B, interpolated_A, interpolated_B)

        # 平均補間値で次の配列を作成
        A[:, 1] = (A[:, 1] + interpolated_A) / 2
        B[:, 1] = (B[:, 1] + interpolated_B) / 2

        print(f"Iteration {iterations}, RMSE: {rmse}")

    return A, B

# AとBの補間後の結果をマージし、Xでソートして表示
def merge_and_sort(A, B):
    merged = np.concatenate((A, B), axis=0)
    merged_sorted = merged[merged[:, 0].argsort()]  # Xの値でソート
    return merged_sorted

# 実行
data = np.array([[120, 11794], [162, 14872], [200, 12705], [228, 9926], [260, 14614], [280, 10376], [320, 12330], [344, 11288], [382, 14818], [415, 10964], [434, 9285], [464, 11598], [500, 10321], [515, 11564], [532, 8844], [574, 6635], [593, 5982], [620, 7101], [664, 8846], [681, 9868], [712, 7638], [734, 8096]])

final_A, final_B = process_data(data)
final_merged = merge_and_sort(final_A, final_B)

# 結果の表示
print("Final merged and sorted result:")
for row in final_merged:
    print(f"{row[0]}, {row[1]}")
