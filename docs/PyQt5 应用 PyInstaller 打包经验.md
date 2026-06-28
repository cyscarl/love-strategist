# PyInstaller 打包经验总结


**Python**: 3.9+ / PyInstaller: 6.0+ / PyQt5

## 一、核心原则

### 1.1 区分只读资源与可写数据

PyInstaller `--onedir` 模式下，被导入模块的 `__file__` 指向 `_internal/` 内部：

text

```
dist/LoveStrategist/
├── LoveStrategist.exe     ← sys.executable 在这
└── _internal/             ← 所有 Python 代码、依赖、打包资源在这
```



**只读资源**（icons, QSS, 静态资源）：保持在 `_internal/` 内，用 `__file__` 相对路径访问。
**可写数据**（配置 config.yaml, 日志, 数据库 love_strategist.db）：必须落到 exe 同级，用 `get_app_dir()`：

python

```
import sys
import os

def get_app_dir():
    """获取应用可写数据目录（exe 所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# 使用示例
APP_DIR = get_app_dir()
CONFIG_PATH = os.path.join(APP_DIR, 'config', 'config.yaml')
DB_PATH = os.path.join(APP_DIR, 'data', 'love_strategist.db')
LOG_DIR = os.path.join(APP_DIR, 'logs')
```



### 1.2 配置文件外置

配置文件 `config/config.yaml` 放在 exe 同级，打包后用户可直接编辑。首次启动时，若配置文件不存在，自动从 `_internal/config/config.yaml.template` 复制到 `config/config.yaml`。

text

```
dist/LoveStrategist/
├── LoveStrategist.exe
├── config/
│   └── config.yaml          ← 用户可编辑（首次启动自动生成）
├── data/
│   └── love_strategist.db   ← 数据库（首次启动自动创建）
├── logs/                    ← 日志目录（运行时生成）
└── _internal/
    ├── config/
    │   └── config.yaml.template  ← 只读模板
    ├── src/...
    └── PyQt5/...
```



### 1.3 路径解析工具函数

python

```
# src/utils/path_utils.py
import sys
import os

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_resource_path(relative_path):
    """获取只读资源路径（开发/打包统一）"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS  # PyInstaller 设置的临时目录
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)

def get_data_path(relative_path):
    """获取可写数据路径（exe 同级）"""
    return os.path.join(get_app_dir(), relative_path)
```



## 二、已踩坑与避坑指南

### 坑 1: sys.stderr 在 console=False 时为 None

**症状**: 双击 exe 崩溃，`TypeError: Cannot log to objects of type 'NoneType'`

**原因**: `--windowed` (console=False) 编译的 Windows 应用无控制台，`sys.stderr` 和 `sys.stdout` 为 `None`，loguru 的 `logger.add(sys.stderr, ...)` 向 None 写入。

**修复**: 在 `src/utils/logger.py` 中添加判断：

python

```
# src/utils/logger.py
import sys
from loguru import logger

# 移除默认 handler
logger.remove()

# 添加文件日志（始终开启）
logger.add(
    os.path.join(APP_DIR, 'logs', 'love_strategist.log'),
    rotation='1 day',
    retention='30 days',
    level='DEBUG',
    encoding='utf-8'
)

# 控制台输出仅在开发环境或 console=True 时开启
if sys.stderr is not None:
    logger.add(sys.stderr, level='INFO')
```



### 坑 2: 配置文件默认值覆盖用户配置

**症状**: 用户修改了 `config/config.yaml` 中的 API Key，重启应用后发现又被重置为默认值或模板值。

**原因**: `config.py` 启动时直接读取模板文件覆盖了用户配置，或 `load_config()` 未正确处理配置合并逻辑。

**修复**: 严格区分模板加载和用户配置加载：

python

```
# src/utils/config.py
def load_config():
    """加载用户配置，若不存在则从模板创建"""
    user_config_path = get_data_path('config/config.yaml')
    template_path = get_resource_path('config/config.yaml.template')
    
    if not os.path.exists(user_config_path):
        # 首次启动：复制模板到用户目录
        os.makedirs(os.path.dirname(user_config_path), exist_ok=True)
        shutil.copy(template_path, user_config_path)
    
    with open(user_config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_config(config):
    """保存用户配置（仅保存到用户目录，不覆盖模板）"""
    user_config_path = get_data_path('config/config.yaml')
    with open(user_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
```



### 坑 3: UPX 压缩损坏 PyQt5 DLL

PyInstaller 的 UPX 压缩可能损坏 Qt5 DLL（如 `Qt5Core.dll`、`Qt5Gui.dll`、`Qt5Widgets.dll`），导致启动报错或随机崩溃。

**修复**: `.spec` 中设置 `upx=False`，或在 PyInstaller 命令行中添加 `--upx-dir=""` 禁用 UPX。

### 坑 4: 遗漏静态资源文件（QSS、图标、模板）

静态引用的 QSS 文件、图标、配置模板不在 PyInstaller 的依赖分析图中，需在 `.spec` 的 `datas` 中显式声明。

