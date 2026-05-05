# 校园网 Portal 自动登录框架

一个兼容 **Windows 交付场景** 与 **源码运行场景（含早期 Linux 路线）** 的校园网 Portal 自动化登录、故障诊断与新站点采集框架。

> 它不是“所有学校都开箱即用”的万能脚本。  
> 它更适合这样的人：已经知道自己的学校使用的是 Web Portal 认证，愿意通过 Profile 适配页面差异，或者先跑 Collector 采集登录页信息再做适配。

## 仓库地址

- GitHub: `czc6666/campus-portal-auto-login`

---

## 这个项目是什么

这个仓库提炼自一个长期闭源维护的校园网自动登录项目。

核心思路是把问题拆成四层：

- `核心_core/`：通用登录引擎、探针、浏览器操作、提交流程、Wi-Fi 重连、诊断导出
- `学校配置_profiles/`：学校差异配置层
- `examples/`：公开示例入口与环境变量用法
- `工具_tools/采集器_collector/`：当现有 Profile 不适用时，用于采集目标学校 Portal 页面信息

一句话：

**这是一个配置驱动的校园网 Portal 自动化适配框架，而不是一个承诺适配所有学校的一键工具。**

---

## 为什么这个项目值得开源

它开源的价值不在“某一个学校能不能一键登录”，而在于沉淀出了几件可以复用的东西：

- 把“一校一脚本”抽象成 `SchoolProfile`
- 把校园网 Portal 自动化里常见的脏页面问题做成了可复用策略
- 把“失败后怎么排障”做成了结构化证据导出
- 把“新学校怎么建模”做成了 Collector 采集器

所以它更像一个 **校园网 Portal 自动化工程骨架**，不是一个单次脚本成品。

---

## 两条实际运行路线

这个项目历史上其实有两条路线，不是一条：

### 路线 A：源码运行路线（更通用）
特点：

- 早期主要通过 Playwright 自带浏览器运行
- 当时更容易兼容 Linux / 跨平台源码运行
- 适合开发、调试、研究 Portal 页面
- 代价是用户侧通常需要 Python 环境与依赖安装

### 路线 B：Windows 交付路线（更适合给客户）
特点：

- 现在更偏向用 **Playwright 的包去驱动系统里的 Edge**
- 适合后续用 PyInstaller 打包成单文件 exe
- 更方便直接丢给客户电脑运行
- 不要求客户自己先配 Python 环境

所以更准确的说法不是“项目只用 Playwright 自带浏览器”，也不是“完全不用 Playwright 浏览器”，而是：

**项目同时保留了源码运行的通用路线，以及面向 Windows 交付的 Edge 优先路线。**

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
当目标学校无法直接适配时，可以让用户先跑 `collector.py` / `collector.exe`：

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

## 当前公开版保留了什么

这个公开仓保留的是：

- 通用核心逻辑
- `SchoolProfile` 类型定义
- 脱敏后的示例 Profile
- 江西理工大学公开示例配置：`学校配置_profiles/jxust.py`
- Collector 源码
- 示例入口与说明文档

这个公开仓**没有**包含：

- 真实客户账号入口
- 大部分已验证学校的现成配置
- 历史故障归档
- 历史采集包
- exe 打包产物
- 私有交付工作流资料

---

## 已适配学校说明

历史上这个项目已经适配过一些学校/Portal 场景，包括：

- 江西理工大学
- 太原理工大学（学校登录模式已改，原配置已失效）
- 北京理工大学
- 上海大学
- 燕山大学
- 山东外国语职业技术大学
- 常州工学院
- 成都航空职业技术学院
- 亳州学院

当前公开仓里，**只额外公开江西理工大学配置**，原因很简单：

- 江西理工大学是项目作者自己的学校
- 把这份配置公开出来，更像是一种校友向母校做的小贡献
- 其他学校的现成配置暂不直接公开，主要是为了避免维护成本失控，也保留后续协助适配与交流的空间

如果你只是想看怎么写一个真实可用的学校配置，优先参考：

- `学校配置_profiles/jxust.py`
- `学校配置_profiles/example_drcom.py`
- `学校配置_profiles/example_srun.py`
- `学校配置_profiles/example_gportal.py`

如果你所在学校不在公开配置里，可以：

- 先运行 Collector 采集页面
- 再参考示例自己补 Profile
- 或联系作者交流已适配经验与定制适配支持

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
│   └── example_gportal.py
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

如果你走的是**源码运行路线**，通常还需要准备 Playwright 浏览器运行时：

```bash
python -m playwright install chromium
```

如果你走的是**Windows Edge 交付路线**，重点是：

- 构建机安装 `playwright`
- 目标机器已安装 Microsoft Edge
- 运行时优先由 Playwright 调用系统 Edge，而不是优先使用 Playwright 自带 Chromium

---

## 2. 两种使用方式

### 方式 A：源码运行
适合：
- 你自己调试
- 你需要更通用的运行方式
- 你可能在 Linux 或其他非纯 Windows 交付环境中研究页面

推荐准备：
- Python 3.x
- `playwright`
- 需要时安装 Playwright 浏览器运行时
- `pywifi`（如果你要自动连 Wi-Fi）

示例：

```bash
cp examples/.env.example .env
# 然后按需修改 PROFILE_MODULE / CAMPUS_USERNAME / CAMPUS_PASSWORD
```

Linux / macOS shell 示例：

```bash
export PROFILE_MODULE=学校配置_profiles.example_drcom
export CAMPUS_USERNAME=your-campus-account
export CAMPUS_PASSWORD=your-campus-password
export RUN_ONCE=1
python examples/run_with_env.py
```

### 方式 B：Windows 交付 / 打包
适合：
- 面向客户交付
- 希望最终是单文件 exe
- 优先调用客户电脑已有的 Edge

通常需要：
- Python 3.x（构建机上）
- `playwright`
- `pyinstaller`
- Windows + Edge

构建 Collector 的示例命令：

```powershell
scripts\build_collector.bat
```

> 关键点：当前项目依赖的是 **Playwright 运行时能力**。  
> 在 Windows 交付路线里，主链路通常是 **用 Playwright 的包驱动系统 Edge**；并不是优先让客户直接使用 Playwright 自带 Chromium。

> 公开仓当前重点是保留代码与方法论，没有强行重构成标准 `pip install` 包结构。

---

## 3. 使用示例入口

Windows PowerShell 示例：

```powershell
$env:PROFILE_MODULE="学校配置_profiles.example_drcom"
$env:CAMPUS_USERNAME="your-campus-account"
$env:CAMPUS_PASSWORD="your-campus-password"
$env:RUN_ONCE="1"
python examples\run_with_env.py
```

Windows CMD 示例：

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

## 4. 如果示例 Profile 不适合你的学校

不要先急着改核心逻辑，优先做这两件事：

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
- 需要兼顾“源码运行调试”和“Windows 打包交付”两条路线

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

## 项目定位建议

如果你打算基于这个项目二次开发，推荐把它理解成：

**一个“配置驱动的浏览器自动化状态机 + 失败取证系统 + 新站点采集工具”。**

这样理解它，会比把它当作“万能校园网脚本”更准确。
