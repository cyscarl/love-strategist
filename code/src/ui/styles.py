"""集中式 QSS 样式管理。

定义颜色常量、字体规范和全局 QSS 样式表。
参考：docs/ui布局参考.md
"""

# ============================================================
# 颜色方案
# ============================================================
COLORS = {
    # 主色
    "primary": "#07C160",        # 微信绿
    "primary_hover": "#06AD56",
    "primary_light": "#E8F8EF",

    # 辅色
    "secondary": "#1AAD19",

    # 背景
    "bg_main": "#EDEDED",
    "bg_white": "#FFFFFF",
    "bg_card": "#FFFFFF",

    # 分割线
    "border": "#D9D9D9",
    "border_light": "#E5E5E5",

    # 文字
    "text_primary": "#333333",
    "text_secondary": "#999999",
    "text_hint": "#B2B2B2",

    # 语义色
    "danger": "#FA5151",
    "warning": "#FF9F00",
    "info": "#10AEFF",

    # 气泡
    "bubble_user": "#95EC69",     # 我方气泡（绿色）
    "bubble_target": "#FFFFFF",   # 对方气泡（白色）
}

# ============================================================
# 字体规范
# ============================================================
FONTS = {
    "contact_name": "font-size: 19px; font-weight: 500;",
    "message_body": "font-size: 19px; font-weight: 400;",
    "title": "font-size: 21px; font-weight: 700;",
    "button": "font-size: 18px; font-weight: 500;",
}


def _build_global_qss() -> str:
    """构建全局 QSS 样式表。"""
    c = COLORS
    return f"""
    /* 全局 */
    QWidget {{
        font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
        font-size: 20px;
        color: {c["text_primary"]};
    }}

    /* 主窗口 */
    QMainWindow {{
        background-color: {c["bg_main"]};
    }}

    /* 滚动条 */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c["border"]};
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c["text_hint"]};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* 按钮 */
    QPushButton {{
        background-color: {c["primary"]};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 16px;
        font-size: 18px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c["primary_hover"]};
    }}
    QPushButton:pressed {{
        background-color: {c["secondary"]};
    }}
    QPushButton:disabled {{
        background-color: {c["border"]};
        color: {c["text_hint"]};
    }}

    /* 输入框 */
    QLineEdit {{
        border: 1px solid {c["border"]};
        border-radius: 4px;
        padding: 6px 10px;
        background-color: {c["bg_white"]};
    }}
    QLineEdit:focus {{
        border-color: {c["primary"]};
    }}

    /* 文本编辑 */
    QTextEdit {{
        border: 1px solid {c["border"]};
        border-radius: 4px;
        padding: 6px 10px;
        background-color: {c["bg_white"]};
    }}
    QTextEdit:focus {{
        border-color: {c["primary"]};
    }}

    /* 下拉框 */
    QComboBox {{
        border: 1px solid {c["border"]};
        border-radius: 4px;
        padding: 4px 10px;
        background-color: {c["bg_white"]};
    }}

    /* 列表 */
    QListWidget {{
        border: none;
        background-color: {c["bg_white"]};
        outline: none;
    }}
    QListWidget::item {{
        border-bottom: 1px solid {c["border_light"]};
    }}
    QListWidget::item:selected {{
        background-color: {c["primary_light"]};
    }}

    /* 进度条 */
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {c["bg_main"]};
        height: 8px;
        text-align: center;
        font-size: 17px;
    }}
    QProgressBar::chunk {{
        border-radius: 4px;
        background-color: {c["primary"]};
    }}

    /* 对话框 */
    QDialog {{
        background-color: {c["bg_white"]};
    }}

    /* 工具提示 */
    QToolTip {{
        background-color: #FFFFFF;
        color: #333333;
        border: 1px solid #E5E5E5;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 16px;
    }}
    """


GLOBAL_QSS = _build_global_qss()