**常见遗漏**:

- `src/ui/styles.qss` — 全局样式
- `icons/*.png`, `icons/*.svg` — 图标资源
- `config/config.yaml.template` — 配置模板

### 坑 5: PyQt5 平台插件和图片格式插件遗漏

需确认以下 DLL 存在于打包目录中：

| 路径                                                        | 用途             |
| :---------------------------------------------------------- | :--------------- |
| `_internal/PyQt5/Qt5/plugins/platforms/qwindows.dll`        | Windows 平台插件 |
| `_internal/PyQt5/Qt5/plugins/imageformats/qjpeg.dll`        | JPEG 图片支持    |
| `_internal/PyQt5/Qt5/plugins/imageformats/qgif.dll`         | GIF 支持         |
| `_internal/PyQt5/Qt5/plugins/styles/qwindowsvistastyle.dll` | Windows 视觉风格 |

PyInstaller 的 PyQt5 hook 通常自动处理，但首次打包后需验证。

### 坑 6: EXE() + COLLECT() 产生重复 exe

**症状**: `dist/` 下同时存在 `LoveStrategist.exe` 和 `LoveStrategist/` 目录

**原因**: `.spec` 中 `EXE()` 先生成 `dist/LoveStrategist.exe`，`COLLECT()` 再将其复制到 `dist/LoveStrategist/` 目录，但原始的 exe 不会自动删除。

**修复**: 构建脚本末尾删除冗余的根目录 exe，只保留 `dist/LoveStrategist/` 作为最终产物。

python

```
# 在 build.py 或 spec 中处理
import os
root_exe = os.path.join('dist', 'LoveStrategist.exe')
if os.path.exists(root_exe):
    os.remove(root_exe)
```



或使用 `--onefile` 模式避免此问题（但启动较慢）。

## 三、Spec 文件关键配置

python

```
# LoveStrategist.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 只读资源：格式为 (源路径, 目标路径)
        ('config/config.yaml.template', 'config'),
        ('src/ui/styles.qss', 'src/ui'),
        ('icons', 'icons'),
    ],
    hiddenimports=[
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'requests',
        'yaml',
        'sqlite3',
        'PIL',                # Pillow 图片处理
        'PIL.Image',
        'PIL.ImageQt',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LoveStrategist',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                        # ← 必须禁用 UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                    # ← 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icons/app.ico',             # ← 应用图标
)

# 使用 COLLECT 生成 onedir 包
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,                        # ← 必须禁用 UPX
    upx_exclude=[],
    name='LoveStrategist',
)
```



## 四、构建脚本（build.py）

python

```
# build.py
import os
import sys
import shutil
import subprocess

def clean_build():
    """清理之前的构建产物"""
    dirs = ['build', 'dist']
    for d in dirs:
        if os.path.exists(d):
            shutil.rmtree(d)
    # 清理 .spec 文件
    for f in os.listdir('.'):
        if f.endswith('.spec'):
            os.remove(f)

def build():
    # 1. 清理
    clean_build()
    
    # 2. 生成 spec 文件
    subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--name=LoveStrategist',
        '--onedir',
        '--windowed',
        '--add-data=config/config.yaml.template;config',
        '--add-data=src/ui/styles.qss;src/ui',
        '--add-data=icons;icons',
        '--hidden-import=PyQt5.sip',
        '--hidden-import=PIL',
        '--hidden-import=requests',
        '--hidden-import=yaml',
        '--icon=icons/app.ico',
        'src/main.py'
    ], check=True)
    
    # 3. 删除冗余根目录 exe（COLLECT 产生的重复）
    root_exe = os.path.join('dist', 'LoveStrategist.exe')
    if os.path.exists(root_exe):
        os.remove(root_exe)
        print(f"✅ 已删除冗余文件: {root_exe}")
    
    # 4. 创建分发所需目录结构
    dist_dir = os.path.join('dist', 'LoveStrategist')
    os.makedirs(os.path.join(dist_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, 'logs'), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, 'config'), exist_ok=True)
    
    # 5. 复制配置模板到 _internal 和外部
    # 外部模板用于首次启动复制
    shutil.copy('config/config.yaml.template', os.path.join(dist_dir, 'config', 'config.yaml.template'))
    
    print(f"✅ 打包完成: {dist_dir}")
    print(f"📦 请检查以下文件是否存在:")
    print(f"   - {dist_dir}/LoveStrategist.exe")
    print(f"   - {dist_dir}/_internal/PyQt5/Qt5/plugins/platforms/qwindows.dll")
    print(f"   - {dist_dir}/config/config.yaml.template")

if __name__ == '__main__':
    build()
```



## 五、分发前检查清单

### 5.1 核心功能检查

