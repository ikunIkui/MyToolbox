# MyToolbox 个人效率工具台

毕业设计项目 · Windows 桌面效率工具

---

## 技术栈

- Python 3.10
- PySide6（Qt for Python）
- SQLite + FTS5 全文索引
- APScheduler（定时调度）
- winotify（系统通知）
- winsdk（Windows 定位）
- python-docx / reportlab / pypdf / Pillow（文档处理）
- PyInstaller + Inno Setup（打包发布）

---

## 项目锚点（关键信息）

- 项目名：**MyToolbox**
- 技术栈：**Python 3.10 + PySide6**
- 当前版本：**v0.4.0**
- 数据目录：**`%APPDATA%\MyToolbox\`**
- 主色：**`#4a6bff`**
- 深色背景：**`#1e2128`**
- 主界面：左侧导航（首页 / 日志记录 / 任务 / 更新日志 / 设置）+ 顶部命令栏 + 天气卡片
- 首页 = 功能宫格，按分类分组（时间管理 / 系统工具 / 内容创作 / 系统信息）

---

## 文件清单

| 文件 | 说明 |
|---|---|
| `main.py` | 程序入口、单实例锁、主题初始化 |
| `app_paths.py` | 数据目录、配置读写、资源路径 |
| `theme.py` | 深色/浅色配色、系统主题检测、全局 QSS |
| `anim.py` | 淡入、滑入、阴影动画工具 |
| `widgets.py` | 通用控件（提示条、时长选择、主按钮） |
| `commands.py` | 命令注册表、正则匹配、帮助生成 |
| `scheduler.py` | 倒计时、定时关机、任务调度 |
| `notifier.py` | 系统通知（winotify + 托盘气泡） |
| `screen_notify.py` | 屏幕浮窗通知（四角可选） |
| `logger.py` | 操作日志（SQLite） |
| `task_history.py` | 任务历史（SQLite） |
| `location_win.py` | Windows 系统定位 |
| `weather.py` | 天气数据（三级定位 + Open-Meteo） |
| `weather_widget.py` | 顶部天气卡片 |
| `note_db.py` | 笔记数据库（FTS5 全文索引） |
| `note_page.py` | 笔记页面（编辑 + 搜索 + 导出） |
| `note_classifier.py` | 笔记智能分类 |
| `nlp_reminder.py` | 自然语言提醒识别 |
| `exporter.py` | 导出 Markdown / Word / PDF |
| `doc_convert.py` | 文档互转 |
| `settings_page.py` | 设置页 |
| `autostart.py` | 开机自启（注册表） |
| `changelog.py` | 版本数据 |
| `changelog_widget.py` | 更新日志页面 |
| `features.py` | 功能注册表（宫格 + 分类） |
| `main_window.py` | 主窗口（导航 + 命令栏 + 托盘） |
| `setup.iss` | Inno Setup 安装脚本 |
| `build.bat` | 一键打包脚本 |
| `res/check.svg` | 复选框对勾图标 |

---

## 已完成功能

### 主界面
- 左侧导航：首页 / 日志记录 / 任务 / 更新日志 / 设置
- 顶部命令栏 + 执行按钮 + 天气卡片
- 系统托盘常驻，双击唤起，关闭最小化到托盘
- 单实例锁

### 命令系统
- 命令注册表 + 正则匹配
- 绝对指令：倒计时 / 关机 / 锁屏 / 打开 / 天气 / 帮助
- `/help` 列出所有命令

### 时间管理
- 倒计时，到点弹通知
- 定时关机，关机前 1 分钟提醒，可取消

### 系统工具
- 锁屏（先通知后锁，默认 3 秒）
- 打开程序 / 网址
- 开机自启

### 天气
- 三级定位：系统 → IP → 默认北京
- 手动切换城市 / 自动定位
- 30 分钟自动刷新，6 小时定位缓存

### 笔记
- Markdown 编辑
- SQLite + FTS5 全文搜索
- 保存后进入新草稿
- 智能分类（待办 / 日程 / 灵感 / 学习 / 财务 / 其他）
- 智能提醒（识别时间 + 意图词）
- 导出 Markdown / Word / PDF

### 文档互转
- Markdown → Word
- Word → Markdown
- 图片 → PDF
- PDF 合并 / 拆分

### 数据与日志
- 操作日志：时间 + 来源 + 内容，按级别着色
- 任务历史：已完成 / 已取消 / 已中断
- SQLite 持久化

