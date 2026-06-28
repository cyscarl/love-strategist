"""消息气泡 —— 宽度由内容自然决定，上限为聊天区宽度的 70%。"""

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy, QMenu, QAction, QSpacerItem,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont

from src.models.enums import SenderType, ContentType
from .avatar_widget import AvatarWidget

BUBBLE_USER = "#95EC69"
BUBBLE_TARGET = "#E8E8E8"
TEXT_PRIMARY = "#333333"


class MessageBubble(QFrame):
    """消息气泡。"""

    edit_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    insert_above_requested = pyqtSignal(int, str)

    def __init__(
        self,
        msg_id: int = 0,
        sender_type: SenderType = SenderType.USER,
        sender_name: str = "",
        content: str = "",
        content_type: ContentType = ContentType.TEXT,
        max_width: int = 400,
        avatar_path: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._msg_id = msg_id
        self._sender_type = sender_type
        self._content = content
        self._max_width = max_width
        self._build_ui(sender_name, content, avatar_path)

    @property
    def msg_id(self) -> int: return self._msg_id
    @property
    def sender_type(self) -> SenderType: return self._sender_type

    def set_max_width(self, w: int) -> None:
        self._max_width = w
        self._apply_label_width()

    def _apply_label_width(self) -> None:
        """根据文本长度决定气泡宽度：短文本=自适应，长文本=上限封顶换行。"""
        if not hasattr(self, '_content_label'):
            return
        label = self._content_label
        text = self._content
        fm = label.fontMetrics()
        # 文本实际像素宽度 + 气泡 padding
        text_w = fm.boundingRect(text).width() + 28
        if text_w < self._max_width:
            # 短文本：固定宽度 = 文本实际宽度
            label.setWordWrap(False)
            label.setFixedWidth(text_w)
        else:
            # 长文本：上限封顶 + 自动换行
            label.setFixedWidth(16777215)  # 取消 fixed
            label.setWordWrap(True)
            label.setMaximumWidth(self._max_width)
        label.updateGeometry()
        self.updateGeometry()

    def sizeHint(self) -> QSize:
        """返回考虑到 maximumWidth 约束后的实际尺寸。"""
        sh = super().sizeHint()
        if hasattr(self, '_content_label'):
            label_sh = self._content_label.sizeHint()
            # QLabel 加 padding + avatar + margins ≈ label 宽度 + 100
            bw = min(label_sh.width(), self._max_width) + 100
            sh.setWidth(min(bw, sh.width()))
        return sh

    def _build_ui(self, sender_name: str, content: str, avatar_path: str = "") -> None:
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        is_user = self._sender_type == SenderType.USER
        bubble_color = BUBBLE_USER if is_user else BUBBLE_TARGET

        avatar = AvatarWidget(size=54)
        if avatar_path:
            avatar.set_image(avatar_path)
        else:
            avatar.set_fallback(sender_name or ("我" if is_user else "TA"))

        self._content_label = QLabel(content)
        self._content_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._content_label.setTextFormat(Qt.PlainText)
        f = QFont("Microsoft YaHei", 20)
        self._content_label.setFont(f)
        self._content_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bubble_color};
                color: {TEXT_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)

        # 内容行
        # 剩余空间由 stretch=1 的弹簧填充（仿微信效果）
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)
        if is_user:
            content_row.addStretch(1)
            content_row.addWidget(self._content_label, 100)
        else:
            content_row.addWidget(self._content_label, 100)
            content_row.addStretch(1)

        # 根据文本长度设置宽度策略
        self._apply_label_width()

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(0)
        info.addLayout(content_row)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 3, 16, 3)
        root.setSpacing(10)

        if is_user:
            root.addStretch()
            root.addLayout(info)
            root.addWidget(avatar, alignment=Qt.AlignTop)
        else:
            root.addWidget(avatar, alignment=Qt.AlignTop)
            root.addLayout(info)
            root.addStretch()

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #FFF; border: 1px solid #E5E5E5; border-radius: 4px; padding: 4px 0; }
            QMenu::item { padding: 6px 24px; font-size: 18px; }
            QMenu::item:selected { background-color: #E8F8EF; color: #07C160; }
        """)
        copy_a = menu.addAction("复制")
        edit_a = menu.addAction("编辑内容")
        del_a = menu.addAction("删除")
        menu.addSeparator()
        ins_t = menu.addAction("在上方插入对方消息")
        ins_u = menu.addAction("在上方插入己方消息")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == copy_a:
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(self._content)
        elif action == edit_a:
            self.edit_requested.emit(self._msg_id)
        elif action == del_a:
            self.delete_requested.emit(self._msg_id)
        elif action == ins_t:
            self.insert_above_requested.emit(self._msg_id, "target")
        elif action == ins_u:
            self.insert_above_requested.emit(self._msg_id, "user")
