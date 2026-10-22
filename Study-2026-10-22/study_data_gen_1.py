import numpy as np
from study_schema_1 import enemy_dtype, ORBIT

WORLD_W  = 20000.0
WORLD_H  = 20000.0
SIM_DT   = 0.05
CAPACITY = 1000
FOLLOW_GAIN       = 1.2
FOLLOW_MAX_RATIO  = 1.5
FOLLOW_TURN_RATE  = 4.0
MANEUVER_ON_MEAN  = 4.0
MANEUVER_OFF_MEAN = 6.0
CONTAIN_ACCEL     = 45.0
CONTAIN_RADII     = 10.0
EDGE_MODES = ["exit", "return"]
CROSS_START_RATIO = 0.6
FLOCK_SPAWN_SPREAD  = np.deg2rad(30)
RANDOM_SPAWN_SPREAD = np.deg2rad(60)
INBOUND_SPREAD      = np.deg2rad(5)


DEFAULT_PARAMS = {
    "scenario": "random",
    "orbit": "straight",
    "seed": 0,
    "initial": 5,
    "spawn_rate": 5.0,
    "speed": 100.0,
    "turn_accel": 10.0,
    "flock_size": 5,
    "flock_spread": 45.0,
    "cross_n": 3,
    "cross_angle": 60.0,
    "edge": "exit",
}

#角度を-π~πに畳みこむ
def wrapAngle(a):
    return np.arctan2(np.sin(a), np.cos(a))

