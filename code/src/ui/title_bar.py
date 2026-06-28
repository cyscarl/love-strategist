"""自定义标题栏 —— 与导航栏同色 (#E8E8E8)，显示时间，支持拖拽。"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QPoint, QTimer, QTime
from PyQt5.QtGui import QFont, QMouseEvent

C_BG = "#EDEDED"
C_TEXT = "#555555"
C_HOVER = "#E0E0E0"
C_CLOSE_HOVER = "#E81123"

BAR_HEIGHT = 48


class TitleBar(QWidget):
    """自定义标题栏。"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._window = parent
        self._drag_pos: QPoint | None = None
        self.setFixedHeight(BAR_HEIGHT)
        self.setStyleSheet(f"background-color: {C_BG};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 4, 0)
        layout.setSpacing(0)

        # 时间显示
        self._time_label = QLabel(QTime.currentTime().toString("HH:mm"))
        self._time_label.setFont(QFont("Microsoft YaHei", 16))
        self._time_label.setStyleSheet(f"color: {C_TEXT}; font-weight: 500;")
        layout.addWidget(self._time_label)

        # 余额/用量信息
        self._balance_label = QLabel("")
        self._balance_label.setFont(QFont("Microsoft YaHei", 16))
        self._balance_label.setStyleSheet(f"color: {C_TEXT}; padding-left: 8px;")
        layout.addWidget(self._balance_label)

        layout.addStretch()

        # 最小化
        min_btn = self._mk_btn("─")
        min_btn.clicked.connect(self._window.showMinimized)
        layout.addWidget(min_btn)

        # 最大化
        max_btn = self._mk_btn("□")
        max_btn.clicked.connect(self._toggle_max)
        layout.addWidget(max_btn)

        # 关闭
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(92, BAR_HEIGHT)
        close_btn.setFont(QFont("Microsoft YaHei", 22))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C_TEXT}; border: none; font-size: 28px; }}
            QPushButton:hover {{ background-color: {C_CLOSE_HOVER}; color: white; }}
        """)
        close_btn.clicked.connect(self._window.close)
        layout.addWidget(close_btn)

        # 每秒更新时间
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self._time_label.setText(QTime.currentTime().toString("HH:mm")))
        self._timer.start(1000)

    def _mk_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(92, BAR_HEIGHT)
        btn.setFont(QFont("Microsoft YaHei", 22))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C_TEXT}; border: none; font-size: 28px; }}
            QPushButton:hover {{ background-color: {C_HOVER}; }}
        """)
        return btn

    def _toggle_max(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None:
            delta = event.globalPos() - self._drag_pos
            self._window.move(self._window.pos() + delta)
            self._drag_pos = event.globalPos()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self._toggle_max()