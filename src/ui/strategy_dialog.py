"""策略调整弹窗。

模态对话框，用户输入当前想法或建议，智能体据此重新生成回复策略。
边框使用橙色 (#FF9F00) 突出显示，区别于普通对话框。
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


C_BG = "#FFFFFF"
C_TEXT = "#333333"
C_HINT = "#999999"
C_BORDER = "#FF9F00"
C_WARNING = "#FF9F00"


class StrategyDialog(QDialog):
    """策略调整弹窗。

    Signals:
        confirmed(text): 用户确认输入的想法文本
    """

    confirmed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._drag_pos = None
        self.setWindowTitle("策略调整")
        self.setMinimumSize(420, 300)
        self.resize(440, 320)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None:
            self.move(self.pos() + e.globalPos() - self._drag_pos)
            self._drag_pos = e.globalPos()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # 外层（透明背景）→ 内层（白色 + 橙色边框）
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        inner = QFrame()
        inner.setObjectName("strategy_inner")
        inner.setStyleSheet(f"""
            QFrame#strategy_inner {{
                background-color: {C_BG};
                border: 2px solid {C_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("🧠 策略调整")
        title.setFont(QFont("Microsoft YaHei", 20))
        title.setStyleSheet(f"font-weight: 700; color: {C_TEXT}; border: none;")

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_HINT};
                border: none;
                font-size: 21px;
            }}
            QPushButton:hover {{ color: {C_TEXT}; }}
        """)
        close_btn.clicked.connect(self.reject)

        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(close_btn)
        layout.addLayout(title_row)

        # 说明文字
        hint = QLabel("告诉智能体你的想法或当前情况，它将重新制定回复策略：")
        hint.setFont(QFont("Microsoft YaHei", 17))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {C_HINT}; border: none;")
        layout.addWidget(hint)

        # 输入区
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("例如：她今天好像不太开心，聊得有点冷淡。帮我换个轻松有趣的话题，最好能让她笑一笑。")
        self.text_edit.setMinimumHeight(100)
        self.text_edit.setFont(QFont("Microsoft YaHei", 18))
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid #E5E5E5;
                border-radius: 6px;
                padding: 8px 12px;
                background-color: #FAFAFA;
                color: {C_TEXT};
            }}
            QTextEdit:focus {{ border-color: {C_WARNING}; }}
        """)
        layout.addWidget(self.text_edit)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #666;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 18px;
            }
            QPushButton:hover { background-color: #E5E5E5; }
        """)
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("重新生成策略")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_WARNING};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 18px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #E08F00; }}
        """)
        from src.utils.thread_utils import debounce_button
        confirm_btn.clicked.connect(lambda: (self._on_confirm(), debounce_button(confirm_btn)))

        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

        outer.addWidget(inner)

    # ------------------------------------------------------------------
    def get_input(self) -> str:
        """获取用户输入。"""
        return self.text_edit.toPlainText().strip()

    def set_input(self, text: str) -> None:
        """预设输入内容。"""
        self.text_edit.setText(text)
        self.text_edit.setFocus()

    # ------------------------------------------------------------------
    def _on_confirm(self) -> None:
        """确认按钮：校验非空后发射信号。"""
        text = self.get_input()
        if not text:
            self.text_edit.setFocus()
            self.text_edit.setStyleSheet(self.text_edit.styleSheet() + """
                QTextEdit { border-color: #FA5151; }
            """)
            return
        self.confirmed.emit(text)
        self.accept()