#シミュレーションのデータ操作関数クラス
class Simulation:
    def __init__(self, width, height, params=None):
        self.width  = width
        self.height = height
        self.cx     = width / 2
        self.cy     = height / 2
        self.params = dict(DEFAULT_PARAMS)
        if params:
            self.params.update(params)        
        self.reset()

        return

    #初期化
    def reset(self):
        p = self.params
        self.rng     = np.random.default_rng(int(p["seed"]))
        self.enemies = np.zeros(CAPACITY, dtype=enemy_dtype)
        self.enemies["leader"] = -1
        self.next_id = 1
        self.t       = 0.0

        scenario = p["scenario"]
        if   scenario == "random":
            for _ in range(int(p["initial"])):
                self.spawnInside()
        elif scenario == "flock":
            for _ in range(int(p["initial"])):
                self.spawnFlock()
        elif scenario == "inbound":
            for _ in range(int(p["initial"])):
                self.spawnEdge(INBOUND_SPREAD)
        elif scenario == "crossing":
            self.spawnCrossing()
        
        return
    
    #スロットにkの分だけ割り当てを行う
    def allocate(self, k):
        e = self.enemies
        #空いているスロットを探してきてindexを格納
        free = np.flatnonzero(~e["alive"])

        #空きがないならNoneを返す
        if free.size < k:
            return None
        slots = free[:k]
        e[slots] = np.zeros(k, dtype=enemy_dtype)
        e["alive"][slots]  = True
        e["leader"][slots] = -1
        e["id"][slots]     = np.arange(self.next_id, self.next_id+k)
        
        self.next_id+=k

        orbit = ORBIT.get(self.params["orbit"], ORBIT["straight"])
        e["orbit"][slots] = orbit
        if orbit == ORBIT["maneuver"]:
            e["turn_sign"][slots] = 0.0
            e["man_t"][slots]     = self.rng.exponential(MANEUVER_OFF_MEAN, k)
        else:
            e["turn_sign"][slots] = self.rng.choice([-1.0, 1.0], k)

        return slots

    #それぞれのスピードをランダムに返す
    def drawSpeed(self,k):
        return self.params["speed"] * self.rng.uniform(0.7, 1.3, k)

    #端スポーン地点の決定
    def edgePoint(self):
        w, h = self.width, self.height
        #wとhの和の2倍から全周の長さを作り、そこからランダムで選ぶ
        s = self.rng.uniform(0, 2 * (w + h))
        if   s < w:
            x, y = s, 0.0
        elif s < w + h:
            x, y = w, s-w
        elif s < 2 * w + h:
            x, y = s - (w + h), h
        else:
            x, y = 0.0, s - (2 * w + h)
        return x, y, np.arctan2(self.cy - y, self.cx - x)

    #内部スポーン地点の決定
    def spawnInside(self):
        s = self.allocate(1)
        if s is None:
            return 
        e = self.enemies
        e["x"][s] = self.rng.uniform(0,self.width)
        e["y"][s] = self.rng.uniform(0, self.height)
        e["angle"][s] = self.rng.uniform(0, 2*np.pi)
        e["speed"][s] = self.drawSpeed(1)
        
        return

    #外部スポーンのオブジェクト生成
    def spawnEdge(self, spread):
        s = self.allocate(1)
        if s is None:
            return
        e = self.enemies
        x,y,inward = self.edgePoint()
        e["x"][s] = x
        e["y"][s] = y
        e["angle"][s] = inward + self.rng.uniform(-spread, spread)
        e["speed"][s] = self.drawSpeed(1)

        return

    #群れのオブジェクト生成
    def spawnFlock(self):
        p = self.params
        k = int(p["flock_size"])
        s = self.allocate(k)
        if s is None:
            return
        e = self.enemies
        x, y, inward = self.edgePoint()
        heading = inward + self.rng.uniform(-FLOCK_SPAWN_SPREAD, FLOCK_SPAWN_SPREAD)
        spread  = p["flock_spread"]
        head      = s[0]
        followers = s[1:]
        ox = np.clip(x + self.rng.normal(0, spread, k-1), 0, self.width) - x
        oy = np.clip(y + self.rng.normal(0, spread, k-1), 0, self.height) - y

        e["x"][head] = x
        e["y"][head] = y
        e["x"][followers] = x + ox
        e["y"][followers] = y + oy
        e["angle"][s] = heading
        e["speed"][s] = self.drawSpeed(1)[0]
        e["leader"][followers] = head
        e["ox"][followers] = ox
        e["oy"][followers] = oy

        return

    #クロス時のオブジェクト生成
    def spawnCrossing(self):
        p = self.params
        k = int(p["cross_n"])
        s = self.allocate(k)
        if s is None:
            return
        e = self.enemies
        theta = np.deg2rad(p["cross_angle"])
        base  = self.rng.uniform(0, 2 * np.pi)
        half  = min(self.width, self.height) / 2
        px    = self.cx + self.rng.uniform(-0.2, 0.2) * half
        py    = self.cy + self.rng.uniform(-0.2, 0.2) * half
        dist  = CROSS_START_RATIO * half
        headings = base + (np.arange(k) - (k - 1) / 2) * theta

        e["angle"][s] = headings
        e["speed"][s] = p["speed"]
        e["x"][s]     = px-dist * np.cos(headings)
        e["y"][s]     = py-dist * np.sin(headings)
        self.cross_point    = (px, py)
        self.cross_time     = self.t + dist / (p["speed"]) 
        self.cross_deadline = self.t + 2 * dist / (p["speed"])

        return

    #シナリオに応じたスポーン管理
    def spawnProcess(self, dt):
        p = self.params
        scenario = p["scenario"]
        if scenario == "crossing":
            if not self.enemies["alive"].any() or self.t >= self.cross_deadline:
                self.enemies["alive"] = False
                self.spawnCrossing()
            return

        for _ in range(self.rng.poisson(p["spawn_rate"] / 60.0 * dt)):
            if   scenario == "random":
                self.spawnEdge(RANDOM_SPAWN_SPREAD)
            elif scenario == "flock":
                self.spawnFlock()
            elif scenario == "inbound":
                self.spawnEdge(INBOUND_SPREAD)

        return

    #端での引き返し処理
    def contain(self, dt):
        e = self.enemies
        steer = np.zeros(CAPACITY, dtype=bool)
        if self.params["edge"] != "return":
            return steer
        idx = np.flatnonzero((e["alive"]) & (e["leader"] < 0))
        if idx.size == 0:
            return steer
        v     = np.maximum(e["speed"][idx], 1e-6)
        ang   = e["angle"][idx]
        reach = CONTAIN_RADII * v ** 2 / CONTAIN_ACCEL
        px = e["x"][idx] + reach * np.cos(ang)
        py = e["y"][idx] + reach * np.sin(ang)
        out = (px < 0) | (px > self.width) | (py < 0) | (py > self.height)
        k = idx[out]

        if k.size == 0:
            return steer
        inward = np.arctan2(self.cy - e["y"][k], self.cx - e["x"][k])
        diff   = wrapAngle(inward - e["angle"][k])
        max_step = CONTAIN_ACCEL / v[out] * dt
        e["angle"][k] += np.clip(diff, -max_step, max_step)
        steer[k] = True
        return steer

    #OrbitとManeuverを持つオブジェクトの角度計算
    def applyOrbit(self, dt, steer):
        e = self.enemies
        free = e["alive"] & (e["leader"] < 0) & ~steer

        man = free & (e["orbit"] == ORBIT["maneuver"])
        if man.any():
            e["man_t"][man] -= dt
            idx = np.flatnonzero(man & (e["man_t"] < 0))
            if idx.size:
                turning = e["turn_sign"][idx] != 0
                new_sign = np.where(turning, 0.0, self.rng.choice([-1.0, 1.0], idx.size))
                e["turn_sign"][idx] = new_sign
                e["man_t"][idx]     = np.where(new_sign != 0,
                                               self.rng.exponential(MANEUVER_ON_MEAN, idx.size),
                                               self.rng.exponential(MANEUVER_OFF_MEAN, idx.size))

        turn = free & ((e["orbit"] == ORBIT["turn"]) | (e["orbit"] == ORBIT["maneuver"]))
        if turn.any():
            v = np.maximum(e["speed"][turn], 1e-6)
            e["angle"][turn] += e["turn_sign"][turn] * self.params["turn_accel"] / v * dt

        return

    #群れの子機の角度と速度計算
    def followLeader(self, dt):
        e = self.enemies
        idx = np.flatnonzero(e["alive"] & (e["leader"] >= 0))
        if idx.size == 0:
            return

        lead= e[e["leader"][idx]]
        lead_speed = lead["speed"]
        fx = e["x"][idx]
        fy = e["y"][idx]

        dvx = lead_speed * np.cos(lead["angle"]) + FOLLOW_GAIN * (lead["x"] + e["ox"][idx] - fx)
        dvy = lead_speed * np.sin(lead["angle"]) + FOLLOW_GAIN * (lead["y"] + e["oy"][idx] - fy)

        angle    = e["angle"][idx]
        diff     = wrapAngle(np.arctan2(dvy, dvx) - angle)
        max_step = FOLLOW_TURN_RATE * dt

        e["angle"][idx] = angle + np.clip(diff, -max_step, max_step)
        e["speed"][idx] = np.minimum(np.hypot(dvx, dvy), lead["speed"] * FOLLOW_MAX_RATIO)
        return

    #角度に応じて位置計算
    def move(self, dt):
        e = self.enemies
        alive = e["alive"]
        step = e["speed"][alive] *dt
        e["x"][alive] += step * np.cos(e["angle"][alive])
        e["y"][alive] += step * np.sin(e["angle"][alive])

        return

    #画面外かつその方向に進んでいるならデスポーン
    def despawn(self):
        if self.params["edge"] == "return":
            return

        e = self.enemies
        c = np.cos(e["angle"])
        s = np.sin(e["angle"])
        leaving =  (((e["x"] < 0) & (c < 0)) | ((e["x"] > self.width) & (c > 0)) |
                   ((e["y"] < 0) & (s < 0)) | ((e["y"] > self.height) & (s > 0)))
        dead = np.flatnonzero(e["alive"] & leaving)
        if dead.size == 0:
            return
        e["alive"][dead] = False
        e["leader"][np.isin(e["leader"], dead)] = -1

        return
    
    def step(self, dt=SIM_DT):
        self.spawnProcess(dt)
        steer = self.contain(dt)
        self.applyOrbit(dt, steer)
        self.followLeader(dt)
        self.move(dt)
        self.despawn()
        self.t += dt
        
        return