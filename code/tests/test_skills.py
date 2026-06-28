"""Skill 系统单元测试。

测试范围：
- BaseSkill 抽象类
- SkillManager 注册/获取/列表/执行/禁用
- 各内置 Skill 的参数校验
- JSON 解析容错
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.skills.base import BaseSkill
from src.skills.manager import SkillManager
from src.skills.builtin import BUILTIN_SKILLS


# ============================================================
# BaseSkill 测试
# ============================================================

class TestBaseSkill:
    """BaseSkill 抽象基类测试。"""

    def test_cannot_instantiate_abstract(self):
        """抽象类不能直接实例化。"""
        with pytest.raises(TypeError):
            BaseSkill()  # type: ignore

    def test_concrete_skill_instantiable(self):
        """具体子类可实例化。"""
        class TestSkill(BaseSkill):
            name = "Test"
            description = "测试用"
            def execute(self, context):
                return {"ok": True}
            def get_prompt(self):
                return "test prompt"

        s = TestSkill()
        assert s.name == "Test"
        assert s.version == "1.0.0"

    def test_validate_context_passes(self):
        """参数校验通过。"""
        class T(BaseSkill):
            name = "T"
            description = ""
            def execute(self, c):
                return {}
            def get_prompt(self):
                return ""
        s = T()
        assert s.validate_context({"a": 1, "b": 2}, ["a"]) is None

    def test_validate_context_fails(self):
        """参数校验失败返回错误信息。"""
        class T(BaseSkill):
            name = "T"
            description = ""
            def execute(self, c):
                return {}
            def get_prompt(self):
                return ""
        s = T()
        err = s.validate_context({}, ["missing_key"])
        assert err is not None
        assert "missing_key" in err


# ============================================================
# SkillManager 测试
# ============================================================

class TestSkillManager:
    """SkillManager 测试。"""

    def test_singleton(self):
        """单例模式。"""
        a = SkillManager()
        b = SkillManager()
        assert a is b

    def test_register_and_get(self):
        """注册和获取。"""
        class S(BaseSkill):
            name = "TestSkill"
            description = "test"
            def execute(self, c):
                return {"x": 1}
            def get_prompt(self):
                return ""

        mgr = SkillManager()
        mgr.register(S())
        s = mgr.get("TestSkill")
        assert s is not None
        assert s.name == "TestSkill"
        assert s.execute({}) == {"x": 1}

    def test_register_duplicate_overwrites(self):
        """重复注册覆盖旧版本。"""
        class S1(BaseSkill):
            name = "Dup"
            description = "v1"
            version = "1.0.0"
            def execute(self, c):
                return {}
            def get_prompt(self):
                return ""

        class S2(BaseSkill):
            name = "Dup"
            description = "v2"
            version = "2.0.0"
            def execute(self, c):
                return {}
            def get_prompt(self):
                return ""

        mgr = SkillManager()
        mgr.register(S1())
        mgr.register(S2())
        assert mgr.get("Dup").version == "2.0.0"

    def test_list_all(self):
        """列出所有 Skill。"""
        mgr = SkillManager()
        info = mgr.list_all()
        # 可能包含之前测试注册的 Skill
        names = [i["name"] for i in info]
        assert "ReplyGenerator" in names or "TestSkill" in names

    def test_execute_unregistered_raises(self):
        """执行未注册 Skill 抛出 ValueError。"""
        mgr = SkillManager()
        with pytest.raises(ValueError, match="未注册"):
            mgr.execute("NoSuchSkill", {})

    def test_validation_error_returned_not_raised(self):
        """参数校验错误作为返回值，不抛异常。"""
        mgr = SkillManager()
        # ReplyGenerator 应该已经被注册了
        rg = mgr.get("ReplyGenerator")
        if rg is None:
            pytest.skip("ReplyGenerator 未注册")
        result = mgr.execute("ReplyGenerator", {})
        assert "error" in result
        assert result["suggestions"] == []


# ============================================================
# 内置 Skill 测试
# ============================================================

class TestBuiltinSkills:
    """内置 Skill 实例化和基本属性测试。"""

    @pytest.mark.parametrize("skill_cls", BUILTIN_SKILLS)
    def test_instantiate(self, skill_cls):
        """所有内置 Skill 可实例化。"""
        s = skill_cls()
        assert s.name
        assert s.description
        assert s.version

    @pytest.mark.parametrize("skill_cls", BUILTIN_SKILLS)
    def test_get_prompt_returns_string(self, skill_cls):
        """get_prompt 返回非空字符串。"""
        s = skill_cls()
        prompt = s.get_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 10

    def test_reply_generator_validation(self):
        """ReplyGenerator 需要 recent_messages。"""
        from src.skills.builtin import ReplyGenerator
        rg = ReplyGenerator()
        result = rg.execute({})
        assert "error" in result

    def test_profile_analyzer_validation(self):
        """ProfileAnalyzer 需要 contact_name 和 conversation_text。"""
        from src.skills.builtin import ProfileAnalyzer
        pa = ProfileAnalyzer()
        result = pa.execute({})
        assert "error" in result

    def test_sentiment_analyzer_validation(self):
        """SentimentAnalyzer 需要 message_text。"""
        from src.skills.builtin import SentimentAnalyzer
        sa = SentimentAnalyzer()
        result = sa.execute({})
        assert "error" in result

    def test_affinity_estimator_validation(self):
        """AffinityEstimator 需要 recent_messages。"""
        from src.skills.builtin import AffinityEstimator
        ae = AffinityEstimator()
        result = ae.execute({})
        assert "error" in result

    def test_reply_generator_json_fallback(self):
        """ReplyGenerator JSON 解析容错：非 JSON 文本应回退到按行拆分。"""
        from src.skills.builtin import ReplyGenerator
        result = ReplyGenerator._parse_response("1. 你好\n2. 在吗\n3. 早点休息")
        assert len(result["suggestions"]) == 3
        assert result["suggestions"][0] == "你好"

    def test_profile_analyzer_json_fallback(self):
        """ProfileAnalyzer JSON 解析容错：无效 JSON 返回空字典。"""
        from src.skills.builtin import ProfileAnalyzer
        result = ProfileAnalyzer._parse_json("not json at all")
        assert result == {}

    def test_sentiment_analyzer_json_fallback(self):
        """SentimentAnalyzer 无效 JSON 返回默认值。"""
        from src.skills.builtin import SentimentAnalyzer
        result = SentimentAnalyzer._parse_json("garbage")
        assert result["sentiment"] == "中性"
        assert result["score"] == 0.0


# ============================================================
# Skill 配置测试
# ============================================================

class TestSkillConfig:
    """Skill 配置相关测试。"""

    def test_topic_suggester_no_required_fields(self):
        """TopicSuggester 无必需字段，空 context 不报错。"""
        from src.skills.builtin import TopicSuggester
        ts = TopicSuggester()
        # 无必需字段，但调用 LLM 会因缺 API Key 失败
        result = ts.execute({})
        assert "topics" in result or "error" in result
