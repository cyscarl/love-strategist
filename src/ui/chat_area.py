"""聊天区域 —— 消息气泡列表，支持右键菜单。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox, QLabel,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont

from src.models.enums import SenderType, ContentType
from src.storage.message_dao import (
    get_message_by_id, update_message, delete_message, create_message,
)
from src.utils.logger import logger
from .widgets.message_bubble import MessageBubble

C_BG = "#FFFFFF"


class ChatArea(QWidget):
    """聊天区域。

    Signals:
        load_older(contact_id, before_id): 滚动到顶部，传入最旧消息 id
        message_changed(): 消息被编辑/删除/插入后发射
    """

    load_older = pyqtSignal(int, int)  # contact_id, before_id
    message_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._contact_id: int | None = None
        self._contact_name: str = ""
        self._contact_avatar: str = ""
        self._items: list[tuple[MessageBubble, QListWidgetItem]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部联系人姓名栏
        self._header = QWidget()
        self._header.setFixedHeight(96)
        self._header.setStyleSheet("background-color: #FFFFFF;")
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(20, 0, 20, 0)
        self._header_name = QLabel("")
        self._header_name.setFont(QFont("Microsoft YaHei", 20))
        self._header_name.setStyleSheet("font-weight: 700; color: #333;")
        hl.addWidget(self._header_name)
        hl.addStretch()
        layout.addWidget(self._header)

        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(f"QListWidget {{ background-color: {C_BG}; border: none; }}")
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.verticalScrollBar().valueChanged.connect(self._on_scroll)
        layout.addWidget(self.list_widget, 1)

    # ------------------------------------------------------------------
    def set_contact(self, contact_id: int, name: str, avatar: str = "") -> None:
        """切换联系人。"""
        self._contact_id = contact_id
        self._contact_name = name
        self._contact_avatar = avatar
        self._header_name.setText(name)
        self.clear()

    def add_message(self, msg: dict) -> None:
        """追加一条消息到末尾。"""
        try:
            bubble = self._create_bubble(msg)
            item = QListWidgetItem()
            item.setSizeHint(bubble.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, bubble)
            self._items.append((bubble, item))
            self._scroll_to_bottom()
        except Exception as e:
            logger.error(f"add_message 失败: {e}\nmsg keys={list(msg.keys()) if msg else 'None'}")

    def prepend_messages(self, msgs: list[dict]) -> None:
        """在顶部批量插入历史消息。"""
        for msg in reversed(msgs):
            bubble = self._create_bubble(msg)
            item = QListWidgetItem()
            item.setSizeHint(bubble.sizeHint())
            self.list_widget.insertItem(0, item)
            self.list_widget.setItemWidget(item, bubble)
            self._items.insert(0, (bubble, item))

    def clear(self) -> None:
        """安全清空所有消息。

        用 deleteLater 而非 setItemWidget(item, None) ——
        后者会触发 Qt 立即销毁 C++ widget 导致 segfault。
        """
        for bubble, _ in self._items:
            try:
                bubble.edit_requested.disconnect()
                bubble.delete_requested.disconnect()
                bubble.insert_above_requested.disconnect()
            except Exception:
                pass
            bubble.hide()
            bubble.deleteLater()
        self._items.clear()
        self.list_widget.clear()

    def get_messages(self) -> list[dict]:
        """返回当前显示的消息列表（供外部使用）。"""
        return [{"msg_id": b.msg_id, "sender_type": b.sender_type} for b, _ in self._items]

    # ------------------------------------------------------------------
    # 右键菜单处理
    # ------------------------------------------------------------------

    def _on_edit_message(self, msg_id: int) -> None:
        msg = get_message_by_id(msg_id)
        if msg is None:
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "编辑消息", "修改内容:", msg.content
        )
        if ok and text.strip():
            update_message(msg_id, text.strip())
            # 延迟发射：等当前事件处理器返回后再刷新，防止 widget 被自身回调删除
            QTimer.singleShot(0, self.message_changed.emit)
            logger.debug(f"消息已编辑: id={msg_id}")

    def _on_delete_message(self, msg_id: int) -> None:
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这条消息吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            delete_message(msg_id)
            QTimer.singleShot(0, self.message_changed.emit)
            logger.debug(f"消息已删除: id={msg_id}")

    def _on_insert_above(self, msg_id: int, sender_type: str) -> None:
        """在指定消息上方插入一条新消息。"""
        if self._contact_id is None:
            return
        role = "己方" if sender_type == "user" else "对方"
        text, ok = QInputDialog.getMultiLineText(
            self, "插入消息",
            f"输入{role}消息内容（将插入到本条消息上方）:"
        )
        if ok and text.strip():
            new_msg = create_message(self._contact_id, SenderType(sender_type), text.strip())
            # 找到目标消息在列表中的位置
            insert_pos = -1
            for i, (bubble, _) in enumerate(self._items):
                if bubble.msg_id == msg_id:
                    insert_pos = i
                    break
            if insert_pos >= 0:
                bubble = self._create_bubble({
                    "id": new_msg.id, "sender_type": SenderType(sender_type),
                    "sender_name": self._contact_name if sender_type == "target" else "我",
                    "content": text.strip(),
                    "avatar_path": self._contact_avatar if sender_type == "target" else "",
                })
                item = QListWidgetItem()
                item.setSizeHint(bubble.sizeHint())
                self.list_widget.insertItem(insert_pos, item)
                self.list_widget.setItemWidget(item, bubble)
                self._items.insert(insert_pos, (bubble, item))
            else:
                # fallback: 刷新全部
                QTimer.singleShot(0, self.message_changed.emit)
            logger.debug(f"消息已插入: above={msg_id}")

    # ------------------------------------------------------------------
    def _create_bubble(self, msg: dict) -> MessageBubble:
        max_w = self._calc_max_width()
        bubble = MessageBubble(
            msg_id=msg.get("id", 0),
            sender_type=msg.get("sender_type", SenderType.USER),
            sender_name=msg.get("sender_name", ""),
            content=msg.get("content", ""),
            content_type=msg.get("content_type", ContentType.TEXT),
            max_width=max_w,
            avatar_path=msg.get("avatar_path", ""),
        )
        bubble.edit_requested.connect(self._on_edit_message)
        bubble.delete_requested.connect(self._on_delete_message)
        bubble.insert_above_requested.connect(self._on_insert_above)
        return bubble

    # ------------------------------------------------------------------
    def _calc_max_width(self) -> int:
        """气泡最大宽度 = 自身宽度的 70%。"""
        return max(180, int(self.width() * 0.70))

    def refresh_all_bubbles(self) -> None:
        """强制所有气泡重新计算宽度（用于初始加载后）。"""
        new_w = self._calc_max_width()
        for bubble, item in self._items:
            try:
                bubble.set_max_width(new_w)
                bubble.adjustSize()
                item.setSizeHint(bubble.sizeHint())
            except Exception:
                pass
        self.list_widget.doItemsLayout()

    def resizeEvent(self, event) -> None:
        """ChatArea 大小变化 → 更新所有已有气泡宽度。"""
        super().resizeEvent(event)
        new_w = self._calc_max_width()
        for bubble, item in self._items:
            try:
                bubble.set_max_width(new_w)
                item.setSizeHint(bubble.sizeHint())
            except Exception:
                pass
        self.list_widget.doItemsLayout()

    def _scroll_to_bottom(self) -> None:
        """延迟滚动到底部（等布局完成后再滚）。"""
        QTimer.singleShot(10, self._do_scroll)

    def _do_scroll(self) -> None:
        try:
            scrollbar = self.list_widget.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass

    def _on_scroll(self, value: int) -> None:
        if value == 0 and self._contact_id is not None and self._items:
            oldest_id = self._items[0][0].msg_id
            if oldest_id:
                self.load_older.emit(self._contact_id, oldest_id)
