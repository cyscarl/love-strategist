"""人物画像弹窗（精简版：无头像，仅姓名+好感度数字，可滚动详情）。"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .widgets.affinity_bar import _affinity_color
from src.utils.thread_utils import debounce_button

C_BG = "#FFFFFF"
C_TEXT = "#333333"
C_HINT = "#999999"
C_BORDER = "#E5E5E5"
C_GREEN = "#07C160"
C_SECTION_BG = "#FAFAFA"

_KEY_CN = {
    "age": "年龄", "occupation": "职业", "city": "城市",
    "reply_style": "回复风格",
    "回复风格": "回复风格",
}

def _translate_keys(d: dict) -> dict:
    return {_KEY_CN.get(k, k): v for k, v in d.items()}


class ProfileDialog(QDialog):
    """人物画像弹窗。"""

    refresh_requested = pyqtSignal(int)
    edit_requested = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._contact_id: int = 0
        self._drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(380, 480)
        self.resize(400, 520)
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

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(0)

        # 标题栏
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setStyleSheet("background-color: #EDEDED; border-radius: 10px 10px 0 0;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 0, 4, 0)
        tl = QLabel("人物画像")
        tl.setFont(QFont("Microsoft YaHei", 13))
        tl.setStyleSheet("color: #555; font-weight: 500; background: transparent;")
        bl.addWidget(tl); bl.addStretch()
        cb = QPushButton("✕")
        cb.setFixedSize(36, 36); cb.setFont(QFont("Microsoft YaHei", 12))
        cb.setCursor(Qt.PointingHandCursor)
        cb.setStyleSheet("QPushButton{background:transparent;color:#555;border:none;font-size:16px;} QPushButton:hover{background:#E81123;color:white;border-radius:0 8px 0 0;}")
        cb.clicked.connect(self.reject)
        bl.addWidget(cb)
        root.addWidget(bar)

        # 内容卡片
        card = QWidget()
        card.setStyleSheet(f"background-color: {C_BG}; border-radius: 0 0 10px 10px;")
        cl_main = QVBoxLayout(card)
        cl_main.setContentsMargins(0, 0, 0, 0)
        cl_main.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {C_BG}; border: none; }}")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 姓名
        self.name_label = QLabel("")
        self.name_label.setFont(QFont("Microsoft YaHei", 22))
        self.name_label.setStyleSheet(f"font-weight: 700; color: {C_TEXT};")
        layout.addWidget(self.name_label)

        layout.addWidget(self._divider())

        # 基本信息
        self._add_section(layout, "基本信息", "basic_info_value")
        # 性格特征
        self._add_section(layout, "性格特征", "personality_value")
        # 兴趣爱好
        self._add_section(layout, "兴趣爱好", "hobbies_value")
        # 行为习惯
        self._add_section(layout, "行为习惯", "behavior_value")
        # 关系摘要
        self._add_section(layout, "关系摘要", "summary_value")

        layout.addStretch()
        scroll.setWidget(content)
        cl_main.addWidget(scroll, 1)

        # 底部按钮
        footer = QFrame()
        footer.setStyleSheet(f"QFrame {{ background-color: {C_SECTION_BG}; border-top: 1px solid {C_BORDER}; }}")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)

        refresh_btn = QPushButton("重新分析")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {C_GREEN}; color: white; border: none;
                border-radius: 4px; padding: 8px 20px; font-size: 16px; font-weight: 500; }}
            QPushButton:hover {{ background-color: #06AD56; }}
        """)
        refresh_btn.clicked.connect(lambda: (self.refresh_requested.emit(self._contact_id), debounce_button(refresh_btn)))

        edit_btn = QPushButton("编辑")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};
                border-radius: 4px; padding: 8px 20px; font-size: 16px; }}
            QPushButton:hover {{ background-color: #F5F5F5; }}
        """)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._contact_id))

        fl.addWidget(refresh_btn)
        fl.addWidget(edit_btn)
        fl.addStretch()
        cl_main.addWidget(footer)

        root.addWidget(card)

        # 保存引用
        self._basic_label = content.findChild(QLabel, "basic_info_value")
        self._personality_label = content.findChild(QLabel, "personality_value")
        self._hobbies_label = content.findChild(QLabel, "hobbies_value")
        self._behavior_label = content.findChild(QLabel, "behavior_value")
        self._summary_label = content.findChild(QLabel, "summary_value")

    def load_profile(self, contact_id: int, name: str, profile: dict) -> None:
        self._contact_id = contact_id
        self.name_label.setText(name)

        bi = profile.get("basic_info", {})
        bi_cn = _translate_keys(bi)
        basic_text = "\n".join(f"{k}: {v}" for k, v in bi_cn.items()) if bi_cn else "暂无信息"
        self._basic_label.setText(basic_text)

        per = profile.get("personality", {})
        traits = per.get("traits", []) + per.get("tags", [])
        self._personality_label.setText(" · ".join(traits) if traits else "暂无分析")

        hob = profile.get("hobbies", [])
        self._hobbies_label.setText("  ".join(f"#{h}" for h in hob) if hob else "暂无记录")

        bp = profile.get("behavior_patterns", {})
        bp_cn = _translate_keys(bp)
        bp_text = " / ".join(f"{k}: {v}" for k, v in bp_cn.items()) if bp_cn else "暂无分析"
        self._behavior_label.setText(bp_text)

        self._summary_label.setText(profile.get("summary", "暂无摘要"))

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {C_BORDER};")
        return line

    def _section_header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont("Microsoft YaHei", 16))
        label.setStyleSheet(f"color: {C_HINT}; font-weight: 500;")
        return label

    def _add_section(self, parent, title: str, obj_name: str) -> None:
        parent.addWidget(self._section_header(title))
        sec_scroll = QScrollArea()
        sec_scroll.setWidgetResizable(True)
        sec_scroll.setFrameShape(QFrame.NoFrame)
        sec_scroll.setMaximumHeight(100)
        sec_scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }}")
        value_label = QLabel("暂无数据")
        value_label.setObjectName(obj_name)
        value_label.setFont(QFont("Microsoft YaHei", 18))
        value_label.setWordWrap(True)
        value_label.setStyleSheet(f"color: {C_TEXT}; margin-left: 8px; background: transparent;")
        value_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        sec_scroll.setWidget(value_label)
        parent.addWidget(sec_scroll)
