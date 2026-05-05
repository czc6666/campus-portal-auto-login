# Troubleshooting

## 1. 页面显示成功，但实际上没网

不要只看页面跳转结果。

优先检查：

- 登录后探针是否真实在线
- 是否误用了默认运营商
- 是否进入了“假成功页”

原则：**以探针结果为准，不以成功页面文案为准。**

---

## 2. 看起来没点登录按钮

不要先凭视频主观判断。

优先看：

- `attempts.json`
- `events.jsonl`
- `final.html`

如果 `submit` 已成功，说明程序并不一定是“没点登录”，也可能是：

- portal 参数过期
- 运营商未正确选中
- 登录状态生效有延迟

---

## 3. 密码框怎么都填不进去

常见原因：

- 密码框是隐藏控件
- 页面上看到的是占位用假输入框
- 需要触发 JS 事件而不是单纯 DOM value 修改

优先尝试：

- `input.mode = js_first`
- 增加 password selector 候选

---

## 4. Portal 直接打开提示设备未注册

常见原因：

- 目标学校需要使用当前设备实时重定向出的动态 Portal URL
- 不能长期写死带设备参数的 URL

建议：

- 让探针先捕获当前机重定向地址
- Profile 中保留基础候选地址，不长期固定历史参数 URL

---

## 5. 页面结构变化后 selector 全失效

处理顺序：

1. 先跑 Collector
2. 对比 `elements_guess.json`
3. 再调整 Profile selector
4. 最后才考虑改 core

---

## 6. 什么时候应该改 core

只有以下情况才建议改：

- 当前所有 input / submit / frame / operator 策略都不足以表达目标页面
- 你已经确认问题不是 selector、URL、时序或 Profile 配置错误
- 你有办法重新验证改动结果

如果你现在没有实网验证条件，就更应该：

**先保守，优先改 Profile，不要动核心逻辑。**
