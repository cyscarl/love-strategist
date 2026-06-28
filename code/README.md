# Love Strategist

基于大模型 API 驱动的聊天辅助工具，分析与目标对象的聊天记录，生成高情商回复建议。

## 快速开始

### 1. 安装依赖

```bash
cd code
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `../config/config.yaml`（首次启动自动从模板创建）：

```yaml
llm:
  api_key: "sk-your-key-here"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4"
```

支持 OpenAI 兼容接口（DeepSeek、智谱、自定义等）。

### 3. 启动

```bash
python src/main.py
```

## 功能

- **联系人管理**：多联系人独立聊天，角色备忘录
- **聊天记录**：手动录入双方消息，气泡显示，分页加载
- **智能回复**：召唤智能体生成 3 条高情商回复（Galgame 多选风格）
- **策略调整**：告诉智能体你的想法，重新制定回复策略
- **人物画像**：自动分析对话，提炼性格/爱好/好感度
- **常开模式**：后台监控，检测负面情绪自动提醒

## 技术栈

| 组件 | 选型 |
|------|------|
| GUI | PyQt5 (仿微信布局) |
| 数据库 | SQLite (WAL 模式) |
| LLM API | OpenAI 兼容接口 |
| 日志 | loguru |
| 测试 | pytest |

## 项目结构

```
code/
├── src/
│   ├── main.py              # 入口
│   ├── ui/                  # UI 层
│   ├── controllers/         # 控制器
│   ├── models/              # 数据模型
│   ├── services/            # 服务层
│   ├── skills/              # Skill 系统
│   ├── storage/             # 数据层
│   └── utils/               # 工具
├── tests/
├── scripts/
└── config/
```

## 运行测试

```bash
pytest tests/
```

## 清理临时文件

```bash
python scripts/clean_temp.py
```
