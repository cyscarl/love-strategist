"""基础对话框 —— 无框 + 自定义标题栏，与主窗口风格一致。"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QMouseEvent

C_BG = "#EDEDED"
C_TEXT = "#555555"
C_CLOSE_HOVER = "#E81123"


class BaseDialog(QDialog):
    """无框对话框基类，自带标题栏。"""

    def __init__(self, parent=None, title: str = "") -> None:
        super().__init__(parent)
        self._drag_pos: QPoint | None = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._title_text = title
        self._build_frame()

    def _build_frame(self) -> None:
        """构建标题栏 + 内容区的外框。子类重写 _build_content 填充内容。"""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        outer.setSpacing(0)

        # 内容卡片（白底圆角）
        card = QWidget()
        card.setObjectName("dialog_card")
        card.setStyleSheet("""
            QWidget#dialog_card {
                background-color: #FFFFFF;
                border-radius: 12px;
            }
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # 标题栏
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setStyleSheet(f"background-color: {C_BG}; border-radius: 12px 12px 0 0;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 0, 4, 0)

        title_label = QLabel(self._title_text)
        title_label.setFont(QFont("Microsoft YaHei", 13))
        title_label.setStyleSheet(f"color: {C_TEXT}; font-weight: 500; background: transparent;")
        bl.addWidget(title_label)
        bl.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setFont(QFont("Microsoft YaHei", 12))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C_TEXT}; border: none; font-size: 16px; }}
            QPushButton:hover {{ background-color: {C_CLOSE_HOVER}; color: white; border-radius: 0 8px 0 0; }}
        """)
        close_btn.clicked.connect(self.reject)
        bl.addWidget(close_btn)
        cl.addWidget(bar)

        # 内容区（子类填充）
        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(20, 16, 20, 16)
        self._content_layout.setSpacing(12)
        cl.addLayout(self._content_layout, 1)

        outer.addWidget(card)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None:
            delta = event.globalPos() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPos()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
