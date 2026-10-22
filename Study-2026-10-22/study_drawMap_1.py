import sys
import numpy as np
import pygame
from study_data_gen_1 import Simulation, SIM_DT, DEFAULT_PARAMS, WORLD_H, WORLD_W, EDGE_MODES
from study_schema_1 import ORBIT, SCENARIOS
from study_ui_1 import Slider, Dropdown, Button, PANEL_BG, SUBTLE
from study_camera_1 import Camera, VIEW_MODES

MAP_W, MAP_H = 800, 800
PANEL_W      = 300
MAP_RECT     = pygame.Rect(0, 0, MAP_W, MAP_H)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
OUTSIDE = (38, 38, 46)
BORDER = (90, 90, 105)
FOCUS = (255, 210, 60)
MAX_STEPS_PER_FRAME = 400
PICK_PX = 8
HOME_PX = 10
SCALE_BAR_PX = 120

#モードに応じたスライダー表示切替用の判別式
VISIBLE_IF = {
    "initial": lambda s, o: s in ("random", "flock", "inbound"),
    "spawn_rate": lambda s, o: s in ("random", "flock", "inbound"),
    "flock_size": lambda s, o: s == "flock",
    "flock_spread": lambda s, o: s == "flock",
    "cross_n": lambda s, o: s == "crossing",
    "cross_angle": lambda s, o: s == "crossing",
    "turn_accel": lambda s, o: o in ("turn", "maneuver"),
}

#スライダー設定
def buildSliders():
    p = DEFAULT_PARAMS
    return {
        "seed": Slider("Seed (Reset)", 0, 99, p["seed"], 1),
        "speed": Slider("Speed [m/s]", 10, 700, p["speed"], 1),
        "initial": Slider("Initial targets/flocks (Reset)", 0, 30, p["initial"], 1),
        "spawn_rate": Slider("Spawn rate [/min]", 0, 60, p["spawn_rate"], 1),
        "turn_accel": Slider("Turn accel [m/s^2]", 0, 30, p["turn_accel"], 0.5, "{:.1f}"),
        "flock_size": Slider("Flock size", 2, 12, p["flock_size"], 1),
        "flock_spread": Slider("Flock spread [m]", 5, 100, p["flock_spread"], 1),
        "cross_n": Slider("Crossing targets", 2, 6, p["cross_n"], 1),
        "cross_angle": Slider("Crossing angle [deg]", 5, 180, p["cross_angle"], 1),
    }

#インターフェースの位置計算
def layout(dropdowns, sliders, time_scale, buttons):
    x = MAP_W + 20
    w = PANEL_W - 40
    y = 15
    for d in dropdowns:
        y = d.place(x, y, w)
    scenario, orbit = dropdowns[0].value, dropdowns[1].value
    #シナリオと軌道を入力して、真になるものだけ表示
    for key, s in sliders.items():
        rule = VISIBLE_IF.get(key)
        s.visible = rule is None or rule(scenario, orbit)
        if s.visible:
            y = s.place(x, y, w)
    y    = time_scale.place(x, y + 10, w)
    half = (w - 10) // 2
    buttons[0].place(x, y + 10, half)
    y    = buttons[1].place(x + half + 10, y + 10, half)
    buttons[2].place(x, y, half)
    buttons[3].place(x + half + 10, y, half)

    return

#ボタンの表示文字を作る
def edgeLabel(mode):
    return f"Edge: {mode}"

#指定位置と最も近い目標を選択
def pickTarget(sim, cam, pos):
    e   = sim.enemies
    idx = np.flatnonzero(e["alive"])
    if idx.size == 0:
        return -1

    sx, sy = cam.toScreen(e["x"][idx], e["y"][idx])
    d = np.hypot(sx - pos[0], sy - pos[1])
    k = int(np.argmin(d))
    if d[k] > PICK_PX:
        return -1
    return int(idx[k])

#縮尺バーの長さ調整
def niceLength(m):
    p = 10 ** np.floor(np.log10(m))
    for k in (5, 2, 1):
        if k * p <= m:
            return k * p
    return p

