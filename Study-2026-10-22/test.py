import numpy as np
from study_data_gen_1 import Simulation, wrapAngle

sim = Simulation(800, 800, {"initial": 0})
pts = np.array([sim.edgePoint() for _ in range(10000)])
on_edge = (pts[:, 0] == 0) | (pts[:, 0] == 800) | (pts[:, 1] == 0) | (pts[:, 1] == 800)
print(on_edge.all())
print((pts[:, 1] == 0).mean(), (pts[:, 0] == 800).mean(), (pts[:, 1] == 800).mean(), (pts[:, 0] == 0).mean())

sim = Simulation(800, 800, {"initial": 0, "spawn_rate": 20.0})
for _ in range(12000):
    sim.step()
print(sim.next_id - 1)

sim = Simulation(800, 800, {"scenario": "inbound", "initial": 20})
e = sim.enemies
al = np.flatnonzero(e["alive"])
to_c = np.arctan2(400 - e["y"][al], 400 - e["x"][al])
print(np.rad2deg(np.abs(wrapAngle(e["angle"][al] - to_c))).max())