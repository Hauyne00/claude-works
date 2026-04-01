"""
ぷかぷかシャボン - 4歳向け知育シャボン玉割りゲーム
"""

import pygame
import random
import math
import sys
import time
import threading
import array

# ============================================================
#  TTS (指示文のみ使用)
# ============================================================
TTS_AVAILABLE = False

def _init_tts():
    global TTS_AVAILABLE
    try:
        import pyttsx3
        e = pyttsx3.init()
        e.runAndWait()
        TTS_AVAILABLE = True
    except Exception:
        pass

threading.Thread(target=_init_tts, daemon=True).start()


def speak(text: str):
    if not TTS_AVAILABLE:
        return
    def _worker():
        try:
            import pyttsx3
            e = pyttsx3.init()
            for v in e.getProperty('voices'):
                vid = v.id.lower()
                if any(k in vid for k in ('ja', 'japanese', 'haruka', 'ichiro')):
                    e.setProperty('voice', v.id)
                    break
            e.setProperty('rate', 135)
            e.setProperty('volume', 1.0)
            e.say(text)
            e.runAndWait()
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()


# ============================================================
#  SE 生成 (pygame.mixer で音を作成)
# ============================================================
_SR = 22050  # sample rate


def make_tone(freqs: list, durations: list, volume=0.45) -> pygame.mixer.Sound:
    """周波数・長さのリストから Sound を生成 (22050Hz, 16bit stereo)"""
    total = sum(int(_SR * d) for d in durations)
    buf = bytearray(total * 4)
    pos = 0
    for freq, dur in zip(freqs, durations):
        n = int(_SR * dur)
        for i in range(n):
            att = max(1, int(n * 0.02))
            rel = max(1, int(n * 0.25))
            env = 1.0
            if i < att:
                env = i / att
            elif i > n - rel:
                env = max(0.0, (n - i) / rel)
            val = int(32767 * volume * env * math.sin(2 * math.pi * freq * i / _SR))
            val = max(-32768, min(32767, val))
            b = val.to_bytes(2, byteorder='little', signed=True)
            idx = (pos + i) * 4
            buf[idx], buf[idx + 1] = b[0], b[1]
            buf[idx + 2], buf[idx + 3] = b[0], b[1]
        pos += n
    return pygame.mixer.Sound(buffer=bytes(buf))


# ============================================================
#  定数
# ============================================================
W, H        = 1280, 720
FPS         = 60
PANEL_H     = 104   # HUD 高さ（2行レイアウト）
MAX_BUBBLES = 9
N_COLS      = 8     # 横方向ゾーン数

SKY_TOP    = (115, 190, 245)
SKY_BOTTOM = (210, 235, 255)

JP_FONT_PATHS = [
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/YuGothR.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
    "C:/Windows/Fonts/msmincho.ttc",
]


def load_jp_font(size: int) -> pygame.font.Font:
    for path in JP_FONT_PATHS:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            pass
    return pygame.font.Font(None, size)


# ============================================================
#  モード定義
# ============================================================

# 色 10種
COLORS = [
    {"name": "あか",     "tts": "あかい",     "rgb": (225, 65,  65)},
    {"name": "あお",     "tts": "あおい",     "rgb": (65,  115, 230)},
    {"name": "きいろ",   "tts": "きいろい",   "rgb": (240, 215, 25)},
    {"name": "みどり",   "tts": "みどりの",   "rgb": (50,  185, 70)},
    {"name": "ピンク",   "tts": "ピンクの",   "rgb": (245, 120, 190)},
    {"name": "むらさき", "tts": "むらさきの", "rgb": (165, 80,  215)},
    {"name": "オレンジ", "tts": "オレンジの", "rgb": (245, 145, 35)},
    {"name": "みずいろ", "tts": "みずいろの", "rgb": (75,  205, 245)},
    {"name": "ちゃいろ", "tts": "ちゃいろの", "rgb": (170, 105, 55)},
    {"name": "きみどり", "tts": "きみどりの", "rgb": (160, 220, 50)},
]

