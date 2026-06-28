"""设置页右侧 —— LLM 配置 / 本地存储 / 关于（分页）。"""

import os
import subprocess

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QFrame, QScrollArea, QStackedWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from src.utils.config import load_config, save_config, reload_config
from src.utils.logger import LOG_DIR, logger
from src.utils.config import DATA_DIR
from src.utils.thread_utils import debounce_button
from src.services.llm_service import test_connection, list_models

C_BG = "#FFFFFF"
C_BORDER = "#E5E5E5"
C_TEXT = "#333333"
C_HINT = "#999999"
C_GREEN = "#07C160"
C_RED = "#FA5151"

PROVIDERS = {
    "自定义":    {"url": "", "models": [], "balance_url": ""},
    "OpenAI":    {"url": "https://api.openai.com/v1",          "models": ["gpt-4o", "gpt-4o-mini", "gpt-4"], "balance_url": ""},
    "DeepSeek":  {"url": "https://api.deepseek.com/v1",        "models": ["deepseek-v4-pro", "deepseek-v4-flash"], "balance_url": "https://api.deepseek.com/user/balance"},
    "智谱 GLM":  {"url": "https://open.bigmodel.cn/api/paas/v4", "models": ["glm-4", "glm-4-flash"], "balance_url": ""},
}

def _get_version() -> str:
    """从 pyproject.toml 读取版本号。兼容 Python 3.9+。"""
    try:
        import os, re
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "pyproject.toml")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "0.1.0"

VERSION = _get_version()

# 用量查询关键词（按优先级）
_BALANCE_KEYS = (
    "balance", "total_balance", "total_used", "available", "remaining",
    "total_granted", "granted", "used", "quota", "credits",
    "余额", "可用", "已用", "总额", "剩余",
)

# 用量类关键词（优先匹配，用量）
_USAGE_KEYS = ("total_used", "used", "usage", "consumed", "已用", "消耗")
# 余额类关键词（余额）
_BALANCE_KEYS = ("balance", "total_balance", "available", "remaining",
                  "total_granted", "granted", "quota", "credits",
                  "余额", "可用", "剩余", "总额")

def _parse_balance(data) -> str | None:
    """从 JSON 提取用量或余额，跳过零值，附带货币和标签。"""
    candidates = []  # (value_float, display_str)
    _collect_amounts(data, candidates)
    nonzero = [(v, s) for v, s in candidates if v > 0]
    if nonzero:
        nonzero.sort(reverse=True)
        _, best = nonzero[0]
        return best
    if candidates:
        return candidates[0][1]
    return None

def _collect_amounts(node, out: list, currency: str = ""):
    """递归收集金额，区分用量/余额标签。"""
    if isinstance(node, dict):
        cur = node.get("currency", currency) or currency
        for k in _USAGE_KEYS:
            if k in node and node[k] is not None:
                _add_value(node[k], cur, "用量", out)
        for k in _BALANCE_KEYS:
            if k in node and node[k] is not None:
                _add_value(node[k], cur, "余额", out)
        for v in node.values():
            _collect_amounts(v, out, cur)
    elif isinstance(node, list):
        for item in node[:20]:
            _collect_amounts(item, out, currency)

def _add_value(v, cur: str, label: str, out: list):
    try:
        fv = float(v)
        s = f"{label}: {fv:.2f}{cur}" if cur else f"{label}: {fv:.2f}"
        out.append((fv, s))
    except (ValueError, TypeError):
        if isinstance(v, str) and v.strip():
            out.append((0, f"{label}: {v.strip()}"))

def _set_opts_visible(layout, visible: bool) -> None:
    for i in range(layout.count()):
        w = layout.itemAt(i).widget()
        if w: w.setVisible(visible)
def _get_help_path() -> str:
    """获取帮助文档路径（开发/打包兼容）。"""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "help.html")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "help.html")

HELP_PATH = _get_help_path()