#スケールの表示
def drawScale(screen, font, cam):
    length = niceLength(SCALE_BAR_PX / cam.zoom)
    px     = int(round(length * cam.zoom))
    x, y   = 20, MAP_H - 25

    pygame.draw.line(screen, WHITE, (x, y), (x + px, y), 2)
    pygame.draw.line(screen, WHITE, (x, y - 5), (x, y + 5), 1)
    pygame.draw.line(screen, WHITE, (x + px, y - 5), (x + px, y + 5), 1)
    label = f"{length / 1000:g} km" if length >= 1000 else f"{length:g} m"
    screen.blit(font.render(label, True, WHITE), (x, y - 20))

    return

#各enemyの表示
def drawWorld(screen, font, sim, cam, show_truth):
    screen.set_clip(MAP_RECT)
    screen.fill(OUTSIDE, MAP_RECT)
    x0, y0 = cam.toScreen(0.0, 0.0)
    x1, y1 = cam.toScreen(sim.width, sim.height)
    world  = pygame.Rect(round(x0), round(y0), round(x1 - x0), round(y1 - y0))
    screen.fill (BLACK, world.clip(MAP_RECT))
    pygame.draw.rect(screen, BORDER, world, 1)

    e = sim.enemies
    if show_truth:
        idx    = np.flatnonzero(e["alive"])
        sx, sy = cam.toScreen(e["x"][idx], e["y"][idx])
        hx = sx + 10 * np.cos(e["angle"][idx])
        hy = sy + 10 * np.sin(e["angle"][idx])

        inside = (sx > -20) & (sx < MAP_W + 20) & (sy > -20) & (sy < MAP_H + 20)
        for i, x, y, x2, y2 in zip(idx[inside], sx[inside], sy[inside], hx[inside], hy[inside]):
            color = WHITE if e["leader"][i] >= 0 else RED
            p = (round(x), round(y))
            pygame.draw.circle(screen, color, p, 3)
            pygame.draw.line(screen, color, p, (round(x2), round(y2)), 1)

        if cam.follow >= 0:
            fx, fy = cam.toScreen(e["x"][cam.follow], e["y"][cam.follow])
            pygame.draw.circle(screen, FOCUS, (round(fx), round(fy)), 9, 1)

    cx, cy = MAP_RECT.center
    pygame.draw.line(screen, SUBTLE, (cx - 6, cy), (cx + 6, cy), 1)
    pygame.draw.line(screen, SUBTLE, (cx, cy - 6), (cx, cy + 6), 1)

    drawScale(screen, font, cam)
    info = f"t = {sim.t:7.2f} s   alive = {int(e['alive'].sum())}   issued = {sim.next_id - 1}"
    screen.blit(font.render(info, True, WHITE), (10, 10))
    view = f"view {cam.viewWidth() / 1000:.2f} km   x{cam.zoomRatio():.1f}"
    if cam.follow >= 0:
        view += f"   follow id {cam.follow_id}"
    screen.blit(font.render(view, True, WHITE), (10, 30))
    screen.set_clip(None)

    return

#各インターフェースの表示
def drawPanel(screen, font, dropdowns, sliders, time_scale, buttons):
    pygame.draw.rect(screen, PANEL_BG, pygame.Rect(MAP_W, 0, PANEL_W, MAP_H))
    for d in dropdowns:
        d.draw(screen, font)
    for s in sliders.values():
        s.draw(screen, font)
    time_scale.draw(screen, font)
    for b in buttons:
        b.draw(screen, font)

    lx, ly = MAP_W + 20, MAP_H - 70
    help_lines = ("Click target: follow", "Click empty: move center",
                   "Click center: home   Wheel: zoom")
    for k, line in enumerate(help_lines):
        screen.blit(font.render(line, True, SUBTLE), (lx, ly - 70 + 18 * k))        
    screen.blit(font.render("Ground truth (user only)", True, SUBTLE), (lx, ly))
    pygame.draw.circle(screen, RED, (lx + 5, ly + 27), 4)
    screen.blit(font.render("leader / single", True, SUBTLE), (lx + 16, ly + 20))
    pygame.draw.circle(screen, WHITE, (lx + 5, ly + 47), 4)
    screen.blit(font.render("follower", True, SUBTLE), (lx + 16, ly + 40))

    for d in dropdowns:
        d.drawList(screen, font)

