# Trade Event Alert

Windows desktop MVP for monitoring selected X accounts, turning posts into market event alerts, and opening configurable trade/watch links for related tickers.

## What it does

- Uses the official X API with your Bearer Token to read recent posts from configured accounts.
- Provides a paste-analysis tab for manually analyzing copied X, Truth Social, or news text without using X API credits.
- Stores seen posts and alerts in a local SQLite database under `%APPDATA%\TradeEventAlert`.
- Runs a local rule engine for event classification and ticker direction.
- Optionally calls an AI provider for structured semantic analysis when you enable `use_gpt`.
- Supports OpenAI Responses, OpenAI-compatible Chat Completions, xAI Grok, DeepSeek, Moonshot/Kimi, OpenRouter, and Gemini REST.
- Shows event category, severity, confidence, suggested asset classes, ticker direction, and reasons.
- Supports deleting selected alerts or bulk deleting alerts by account/source, category, severity, or manual-paste source.
- Shows a bottom status bar with click feedback, operation results, and next-step hints.
- Provides hover tooltips for primary buttons and clickable tables.
- Provides an AI selection drawer in Settings so users pick a provider instead of typing provider names.
- Validates required settings before saving; when AI analysis is enabled, API key, model, and Base URL are required.
- Opens AI semantic re-analysis in a separate window and runs slow AI calls in the background.
- Separates captured content into `新发布内容` and `过去一天` views.
- Adds `收藏夹`, `回收站`, and `工作流` views. Deleted alerts go to the recycle bin first and can be restored or permanently deleted.
- Opens a configurable link template such as TradingView, Robinhood, or your broker page with `{symbol}` replaced by the selected ticker.

It does not place orders automatically. It is a news/event alert and research tool, not investment advice.

## Run from source

```powershell
.\run_dev.ps1
```

The first launch creates:

```text
%APPDATA%\TradeEventAlert\config.json
%APPDATA%\TradeEventAlert\alerts.sqlite3
```

You can also edit settings inside the app.

## Paste analysis without X API credits

Open the `粘贴分析` tab, paste the post or news text, optionally enter an account/source and original URL, then click `分析并加入预警`.

This path does not call the X API and does not consume X credits. It still uses the same event classification, ticker-direction logic, and trade/watch links as automatic monitoring.

## Delete alerts

In the `实时预警` tab:

- Use `删除选中` to remove the currently selected alert rows.
- Use `自定义删除` to remove alerts matching account/source text, category text, maximum severity, or only manually pasted alerts.

Deletion only removes local alert history from `%APPDATA%\TradeEventAlert\alerts.sqlite3`; it does not change API keys or app settings.

## Build EXE

```powershell
.\build_exe.ps1
```

The executable is created at:

```text
.\dist\TradeEventAlert.exe
```

## Build Installer

```powershell
.\build_installer.ps1
```

The installer is created at:

```text
.\installer_dist\TradeEventAlert-Setup.exe
```

The installer is per-user and installs to:

```text
%LOCALAPPDATA%\Programs\TradeEventAlert
```

It creates Start Menu and desktop shortcuts plus a Windows uninstall entry. It only packages `TradeEventAlert.exe` and install/uninstall scripts. It does not package `%APPDATA%\TradeEventAlert`, `alerts.sqlite3`, `config.json`, API keys, Bearer Tokens, or any user data.

## Required accounts and keys

X data access uses the official X API. Create an X Developer App and copy the Bearer Token into the Settings tab. X API access and cost depend on your developer account permissions and the current X pay-per-use rules.

AI semantic analysis is optional. If you enable GPT/AI analysis, choose an AI provider, paste that provider's API key, and set the model/Base URL. Without an AI key, the app still runs with local keyword/event rules. Slow models can exceed the request timeout, so the Settings tab includes `AI 超时秒数`; the default is 90 seconds. Moonshot/Kimi automatically uses at least 180 seconds because Kimi models can respond more slowly.

Supported AI presets:

```text
OpenAI Responses        https://api.openai.com/v1
OpenAI-compatible       https://api.openai.com/v1
xAI Grok                https://api.x.ai/v1
DeepSeek                https://api.deepseek.com
Moonshot/Kimi           https://api.moonshot.cn/v1
OpenRouter              https://openrouter.ai/api/v1
Google Gemini           https://generativelanguage.googleapis.com/v1beta
```

In the Settings tab, click `选择 AI` to open the provider drawer, choose a provider card, then save settings. Required fields are validated before saving. In the alert detail panel, use `语义分析重生成` to choose a provider/model and regenerate analysis for the selected alert.

The app separates alerts by capture context:

