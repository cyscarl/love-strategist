"""聊天页中间列 —— 联系人列表（按最后交流时间排序）。

顶部搜索框（模糊匹配名称或聊天内容），
无新建按钮（新建在通讯录页面）。
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QLabel, QHBoxLayout, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont

from .widgets.avatar_widget import AvatarWidget

C_BORDER = "#E5E5E5"
C_TEXT = "#333333"
C_HINT = "#999999"
C_ITEM_HOVER = "#F5F5F5"
C_BG = "#E8E8E8"


class ChatContactItem(QFrame):
    """聊天列表项。"""

    clicked = pyqtSignal(int)

    def __init__(self, contact_id: int, name: str, last_msg: str = "", avatar_path: str = "", parent=None) -> None:
        super().__init__(parent)
        self.contact_id = contact_id
        self.setFixedHeight(96)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.avatar = AvatarWidget(size=54)
        if avatar_path:
            self.avatar.set_image(avatar_path)
        else:
            self.avatar.set_fallback(name)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Microsoft YaHei", 19))
        self.name_label.setStyleSheet(f"font-weight: 500; color: {C_TEXT};")

        preview = last_msg[:7] + ("..." if len(last_msg) > 7 else "") if last_msg else ""
        self.preview_label = QLabel(preview)
        self.preview_label.setFont(QFont("Microsoft YaHei", 12))
        self.preview_label.setStyleSheet(f"color: {C_HINT};")

        text_col.addWidget(self.name_label)
        text_col.addWidget(self.preview_label)

        layout.addWidget(self.avatar)
        layout.addLayout(text_col, 1)

    def _apply_avatar(self, path: str = "") -> None:
        if path:
            self.avatar.set_image(path)
        else:
            self.avatar.set_fallback(self.name_label.text())

    def update_preview(self, name: str, last_msg: str = "", avatar_path: str = "") -> None:
        self.name_label.setText(name)
        preview = last_msg[:10] + ("..." if len(last_msg) > 10 else "") if last_msg else ""
        self.preview_label.setText(preview)
        self._apply_avatar(avatar_path)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.contact_id)
        super().mousePressEvent(event)


class ChatContactList(QWidget):
    """聊天页联系人列表。

    Signals:
        contact_selected(contact_id)
        search_changed(text)
    """

    contact_selected = pyqtSignal(int)
    search_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: dict[int, tuple[QListWidgetItem, ChatContactItem]] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 搜索框（外包容器，与联系人标签同高同色）
        search_container = QFrame()
        search_container.setFixedHeight(96)
        search_container.setStyleSheet(f"background-color: {C_BG};")
        sc_layout = QVBoxLayout(search_container)
        sc_layout.setContentsMargins(12, 20, 12, 20)
        sc_layout.setSpacing(0)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索联系人")
        self.search_box.setFixedHeight(56)
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {C_BORDER};
                border-radius: 8px;
                padding: 4px 16px;
                font-size: 18px;
                background-color: #FAFAFA;
            }}
            QLineEdit:focus {{ background-color: #FFFFFF; border-color: #07C160; }}
        """)
        self.search_box.textChanged.connect(self._on_search)
        sc_layout.addWidget(self.search_box)
        layout.addWidget(search_container)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(f"QListWidget {{ background-color: {C_BG}; }}")
        self.list_widget.itemClicked.connect(self._on_clicked)
        layout.addWidget(self.list_widget, 1)

    def add_contact(self, contact_id: int, name: str, last_msg: str = "", avatar_path: str = "") -> None:
        widget = ChatContactItem(contact_id, name, last_msg, avatar_path)
        widget.clicked.connect(self.contact_selected.emit)

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 96))
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        self._items[contact_id] = (item, widget)

    def remove_contact(self, contact_id: int) -> None:
        if contact_id in self._items:
            item, _ = self._items.pop(contact_id)
            self.list_widget.takeItem(self.list_widget.row(item))

    def update_contact(self, contact_id: int, name: str, last_msg: str = "", avatar_path: str = "") -> None:
        if contact_id in self._items:
            old_item, old_widget = self._items.pop(contact_id)
            row = self.list_widget.row(old_item)
            self.list_widget.takeItem(row)
            old_widget.hide()
            old_widget.deleteLater()
            new_widget = ChatContactItem(contact_id, name, last_msg, avatar_path)
            new_widget.clicked.connect(self.contact_selected.emit)
            new_item = QListWidgetItem()
            new_item.setSizeHint(QSize(0, 96))
            self.list_widget.insertItem(0, new_item)
            self.list_widget.setItemWidget(new_item, new_widget)
            self._items[contact_id] = (new_item, new_widget)

    def select_contact(self, contact_id: int) -> None:
        if contact_id in self._items:
            item, _ = self._items[contact_id]
            self.list_widget.setCurrentItem(item)

    def clear_all(self) -> None:
        for cid in list(self._items.keys()):
            item, widget = self._items.pop(cid)
            widget.hide()
            widget.deleteLater()
        self.list_widget.clear()
        self._items.clear()

    def _on_clicked(self, item: QListWidgetItem) -> None:
        for cid, (i, w) in self._items.items():
            if i is item:
                self.contact_selected.emit(cid)
                return

    def _on_search(self, text: str) -> None:
        """模糊匹配：名称包含搜索词，或最后消息包含搜索词。"""
        t = text.lower().strip()
        for cid, (item, widget) in self._items.items():
            if not t:
                item.setHidden(False)
                continue
            name_match = t in widget.name_label.text().lower()
            preview_match = t in widget.preview_label.text().lower()
            item.setHidden(not (name_match or preview_match))
