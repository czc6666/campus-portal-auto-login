# Collector

Collector 用于采集一个陌生校园网 Portal 页面的结构信息，帮助后续编写 Profile。

源码位置：

- `工具_tools/采集器_collector/collector.py`

构建脚本：

- `scripts/build_collector.bat`

---

## Collector 做什么

运行后，它会：

- 打开浏览器（优先 Edge）
- 记录主页面导航链
- 保存主页面 DOM
- 保存 frame DOM
- 自动猜测用户名/密码/登录按钮/运营商/验证码 selector
- 记录 click / input / change / submit 事件
- 输出 zip 采集包

---

## 典型使用方式

1. 运行 Collector
2. 按平时习惯打开学校认证页并尝试登录
3. 操作完成后关闭浏览器
4. Collector 自动打包结果
5. 分析：
   - `urls.json`
   - `elements_guess.json`
   - `timeline.jsonl`
   - `dom_main.html`
   - `frames/`

---

## 输出内容

典型结果包含：

- `meta.json`
- `urls.json`
- `timeline.jsonl`
- `dom_main.html`
- `frames/`
- `snapshots/`
- `elements_guess.json`
- `net_state.json`
- `collector.log`
- `collector_error.json`（若异常）

---

## 注意事项

- 不要把包含真实账号、真实 Portal 参数的采集包直接公开上传
- 某些学校页面会把会话参数写进 URL
- 如果采集时用户手动反复切页面，结果会更噪
- Collector 是辅助建模工具，不等于自动生成可用 Profile
