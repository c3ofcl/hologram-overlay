"""Windows click-through hologram visual effect, powered by PySide6.
Does not capture the screen, alter the underlying window, or draw a base circle.
"""
import math
import random
import sys
import ctypes
from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient, QLinearGradient
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSlider, QCheckBox, QGroupBox)


@dataclass
class Options:
    x: int = 700
    foot_y: int = 850
    width: int = 280
    height: int = 550
    brightness: int = 75
    speed: int = 65
    enabled: bool = True
    wisps: bool = True
    particles: bool = True
    scans: bool = True
    wave: bool = True


class Overlay(QWidget):
    def __init__(self, opt):
        super().__init__(None)
        self.opt = opt
        self.setWindowTitle('Hologram Overlay')
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.t = 0.0
        self.rng = random.Random(818)
        self.sparks = [(self.rng.random(), self.rng.random(), self.rng.random(),
                        self.rng.random()) for _ in range(115)]
        screen = QApplication.primaryScreen().virtualGeometry()
        self.bounds = screen
        self.setGeometry(screen)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)
        self.show()
        self.make_click_through()

    def make_click_through(self):
        if sys.platform != 'win32':
            return
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_NOACTIVATE = 0x08000000
        u32 = ctypes.windll.user32
        getter = u32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else u32.GetWindowLongW
        setter = u32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else u32.SetWindowLongW
        getter.argtypes = [ctypes.c_void_p, ctypes.c_int]
        getter.restype = ctypes.c_ssize_t
        setter.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
        setter.restype = ctypes.c_ssize_t
        old = getter(hwnd, GWL_EXSTYLE)
        setter(hwnd, GWL_EXSTYLE, old | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)

    def tick(self):
        self.t += 0.033 * (0.3 + self.opt.speed / 75.0)
        self.update()

    def paintEvent(self, event):
        if not self.opt.enabled:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        o = self.opt
        x = o.x - self.bounds.x()
        bottom = o.foot_y - self.bounds.y()
        w, h = o.width, o.height
        top = bottom - h
        intensity = o.brightness / 100.0
        p.setClipRect(QRectF(x-w*0.8, top-30, w*1.6, h+65))

        if o.wisps:
            # Soft, narrow volumetric columns rising from the person's feet.
            for i in range(9):
                k = (i - 4) / 4.0
                sway = math.sin(self.t*0.95+i*1.2)*w*0.045
                x0 = x + k*w*0.10
                x1 = x + k*w*0.31 + sway
                path = QPainterPath(QPointF(x0, bottom))
                path.cubicTo(x0 + k*w*0.05, bottom-h*0.28,
                             x1-k*w*0.13, top+h*0.33, x1, top+h*0.03)
                grad = QLinearGradient(x0, bottom, x1, top)
                alpha = int((32 if i%2 else 49) * intensity)
                grad.setColorAt(0, QColor(0, 220, 255, alpha))
                grad.setColorAt(0.35, QColor(20, 155, 255, int(alpha*.70)))
                grad.setColorAt(1, QColor(0, 135, 255, 0))
                pen = QPen(grad, w*(0.04 if i%3 else 0.085))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.drawPath(path)

            # Bright upwards tapered rays, no ground disc.
            for i in range(13):
                k = (i - 6)/6
                life = (self.t*0.23 + i*0.137) % 1
                px = x + k*w*0.15
                yy = bottom - h*(0.13 + life*.65)
                alpha = int(80*intensity*(1-life))
                pen = QPen(QColor(58, 225, 255, alpha), max(1.0, 2.8*(1-life)))
                p.setPen(pen)
                p.drawLine(QPointF(px, min(bottom,yy+45)), QPointF(px+k*w*.08, yy))

        if o.wave:
            # Repeating upward 'whoosh', brightest near the leading edge.
            progress = (self.t * 0.18) % 1.0
            y = bottom - progress*h
            wave_w = w*(0.31 + progress*.28)
            fade = math.sin(math.pi*progress)**0.6
            for band in range(8):
                dy = band*8
                a = int(42*intensity*fade*(1-band/9))
                p.setPen(QPen(QColor(30, 213, 255, a), 2.0+band*1.5))
                p.drawLine(QPointF(x-wave_w*(1-band*.045), y+dy),
                           QPointF(x+wave_w*(1-band*.045), y+dy))

        if o.scans:
            # Subtle hologram scanlines within the character's vertical region.
            step = 13
            shift = (self.t*19) % step
            for j in range(int(h/step)+2):
                yy = top + j*step + shift
                norm = (bottom-yy)/h
                if norm < 0 or norm > 1:
                    continue
                breadth = w*(0.16 + .32*norm)
                twinkle = .60+.40*math.sin(self.t*1.7+j*0.77)
                alpha = int(32*intensity*twinkle*math.sin(math.pi*norm)**.6)
                p.setPen(QPen(QColor(83, 211, 255, alpha), 1))
                p.drawLine(QPointF(x-breadth, yy), QPointF(x+breadth, yy))

        if o.particles:
            p.setPen(Qt.PenStyle.NoPen)
            for n, (seed_x, seed_y, seed_r, seed_phase) in enumerate(self.sparks):
                progress = (seed_y + self.t*(0.10+seed_r*.12)) % 1
                yy = bottom - progress*h
                spread = w*(0.10 + 0.40*progress)
                px = x + (seed_x*2-1)*spread + math.sin(self.t*1.25+seed_phase*6.28)*8
                alpha = int(205*intensity*(1-progress)**0.65*(.65+.35*math.sin(self.t*3+n)**2))
                radius = 0.75 + 2.4*seed_r
                p.setBrush(QColor(55, 212, 255, max(0,min(255,alpha))))
                p.drawEllipse(QPointF(px,yy),radius,radius)
                if n % 9 == 0:
                    p.setPen(QPen(QColor(130,235,255,alpha//2), 1))
                    p.drawLine(QPointF(px-5, yy), QPointF(px+5,yy))
                    p.drawLine(QPointF(px, yy-5), QPointF(px,yy+5))
                    p.setPen(Qt.PenStyle.NoPen)
        p.end()


class Controls(QWidget):
    def __init__(self, opt, overlay):
        super().__init__()
        self.opt, self.overlay = opt, overlay
        self.setWindowTitle('Hologram FX | 操作パネル')
        self.setMinimumWidth(355)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        root = QVBoxLayout(self)
        title = QLabel('青いホログラム FX  |  足元の円なし')
        title.setStyleSheet('font-size: 17px; font-weight: bold; padding: 7px;')
        root.addWidget(title)
        root.addWidget(QLabel('人物の足元に「中心X」「足元Y」を合わせてください。'))
        root.addWidget(QLabel('数値はメイン画面基準のピクセル座標です。'))
        screen = QApplication.primaryScreen().geometry()
        fields = [
            ('中心 X', 'x', 0, max(2500, screen.width()*2), 1),
            ('足元 Y', 'foot_y', 0, max(1500, screen.height()*2), 1),
            ('エフェクト幅', 'width', 60, 1100, 1),
            ('エフェクト高さ', 'height', 100, 1300, 1),
            ('明るさ', 'brightness', 5, 100, 1),
            ('速度', 'speed', 5, 100, 1),
        ]
        for label, field, low, high, unit in fields:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(low); slider.setMaximum(high)
            slider.setValue(getattr(opt,field))
            value = QLabel(str(getattr(opt,field)))
            value.setMinimumWidth(45)
            def changed(v, field=field, value=value):
                setattr(self.opt,field,v)
                value.setText(str(v))
                self.overlay.update()
            slider.valueChanged.connect(changed)
            row.addWidget(slider, 1)
            row.addWidget(value)
            root.addLayout(row)
        for label, field in [('青い光の柱', 'wisps'), ('上昇する粒子', 'particles'),
                             ('水平走査線', 'scans'), ('上に広がる光の波', 'wave')]:
            checkbox = QCheckBox(label)
            checkbox.setChecked(getattr(opt,field))
            checkbox.toggled.connect(lambda checked, field=field: setattr(opt,field,checked))
            root.addWidget(checkbox)
        row = QHBoxLayout()
        self.toggle = QPushButton('エフェクトを一時停止')
        self.toggle.clicked.connect(self.toggle_fx)
        row.addWidget(self.toggle)
        quit_button = QPushButton('終了')
        quit_button.clicked.connect(QApplication.quit)
        row.addWidget(quit_button)
        root.addLayout(row)
        self.move(35, 65)

    def toggle_fx(self):
        self.opt.enabled = not self.opt.enabled
        self.toggle.setText('エフェクトを一時停止' if self.opt.enabled else 'エフェクトを再開')
        self.overlay.update()

    def closeEvent(self, event):
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    geometry = app.primaryScreen().geometry()
    opt = Options(x=geometry.center().x(), foot_y=int(geometry.height()*.88),
                  width=max(180,int(geometry.width()*.22)),
                  height=max(320,int(geometry.height()*.60)))
    overlay = Overlay(opt)
    controls = Controls(opt, overlay)
    controls.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
