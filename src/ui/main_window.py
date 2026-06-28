"""主窗口 —— 微信三栏布局。

Phase 7 重写：导航栏 + 中间列 + 右侧内容，QStackedWidget 页面切换。

页面：
  聊天（默认）：中间=聊天列表，右侧=聊天区+输入面板
  通讯录：中间=联系人管理，右侧=联系人详情
  设置：中间=设置类别，右侧=具体设置项
"""

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout, QStackedWidget,
    QInputDialog, QApplication,
)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainterPath
import ctypes

from .styles import GLOBAL_QSS
from .navigation_bar import NavigationBar
from .chat_contact_list import ChatContactList
from .contact_manage_list import ContactManageList
from .settings_list import SettingsList
from .chat_area import ChatArea
from .input_panel import InputPanel
from .contact_detail import ContactDetail
from .settings_detail import SettingsDetail
from .profile_dialog import ProfileDialog
from .strategy_dialog import StrategyDialog

from src.models.enums import SenderType, ContentType
from src.storage.contact_dao import (
    create_contact, get_all_contacts, get_contact_by_id, update_contact,
)
from src.storage.message_dao import (
    create_message, get_recent, get_before, get_last_message,
)
from src.utils.config import get_self_contact_id, set_self_contact_id
from src.storage.profile_dao import get_profile
from src.controllers.chat_controller import ChatController
from src.utils.logger import logger

C_MIDDLE_W = 312


def _pinyin_key(name: str) -> str:
    """将中文名称转为拼音排序键（A-Z）。pypinyin 不可用时回退 Unicode。"""
    try:
        from pypinyin import lazy_pinyin
        return "".join(lazy_pinyin(name)).lower()
    except ImportError:
        return name.lower()


