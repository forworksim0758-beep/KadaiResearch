import numpy as np

#座標Zの追加を将来的に

enemy_dtype = np.dtype([
    ("id", np.int32),           #識別番号
    ("alive", np.bool_),         #生存判定
    ("x", np.float64),          #座標X
    ("y", np.float64),          #座標Y
    ("angle", np.float64),      #角度
    ("speed", np.float64),      #速度
    ("orbit", np.int8),         #軌道の種類
    ("leader", np.int32),       #親のスロット番号
    ("ox", np.float64),         #親からのオフセットX
    ("oy", np.float64),         #親からのオフセットY
    ("turn_sign", np.float64),  #旋回の符号
    ("man_t", np.float64),      #maneuver の次の切替までの残り時間
])

ORBIT = {
    "straight": 0,
    "turn"    : 1,
    "maneuver": 2,
}

SCENARIOS = [
    "random",
    "flock",
    "crossing",
    "inbound",
]