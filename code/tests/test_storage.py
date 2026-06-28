"""数据层单元测试。

测试范围：
- ContactDAO: CRUD
- MessageDAO: CRUD + 分页查询
- ProfileDAO: CRUD + JSON 序列化
- 级联删除
"""

import os
import sys
import tempfile
import pytest
# (timestamp removed — tests use message id for ordering)

# 确保 code/src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# 重定向数据库路径到临时文件（避免污染开发数据库）
import src.utils.config as config_mod
import src.storage.database as db_mod


@pytest.fixture(autouse=True)
def temp_db():
    """每个测试使用独立的临时数据库。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    # 重写路径
    original_db = config_mod.DB_PATH
    config_mod.DB_PATH = tmp.name
    db_mod.DB_PATH = tmp.name

    # 清除连接缓存
    if hasattr(db_mod._local, "connection") and db_mod._local.connection:
        db_mod._local.connection.close()
        db_mod._local.connection = None

    # 建表
    db_mod.init_db()

    yield tmp.name

    # 清理
    if hasattr(db_mod._local, "connection") and db_mod._local.connection:
        db_mod._local.connection.close()
        db_mod._local.connection = None
    os.unlink(tmp.name)
    config_mod.DB_PATH = original_db
    db_mod.DB_PATH = original_db


# ============================================================
# ContactDAO 测试
# ============================================================

class TestContactDAO:
    """联系人 CRUD 测试。"""

    def test_create_contact(self, temp_db):
        from src.storage.contact_dao import create_contact, get_contact_by_id

        c = create_contact("小美")
        assert c.id is not None
        assert c.name == "小美"
        assert c.avatar is None
        assert c.created_at is not None

        fetched = get_contact_by_id(c.id)
        assert fetched is not None
        assert fetched.name == "小美"

    def test_create_contact_with_avatar(self, temp_db):
        from src.storage.contact_dao import create_contact

        c = create_contact("小美", avatar="test_avatar.png")
        assert c.avatar == "test_avatar.png"

    def test_get_nonexistent_contact(self, temp_db):
        from src.storage.contact_dao import get_contact_by_id

        assert get_contact_by_id(999) is None

    def test_get_all_contacts(self, temp_db):
        from src.storage.contact_dao import create_contact, get_all_contacts

        create_contact("A")
        create_contact("B")
        create_contact("C")

        all_contacts = get_all_contacts()
        assert len(all_contacts) == 3
        names = [c.name for c in all_contacts]
        assert "A" in names
        assert "B" in names
        assert "C" in names

    def test_update_contact_name(self, temp_db):
        from src.storage.contact_dao import create_contact, update_contact

        c = create_contact("旧名字")
        updated = update_contact(c.id, name="新名字")
        assert updated.name == "新名字"

    def test_update_contact_partial(self, temp_db):
        from src.storage.contact_dao import create_contact, update_contact

        c = create_contact("小美", avatar="old.png")
        updated = update_contact(c.id, name="小美2")  # 只更新 name
        assert updated.name == "小美2"
        assert updated.avatar == "old.png"  # avatar 不变

    def test_update_nonexistent(self, temp_db):
        from src.storage.contact_dao import update_contact

        assert update_contact(999, name="X") is None

    def test_delete_contact(self, temp_db):
        from src.storage.contact_dao import (
            create_contact, delete_contact, get_contact_by_id
        )

        c = create_contact("待删除")
        assert delete_contact(c.id) is True
        assert get_contact_by_id(c.id) is None

    def test_delete_nonexistent(self, temp_db):
        from src.storage.contact_dao import delete_contact

        assert delete_contact(999) is False

    def test_contact_exists(self, temp_db):
        from src.storage.contact_dao import create_contact, contact_exists

        assert contact_exists(1) is False
        c = create_contact("测试")
        assert contact_exists(c.id) is True


# ============================================================
# MessageDAO 测试
# ============================================================

class TestMessageDAO:
    """消息 CRUD + 分页测试（无时间戳）。"""

    @pytest.fixture
    def contact(self, temp_db):
        from src.storage.contact_dao import create_contact
        return create_contact("测试联系人")

    def test_create_message(self, temp_db, contact):
        from src.storage.message_dao import create_message, get_message_by_id
        from src.models.enums import SenderType

        m = create_message(contact.id, SenderType.USER, "你好")
        assert m.id is not None
        assert m.contact_id == contact.id
        assert m.sender_type == SenderType.USER
        assert m.content == "你好"
        assert m.is_edited is False

        fetched = get_message_by_id(m.id)
        assert fetched.content == "你好"

    def test_update_message(self, temp_db, contact):
        from src.storage.message_dao import create_message, update_message
        from src.models.enums import SenderType

        m = create_message(contact.id, SenderType.USER, "原始内容")
        updated = update_message(m.id, "修改后内容")
        assert updated.content == "修改后内容"
        assert updated.is_edited is True

    def test_update_nonexistent_message(self, temp_db):
        from src.storage.message_dao import update_message
        assert update_message(999, "X") is None

    def test_delete_message(self, temp_db, contact):
        from src.storage.message_dao import (
            create_message, delete_message, get_message_by_id
        )
        from src.models.enums import SenderType
        m = create_message(contact.id, SenderType.USER, "待删除")
        assert delete_message(m.id) is True
        assert get_message_by_id(m.id) is None

    def test_get_nonexistent_message(self, temp_db):
        from src.storage.message_dao import get_message_by_id
        assert get_message_by_id(999) is None

    def test_get_recent_returns_ascending_order(self, temp_db, contact):
        from src.storage.message_dao import create_message, get_recent
        from src.models.enums import SenderType
        for i in range(5):
            create_message(contact.id, SenderType.USER, f"消息{i}")
        recent = get_recent(contact.id, limit=50)
        assert len(recent) == 5
        for i in range(len(recent) - 1):
            assert recent[i].id < recent[i + 1].id

    def test_get_recent_with_limit(self, temp_db, contact):
        from src.storage.message_dao import create_message, get_recent
        from src.models.enums import SenderType
        ids = []
        for i in range(10):
            m = create_message(contact.id, SenderType.USER, f"消息{i}")
            ids.append(m.id)
        recent = get_recent(contact.id, limit=3)
        assert len(recent) == 3
        assert recent[0].content == "消息7"
        assert recent[2].content == "消息9"

    def test_get_before_pagination(self, temp_db, contact):
        from src.storage.message_dao import create_message, get_before
        from src.models.enums import SenderType
        ids = []
        for i in range(20):
            m = create_message(contact.id, SenderType.USER, f"消息{i}")
            ids.append(m.id)
        # 取第 10 条(id=ids[10]) 之前 5 条
        older = get_before(contact.id, ids[10], limit=5)
        assert len(older) == 5
        assert older[0].content == "消息5"
        assert older[4].content == "消息9"

    def test_get_before_empty(self, temp_db, contact):
        from src.storage.message_dao import create_message, get_before
        from src.models.enums import SenderType
        m = create_message(contact.id, SenderType.USER, "唯一消息")
        older = get_before(contact.id, m.id, limit=10)
        assert len(older) == 0

    def test_get_message_count(self, temp_db, contact):
        from src.storage.message_dao import create_message, get_message_count
        from src.models.enums import SenderType
        assert get_message_count(contact.id) == 0
        for i in range(5):
            create_message(contact.id, SenderType.USER, f"消息{i}")
        assert get_message_count(contact.id) == 5

    def test_get_last_message(self, temp_db, contact):
        from src.storage.message_dao import create_message, get_last_message
        from src.models.enums import SenderType
        assert get_last_message(contact.id) is None
        create_message(contact.id, SenderType.USER, "第一条")
        create_message(contact.id, SenderType.TARGET, "第二条（最后）")
        last = get_last_message(contact.id)
        assert last.content == "第二条（最后）"

    def test_messages_isolated_by_contact(self, temp_db):
        from src.storage.contact_dao import create_contact
        from src.storage.message_dao import create_message, get_recent
        from src.models.enums import SenderType
        a = create_contact("A")
        b = create_contact("B")
        create_message(a.id, SenderType.USER, "A的消息")
        create_message(b.id, SenderType.USER, "B的消息")
        a_msgs = get_recent(a.id)
        b_msgs = get_recent(b.id)
        assert len(a_msgs) == 1
        assert len(b_msgs) == 1
        assert a_msgs[0].content == "A的消息"
        assert b_msgs[0].content == "B的消息"

    def test_delete_messages_by_contact(self, temp_db, contact):
        from src.storage.message_dao import (
            create_message, delete_messages_by_contact, get_message_count
        )
        from src.models.enums import SenderType
        for i in range(3):
            create_message(contact.id, SenderType.USER, f"消息{i}")
        assert get_message_count(contact.id) == 3
        count = delete_messages_by_contact(contact.id)
        assert count == 3
        assert get_message_count(contact.id) == 0


# ============================================================
# ProfileDAO 测试
# ============================================================

class TestProfileDAO:
    """画像 CRUD + JSON 序列化测试。"""

    @pytest.fixture
    def contact(self, temp_db):
        from src.storage.contact_dao import create_contact
        return create_contact("测试联系人")

    def test_create_profile(self, temp_db, contact):
        from src.storage.profile_dao import create_or_update_profile, get_profile

        p = create_or_update_profile(
            contact.id,
            basic_info={"age": 25, "city": "上海"},
            personality={"traits": ["外向", "细心"]},
            hobbies=["摄影", "旅行"],
            affinity_score=30,
            summary="测试摘要",
        )
        assert p.contact_id == contact.id
        assert p.basic_info == {"age": 25, "city": "上海"}
        assert p.personality == {"traits": ["外向", "细心"]}
        assert p.hobbies == ["摄影", "旅行"]
        assert p.affinity_score == 30
        assert p.summary == "测试摘要"
        assert p.last_updated is not None

    def test_create_profile_defaults(self, temp_db, contact):
        from src.storage.profile_dao import create_or_update_profile

        p = create_or_update_profile(contact.id)
        assert p.affinity_score == 0
        assert p.basic_info == {}
        assert p.hobbies == []

    def test_get_nonexistent_profile(self, temp_db):
        from src.storage.profile_dao import get_profile

        assert get_profile(999) is None

    def test_update_profile_partial(self, temp_db, contact):
        from src.storage.profile_dao import create_or_update_profile

        # 创建初始画像
        create_or_update_profile(
            contact.id,
            basic_info={"age": 25},
            hobbies=["摄影"],
            affinity_score=10,
        )

        # 部分更新
        updated = create_or_update_profile(
            contact.id,
            hobbies=["旅行", "看电影"],  # 替换 hobbies
            affinity_score=50,           # 更新好感度
        )

        assert updated.basic_info == {"age": 25}  # 不变
        assert updated.hobbies == ["旅行", "看电影"]  # 更新
        assert updated.affinity_score == 50

    def test_update_profile_accumulates(self, temp_db, contact):
        from src.storage.profile_dao import create_or_update_profile

        p1 = create_or_update_profile(contact.id, basic_info={"age": 25})
        p2 = create_or_update_profile(contact.id, personality={"traits": ["幽默"]})
        p3 = create_or_update_profile(contact.id, affinity_score=80)

        # 最终应合并所有字段
        final = create_or_update_profile(contact.id)
        assert final.basic_info == {"age": 25}
        assert final.personality == {"traits": ["幽默"]}
        assert final.affinity_score == 80

    def test_delete_profile(self, temp_db, contact):
        from src.storage.profile_dao import (
            create_or_update_profile, delete_profile, get_profile
        )

        create_or_update_profile(contact.id)
        assert delete_profile(contact.id) is True
        assert get_profile(contact.id) is None

    def test_delete_nonexistent_profile(self, temp_db):
        from src.storage.profile_dao import delete_profile

        assert delete_profile(999) is False

    def test_profile_json_roundtrip(self, temp_db, contact):
        """验证复杂 JSON 字段的序列化往返。"""
        from src.storage.profile_dao import create_or_update_profile, get_profile

        complex_data = {
            "basic_info": {"name": "小美", "details": {"height": 165, "weight": 50}},
            "personality": {"traits": ["外向", "细心", "幽默"], "mbti": "ENFP"},
            "hobbies": [
                {"name": "摄影", "level": "资深"},
                {"name": "旅行", "level": "爱好者"},
            ],
        }

        create_or_update_profile(
            contact.id,
            basic_info=complex_data["basic_info"],
            personality=complex_data["personality"],
            hobbies=complex_data["hobbies"],
        )

        p = get_profile(contact.id)
        assert p.basic_info == complex_data["basic_info"]
        assert p.personality == complex_data["personality"]
        assert p.hobbies == complex_data["hobbies"]

    def test_get_all_profiles(self, temp_db):
        from src.storage.contact_dao import create_contact
        from src.storage.profile_dao import create_or_update_profile, get_all_profiles

        a = create_contact("A")
        b = create_contact("B")
        create_or_update_profile(a.id)
        create_or_update_profile(b.id)

        all_p = get_all_profiles()
        assert len(all_p) == 2


# ============================================================
# 级联删除测试
# ============================================================

class TestCascadeDelete:
    """测试联系人删除时的级联效果。"""

    def test_delete_contact_cascades_messages(self, temp_db):
        from src.storage.contact_dao import create_contact, delete_contact
        from src.storage.message_dao import create_message, get_message_count
        from src.models.enums import SenderType

        c = create_contact("测试")
        create_message(c.id, SenderType.USER, "消息1")
        create_message(c.id, SenderType.TARGET, "消息2")
        assert get_message_count(c.id) == 2

        delete_contact(c.id)
        assert get_message_count(c.id) == 0  # 级联删除

    def test_delete_contact_cascades_profile(self, temp_db):
        from src.storage.contact_dao import create_contact, delete_contact
        from src.storage.profile_dao import create_or_update_profile, get_profile

        c = create_contact("测试")
        create_or_update_profile(c.id, affinity_score=42)
        assert get_profile(c.id) is not None

        delete_contact(c.id)
        assert get_profile(c.id) is None  # 级联删除
