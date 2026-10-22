ZOOM_STEP  = 1.25
MIN_VIEW_M = 200
BLEND_ZOOM = 2.0
VIEW_MODES = ["blend", "clamp", "free"]

#カメラデータクラス
class Camera:
    #初期化
    def __init__(self, world_w, world_h, view_x, view_y, view_w, view_h):
        self.world_w  = world_w
        self.world_h  = world_h
        self.vx       = view_x
        self.vy       = view_y
        self.vw       = view_w
        self.vh       = view_h

        #全体が収まる拡大率
        self.fit      = min(view_w / world_w, view_h / world_h)

        #最大倍率
        self.zoom_max = min(view_w, view_h) / MIN_VIEW_M

        self.mode     = VIEW_MODES[0]
        self.home()

        return

    #デフォルト位置
    def home(self):
        self.fx        = self.world_w / 2
        self.fy        = self.world_h / 2
        self.zoom      = self.fit
        self.follow    = -1
        self.follow_id = 0

        return

    #視野がワールドからはみ出さないよう中心を制限
    def clampAxis(self, f, world, view):
        half = view / (2 * self.zoom)
        if 2 * half >= world:
            return world / 2
        return min(max(f, half), world - half)

    #表示モードに応じた、画面の中心に映す世界座標
    def center(self):
        if self.mode == "free":
            return self.fx, self.fy
        if self.mode == "clamp":
            return (self.clampAxis(self.fx, self.world_w, self.vw),
                    self.clampAxis(self.fy, self.world_h, self.vh))

        wx = self.world_w / 2
        wy = self.world_h / 2
        w  = min(max((self.zoom / self.fit - 1) / (BLEND_ZOOM - 1), 0.0), 1.0)
        return wx + (self.fx - wx) * w, wy + (self.fy - wy) * w

    #世界座標を画面座標に変換
    def toScreen(self, x, y):
        cx, cy = self.center()
        sx = self.vx + self.vw / 2 + (x - cx) * self.zoom
        sy = self.vy + self.vh / 2 + (y - cy) * self.zoom
        return sx, sy

    #画面座標を世界座標に変換
    def toWorld(self, sx, sy):
        cx, cy = self.center()
        x = cx + (sx - self.vx - self.vw / 2) / self.zoom
        y = cy + (sy - self.vy - self.vh / 2) / self.zoom
        return x, y

    #倍率制御
    def zoomBy(self, notches):
        z = self.zoom * ZOOM_STEP ** notches
        self.zoom = min(max(z, self.fit), self.zoom_max)

        return

    #焦点移動
    def focusAt(self, x, y):
        self.fx = min(max(x, 0.0), self.world_w)
        self.fy = min(max(y, 0.0), self.world_h)
        self.follow = -1

        return

    #追跡するターゲットのスロットとID記録
    def followTarget(self, slot, target_id):
        self.follow = slot
        self.follow_id = target_id

        return

    #追跡処理
    def update(self, enemies):
        if self.follow < 0:
            return
        e = enemies[self.follow]
        if not e["alive"] or e["id"] != self.follow_id:
            self.follow = -1
            return
        self.fx = float(e["x"])
        self.fy = float(e["y"])

        return

    #窓二秒されている範囲の幅
    def viewWidth(self):
        return self.vw / self.zoom

    #拡大比率
    def zoomRatio(self):
        return self.zoom / self.fit