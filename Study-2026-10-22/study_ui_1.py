import pygame

PANEL_BG = (28, 28, 34)
TEXT = (225, 225, 225)
SUBTLE = (140, 140, 150)
TRACK = (70, 70, 82)
ACCENT = (90, 160, 255)
BOX = (50, 50, 60)
BOX_HOVER = (75, 75, 92)
BORDER = (110, 110, 125)

LABEL_H = 18
ROW_H = 24

#スライダーボタンの関数クラス
class Slider:
    #初期化
    def __init__(self, label, vmin, vmax, value, step=1.0, fmt="{:.0f}"):
        self.label = label
        self.vmin  = vmin
        self.vmax  = vmax
        self.value = value
        self.step  = step
        self.fmt   = fmt
        self.rect = pygame.Rect(0 ,0, 0, 0)
        self.bar  = pygame.Rect(0, 0, 0, 0) 
        self.dragging = False
        self.visible = True

        return

    #枠設定
    def place(self, x, y, w):
        self.rect = pygame.Rect(x, y, w, LABEL_H + 20)
        self.bar  = pygame.Rect(x + 6, y + LABEL_H + 6, w - 12, 6)
        return self.rect.bottom + 6

    #スライダーの可動部計算
    def setFromX(self, px):
        r = min(max((px - self.bar.x)/self.bar.w, 0.0), 1.0)
        v = self.vmin + r * (self.vmax - self.vmin)
        #step(刻み)に指定がある場合は丸める
        if self.step:
            v = self.vmin + round((v - self.vmin) / self.step) * self.step
            v = min(max(v, self.vmin), self.vmax)

        changed = v != self.value
        self.value = v
        return changed

    def handle(self, event):
        if not self.visible:
            self.dragging = False
            return False

        if   event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.bar.inflate(14, 20).collidepoint(event.pos):
                self.dragging = True
                return self.setFromX(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            return self.setFromX(event.pos[0])

        return False
    
    #スライダー描画
    def draw(self, surf, font):
        if not self.visible:
            return
        text = f"{self.label}: {self.fmt.format(self.value)}"
        surf.blit(font.render(text, True, TEXT), (self.rect.x, self.rect.y))
        pygame.draw.rect(surf, TRACK, self.bar, border_radius=3)

        r = (self.value - self.vmin) / (self.vmax - self.vmin)
        fill = self.bar.copy()
        fill.w = int(self.bar.w * r)
        pygame.draw.rect(surf, ACCENT, fill, border_radius=3)
        pygame.draw.circle(surf, TEXT, (self.bar.x + int(self.bar.w * r), self.bar.centery), 7) 

        return

class Dropdown:
    def __init__(self, label, options, index=0):
        self.label   = label
        self.options = list(options)
        self.index   = index
        self.open    = False
        self.box       = pygame.Rect(0, 0, 0, 0)
        self.label_pos = 0,0

        return

    @property
    def value(self):
        return self.options[self.index]
    
    def place(self, x, y, w):
        self.label_pos = (x, y)
        self.box = pygame.Rect(x, y + LABEL_H, w, ROW_H)
        return self.box.bottom + 10

    def itemRects(self):
        return [pygame.Rect(self.box.x, self.box.bottom + i * ROW_H, self.box.w, ROW_H)
                for i in range(len(self.options))]
    
    def handle(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.open:
            self.open = False
            for i, r in enumerate(self.itemRects()):
                if r.collidepoint(event.pos):
                    changed    = i!= self.index
                    self.index = i
                    return changed
            return False

        if self.box.collidepoint(event.pos):
            self.open = True
        return False
        

    def draw(self, surf, font):
        surf.blit(font.render(self.label, True, SUBTLE), self.label_pos)
        pygame.draw.rect(surf, BOX, self.box, border_radius=4)
        pygame.draw.rect(surf, BORDER, self.box, 1, border_radius=4)
        surf.blit(font.render(self.value, True, TEXT), (self.box.x + 8, self.box.y + 5))
        ax = self.box.right - 16
        ay = self.box.centery
        pygame.draw.polygon(surf, TEXT, [(ax - 5, ay - 3), (ax + 5, ay - 3), (ax, ay + 4)])

    def drawList(self, surf, font):
        if not self.open:
            return
        mouse = pygame.mouse.get_pos()
        for i, r in enumerate(self.itemRects()):
            color = BOX_HOVER if r.collidepoint(mouse) or i == self.index else BOX
            pygame.draw.rect(surf, color, r)
            pygame.draw.rect(surf, BORDER, r, 1)
            surf.blit(font.render(self.options[i], True, TEXT), (r.x + 8, r.y + 5))
            
        return

class Button:
    #初期化
    def __init__(self, text):
        self.text = text
        self.rect = pygame.Rect(0, 0, 0, 0)
        return

    #枠設定
    def place(self, x, y, w, h=28):
        self.rect = pygame.Rect(x, y, w, h)
        return self.rect.bottom + 8

    #ボタン押下検知
    def handle(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN 
                and event.button == 1
                and self.rect.collidepoint(event.pos))

    #ボタン描画
    def draw(self, surf, font):
        color = BOX_HOVER if self.rect.collidepoint(pygame.mouse.get_pos()) else BOX
        pygame.draw.rect(surf, color, self.rect, border_radius=4)
        pygame.draw.rect(surf, BORDER, self.rect, 1, border_radius=4)

        img = font.render(self.text, True, TEXT)
        surf.blit(img, img.get_rect(center=self.rect.center))

        return
    