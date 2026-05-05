# Architecture

## 总体结构

项目拆成三层核心能力和一层辅助能力：

### 1. `核心_core/`
负责统一执行流：

- 网络在线探测
- Portal 可达性等待
- 浏览器启动
- 登录页打开
- 表单元素等待
- 输入账号密码
- 运营商选择
- 验证码检测
- 登录提交
- 登录后探针复核
- 失败诊断导出

### 2. `学校配置_profiles/`
负责描述每个学校的差异：

- 登录地址候选
- 登录表单 selector
- 运营商逻辑
- 浏览器偏好
- Wi-Fi 策略
- 时间参数

### 3. `examples/`
负责演示如何安全地把账号密码注入运行流程，而不是把真实凭证写死进公开仓。

### 4. `工具_tools/采集器_collector/`
负责在新学校未适配时收集 Portal 页面现场，帮助后续写 Profile。

---

## 浏览器运行模型：历史上有两条路

这个项目不是一直只有一种浏览器运行方式，而是经历过两条路线并长期共存：

### 路线 A：Playwright 自带浏览器 / 源码运行路线
特征：

- 更偏早期方案
- 更容易在 Linux 等环境里直接源码运行
- 更适合开发、调试、快速实验
- 一般要求开发者自己准备 Python 环境与 Playwright 运行时

### 路线 B：系统 Edge 优先 / Windows 交付路线
特征：

- 更偏后期稳定交付方案
- 通过 Playwright 的 Python 包调用系统已安装的 Edge
- 更适合后续用 PyInstaller 打包成单文件 exe 给客户直接运行
- 降低客户侧环境准备成本

在当前公开保留的代码里，这个偏好体现在：

- `核心_core/browser.py`
- `工具_tools/采集器_collector/collector.py`

其中优先会尝试：

- `playwright.chromium.launch(channel="msedge", ...)`

失败后，部分模式才会 fallback 到 Playwright Chromium。

因此更准确的理解是：

**项目依赖 Playwright 的自动化能力，但运行时既可以走“自带浏览器源码路线”，也可以走“系统 Edge 交付路线”。**

---

## 执行流

主入口在：

- `核心_core.run_profile()`
- `核心_core.run_login_once()`

典型执行顺序：

1. `check_online()` 探测当前是否已联网
2. 若离线，则 `ensure_wifi_connected()` 尝试连目标 Wi-Fi（若启用）
3. `wait_portal_reachable()` 等待认证页可达
4. `launch_browser()` 启动 Edge 或 Chromium
5. `open_portal()` 依次尝试 Portal URL 候选
6. `wait_for_login_form()` 等待用户名输入框出现
7. `set_input()` 输入用户名/密码
8. `choose_operator()` 选择运营商（若需要）
9. `captcha_detected()` 检查验证码
10. `submit_login()` 提交登录
11. `check_online_detailed()` 再次探测真实联网状态
12. 失败则通过 `DiagExporter` 导出证据包

---

## 为什么需要多种输入与提交策略

校园网 Portal 页面往往比较脏，常见问题包括：

- 输入框是隐藏控件 + 可见假输入框
- Playwright click 成功，但页面 JS 没有真正触发登录逻辑
- 登录按钮需要通过 `onclick`、脚本函数或键盘焦点触发
- 运营商选项在收起面板里，或者需要调用页面脚本才算选中
- 页面在 iframe 内

因此核心代码里引入多套兜底策略，而不是只依赖一种标准化交互方式。

---

## Probe 与成功判定

这个项目不把“页面跳到 success.jsp”简单等同于成功。

更可靠的标准是：

- 登录流程跑完后
- 再执行联网探针
- 只有探针结果表明已真实联网，才认为成功

这是因为很多学校 Portal 会出现：

- 页面看起来成功
- 实际仍未获得外网访问能力

---

## Diag 与 Collector 的区别

### Diag
Diag 是**登录失败后的自动证据导出**：

- 由主登录流程触发
- 自动保存流程日志、探针结果、页面快照等

### Collector
Collector 是**适配前/排障时的主动采集工具**：

- 用户手动操作浏览器
- 工具记录页面结构、URL、事件轨迹
- 更适合分析陌生学校页面

可以简单理解为：

- `Diag` = 失败复盘
- `Collector` = 新页面建模
