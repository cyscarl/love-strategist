"""联系人列表（QListWidget）。

每个联系人项显示：圆形头像 + 名称 + 最后消息预览。
顶部搜索框，底部"+"新建按钮。
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QHBoxLayout, QLabel, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont

from .widgets.avatar_widget import AvatarWidget


# 样式常量
C_ITEM_HOVER = "#F5F5F5"
C_ITEM_SELECTED = "#E8F8EF"
C_BORDER = "#E5E5E5"
C_TEXT = "#333333"
C_HINT = "#999999"


class ContactItemWidget(QFrame):
    """单个联系人项的自定义 Widget。"""

    clicked = pyqtSignal(int)  # contact_id

    def __init__(self, contact_id: int, name: str, last_msg: str = "", parent=None) -> None:
        super().__init__(parent)
        self.contact_id = contact_id
        self.setFixedHeight(62)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # 头像
        self.avatar = AvatarWidget(size=44)
        self.avatar.set_fallback(name)

        # 名称 + 预览
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Microsoft YaHei", 18))
        self.name_label.setStyleSheet(f"font-weight: 500; color: {C_TEXT};")

        self.preview_label = QLabel(last_msg[:30] + ("..." if len(last_msg) > 30 else "") if last_msg else "")
        self.preview_label.setFont(QFont("Microsoft YaHei", 16))
        self.preview_label.setStyleSheet(f"color: {C_HINT};")

        text_col.addWidget(self.name_label)
        text_col.addWidget(self.preview_label)

        layout.addWidget(self.avatar)
        layout.addLayout(text_col, 1)

    def update_preview(self, name: str, last_msg: str = "") -> None:
        """更新名称和最后消息预览。"""
        self.name_label.setText(name)
        preview = last_msg[:30] + ("..." if len(last_msg) > 30 else "") if last_msg else ""
        self.preview_label.setText(preview)
        self.avatar.set_fallback(name)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.contact_id)
        super().mousePressEvent(event)


class ContactList(QWidget):
    """联系人列表面板。

    Signals:
        contact_selected(contact_id): 选中联系人
        add_contact_requested(): 请求新建联系人
        search_changed(text): 搜索文本变化
    """

    contact_selected = pyqtSignal(int)
    add_contact_requested = pyqtSignal()
    search_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: dict[int, tuple[QListWidgetItem, ContactItemWidget]] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background-color: #FFFFFF; border-bottom: 1px solid {C_BORDER};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        title = QLabel("💬 恋爱军师")
        title.setFont(QFont("Microsoft YaHei", 20))
        title.setStyleSheet("font-weight: 700; color: #333;")
        hl.addWidget(title)
        layout.addWidget(header)

        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索联系人")
        self.search_box.setFixedHeight(36)
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                border-bottom: 1px solid {C_BORDER};
                border-radius: 0;
                padding: 4px 16px;
                font-size: 18px;
                background-color: #FAFAFA;
            }}
            QLineEdit:focus {{
                background-color: #FFFFFF;
                border-bottom: 1px solid #07C160;
            }}
        """)
        self.search_box.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_box)

        # 联系人列表
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet("QListWidget { background-color: #FFFFFF; }")
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, 1)

        # 底部"+"按钮
        footer = QFrame()
        footer.setFixedHeight(48)
        footer.setStyleSheet(f"background-color: #FFFFFF; border-top: 1px solid {C_BORDER};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(0, 0, 0, 0)

        add_btn = QPushButton("＋ 新建联系人")
        add_btn.setFlat(True)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                color: #07C160;
                font-size: 19px;
                font-weight: 500;
                padding: 12px 0;
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        add_btn.clicked.connect(self.add_contact_requested.emit)
        fl.addWidget(add_btn)
        layout.addWidget(footer)

    # ------------------------------------------------------------------
    def add_contact(self, contact_id: int, name: str, last_msg: str = "") -> None:
        """添加或更新联系人项。"""
        widget = ContactItemWidget(contact_id, name, last_msg)
        widget.clicked.connect(self.contact_selected.emit)

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 64))
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        self._items[contact_id] = (item, widget)

    def remove_contact(self, contact_id: int) -> None:
        """移除联系人项。"""
        if contact_id in self._items:
            item, _ = self._items.pop(contact_id)
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)

    def update_contact(self, contact_id: int, name: str, last_msg: str = "") -> None:
        """更新联系人名称和预览。"""
        if contact_id in self._items:
            _, widget = self._items[contact_id]
            widget.update_preview(name, last_msg)

    def select_contact(self, contact_id: int) -> None:
        """高亮选中指定联系人。"""
        if contact_id in self._items:
            item, _ = self._items[contact_id]
            self.list_widget.setCurrentItem(item)

    def clear_all(self) -> None:
        """清空所有联系人。"""
        self.list_widget.clear()
        self._items.clear()

    def get_search_text(self) -> str:
        return self.search_box.text()

    # ------------------------------------------------------------------
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """列表项点击 → 查找对应 widget 并发射信号。"""
        for cid, (i, w) in self._items.items():
            if i is item:
                self.contact_selected.emit(cid)
                return
