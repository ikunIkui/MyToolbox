# MyToolbox 个人效率工具台

> 一个 Windows 桌面效率工具：时间管理、笔记、待办、天气、文档转换，一个窗口全搞定。

初稿程序设计项目

---

## 目录

- [这是什么](#这是什么)
- [功能一览](#功能一览)
- [快速开始](#快速开始)
- [命令用法](#命令用法)
- [数据位置](#数据位置)
- [关于收费](#关于收费)
- [后续计划](#后续计划)
- [已知问题](#已知问题)
- [开发环境搭建](#开发环境搭建)
- [编译打包教程](#编译打包教程)
- [常见问题](#常见问题)
- [文件清单](#文件清单)
- [更新日志](#更新日志)
- [许可证](#许可证)
- [致谢](#致谢)
- [联系方式](#联系方式)

---

## 这是什么

MyToolbox 是一个**个人效率工具台**，把日常电脑上零散的小工具整合到一个窗口里：

- 想定个 20 分钟倒计时 → 一句 `倒计时 20 分钟`
- 想 30 分钟后自动关机 → 一句 `关机 30 分钟`
- 随手记个笔记 → 自动分类、自动识别提醒、自动进待办
- 想知道今天啥天气 → 顶部天气卡片实时显示
- 想把 Word 转成 Markdown → 内置文档互转

**特点**：

- 原生 Windows 桌面应用，启动快、无广告
- 深色 / 浅色主题，跟随系统
- 系统通知 + 屏幕浮窗双重提醒
- 数据本地保存，不上传云端
- 完全免费，永久免费

---

## 功能一览

### 时间管理

| 功能 | 说明 |
|---|---|
| 倒计时 | 设个时长，到点弹窗提醒，支持「N 分钟后再提醒」 |
| 定时关机 | N 分钟后自动关机，关机前 1 分钟提醒，可随时取消 |
| 待办清单 | 自动从笔记提取，支持勾选完成、撤销移除、查看原文 |

### 内容创作

| 功能 | 说明 |
|---|---|
| 笔记 | Markdown 编辑，SQLite + FTS5 全文搜索 |
| 智能分类 | 自动识别待办 / 日程 / 灵感 / 学习 / 财务 / 其他 |
| 智能提醒 | 笔记里写"30 分钟后提醒我喝水"，自动创建倒计时 |
| 导出 | Markdown / Word / PDF 一键导出 |
| 文档互转 | Markdown 转 Word、Word 转 Markdown、图片转 PDF、PDF 合并拆分 |

### 系统信息

| 功能 | 说明 |
|---|---|
| 天气 | 三级定位（系统 → IP → 默认北京），30 分钟自动刷新 |

### 系统工具

| 功能 | 说明 |
|---|---|
| 锁屏 | 一键锁定，延迟可配 |
| 打开程序 / 网址 | 命令行直接打开 |
| 系统托盘 | 常驻托盘，双击唤起 |
| 开机自启 | 可选 |

### 通知系统

| 功能 | 说明 |
|---|---|
| 系统通知 | Windows 操作中心原生通知 |
| 屏幕浮窗 | 四角可选（左上 / 左下 / 右上 / 右下） |
| 通知音效 | 3 个内置音效 + 自定义 wav 文件 |
| 时长自适应 | 通知停留时长按内容长度自动调整 |
| 延后提醒 | 倒计时通知带「N 分钟后再提醒」按钮 |

### 界面

| 功能 | 说明 |
|---|---|
| 主题 | 深色 / 浅色，跟随系统 |
| 动画 | 页面淡入、卡片错峰、悬停阴影、启动淡入 |
| 窗口记忆 | 记住上次的大小 / 位置 / 最大化状态 |
| 启动欢迎 | 每天首次启动弹欢迎卡片（日期 / 天气 / 待办数） |

### 命令系统

顶部命令栏支持**自然语言指令**，输入即执行，`/help` 查看全部。

---

## 快速开始

### 方式一：下载安装包（推荐）

1. 打开 Releases 页
2. 下载最新的 `MyToolbox_Setup_x.x.x.exe`
3. 双击安装，一路下一步
4. 从桌面或开始菜单启动

系统要求：Windows 10 / 11（64 位）

### 方式二：绿色版

1. 在 Releases 下载 `MyToolbox_green_x.x.x.zip`
2. 解压到任意目录
3. 双击 `MyToolbox.exe` 运行

### 方式三：从源码运行

```bash
git clone https://github.com/ikunIkui/MyToolbox.git
cd MyToolbox
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

环境要求：Python 3.10+

---

## 命令用法

| 指令 | 说明 |
|---|---|
| `倒计时 20 分钟` | 设 20 分钟倒计时 |
| `关机 30 分钟` | 30 分钟后自动关机 |
| `取消关机` | 取消所有关机任务 |
| `锁屏` | 立即锁屏 |
| `打开 notepad` | 打开记事本 |
| `打开 https://github.com` | 打开网址 |
| `天气 上海` | 切换天气城市 |
| `自动定位` | 恢复天气自动定位 |
| `/help` | 显示所有命令 |

支持的时间单位：秒、分钟、分、小时、时、s、min、h

---

## 数据位置

```
%APPDATA%\MyToolbox\
├── config.json       配置（主题、城市、通知等）
├── actions.db        操作日志
├── notes.db          笔记 + 待办
└── task_history.db   任务历史
```

卸载程序不会删除此目录，用户数据会保留。如需彻底清理，手动删除该目录。

备份建议：定期复制整个 `%APPDATA%\MyToolbox\` 目录。

---

## 关于收费

本项目完全免费，永久免费。

- 个人使用免费
- 商用免费
- 二次开发免费（保留原作者信息即可）
- 无广告、无内购、无会员

如果你觉得有用，给个 Star 就是最大的支持。

---

## 后续计划

以下功能尚未实现，后续版本会补齐：

| 优先级 | 功能 | 状态 |
|---|---|---|
| 高 | 全局热键（可自定义，默认 Alt+Space 唤起） | 计划中 |
| 中 | 系统监控（CPU / 内存 / 网速） | 计划中 |
| 中 | 剪贴板历史 | 计划中 |
| 中 | 窗口布局自适应 | 进行中 |
| 低 | 截图 / 取色器 | 计划中 |
| 低 | 自动更新 | 计划中 |
| 低 | 插件化重构 | 计划中 |

有想要的功能，去 Issue 提。

---

## 已知问题

- 天气偶发 SSL 握手超时（网络原因，可换源）
- 笔记搜索中文分词不够精准（FTS5 默认分词器限制）
- 设置页部分交互在浅色主题下对比度偏低（大部分已修复）

---

## 开发环境搭建

### 1. 装 Python 3.10+

检查：

```bat
python --version
```

没有就去 python.org 下载，安装时勾选 "Add Python to PATH"。

### 2. 克隆项目

```bat
git clone https://github.com/ikunIkui/MyToolbox.git
cd MyToolbox
```

### 3. 创建虚拟环境

```bat
python -m venv venv
```

### 4. 激活虚拟环境

```bat
venv\Scripts\activate
```

激活后命令行前面会出现 `(venv)`。

### 5. 装依赖

```bat
pip install -r requirements.txt
```

没有 requirements.txt 的话：

```bat
pip install PySide6 APScheduler winotify winsdk python-docx reportlab pypdf Pillow
```

国内加速：

```bat
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### 6. 运行

```bat
python main.py
```

---

## 编译打包教程

### 1. 装 PyInstaller

```bat
pip install pyinstaller
```

### 2. 打包命令

在项目根目录跑：

```bat
python -m PyInstaller -D -w --name MyToolbox ^
  --icon=res/app.ico ^
  --add-data "res;res" ^
  --hidden-import=winotify ^
  --hidden-import=winsdk ^
  --hidden-import=docx ^
  --hidden-import=reportlab ^
  --hidden-import=reportlab.pdfbase.cidfonts ^
  --hidden-import=PySide6.QtMultimedia ^
  main.py
```

参数说明：

| 参数 | 说明 |
|---|---|
| `-D` | 打包成文件夹（不是单文件），启动快 |
| `-w` | 无控制台窗口（GUI 程序） |
| `--name MyToolbox` | 生成的 exe 名字 |
| `--icon=res/app.ico` | 程序图标（没图标就删这行） |
| `--add-data "res;res"` | 把 res 目录打进包 |
| `--hidden-import=xxx` | 显式声明隐式依赖 |

完成后：

- `dist/MyToolbox/` 绿色版
- `build/` 中间产物

### 3. Inno Setup 打包安装程序

装 Inno Setup 6：jrsoftware.org/isdl.php

编译：

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
```

完成后：`Output\MyToolbox_Setup_0.5.0.exe`

### 4. 一键打包

项目根目录已有 `build.bat`，双击即可自动完成：

1. 清理旧产物
2. PyInstaller 打包
3. Inno Setup 编译
4. 打开输出目录

---

## 常见问题

### Q1: python 不是内部命令

装 Python 时没勾 "Add Python to PATH"。重新安装并勾选。

### Q2: venv\Scripts\activate 报错"禁止运行脚本"

PowerShell 执行策略限制。改用 CMD，或跑：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Q3: pip install 很慢

换清华源：

```bat
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple PySide6 APScheduler winotify winsdk python-docx reportlab pypdf Pillow
```

### Q4: PyInstaller 报找不到 PySide6.QtMultimedia

```bat
pip install --upgrade PySide6
```

打包时加 `--hidden-import=PySide6.QtMultimedia`。

### Q5: 打包后 exe 运行报错

用控制台版打包一次（去掉 `-w`）：

```bat
python -m PyInstaller -D --name MyToolbox --add-data "res;res" main.py
```

跑 `dist\MyToolbox\MyToolbox.exe`，控制台会显示报错。

### Q6: 打包后图标还是默认的

- 确认 `res/app.ico` 存在
- 确认命令里有 `--icon=res/app.ico`
- 清 `build/` 和 `dist/` 重新打包

### Q7: 天气获取失败

网络问题，或定位服务未开。设置页手动指定城市。

### Q8: 数据在哪里

`%APPDATA%\MyToolbox\`，卸载不删。

### Q9: 怎么卸载

设置 → 应用 → MyToolbox → 卸载。

### Q10: 支持 Mac / Linux 吗

不支持。依赖 Windows 特性（winotify、winsdk、winsound、注册表自启）。

---

## 文件清单

### 核心

| 文件 | 说明 |
|---|---|
| `main.py` | 程序入口、单实例锁、主题初始化 |
| `main_window.py` | 主窗口（导航 + 命令栏 + 托盘） |
| `app_paths.py` | 数据目录、配置读写、资源路径 |
| `theme.py` | 深色 / 浅色配色、系统主题检测、全局 QSS |
| `anim.py` | 淡入、滑入、阴影动画工具 |
| `widgets.py` | 通用控件（提示条、时长选择、主按钮） |

### 功能模块

| 文件 | 说明 |
|---|---|
| `commands.py` | 命令注册表、正则匹配、帮助生成 |
| `scheduler.py` | 倒计时、定时关机、任务调度 |
| `notifier.py` | 系统通知（winotify） |
| `sound.py` | 通知音效播放（winsound） |
| `screen_notify.py` | 屏幕浮窗通知 |
| `welcome.py` | 欢迎卡片逻辑 |
| `logger.py` | 操作日志（SQLite） |
| `task_history.py` | 任务历史（SQLite） |
| `todo_db.py` | 待办数据库 |
| `todo_page.py` | 待办页面 |
| `note_db.py` | 笔记数据库（FTS5 全文索引） |
| `note_page.py` | 笔记页面 |
| `note_classifier.py` | 笔记智能分类 |
| `nlp_reminder.py` | 自然语言提醒识别 |
| `exporter.py` | 导出 Markdown / Word / PDF |
| `doc_convert.py` | 文档互转 |
| `location_win.py` | Windows 系统定位 |
| `weather.py` | 天气数据 |
| `weather_widget.py` | 顶部天气卡片 |
| `settings_page.py` | 设置页 |
| `autostart.py` | 开机自启（注册表） |
| `changelog.py` | 版本数据 |
| `changelog_widget.py` | 更新日志页面 |
| `features.py` | 功能注册表（宫格 + 分类） |

### 打包

| 文件 | 说明 |
|---|---|
| `setup.iss` | Inno Setup 安装脚本 |
| `build.bat` | 一键打包脚本 |
| `requirements.txt` | Python 依赖清单 |

### 资源

| 文件 | 说明 |
|---|---|
| `res/check.svg` | 复选框对勾图标 |
| `res/app.ico` | 程序图标 |
| `res/sounds/*.wav` | 通知音效 |

---

## 更新日志

### v0.5.0 — 2026-09-22

新增：

- 待办清单：自动从笔记提取待办分类或含提醒时间的条目
- 待办支持勾选完成、取消完成、右键打开原笔记、删除笔记
- 待办支持撤销移除，带进度条倒计时（5.5 秒内可撤销）
- 待办标题智能显示：标题无意义时自动取正文第一行
- 待办每行支持查看按钮，弹窗预览笔记原文
- 通知音效系统：内置 3 个音效（默认 / 提示 / 警告）+ 自定义 wav 文件
- 倒计时通知新增 N 分钟后再提醒按钮，N 可在设置里选
- 通知关闭时长按内容自适应
- 窗口记忆：记住上次的大小 / 位置 / 最大化状态
- 启动动画：窗口淡入 + 从 95% 放大到 100%
- 欢迎卡片：每天首次启动弹出，显示日期 / 天气 / 待办数 / 任务数
- 退出时若有进行中任务，弹确认框提示
- 退出时保存窗口几何 + 停止调度器 + 未完成任务记入历史

修复：

- 修复通知关闭按钮不显示的问题
- 修复浅色主题下更新日志卡片、天气卡片、任务面板、宫格卡片配色
- 锁屏延迟改为读配置，不再写死 800ms

### v0.4.5 — 2026-09-20

- 新增深色 / 浅色主题，自动跟随系统
- 设置页支持手动切换主题
- 新增设置页：主题、天气城市、通知声音、开机自启、锁屏延迟
- 新增数据管理：打开数据目录、清空日志 / 笔记
- 复选框新增白色对勾样式

### v0.4.0 — 2026-09-19

- 新增更多功能宫格页
- 新增倒计时、定时关机、锁屏、打开程序、天气城市的可视化页面
- 功能详情页底部新增绝对指令提示条

### v0.3.0 — 2026-09-19

- 命令执行后弹出系统通知
- 通知失败时自动回退到托盘气泡

### v0.2.0 — 2026-09-19

- 新增天气卡片
- 三级自动定位：系统 → IP → 默认北京
- 新增天气城市 / 自动定位指令

### v0.1.0 — 2026-09-19

- 项目初始化
- 左侧导航 + 顶部命令栏 + 首页日志
- 倒计时 / 定时关机 / 锁屏 / 打开程序 指令
- 系统托盘 + 单实例锁

---

## 许可证

MIT License

你可以：

- 自由使用、修改、分发
- 商用

你需要：

- 保留原作者的版权声明

---

## 致谢

- PySide6 — Qt for Python
- APScheduler — 定时调度
- winotify — Windows 通知
- Open-Meteo — 免费天气 API
- ip-api — 免费 IP 定位

---

## 联系方式

- 作者：涛涛
- GitHub：@ikunIkui
- Issue：https://github.com/ikunIkui/MyToolbox/issues

---

如果这个项目对你有帮助，欢迎 Star！