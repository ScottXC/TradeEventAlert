# Trade Event Alert

<details open>
<summary>English</summary>

## Overview

Trade Event Alert is a Windows desktop app for monitoring selected X accounts, converting posts into market event alerts, and opening configurable trading or watchlist links for related tickers.

The app does not place orders automatically. It is a news, event alert, and research tool. It is not investment advice.

## Main Features

- Reads recent posts from configured X accounts through the official X API and your Bearer Token.
- Separates newly captured posts from posts that were already published during the last 24 hours.
- Provides paste analysis for copied public text without consuming X API credits.
- Stores settings, seen posts, alerts, favorites, and trash locally under `%APPDATA%\TradeEventAlert`.
- Supports local rule-based analysis and optional AI semantic analysis.
- Supports OpenAI Responses, OpenAI-compatible Chat Completions, xAI Grok, DeepSeek, Moonshot/Kimi, OpenRouter, and Google Gemini.
- Supports interface languages: English, Chinese, Spanish, Japanese, and Korean.
- Makes AI analysis output follow the selected language when AI analysis is enabled.
- Shows event category, severity, confidence, related tickers, direction, asset class, and reasons.
- Provides favorites, trash, restore, permanent delete, and workflow tracking.
- Opens configurable links such as TradingView, Robinhood, or broker pages by replacing `{symbol}` with the selected ticker.
- Adds a safe trade ticket page with broker profiles for Alpaca Paper Trading, Interactive Brokers, Schwab, and Tradier.
- Only Alpaca Paper Trading can submit through the API in this build. Other brokers generate an order ticket and open the broker confirmation page.
- Real orders are not sent automatically from AI analysis. Users must review the ticket and confirm manually.

## Run From Source

```powershell
.\run_dev.ps1
```

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

## Privacy

The installer only packages the application executable and install scripts. It does not package `%APPDATA%\TradeEventAlert`, `config.json`, `alerts.sqlite3`, API keys, Bearer Tokens, or user data.

</details>

<details>
<summary>中文</summary>

## 简介

Trade Event Alert 是一个 Windows 桌面软件，用于监控指定 X 账号，把帖子转换为市场事件预警，并为相关股票代码打开可配置的交易或看盘链接。

软件不会自动下单。它只用于新闻、事件预警和研究辅助，不构成投资建议。

## 主要功能

- 通过 X 官方 API 和你的 Bearer Token 读取已配置账号的近期帖子。
- 区分本次运行后新抓取的内容和过去 24 小时内已经发布的历史内容。
- 提供粘贴分析功能，可手动分析复制的公开文本，不消耗 X API credits。
- 在 `%APPDATA%\TradeEventAlert` 本地保存设置、已读取帖子、预警、收藏夹和回收站数据。
- 支持本地规则分析，也支持可选 AI 语义分析。
- 支持 OpenAI Responses、OpenAI 兼容 Chat Completions、xAI Grok、DeepSeek、月之暗面 Kimi、OpenRouter 和 Google Gemini。
- 支持界面语言：中文、英文、西班牙文、日文、韩文。
- 启用 AI 分析时，AI 输出语言会跟随已选择的界面语言。
- 显示事件类别、级别、置信度、相关代码、方向、资产类别和理由。
- 提供收藏夹、回收站、恢复、永久删除和工作流耗时跟踪。
- 支持配置交易或看盘链接模板，用选中代码替换 `{symbol}` 后打开页面。
- 新增安全交易票据页面，内置 Alpaca Paper Trading、Interactive Brokers、Schwab 和 Tradier 平台档案。
- 当前版本只有 Alpaca Paper Trading 会通过 API 提交模拟订单，其他平台会生成订单票据并打开券商确认页。
- AI 分析结果不会自动实盘下单，用户必须检查订单票据并手动确认。

## 从源码运行

```powershell
.\run_dev.ps1
```

## 打包 EXE

```powershell
.\build_exe.ps1
```

生成位置：

```text
.\dist\TradeEventAlert.exe
```

## 打包安装包

```powershell
.\build_installer.ps1
```

生成位置：

```text
.\installer_dist\TradeEventAlert-Setup.exe
```

## 隐私说明

安装包只包含软件主程序和安装脚本，不包含 `%APPDATA%\TradeEventAlert`、`config.json`、`alerts.sqlite3`、API Key、Bearer Token 或任何用户数据。

</details>

<details>
<summary>Español</summary>

## Descripción

Trade Event Alert es una aplicación de escritorio para Windows que supervisa cuentas seleccionadas de X, convierte publicaciones en alertas de eventos de mercado y abre enlaces configurables de trading o seguimiento para los símbolos relacionados.

La aplicación no envía órdenes automáticamente. Es una herramienta de noticias, alertas e investigación. No es asesoramiento financiero.

## Funciones principales

