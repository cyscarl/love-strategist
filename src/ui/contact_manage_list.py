"""通讯录页中间列 —— 联系人管理列表。

顶部搜索框（模糊匹配名称），
第二行"新建联系人"按钮，
列表按名称首字母排列。
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QLabel, QHBoxLayout, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont

from .widgets.avatar_widget import AvatarWidget

C_BG = "#E8E8E8"
C_BORDER = "#E5E5E5"
C_TEXT = "#333333"
C_HINT = "#999999"
C_GREEN = "#07C160"


class ContactManageItem(QFrame):
    """通讯录列表项。"""

    clicked = pyqtSignal(int)

    def __init__(self, contact_id: int, name: str, avatar_path: str = "", parent=None) -> None:
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

        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Microsoft YaHei", 19))
        self.name_label.setStyleSheet(f"font-weight: 400; color: {C_TEXT};")

        layout.addWidget(self.avatar)
        layout.addWidget(self.name_label, 1)

    def update_name(self, name: str, avatar_path: str = "") -> None:
        self.name_label.setText(name)
        if avatar_path:
            self.avatar.set_image(avatar_path)
        else:
            self.avatar.set_fallback(name)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.contact_id)
        super().mousePressEvent(event)


class ContactManageList(QWidget):
    """通讯录管理列表。

    Signals:
        contact_selected(contact_id)
        add_contact_requested()
    """

    contact_selected = pyqtSignal(int)
    add_contact_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: dict[int, tuple[QListWidgetItem, ContactManageItem]] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 搜索框（外包容器）
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

        # 新建按钮
        add_btn = QPushButton("＋ 新建联系人")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(40)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_BG};
                color: {C_GREEN};
                border: none;
                border-bottom: 1px solid {C_BORDER};
                font-size: 18px;
                font-weight: 500;
                text-align: left;
                padding-left: 16px;
            }}
            QPushButton:hover {{ background-color: #F5F5F5; }}
        """)
        add_btn.clicked.connect(self.add_contact_requested.emit)
        layout.addWidget(add_btn)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(f"QListWidget {{ background-color: {C_BG}; }}")
        self.list_widget.itemClicked.connect(self._on_clicked)
        layout.addWidget(self.list_widget, 1)

    # ------------------------------------------------------------------
    def add_contact(self, contact_id: int, name: str, avatar_path: str = "") -> None:
        """添加联系人（调用方应保证按字母序传入，或调用后 rebuild）。"""
        widget = ContactManageItem(contact_id, name, avatar_path)
        widget.clicked.connect(self.contact_selected.emit)

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 96))
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        self._items[contact_id] = (item, widget)

    def rebuild_sorted(self) -> None:
        """销毁全部项并按名称首字母重建（安全：旧 widget 全部 deleteLater）。"""
        from src.utils.config import get_self_contact_id
        from src.storage.contact_dao import get_contact_by_id
        # 保存数据
        entries = [(cid, w.name_label.text()) for cid, (_, w) in self._items.items()]
        # 安全销毁所有旧 widget
        for cid in list(self._items.keys()):
            _, w = self._items.pop(cid)
            w.hide()
            w.deleteLater()
        self.list_widget.clear()
        # "自己"始终在第一位（按 config 中的 id 识别），其余按名称排序
        self_id = get_self_contact_id()
        self_entries = [e for e in entries if e[0] == self_id]
        other_entries = [e for e in entries if e[0] != self_id]
        other_entries.sort(key=lambda x: x[1].lower())
        for cid, name in self_entries + other_entries:
            contact = get_contact_by_id(cid)
            av = contact.avatar if contact else ""
            widget = ContactManageItem(cid, name, av)
            widget.clicked.connect(self.contact_selected.emit)
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 96))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            self._items[cid] = (item, widget)

    def remove_contact(self, contact_id: int) -> None:
        if contact_id in self._items:
            item, widget = self._items.pop(contact_id)
            widget.hide()
            widget.deleteLater()
            self.list_widget.takeItem(self.list_widget.row(item))

    def update_contact(self, contact_id: int, name: str, avatar_path: str = "") -> None:
        if contact_id in self._items:
            _, widget = self._items[contact_id]
            widget.update_name(name, avatar_path)

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

    # ------------------------------------------------------------------
    def _on_clicked(self, item: QListWidgetItem) -> None:
        for cid, (i, w) in self._items.items():
            if i is item:
                self.contact_selected.emit(cid)
                return

    def _on_search(self, text: str) -> None:
        """按名称模糊过滤。"""
        for cid, (item, widget) in self._items.items():
            hidden = text.lower() not in widget.name_label.text().lower() if text else False
            item.setHidden(hidden)
