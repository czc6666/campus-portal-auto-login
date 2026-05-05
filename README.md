# 校园网 Portal 自动登录框架

一个面向中国校园网认证页场景的自动登录、页面采集与故障排查开源项目。

> 它不是“所有学校都开箱即用”的万能脚本。  
> 它更适合已经知道自己学校使用 Web Portal 认证、并愿意按页面实际情况做少量适配的人。

## 仓库地址

- GitHub: `czc6666/campus-portal-auto-login`

---

## 项目简介

这个仓库提炼自一个长期闭源维护的校园网自动登录项目。

它的目标不是把所有学校都做成“一键通用”，而是提供一套可复用的基础骨架，让你可以围绕校园网 Portal 认证页去做：

- 自动登录
- 页面采集
- 状态校验
- 故障排查
- 新学校适配

项目主体分成四层：

- `核心_core/`：通用登录引擎、探针、浏览器操作、提交流程、诊断导出
- `学校配置_profiles/`：学校差异配置层
- `examples/`：公开示例入口与环境变量用法
- `工具_tools/采集器_collector/`：用于采集目标学校 Portal 页面信息

一句话：

**这是一个配置驱动的校园网 Portal 自动化适配项目，而不是一个承诺适配所有学校的一键工具。**

---

## 为什么值得开源

这个项目的价值不在“某一个学校能不能一键登录”，而在于沉淀出了一套可复用的方法：

- 把“一校一脚本”抽象成 `SchoolProfile`
- 把常见 Portal 脏页面问题做成可复用策略
- 把失败后的排障流程做成结构化诊断导出
- 把新学校页面建模做成 Collector 采集器

所以它更像一个 **校园网 Portal 自动化工程骨架**，而不是一个一次性脚本。

---

## 浏览器运行方式

这个项目历史上主要有两种运行方式：

### 1. 源码运行方式
特点：

- 更适合开发、调试、研究 Portal 页面
- 早期更容易兼容 Linux / 跨平台源码运行
- 通常依赖 Python 环境、Playwright 和对应浏览器运行时

### 2. Windows 本地运行方式
特点：

- 更适合日常自用或在 Windows 机器上长期运行
- 当前代码更偏向用 **Playwright 的包去驱动系统里的 Edge**
- 也方便后续继续做 PyInstaller 单文件打包

更准确地说：

**这个项目依赖 Playwright 的自动化能力，但既保留了较通用的源码运行方式，也保留了更贴近 Windows 实际使用的 Edge 优先方式。**

---

## 项目亮点

### 1. 配置驱动，而不是一校一坨脚本
通过 `SchoolProfile` 把这些差异配置化：

- 登录页 URL 候选
- 用户名 / 密码 / 登录按钮选择器
- 运营商选择器
- 验证码检测
- 输入策略
- 提交策略
- 浏览器策略
- Wi-Fi 重连策略
- 登录后等待与探针参数

### 2. 针对脏 Portal 页面做了鲁棒性兜底
内核已经内置多种策略：

- 输入：`fill_first / js_first / keyboard`
- 提交：`click_then_enter / keyboard_tab_enter`
- frame 查找
- DOM click / onclick / portal 页面脚本兜底

### 3. 失败时自动导出诊断材料
登录失败时会输出：

- `runtime.log`
- `events.jsonl`
- `attempts.json`
- `probe.json`
- `portal_check.json`
- `net_state.json`
- `final.html / final.png / frames/`

适合远程排障和后续 Profile 修正。

### 4. 自带 Collector 采集器
当目标学校无法直接适配时，可以先跑 `collector.py` / `collector.exe`：

- 自动记录导航链
- 保存主页面 DOM 和 frame DOM
- 猜测用户名/密码/登录按钮等 selector
- 记录 click / input / submit 事件
- 打包成 zip 供后续分析

---

## 项目总览图

下图更适合作为项目能力总览，而不是 README 顶部头图。它集中展示了这个项目的核心定位：自动登录、页面采集、状态校验、配置管理与日志排障。

![项目总览图](docs/assets/project-overview.jpg)

---

## 当前公开版包含什么

这个公开仓当前主要包含：

- 通用核心逻辑
- `SchoolProfile` 类型定义
- 脱敏后的示例 Profile
- 江西理工大学公开示例配置：`学校配置_profiles/jxust.py`
- Collector 源码
- 示例入口与说明文档

这个公开仓**不包含**：

- 真实客户账号入口
- 大部分已验证学校的现成配置
- 历史故障归档
- 历史采集包
- exe 打包产物
- 私有交付工作流资料

---

## 已适配学校说明

历史上这个项目已经适配过一些学校 / Portal 场景，包括：

- 江西理工大学
- 太原理工大学（学校登录模式已改，原配置已失效）
- 北京理工大学
- 上海大学
- 燕山大学
- 山东外国语职业技术大学
- 常州工学院
- 成都航空职业技术学院
- 亳州学院