def main():
    pygame.init()
    screen = pygame.display.set_mode((MAP_W + PANEL_W, MAP_H))
    pygame.display.set_caption("Radar Target Simulator")
    font  = pygame.font.SysFont(None, 20)
    clock = pygame.time.Clock()

    sim = Simulation(WORLD_W, WORLD_H)
    cam = Camera(WORLD_W, WORLD_H, MAP_RECT.x, MAP_RECT.y, MAP_W, MAP_H)
    orbits    = list(ORBIT)
    view_mode = Dropdown("View (when zoomed out)", VIEW_MODES, 0)
    dropdowns = (
        Dropdown("Scenario", SCENARIOS, SCENARIOS.index(sim.params["scenario"])),
        Dropdown("Orbit", orbits, orbits.index(sim.params["orbit"])),
        view_mode,
    )
    sliders = buildSliders()
    time_scale = Slider("Time scale", 0.25, 16.0, 1.0, 0.25, "{:.2f}x")
    buttons = (Button("Reset"), Button("Pause"), Button("Hide truth"),
               Button(edgeLabel(sim.params["edge"])))

    acc = 0.0
    paused = False
    show_truth = True

    #操作の適用
    def doReset():
        nonlocal acc
        for key, s in sliders.items():
            sim.params[key] = s.value
        sim.params["scenario"] = dropdowns[0].value
        sim.params["orbit"] = dropdowns[1].value
        sim.reset()
        acc = 0.0

    #マップ上でのイベント管理(縮尺, 追跡指定, 初期位置帰還)
    def handleMap(event):
        if event.type == pygame.MOUSEWHEEL:
            if MAP_RECT.collidepoint(pygame.mouse.get_pos()):
                cam.zoomBy(event.y)
                return True
            return False

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if not MAP_RECT.collidepoint(event.pos):
            return False

        hit = pickTarget(sim, cam, event.pos) if show_truth else -1
        near_center = np.hypot(event.pos[0] - MAP_RECT.centerx,
                               event.pos[1] - MAP_RECT.centery) <= HOME_PX
        if hit >= 0 and hit != cam.follow:
            cam.followTarget(hit, int(sim.enemies["id"][hit]))
        elif hit >= 0 or near_center:
            cam.home()
        else:
            cam.focusAt(*cam.toWorld(*event.pos))
        return True

    #全体でのイベント管理(コンボボックス, マップ, スライダー, ボタン)
    def handleEvent(event):
        nonlocal paused, show_truth
        for d in dropdowns:
            if d.open:
                if d.handle(event) and d is not view_mode:
                    doReset()
                return

        for d in dropdowns:
            d.handle(event)
            if d.open:
                return

        if handleMap(event):
            return

        for key, s in sliders.items():
            if s.handle(event):
                sim.params[key] = s.value

        time_scale.handle(event)

        if buttons[0].handle(event):
            doReset()
        if buttons[1].handle(event):
            paused = not paused
            buttons[1].text = "Resume" if paused else "Pause"
        if buttons[2].handle(event):
            show_truth = not show_truth
            buttons[2].text = "Hide truth" if show_truth else "Show truth"
        if buttons[3].handle(event):
            k = EDGE_MODES.index(sim.params["edge"])
            sim.params["edge"] = EDGE_MODES[(k + 1) % len(EDGE_MODES)]
            buttons[3].text = edgeLabel(sim.params["edge"])

    #処理ループ
    running = True
    while running:
        real_dt = clock.tick(60) / 1000
        layout(dropdowns, sliders, time_scale, buttons)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                handleEvent(event)

        #処理落ち対策
        if not paused:
            acc += real_dt * time_scale.value
            steps = 0
            while acc >= SIM_DT and steps < MAX_STEPS_PER_FRAME:
                sim.step(SIM_DT)
                acc -= SIM_DT
                steps += 1
            if acc >= SIM_DT:
                acc = 0.0

        cam.mode = view_mode.value
        cam.update(sim.enemies)
        drawWorld(screen, font, sim, cam, show_truth)
        drawPanel(screen, font, dropdowns, sliders, time_scale, buttons)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()