class SettingsDetail(QWidget):
    config_saved = pyqtSignal()
    balance_updated = pyqtSignal(str)  # 余额文本，显示在窗口标题

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status_label: QLabel | None = None
        self._balance_timer: QTimer | None = None
        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        self._stack = QStackedWidget()

        # 页0: LLM 配置
        self._stack.addWidget(self._build_llm_page())
        # 页1: 本地存储
        self._stack.addWidget(self._build_storage_page())
        # 页2: 关于
        self._stack.addWidget(self._build_about_page())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)

    # ==================================================================
    # LLM 配置页
    # ==================================================================

    def _build_llm_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {C_BG}; border: none; }}")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 24, 32, 24)
        layout.setSpacing(12)

        # 供应商
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(list(PROVIDERS.keys()))
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        layout.addLayout(self._row("供应商", self._provider_combo))

        # API URL
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://api.openai.com/v1")
        layout.addLayout(self._row("请求地址", self._url_input))

        # API Key
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("sk-...")
        layout.addLayout(self._row("API Key", self._key_input))

        # 模型
        model_row = QHBoxLayout()
        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        model_row.addWidget(self._model_combo, 1)
        refresh_btn = QPushButton("⟳")
        refresh_btn.setFixedWidth(48)
        refresh_btn.setStyleSheet(f"QPushButton{{background:#F0F0F0; color:{C_TEXT}; border:none; border-radius:4px; font-size:16px;}} QPushButton:hover{{background:#E5E5E5;}}")
        refresh_btn.clicked.connect(lambda: (self._on_refresh_models(), debounce_button(refresh_btn)))
        model_row.addWidget(refresh_btn)
        layout.addLayout(self._row("模型", model_row))

        # 超时
        opt = QHBoxLayout()
        opt.setSpacing(16)
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 120); self._timeout_spin.setValue(30)
        opt.addWidget(QLabel("超时（秒）")); opt.addWidget(self._timeout_spin)
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0); self._temp_spin.setSingleStep(0.1); self._temp_spin.setValue(0.8)
        opt.addWidget(QLabel("温度")); opt.addWidget(self._temp_spin)
        opt.addStretch()
        layout.addLayout(opt)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        save_btn = QPushButton("保存配置")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(f"QPushButton{{background:{C_GREEN}; color:white; border:none; border-radius:4px; padding:8px 20px; font-size:18px; font-weight:600;}} QPushButton:hover{{background:#06AD56;}}")
        save_btn.clicked.connect(self._on_save)
        test_btn = QPushButton("测试连接")
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.setStyleSheet(f"QPushButton{{background:#F0F0F0; color:{C_TEXT}; border:none; border-radius:4px; padding:8px 20px; font-size:18px;}} QPushButton:hover{{background:#E5E5E5;}}")
        test_btn.clicked.connect(lambda: (self._on_test(), debounce_button(test_btn)))
        self._status_label = QLabel("")
        btn_row.addWidget(save_btn); btn_row.addWidget(test_btn); btn_row.addWidget(self._status_label, 1)
        layout.addLayout(btn_row)

        # ---- 用量查询 ----
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet(f"color:{C_BORDER};"); layout.addWidget(line)

        bal_title_row = QHBoxLayout()
        bal_title_row.addWidget(QLabel("用量查询"))
        self._balance_switch = QPushButton("开启")
        self._balance_switch.setCheckable(True); self._balance_switch.setFixedWidth(80)
        self._balance_switch.setCursor(Qt.PointingHandCursor)
        self._balance_switch.setStyleSheet(f"QPushButton{{background:{C_BG}; color:{C_TEXT}; border:1px solid {C_BORDER}; border-radius:4px; font-size:16px;}} QPushButton:hover{{background:#F5F5F5;}}")
        self._balance_switch.clicked.connect(self._on_balance_toggle)
        bal_title_row.addWidget(self._balance_switch)
        self._balance_refresh_btn = QPushButton("⟳")
        self._balance_refresh_btn.setFixedWidth(48)
        self._balance_refresh_btn.setStyleSheet(f"QPushButton{{background:#F0F0F0; color:{C_TEXT}; border:none; border-radius:4px; font-size:16px;}} QPushButton:hover{{background:#E5E5E5;}}")
        self._balance_refresh_btn.clicked.connect(lambda: (self._on_balance_query(), debounce_button(self._balance_refresh_btn)))
        bal_title_row.addWidget(self._balance_refresh_btn)
        bal_title_row.addStretch()
        layout.addLayout(bal_title_row)

        self._balance_url_input = QLineEdit()
        self._balance_url_input.setPlaceholderText("用量查询 API URL（留空则自动推断）")
        bal_url_row, self._balance_url_label = self._row("查询地址", self._balance_url_input, return_label=True)
        layout.addLayout(bal_url_row)

        self._balance_opts = QHBoxLayout()
        self._balance_opts.setSpacing(16)
        self._balance_interval = QSpinBox()
        self._balance_interval.setRange(1, 60); self._balance_interval.setValue(5)
        self._balance_opts.addWidget(QLabel("间隔（分钟）")); self._balance_opts.addWidget(self._balance_interval)
        self._balance_timeout = QSpinBox()
        self._balance_timeout.setRange(1, 30); self._balance_timeout.setValue(5)
        self._balance_opts.addWidget(QLabel("超时（秒）")); self._balance_opts.addWidget(self._balance_timeout)
        self._balance_opts.addStretch()
        layout.addLayout(self._balance_opts)

        layout.addStretch()
        scroll.setWidget(content)
        page = QWidget()
        pl = QVBoxLayout(page); pl.setContentsMargins(0,0,0,0); pl.addWidget(scroll)
        return page

    # ==================================================================
    # 本地存储页
    # ==================================================================

    def _build_storage_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        open_btn = QPushButton("打开日志目录")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(f"QPushButton{{background:{C_BG}; color:{C_TEXT}; border:1px solid {C_BORDER}; border-radius:4px; padding:8px 16px; font-size:18px;}} QPushButton:hover{{background:#F5F5F5;}}")
        open_btn.clicked.connect(lambda: os.startfile(LOG_DIR) if hasattr(os, 'startfile') else None)
        layout.addWidget(open_btn)

        data_btn = QPushButton("打开数据目录")
        data_btn.setCursor(Qt.PointingHandCursor)
        data_btn.setStyleSheet(f"QPushButton{{background:{C_BG}; color:{C_TEXT}; border:1px solid {C_BORDER}; border-radius:4px; padding:8px 16px; font-size:18px;}} QPushButton:hover{{background:#F5F5F5;}}")
        data_btn.clicked.connect(lambda: os.startfile(DATA_DIR) if hasattr(os, 'startfile') else None)
        layout.addWidget(data_btn)
        layout.addStretch()
        return page

    # ==================================================================
    # 关于页
    # ==================================================================

    def _build_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        layout.addWidget(QLabel(f"聊天助手 Love Strategist"))
        layout.addWidget(QLabel(f"版本 {VERSION}"))

        layout.addWidget(self._title("更新设置"))
        self._repo_url_input = QLineEdit()
        self._repo_url_input.setReadOnly(True)
        self._repo_url_input.setStyleSheet(f"QLineEdit{{border:1px solid {C_BORDER};border-radius:4px;padding:6px 10px;font-size:18px;background:#F5F5F5;}}")
        layout.addLayout(self._row("仓库地址", self._repo_url_input))

        update_btn = QPushButton("检查更新")
        update_btn.setCursor(Qt.PointingHandCursor)
        update_btn.setStyleSheet(f"QPushButton{{background:{C_BG}; color:{C_TEXT}; border:1px solid {C_BORDER}; border-radius:4px; padding:8px 16px; font-size:18px;}} QPushButton:hover{{background:#F5F5F5;}}")
        update_btn.clicked.connect(self._on_check_update)
        layout.addWidget(update_btn)

        help_btn = QPushButton("使用帮助")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setStyleSheet(f"QPushButton{{background:{C_BG}; color:{C_TEXT}; border:1px solid {C_BORDER}; border-radius:4px; padding:8px 16px; font-size:18px;}} QPushButton:hover{{background:#F5F5F5;}}")
        help_btn.clicked.connect(self._on_help)
        layout.addWidget(help_btn)
        layout.addStretch()
        return page

    # ==================================================================
    # 公共
    # ==================================================================

    def set_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    # ==================================================================
    # 事件处理
    # ==================================================================

    def _load_config(self) -> None:
        config = load_config()
        llm = config.get("llm", {})
        url = llm.get("base_url", "")
        matched = "自定义"
        for name, info in PROVIDERS.items():
            if info["url"] and url.startswith(info["url"].rstrip("/")):
                matched = name; break
        self._provider_combo.setCurrentText(matched)
        self._url_input.setText(url)
        self._key_input.setText(llm.get("api_key", ""))
        self._model_combo.clear()
        if matched in PROVIDERS and PROVIDERS[matched]["models"]:
            self._model_combo.addItems(PROVIDERS[matched]["models"])
        self._model_combo.setCurrentText(llm.get("model", ""))
        self._timeout_spin.setValue(llm.get("timeout", 30))
        self._temp_spin.setValue(llm.get("temperature", 0.8))
        # 更新配置
        upd = config.get("update", {})
        self._repo_url_input.setText(upd.get("repo_url", ""))
        # 用量查询配置
        bal = config.get("balance", {})
        enabled = bal.get("enabled", False)
        self._balance_switch.setChecked(enabled)
        self._balance_switch.setText("关闭" if enabled else "开启")
        self._balance_refresh_btn.setVisible(enabled)
        self._balance_url_input.setText(bal.get("url", ""))
        self._balance_interval.setValue(bal.get("interval_minutes", 5))
        self._balance_timeout.setValue(bal.get("timeout_seconds", 5))
        _set_opts_visible(self._balance_opts, enabled)
        self._balance_url_input.setVisible(enabled)
        self._balance_url_label.setVisible(enabled)
        if enabled:
            self._start_balance_timer()

    def _on_save(self) -> None:
        config = load_config()
        config["llm"] = {
            "api_key": self._key_input.text().strip(),
            "base_url": self._url_input.text().strip(),
            "model": self._model_combo.currentText(),
            "timeout": self._timeout_spin.value(),
            "temperature": self._temp_spin.value(),
            "max_tokens": config["llm"].get("max_tokens", 2048),
        }
        config["update"] = {
            "repo_url": self._repo_url_input.text().strip(),
            "auto_check": config.get("update", {}).get("auto_check", False),
        }
        config["balance"] = {
            "enabled": self._balance_switch.isChecked(),
            "url": self._balance_url_input.text().strip(),
            "interval_minutes": self._balance_interval.value(),
            "timeout_seconds": self._balance_timeout.value(),
        }
        en = self._balance_switch.isChecked()
        _set_opts_visible(self._balance_opts, en)
        self._balance_refresh_btn.setVisible(en)
        self._balance_url_input.setVisible(en)
        self._balance_url_label.setVisible(en)
        save_config(config)
        reload_config()
        self._status_label.setText("已保存")
        self._status_label.setStyleSheet(f"color:{C_GREEN};font-size:17px;")
        self.config_saved.emit()
        # 余额定时器
        if self._balance_switch.isChecked():
            self._start_balance_timer()
        else:
            self._stop_balance_timer()

    def _on_test(self) -> None:
        self._on_save()
        self._status_label.setText("测试中...")
        self._status_label.setStyleSheet(f"color:{C_HINT};font-size:17px;")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, self._do_test)

    def _do_test(self) -> None:
        ok, msg = test_connection()
        if ok:
            self._status_label.setText("连接成功！")
            self._status_label.setStyleSheet(f"color:{C_GREEN};font-size:17px;")
        elif "超时" in msg:
            self._status_label.setText("连接超时")
            self._status_label.setStyleSheet(f"color:{C_RED};font-size:17px;")
        else:
            self._status_label.setText("失败: " + msg[:40])
            self._status_label.setStyleSheet(f"color:{C_RED};font-size:17px;")

    def _on_provider_changed(self, name: str) -> None:
        if name in PROVIDERS:
            info = PROVIDERS[name]
            if info["url"]: self._url_input.setText(info["url"])
            self._model_combo.clear()
            if info["models"]: self._model_combo.addItems(info["models"])
            if info.get("balance_url"): self._balance_url_input.setText(info["balance_url"])

    def _on_refresh_models(self) -> None:
        from PyQt5.QtWidgets import QMessageBox
        current = self._model_combo.currentText()
        models, err = list_models(
            base_url=self._url_input.text().strip(),
            api_key=self._key_input.text().strip(),
        )
        if models:
            self._model_combo.clear(); self._model_combo.addItems(models)
            idx = self._model_combo.findText(current)
            if idx >= 0: self._model_combo.setCurrentIndex(idx)
            else: self._model_combo.setCurrentText(current)
            QMessageBox.information(self, "刷新模型", f"已获取 {len(models)} 个模型")
        else:
            QMessageBox.warning(self, "刷新模型", f"获取失败\n{err}")

    def _on_balance_toggle(self) -> None:
        checked = self._balance_switch.isChecked()
        self._balance_switch.setText("关闭" if checked else "开启")
        self._balance_refresh_btn.setVisible(checked)
        self._balance_url_input.setVisible(checked)
        self._balance_url_label.setVisible(checked)
        _set_opts_visible(self._balance_opts, checked)
        self._on_save()  # 冷保存开关状态
        if checked:
            self._do_balance_query()
            self._start_balance_timer()
        else:
            self._stop_balance_timer()
            self.balance_updated.emit("")

    def _on_balance_query(self) -> None:
        self._on_save()  # 先保存配置
        self.balance_updated.emit(" | 查询中...")
        self._do_balance_query()

    def _do_balance_query(self) -> None:
        import requests
        config = load_config()
        llm = config.get("llm", {})
        api_key = llm.get("api_key", "")
        bal = config.get("balance", {})
        url = bal.get("url", "").strip()
        timeout = bal.get("timeout_seconds", 5)
        if not api_key:
            self.balance_updated.emit(" | 未配置Key")
            return
        if not url:
            url = f"{llm.get('base_url', '').rstrip('/')}/user/balance"
        try:
            resp = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)
            if resp.status_code == 200:
                raw = resp.text
                logger.info(f"用量查询响应: {raw[:500]}")
                data = resp.json()
                val = _parse_balance(data)
                text = f" | {val}" if val is not None else ""
                self.balance_updated.emit(text)
                return
            elif resp.status_code == 401:
                self.balance_updated.emit(" | 用量: 无权限")
            else:
                self.balance_updated.emit(f" | 用量: HTTP {resp.status_code}")
        except Exception as e:
            self.balance_updated.emit(" | 用量查询超时")

    def _start_balance_timer(self) -> None:
        self._stop_balance_timer()
        config = load_config()
        interval = config.get("balance", {}).get("interval_minutes", 5) * 60000
        self._balance_timer = QTimer(self)
        self._balance_timer.timeout.connect(self._do_balance_query)
        self._balance_timer.start(interval)
        self._do_balance_query()

    def _stop_balance_timer(self) -> None:
        if self._balance_timer:
            self._balance_timer.stop()
            self._balance_timer = None

    def _on_check_update(self) -> None:
        from PyQt5.QtWidgets import QMessageBox
        config = load_config()
        repo_url = config.get("update", {}).get("repo_url", "")
        if not repo_url:
            QMessageBox.information(self, "检查更新", "请先在设置中填写 GitHub 仓库地址")
            return
        self._status_label.setText("检查中...")
        self._status_label.setStyleSheet(f"color:{C_HINT};font-size:17px;")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._do_check_update(repo_url))

    def _do_check_update(self, repo_url: str) -> None:
        from PyQt5.QtWidgets import QMessageBox
        from src.services.update_checker import check_github_update, download_and_update
        result = check_github_update(repo_url, VERSION)
        if result is None:
            self._status_label.setText("")
            QMessageBox.information(self, "检查更新", "当前已是最新版本")
        elif isinstance(result, dict) and result.get("latest"):
            self._status_label.setText("")
            zip_url = result.get("zip_url", "")
            if zip_url:
                reply = QMessageBox.question(
                    self, "检查更新",
                    f"检测到新版本 {result['latest']}\n\n{result.get('body', '')}\n是否自动下载并更新？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._status_label.setText("下载中...")
                    self._status_label.setStyleSheet(f"color:{C_HINT};font-size:17px;")
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(100, lambda: self._do_download(zip_url))
            else:
                reply = QMessageBox.question(
                    self, "检查更新",
                    f"检测到新版本 {result['latest']}\n\n{result.get('body', '')}\n是否前往下载页面？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    import webbrowser
                    webbrowser.open(result.get("url", repo_url + "/releases/latest"))
        else:
            self._status_label.setText("检查失败")
            self._status_label.setStyleSheet(f"color:{C_RED};font-size:17px;")

    def _do_download(self, zip_url: str) -> None:
        from PyQt5.QtWidgets import QMessageBox, QProgressDialog
        from PyQt5.QtCore import QTimer
        from src.services.update_checker import download_and_update

        progress = QProgressDialog("正在下载更新...", "取消", 0, 100, self)
        progress.setWindowTitle("更新")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setAutoClose(False)
        progress.canceled.connect(lambda: None)  # 不允许取消

        def update_progress(msg):
            if "%" in msg:
                try:
                    pct = int(msg.split("%")[0].split()[-1])
                    progress.setValue(pct)
                except ValueError:
                    pass
            progress.setLabelText(msg)

        ok, msg = download_and_update(zip_url, callback=update_progress)
        progress.close()

        if ok:
            QMessageBox.information(self, "更新", "新版本已下载完成。\n\n请关闭应用，双击运行目录下的 _update.bat 完成更新。")
        else:
            QMessageBox.warning(self, "更新失败", msg)

    def _on_help(self) -> None:
        os.makedirs(os.path.dirname(HELP_PATH), exist_ok=True)
        if not os.path.exists(HELP_PATH):
            with open(HELP_PATH, "w", encoding="utf-8") as f:
                f.write("<html><body><h1>使用帮助</h1><p>内容待补充</p></body></html>")
        os.startfile(HELP_PATH) if hasattr(os, 'startfile') else None

    # ==================================================================
    # 辅助
    # ==================================================================

    def _row(self, label: str, widget, return_label: bool = False):
        """标签固定宽度 + 控件左对齐。return_label=True 返回 (row, label_widget)。"""
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(96)
        lbl.setStyleSheet(f"color:{C_TEXT};")
        row.addWidget(lbl)
        if isinstance(widget, QHBoxLayout):
            row.addLayout(widget, 1)
        else:
            row.addWidget(widget, 1)
        return (row, lbl) if return_label else row

    def _title(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setFont(QFont("Microsoft YaHei", 19))
        l.setStyleSheet(f"font-weight:700; color:{C_TEXT};")
        return l

    def _input_s(self) -> str:
        return f"QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox{{border:1px solid {C_BORDER};border-radius:4px;padding:6px 10px;font-size:18px;background:{C_BG};}}"