class MainWindow(QMainWindow):
    """三栏布局主窗口。"""

    def __init__(self, controller: ChatController | None = None) -> None:
        super().__init__()
        self._ctrl = controller
        self._current_contact_id: int | None = None
        self._current_page: int = 0

        self._setup_window()
        self._build_nav()
        self._build_middle_panels()
        self._build_right_panels()
        self._apply_styles()
        self._wire_signals()
        self._switch_page(0)
        self._load_contacts()

    # ==================================================================
    # UI 构建
    # ==================================================================

    def _setup_window(self) -> None:
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1280, 960)
        self.setMinimumSize(960, 600)

    def _build_nav(self) -> None:
        from .title_bar import TitleBar
        self._title_bar = TitleBar(self)

        self.nav = NavigationBar()
        self._middle_stack = QStackedWidget()
        self._middle_stack.setFixedWidth(C_MIDDLE_W)
        self._middle_stack.setStyleSheet("QStackedWidget { border-radius: 12px 0 0 12px; }")
        self._right_stack = QStackedWidget()
        self._right_stack.setStyleSheet("QStackedWidget { background-color: #FFFFFF; border-radius: 0 12px 12px 0; }")

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(0)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        splitter.addWidget(self.nav)
        splitter.addWidget(self._middle_stack)
        splitter.addWidget(self._right_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([120, C_MIDDLE_W, 848])

        # 标题栏 + splitter 垂直布局（圆角窗口）
        central = QWidget()
        central.setObjectName("central_widget")
        central.setStyleSheet("""
            QWidget#central_widget {
                background-color: #EDEDED;
                border-radius: 12px;
            }
        """)
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(self._title_bar)
        cl.addWidget(splitter, 1)
        self.setCentralWidget(central)

    def _build_middle_panels(self) -> None:
        # 页0: 聊天联系人列表
        self._chat_list = ChatContactList()
        self._middle_stack.addWidget(self._chat_list)

        # 页1: 通讯录管理列表
        self._contact_mgr = ContactManageList()
        self._middle_stack.addWidget(self._contact_mgr)

        # 页2: 设置类别
        self._settings_list = SettingsList()
        self._middle_stack.addWidget(self._settings_list)

    def _build_right_panels(self) -> None:
        # 页0: 聊天区 + 输入面板
        chat_page = QWidget()
        cl = QVBoxLayout(chat_page)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        self._chat_area = ChatArea()
        self._input_panel = InputPanel()
        self._input_panel.setMinimumHeight(120)
        cl.addWidget(self._chat_area, 1)
        cl.addWidget(self._input_panel, 0)
        self._right_stack.addWidget(chat_page)

        # 页1: 联系人详情
        self._contact_detail = ContactDetail()
        self._right_stack.addWidget(self._contact_detail)

        # 页2: 设置详情
        self._settings_detail = SettingsDetail()
        self._right_stack.addWidget(self._settings_detail)

    def _apply_styles(self) -> None:
        self.setStyleSheet(GLOBAL_QSS)
        QApplication.instance().setStyleSheet(
            QApplication.instance().styleSheet() +
            " QToolTip { background-color: #FFF; color: #333; border: 1px solid #E5E5E5; border-radius: 4px; padding: 4px 8px; font-size: 16px; }"
        )

    # ==================================================================
    # 信号接线
    # ==================================================================

    def _wire_signals(self) -> None:
        # 导航
        self.nav.page_changed.connect(self._switch_page)

        # 聊天页
        self._chat_list.contact_selected.connect(self._on_chat_contact)
        self._chat_area.load_older.connect(self._on_load_older)
        self._chat_area.message_changed.connect(self._on_message_changed)
        self._input_panel.send_clicked.connect(self._on_send)
        self._input_panel.summon_clicked.connect(self._on_summon)
        self._input_panel.strategy_clicked.connect(self._on_strategy)
        self._input_panel.suggestion_selected.connect(
            lambda t: self._input_panel.set_input_text(t)
        )
        self._input_panel.refresh_suggestions.connect(self._on_summon)

        # 通讯录页
        self._contact_mgr.contact_selected.connect(self._on_manage_contact)
        self._contact_mgr.add_contact_requested.connect(self._on_add_contact)
        self._contact_detail.name_changed.connect(self._on_name_changed)
        self._contact_detail.avatar_changed.connect(self._on_avatar_changed)
        self._contact_detail.notes_changed.connect(self._on_notes_changed)
        self._contact_detail.more_clicked.connect(self._on_profile_more)
        self._contact_detail.delete_requested.connect(self._on_delete_contact)
        self._contact_detail.chat_requested.connect(self._on_chat_from_contact)

        # 设置页
        self._settings_list.category_selected.connect(self._settings_detail.set_page)
        self._settings_detail.config_saved.connect(self._on_config_saved)
        self._settings_detail.balance_updated.connect(self._on_balance_updated)
        from src.utils.config import load_config
        if load_config().get("balance", {}).get("enabled"):
            self._settings_detail._do_balance_query()

        # Controller（如果有）
        if self._ctrl:
            self._ctrl.suggestions_ready.connect(self._input_panel.set_suggestions)
            self._ctrl.suggestions_refreshed.connect(self._input_panel.set_suggestions)
            self._ctrl.profile_data_ready.connect(self._on_profile_refreshed)

    # ==================================================================
    # 页面切换
    # ==================================================================

    def _switch_page(self, index: int) -> None:
        self._current_page = index
        self._middle_stack.setCurrentIndex(index)

        if index == 0:  # 聊天
            self._right_stack.setCurrentIndex(0)
        elif index == 1:  # 通讯录
            self._right_stack.setCurrentIndex(1)
            # 首次切换：自动选中第一个联系人
            if self._contact_mgr._items and self._contact_detail._contact_id == 0:
                first_id = next(iter(self._contact_mgr._items.keys()))
                self._on_manage_contact(first_id)
        elif index == 2:  # 设置
            self._right_stack.setCurrentIndex(2)

    # ==================================================================
    # 聊天页操作
    # ==================================================================

    def _on_chat_contact(self, contact_id: int) -> None:
        self._current_contact_id = contact_id
        contact = get_contact_by_id(contact_id)
        if contact is None:
            return
        self._chat_area.set_contact(contact_id, contact.name, contact.avatar or "")

        messages = get_recent(contact_id, limit=50)
        contact_name = contact.name
        avatar = contact.avatar or ""
        self_name, self_avatar = self._get_self_info()
        for m in messages:
            self._chat_area.add_message({
                "id": m.id,
                "sender_type": m.sender_type,
                "sender_name": contact_name if m.sender_type == SenderType.TARGET else self_name,
                "content": m.content,
                "content_type": m.content_type,
                "avatar_path": avatar if m.sender_type == SenderType.TARGET else self_avatar,
            })
        self._ensure_right_page(0)
        QTimer.singleShot(20, self._chat_area.refresh_all_bubbles)

    def _on_send(self, sender_type: str, content: str) -> None:
        if self._current_contact_id is None:
            return
        sender = SenderType(sender_type)
        msg = create_message(self._current_contact_id, sender, content)

        contact = get_contact_by_id(self._current_contact_id)
        self_name, self_avatar = self._get_self_info()
        sender_name = self_name if sender == SenderType.USER else (contact.name if contact else "对方")

        self._chat_area.add_message({
            "id": msg.id,
            "sender_type": sender,
            "sender_name": sender_name,
            "content": content,
            "content_type": ContentType.TEXT,
            "avatar_path": contact.avatar if contact and sender == SenderType.TARGET else self_avatar,
        })
        self._input_panel.clear_input()

        # 刷新气泡宽度
        QTimer.singleShot(10, self._chat_area.refresh_all_bubbles)

        # 更新聊天列表预览并置顶 + 持久化排序（刷新 updated_at）
        if contact:
            update_contact(contact.id)  # 仅刷新 updated_at 用于持久化排序
            self._chat_list.update_contact(contact.id, contact.name, content, contact.avatar or "")

        # 每 10 条消息自动触发一次画像分析
        from src.storage.message_dao import get_message_count
        if self._ctrl and get_message_count(self._current_contact_id) % 10 == 0:
            self._ctrl.refresh_profile(self._current_contact_id)

    def _on_load_older(self, contact_id: int, before_id: int) -> None:
        older = get_before(contact_id, before_id, limit=50)
        if not older:
            return
        contact = get_contact_by_id(contact_id)
        cn = contact.name if contact else "对方"
        av = contact.avatar if contact else ""
        self_name, self_avatar = self._get_self_info()
        msgs = []
        for m in older:
            msgs.append({
                "id": m.id,
                "sender_type": m.sender_type,
                "sender_name": cn if m.sender_type == SenderType.TARGET else self_name,
                "content": m.content,
                "content_type": m.content_type,
                "avatar_path": av if m.sender_type == SenderType.TARGET else self_avatar,
            })
        self._chat_area.prepend_messages(msgs)

    def _on_message_changed(self) -> None:
        """消息被编辑/删除/插入后 → 刷新聊天区。"""
        if self._current_contact_id is None:
            return
        self._chat_area.clear()
        self._on_chat_contact(self._current_contact_id)

    def _on_summon(self) -> None:
        if self._current_contact_id is None:
            return
        self._input_panel.show_thinking()
        if self._ctrl:
            self._ctrl.summon_agent(self._current_contact_id)
        else:
            self._input_panel.set_suggestions([
                "嗯嗯，我也这么觉得～",
                "哈哈，你太有趣了！",
                "那下次一起去试试吧",
            ])

    def _on_strategy(self) -> None:
        dlg = StrategyDialog(self)
        if dlg.exec_() and self._current_contact_id and self._ctrl:
            text = dlg.get_input()
            if text:
                self._input_panel.show_thinking()
                self._ctrl.update_strategy(self._current_contact_id, text)

    # ==================================================================
    # 通讯录页操作
    # ==================================================================

    def _on_manage_contact(self, contact_id: int) -> None:
        contact = get_contact_by_id(contact_id)
        if contact is None:
            return
        is_self = contact.id == get_self_contact_id()
        profile = get_profile(contact_id) if not is_self else None

        self._contact_detail.load_contact(contact_id, contact.name)
        self._contact_detail.set_is_self(is_self)

        if is_self:
            self._contact_detail.set_summary("")
        else:
            self._contact_detail.set_affinity(profile.affinity_score if profile else 0)
            # 简要人格摘要（六层模型）
            if profile:
                summary_parts = []
                per = profile.personality
                traits = per.get("traits", [])
                if traits: summary_parts.append("性格: " + " · ".join(traits[:5]))
                if per.get("mbti_guess"): summary_parts.append(f"MBTI: {per['mbti_guess']}")
                if per.get("attachment_style"): summary_parts.append(f"依恋: {per['attachment_style']}")
                if profile.hobbies: summary_parts.append("爱好: " + " · ".join(profile.hobbies[:5]))
                bp = profile.behavior_patterns
                if isinstance(bp, dict) and bp.get("关系阶段"): summary_parts.append(bp["关系阶段"])
                if profile.summary: summary_parts.append(profile.summary[:80])
                self._contact_detail.set_summary("\n".join(summary_parts) if summary_parts else "暂无分析数据")
            else:
                self._contact_detail.set_summary("暂无分析数据")

        self._contact_detail.set_notes(contact.notes)
        if contact.avatar:
            self._contact_detail.set_avatar_path(contact.avatar)
        self._ensure_right_page(1)

    def _on_add_contact(self) -> None:
        name, ok = QInputDialog.getText(self, "新建联系人", "请输入联系人名称：")
        if not ok or not name.strip():
            return
        name = name.strip()

        from src.storage.profile_dao import create_or_update_profile
        contact = create_contact(name)
        create_or_update_profile(contact.id)

        # 同步到两个列表
        self._contact_mgr.add_contact(contact.id, contact.name)
        self._chat_list.add_contact(contact.id, contact.name, avatar_path=contact.avatar or "")
        self._contact_mgr.rebuild_sorted()
        self._on_manage_contact(contact.id)
        self._contact_mgr.select_contact(contact.id)

    def _on_avatar_changed(self, contact_id: int, path: str) -> None:
        update_contact(contact_id, avatar=path)
        contact = get_contact_by_id(contact_id)
        if contact:
            last = get_last_message(contact_id)
            preview = last.content if last else ""
            self._chat_list.update_contact(contact_id, contact.name, preview, path)
            self._contact_mgr.update_contact(contact_id, contact.name, path)
            if self._current_contact_id == contact_id:
                self._chat_area.clear()
                self._on_chat_contact(contact_id)

    def _on_name_changed(self, contact_id: int, name: str) -> None:
        update_contact(contact_id, name=name)
        contact = get_contact_by_id(contact_id)
        av = contact.avatar if contact else ""
        self._chat_list.update_contact(contact_id, name,
            get_last_message(contact_id).content if get_last_message(contact_id) else "", av)
        self._contact_mgr.update_contact(contact_id, name, av)

    def _on_notes_changed(self, contact_id: int, notes: str) -> None:
        update_contact(contact_id, notes=notes)
        logger.debug(f"备注已更新: contact={contact_id}")

    def _on_profile_more(self, contact_id: int) -> None:
        """打开完整画像弹窗。"""
        contact = get_contact_by_id(contact_id)
        profile = get_profile(contact_id)
        if contact is None:
            return

        profile_data = {
            "affinity_score": profile.affinity_score if profile else 0,
            "basic_info": profile.basic_info if profile else {},
            "personality": profile.personality if profile else {},
            "hobbies": profile.hobbies if profile else [],
            "behavior_patterns": profile.behavior_patterns if profile else {},
            "summary": profile.summary if profile else "",
        }

        dlg = ProfileDialog(self)
        dlg.load_profile(contact_id, contact.name, profile_data)
        dlg.refresh_requested.connect(self._on_profile_refresh)
        dlg.edit_requested.connect(self._on_profile_edit)
        dlg.exec_()

    def _on_profile_refresh(self, contact_id: int) -> None:
        if self._ctrl:
            self._ctrl.refresh_profile(contact_id)

    def _on_profile_refreshed(self, data: dict) -> None:
        """Controller 通知画像已刷新 → 更新通讯录详情。"""
        cid = self._current_contact_id
        if cid:
            self._on_manage_contact(cid)

    def _on_profile_edit(self, contact_id: int) -> None:
        """编辑画像：打开可编辑字段的对话框。"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout

        contact = get_contact_by_id(contact_id)
        profile = get_profile(contact_id)
        if contact is None:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"编辑画像 - {contact.name}")
        dlg.resize(500, 550)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)

        def _add_field(label, value):
            layout.addWidget(QLabel(label))
            te = QTextEdit()
            te.setPlainText(value)
            te.setMaximumHeight(80)
            layout.addWidget(te)
            return te

        p = profile
        # 基本信息：格式化为中文可读文本，不展示英文 JSON
        bi_parts = []
        if p:
            bi = p.basic_info
            if bi.get("age"): bi_parts.append(f"年龄: {bi['age']}")
            if bi.get("occupation"): bi_parts.append(f"职业: {bi['occupation']}")
            if bi.get("city"): bi_parts.append(f"城市: {bi['city']}")
            for k, v in bi.items():
                if k not in ("age", "occupation", "city") and v:
                    bi_parts.append(f"{k}: {v}")
        bi = "\n".join(bi_parts) if bi_parts else ""
        per = "、".join(p.personality.get("traits", []) + p.personality.get("tags", [])) if p else ""
        hob = "、".join(p.hobbies) if p and p.hobbies else ""
        bp_parts = []
        if p and p.behavior_patterns:
            for k, v in p.behavior_patterns.items():
                if v: bp_parts.append(f"{k}: {v}")
        bp = "\n".join(bp_parts)
        summ = p.summary if p else ""

        te_bi = _add_field("基本信息（每行一个）", bi)
        te_per = _add_field("性格特征（顿号分隔）", per)
        te_hob = _add_field("兴趣爱好（顿号分隔）", hob)
        te_bp = _add_field("行为模式（每行一个）", bp)
        te_sum = _add_field("关系摘要", summ)

        # 好感度
        from PyQt5.QtWidgets import QSpinBox
        aff_row = QHBoxLayout()
        aff_row.addWidget(QLabel("好感度 (-100 ~ 100)"))
        aff_spin = QSpinBox()
        aff_spin.setRange(-100, 100)
        aff_spin.setValue(p.affinity_score if p else 0)
        aff_spin.setStyleSheet("border: 1px solid #E5E5E5; border-radius: 4px; padding: 6px 10px; font-size: 18px;")
        aff_row.addWidget(aff_spin)
        aff_row.addStretch()
        layout.addLayout(aff_row)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("background-color: #07C160; color: white; border: none; border-radius: 4px; padding: 8px 20px; font-size: 16px;")
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background-color: #FFFFFF; color: #666; border: 1px solid #E5E5E5; border-radius: 4px; padding: 8px 20px; font-size: 16px;")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        def _on_save():
            # 解析中文格式文本
            new_bi = {}
            for line in te_bi.toPlainText().strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    new_bi[k.strip()] = v.strip()
            new_per = {"traits": [t.strip() for t in te_per.toPlainText().replace("、", ",").split(",") if t.strip()]}
            new_hob = [h.strip() for h in te_hob.toPlainText().replace("、", ",").split(",") if h.strip()]
            new_bp = {}
            for line in te_bp.toPlainText().strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    new_bp[k.strip()] = v.strip()
            new_sum = te_sum.toPlainText().strip()

            from src.storage.profile_dao import create_or_update_profile
            create_or_update_profile(
                contact_id, basic_info=new_bi, personality=new_per,
                hobbies=new_hob, behavior_patterns=new_bp, summary=new_sum,
                affinity_score=aff_spin.value(),
            )
            dlg.accept()
            # 刷新通讯录页
            if self._current_page == 1:
                self._on_manage_contact(contact_id)

        save_btn.clicked.connect(_on_save)
        dlg.exec_()

    def _on_chat_from_contact(self, contact_id: int) -> None:
        """从通讯录点击发消息 → 跳转到聊天页。"""
        self.nav.set_page(0)
        self._switch_page(0)
        self._current_contact_id = contact_id
        self._chat_list.select_contact(contact_id)
        self._on_chat_contact(contact_id)

    def _on_delete_contact(self, contact_id: int) -> None:
        """删除联系人：二次确认后清除所有关联数据。"""
        from PyQt5.QtWidgets import QMessageBox
        from src.storage.contact_dao import delete_contact as dc, get_contact_by_id
        from src.storage.profile_dao import delete_profile
        from src.storage.message_dao import delete_messages_by_contact
        import os

        contact = get_contact_by_id(contact_id)
        if contact is None:
            return
        name = contact.name

        reply = QMessageBox.warning(
            self, "删除联系人",
            f"确定要删除「{name}」吗？\n\n此操作将清除：\n"
            f"· 所有聊天记录\n· 人物画像数据\n· 本地头像文件\n· 自定义备注\n\n"
            f"此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 清理头像文件
        if contact.avatar and os.path.exists(contact.avatar):
            try:
                os.remove(contact.avatar)
            except OSError:
                pass

        # 清理数据库
        delete_messages_by_contact(contact_id)
        delete_profile(contact_id)
        dc(contact_id)

        # 更新 UI 列表
        self._chat_list.remove_contact(contact_id)
        self._contact_mgr.remove_contact(contact_id)

        # 如果当前聊天页正显示这个联系人，清空聊天区
        if self._current_contact_id == contact_id:
            self._current_contact_id = None
            self._chat_area.clear()

        # 自动选中下一个联系人
        if self._contact_mgr._items:
            next_id = next(iter(self._contact_mgr._items.keys()))
            self._contact_mgr.select_contact(next_id)
            self._on_manage_contact(next_id)
        else:
            self._contact_detail.load_contact(0, "")


    # ==================================================================
    # 设置页
    # ==================================================================

    def _on_config_saved(self) -> None:
        pass

    # ==================================================================
    # Windows 原生边缘缩放（WM_NCHITTEST）
    # ==================================================================

    def nativeEvent(self, eventType, message):
        """处理 Windows 原生消息，让无框窗口支持边缘拖拽缩放。"""
        if eventType == "windows_generic_MSG":
            mw = ctypes.wintypes.MSG.from_address(int(message))
            if mw.message == 0x0084:  # WM_NCHITTEST
                x = mw.pt.x
                y = mw.pt.y
                pt = self.mapFromGlobal(QPoint(x, y))
                m = 6
                left = pt.x() <= m
                right = pt.x() >= self.width() - m
                top = pt.y() <= m
                bottom = pt.y() >= self.height() - m
                if top and left: return True, 13
                if top and right: return True, 14
                if bottom and left: return True, 16
                if bottom and right: return True, 17
                if left: return True, 10
                if right: return True, 11
                if top: return True, 12
                if bottom: return True, 15
        return False, 0

    def resizeEvent(self, event) -> None:
        """窗口大小变化时重新应用四角圆角遮罩。"""
        super().resizeEvent(event)
        from PyQt5.QtGui import QRegion
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _on_balance_updated(self, text: str) -> None:
        self._title_bar._balance_label.setText(text)

    # ==================================================================
    # 联系人加载（启动时）
    # ==================================================================

    def _get_self_info(self) -> tuple[str, str]:
        """获取'自己'的名称和头像路径。"""
        c = get_contact_by_id(get_self_contact_id())
        if c:
            return c.name, c.avatar or ""
        return "我", ""

    def _load_contacts(self) -> None:
        contacts = get_all_contacts()
        self_id = get_self_contact_id()

        # 确保"自己"联系人存在（用 config 中保存的 id 识别）
        self_contact = None
        others = []
        for c in contacts:
            if c.id == self_id:
                self_contact = c
            else:
                others.append(c)
        if self_contact is None:
            from src.storage.profile_dao import create_or_update_profile
            self_contact = create_contact("我")
            create_or_update_profile(self_contact.id)
            set_self_contact_id(self_contact.id)

        # "自己" 始终在通讯录第一位，不加入聊天列表
        self._contact_mgr.add_contact(self_contact.id, self_contact.name, self_contact.avatar or "")

        # 聊天页（不含"自己"）
        for c in contacts:
            if c.id == self_id:
                continue
            last = get_last_message(c.id)
            preview = last.content if last else ""
            self._chat_list.add_contact(c.id, c.name, preview, c.avatar or "")

        # 通讯录其余按拼音排序
        others_pinyin = sorted(others, key=lambda c: _pinyin_key(c.name))
        for c in others_pinyin:
            self._contact_mgr.add_contact(c.id, c.name, c.avatar or "")

    # ==================================================================
    # 工具
    # ==================================================================

    def _ensure_right_page(self, index: int) -> None:
        """确保右侧面板显示正确的页面。"""
        if self._right_stack.currentIndex() != index:
            self._right_stack.setCurrentIndex(index)
