"""设置页中间列 —— 设置项类别列表。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel,
)
from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtGui import QFont

C_BG = "#E8E8E8"
C_TEXT = "#333333"


class SettingsList(QWidget):
    """设置类别列表。"""

    category_selected = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setStyleSheet(f"QListWidget {{ background-color: {C_BG}; }}")
        self.list_widget.itemClicked.connect(self._on_clicked)

        for text in ["LLM 配置", "本地存储", "关于"]:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 48))
            self.list_widget.addItem(item)
            label = QLabel(f"  {text}")
            label.setFont(QFont("Microsoft YaHei", 19))
            label.setStyleSheet(f"color: {C_TEXT}; padding: 4px 16px;")
            self.list_widget.setItemWidget(item, label)

        layout.addWidget(self.list_widget, 1)

    def _on_clicked(self, item: QListWidgetItem) -> None:
        self.category_selected.emit(self.list_widget.row(item))
