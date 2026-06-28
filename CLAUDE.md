# CLAUDE.md

This file provides guidance to Claude Code ([claude.ai/code](https://claude.ai/code)) when working with code in this repository.

## 项目概述

Python 3.9+ / PyQt5 / SQLite 桌面应用 —— **聊天辅助工具（Love Strategist）**。
通过大模型 API 驱动智能体，分析用户与目标对象的聊天记录，生成高情商回复建议，辅助推进人际关系。

## 项目结构

```
GAL/
├── code/                            # 所有工程代码
│   ├── src/                         # 源代码
│   │   ├── main.py                  # 入口（依赖注入、启动）
│   │   ├── ui/                      # UI 层（PyQt5 视图）
│   │   │   ├── main_window.py       # 主窗口
│   │   │   ├── contact_list.py      # 联系人列表
│   │   │   ├── chat_area.py         # 聊天区域（气泡消息）
│   │   │   ├── input_panel.py       # 输入面板（含切换开关）
│   │   │   ├── profile_dialog.py    # 人物信息弹窗
│   │   │   ├── strategy_dialog.py   # 策略调整弹窗
│   │   │   ├── styles.py            # 集中式 QSS 样式
│   │   │   └── widgets/             # 通用控件
│   │   │       ├── avatar_widget.py # 圆形头像
│   │   │       ├── message_bubble.py# 消息气泡
│   │   │       └── affinity_bar.py  # 好感度进度条
│   │   ├── controllers/
│   │   │   └── chat_controller.py   # 主控制器（信号/槽路由）
│   │   ├── models/
│   │   │   ├── contact.py
│   │   │   ├── message.py
│   │   │   ├── profile.py
│   │   │   └── enums.py
│   │   ├── services/
│   │   │   ├── llm_service.py       # LLM API 封装（含 token 计数）
│   │   │   ├── profile_service.py   # 画像生成/更新
│   │   │   └── context_summarizer.py# 历史摘要生成
│   │   ├── skills/
│   │   │   ├── base.py              # BaseSkill 抽象类
│   │   │   ├── manager.py           # SkillManager（注册/执行）
│   │   │   └── builtin/             # 内置 Skill 实现
│   │   │       ├── reply_generator.py
│   │   │       ├── profile_analyzer.py
│   │   │       ├── sentiment_analyzer.py
│   │   │       ├── topic_suggester.py
│   │   │       └── affinity_estimator.py
│   │   ├── storage/                 # 数据层（SQLite DAO）
│   │   │   ├── database.py          # SQLite 连接与基础操作
│   │   │   ├── contact_dao.py
│   │   │   ├── message_dao.py
│   │   │   └── profile_dao.py
│   │   └── utils/
│   │       ├── config.py            # 配置加载/保存
│   │       ├── logger.py            # 日志（基于 loguru）
│   │       └── thread_utils.py      # QThread 异步封装
│   ├── tests/
│   │   ├── test_storage.py
│   │   ├── test_services.py
│   │   └── test_skills.py
│   ├── scripts/
│   │   └── clean_temp.py            # 清理临时文件
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── README.md
├── docs/                            # 项目文档（设计参考）
├── config/                          # 用户配置目录
│   └── config.yaml                  # 用户配置（gitignore）
├── data/                            # 运行时数据（gitignore）
│   └── love_strategist.db
├── temp/                            # 临时文件（gitignore）
├── logs/                            # 日志文件（gitignore）
├── CLAUDE.md
├── .gitignore
└── .claudeignore
```

## 常用命令

所有命令在 `code/` 目录下执行：

```bash
# 安装依赖
cd code && pip install -r requirements.txt

# 启动应用
cd code && python src/main.py

# 验证关键模块可导入
cd code && python -c "from src.ui.main_window import MainWindow; from src.models.contact import Contact; print('OK')"

# 清理临时文件（开发完成后）
cd code && python scripts/clean_temp.py

# 运行单元测试
cd code && pytest tests/
```

## 数据库架构

使用 **SQLite** 单文件数据库 `data/love_strategist.db`，包含四张核心表：

| 表名         | 用途                                                         |
| :----------- | :----------------------------------------------------------- |
| `contacts`   | 联系人基本信息（id, name, avatar, created_at, updated_at）   |
| `messages`   | 聊天记录（id, contact_id, sender_type, content, content_type, timestamp, is_edited） |
| `profiles`   | 人物画像（contact_id, basic_info, personality, hobbies, behavior_patterns, affinity_score, summary, last_updated） |
| `skill_logs` | Skill 执行日志（可选，用于调试和 token 统计）                |

数据库操作统一在 `code/src/storage/database.py` 中封装，提供 `get_connection()`、`execute_query()`、`execute_write()` 等基础接口，以及各业务 DAO（`ContactDAO`、`MessageDAO`、`ProfileDAO`）。所有写操作需使用 `threading.Lock` 保护，避免多线程冲突。

### 数据路径说明

- **开发环境**：`data/` 目录位于项目根目录（与 `code/` 同级），数据库文件为 `data/love_strategist.db`
- **打包后**：`data/` 目录位于 exe 同级目录，通过 `get_data_path('data/love_strategist.db')` 获取
- 路径工具函数定义在 `code/src/utils/path_utils.py`（如存在），或内嵌于 `config.py`

## 数据模型约定

模型类位于 `code/src/models/`，属性名使用 **snake_case**（如 `contact_id`、`sender_type`），对应数据库字段名。主要模型：

- `Contact`：`id`, `name`, `avatar`, `created_at`, `updated_at`
- `Message`：`id`, `contact_id`, `sender_type`（'user'|'target'）, `content`, `content_type`（'text'|'image'|'emoji'）, `timestamp`, `is_edited`
- `Profile`：`contact_id`, `basic_info`(JSON), `personality`(JSON), `hobbies`(JSON), `behavior_patterns`(JSON), `affinity_score`(int, -100~100), `summary`(str), `last_updated`

## 分层架构

```
UI (PyQt5 Widget)  ←── 持有 Controller 引用，发射信号
Controller (QObject) ←── 持有 UI 引用 + Service 实例，处理业务路由
Service              ←── 纯业务逻辑，调用 DAO 执行数据操作
DAO                  ←── 数据库原子操作（CRUD）
Model                ←── 数据类 / ORM 映射（使用 dataclass 或普通类）
```

- **UI 层**：`code/src/ui/` 下所有视图类，只负责界面渲染和用户交互，不包含业务逻辑。
- **Controller**：`code/src/controllers/chat_controller.py` 是唯一枢纽，接收 UI 事件，调用 Service 和 SkillManager，通过 `pyqtSignal` 通知 UI 更新。
- **Service**：`code/src/services/` 包含 `LLMService`（API 调用）、`ProfileService`（画像生成/更新）、`ContextSummarizer`（上下文摘要）。各 Service 接受 DAO 实例，不直接操作数据库。
- **Skill 系统**：`code/src/skills/` 下所有 Skill 继承 `BaseSkill`，由 `SkillManager` 注册和执行。Skill 执行时通过 Controller 获取上下文，返回结果。

所有依赖注入在 `code/src/main.py` 中完成（创建 DAO → Service → Controller → UI 并相互注入）。

## Token 优化策略（关键）

**绝不**将完整聊天记录全部送入 LLM。采用三层上下文结构：

1. **人物画像**（`profiles.summary` + 结构化字段）：由 `ProfileService` 定期从聊天记录提炼，约占 200-300 token。
2. **近期对话窗口**：默认最近 30 条消息，由 `MessageDAO` 按时间倒序获取，约占 800-1500 token。
3. **历史摘要**：对 30 条之前的对话，由 `ContextSummarizer` 调用 LLM 生成 300 字以内摘要，随窗口滑动更新。

最终 Prompt 组装顺序：`[系统指令] + [人物画像] + [历史摘要] + [近期对话] + [用户指令]`。总 token 控制在 2500 以内。

## 聊天记录分页加载

- 打开联系人时，`ChatController` 调用 `MessageDAO.get_recent(contact_id, limit=50)` 加载最近 50 条。
- `ChatArea` 监听滚动条滚动到顶部，发射 `load_older` 信号 → Controller 调用 `MessageDAO.get_before(contact_id, before_timestamp, limit=50)` 追加到列表顶部。
- 所有消息按时间戳升序显示（旧在上，新在下）。

## 智能体交互模式

- **静默模式（默认）**：智能体仅读取最新消息，不主动发言。用户点击"召唤"按钮 → Controller 收集上下文 → 调用 `ReplyGenerator` Skill → 生成 3 条回复建议 → UI 显示选择按钮。
- **常开模式**：用户可通过设置开启。智能体在后台持续监控，当检测到冷场或情绪波动时，通过系统托盘通知或 UI 角标提醒用户。
- **策略调整弹窗**：点击常驻"策略调整"按钮 → 弹出模态对话框，用户输入想法（如"她好像不开心，换个轻松话题"）→ Controller 重新调用 Skill（带上额外指令）生成新回复。

## 配置管理

用户配置位于 `config/config.yaml`（不入 Git，首次启动自动从模板生成）：

```yaml
llm:
  api_key: "your-key"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4"
  timeout: 30
ui:
  theme: "light"   # 或 "dark"
  language: "zh-CN"
```

`code/src/utils/config.py` 提供 `load_config()`、`save_config()`、`get_llm_config()` 等函数。配置变更通过 Controller 通知各 Service 重新加载。

首次启动若无 `config/config.yaml`，自动从 `code/config/config.yaml.template` 复制并弹出配置引导。

## UI 设计规范（仿微信）

- **布局**：左侧联系人列表（`QListWidget`），右侧聊天区域（`QListWidget` 气泡消息），下方输入面板（`QTextEdit` + 发送按钮 + 发言人切换开关）。
- **联系人项**：显示头像（圆形）、名称、最后一条消息预览。
- **消息气泡**：用户消息右对齐（蓝色背景），目标消息左对齐（白色背景）。
- **输入面板**：下方包含"我/对方"切换开关（`QComboBox`），"召唤智能体"按钮，"策略调整"按钮。
- **头像点击**：弹出 `ProfileDialog` 显示人物基本信息、性格爱好、好感度（进度条 -100~100）。
- **风格**：QSS 统一在 `code/src/ui/styles.py` 中管理，定义 `COLORS`、`FONTS`、`GLOBAL_QSS`。
- **详细参考**：UI 布局、颜色方案、字体规范、间距规范见 `docs/ui布局参考.md`。

## Skill 系统

所有 Skill 位于 `code/src/skills/builtin/`，继承 `BaseSkill` 并实现 `execute(context: dict) -> dict`。

内置 Skill：

| Skill 名称           | 功能                             | 触发时机         |
| :------------------- | :------------------------------- | :--------------- |
| `ReplyGenerator`     | 生成 3 条回复建议（核心 Skill）  | 用户点击召唤     |
| `ProfileAnalyzer`    | 分析对话，更新人物画像           | 每次对话后/定时  |
| `SentimentAnalyzer`  | 情感分析，判断对方情绪           | 每次收到新消息   |
| `TopicSuggester`     | 话题推荐（破冰/延续/深入）       | 用户主动请求     |
| `AffinityEstimator`  | 好感度估算（结合情感和互动频率） | 每次对话后更新   |

Skill 在 `SkillManager` 中注册，可通过配置文件启用/禁用。新增 Skill 只需在 `builtin/` 下创建新文件，并在 `__init__.py` 中导入注册。

## 回复风格约束

在系统提示词中明确约束（详见 `docs/回复风格控制.md`）：

1. 接近 00 后日常交流方式，自然不刻意
2. 多用碎片化、生活化的短文本，避免长篇大论
3. 禁止土味情话和油腻表达
4. 初期：以了解对方、消除隔阂为主
5. 后期：提供情绪价值，适度推进关系

## 开发完成检查清单

每次任务完成后执行：

### 1. 代码验证

- `cd code && python src/main.py` 启动无报错
- 新功能 UI 验证通过（有显示环境时）
- 关键 import 正常：`cd code && python -c "from src.ui.xxx import Xxx"`

### 2. 文档更新（按需）

| 文档               | 何时更新             |
| :----------------- | :------------------- |
| `README.md`        | 新增功能、配置项变更 |
| `CLAUDE.md`        | 架构、重要流程变更   |
| `docs/用户手册.md` | 面向用户的 UI 变化   |

### 3. 开发总结

在 `docs/summaries/` 下新建 `YYYY-MM-DD-开发总结.md`，内容：任务目标、修改文件、关键技术点、待办事项。

### 4. 清理

- 无 `print()` 残留（使用 `from src.utils.logger import logger`）
- 无注释掉的死代码
- 无临时/测试文件（如 `temp/` 下的文件已移除）

## 核心规则

1. **收到任务时，先检查是否有匹配的 skill** — 哪怕只有 1% 的可能性也要检查（使用 `Skill` 工具）。
2. **设计先于编码** — 收到功能需求时，先用 brainstorming skill 做需求分析，明确影响范围和依赖。
3. **验证先于完成** — 声称完成前必须运行验证命令（启动、导入测试）。

## 红线

- **NEVER** 在代码中硬编码 API Key（必须从 `config.yaml` 读取）
- **ALWAYS** 外部 API 调用设置超时（`timeout=30`），并在 `QThread` 中执行，避免阻塞 UI
- **NEVER** 将完整聊天记录直接拼接进 Prompt（必须使用三层上下文策略）
- **ALWAYS** 数据库操作使用参数化查询（防 SQLite 注入）
- **禁止**在 UI 线程中执行耗时的 LLM 调用或数据库批量查询