- `新发布内容`: posts published after monitoring/one-time fetch starts.
- `过去一天`: posts from the last 24 hours that were already published before the current fetch run.
- `收藏夹`: manually collected alerts for later review.
- `回收站`: deleted alerts; restore them or permanently delete them.
- `工作流`: current and recent operations with elapsed time.

## Trade link examples

Use any URL that accepts a symbol in the path or query:

```text
https://www.tradingview.com/symbols/{symbol}/
https://robinhood.com/stocks/{symbol}
https://www.interactivebrokers.com/en/trading/products-stocks.php?symbol={symbol}
```

When you click "打开交易/看盘链接", the app opens the selected ticker with that template. You still confirm any trade manually in your broker.

---

# Trade Event Alert 中文说明

这是一个 Windows 桌面版 MVP，用于监控指定 X 账号或手动粘贴公开文本，把帖子/新闻转成市场事件预警，并为相关股票、ETF 或资产类别生成研究辅助判断。

本软件不会自动下单，不构成投资建议。它只做新闻/事件预警、文本分析、股票代码方向提示和交易/看盘链接跳转。

## 主要功能

- 使用 X 官方 API Bearer Token 读取你配置的 X 账号近期帖子。
- 支持 `粘贴分析`，可以手动粘贴 X、Truth Social、新闻标题或其他公开文本，不消耗 X API credits。
- 本地 SQLite 保存已读取帖子和预警历史，位置在 `%APPDATA%\TradeEventAlert`。
- 使用本地规则引擎识别事件类别和股票/ETF 利好利空方向。
- 可选启用 AI 语义分析；没有 AI API Key 时仍可用本地规则运行。
- 支持 OpenAI Responses、OpenAI 兼容 Chat Completions、xAI Grok、DeepSeek、月之暗面 Kimi、OpenRouter 和 Gemini REST。
- 显示事件类别、预警级别、置信度、建议交易类别、股票/ETF 代码、方向和理由。
- 支持删除选中预警，也支持按账号/来源、类别、级别、是否粘贴来源来自定义批量删除。
- 底部状态栏会显示点击反馈、操作结果和下一步提示。
- 主要按钮和可点击表格支持悬停说明，鼠标停留一会儿会看到简短解释。
- 设置页提供 `选择 AI` 抽屉，用户点击卡片选择 AI 服务商，不需要手动输入服务商名称。
- 保存设置前会校验必填项；启用 AI 时，AI API Key、模型和 Base URL 必须填写。
- AI 语义重分析在单独窗口中进行，并且后台运行，慢模型不会卡住界面。
- 抓取内容分成 `新发布内容` 和 `过去一天` 两个窗口。
- 新增 `收藏夹`、`回收站`、`工作流`。删除内容先进回收站，可恢复；回收站支持永久删除。
- 支持配置交易/看盘链接模板，例如 TradingView、Robinhood、IBKR 等。

## 直接运行 EXE

已打包好的程序在：

```text
.\dist\TradeEventAlert.exe
```

第一次启动后会自动创建：

```text
%APPDATA%\TradeEventAlert\config.json
%APPDATA%\TradeEventAlert\alerts.sqlite3
```

你也可以在软件的 `设置` 页修改配置。

## 从源码运行

```powershell
.\run_dev.ps1
```

## 设置 X API

如果你要自动抓取 X 账号，需要：

1. 打开 X Developer Console。
2. 创建或进入你的 App。
3. 在 `Keys & Tokens` 里生成 `Bearer Token`。
4. 粘贴到软件 `设置 -> X Bearer Token`。
5. 在 `监控账号` 中填入账号名，例如：

```text
realDonaldTrump
```

注意：X API 目前是 pay-per-use。如果日志出现 `HTTP 402 CreditsDepleted`，表示你的 X 开发者账号没有可用 credits，需要去 X Developer Console 的 `Billing -> Credits` 购买或分配 credits。

## 不买 X credits 的用法

打开 `粘贴分析` 页：

1. 填账号/来源，例如 `TruthSocial`、`realDonaldTrump` 或 `manual`。
2. 原帖链接可填可不填。
3. 粘贴帖子正文或新闻文本。
4. 点击 `分析并加入预警`。

这个功能不会调用 X API，因此不会消耗 X credits。分析结果会自动加入 `实时预警` 列表。

## AI 语义分析设置

AI API Key 是可选的。

- 不填 AI API Key：使用本地规则分析。
- 填 AI API Key 并勾选 `启用 GPT 语义分析`：使用所选 AI 提供商生成更结构化的事件分析。
- 在设置页点击 `选择 AI` 打开抽屉，选择服务商卡片后会自动填入推荐模型和 Base URL。
- 如果勾选 `启用 GPT 语义分析`，保存设置时会要求填写 AI API Key、AI 模型和 AI Base URL。
- `AI 超时秒数` 默认是 90 秒；月之暗面 Kimi 会自动使用至少 180 秒，最大 300 秒。如果仍然超时，可以把设置页里的超时调到 240-300 秒，或换更快/更小的模型。
- 在 `实时预警` 的右侧详情区，可以在 `语义分析重生成` 中选择服务商和模型，对当前选中的预警重新生成分析。

