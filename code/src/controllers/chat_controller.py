"""ChatController —— 主控制器，唯一业务枢纽。

职责：
1. 接收 UI 事件，调用 Service / Skill / DAO
2. 管理 AsyncWorker 异步执行 LLM 调用
3. 通过 pyqtSignal 通知 UI 更新

依赖注入：SkillManager 在 main.py 中注册完毕后传入。
"""

from PyQt5.QtCore import QObject, pyqtSignal

from src.models.enums import SenderType, ContentType
from src.storage import contact_dao, message_dao, profile_dao
from src.services.llm_service import chat_completion
from src.services.profile_service import get_profile_summary
from src.services.context_summarizer import summarize_history
from src.services.web_search import search_web, detect_hot_topics
from src.skills.manager import skill_manager
from src.utils.thread_utils import AsyncWorker
from src.utils.logger import logger


class ChatController(QObject):
    """主控制器。

    ## UI → Controller（UI 调用这些方法）
    - select_contact(contact_id)
    - send_message(contact_id, sender_type, content)
    - load_older_messages(contact_id, before_timestamp)
    - summon_agent(contact_id, extra_instruction=None)
    - refresh_profile(contact_id)
    - toggle_mode(mode: str)
    - create_contact(name) -> Contact

    ## Controller → UI（控制器发射这些信号）
    - contact_loaded(name, affinity)
    - messages_ready(list[dict])
    - older_messages_ready(list[dict])
    - suggestions_ready(list[str])
    - profile_data_ready(dict)
    - status_update(str)
    - error_occurred(str)
    """

    # ---- 信号 ----
    contact_loaded = pyqtSignal(str, int)                    # name, affinity
    messages_ready = pyqtSignal(list)                        # [msg_dict, ...]
    older_messages_ready = pyqtSignal(list)                  # [msg_dict, ...]
    message_sent = pyqtSignal(dict)                          # msg_dict
    suggestions_ready = pyqtSignal(list)                     # [str, str, str]
    suggestions_refreshed = pyqtSignal(list)                 # [str, str, str]
    profile_data_ready = pyqtSignal(dict)                    # profile data for dialog
    status_update = pyqtSignal(str)                          # status bar text
    error_occurred = pyqtSignal(str)                         # error message

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_contact_id: int | None = None
        self._current_contact_name: str = ""
        self._mode: str = "silent"  # silent | active
        self._worker: AsyncWorker | None = None

        # 将内置 Skill 注册到 SkillManager
        self._register_builtin_skills()

    # ==================================================================
    # 联系人操作
    # ==================================================================

    def select_contact(self, contact_id: int) -> None:
        """选中联系人 → 加载聊天记录。"""
        self._current_contact_id = contact_id
        contact = contact_dao.get_contact_by_id(contact_id)
        if contact is None:
            return
        self._current_contact_name = contact.name

        profile = profile_dao.get_profile(contact_id)
        affinity = profile.affinity_score if profile else 0

        # 通知 UI 切换联系人
        self.contact_loaded.emit(contact.name, affinity)

        # 加载最近消息
        messages = message_dao.get_recent(contact_id, limit=50)
        msg_dicts = [self._msg_to_dict(m, contact.name) for m in messages]
        self.messages_ready.emit(msg_dicts)
        self.status_update.emit(f"已选择: {contact.name} | 模式: {'常开' if self._mode == 'active' else '静默'}")

    def create_contact(self, name: str) -> int:
        """创建新联系人，返回 contact_id。"""
        contact = contact_dao.create_contact(name)
        profile_dao.create_or_update_profile(contact.id)  # 初始化画像
        self.status_update.emit(f"已创建联系人: {name}")
        return contact.id

    # ==================================================================
    # 消息操作
    # ==================================================================

    def send_message(self, contact_id: int, sender_type: str, content: str) -> None:
        """发送/录入消息。"""
        sender = SenderType(sender_type)
        msg = message_dao.create_message(contact_id, sender, content)

        contact = contact_dao.get_contact_by_id(contact_id)
        sender_name = "我" if sender == SenderType.USER else (contact.name if contact else "对方")

        msg_dict = {
            "sender_type": sender,
            "sender_name": sender_name,
            "content": content,
            "content_type": ContentType.TEXT,
        }
        self.message_sent.emit(msg_dict)

        # 常开模式：后台分析
        if self._mode == "active" and sender == SenderType.TARGET:
            self._auto_analyze(contact_id, content)

    def load_older_messages(self, contact_id: int, before_id: int) -> None:
        """加载更早的历史消息。"""
        older = message_dao.get_before(contact_id, before_id, limit=50)
        if not older:
            return

        contact = contact_dao.get_contact_by_id(contact_id)
        contact_name = contact.name if contact else "对方"

        msg_dicts = [self._msg_to_dict(m, contact_name) for m in older]
        self.older_messages_ready.emit(msg_dicts)

    # ==================================================================
    # 智能体操作
    # ==================================================================

    def summon_agent(self, contact_id: int, extra_instruction: str = "") -> None:
        """召唤智能体 → 后台生成回复建议。

        Phase 5/6 完整实现：通过三层上下文策略调用 ReplyGenerator Skill。
        """
        self.status_update.emit("智能体思考中...")
        self._run_async(
            lambda: self._do_summon(contact_id, extra_instruction),
            on_done=lambda suggestions: self.suggestions_ready.emit(suggestions),
            on_error=lambda e: self._handle_summon_error(e),
        )

    def refresh_suggestions(self, contact_id: int) -> None:
        """刷新回复建议（重新生成）。"""
        self.status_update.emit("重新生成建议...")
        self._run_async(
            lambda: self._do_summon(contact_id, ""),
            on_done=lambda suggestions: self.suggestions_refreshed.emit(suggestions),
            on_error=lambda e: self._handle_summon_error(e),
        )

    def update_strategy(self, contact_id: int, user_thought: str) -> None:
        """根据用户策略调整重新生成建议。"""
        self.status_update.emit(f"策略调整中...")
        self._run_async(
            lambda: self._do_summon(contact_id, user_thought),
            on_done=lambda suggestions: self.suggestions_ready.emit(suggestions),
            on_error=lambda e: self._handle_summon_error(e),
        )

    def refresh_profile(self, contact_id: int) -> None:
        """刷新人物画像。"""
        self.status_update.emit("分析画像中...")
        self._run_async(
            lambda: self._do_profile_refresh(contact_id),
            on_done=lambda data: self._on_profile_refreshed(contact_id, data),
            on_error=lambda e: self.error_occurred.emit(f"画像刷新失败: {e}"),
        )

    # ==================================================================
    # 模式控制
    # ==================================================================

    def toggle_mode(self, mode: str) -> None:
        """切换静默/常开模式。"""
        self._mode = mode
        label = "常开" if mode == "active" else "静默"
        self.status_update.emit(f"模式已切换: {label}")

    @property
    def mode(self) -> str:
        return self._mode

    # ==================================================================
    # 内部实现
    # ==================================================================

    def _do_summon(self, contact_id: int, extra_instruction: str) -> list[str]:
        """在后台线程中执行召唤流程。"""
        contact = contact_dao.get_contact_by_id(contact_id)
        if contact is None:
            return ["请先选择一个联系人"]

        # 三层上下文
        profile_summary = get_profile_summary(contact_id)
        history_summary = summarize_history(contact_id)
        recent_messages = message_dao.get_recent(contact_id, limit=30)

        recent_dicts = [
            {"sender_type": m.sender_type.value, "content": m.content}
            for m in recent_messages
        ]

        # 检测是否需要联网搜索
        search_context = ""
        recent_contents = [m.content for m in recent_messages]
        hot_query = detect_hot_topics(recent_contents)
        if hot_query:
            search_result = search_web(hot_query)
            if search_result:
                search_context = f"\n联网搜索结果（{hot_query}）：\n{search_result}"

        context = {
            "recent_messages": recent_dicts,
            "profile_summary": profile_summary,
            "history_summary": history_summary,
            "extra_instruction": extra_instruction + search_context,
        }

        result = skill_manager.execute("ReplyGenerator", context)
        return result.get("suggestions", [])

    def _do_profile_refresh(self, contact_id: int) -> dict:
        """在后台线程中执行画像刷新。"""
        contact = contact_dao.get_contact_by_id(contact_id)
        messages = message_dao.get_recent(contact_id, limit=50)

        lines = []
        for m in messages:
            role = "用户" if m.sender_type == SenderType.USER else "对方"
            lines.append(f"[{role}] {m.content}")
        conversation = "\n".join(lines)

        context = {
            "contact_name": contact.name if contact else "",
            "conversation_text": conversation,
        }

        result = skill_manager.execute("ProfileAnalyzer", context)
        if "error" in result:
            return {"error": result["error"]}

        # 更新数据库（含六层模型新字段）
        bp = result.get("behavior_patterns", {})
        if not bp:
            bp = {**result.get("expression", {}), **result.get("emotion_patterns", {}),
                  **result.get("conflict_style", {}), **result.get("relationship_signals", {})}
        profile_dao.create_or_update_profile(
            contact_id=contact_id,
            basic_info=result.get("basic_info"),
            personality=result.get("personality"),
            hobbies=result.get("hobbies"),
            behavior_patterns=bp,
            affinity_score=result.get("affinity_score"),
            summary=result.get("summary"),
        )

        return result

    def _on_profile_refreshed(self, contact_id: int, data: dict) -> None:
        """画像刷新完成 → 通知 UI。"""
        if "error" in data:
            self.error_occurred.emit(f"画像刷新失败: {data['error']}")
            return

        profile = profile_dao.get_profile(contact_id)
        profile_data = {
            "affinity_score": profile.affinity_score if profile else 0,
            "basic_info": profile.basic_info if profile else {},
            "personality": profile.personality if profile else {},
            "hobbies": profile.hobbies if profile else [],
            "behavior_patterns": profile.behavior_patterns if profile else {},
            "summary": profile.summary if profile else "",
        }
        self.profile_data_ready.emit(profile_data)
        self.status_update.emit(
            f"画像已刷新 | 好感度: {profile_data['affinity_score']}"
        )

    def _auto_analyze(self, contact_id: int, content: str) -> None:
        """常开模式：自动分析新消息（轻量级，仅情感分析）。"""
        # 后台异步执行，不阻塞 UI
        def _analyze():
            recent = message_dao.get_recent(contact_id, limit=5)
            context_lines = []
            for m in recent[:-1]:  # 前几条作为上下文
                role = "对方" if m.sender_type == SenderType.TARGET else "用户"
                context_lines.append(f"[{role}] {m.content}")
            recent_context = "\n".join(context_lines)

            result = skill_manager.execute("SentimentAnalyzer", {
                "message_text": content,
                "recent_context": recent_context,
            })
            return result

        def _on_result(result):
            if "error" not in result and result.get("sentiment") == "负面":
                self.status_update.emit(
                    f"⚠️ 检测到负面情绪: {result.get('emotion', '')}"
                )

        self._run_async(_analyze, on_done=_on_result)

    # ==================================================================
    # 异步工具
    # ==================================================================

    def _run_async(self, target, on_done=None, on_error=None) -> None:
        """在后台线程中执行耗时操作。"""
        self._worker = AsyncWorker()
        if on_done:
            self._worker.finished.connect(on_done)
        if on_error:
            self._worker.error.connect(on_error)
        else:
            self._worker.error.connect(lambda e: self.error_occurred.emit(str(e)))
        self._worker.run(target)

    def _handle_summon_error(self, error: str) -> None:
        """召唤失败的统一处理。"""
        logger.error(f"召唤智能体失败: {error}")
        self.suggestions_ready.emit([
            "嗯嗯，我理解～",
            "哈哈，你继续说",
            "好的，我知道啦",
        ])
        self.status_update.emit(f"⚠️ 智能体调用失败，已使用默认建议")

    # ==================================================================
    # 工具方法
    # ==================================================================

    @staticmethod
    def _msg_to_dict(msg, contact_name: str = "对方") -> dict:
        """将 Message 模型转为 UI 可用的 dict。"""
        return {
            "sender_type": msg.sender_type,
            "sender_name": "我" if msg.sender_type == SenderType.USER else contact_name,
            "content": msg.content,
            "content_type": msg.content_type,
        }

    @staticmethod
    def _register_builtin_skills() -> None:
        """确保内置 Skill 已注册（幂等）。"""
        from src.skills.builtin import BUILTIN_SKILLS
        existing = set(skill_manager.list_names())
        for cls in BUILTIN_SKILLS:
            if cls.name not in existing:
                skill_manager.register(cls())
