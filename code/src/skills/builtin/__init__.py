"""内置 Skill 实现。

所有 Skill 在此导入并注册到 SkillManager。
"""

from .reply_generator import ReplyGenerator
from .profile_analyzer import ProfileAnalyzer
from .sentiment_analyzer import SentimentAnalyzer
from .topic_suggester import TopicSuggester
from .affinity_estimator import AffinityEstimator

__all__ = [
    "ReplyGenerator",
    "ProfileAnalyzer",
    "SentimentAnalyzer",
    "TopicSuggester",
    "AffinityEstimator",
]

# 默认注册的内置 Skill 列表（按注册顺序）
BUILTIN_SKILLS = [
    ReplyGenerator,
    ProfileAnalyzer,
    SentimentAnalyzer,
    TopicSuggester,
    AffinityEstimator,
]
