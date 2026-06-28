"""好感度进度条（-100 ~ 100）。

颜色规则：
- 负值（-100 ~ 0）：红色系
- 零：灰色
- 正值（0 ~ 100）：绿色系

显示格式：数值 + 进度条
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt


def _affinity_color(score: int) -> str:
    """根据好感度值返回颜色。"""
    if score < 0:
        # 红色：从浅红到深红
        ratio = abs(score) / 100.0
        r = 250
        g = int(81 - ratio * 50)
        b = int(81 - ratio * 50)
        return f"rgb({r}, {g}, {b})"
    elif score == 0:
        return "#999999"
    else:
        # 绿色：从浅绿到微信绿
        ratio = score / 100.0
        r = int(7 + (1 - ratio) * 150)
        g = int(193 - (1 - ratio) * 100)
        b = int(96 - (1 - ratio) * 60)
        return f"rgb({r}, {g}, {b})"


class AffinityBar(QWidget):
    """好感度进度条控件。

    用法:
        bar = AffinityBar()
        bar.set_value(45)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._value: int = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标签
        self._label = QLabel("好感度")
        self._label.setStyleSheet("font-size: 17px; color: #999999;")

        # 进度条
        self._bar = QProgressBar()
        self._bar.setMinimum(-100)
        self._bar.setMaximum(100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(10)

        # 数值
        self._score_label = QLabel("0")
        self._score_label.setStyleSheet("font-size: 19px; font-weight: 700;")
        self._score_label.setFixedWidth(40)
        self._score_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self._label)
        layout.addWidget(self._bar, 1)
        layout.addWidget(self._score_label)

        self._update_style()

    # ------------------------------------------------------------------
    @property
    def value(self) -> int:
        return self._value

    def set_value(self, score: int) -> None:
        """设置好感度数值（-100 ~ 100）。"""
        self._value = max(-100, min(100, score))
        self._bar.setValue(self._value)
        self._score_label.setText(str(self._value))
        self._update_style()

    def _update_style(self) -> None:
        """根据当前值更新样式。"""
        color = _affinity_color(self._value)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 5px;
                background-color: #E5E5E5;
            }}
            QProgressBar::chunk {{
                border-radius: 5px;
                background-color: {color};
            }}
        """)
        self._score_label.setStyleSheet(
            f"font-size: 19px; font-weight: 700; color: {color};"
        )