- Lee publicaciones recientes de cuentas configuradas de X mediante la API oficial y tu Bearer Token.
- Separa publicaciones nuevas de contenido publicado durante las últimas 24 horas.
- Permite analizar texto pegado sin consumir créditos de la API de X.
- Guarda configuración, publicaciones vistas, alertas, favoritos y papelera localmente en `%APPDATA%\TradeEventAlert`.
- Incluye análisis local por reglas y análisis semántico opcional con IA.
- Soporta OpenAI Responses, Chat Completions compatibles con OpenAI, xAI Grok, DeepSeek, Moonshot/Kimi, OpenRouter y Google Gemini.
- Soporta interfaz en español, inglés, chino, japonés y coreano.
- Cuando la IA está activada, la salida del análisis sigue el idioma seleccionado.
- Añade una página segura de boleta de orden con perfiles para Alpaca Paper Trading, Interactive Brokers, Schwab y Tradier.
- En esta versión solo Alpaca Paper Trading puede enviar órdenes por API. Otros brókers generan una boleta y abren la página de confirmación.
- La IA no envía órdenes reales automáticamente. El usuario debe revisar y confirmar la boleta.

## Ejecutar desde el código fuente

```powershell
.\run_dev.ps1
```

## Crear EXE

```powershell
.\build_exe.ps1
```

## Crear instalador

```powershell
.\build_installer.ps1
```

</details>

<details>
<summary>日本語</summary>

## 概要

Trade Event Alert は Windows デスクトップアプリです。指定した X アカウントを監視し、投稿を市場イベント警報に変換し、関連銘柄の取引または監視リンクを開きます。

このアプリは自動注文を行いません。ニュース、イベント警報、調査補助のためのツールであり、投資助言ではありません。

## 主な機能

- X 公式 API と Bearer Token を使って設定済みアカウントの最近の投稿を取得します。
- 新規取得投稿と過去 24 時間内に既に公開されていた内容を分けて表示します。
- 貼り付けた公開テキストを分析でき、X API credits を消費しません。
- 設定、既読投稿、警報、お気に入り、ごみ箱を `%APPDATA%\TradeEventAlert` にローカル保存します。
- ローカルルール分析と任意の AI 意味分析に対応します。
- OpenAI Responses、OpenAI 互換 Chat Completions、xAI Grok、DeepSeek、Moonshot/Kimi、OpenRouter、Google Gemini に対応します。
- 日本語、英語、中国語、スペイン語、韓国語の画面表示に対応します。
- AI 分析を有効にした場合、分析結果の言語は選択した表示言語に従います。
- Alpaca Paper Trading、Interactive Brokers、Schwab、Tradier のプロファイルを備えた安全な注文チケット画面を追加しました。
- このビルドで API 送信できるのは Alpaca Paper Trading のみです。他のブローカーは注文チケットを作成し、確認ページを開きます。
- AI 分析結果から実注文が自動送信されることはありません。ユーザーがチケットを確認して手動で承認します。

## ソースから実行

```powershell
.\run_dev.ps1
```

## EXE 作成

```powershell
.\build_exe.ps1
```

## インストーラー作成

```powershell
.\build_installer.ps1
```

</details>

<details>
<summary>한국어</summary>

## 개요

Trade Event Alert는 Windows 데스크톱 앱입니다. 선택한 X 계정을 모니터링하고 게시물을 시장 이벤트 알림으로 변환하며 관련 종목의 거래 또는 관심 목록 링크를 엽니다.

이 앱은 자동 주문을 실행하지 않습니다. 뉴스, 이벤트 알림, 리서치 보조 도구이며 투자 조언이 아닙니다.

## 주요 기능

- X 공식 API와 Bearer Token으로 설정된 계정의 최근 게시물을 읽습니다.
- 새로 수집된 게시물과 최근 24시간 내에 이미 게시된 내용을 분리해 표시합니다.
- 붙여넣은 공개 텍스트를 분석할 수 있으며 X API credits를 사용하지 않습니다.
- 설정, 확인한 게시물, 알림, 즐겨찾기, 휴지통 데이터를 `%APPDATA%\TradeEventAlert`에 로컬 저장합니다.
- 로컬 규칙 분석과 선택적 AI 의미 분석을 지원합니다.
- OpenAI Responses, OpenAI 호환 Chat Completions, xAI Grok, DeepSeek, Moonshot/Kimi, OpenRouter, Google Gemini를 지원합니다.
- 한국어, 영어, 중국어, 스페인어, 일본어 인터페이스를 지원합니다.
- AI 분석을 켜면 분석 결과 언어가 선택한 인터페이스 언어를 따릅니다.
- Alpaca Paper Trading, Interactive Brokers, Schwab, Tradier 프로필을 포함한 안전한 주문 티켓 페이지를 추가했습니다.
- 이 빌드에서는 Alpaca Paper Trading만 API로 모의 주문을 제출할 수 있습니다. 다른 브로커는 주문 티켓을 만들고 확인 페이지를 엽니다.
- AI 분석 결과가 실거래 주문으로 자동 제출되지 않습니다. 사용자가 티켓을 검토하고 직접 확인해야 합니다.

## 소스에서 실행

```powershell
.\run_dev.ps1
```

## EXE 빌드

```powershell
.\build_exe.ps1
```

## 설치 프로그램 빌드

```powershell
.\build_installer.ps1
```

</details>