# 形 5種
SHAPES = [
    {"name": "まる",     "tts": "まるの"},
    {"name": "さんかく", "tts": "さんかくの"},
    {"name": "しかく",   "tts": "しかくの"},
    {"name": "ほし",     "tts": "ほしの"},
    {"name": "ハート",   "tts": "ハートの"},
]
SHAPE_COLORS = {
    "まる":     (225, 80,  80),
    "さんかく": (70,  185, 80),
    "しかく":   (70,  130, 230),
    "ほし":     (235, 200, 35),
    "ハート":   (235, 100, 160),
}

# 数字 1〜20
NUMBERS = list(range(1, 21))
NUM_COLORS = [
    (225, 90,  90),  (90, 140, 230), (90, 200, 90),  (230, 185, 40),
    (185, 80, 215),  (245, 130, 45), (65, 195, 235),  (155, 95, 215),
    (80, 185, 155),  (225, 130, 185),
]


# ============================================================
#  描画ヘルパー
# ============================================================

def draw_star(surf, color, cx, cy, r, width=0):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        ri  = r if i % 2 == 0 else r * 0.42
        pts.append((int(cx + math.cos(ang) * ri), int(cy + math.sin(ang) * ri)))
    pygame.draw.polygon(surf, color, pts, width)


def draw_heart(surf, color, cx, cy, r, width=0):
    pts = []
    for i in range(80):
        t = (i / 80) * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        s = r / 17
        pts.append((int(cx + x * s), int(cy + y * s)))
    if len(pts) >= 3:
        pygame.draw.polygon(surf, color, pts, width)


_bg_cache: pygame.Surface | None = None


def get_bg() -> pygame.Surface:
    global _bg_cache
    if _bg_cache is None:
        _bg_cache = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            r = int(SKY_TOP[0] * (1-t) + SKY_BOTTOM[0] * t)
            g = int(SKY_TOP[1] * (1-t) + SKY_BOTTOM[1] * t)
            b = int(SKY_TOP[2] * (1-t) + SKY_BOTTOM[2] * t)
            pygame.draw.line(_bg_cache, (r, g, b), (0, y), (W, y))
    return _bg_cache


# ============================================================
#  Bubble クラス
# ============================================================

