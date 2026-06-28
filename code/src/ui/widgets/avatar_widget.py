"""头像控件 —— 方形圆角（仿微信），默认蓝底白字。"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath, QColor, QFont


DEFAULT_BG = "#4A90D9"   # 蓝底
DEFAULT_FG = "#FFFFFF"   # 白字
RADIUS = 4               # 圆角半径


class AvatarWidget(QLabel):
    """方形圆角头像。

    用法:
        avatar = AvatarWidget(size=40)
        avatar.set_image("path/to/avatar.png")   # 设置图片
        avatar.set_fallback("小美")              # 设置文字占位
    """

    def __init__(self, size: int = 40, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self._pixmap: QPixmap | None = None
        self._fallback_char: str = ""
        self._bg_color: str = DEFAULT_BG

        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)

    def set_image(self, path: str | None) -> None:
        if path:
            pix = QPixmap(path)
            if not pix.isNull():
                self._pixmap = pix
                self.update()
                return
        self._pixmap = None
        self.update()

    def set_fallback(self, char: str) -> None:
        self._fallback_char = char[0] if char else ""
        self._pixmap = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self._size, self._size, RADIUS, RADIUS)
        painter.setClipPath(path)

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self._size, self._size,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (self._size - scaled.width()) // 2
            y = (self._size - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(DEFAULT_BG))
            painter.drawRoundedRect(0, 0, self._size, self._size, RADIUS, RADIUS)

            if self._fallback_char:
                painter.setPen(QColor(DEFAULT_FG))
                font = QFont("Microsoft YaHei", self._size // 2)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(self.rect(), Qt.AlignCenter, self._fallback_char)