- exe 双击启动不报错（无 Python 环境运行）
- 首次启动自动创建 `config/config.yaml`（从模板复制）
- 首次启动自动创建空 `data/love_strategist.db`（建表）
- 日志写入 `logs/love_strategist.log`（而非 `_internal/logs/`）
- `config/config.yaml` 中填入 API Key 后，调用智能体功能正常
- 联系人创建、消息发送、聊天记录加载正常
- 好感度显示、人物画像弹窗正常
- 滚动分页加载历史消息正常

### 5.2 文件与路径检查

- `config/config.yaml` 位于 exe 同级（而非 `_internal/` 内）
- `data/love_strategist.db` 位于 exe 同级
- `logs/` 日志目录位于 exe 同级
- `_internal/` 内无 `config.yaml` 或其他可写文件
- `_internal/PyQt5/Qt5/plugins/platforms/qwindows.dll` 存在
- `_internal/PyQt5/Qt5/plugins/imageformats/qjpeg.dll` 存在（头像图片显示需要）
- `_internal/config/config.yaml.template` 存在
- `_internal/src/ui/styles.qss` 存在（UI 样式）

### 5.3 环境与依赖检查

- VC++ 运行时已随包（`_internal/VCRUNTIME140.dll` 存在）
- 分发包包含 `config/` 空目录结构（用于存放 config.yaml）
- 分发包包含 `data/` 空目录结构（用于存放数据库）
- 分发包包含 `logs/` 空目录结构（用于存放日志）

### 5.4 体积检查

- 体积合理（PyQt5 + 依赖项目约 80~120MB 为正常范围）
- `_internal/` 下无重复的 `.pyc` 或 `.py` 源码文件（仅 `.pyc` 即可）

## 六、命令行快速打包（备选）

如不使用 `.spec` 文件，可直接使用 PyInstaller 命令：

bash

```
# 基本打包（onedir + windowed + 禁用UPX）
pyinstaller --name="LoveStrategist" ^
            --onedir ^
            --windowed ^
            --upx-dir="" ^
            --add-data "config/config.yaml.template;config" ^
            --add-data "src/ui/styles.qss;src/ui" ^
            --add-data "icons;icons" ^
            --hidden-import "PyQt5.sip" ^
            --hidden-import "PIL" ^
            --hidden-import "requests" ^
            --hidden-import "yaml" ^
            --icon "icons/app.ico" ^
            src/main.py

# 如需 console 调试（显示控制台窗口，方便查看错误）
pyinstaller --name="LoveStrategist_debug" ^
            --onedir ^
            --console ^
            --upx-dir="" ^
            --add-data "config/config.yaml.template;config" ^
            --add-data "src/ui/styles.qss;src/ui" ^
            --add-data "icons;icons" ^
            --icon "icons/app.ico" ^
            src/main.py
```



> **提示**: 首次打包建议使用 `--console` 生成调试版本，确认无错误后再生成 `--windowed` 发布版本。

## 七、技术选型要点

| 决策         | 结论                  | 理由                                       |
| :----------- | :-------------------- | :----------------------------------------- |
| 打包模式     | `onedir`              | 启动快 3-5 秒，更新可替换单文件，调试方便  |
| UPX 压缩     | **禁用**              | 压缩会损坏 PyQt5 DLL，导致启动崩溃         |
| 控制台       | **不显示** (windowed) | 用户不应看到黑窗口，但调试阶段保留 console |
| 配置文件位置 | exe 同级 `config/`    | 用户可手动编辑，应用内设置页可修改         |
| 数据目录     | exe 同级 `data/`      | 与程序文件隔离，便于备份和迁移             |
| 日志目录     | exe 同级 `logs/`      | 用户可查看日志反馈问题，便于远程协助       |
| 资源文件     | 打包到 `_internal/`   | 只读，用户不应修改                         |
| 数据库       | SQLite 单文件         | 纯本地，备份简单（用户只需复制 .db 文件）  |

## 八、常见问题排查

### Q1: 启动后提示 "Failed to load platform plugin"

**原因**: `qwindows.dll` 未正确打包或路径错误。
**解决**: 检查 `_internal/PyQt5/Qt5/plugins/platforms/qwindows.dll` 是否存在。若不存在，手动从 Python 环境复制：`site-packages/PyQt5/Qt5/plugins/platforms/qwindows.dll` → `dist/LoveStrategist/_internal/PyQt5/Qt5/plugins/platforms/`

### Q2: 日志文件未生成

**原因**: 日志目录路径使用了 `__file__` 相对路径，打包后指向了 `_internal/`。
**解决**: 使用 `get_data_path('logs')` 确保日志写入 exe 同级。

### Q3: 打包后体积过大 (>200MB)

**原因**: 可能包含了不必要的依赖或重复文件。
**解决**: 检查 `_internal/` 下是否有 `.py` 源文件（仅保留 `.pyc`），使用 `--exclude-module` 排除未使用的库。

### Q4: 配置文件被重置为默认值

**原因**: 代码中未区分模板和用户配置，启动时用模板覆盖了用户配置。
**解决**: 严格遵循 2.2 节的设计，模板仅用于首次创建，后续仅读取和写入用户配置文件。