### 通知
- 系统通知（Windows 操作中心）
- 屏幕浮窗通知（左上 / 左下 / 右上 / 右下）
- 声音开关
- 两个通知可独立开启 / 关闭

### 界面与主题
- 深色 / 浅色主题，跟随系统
- 全局 QSS 统一控件样式
- 动画：页面淡入、卡片错峰、阴影悬停、详情滑入
- 复选框带白色对勾

### 设置页
- 主题切换
- 天气城市
- 通知（声音 / 系统 / 浮窗 / 位置 / 测试按钮）
- 开机自启
- 锁屏延迟
- 数据目录打开
- 清空日志 / 笔记 / 任务历史（带备份提示）

### 打包
- PyInstaller 绿色版
- Inno Setup 安装包（含中文）
- `build.bat` 一键打包

---

## 待做清单

| 优先级 | 功能 | 难度 |
|---|---|---|
| 高 | 全局热键（Alt+Space） | ★ |
| 高 | 待办清单 | ★★ |
| 中 | 系统监控（CPU / 内存 / 网速） | ★ |
| 中 | 窗口自适应 + 记忆尺寸 | ★ |
| 中 | 剪贴板历史 | ★★ |
| 低 | 截图 / 取色器 | ★★ |
| 低 | 自动更新 | ★★★ |
| 低 | 插件化重构 | ★★★ |

---

## 已知问题

- 笔记搜索目前只能搜标题，需改为全文搜索
- 天气偶发 SSL 握手超时（网络原因，可换源）
- 设置页部分交互在浅色主题下对比度偏低

---

## 数据位置

```
%APPDATA%\MyToolbox\
├── config.json       配置（主题、城市、通知等）
├── actions.db        操作日志
├── notes.db          笔记
└── task_history.db   任务历史
```

卸载程序不会删除此目录，用户数据保留。

---

## 打包

双击 `build.bat`，自动完成：

1. PyInstaller 打包绿色版 → `dist\MyToolbox\`
2. Inno Setup 编译安装包 → `Output\MyToolbox_Setup_0.4.0.exe`

手动打包命令：

```bat
python -m PyInstaller -D -w --name MyToolbox ^
  --add-data "res;res" ^
  --hidden-import=winotify ^
  --hidden-import=winsdk ^
  --hidden-import=docx ^
  --hidden-import=reportlab ^
  --hidden-import=reportlab.pdfbase.cidfonts ^
  main.py
```

---

## 当前版本

```
v0.4.0
```

---

## 最近一次改动

- 新增 `screen_notify.py`：屏幕浮窗通知
- 通知位置可选：左上 / 左下 / 右上 / 右下
- `settings_page.py` 加通知开关 + 位置选择 + 测试按钮
- `task_history.py`：任务历史入库
- `main_window.py`：首页导航可回宫格
- `app_paths.py`：加 `notify_system` / `notify_screen` / `notify_position` 配置

---

## 关键决策记录

- 主题用全局 QSS 统一管理，控件只设 objectName 或内联少量样式
- 通知分系统通知和屏幕浮窗，两个独立开关
- 笔记保存后自动进入新草稿
- 任务历史单独一个数据库 `task_history.db`
- 屏幕浮窗用 `QWidget` + `Qt.Tool` + `WA_ShowWithoutActivating`，不抢焦点

---

# 新对话怎么继续

## 一、新对话开头模板

复制下面这段给新的 AI 对话：

```
项目：MyToolbox 个人效率工具台
技术栈：Python 3.10 + PySide6
版本：v0.4.0
主界面：左侧导航（首页 / 日志记录 / 任务 / 更新日志 / 设置）+ 顶部命令栏 + 天气卡片
数据目录：%APPDATA%\MyToolbox

现在想继续做：【这里写你的需求】

涉及的代码我会贴完整文件。
```

## 二、贴代码的规矩

1. 改哪个文件就贴哪个文件，不要一次贴十个
2. 报错先贴完整 Traceback
3. 说清楚：点了什么 → 期望什么 → 实际什么
4. 大改动前先备份

## 三、备份建议

每次大改动前：

```bat
cd C:\Users\任涛\Desktop
xcopy mytoolbox mytoolbox_backup_日期 /E /I
```

或者用 git：

```bat
cd mytoolbox
git init
git add .
git commit -m "改动说明"
```

---

## 联系方式

（毕设答辩用，自行填写）