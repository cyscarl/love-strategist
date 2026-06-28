"""通讯录页右侧 —— 联系人详情。

展示：头像（可导入+自动方形裁剪）、名称、备注栏、
好感度条、简要人格摘要、"更多"按钮打开完整画像弹窗。
"""

import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QFileDialog, QMenu,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap

from .widgets.avatar_widget import AvatarWidget
from .widgets.affinity_bar import AffinityBar

C_BG = "#FFFFFF"
C_BORDER = "#E5E5E5"
C_TEXT = "#333333"
C_HINT = "#999999"
C_GREEN = "#07C160"


class ContactDetail(QWidget):
    """联系人详情面板。

    Signals:
        avatar_changed(contact_id, path)
        name_changed(contact_id, name)
        notes_changed(contact_id, notes)
        more_clicked(contact_id)
    """

    avatar_changed = pyqtSignal(int, str)
    name_changed = pyqtSignal(int, str)
    notes_changed = pyqtSignal(int, str)
    more_clicked = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    chat_requested = pyqtSignal(int)            # 跳转聊天页

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._contact_id: int = 0
        self._suppress_notes: bool = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 24)
        layout.setSpacing(16)

        # ---- 头像 + 名称 + 更多按钮 ----
        top_row = QHBoxLayout()

        self.avatar = AvatarWidget(size=108)
        self.avatar.setCursor(Qt.PointingHandCursor)
        self.avatar.mousePressEvent = self._on_avatar_click  # type: ignore

        name_col = QVBoxLayout()
        name_col.setSpacing(4)

        self.name_label = QLabel("")
        self.name_label.setFont(QFont("Microsoft YaHei", 27))
        self.name_label.setStyleSheet(f"font-weight: 700; color: {C_TEXT};")
        # 双击编辑姓名
        self.name_label.mouseDoubleClickEvent = self._on_name_double_click

        self.affinity_bar = AffinityBar()
        self.affinity_bar.setVisible(False)

        self._self_hint = QLabel("这是你自己")
        self._self_hint.setFont(QFont("Microsoft YaHei", 16))
        self._self_hint.setStyleSheet(f"color: {C_HINT};")
        self._self_hint.setVisible(False)

        name_col.addWidget(self.name_label)
        name_col.addWidget(self.affinity_bar)
        name_col.addWidget(self._self_hint)

        self.more_btn = QPushButton("...")
        self.more_btn.setFixedSize(48, 48)
        self.more_btn.setCursor(Qt.PointingHandCursor)
        self.more_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_HINT};
                border: 1px solid {C_BORDER};
                border-radius: 6px;
                font-size: 29px;
                font-weight: bold;
                text-align: center;
                padding: 0;
            }}
            QPushButton:hover {{ background-color: #F5F5F5; color: {C_TEXT}; }}
        """)
        self.more_btn.clicked.connect(self._show_more_menu)

        top_row.addWidget(self.avatar)
        top_row.addLayout(name_col, 1)
        top_row.addWidget(self.more_btn, alignment=Qt.AlignTop)
        layout.addLayout(top_row)

        # ---- 分割线 ----
        layout.addWidget(self._divider())

        # ---- 备注 ----
        notes_header = QLabel("备注")
        notes_header.setFont(QFont("Microsoft YaHei", 19))
        notes_header.setStyleSheet(f"color: {C_HINT}; font-weight: 500;")
        layout.addWidget(notes_header)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("添加备注（不影响助手决策）...")
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setFont(QFont("Microsoft YaHei", 19))
        self.notes_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {C_BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                color: {C_TEXT};
            }}
            QTextEdit:focus {{ border-color: {C_GREEN}; }}
        """)
        self.notes_edit.textChanged.connect(self._on_notes_changed)
        layout.addWidget(self.notes_edit)

        # ---- 简要人格摘要 ----
        self._summary_header = QLabel("人格摘要")
        summary_header = self._summary_header
        summary_header.setFont(QFont("Microsoft YaHei", 19))
        summary_header.setStyleSheet(f"color: {C_HINT}; font-weight: 500;")
        layout.addWidget(summary_header)

        from PyQt5.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(60)
        scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: 1px solid {C_BORDER}; border-radius: 4px; }}")
        self._summary_scroll = scroll
        self.summary_label = QLabel("暂无分析数据")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignTop | Qt.AlignJustify)
        self.summary_label.setFont(QFont("Microsoft YaHei", 19))
        self.summary_label.setStyleSheet(f"color: {C_TEXT}; padding: 4px; background: transparent;")
        scroll.setWidget(self.summary_label)
        layout.addWidget(scroll, 1)

        layout.addSpacing(8)

        # 发消息按钮
        self._chat_btn = QPushButton("发消息")
        chat_btn = self._chat_btn
        chat_btn.setCursor(Qt.PointingHandCursor)
        chat_btn.setFixedHeight(38)
        chat_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_GREEN}; color: white; border: none;
                border-radius: 4px; font-size: 20px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #06AD56; }}
        """)
        chat_btn.clicked.connect(lambda: self.chat_requested.emit(self._contact_id))
        layout.addWidget(chat_btn)

        layout.addStretch()

    # ------------------------------------------------------------------
    def load_contact(self, contact_id: int, name: str) -> None:
        """加载联系人基本信息。"""
        self._contact_id = contact_id
        self.name_label.setText(name)
        self.avatar.set_fallback(name)
        self._suppress_notes = True
        self.notes_edit.clear()
        self._suppress_notes = False

    def set_affinity(self, score: int) -> None:
        self.affinity_bar.setVisible(True)
        self.affinity_bar.set_value(score)

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text if text else "暂无分析数据")

    def set_notes(self, text: str) -> None:
        self._suppress_notes = True
        self.notes_edit.setText(text)
        self._suppress_notes = False

    def set_avatar_path(self, path: str) -> None:
        if path and os.path.exists(path):
            self.avatar.set_image(path)
        elif path:
            # 旧路径不存在（可能因历史 bug 保存到错误目录），尝试修正到正确目录
            from src.utils.config import DATA_DIR
            alt = os.path.join(DATA_DIR, "avatars", os.path.basename(path))
            if os.path.exists(alt):
                self.avatar.set_image(alt)

    def set_is_self(self, is_self: bool) -> None:
        """'自己' 不显示人格摘要、好感度、更多按钮、发消息；好感度位置显示'这是你自己'。"""
        self.affinity_bar.hide()
        self.more_btn.setVisible(not is_self)
        if hasattr(self, '_summary_header'):
            self._summary_header.setVisible(not is_self)
            self._summary_scroll.setVisible(not is_self)
        if hasattr(self, '_chat_btn'):
            self._chat_btn.setVisible(not is_self)
        if hasattr(self, '_self_hint'):
            self._self_hint.setVisible(is_self)

    def _on_notes_changed(self) -> None:
        if not self._suppress_notes:
            self.notes_changed.emit(self._contact_id, self.notes_edit.toPlainText())

    # ------------------------------------------------------------------
    def _on_name_double_click(self, event) -> None:
        """双击姓名 → 编辑。"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "编辑姓名", "联系人姓名:", text=self.name_label.text())
        if ok and name.strip():
            self.name_label.setText(name.strip())
            self.name_changed.emit(self._contact_id, name.strip())

    def _show_more_menu(self) -> None:
        """点击 ... 弹出菜单。"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #FFF; border: 1px solid #E5E5E5; border-radius: 4px; padding: 4px 0; }
            QMenu::item { padding: 8px 32px; font-size: 18px; }
            QMenu::item:selected { background-color: #E8F8EF; color: #07C160; }
        """)
        edit_action = menu.addAction("查看详情")
        menu.addSeparator()
        delete_action = menu.addAction("删除联系人")

        action = menu.exec_(self.more_btn.mapToGlobal(
            self.more_btn.rect().bottomLeft()))

        if action == edit_action:
            self.more_clicked.emit(self._contact_id)
        elif action == delete_action:
            self.delete_requested.emit(self._contact_id)

    def _on_avatar_click(self, event) -> None:
        """点击头像 → 选择图片 → 裁剪对话框 → 保存。"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择头像", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not path:
            return

        from .widgets.crop_dialog import CropDialog
        dlg = CropDialog(path, parent=self)
        if dlg.exec_():
            from src.utils.config import DATA_DIR
            save_dir = os.path.join(DATA_DIR, "avatars")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f"avatar_{self._contact_id}.png")
            dlg.save_cropped(save_path)
            self.avatar.set_image(save_path)
            self.avatar_changed.emit(self._contact_id, save_path)

    # ------------------------------------------------------------------
    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {C_BORDER};")
        return line
