"""左侧导航栏 —— 轻灰色底色，深灰未选中 / 绿色选中。"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

C_BG = "#EDEDED"
C_BG_HOVER = "#E0E0E0"
C_BG_ACTIVE = "#E0E0E0"
C_TEXT = "#555555"
C_TEXT_ACTIVE = "#07C160"
C_INDICATOR = "#07C160"


class NavButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        self._active = False
        self.setText(text)
        self.setFont(QFont("Microsoft YaHei", 19))
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(120, 56)
        self.setCheckable(True)
        self.setStyleSheet(self._style(False))

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setChecked(active)
        self.setStyleSheet(self._style(active))

    def _style(self, active: bool | None = None) -> str:
        if active is None:
            active = self._active
        c = C_TEXT_ACTIVE if active else C_TEXT
        bg = C_BG_ACTIVE if active else C_BG
        border = f"3px solid {C_INDICATOR}" if active else "3px solid transparent"
        return f"""
            QPushButton {{
                background-color: {bg}; color: {c}; border: none;
                border-left: {border}; font-size: 19px; font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {C_BG_HOVER}; color: {'#07C160' if not active else C_TEXT_ACTIVE};
            }}
        """

class NavigationBar(QWidget):
    """左侧导航栏。"""

    page_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(120)
        self.setStyleSheet(f"background-color: {C_BG};")
        self._buttons: list[NavButton] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(6)

        items = ["聊天", "通讯录", "设置"]
        for i, text in enumerate(items):
            btn = NavButton(text)
            btn.clicked.connect(lambda checked, idx=i: self._on_clicked(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()
        self._buttons[0].set_active(True)

    def _on_clicked(self, index: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.set_active(i == index)
        self.page_changed.emit(index)

    def set_page(self, index: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.set_active(i == index)