class Bubble:
    def __init__(self, x: float, y: float, radius: int, mode: str, value):
        self.x       = x
        self.y       = y
        self.r       = radius
        self.mode    = mode
        self.value   = value
        self.vy      = -random.uniform(0.9, 2.0)
        self.vx      = random.uniform(-0.3, 0.3)
        self.phase   = random.uniform(0, math.pi * 2)
        self.wobble  = random.uniform(1.4, 2.6)
        self.popped      = False
        self.pop_timer   = 0
        self.wrong_timer = 0

    def rgb(self):
        if self.mode == 'color':
            return self.value['rgb']
        elif self.mode == 'number':
            return NUM_COLORS[self.value % len(NUM_COLORS)]
        else:
            return SHAPE_COLORS.get(self.value['name'], (200, 200, 200))

    def update(self):
        if not self.popped:
            self.y += self.vy
            self.x += self.vx
            self.x += math.sin(time.time() * self.wobble + self.phase) * 0.4
            if self.wrong_timer > 0:
                self.wrong_timer -= 1
        else:
            self.pop_timer += 1

    def draw(self, surf, font_num1, font_num2):
        cx, cy, r = int(self.x), int(self.y), self.r
        col = self.rgb()

        if not self.popped:
            # 不透明な塗りつぶし
            pygame.draw.circle(surf, col, (cx, cy), r)
            # やや明るいエッジ
            lighter = tuple(min(255, c + 65) for c in col)
            pygame.draw.circle(surf, lighter, (cx, cy), r, 4)
            # ハイライト（白い光沢点）
            pygame.draw.circle(surf, (255, 255, 255), (cx - r//3, cy - r//3), r//5)

            if self.mode == 'number':
                # 2桁は小さいフォント
                font = font_num1 if self.value < 10 else font_num2
                txt = font.render(str(self.value), True, (255, 255, 255))
                surf.blit(txt, txt.get_rect(center=(cx, cy)))
            elif self.mode == 'shape':
                self._draw_shape_icon(surf, cx, cy)

            # 不正解フラッシュ
            if self.wrong_timer > 0 and self.wrong_timer % 6 < 3:
                pygame.draw.circle(surf, (255, 50, 50), (cx, cy), r, 7)
        else:
            if self.pop_timer < 36:
                p      = self.pop_timer / 36.0
                ring_r = int(r * (1 + p * 2.2))
                alpha  = int(255 * (1 - p))
                rs = pygame.Surface((ring_r*2+8, ring_r*2+8), pygame.SRCALPHA)
                pygame.draw.circle(rs, (*col, alpha), (ring_r+4, ring_r+4), ring_r, 5)
                surf.blit(rs, (cx-ring_r-4, cy-ring_r-4))
                for i in range(10):
                    ang  = (i / 10) * math.pi * 2
                    dist = self.pop_timer * 5.5
                    px   = cx + math.cos(ang) * dist
                    py   = cy + math.sin(ang) * dist
                    ps   = max(1, int(8 * (1 - p)))
                    pa   = max(0, alpha)
                    if pa > 0 and ps > 0:
                        ps_s = pygame.Surface((ps*2, ps*2), pygame.SRCALPHA)
                        pygame.draw.circle(ps_s, (*col, pa), (ps, ps), ps)
                        surf.blit(ps_s, (int(px)-ps, int(py)-ps))

    def _draw_shape_icon(self, surf, cx, cy):
        name = self.value['name']
        r    = int(self.r * 0.52)
        c    = (255, 255, 255)
        w    = 5
        if name == 'まる':
            pygame.draw.circle(surf, c, (cx, cy), r, w)
        elif name == 'さんかく':
            pts = [
                (cx, cy - r),
                (cx - int(r * 0.866), cy + r // 2),
                (cx + int(r * 0.866), cy + r // 2),
            ]
            pygame.draw.polygon(surf, c, pts, w)
        elif name == 'しかく':
            s = int(r * 1.35)
            pygame.draw.rect(surf, c, (cx - s//2, cy - s//2, s, s), w)
        elif name == 'ほし':
            draw_star(surf, c, cx, cy, r, w)
        elif name == 'ハート':
            draw_heart(surf, c, cx, cy, r, w)

    def is_clicked(self, pos) -> bool:
        return math.hypot(pos[0] - self.x, pos[1] - self.y) <= self.r

    def is_gone(self) -> bool:
        return self.y + self.r < 0 or (self.popped and self.pop_timer >= 36)


# ============================================================
#  GameScene
# ============================================================

class GameScene:
    MAX_SCORE = 10

    def __init__(self, screen: pygame.Surface, mode: str,
                 se_correct: pygame.mixer.Sound, se_wrong: pygame.mixer.Sound):
        self.screen     = screen
        self.mode       = mode
        self.se_correct = se_correct
        self.se_wrong   = se_wrong
        self.bubbles: list[Bubble] = []
        self.target     = None
        self.instruction = ""
        self.score      = 0
        self.done       = False
        self.reward_timer   = 0
        self.feedback       = ""
        self.feedback_timer = 0
        self.next_target_cd = 0
        self.spawn_timer    = 0
        self.spawn_interval = 95
        self._back_rect = pygame.Rect(0, 0, 185, 48)

        self.f_instr  = load_jp_font(44)
        self.f_score  = load_jp_font(28)
        self.f_num1   = load_jp_font(60)   # 1桁用
        self.f_num2   = load_jp_font(44)   # 2桁用
        self.f_fb     = load_jp_font(70)
        self.f_reward = load_jp_font(82)
        self.f_sub    = load_jp_font(46)
        self.f_small  = load_jp_font(30)
        self.f_back   = load_jp_font(30)

        self._set_target()

    # -- ターゲット設定 --
    def _set_target(self):
        if self.mode == 'color':
            self.target = random.choice(COLORS)
            self.instruction = f"{self.target['name']} の シャボン玉を わってね！"
            speak(f"{self.target['tts']} シャボン玉を わってね")
        elif self.mode == 'number':
            self.target = random.choice(NUMBERS)
            self.instruction = f"{self.target} の シャボン玉を わってね！"
            speak(f"{self.target} の シャボン玉を わってね")
        else:
            self.target = random.choice(SHAPES)
            self.instruction = f"{self.target['name']} の シャボン玉を わってね！"
            speak(f"{self.target['tts']} シャボン玉を わってね")
        self.bubbles.clear()
        self._spawn(5)

    # -- カラムベースの横位置決め（重なり防止） --
    def _get_spawn_x(self, r: int) -> int:
        col_w = W // N_COLS
        counts = [0] * N_COLS
        for b in self.bubbles:
            if not b.popped:
                col = max(0, min(N_COLS - 1, int(b.x / col_w)))
                counts[col] += 1
        free = [i for i, c in enumerate(counts) if c == 0]
        pool = free if free else [i for i, c in enumerate(counts) if c <= 1]
        if not pool:
            pool = list(range(N_COLS))
        col   = random.choice(pool)
        x_min = col * col_w + r + 10
        x_max = (col + 1) * col_w - r - 10
        if x_min > x_max:
            return col * col_w + col_w // 2
        return random.randint(x_min, x_max)

    def _make_bubble(self, force_target=False) -> Bubble:
        r = random.randint(50, 68)
        x = self._get_spawn_x(r)
        y = H + random.randint(30, 180)
        if force_target or random.random() < 0.38:
            value = self.target
        else:
            if self.mode == 'color':
                value = random.choice(COLORS)
            elif self.mode == 'number':
                value = random.choice(NUMBERS)
            else:
                value = random.choice(SHAPES)
        return Bubble(x, y, r, self.mode, value)

    def _spawn(self, n: int):
        visible = sum(1 for b in self.bubbles if not b.popped)
        for _ in range(min(n, MAX_BUBBLES - visible)):
            self.bubbles.append(self._make_bubble())

    def _has_target(self) -> bool:
        for b in self.bubbles:
            if b.popped:
                continue
            if self.mode == 'color'  and b.value is self.target: return True
            if self.mode == 'number' and b.value == self.target:  return True
            if self.mode == 'shape'  and b.value is self.target: return True
        return False

    # -- クリック/タッチ --
    def handle_click(self, pos):
        if self.done or self.next_target_cd > 0:
            return
        if self._back_rect.collidepoint(pos):
            return
        for b in self.bubbles:
            if b.popped or not b.is_clicked(pos):
                continue
            correct = (
                (self.mode == 'color'  and b.value is self.target) or
                (self.mode == 'number' and b.value == self.target)  or
                (self.mode == 'shape'  and b.value is self.target)
            )
            if correct:
                b.popped = True
                self.score += 1
                self.se_correct.play()
                self.feedback = "やったね！"
                self.feedback_timer = 75
                if self.score >= self.MAX_SCORE:
                    self.done = True
                    speak("すごい！ぜんぶできたね！")
                else:
                    self.next_target_cd = 105
            else:
                b.wrong_timer = 36
                self.se_wrong.play()
                self.feedback = "ちがうよ、もう一度！"
                self.feedback_timer = 60
            break

    def is_back_clicked(self, pos) -> bool:
        return self._back_rect.collidepoint(pos) and not self.done

    # -- 更新 --
    def update(self):
        if self.done:
            self.reward_timer += 1
            return
        for b in self.bubbles:
            b.update()
        self.bubbles = [b for b in self.bubbles if not b.is_gone()]
        if not self._has_target():
            self.bubbles.append(self._make_bubble(force_target=True))
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self._spawn(2)
        if self.feedback_timer > 0:
            self.feedback_timer -= 1
        if self.next_target_cd > 0:
            self.next_target_cd -= 1
            if self.next_target_cd == 0:
                self._set_target()

    # -- 描画 --
    def draw(self):
        self.screen.blit(get_bg(), (0, 0))
        for b in self.bubbles:
            b.draw(self.screen, self.f_num1, self.f_num2)
        if self.done:
            self._draw_reward()
        else:
            self._draw_hud()
            if self.feedback_timer > 0:
                col = (40, 180, 40) if "やった" in self.feedback else (210, 70, 70)
                fb  = self.f_fb.render(self.feedback, True, col)
                self.screen.blit(fb, fb.get_rect(center=(W//2, H//2 - 20)))

    def _draw_hud(self):
        # 2行レイアウト
        # 行1 (y≈0–48): ← もどる  |  ★☆☆☆☆
        # 行2 (y≈48–104): 指示テキスト
        panel = pygame.Surface((W, PANEL_H), pygame.SRCALPHA)
        panel.fill((255, 255, 255, 185))
        self.screen.blit(panel, (0, 0))

        # 仕切り線
        pygame.draw.line(self.screen, (200, 210, 230), (0, 48), (W, 48), 1)

        # 行1: もどるボタン
        back = self.f_back.render("← もどる", True, (90, 100, 140))
        self.screen.blit(back, (15, 11))
        self._back_rect = pygame.Rect(0, 0, back.get_width() + 20, 48)

        # 行1: スコア
        stars = "★" * self.score + "☆" * (self.MAX_SCORE - self.score)
        sc = self.f_score.render(stars, True, (215, 160, 10))
        self.screen.blit(sc, sc.get_rect(midright=(W - 12, 25)))

        # 行2: 指示テキスト
        instr = self.f_instr.render(self.instruction, True, (35, 50, 160))
        self.screen.blit(instr, instr.get_rect(center=(W//2, 76)))

    def _draw_reward(self):
        t = self.reward_timer
        pulse = abs(math.sin(t * 0.055))
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((255, 235, 100, int(70 * pulse)))
        self.screen.blit(ov, (0, 0))
        for i in range(18):
            sx   = (i * 71 + int(t * 1.8)) % W
            sy   = (i * 53 + int(t * 2.5)) % H
            size = 18 + (i % 4) * 9
            draw_star(self.screen, (255, 220, 40), sx, sy, size)
        msg1 = self.f_reward.render("すごい！！", True, (215, 55, 55))
        msg2 = self.f_sub.render("ぜんぶできたね！", True, (50, 95, 210))
        self.screen.blit(msg1, msg1.get_rect(center=(W//2, H//2 - 70)))
        self.screen.blit(msg2, msg2.get_rect(center=(W//2, H//2 + 20)))
        if t > 100:
            hint = self.f_small.render("タッチしてもどる", True, (100, 100, 145))
            self.screen.blit(hint, hint.get_rect(center=(W//2, H - 65)))


# ============================================================
#  TitleScene
# ============================================================

class TitleScene:
    def __init__(self, screen: pygame.Surface):
        self.screen  = screen
        self.f_title = load_jp_font(72)
        self.f_sub   = load_jp_font(38)
        self.f_btn   = load_jp_font(48)
        self.f_small = load_jp_font(26)
        self.buttons = [
            {"mode": "color",  "label": "いろ モード",   "color": (225, 95,  95)},
            {"mode": "number", "label": "かず モード",   "color": (90,  135, 225)},
            {"mode": "shape",  "label": "かたち モード", "color": (70,  185, 90)},
        ]
        self._rects: list[pygame.Rect] = []
        self._quit_rect = pygame.Rect(0, 0, 0, 0)

    def handle_click(self, pos):
        for i, rect in enumerate(self._rects):
            if rect.collidepoint(pos):
                return self.buttons[i]["mode"]
        if self._quit_rect.collidepoint(pos):
            return "quit"
        return None

    def draw(self):
        self.screen.blit(get_bg(), (0, 0))
        t = time.time()
        deco = [
            (220,100,100),(100,130,220),(95,205,105),(225,195,45),
            (205,95,175),(90,195,200),(220,145,75),(155,95,220),
        ]
        for i in range(8):
            bx = 60 + i * 118 + math.sin(t * 0.75 + i * 1.1) * 22
            by = H - 70 + math.cos(t * 0.55 + i * 0.9) * 18
            pygame.draw.circle(self.screen, deco[i], (int(bx), int(by)), 36, 4)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(bx)-11, int(by)-11), 8)

        title = self.f_title.render("ぷかぷかシャボン", True, (35, 65, 200))
        self.screen.blit(title, title.get_rect(center=(W//2, 115)))
        sub = self.f_sub.render("モードをえらんでね！", True, (55, 75, 160))
        self.screen.blit(sub, sub.get_rect(center=(W//2, 192)))

        self._rects = []
        bw, bh = 420, 108
        for i, btn in enumerate(self.buttons):
            rect = pygame.Rect(W//2 - bw//2, 258 + i * 138, bw, bh)
            self._rects.append(rect)
            sh = pygame.Surface((bw+8, bh+8), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0, 0, 0, 55), (0, 0, bw+8, bh+8), border_radius=24)
            self.screen.blit(sh, (rect.x+4, rect.y+5))
            pygame.draw.rect(self.screen, btn["color"], rect, border_radius=24)
            hl = pygame.Surface((bw, bh//2), pygame.SRCALPHA)
            pygame.draw.rect(hl, (255, 255, 255, 55), (0, 0, bw, bh//2), border_radius=24)
            self.screen.blit(hl, rect.topleft)
            pygame.draw.rect(self.screen, (255, 255, 255), rect, 3, border_radius=24)
            txt = self.f_btn.render(btn["label"], True, (255, 255, 255))
            self.screen.blit(txt, txt.get_rect(center=rect.center))

        ft = self.f_small.render("タッチしてえらんでね", True, (80, 90, 130))
        self.screen.blit(ft, ft.get_rect(center=(W//2, H - 30)))

        # おわるボタン（右下）
        qw, qh = 160, 52
        self._quit_rect = pygame.Rect(W - qw - 20, H - qh - 15, qw, qh)
        pygame.draw.rect(self.screen, (160, 160, 170), self._quit_rect, border_radius=14)
        pygame.draw.rect(self.screen, (200, 200, 210), self._quit_rect, 2, border_radius=14)
        qt = self.f_small.render("おわる", True, (255, 255, 255))
        self.screen.blit(qt, qt.get_rect(center=self._quit_rect.center))


# ============================================================
#  メイン
# ============================================================

def get_pos(event) -> tuple:
    if event.type == pygame.FINGERDOWN:
        return (int(event.x * W), int(event.y * H))
    return event.pos


def main():
    pygame.mixer.pre_init(_SR, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("ぷかぷかシャボン")
    clock = pygame.time.Clock()

    se_correct = make_tone([523, 659, 784], [0.08, 0.08, 0.18])
    se_wrong   = make_tone([220, 180],      [0.10, 0.12])

    scene = TitleScene(screen)
    state = "title"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state == "game":
                    scene = TitleScene(screen)
                    state = "title"
                else:
                    pygame.quit()
                    sys.exit()

            # 左クリックまたはタッチのみ反応
            is_tap = (
                (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or
                event.type == pygame.FINGERDOWN
            )
            if not is_tap:
                continue

            pos = get_pos(event)

            if state == "title":
                mode = scene.handle_click(pos)
                if mode == "quit":
                    pygame.quit()
                    sys.exit()
                elif mode:
                    scene = GameScene(screen, mode, se_correct, se_wrong)
                    state = "game"

            elif state == "game":
                if scene.done and scene.reward_timer > 100:
                    scene = TitleScene(screen)
                    state = "title"
                elif scene.is_back_clicked(pos):
                    scene = TitleScene(screen)
                    state = "title"
                else:
                    scene.handle_click(pos)

        if state == "game":
            scene.update()

        scene.draw()
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