## 内容整理

- `新发布内容`：只收录本次运行抓取之后发布的新内容。
- `过去一天`：收录过去 24 小时内的历史内容。
- `收藏夹`：对选中内容点击 `收藏选中` 后可在这里集中整理。
- `回收站`：删除内容不会立即消失，可恢复；点击 `永久删除` 后无法恢复。
- `工作流`：显示当前正在进行的抓取、分析等操作，以及每项耗时。

内置预设：

```text
OpenAI Responses        https://api.openai.com/v1                 gpt-4o-mini
OpenAI 兼容             https://api.openai.com/v1                 gpt-4o-mini
xAI Grok                https://api.x.ai/v1                       grok-4.20-reasoning
DeepSeek                https://api.deepseek.com                   deepseek-v4-flash
月之暗面 Kimi           https://api.moonshot.cn/v1                 kimi-k2.6
OpenRouter              https://openrouter.ai/api/v1               openai/gpt-4o-mini
Google Gemini           https://generativelanguage.googleapis.com/v1beta  gemini-2.5-flash
```

如果模型报错或没有权限，先确认你的 API Key、账户余额、模型名称和 Base URL 是否匹配当前服务商。

## 删除预警

在 `实时预警` 页：

- `删除选中`：删除当前选中的预警。
- `自定义删除`：按账号/来源、类别、最高级别、是否只删除粘贴分析来源进行批量删除。

删除只影响本地预警历史，不会删除 API Key、设置或远程数据。

## 打包 EXE

```powershell
.\build_exe.ps1
```

生成文件：

```text
.\dist\TradeEventAlert.exe
```

## 生成安装包

```powershell
.\build_installer.ps1
```

安装包输出位置：

```text
.\installer_dist\TradeEventAlert-Setup.exe
```

安装包是单用户安装，不需要管理员权限，默认安装到：

```text
%LOCALAPPDATA%\Programs\TradeEventAlert
```

安装后会创建桌面快捷方式、开始菜单快捷方式和 Windows 卸载入口。安装包只包含主程序 `TradeEventAlert.exe` 和安装/卸载脚本，不会打包 `%APPDATA%\TradeEventAlert` 下的 `config.json`、`alerts.sqlite3`、X Bearer Token、AI API Key 或任何用户个人数据。

## 交易/看盘链接模板

模板必须包含 `{symbol}`。例如：

```text
https://www.tradingview.com/symbols/{symbol}/
https://robinhood.com/stocks/{symbol}
https://www.interactivebrokers.com/en/trading/products-stocks.php?symbol={symbol}
```

点击 `打开交易/看盘链接` 时，软件会把 `{symbol}` 替换成当前选中的股票或 ETF 代码。你仍然需要在券商页面手动确认交易。

## 风险提示

本软件输出的 `bullish`、`bearish`、`mixed`、`neutral` 只是新闻事件研究标签，不是买卖建议。真实交易前需要结合价格走势、成交量、更多新闻源、财报、宏观环境和个人风险承受能力。

## 最新交互优化

- `过去一天` 页面现在有独立的摘要和股票/ETF 判断区，点击历史内容不会跳到 `新发布内容` 页面。
- `过去一天` 页面右侧已加入 `AI 分析窗口`、`打开原帖`、`打开交易/看盘链接`，可直接对历史内容重新生成中文 AI 分析。
- AI 提示词要求面向用户阅读的字段使用简体中文，包括标题、摘要和股票理由。
- X 抓取现在保留全部帖子内容；原本会被“排除回复/转发”筛掉的内容会用 `[原筛选: 回复/转发]` 标记并以浅黄色行区分。
- 详情分析栏删除了风险提示展示，并在顶部增加 `AI 分析结果`、`本地规则分析`、`原筛选内容` 等标题区分。
- `立即轮询` 会重新添加已经从活动列表移除、只留在回收站或无 active 预警的同帖内容；后台自动监控仍保持普通去重。
- 刷新提示里的“当前活动内容显示”只统计新发布和过去一天的 active 内容，不把回收站内容算进去。
- AI 分析窗口会保持打开，并显示“AI 正在运行”和实时耗时，完成或失败后会在窗口内更新状态。
- 抓取过去一天历史内容时默认先用本地快速规则入库，避免 AI 模型拖慢首次抓取；需要深度分析时，可以对具体内容再打开 AI 分析窗口重新生成。
- 抓取过程会批量刷新界面，不再每抓到一条历史内容就刷新一次，过去内容加载更快。
