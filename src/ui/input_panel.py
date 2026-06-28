"""输入面板 —— 微信风格。

布局：
┌──────────────────────────────────────────┐
│  [正在思考...]                            │ ← 思考状态（求助时显示）
│  [建议1] [建议2] [建议3] [刷新] [策略]    │ ← 建议行（召唤后显示）
├──────────────────────────────────────────┤
│  [文本输入框（顶格，多行）]               │
├──────────────────────────────────────────┤
│  [对方发送]    [求助]    [发送]           │ ← 按钮行
└──────────────────────────────────────────┘
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QFrame, QLabel,
)
from PyQt5.QtCore import Qt, pyqtSignal
from src.utils.thread_utils import debounce_button
from PyQt5.QtGui import QFont, QKeyEvent


C_BG = "#FFFFFF"
C_BORDER = "#E5E5E5"
C_GREEN = "#07C160"
C_GREEN_HOVER = "#06AD56"
C_TEXT = "#333333"
C_HINT = "#999999"


class InputPanel(QWidget):
    """输入面板。"""

    send_clicked = pyqtSignal(str, str)
    summon_clicked = pyqtSignal()
    strategy_clicked = pyqtSignal()
    suggestion_selected = pyqtSignal(str)
    refresh_suggestions = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background-color: {C_BG}; border-top: 1px solid {C_BORDER};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(6)

        # ---- 思考状态行（默认隐藏） ----
        self.thinking_label = QLabel("正在思考...")
        self.thinking_label.setFont(QFont("Microsoft YaHei", 19))
        self.thinking_label.setStyleSheet(f"color: {C_HINT}; padding: 2px 4px;")
        self.thinking_label.setVisible(False)
        layout.addWidget(self.thinking_label)

        # ---- 建议行（默认隐藏，在文本框上方） ----
        self.suggestions_frame = QFrame()
        self.suggestions_frame.setVisible(False)
        sf = QHBoxLayout(self.suggestions_frame)
        sf.setContentsMargins(0, 0, 0, 0)
        sf.setSpacing(6)

        self.suggestion_btns: list[QPushButton] = []
        for i in range(3):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C_BG}; color: {C_GREEN};
                    border: 1px solid {C_GREEN}; border-radius: 4px;
                    padding: 5px 10px; font-size: 18px;
                }}
                QPushButton:hover {{ background-color: #E8F8EF; }}
            """)
            btn.clicked.connect(lambda checked, idx=i: self._on_suggestion(idx))
            sf.addWidget(btn, 1)
            self.suggestion_btns.append(btn)

        refresh_btn = QPushButton("⟳")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedWidth(48)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_BG}; color: {C_HINT};
                border: 1px solid {C_BORDER}; border-radius: 4px;
                padding: 5px 6px; font-size: 18px;
            }}
            QPushButton:hover {{ color: {C_TEXT}; }}
        """)
        refresh_btn.clicked.connect(lambda: (self.refresh_suggestions.emit(), debounce_button(refresh_btn)))

        strategy_btn = QPushButton("策略")
        strategy_btn.setCursor(Qt.PointingHandCursor)
        strategy_btn.setFixedWidth(48)
        strategy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_BG}; color: {C_HINT};
                border: 1px solid {C_BORDER}; border-radius: 4px;
                padding: 5px 6px; font-size: 18px;
            }}
            QPushButton:hover {{ color: {C_TEXT}; }}
        """)
        strategy_btn.clicked.connect(self.strategy_clicked.emit)

        sf.addWidget(refresh_btn)
        sf.addWidget(strategy_btn)
        layout.addWidget(self.suggestions_frame)

        # ---- 文本输入框 ----
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("输入消息...")
        self.text_edit.setFixedHeight(168)
        self.text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self._show_text_menu)
        self.text_edit.setFont(QFont("Microsoft YaHei", 20))
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {C_BORDER}; border-radius: 4px;
                padding: 8px 12px; background-color: {C_BG}; color: {C_TEXT};
            }}
            QTextEdit:focus {{ border-color: {C_GREEN}; }}
        """)
        layout.addWidget(self.text_edit)

        # ---- 按钮行 ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.target_btn = QPushButton("对方发送")
        self.target_btn.setCursor(Qt.PointingHandCursor)
        self.target_btn.setFixedHeight(34)
        self.target_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_BG}; color: {C_GREEN};
                border: 1px solid {C_GREEN}; border-radius: 4px;
                padding: 6px 14px; font-size: 19px; font-weight: 500;
            }}
            QPushButton:hover {{ background-color: #E8F8EF; }}
        """)
        self.target_btn.clicked.connect(lambda: self._do_send("target"))

        self.summon_btn = QPushButton("求助")
        self.summon_btn.setCursor(Qt.PointingHandCursor)
        self.summon_btn.setFixedHeight(34)
        self.summon_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F0F0F0; color: {C_TEXT};
                border: none; border-radius: 4px;
                padding: 6px 14px; font-size: 18px;
            }}
            QPushButton:hover {{ background-color: #E5E5E5; }}
        """)
        self.summon_btn.clicked.connect(lambda: (self._on_summon(), debounce_button(self.summon_btn)))

        self.send_btn = QPushButton("发送")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setFixedHeight(34)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_GREEN}; color: white;
                border: none; border-radius: 4px;
                padding: 6px 20px; font-size: 18px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {C_GREEN_HOVER}; }}
        """)
        self.send_btn.clicked.connect(lambda: self._do_send("user"))

        btn_row.addWidget(self.target_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.summon_btn)
        btn_row.addWidget(self.send_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    def get_input_text(self) -> str:
        return self.text_edit.toPlainText().strip()

    def clear_input(self) -> None:
        self.text_edit.clear()

    def set_input_text(self, text: str) -> None:
        self.text_edit.setText(text)
        self.text_edit.setFocus()
        c = self.text_edit.textCursor()
        c.movePosition(c.End)
        self.text_edit.setTextCursor(c)

    def show_thinking(self) -> None:
        """立即显示"正在思考..."。"""
        self.thinking_label.setVisible(True)
        self.suggestions_frame.setVisible(False)

    def set_suggestions(self, suggestions: list[str]) -> None:
        """显示建议，隐藏思考状态。"""
        self.thinking_label.setVisible(False)
        if not suggestions:
            self.suggestions_frame.setVisible(False)
            return
        self._suggestion_texts = suggestions
        for i, btn in enumerate(self.suggestion_btns):
            if i < len(suggestions):
                s = suggestions[i]
                btn.setText(s[:9] + "..." if len(s) > 12 else s)
                btn.setToolTip(s)
                btn.setVisible(True)
            else:
                btn.setVisible(False)
        self.suggestions_frame.setVisible(True)

    # ------------------------------------------------------------------
    def _on_summon(self) -> None:
        """点击求助：立即显示思考状态 + 发射信号。"""
        self.show_thinking()
        self.summon_clicked.emit()

    def _do_send(self, sender: str) -> None:
        content = self.get_input_text()
        if content:
            self.send_clicked.emit(sender, content)

    def _on_suggestion(self, idx: int) -> None:
        texts = getattr(self, '_suggestion_texts', [])
        if idx < len(texts):
            self.suggestion_selected.emit(texts[idx])

    def _show_text_menu(self, pos) -> None:
        """中文右键菜单。"""
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background:#FFF; border:1px solid #E5E5E5; border-radius:4px; padding:4px 0; } QMenu::item { padding:6px 24px; font-size:18px; } QMenu::item:selected { background:#E8F8EF; color:#07C160; }")
        te = self.text_edit
        for text, slot, shortcut in [
            ("撤销", te.undo, "Ctrl+Z"),
            ("重做", te.redo, "Ctrl+Y"),
            (None, None, None),
            ("剪切", te.cut, "Ctrl+X"),
            ("复制", te.copy, "Ctrl+C"),
            ("粘贴", te.paste, "Ctrl+V"),
            ("删除", lambda: te.textCursor().removeSelectedText(), "Delete"),
            (None, None, None),
            ("全选", te.selectAll, "Ctrl+A"),
        ]:
            if text is None:
                menu.addSeparator()
            else:
                a = menu.addAction(f"{text}\t{shortcut}")
                a.triggered.connect(slot)
        menu.exec_(self.text_edit.mapToGlobal(pos))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self._do_send("user")
        else:
            super().keyPressEvent(event)