当前公开仓里，**只额外公开江西理工大学配置**。原因很简单：

- 江西理工大学是项目作者自己的学校
- 把这份配置公开出来，更像是一种校友向母校做的小贡献
- 其他学校的现成配置暂不直接公开，主要是为了避免维护成本失控，同时保留后续适配交流空间

如果你只是想看一个真实可用的学校配置，优先参考：

- `学校配置_profiles/jxust.py`
- `学校配置_profiles/example_drcom.py`
- `学校配置_profiles/example_srun.py`
- `学校配置_profiles/example_gportal.py`

---

## 目录结构

```text
campus-portal-auto-login/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── docs/
├── examples/
│   ├── .env.example
│   └── run_with_env.py
├── scripts/
│   └── build_collector.bat
├── 学校配置_profiles/
│   ├── __init__.py
│   ├── types.py
│   ├── example_drcom.py
│   ├── example_srun.py
│   ├── example_gportal.py
│   └── jxust.py
├── 工具_tools/
│   └── 采集器_collector/
│       └── collector.py
└── 核心_core/
    ├── actions.py
    ├── browser.py
    ├── diag.py
    ├── portal.py
    ├── probe.py
    ├── runner.py
    ├── types.py
    └── wifi.py
```

---

## 快速开始

## 1. 安装依赖

先安装基础依赖：

```bash
pip install -r requirements.txt
```

如果你走的是**源码运行方式**，通常还需要准备 Playwright 浏览器运行时：

```bash
python -m playwright install chromium
```

如果你更偏向 **Windows + Edge** 的运行方式，重点是：

- 当前机器已安装 Microsoft Edge
- 环境里有 `playwright`
- 运行时优先由 Playwright 调用系统 Edge，而不是优先使用 Playwright 自带 Chromium

---

## 2. 运行示例

### Linux / macOS shell 示例

```bash
export PROFILE_MODULE=学校配置_profiles.example_drcom
export CAMPUS_USERNAME=your-campus-account
export CAMPUS_PASSWORD=your-campus-password
export RUN_ONCE=1
python examples/run_with_env.py
```

### Windows PowerShell 示例

```powershell
$env:PROFILE_MODULE="学校配置_profiles.example_drcom"
$env:CAMPUS_USERNAME="your-campus-account"
$env:CAMPUS_PASSWORD="your-campus-password"
$env:RUN_ONCE="1"
python examples\run_with_env.py
```

### Windows CMD 示例

```cmd
set PROFILE_MODULE=学校配置_profiles.example_drcom
set CAMPUS_USERNAME=your-campus-account
set CAMPUS_PASSWORD=your-campus-password
set RUN_ONCE=1
python examples\run_with_env.py
```

如果你想一直守护循环，而不是只跑一次：

```powershell
$env:RUN_ONCE="0"
python examples\run_with_env.py
```

---

## 3. 如果示例不适合你的学校

不要先急着改核心逻辑，建议按这个顺序来：

1. 先看公开的江西理工大学配置 `学校配置_profiles/jxust.py` 和几个脱敏示例
2. 如果页面结构很陌生，先跑 Collector 采集 Portal 页面
3. 再新增或调整你自己的 Profile

---

## 适合什么场景

适合：

- Windows 上的校园网 Web Portal 自动登录
- 想把“一校一脚本”整理成统一框架
- 已知学校 Portal 可被浏览器自动化操作
- 需要远程排障、复盘失败现场
- 需要兼顾“源码运行调试”和“Windows 本地运行”两种方式

不适合：

- 期待“不配置就适配所有学校”
- 期待完全零维护、永久稳定
- 目标学校强依赖验证码 / 二次验证 / App 扫码
- 完全无法接受页面结构变化带来的维护成本

---

## 安全与边界

请务必注意：

- **不要把真实账号密码提交到 Git 仓库**
- 不要公开上传未脱敏的故障包、采集包、页面 HTML
- 某些 Portal 的 URL 带设备参数、会话参数，不能长期硬编码
- 登录成功不要只看页面跳转，必须结合联网探针判断

更多见：

- `docs/privacy-and-safety.md`
- `docs/troubleshooting.md`

---

## 文档索引

- `docs/architecture.md`：架构与执行流说明
- `docs/profiles.md`：Profile 字段与适配方法
- `docs/collector.md`：Collector 采集器说明
- `docs/troubleshooting.md`：常见问题与排障思路
- `docs/privacy-and-safety.md`：隐私、安全与公开边界
- `docs/migration-notes.md`：从私有交付项目提炼为公开仓的迁移说明

---

## 项目定位

如果你打算基于这个项目二次开发，推荐把它理解成：

**一个“配置驱动的浏览器自动化状态机 + 失败取证系统 + 新站点采集工具”。**

这样理解它，会比把它当作“万能校园网脚本”更准确。
