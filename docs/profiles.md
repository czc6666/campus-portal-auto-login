# Profiles

`SchoolProfile` 是这个项目最重要的扩展点。

你不应该优先修改 `核心_core/`，而应该优先新增或调整一个 Profile。

---

## Profile 结构

定义见：

- `学校配置_profiles/types.py`

主要字段包括：

### `portal`
Portal 地址与可达性检查：

- `url_candidates`
- `reachable_host`
- `reachable_port`
- `wait_sec`
- `goto_retries`

### `selectors`
登录页 selector 集合：

- `username`
- `password`
- `login_button`
- `operator`
- `captcha`

每一项都是列表，表示可以按顺序尝试多个候选 selector。

### `input`
输入策略：

- `fill_first`
- `js_first`
- `keyboard`

#### 什么时候用 `js_first`
当页面存在以下情况时优先考虑：

- 密码框是隐藏控件
- 直接 `fill()` 失败
- 需要触发 `input/change` 事件

### `submit`
提交策略：

- `click_then_enter`
- `keyboard_tab_enter`

#### 什么时候用 `keyboard_tab_enter`
适合：

- 页面按钮可见但 click 不稳定
- 登录按钮实际依赖焦点与键盘触发
- 某些 Drcom 风格页面

### `browser`
浏览器策略：

- `edge_only`
- `edge_then_chromium`
- `chromium_only`

### `timing`
时间参数：

- `check_interval_sec`
- `login_wait_sec`
- `retry_cooldown_sec`
- `probe_timeout_sec`
- `action_timeout_ms`
- `navigation_timeout_ms`

### `probe`
联网探针策略。

### `wifi`
Wi-Fi 自动连接策略：

- `none`
- `pywifi`
- `netsh`

### `frame`
是否需要在 frame 里寻找登录表单。

### `operator_value`
某些学校需要选择运营商时使用。

---

## 适配建议顺序

新增学校时，建议按以下顺序处理：

1. 先用 Collector 获取页面信息
2. 再写一个新 Profile
3. 先改 selector，不要先改 core
4. 先用已有 input / submit 策略组合尝试
5. 只有现有策略完全不够时，才考虑补 core

---

## 示例文件

公开仓提供了三种脱敏示例：

- `学校配置_profiles/example_drcom.py`
- `学校配置_profiles/example_srun.py`
- `学校配置_profiles/example_gportal.py`

它们不是为了保证直接可用，而是为了展示：

- 典型字段怎么填
- 不同 Portal 风格怎么建模
