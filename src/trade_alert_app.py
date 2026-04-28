import json
import os
import queue
import sqlite3
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, BooleanVar, StringVar, Text, Tk, Toplevel, messagebox
from tkinter import ttk


APP_NAME = "TradeEventAlert"
APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_PATH = APP_DIR / "config.json"
DB_PATH = APP_DIR / "alerts.sqlite3"


COLORS = {
    "bg": "#f5f7fb",
    "panel": "#ffffff",
    "panel_alt": "#f9fafc",
    "border": "#d9dfeb",
    "text": "#172033",
    "muted": "#5f6b7a",
    "accent": "#2563eb",
    "accent_dark": "#1d4ed8",
    "danger": "#dc2626",
    "warning_bg": "#fff7ed",
    "warning_text": "#8a4b0b",
    "success_bg": "#ecfdf5",
    "danger_bg": "#fef2f2",
    "info_bg": "#eff6ff",
}


DEFAULT_CONFIG = {
    "x_bearer_token": "",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "ai_provider": "openai_responses",
    "ai_api_key": "",
    "ai_model": "gpt-4o-mini",
    "ai_base_url": "https://api.openai.com/v1",
    "ai_timeout_seconds": 90,
    "accounts": ["realDonaldTrump"],
    "poll_seconds": 90,
    "max_posts_per_account": 5,
    "use_gpt": False,
    "exclude_replies": True,
    "exclude_retweets": True,
    "trade_link_template": "https://www.tradingview.com/symbols/{symbol}/",
}


AI_PROVIDER_PRESETS = {
    "openai_responses": {
        "label": "OpenAI Responses",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-5.5"],
        "temperature": 0.2,
        "kind": "responses",
    },
    "openai_compatible": {
        "label": "OpenAI 兼容",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
        "temperature": 0.2,
        "kind": "chat_completions",
    },
    "xai": {
        "label": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "model": "grok-4.20-reasoning",
        "models": ["grok-4.20-reasoning", "grok-4", "grok-3"],
        "temperature": 0.2,
        "kind": "chat_completions",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"],
        "temperature": 0.2,
        "kind": "chat_completions",
    },
    "moonshot": {
        "label": "月之暗面 Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "kimi-k2.6",
        "models": ["kimi-k2.6", "kimi-k2.5", "kimi-k2", "kimi-k2-thinking", "moonshot-v1"],
        "temperature": 1,
        "min_timeout_seconds": 180,
        "kind": "chat_completions",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "models": ["openai/gpt-4o-mini", "openai/gpt-4.1-mini", "anthropic/claude-sonnet-4.5", "google/gemini-2.5-flash"],
        "temperature": 0.2,
        "kind": "chat_completions",
    },
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-2.5-flash",
        "models": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-2.0-flash"],
        "temperature": 0.2,
        "kind": "gemini",
    },
}

AI_PROVIDER_LABELS = {key: value["label"] for key, value in AI_PROVIDER_PRESETS.items()}
AI_LABEL_TO_PROVIDER = {value: key for key, value in AI_PROVIDER_LABELS.items()}


EVENT_RULES = [
    {
        "category": "tariff_trade",
        "keywords": [
            "tariff",
            "tariffs",
            "trade war",
            "import tax",
            "china",
            "mexico",
            "canada",
            "eu",
            "european union",
            "reciprocal",
            "关税",
            "贸易战",
            "中国",
            "墨西哥",
            "加拿大",
            "欧盟",
        ],
        "asset_classes": ["equity_index", "china_adr", "fx", "safe_haven"],
        "tickers": [
            ("SPY", "bearish", "贸易摩擦通常压低风险偏好"),
            ("QQQ", "bearish", "成长股对政策冲击和估值变化更敏感"),
            ("FXI", "bearish", "中国相关资产受贸易冲突影响"),
            ("BABA", "bearish", "中国 ADR 对中美贸易消息敏感"),
            ("JD", "bearish", "中国消费/电商 ADR 对政策风险敏感"),
            ("GLD", "bullish", "避险需求可能上升"),
        ],
    },
    {
        "category": "fed_rates",
        "keywords": [
            "fed",
            "federal reserve",
            "powell",
            "rate cut",
            "rate hike",
            "interest rates",
            "inflation",
            "cpi",
            "美联储",
            "降息",
            "加息",
            "通胀",
        ],
        "asset_classes": ["equity_index", "bonds", "banks"],
        "tickers": [
            ("QQQ", "mixed", "利率路径取决于降息/通胀语境"),
            ("SPY", "mixed", "宏观利率信号需结合方向判断"),
            ("TLT", "mixed", "长债价格对利率预期敏感"),
            ("XLF", "mixed", "银行股受利差和信用风险共同影响"),
        ],
    },
    {
        "category": "energy_oil",
        "keywords": [
            "oil",
            "crude",
            "opec",
            "gasoline",
            "drill",
            "energy",
            "pipeline",
            "石油",
            "原油",
            "能源",
            "汽油",
        ],
        "asset_classes": ["energy", "commodity"],
        "tickers": [
            ("XLE", "bullish", "能源供给紧张或扩产政策会直接影响板块"),
            ("XOM", "bullish", "大型油气公司对油价和政策敏感"),
            ("CVX", "bullish", "大型油气公司对油价和政策敏感"),
            ("USO", "mixed", "原油方向取决于供给/需求语境"),
        ],
    },
    {
        "category": "war_geopolitics",
        "keywords": [
            "war",
            "missile",
            "iran",
            "russia",
            "ukraine",
            "israel",
            "ceasefire",
            "nato",
            "sanction",
            "战争",
            "导弹",
            "伊朗",
            "俄罗斯",
            "乌克兰",
            "以色列",
            "停火",
            "制裁",
        ],
        "asset_classes": ["defense", "safe_haven", "equity_index"],
        "tickers": [
            ("LMT", "bullish", "地缘冲突可能增加防务预期"),
            ("RTX", "bullish", "防务承包商对军费和冲突消息敏感"),
            ("NOC", "bullish", "防务承包商对军费和冲突消息敏感"),
            ("GLD", "bullish", "冲突升级常见避险需求"),
            ("SPY", "bearish", "冲突升级通常压低风险偏好"),
        ],
    },
    {
        "category": "semiconductors",
        "keywords": [
            "chip",
            "chips",
            "semiconductor",
            "ai chip",
            "nvidia",
            "export control",
            "tsmc",
            "芯片",
            "半导体",
            "英伟达",
            "出口管制",
        ],
        "asset_classes": ["semiconductor", "technology"],
        "tickers": [
            ("NVDA", "mixed", "芯片政策和 AI 需求消息对其高度敏感"),
            ("AMD", "mixed", "芯片政策和 AI 需求消息对其高度敏感"),
            ("SMH", "mixed", "半导体 ETF 对行业政策消息敏感"),
            ("TSM", "mixed", "供应链和地缘政策影响台积电预期"),
        ],
    },
    {
        "category": "autos_ev",
        "keywords": [
            "auto",
            "cars",
            "ev",
            "electric vehicle",
            "tesla",
            "ford",
            "gm",
            "汽车",
            "电动车",
            "特斯拉",
        ],
        "asset_classes": ["autos", "ev"],
        "tickers": [
            ("TSLA", "mixed", "电动车政策、关税和补贴消息影响较大"),
            ("F", "mixed", "汽车关税和制造政策影响较大"),
            ("GM", "mixed", "汽车关税和制造政策影响较大"),
        ],
    },
    {
        "category": "crypto",
        "keywords": [
            "bitcoin",
            "btc",
            "crypto",
            "cryptocurrency",
            "stablecoin",
            "比特币",
            "加密货币",
            "稳定币",
        ],
        "asset_classes": ["crypto", "crypto_equities"],
        "tickers": [
            ("BTC-USD", "mixed", "加密资产方向取决于监管/支持语境"),
            ("COIN", "mixed", "交易所股票对加密政策和成交量敏感"),
            ("MSTR", "mixed", "高比特币敞口股票对 BTC 方向敏感"),
            ("IBIT", "mixed", "比特币 ETF 对 BTC 价格敏感"),
        ],
    },
    {
        "category": "healthcare_drug_pricing",
        "keywords": [
            "drug price",
            "pharma",
            "medicare",
            "healthcare",
            "vaccine",
            "药价",
            "制药",
            "医疗",
            "医保",
            "疫苗",
        ],
        "asset_classes": ["healthcare", "pharma"],
        "tickers": [
            ("XLV", "mixed", "医疗板块受监管和支付政策影响"),
            ("PFE", "mixed", "药价和监管消息影响制药公司"),
            ("MRK", "mixed", "药价和监管消息影响制药公司"),
            ("UNH", "mixed", "医保支付和监管消息影响管理式医疗"),
        ],
    },
]


SEVERITY_BY_CATEGORY = {
    "war_geopolitics": 4,
    "tariff_trade": 4,
    "fed_rates": 4,
    "semiconductors": 3,
    "energy_oil": 3,
    "autos_ev": 3,
    "crypto": 3,
    "healthcare_drug_pricing": 3,
    "general": 2,
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def ensure_app_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    ensure_app_dir()
    if CONFIG_PATH.exists():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(loaded)
            if not cfg.get("ai_api_key") and cfg.get("openai_api_key"):
                cfg["ai_api_key"] = cfg.get("openai_api_key", "")
            if not cfg.get("ai_model") and cfg.get("openai_model"):
                cfg["ai_model"] = cfg.get("openai_model", "")
            if cfg.get("ai_provider") not in AI_PROVIDER_PRESETS:
                cfg["ai_provider"] = "openai_responses"
            if isinstance(cfg.get("accounts"), str):
                cfg["accounts"] = parse_accounts(cfg["accounts"])
            return cfg
        except Exception:
            return DEFAULT_CONFIG.copy()
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    ensure_app_dir()
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_accounts(raw):
    if isinstance(raw, list):
        return [clean_account(x) for x in raw if clean_account(x)]
    raw = raw.replace(",", "\n")
    return [clean_account(x) for x in raw.splitlines() if clean_account(x)]


def clean_account(value):
    value = str(value).strip()
    if value.startswith("@"):
        value = value[1:]
    value = value.strip("/")
    if "x.com/" in value or "twitter.com/" in value:
        value = value.rstrip("/").split("/")[-1]
    return value


def http_json(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def post_json(url, payload, headers=None, timeout=45):
    body = json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json"}
    merged_headers.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=merged_headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def http_error_detail(exc):
    try:
        body = exc.read().decode("utf-8", errors="ignore")
    except Exception:
        body = ""
    body = " ".join(body.split())
    if len(body) > 800:
        body = body[:800] + "..."
    if body:
        return f"HTTP {exc.code}: {body}"
    return f"HTTP {exc.code}: {exc.reason}"


class AlertStore:
    def __init__(self, db_path):
        ensure_app_dir()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    post_id TEXT PRIMARY KEY,
                    account TEXT NOT NULL,
                    created_at TEXT,
                    text TEXT NOT NULL,
                    url TEXT,
                    raw_json TEXT,
                    ingested_at TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT NOT NULL,
                    account TEXT NOT NULL,
                    created_at TEXT,
                    category TEXT,
                    severity INTEGER,
                    confidence REAL,
                    headline TEXT,
                    summary TEXT,
                    analysis_json TEXT,
                    source_url TEXT,
                    inserted_at TEXT NOT NULL
                )
                """
            )
            for column, definition in [
                ("status", "TEXT DEFAULT 'active'"),
                ("deleted_at", "TEXT"),
                ("favorite", "INTEGER DEFAULT 0"),
                ("bucket", "TEXT DEFAULT 'new'"),
            ]:
                try:
                    self.conn.execute(f"ALTER TABLE alerts ADD COLUMN {column} {definition}")
                except sqlite3.OperationalError:
                    pass
            self.conn.commit()

    def seen_post(self, post_id):
        with self.lock:
            row = self.conn.execute("SELECT 1 FROM posts WHERE post_id = ?", (post_id,)).fetchone()
            return row is not None

    def has_active_alert(self, post_id):
        with self.lock:
            row = self.conn.execute(
                "SELECT 1 FROM alerts WHERE post_id = ? AND COALESCE(status, 'active') = 'active' LIMIT 1",
                (post_id,),
            ).fetchone()
            return row is not None

    def add_post_and_alert(self, post, analysis, bucket="new"):
        with self.lock:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO posts
                    (post_id, account, created_at, text, url, raw_json, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post.post_id,
                    post.account,
                    post.created_at,
                    post.text,
                    post.url,
                    json.dumps(post.raw, ensure_ascii=False),
                    now_iso(),
                ),
            )
            self.conn.execute(
                """
                INSERT INTO alerts
                    (post_id, account, created_at, category, severity, confidence,
                     headline, summary, analysis_json, source_url, inserted_at, status, favorite, bucket)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?)
                """,
                (
                    post.post_id,
                    post.account,
                    post.created_at,
                    analysis.get("category", "general"),
                    int(analysis.get("severity", 1)),
                    float(analysis.get("confidence", 0)),
                    analysis.get("headline", ""),
                    analysis.get("summary", ""),
                    json.dumps(analysis, ensure_ascii=False),
                    post.url,
                    now_iso(),
                    bucket,
                ),
            )
            self.conn.commit()

    def latest_alerts(self, limit=100, bucket=None, status="active", favorite=None):
        where = []
        params = []
        if status is not None:
            where.append("COALESCE(status, 'active') = ?")
            params.append(status)
        if bucket:
            where.append("COALESCE(bucket, 'new') = ?")
            params.append(bucket)
        if favorite is not None:
            where.append("COALESCE(favorite, 0) = ?")
            params.append(1 if favorite else 0)
        where_sql = "WHERE " + " AND ".join(where) if where else ""
        params.append(limit)
        with self.lock:
            rows = self.conn.execute(
                f"""
                SELECT id, post_id, account, created_at, category, severity,
                       confidence, headline, summary, analysis_json, source_url,
                       COALESCE(status, 'active'), deleted_at, COALESCE(favorite, 0),
                       COALESCE(bucket, 'new')
                FROM alerts
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [
            {
                "id": r[0],
                "post_id": r[1],
                "account": r[2],
                "created_at": r[3],
                "category": r[4],
                "severity": r[5],
                "confidence": r[6],
                "headline": r[7],
                "summary": r[8],
                "analysis": json.loads(r[9]),
                "source_url": r[10],
                "status": r[11],
                "deleted_at": r[12],
                "favorite": bool(r[13]),
                "bucket": r[14],
            }
            for r in rows
        ]

    def post_for_alert(self, alert_id):
        with self.lock:
            row = self.conn.execute(
                """
                SELECT p.post_id, p.account, p.created_at, p.text, p.url, p.raw_json
                FROM alerts a
                JOIN posts p ON p.post_id = a.post_id
                WHERE a.id = ?
                """,
                (int(alert_id),),
            ).fetchone()
        if not row:
            return None
        return Post(
            post_id=row[0],
            account=row[1],
            created_at=row[2],
            text=row[3],
            url=row[4],
            raw=json.loads(row[5] or "{}"),
        )

    def update_alert_analysis(self, alert_id, analysis):
        with self.lock:
            cur = self.conn.execute(
                """
                UPDATE alerts
                SET category = ?, severity = ?, confidence = ?, headline = ?,
                    summary = ?, analysis_json = ?
                WHERE id = ?
                """,
                (
                    analysis.get("category", "general"),
                    int(analysis.get("severity", 1)),
                    float(analysis.get("confidence", 0)),
                    analysis.get("headline", ""),
                    analysis.get("summary", ""),
                    json.dumps(analysis, ensure_ascii=False),
                    int(alert_id),
                ),
            )
            self.conn.commit()
            return cur.rowcount

    def move_alert_ids_to_trash(self, alert_ids):
        clean_ids = [int(alert_id) for alert_id in alert_ids]
        if not clean_ids:
            return 0
        placeholders = ",".join("?" for _ in clean_ids)
        with self.lock:
            cur = self.conn.execute(
                f"UPDATE alerts SET status = 'deleted', deleted_at = ? WHERE id IN ({placeholders})",
                [now_iso(), *clean_ids],
            )
            self.conn.commit()
            return cur.rowcount

    def delete_alert_ids(self, alert_ids):
        clean_ids = [int(alert_id) for alert_id in alert_ids]
        if not clean_ids:
            return 0
        placeholders = ",".join("?" for _ in clean_ids)
        with self.lock:
            cur = self.conn.execute(f"DELETE FROM alerts WHERE id IN ({placeholders})", clean_ids)
            self.conn.commit()
            return cur.rowcount

    def restore_alert_ids(self, alert_ids):
        clean_ids = [int(alert_id) for alert_id in alert_ids]
        if not clean_ids:
            return 0
        placeholders = ",".join("?" for _ in clean_ids)
        with self.lock:
            cur = self.conn.execute(
                f"UPDATE alerts SET status = 'active', deleted_at = NULL WHERE id IN ({placeholders})",
                clean_ids,
            )
            self.conn.commit()
            return cur.rowcount

    def set_favorite(self, alert_ids, favorite=True):
        clean_ids = [int(alert_id) for alert_id in alert_ids]
        if not clean_ids:
            return 0
        placeholders = ",".join("?" for _ in clean_ids)
        with self.lock:
            cur = self.conn.execute(
                f"UPDATE alerts SET favorite = ? WHERE id IN ({placeholders})",
                [1 if favorite else 0, *clean_ids],
            )
            self.conn.commit()
            return cur.rowcount

    def mark_deleted_refetch_as_past_day(self, post_id):
        with self.lock:
            self.conn.execute(
                "UPDATE alerts SET bucket = 'past_day' WHERE post_id = ? AND COALESCE(status, 'active') = 'deleted'",
                (post_id,),
            )
            self.conn.commit()

    def delete_alerts_matching(self, account="", category="", max_severity="", manual_only=False):
        where = []
        params = []
        account = account.strip().lower()
        category = category.strip().lower()
        max_severity = str(max_severity).strip()
        if account:
            where.append("LOWER(account) LIKE ?")
            params.append(f"%{account}%")
        if category:
            where.append("LOWER(category) LIKE ?")
            params.append(f"%{category}%")
        if max_severity:
            where.append("severity <= ?")
            params.append(int(max_severity))
        if manual_only:
            where.append("post_id LIKE 'manual-%'")
        where.append("COALESCE(status, 'active') = 'active'")
        sql = "UPDATE alerts SET status = 'deleted', deleted_at = ?"
        params = [now_iso(), *params]
        if where:
            sql += " WHERE " + " AND ".join(where)
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur.rowcount


@dataclass
class Post:
    post_id: str
    account: str
    created_at: str
    text: str
    url: str
    raw: dict


class XClient:
    def __init__(self, bearer_token):
        self.bearer_token = bearer_token.strip()
        self.user_cache = {}
        self.api_bases = ["https://api.x.com/2", "https://api.twitter.com/2"]

    def _headers(self):
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def is_configured(self):
        return bool(self.bearer_token)

    def lookup_user(self, username):
        username = clean_account(username)
        if username in self.user_cache:
            return self.user_cache[username]
        data = self._get(f"/users/by/username/{urllib.parse.quote(username)}")
        user_id = data.get("data", {}).get("id")
        if not user_id:
            raise RuntimeError(f"未找到 X 账号: {username}")
        self.user_cache[username] = user_id
        return user_id

    def fetch_recent_posts(self, username, max_results=5, exclude_replies=True, exclude_retweets=True, start_time=None):
        user_id = self.lookup_user(username)
        params = {
            "max_results": max(5, min(int(max_results), 100)),
            "tweet.fields": "created_at,public_metrics,referenced_tweets,entities,context_annotations",
        }
        excludes = []
        if exclude_replies:
            excludes.append("replies")
        if exclude_retweets:
            excludes.append("retweets")
        if excludes:
            params["exclude"] = ",".join(excludes)
        if start_time:
            params["start_time"] = start_time
        query = urllib.parse.urlencode(params)
        data = self._get(f"/users/{user_id}/tweets?{query}")
        posts = []
        for item in data.get("data", []) or []:
            post_id = item.get("id", "")
            posts.append(
                Post(
                    post_id=post_id,
                    account=username,
                    created_at=item.get("created_at", ""),
                    text=item.get("text", ""),
                    url=f"https://x.com/{username}/status/{post_id}" if post_id else "",
                    raw=item,
                )
            )
        return posts

    def _get(self, path):
        last_exc = None
        for base in self.api_bases:
            try:
                return http_json(f"{base}{path}", headers=self._headers())
            except urllib.error.HTTPError as exc:
                last_exc = exc
                if exc.code in {401, 403, 429}:
                    raise
            except Exception as exc:
                last_exc = exc
        raise last_exc


class LocalAnalyzer:
    def analyze(self, text, account=""):
        text_lower = text.lower()
        matches = []
        for rule in EVENT_RULES:
            score = sum(1 for keyword in rule["keywords"] if keyword.lower() in text_lower)
            if score:
                matches.append((score, rule))
        if matches:
            matches.sort(key=lambda item: item[0], reverse=True)
            rule = matches[0][1]
            category = rule["category"]
            tickers = [
                {
                    "symbol": symbol,
                    "direction": self._direction_with_context(direction, text_lower),
                    "asset_class": self._asset_class_for_symbol(symbol, rule["asset_classes"]),
                    "reason": reason,
                }
                for symbol, direction, reason in rule["tickers"]
            ]
            confidence = min(0.88, 0.48 + matches[0][0] * 0.08)
            headline = f"{account}: {category} 事件预警" if account else f"{category} 事件预警"
            summary = self._summary(text, f"命中 {category} 规则，建议人工复核语境后交易。")
            severity = SEVERITY_BY_CATEGORY.get(category, 2)
            asset_classes = rule["asset_classes"]
        else:
            category = "general"
            tickers = [
                {
                    "symbol": "SPY",
                    "direction": "neutral",
                    "asset_class": "equity_index",
                    "reason": "未命中特定宏观/行业规则，仅作为市场基准观察",
                }
            ]
            confidence = 0.25
            headline = f"{account}: 普通动态" if account else "普通动态"
            summary = self._summary(text, "未识别出明确交易事件。")
            severity = 1
            asset_classes = ["watchlist"]
        return {
            "headline": headline,
            "summary": summary,
            "category": category,
            "severity": severity,
            "confidence": round(confidence, 2),
            "asset_classes": asset_classes,
            "tickers": tickers,
            "time_horizon": "minutes_to_days",
            "novelty": "unknown",
            "source": "local_rules",
            "risk_note": "这不是投资建议；方向判断只用于预警和研究，交易前需要结合价格、成交量、新闻确认和个人风险承受能力。",
        }

    @staticmethod
    def _summary(text, suffix):
        cleaned = " ".join(text.split())
        if len(cleaned) > 180:
            cleaned = cleaned[:177] + "..."
        return f"{cleaned}\n{suffix}"

    @staticmethod
    def _direction_with_context(direction, text_lower):
        if direction != "mixed":
            return direction
        positive_terms = ["deal", "agreement", "cut", "lower", "support", "approve", "win", "peace", "停火", "协议", "支持"]
        negative_terms = ["ban", "sanction", "tariff", "higher", "attack", "war", "terminate", "制裁", "关税", "战争", "禁止"]
        pos = sum(1 for term in positive_terms if term in text_lower)
        neg = sum(1 for term in negative_terms if term in text_lower)
        if pos > neg:
            return "bullish"
        if neg > pos:
            return "bearish"
        return "mixed"

    @staticmethod
    def _asset_class_for_symbol(symbol, fallback):
        if symbol in {"SPY", "QQQ", "DIA", "IWM"}:
            return "equity_index"
        if symbol in {"GLD", "USO"}:
            return "commodity_etf"
        if symbol in {"TLT"}:
            return "bond_etf"
        if symbol.endswith("-USD"):
            return "crypto"
        return fallback[0] if fallback else "equity"


class MultiAIAnalyzer:
    def __init__(self, config):
        self.config = config
        self.provider = config.get("ai_provider", "openai_responses")
        self.preset = AI_PROVIDER_PRESETS.get(self.provider, AI_PROVIDER_PRESETS["openai_responses"])
        self.api_key = (config.get("ai_api_key") or config.get("openai_api_key") or "").strip()
        self.model = (config.get("ai_model") or config.get("openai_model") or self.preset["model"]).strip()
        self.base_url = (config.get("ai_base_url") or self.preset["base_url"]).strip().rstrip("/")
        self.timeout = effective_ai_timeout_seconds(config, self.preset)
        self.local = LocalAnalyzer()

    def is_configured(self):
        return bool(self.api_key)

    def analyze(self, text, account=""):
        baseline = self.local.analyze(text, account)
        if not self.is_configured():
            return baseline
        schema = self._schema()
        prompt = self._prompt(text, account, baseline)
        prompt = (
            "重要输出语言要求：所有面向用户阅读的自然语言字段必须使用简体中文，包括 "
            "headline、summary、tickers.reason、risk_note。"
            "category、direction、asset_class、time_horizon、novelty 可以保留英文枚举值。\n\n"
            + prompt
        )
        try:
            kind = self.preset.get("kind")
            if kind == "responses":
                parsed = self._analyze_openai_responses(prompt, schema)
            elif kind == "gemini":
                parsed = self._analyze_gemini(prompt)
            else:
                parsed = self._analyze_chat_completions(prompt)
            parsed["source"] = f"ai_{self.provider}"
            if not parsed.get("tickers"):
                parsed["tickers"] = baseline["tickers"]
            return self._normalize_result(parsed, baseline)
        except TimeoutError as exc:
            baseline["source"] = f"local_rules_after_{self.provider}_timeout"
            baseline["risk_note"] += f"\nAI 分析超时，已回退本地规则: {exc}"
            return baseline
        except Exception as exc:
            baseline["source"] = f"local_rules_after_{self.provider}_error"
            baseline["risk_note"] += f"\nAI 分析失败，已回退本地规则: {exc}"
            return baseline

    @staticmethod
    def _schema():
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "headline": {"type": "string"},
                "summary": {"type": "string"},
                "category": {"type": "string"},
                "severity": {"type": "integer", "minimum": 1, "maximum": 5},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "asset_classes": {"type": "array", "items": {"type": "string"}},
                "tickers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "symbol": {"type": "string"},
                            "direction": {"type": "string", "enum": ["bullish", "bearish", "mixed", "neutral"]},
                            "asset_class": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["symbol", "direction", "asset_class", "reason"],
                    },
                },
                "time_horizon": {"type": "string"},
                "novelty": {"type": "string", "enum": ["new", "repeated", "reversal", "unknown"]},
                "risk_note": {"type": "string"},
            },
            "required": [
                "headline",
                "summary",
                "category",
                "severity",
                "confidence",
                "asset_classes",
                "tickers",
                "time_horizon",
                "novelty",
                "risk_note",
            ],
        }

    @staticmethod
    def _prompt(text, account, baseline):
        return (
            "你是金融新闻事件预警分析器。基于给定帖子判断可能影响的交易类别、"
            "相关股票/ETF 代码和利好利空方向。不要给确定性收益承诺，不要建议自动下单。"
            "优先输出可交易且流动性较好的美股/ETF 代码；无法判断就用 mixed 或 neutral。\n\n"
            "只输出一个 JSON 对象，不要 Markdown，不要解释。JSON 字段必须包含："
            "headline, summary, category, severity, confidence, asset_classes, tickers, "
            "time_horizon, novelty, risk_note。tickers 每项包含 symbol, direction, asset_class, reason。"
            "direction 只能是 bullish, bearish, mixed, neutral；severity 为 1 到 5。\n\n"
            f"账号/来源: @{account}\n帖子: {text}\n\n"
            f"本地规则初判供参考: {json.dumps(baseline, ensure_ascii=False)}"
        )

    def _analyze_openai_responses(self, prompt, schema):
        prompt = (
            prompt
        )
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": "Return only structured JSON that matches the provided schema. User-facing natural language fields must be Simplified Chinese.",
                },
                {"role": "user", "content": prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "market_event_alert",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        try:
            response = post_json(
                f"{self.base_url}/responses",
                payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        except TimeoutError as exc:
            raise TimeoutError(f"{self.preset['label']} / {self.model} 超过 {self.timeout} 秒未返回。可调大 AI 超时秒数，或换更快模型。") from exc
        except urllib.error.HTTPError as exc:
            raise RuntimeError(http_error_detail(exc)) from exc
        return parse_model_json(extract_response_text(response))

    def _analyze_chat_completions(self, prompt):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return only valid JSON. Do not wrap it in Markdown. User-facing natural language fields must be Simplified Chinese."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.preset.get("temperature", 0.2),
            "response_format": {"type": "json_object"},
        }
        try:
            response = post_json(
                f"{self.base_url}/chat/completions",
                payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        except TimeoutError as exc:
            raise TimeoutError(f"{self.preset['label']} / {self.model} 超过 {self.timeout} 秒未返回。可调大 AI 超时秒数，或换更快模型。") from exc
        except urllib.error.HTTPError as exc:
            detail = http_error_detail(exc)
            if exc.code not in {400, 422}:
                raise RuntimeError(detail) from exc
            payload.pop("response_format", None)
            try:
                response = post_json(
                    f"{self.base_url}/chat/completions",
                    payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=self.timeout,
                )
            except TimeoutError as timeout_exc:
                raise TimeoutError(f"{self.preset['label']} / {self.model} 重试后仍超过 {self.timeout} 秒未返回。") from timeout_exc
            except urllib.error.HTTPError as retry_exc:
                raise RuntimeError(f"{detail}; retry without response_format failed: {http_error_detail(retry_exc)}") from retry_exc
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return parse_model_json(content)

    def _analyze_gemini(self, prompt):
        encoded_model = urllib.parse.quote(self.model, safe="")
        url = f"{self.base_url}/models/{encoded_model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.preset.get("temperature", 0.2),
                "responseMimeType": "application/json",
            },
        }
        try:
            response = post_json(url, payload, headers={"x-goog-api-key": self.api_key}, timeout=self.timeout)
        except TimeoutError as exc:
            raise TimeoutError(f"{self.preset['label']} / {self.model} 超过 {self.timeout} 秒未返回。可调大 AI 超时秒数，或换更快模型。") from exc
        except urllib.error.HTTPError as exc:
            detail = http_error_detail(exc)
            if exc.code not in {400, 422}:
                raise RuntimeError(detail) from exc
            payload["generationConfig"].pop("responseMimeType", None)
            try:
                response = post_json(url, payload, headers={"x-goog-api-key": self.api_key}, timeout=self.timeout)
            except TimeoutError as timeout_exc:
                raise TimeoutError(f"{self.preset['label']} / {self.model} 重试后仍超过 {self.timeout} 秒未返回。") from timeout_exc
            except urllib.error.HTTPError as retry_exc:
                raise RuntimeError(f"{detail}; retry without responseMimeType failed: {http_error_detail(retry_exc)}") from retry_exc
        parts = response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in parts)
        return parse_model_json(content)

    @staticmethod
    def _normalize_result(parsed, baseline):
        parsed.setdefault("headline", baseline.get("headline", "事件预警"))
        parsed.setdefault("summary", baseline.get("summary", ""))
        parsed.setdefault("category", baseline.get("category", "general"))
        parsed.setdefault("severity", baseline.get("severity", 1))
        parsed.setdefault("confidence", baseline.get("confidence", 0.25))
        parsed.setdefault("asset_classes", baseline.get("asset_classes", []))
        parsed.setdefault("tickers", baseline.get("tickers", []))
        parsed.setdefault("time_horizon", "minutes_to_days")
        parsed.setdefault("novelty", "unknown")
        parsed.setdefault("risk_note", "这不是投资建议；方向判断只用于预警和研究。")
        return parsed


class GptAnalyzer(MultiAIAnalyzer):
    def __init__(self, api_key, model):
        super().__init__(
            {
                "ai_provider": "openai_responses",
                "ai_api_key": api_key,
                "ai_model": model,
                "ai_base_url": "https://api.openai.com/v1",
            }
        )


def extract_response_text(response):
    if response.get("output_text"):
        return response["output_text"]
    for item in response.get("output", []) or []:
        for content in item.get("content", []) or []:
            if "text" in content:
                return content["text"]
    raise RuntimeError("OpenAI 响应中没有可解析文本")


def parse_model_json(content):
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.strip("`").strip()
        if content.lower().startswith("json"):
            content = content[4:].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise


def build_analyzer(config):
    if config.get("use_gpt"):
        return MultiAIAnalyzer(config)
    return LocalAnalyzer()


def trade_link(symbol, template):
    encoded_symbol = urllib.parse.quote(symbol)
    return template.replace("{symbol}", encoded_symbol)


def effective_ai_timeout_seconds(config, preset):
    try:
        configured = int(config.get("ai_timeout_seconds", 90))
    except (TypeError, ValueError):
        configured = 90
    try:
        provider_min = int(preset.get("min_timeout_seconds", 15))
    except (TypeError, ValueError):
        provider_min = 15
    return max(15, min(max(configured, provider_min), 300))


def x_content_labels(post):
    refs = post.raw.get("referenced_tweets", []) if isinstance(post.raw, dict) else []
    ref_types = {str(ref.get("type", "")).lower() for ref in refs if isinstance(ref, dict)}
    labels = []
    if "replied_to" in ref_types:
        labels.append("回复")
    if "retweeted" in ref_types or str(post.text).startswith("RT @"):
        labels.append("转发")
    if "quoted" in ref_types:
        labels.append("引用")
    return labels or ["原创"]


def annotate_x_filter_state(post, analysis, config):
    labels = x_content_labels(post)
    filtered_labels = []
    if bool(config.get("exclude_replies", True)) and "回复" in labels:
        filtered_labels.append("回复")
    if bool(config.get("exclude_retweets", True)) and "转发" in labels:
        filtered_labels.append("转发")
    analysis["x_content_type"] = " / ".join(labels)
    analysis["filtered_by_settings"] = bool(filtered_labels)
    analysis["filter_note"] = " / ".join(filtered_labels)
    if filtered_labels:
        prefix = f"[原筛选: {'/'.join(filtered_labels)}] "
        headline = analysis.get("headline", "")
        if not headline.startswith(prefix):
            analysis["headline"] = prefix + headline
    elif labels != ["原创"]:
        prefix = f"[{'/'.join(labels)}] "
        headline = analysis.get("headline", "")
        if not headline.startswith(prefix):
            analysis["headline"] = prefix + headline
    return analysis


class MonitorWorker(threading.Thread):
    def __init__(self, config, store, outbox, stop_event, force_readd_inactive=False):
        super().__init__(daemon=True)
        self.config = config
        self.store = store
        self.outbox = outbox
        self.stop_event = stop_event
        self.started_at = datetime.now(timezone.utc)
        self.force_readd_inactive = force_readd_inactive

    def run(self):
        while not self.stop_event.is_set():
            self.poll_once()
            wait_seconds = max(20, int(self.config.get("poll_seconds", 90)))
            for _ in range(wait_seconds):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def poll_once(self):
        op_id = f"poll-{int(time.time() * 1000)}"
        try:
            self.outbox.put(("workflow_start", {"id": op_id, "name": "抓取 X 过去一天和新发布内容"}))
            self.outbox.put(("log", "开始轮询 X 账号..."))
            client = XClient(self.config.get("x_bearer_token", ""))
            if not client.is_configured():
                self.outbox.put(("log", "未配置 X Bearer Token，跳过自动抓取。可使用演示预警测试界面。"))
                self.outbox.put(("workflow_end", {"id": op_id, "status": "跳过", "detail": "未配置 X Bearer Token"}))
                return
            analyzer = build_analyzer(self.config)
            fast_past_analyzer = LocalAnalyzer()
            accounts = parse_accounts(self.config.get("accounts", []))
            new_count = 0
            past_count = 0
            created_any = False
            start_time = (datetime.now(timezone.utc) - timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            for account in accounts:
                posts = client.fetch_recent_posts(
                    account,
                    max_results=int(self.config.get("max_posts_per_account", 5)),
                    exclude_replies=False,
                    exclude_retweets=False,
                    start_time=start_time,
                )
                for post in sorted(posts, key=lambda p: p.created_at or ""):
                    if not post.post_id:
                        continue
                    if self.store.seen_post(post.post_id):
                        if self.force_readd_inactive and not self.store.has_active_alert(post.post_id):
                            self.outbox.put(("log", f"立即轮询重新添加已从活动列表移除的内容: @{account} / {post.post_id}"))
                        else:
                            self.store.mark_deleted_refetch_as_past_day(post.post_id)
                            continue
                    post_time = parse_iso_datetime(post.created_at)
                    bucket = "new" if post_time and post_time >= self.started_at else "past_day"
                    if bucket == "past_day":
                        analysis = fast_past_analyzer.analyze(post.text, post.account)
                        analysis["source"] = "local_rules_fast_past_day"
                        analysis["risk_note"] = (
                            f"{analysis.get('risk_note', '')}\n"
                            "过去一天历史内容使用本地快速规则入库；需要深度语义分析时，请在该条内容上打开 AI 分析窗口重新生成。"
                        ).strip()
                    else:
                        analysis = analyzer.analyze(post.text, post.account)
                    analysis = annotate_x_filter_state(post, analysis, self.config)
                    self.store.add_post_and_alert(post, analysis, bucket=bucket)
                    created_any = True
                    new_count += 1
                    if bucket == "past_day":
                        past_count += 1
            if created_any:
                self.outbox.put(("alert", None))
            self.outbox.put(("log", f"轮询完成，新增 {new_count} 条预警，其中过去一天 {past_count} 条。"))
            self.outbox.put(("workflow_end", {"id": op_id, "status": "完成", "detail": f"新增 {new_count} 条，过去一天 {past_count} 条"}))
        except urllib.error.HTTPError as exc:
            self.outbox.put(("log", f"X API 请求失败: {http_error_detail(exc)}"))
            self.outbox.put(("workflow_end", {"id": op_id, "status": "失败", "detail": http_error_detail(exc)}))
        except Exception as exc:
            self.outbox.put(("log", f"轮询失败: {exc}\n{traceback.format_exc()}"))
            self.outbox.put(("workflow_end", {"id": op_id, "status": "失败", "detail": str(exc)}))


class Tooltip:
    def __init__(self, widget, text, delay_ms=650):
        if widget.winfo_class() != "TButton":
            return
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.after_id = None
        self.tip = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def schedule(self, _event=None):
        self.cancel()
        self.after_id = self.widget.after(self.delay_ms, self.show)

    def cancel(self):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show(self):
        self.after_id = None
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(
            self.tip,
            text=self.text,
            justify=LEFT,
            background="#111827",
            foreground="#ffffff",
            padding=(10, 7),
            wraplength=360,
        )
        label.pack()

    def hide(self, _event=None):
        self.cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None


class TradeAlertApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trade Event Alert - X 实时事件预警")
        self.root.geometry("1180x760")
        self.config = load_config()
        self.store = AlertStore(DB_PATH)
        self.outbox = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.alert_rows = {}
        self.selected_alert = None
        self.status_var = StringVar(value="就绪")
        self.home_feedback_var = StringVar(value="请选择操作：开始监控、立即轮询，或从粘贴分析创建预警。")
        self.status_after_id = None
        self.ai_drawer_visible = False
        self.reanalysis_running = False
        self.workflow_items = {}
        self.active_display_count = 0
        self.secondary_detail_texts = {}
        self.secondary_ticker_trees = {}
        self.ai_window = None
        self.ai_window_status_var = None
        self.ai_window_elapsed_var = None
        self.ai_window_started_at = None
        self.ai_window_timeout_seconds = None
        self.ai_window_timer_after = None
        self._configure_style()
        self._build_ui()
        self.refresh_alerts()
        self.root.after(500, self._process_outbox)

    def _configure_style(self):
        self.root.configure(bg=COLORS["bg"])
        self.root.option_add("*Font", "{Segoe UI} 10")
        self.root.option_add("*TCombobox*Listbox.font", "{Segoe UI} 10")
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", font=("Segoe UI", 10), background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
        style.configure("Warning.TLabel", background=COLORS["warning_bg"], foreground=COLORS["warning_text"], padding=8)
        style.configure("Status.TLabel", background="#e9edf5", foreground=COLORS["muted"], padding=(10, 7))
        style.configure("Feedback.TLabel", background=COLORS["info_bg"], foreground=COLORS["accent_dark"], padding=(12, 9), font=("Segoe UI", 10, "bold"))
        style.configure("Section.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 11, "bold"))
        style.configure("Card.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1)
        style.configure("CardTitle.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Segoe UI", 10, "bold"))
        style.configure("CardMuted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"])
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 8), background="#e9edf5", foreground=COLORS["muted"])
        style.map("TNotebook.Tab", background=[("selected", COLORS["panel"])], foreground=[("selected", COLORS["text"])])
        style.configure("TButton", padding=(12, 7), background="#e8edf7", foreground=COLORS["text"], borderwidth=1)
        style.map("TButton", background=[("active", "#dfe6f3")])
        style.configure("Primary.TButton", background=COLORS["accent"], foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", COLORS["accent_dark"])], foreground=[("active", "#ffffff")])
        style.configure("Danger.TButton", background=COLORS["danger"], foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#b91c1c")], foreground=[("active", "#ffffff")])
        style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], foreground=COLORS["text"], rowheight=30, borderwidth=0)
        style.configure("Treeview.Heading", background="#eef2f8", foreground=COLORS["muted"], padding=(8, 7), font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", COLORS["accent"])], foreground=[("selected", "#ffffff")])
        style.configure("TEntry", fieldbackground=COLORS["panel"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], padding=5)
        style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["text"], padding=4)

    def _text_widget(self, parent, height, width=None):
        options = {
            "height": height,
            "wrap": "word",
            "bg": COLORS["panel"],
            "fg": COLORS["text"],
            "insertbackground": COLORS["accent"],
            "relief": "flat",
            "borderwidth": 8,
            "highlightthickness": 1,
            "highlightbackground": COLORS["border"],
            "highlightcolor": COLORS["accent"],
            "font": ("Segoe UI", 10),
        }
        if width is not None:
            options["width"] = width
        return Text(parent, **options)

    def _button(self, parent, text, command, feedback, tooltip, style=None):
        button = ttk.Button(
            parent,
            text=text,
            command=lambda: self._run_action(feedback, command),
            style=style,
        )
        Tooltip(button, tooltip)
        button.bind("<Enter>", lambda _event: self.set_status(tooltip, temporary=False), add="+")
        button.bind("<Leave>", lambda _event: self.set_status("就绪", temporary=False), add="+")
        return button

    def _run_action(self, feedback, command):
        self.set_status(f"正在执行：{feedback}", temporary=False)
        self.root.update_idletasks()
        command()

    def set_status(self, message, temporary=True, timeout_ms=4500):
        self.status_var.set(message)
        if self.status_after_id:
            self.root.after_cancel(self.status_after_id)
            self.status_after_id = None
        if temporary:
            self.status_after_id = self.root.after(timeout_ms, lambda: self.status_var.set("就绪"))

    def set_home_feedback(self, message):
        self.home_feedback_var.set(message)

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=8, pady=(8, 0))
        self.notebook = notebook

        self.monitor_tab = ttk.Frame(notebook, padding=10)
        self.past_day_tab = ttk.Frame(notebook, padding=10)
        self.favorites_tab = ttk.Frame(notebook, padding=10)
        self.recycle_tab = ttk.Frame(notebook, padding=10)
        self.workflow_tab = ttk.Frame(notebook, padding=10)
        self.paste_tab = ttk.Frame(notebook, padding=10)
        self.settings_tab = ttk.Frame(notebook, padding=10)
        self.log_tab = ttk.Frame(notebook, padding=10)
        notebook.add(self.monitor_tab, text="新发布内容")
        notebook.add(self.past_day_tab, text="过去一天")
        notebook.add(self.favorites_tab, text="收藏夹")
        notebook.add(self.recycle_tab, text="回收站")
        notebook.add(self.workflow_tab, text="工作流")
        notebook.add(self.paste_tab, text="粘贴分析")
        notebook.add(self.settings_tab, text="设置")
        notebook.add(self.log_tab, text="日志")

        self._build_monitor_tab()
        self._build_secondary_tabs()
        self._build_workflow_tab()
        self._build_paste_tab()
        self._build_settings_tab()
        self._build_log_tab()

        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill=X, padx=8, pady=(0, 8))
        self.status_label = ttk.Label(status_bar, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(fill=X)
        Tooltip(self.status_label, "这里显示你刚刚执行的操作、当前状态和下一步提示。")
        notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def _build_monitor_tab(self):
        header = ttk.Frame(self.monitor_tab)
        header.pack(fill=X, pady=(0, 8))
        ttk.Label(header, text="实时事件工作台", style="Section.TLabel").pack(side=LEFT)
        ttk.Label(header, text="自动抓取、语义分析、股票方向和交易链接集中处理", style="Muted.TLabel").pack(side=LEFT, padx=(12, 0))

        toolbar = ttk.Frame(self.monitor_tab)
        toolbar.pack(fill=X, pady=(0, 10))
        self._button(toolbar, "开始监控", self.start_monitor, "开始监控", "保存设置并开始按轮询间隔自动读取账号新帖子。", "Primary.TButton").pack(side=LEFT, padx=(0, 6))
        self._button(toolbar, "停止", self.stop_monitor, "停止监控", "停止后台轮询；已经生成的预警不会被删除。").pack(side=LEFT, padx=(0, 6))
        self._button(toolbar, "立即轮询", self.poll_now, "立即轮询", "立刻请求一次 X API，适合测试 token、credits 和账号配置。").pack(side=LEFT, padx=(0, 6))
        self._button(toolbar, "演示预警", self.add_demo_alert, "添加演示预警", "添加一条模拟关税事件，用来检查界面和分析结果展示。").pack(side=LEFT, padx=(0, 6))
        self._button(toolbar, "刷新列表", self.refresh_alerts_with_feedback, "刷新列表", "从本地数据库重新加载预警列表。").pack(side=LEFT, padx=(0, 6))
        self._button(toolbar, "收藏选中", self.toggle_selected_favorite, "收藏选中", "把选中内容加入收藏夹，方便后续整理。").pack(side=LEFT, padx=(0, 6))
        self._button(toolbar, "删除选中", self.delete_selected_alerts, "删除选中预警", "删除当前选中的预警记录，只影响本地历史。", "Danger.TButton").pack(side=LEFT, padx=(12, 6))
        self._button(toolbar, "自定义删除", self.open_delete_dialog, "打开自定义删除", "按账号、类别、级别或粘贴来源批量删除预警。").pack(side=LEFT, padx=(0, 6))

        feedback = ttk.Label(self.monitor_tab, textvariable=self.home_feedback_var, style="Feedback.TLabel")
        feedback.pack(fill=X, pady=(0, 10))
        Tooltip(feedback, "这里显示首页按钮点击后的结果，例如监控已启动、轮询已发起、预警已删除。")

        panes = ttk.PanedWindow(self.monitor_tab, orient="horizontal")
        panes.pack(fill=BOTH, expand=True)

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        columns = ("time", "account", "category", "severity", "confidence", "headline")
        self.alert_tree = ttk.Treeview(left, columns=columns, show="headings", height=22)
        headings = {
            "time": "时间",
            "account": "账号",
            "category": "类别",
            "severity": "级别",
            "confidence": "置信度",
            "headline": "标题",
        }
        widths = {"time": 160, "account": 120, "category": 150, "severity": 60, "confidence": 70, "headline": 360}
        for col in columns:
            self.alert_tree.heading(col, text=headings[col])
            self.alert_tree.column(col, width=widths[col], anchor="w")
        self.alert_tree.pack(fill=BOTH, expand=True, side=LEFT)
        alert_scroll = ttk.Scrollbar(left, orient="vertical", command=self.alert_tree.yview)
        alert_scroll.pack(side=RIGHT, fill=Y)
        self.alert_tree.configure(yscrollcommand=alert_scroll.set)
        self.alert_tree.bind("<<TreeviewSelect>>", self.on_alert_select)
        self.alert_tree.bind("<Enter>", lambda _event: self.set_status("单击预警查看详情；颜色越偏红通常表示级别越高。", temporary=False), add="+")
        self.alert_tree.bind("<Leave>", lambda _event: self.set_status("就绪", temporary=False), add="+")
        Tooltip(self.alert_tree, "单击一条预警会在右侧显示摘要和相关股票判断；可多选后删除。")
        self.alert_tree.tag_configure("severity_high", background=COLORS["danger_bg"])
        self.alert_tree.tag_configure("severity_medium", background=COLORS["warning_bg"])
        self.alert_tree.tag_configure("severity_low", background=COLORS["info_bg"])
        self.alert_tree.tag_configure("filtered_by_settings", background="#fff7d6")

        ttk.Label(right, text="事件摘要", style="Section.TLabel").pack(anchor="w")
        self.detail_text = self._text_widget(right, height=10)
        self.detail_text.pack(fill=X, pady=(4, 8))
        Tooltip(self.detail_text, "显示当前选中内容的摘要、来源、置信度和分析类型。")

        ttk.Label(right, text="股票/ETF 判断", style="Section.TLabel").pack(anchor="w")
        ticker_columns = ("symbol", "direction", "asset_class", "reason")
        self.ticker_tree = ttk.Treeview(right, columns=ticker_columns, show="headings", height=10)
        ticker_headings = {"symbol": "代码", "direction": "方向", "asset_class": "类别", "reason": "理由"}
        ticker_widths = {"symbol": 80, "direction": 80, "asset_class": 120, "reason": 360}
        for col in ticker_columns:
            self.ticker_tree.heading(col, text=ticker_headings[col])
            self.ticker_tree.column(col, width=ticker_widths[col], anchor="w")
        self.ticker_tree.pack(fill=BOTH, expand=True, pady=(4, 8))
        self.ticker_tree.bind("<Double-1>", lambda _event: self.open_selected_trade_link())
        self.ticker_tree.bind("<Enter>", lambda _event: self.set_status("双击股票/ETF 行可打开交易或看盘链接。", temporary=False), add="+")
        self.ticker_tree.bind("<Leave>", lambda _event: self.set_status("就绪", temporary=False), add="+")
        Tooltip(self.ticker_tree, "单击选择代码；双击打开你在设置中配置的交易/看盘链接。")
        self.ticker_tree.tag_configure("bullish", background=COLORS["success_bg"])
        self.ticker_tree.tag_configure("bearish", background=COLORS["danger_bg"])
        self.ticker_tree.tag_configure("mixed", background=COLORS["warning_bg"])

        action_bar = ttk.Frame(right)
        action_bar.pack(fill=X)
        self._button(action_bar, "打开原帖", self.open_source, "打开原帖", "在浏览器中打开当前预警的原始帖子或来源链接。").pack(side=LEFT, padx=(0, 6))
        self._button(action_bar, "打开交易/看盘链接", self.open_selected_trade_link, "打开交易/看盘链接", "打开当前选中股票/ETF 的交易或看盘页面；软件不会自动下单。").pack(side=LEFT, padx=(0, 6))
        self._button(action_bar, "AI 分析窗口", self.open_ai_analysis_window, "打开 AI 分析窗口", "在独立窗口中选择 AI 和模型，重新分析当前预警。", "Primary.TButton").pack(side=LEFT, padx=(0, 6))

        re_panel = ttk.Frame(right)
        re_panel.pack(fill=X, pady=(10, 0))
        ttk.Label(re_panel, text="语义分析重生成", style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        provider_key = self.config.get("ai_provider", "openai_responses")
        self.re_ai_provider_var = StringVar(value=AI_PROVIDER_LABELS.get(provider_key, AI_PROVIDER_LABELS["openai_responses"]))
        self.re_model_var = StringVar(value=self.config.get("ai_model") or AI_PROVIDER_PRESETS[provider_key]["model"])
        re_provider = ttk.Combobox(re_panel, textvariable=self.re_ai_provider_var, values=list(AI_LABEL_TO_PROVIDER.keys()), width=18, state="readonly")
        re_provider.grid(row=1, column=0, sticky="w", padx=(0, 6))
        re_provider.bind("<<ComboboxSelected>>", lambda _event: self.apply_reanalysis_provider_preset())
        Tooltip(re_provider, "选择用于重新分析当前预警的 AI 服务商。")
        self.re_model_box = ttk.Combobox(re_panel, textvariable=self.re_model_var, values=AI_PROVIDER_PRESETS[provider_key]["models"], width=24)
        self.re_model_box.grid(row=1, column=1, sticky="w", padx=(0, 6))
        Tooltip(self.re_model_box, "选择预设模型，或直接输入当前服务商支持的自定义模型名。")
        self.reanalyze_button = self._button(re_panel, "重新分析当前预警", self.reanalyze_selected_alert, "重新分析当前预警", "用这里选择的 AI 和模型重新生成当前预警分析。", "Primary.TButton")
        self.reanalyze_button.grid(row=1, column=2, sticky="w")

    def _build_secondary_tabs(self):
        self.past_tree = self._build_alert_table_tab(
            self.past_day_tab,
            "过去一天内容",
            "显示抓取时属于过去 24 小时、但不是本次运行后新发的内容。",
            [
                ("刷新", lambda: self.refresh_alerts_with_feedback(), "刷新过去一天内容。"),
                ("收藏", lambda: self.favorite_from_tree(self.past_tree, True), "把选中内容加入收藏夹。"),
                ("移入回收站", lambda: self.trash_from_tree(self.past_tree), "把选中内容移入回收站。"),
            ],
        )
        self.favorite_tree = self._build_alert_table_tab(
            self.favorites_tab,
            "收藏夹",
            "用于整理值得后续跟踪的信息。",
            [
                ("刷新", lambda: self.refresh_alerts_with_feedback(), "刷新收藏夹。"),
                ("取消收藏", lambda: self.favorite_from_tree(self.favorite_tree, False), "取消选中内容的收藏状态。"),
                ("移入回收站", lambda: self.trash_from_tree(self.favorite_tree), "把选中收藏移入回收站。"),
            ],
        )
        self.recycle_tree = self._build_alert_table_tab(
            self.recycle_tab,
            "风险内容回收站",
            "删除的风险内容先进入这里，可恢复或永久删除。",
            [
                ("刷新", lambda: self.refresh_alerts_with_feedback(), "刷新回收站。"),
                ("恢复", self.restore_from_recycle, "恢复选中内容到对应窗口。"),
                ("永久删除", self.permanent_delete_from_recycle, "永久删除选中内容，无法恢复。"),
            ],
        )

    def _build_alert_table_tab(self, tab, title, subtitle, actions):
        header = ttk.Frame(tab)
        header.pack(fill=X, pady=(0, 8))
        ttk.Label(header, text=title, style="Section.TLabel").pack(anchor="w")
        ttk.Label(header, text=subtitle, style="Muted.TLabel", wraplength=980, justify=LEFT).pack(anchor="w", fill=X, pady=(2, 0))
        bar = ttk.Frame(tab)
        bar.pack(fill=X, pady=(0, 8))
        for label, command, tip in actions:
            style = "Danger.TButton" if "永久" in label or "回收站" in label else None
            self._button(bar, label, command, label, tip, style).pack(side=LEFT, padx=(0, 6))
        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill=BOTH, expand=True)
        left_frame = ttk.Frame(panes)
        right_frame = ttk.Frame(panes)
        panes.add(left_frame, weight=2)
        panes.add(right_frame, weight=3)

        columns = ("time", "account", "category", "severity", "confidence", "headline")
        tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=22)
        headings = {"time": "时间", "account": "账号", "category": "类别", "severity": "级别", "confidence": "置信度", "headline": "标题"}
        widths = {"time": 135, "account": 105, "category": 110, "severity": 54, "confidence": 64, "headline": 300}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor="w")
        tree.pack(fill=BOTH, expand=True, side=LEFT)
        scroll = ttk.Scrollbar(left_frame, orient="vertical", command=tree.yview)
        scroll.pack(side=RIGHT, fill=Y)
        tree.configure(yscrollcommand=scroll.set)
        ttk.Label(right_frame, text="摘要 / 分析", style="Section.TLabel").pack(anchor="w")
        detail_text = self._text_widget(right_frame, height=9)
        detail_text.pack(fill=BOTH, expand=True, pady=(4, 10))
        ttk.Label(right_frame, text="股票/ETF 判断", style="Section.TLabel").pack(anchor="w")
        ticker_columns = ("symbol", "direction", "asset_class", "reason")
        ticker_tree = ttk.Treeview(right_frame, columns=ticker_columns, show="headings", height=8)
        for col, title, width in [
            ("symbol", "代码", 72),
            ("direction", "方向", 72),
            ("asset_class", "类别", 110),
            ("reason", "理由", 330),
        ]:
            ticker_tree.heading(col, text=title)
            ticker_tree.column(col, width=width, anchor="w")
        ticker_tree.pack(fill=BOTH, expand=True, pady=(4, 8))
        ticker_tree.tag_configure("bullish", background=COLORS["success_bg"])
        ticker_tree.tag_configure("bearish", background=COLORS["danger_bg"])
        ticker_tree.tag_configure("mixed", background=COLORS["warning_bg"])
        tree.tag_configure("filtered_by_settings", background="#fff7d6")
        ticker_tree.bind("<Double-1>", lambda _event, t=ticker_tree: self.open_trade_link_from_ticker_tree(t))
        action_bar = ttk.Frame(right_frame)
        action_bar.pack(fill=X, pady=(0, 2))
        self._button(action_bar, "打开原帖", self.open_source, "打开原帖", "在浏览器中打开当前选中内容的原始链接。").pack(side=LEFT, padx=(0, 6))
        self._button(action_bar, "打开交易/看盘链接", lambda t=ticker_tree: self.open_trade_link_from_ticker_tree(t), "打开交易/看盘链接", "打开右侧当前选中股票/ETF 的交易或看盘页面。").pack(side=LEFT, padx=(0, 6))
        self._button(action_bar, "AI 分析窗口", self.open_ai_analysis_window, "打开 AI 分析窗口", "对当前选中内容重新进行中文 AI 语义分析。", "Primary.TButton").pack(side=LEFT, padx=(0, 6))
        self.secondary_detail_texts[tree] = detail_text
        self.secondary_ticker_trees[tree] = ticker_tree
        tree.bind("<<TreeviewSelect>>", lambda _event, t=tree: self.select_alert_from_tree(t))
        tree.bind("<Double-1>", lambda _event, t=tree: self.select_alert_from_tree(t))
        return tree

    def _build_workflow_tab(self):
        ttk.Label(self.workflow_tab, text="当前工作流", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        columns = ("name", "status", "elapsed", "detail")
        self.workflow_tree = ttk.Treeview(self.workflow_tab, columns=columns, show="headings", height=18)
        for col, title, width in [
            ("name", "操作", 240),
            ("status", "状态", 90),
            ("elapsed", "耗时", 90),
            ("detail", "说明", 700),
        ]:
            self.workflow_tree.heading(col, text=title)
            self.workflow_tree.column(col, width=width, anchor="w")
        self.workflow_tree.pack(fill=BOTH, expand=True)
        self.root.after(1000, self.refresh_workflow_tree)

    def _build_paste_tab(self):
        form = ttk.Frame(self.paste_tab)
        form.pack(fill=X, anchor="n")

        self.paste_account_var = StringVar(value="manual")
        self.paste_url_var = StringVar(value="")

        ttk.Label(form, text="账号/来源").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.paste_account_var, width=36).grid(row=0, column=1, sticky="w", pady=4, padx=(8, 0))

        ttk.Label(form, text="原帖链接（可选）").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.paste_url_var, width=90).grid(row=1, column=1, sticky="we", pady=4, padx=(8, 0))

        ttk.Label(form, text="帖子正文").grid(row=2, column=0, sticky="nw", pady=4)
        self.paste_text = self._text_widget(form, height=14, width=96)
        self.paste_text.grid(row=2, column=1, sticky="nsew", pady=4, padx=(8, 0))

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=1, sticky="w", pady=8, padx=(8, 0))
        self._button(buttons, "分析并加入预警", self.analyze_pasted_post, "分析粘贴内容", "分析当前粘贴文本，并把结果加入实时预警列表。", "Primary.TButton").pack(side=LEFT, padx=(0, 6))
        self._button(buttons, "清空", self.clear_paste_form, "清空粘贴表单", "清空来源、链接和正文，方便重新输入。").pack(side=LEFT)
        Tooltip(self.paste_text, "粘贴 X、Truth Social、新闻标题或其他公开文本；不会消耗 X API credits。")

        help_text = (
            "可粘贴 X、Truth Social、新闻标题或其他公开文本。"
            "此功能不调用 X API，不消耗 X credits；如果设置里启用 GPT 且填了 OpenAI API Key，会使用 GPT 分析，否则使用本地规则。"
        )
        ttk.Label(self.paste_tab, text=help_text, justify=LEFT, style="Muted.TLabel").pack(anchor="w", pady=(12, 0))

    def _build_settings_tab(self):
        frame = ttk.Frame(self.settings_tab)
        frame.pack(fill=X, anchor="n")

        self.x_token_var = StringVar(value=self.config.get("x_bearer_token", ""))
        provider_key = self.config.get("ai_provider", "openai_responses")
        self.ai_provider_var = StringVar(value=AI_PROVIDER_LABELS.get(provider_key, AI_PROVIDER_LABELS["openai_responses"]))
        self.openai_key_var = StringVar(value=self.config.get("ai_api_key") or self.config.get("openai_api_key", ""))
        self.model_var = StringVar(value=self.config.get("ai_model") or self.config.get("openai_model", "gpt-4o-mini"))
        self.ai_base_url_var = StringVar(value=self.config.get("ai_base_url") or AI_PROVIDER_PRESETS.get(provider_key, AI_PROVIDER_PRESETS["openai_responses"])["base_url"])
        self.ai_timeout_var = StringVar(value=str(self.config.get("ai_timeout_seconds", 90)))
        self.poll_var = StringVar(value=str(self.config.get("poll_seconds", 90)))
        self.max_posts_var = StringVar(value=str(self.config.get("max_posts_per_account", 5)))
        self.trade_template_var = StringVar(value=self.config.get("trade_link_template", DEFAULT_CONFIG["trade_link_template"]))
        self.use_gpt_var = StringVar(value="1" if self.config.get("use_gpt") else "0")
        self.exclude_replies_var = StringVar(value="1" if self.config.get("exclude_replies") else "0")
        self.exclude_retweets_var = StringVar(value="1" if self.config.get("exclude_retweets") else "0")

        ttk.Label(frame, text="AI 提供商").grid(row=0, column=0, sticky="w", pady=4)
        provider_header = ttk.Frame(frame)
        provider_header.grid(row=0, column=1, sticky="we", pady=4, padx=(8, 0))
        self.ai_provider_display = ttk.Label(provider_header, textvariable=self.ai_provider_var, style="Feedback.TLabel")
        self.ai_provider_display.pack(side=LEFT, fill=X, expand=True)
        self._button(provider_header, "选择 AI", self.toggle_ai_drawer, "打开 AI 选择抽屉", "展开或收起 AI 服务商选择抽屉。").pack(side=LEFT, padx=(8, 0))
        self._button(provider_header, "套用预设", self.apply_ai_provider_preset, "套用 AI 预设", "根据当前 AI 服务商填入默认 Base URL 和推荐模型。").pack(side=LEFT, padx=(6, 0))

        self.ai_drawer = ttk.Frame(frame, style="Card.TFrame", padding=10)
        self._build_ai_drawer()

        rows = [
            ("X Bearer Token（自动监控必填）", self.x_token_var, 90, True),
            ("AI API Key（启用 AI 必填）", self.openai_key_var, 90, True),
            ("AI 模型（启用 AI 必填）", self.model_var, 40, False),
            ("AI Base URL（启用 AI 必填）", self.ai_base_url_var, 90, False),
            ("AI 超时秒数 *", self.ai_timeout_var, 12, False),
            ("轮询秒数 *", self.poll_var, 12, False),
            ("每账号最多读取帖子数 *", self.max_posts_var, 12, False),
            ("交易/看盘链接模板 *", self.trade_template_var, 90, False),
        ]
        for idx, (label, var, width, secret) in enumerate(rows):
            row_idx = idx + 2
            ttk.Label(frame, text=label).grid(row=row_idx, column=0, sticky="w", pady=4)
            if label.startswith("AI 模型"):
                provider_key = AI_LABEL_TO_PROVIDER.get(self.ai_provider_var.get(), "openai_responses")
                self.model_box = ttk.Combobox(frame, textvariable=var, values=AI_PROVIDER_PRESETS[provider_key]["models"], width=width)
                self.model_box.grid(row=row_idx, column=1, sticky="w", pady=4, padx=(8, 0))
                Tooltip(self.model_box, "选择预设模型，或直接输入当前 AI 服务商支持的模型名。")
            else:
                entry = ttk.Entry(frame, textvariable=var, width=width, show="*" if secret else "")
                entry.grid(row=row_idx, column=1, sticky="we", pady=4, padx=(8, 0))

        ttk.Label(frame, text="监控账号（逗号或换行分隔）").grid(row=len(rows) + 2, column=0, sticky="nw", pady=4)
        self.accounts_text = self._text_widget(frame, height=6, width=70)
        self.accounts_text.grid(row=len(rows) + 2, column=1, sticky="we", pady=4, padx=(8, 0))
        self.accounts_text.insert("1.0", "\n".join(parse_accounts(self.config.get("accounts", []))))

        check_frame = ttk.Frame(frame)
        check_frame.grid(row=len(rows) + 3, column=1, sticky="w", pady=6, padx=(8, 0))
        ttk.Checkbutton(
            check_frame,
            text="启用 GPT 语义分析",
            variable=self.use_gpt_var,
            onvalue="1",
            offvalue="0",
        ).pack(side=LEFT, padx=(0, 16))
        ttk.Checkbutton(
            check_frame,
            text="排除回复",
            variable=self.exclude_replies_var,
            onvalue="1",
            offvalue="0",
        ).pack(side=LEFT, padx=(0, 16))
        ttk.Checkbutton(
            check_frame,
            text="排除转发",
            variable=self.exclude_retweets_var,
            onvalue="1",
            offvalue="0",
        ).pack(side=LEFT)

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(rows) + 4, column=1, sticky="w", pady=8, padx=(8, 0))
        self._button(buttons, "保存设置", self.save_settings, "保存设置", "把当前 token、账号、轮询和链接模板保存到本地配置文件。").pack(side=LEFT, padx=(0, 6))
        self._button(buttons, "打开配置目录", self.open_config_dir, "打开配置目录", "打开本地配置和数据库所在文件夹。").pack(side=LEFT)

        help_text = (
            "链接模板必须包含 {symbol}，例如：\n"
            "https://www.tradingview.com/symbols/{symbol}/\n"
            "https://robinhood.com/stocks/{symbol}\n"
            "https://www.interactivebrokers.com/en/trading/products-stocks.php?symbol={symbol}\n\n"
            "AI 提供商支持 OpenAI Responses、OpenAI 兼容接口、xAI、DeepSeek、OpenRouter 和 Gemini。\n"
            "X 数据使用官方 API Bearer Token。当前 X API 是按用量计费，读取/流式接口是否可用取决于你的开发者账号权限。"
        )
        ttk.Label(self.settings_tab, text=help_text, justify=LEFT).pack(anchor="w", pady=(18, 0))

    def _build_ai_drawer(self):
        for idx, (provider_key, preset) in enumerate(AI_PROVIDER_PRESETS.items()):
            card = ttk.Frame(self.ai_drawer, style="Card.TFrame", padding=8)
            card.grid(row=idx // 3, column=idx % 3, sticky="nsew", padx=5, pady=5)
            ttk.Label(card, text=preset["label"], style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(card, text=preset["model"], style="CardMuted.TLabel").pack(anchor="w", pady=(2, 0))
            ttk.Label(card, text=preset["base_url"], style="CardMuted.TLabel", wraplength=210).pack(anchor="w", pady=(2, 6))
            self._button(
                card,
                "选择",
                lambda key=provider_key: self.select_ai_provider(key),
                f"选择 {preset['label']}",
                f"选择 {preset['label']} 作为语义分析提供商，并填入默认模型和 Base URL。",
                "Primary.TButton",
            ).pack(anchor="e")

    def toggle_ai_drawer(self):
        if self.ai_drawer_visible:
            self.ai_drawer.grid_forget()
            self.ai_drawer_visible = False
            self.set_status("AI 选择抽屉已收起。")
            return
        self.ai_drawer.grid(row=1, column=1, sticky="we", padx=(8, 0), pady=(2, 8))
        self.ai_drawer_visible = True
        self.set_status("AI 选择抽屉已打开：请选择服务商。")

    def select_ai_provider(self, provider_key):
        preset = AI_PROVIDER_PRESETS[provider_key]
        self.ai_provider_var.set(preset["label"])
        self.apply_ai_provider_preset()
        self.ai_drawer.grid_forget()
        self.ai_drawer_visible = False
        self.set_home_feedback(f"已选择 AI：{preset['label']}。保存设置后生效。")

    def _build_log_tab(self):
        self.log_text = self._text_widget(self.log_tab, height=24)
        self.log_text.pack(fill=BOTH, expand=True)
        Tooltip(self.log_text, "这里记录 API 请求、保存设置、删除预警和分析完成等操作结果。")
        self.log(f"配置文件: {CONFIG_PATH}")
        self.log(f"数据库: {DB_PATH}")

    def save_settings(self, require_x=False):
        accounts = parse_accounts(self.accounts_text.get("1.0", END))
        if not accounts:
            self.set_status("保存失败：至少需要配置一个 X 账号。")
            messagebox.showerror("设置错误", "至少需要配置一个 X 账号。")
            return False
        if require_x and not self.x_token_var.get().strip():
            self.set_status("操作失败：自动监控需要填写 X Bearer Token。")
            messagebox.showerror("缺少 X Bearer Token", "开始监控或立即轮询前，请先填写 X Bearer Token。")
            return False
        if "{symbol}" not in self.trade_template_var.get():
            self.set_status("保存失败：交易/看盘链接模板缺少 {symbol}。")
            messagebox.showerror("设置错误", "交易/看盘链接模板必须包含 {symbol}。")
            return False
        try:
            poll_seconds = int(self.poll_var.get())
            max_posts = int(self.max_posts_var.get())
            ai_timeout = int(self.ai_timeout_var.get())
        except ValueError:
            self.set_status("保存失败：轮询秒数、帖子数和 AI 超时秒数必须是整数。")
            messagebox.showerror("设置错误", "轮询秒数、帖子数和 AI 超时秒数必须是整数。")
            return False
        if ai_timeout < 15 or ai_timeout > 300:
            self.set_status("保存失败：AI 超时秒数必须在 15 到 300 之间。")
            messagebox.showerror("设置错误", "AI 超时秒数必须在 15 到 300 之间。")
            return False
        if poll_seconds < 20:
            self.set_status("保存失败：轮询秒数不能小于 20。")
            messagebox.showerror("设置错误", "轮询秒数不能小于 20。")
            return False
        if max_posts < 5 or max_posts > 100:
            self.set_status("保存失败：每账号读取帖子数必须在 5 到 100 之间。")
            messagebox.showerror("设置错误", "每账号最多读取帖子数必须在 5 到 100 之间。")
            return False
        provider_key = AI_LABEL_TO_PROVIDER.get(self.ai_provider_var.get(), "openai_responses")
        if self.use_gpt_var.get() == "1":
            missing = []
            if not self.openai_key_var.get().strip():
                missing.append("AI API Key")
            if not self.model_var.get().strip():
                missing.append("AI 模型")
            if not self.ai_base_url_var.get().strip():
                missing.append("AI Base URL")
            if missing:
                self.set_status(f"保存失败：启用 AI 时必须填写 {', '.join(missing)}。")
                messagebox.showerror("缺少 AI 必填项", f"启用 GPT/AI 语义分析时必须填写：{', '.join(missing)}。")
                return False
        self.config = {
            "x_bearer_token": self.x_token_var.get().strip(),
            "openai_api_key": self.openai_key_var.get().strip(),
            "openai_model": self.model_var.get().strip() or "gpt-4o-mini",
            "ai_provider": provider_key,
            "ai_api_key": self.openai_key_var.get().strip(),
            "ai_model": self.model_var.get().strip() or AI_PROVIDER_PRESETS[provider_key]["model"],
            "ai_base_url": self.ai_base_url_var.get().strip() or AI_PROVIDER_PRESETS[provider_key]["base_url"],
            "ai_timeout_seconds": ai_timeout,
            "accounts": accounts,
            "poll_seconds": max(20, poll_seconds),
            "max_posts_per_account": max(5, min(max_posts, 100)),
            "use_gpt": self.use_gpt_var.get() == "1",
            "exclude_replies": self.exclude_replies_var.get() == "1",
            "exclude_retweets": self.exclude_retweets_var.get() == "1",
            "trade_link_template": self.trade_template_var.get().strip(),
        }
        save_config(self.config)
        self.log("设置已保存。")
        self.set_status(f"设置已保存：{len(accounts)} 个账号，AI={AI_PROVIDER_LABELS[provider_key]}，轮询间隔 {self.config['poll_seconds']} 秒。")
        self.set_home_feedback("设置已保存。下一步可以开始监控、立即轮询，或粘贴文本分析。")
        return True

    def apply_ai_provider_preset(self):
        provider_key = AI_LABEL_TO_PROVIDER.get(self.ai_provider_var.get(), "openai_responses")
        preset = AI_PROVIDER_PRESETS[provider_key]
        self.ai_base_url_var.set(preset["base_url"])
        self.model_var.set(preset["model"])
        provider_min_timeout = int(preset.get("min_timeout_seconds", 15))
        try:
            current_timeout = int(self.ai_timeout_var.get())
        except ValueError:
            current_timeout = 90
        if current_timeout < provider_min_timeout:
            self.ai_timeout_var.set(str(provider_min_timeout))
        if hasattr(self, "model_box"):
            self.model_box.configure(values=preset["models"])
        self.set_status(f"已套用 {preset['label']} 预设：{preset['model']} / {preset['base_url']}")

    def apply_reanalysis_provider_preset(self):
        provider_key = AI_LABEL_TO_PROVIDER.get(self.re_ai_provider_var.get(), "openai_responses")
        preset = AI_PROVIDER_PRESETS[provider_key]
        self.re_model_var.set(preset["model"])
        if hasattr(self, "re_model_box"):
            self.re_model_box.configure(values=preset["models"])
        self.set_status(f"重新分析模型已切换为 {preset['label']} / {preset['model']}。")

    def open_ai_analysis_window(self):
        if not self.selected_alert:
            messagebox.showinfo("没有选中预警", "请先选中一条预警，再打开 AI 分析窗口。")
            return
        if self.ai_window is not None and self.ai_window.winfo_exists():
            self.ai_window.lift()
            self.ai_window.focus_force()
            return
        dialog = Toplevel(self.root)
        self.ai_window = dialog
        dialog.title("AI 语义分析")
        dialog.geometry("560x330")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)

        def close_dialog():
            self._stop_ai_window_timer()
            self.ai_window = None
            self.ai_window_status_var = None
            self.ai_window_elapsed_var = None
            self.ai_window_timeout_seconds = None
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill=BOTH, expand=True)
        ttk.Label(body, text="AI 语义分析", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(body, text=f"当前预警：{self.selected_alert.get('headline', '')}", style="Muted.TLabel", wraplength=470).grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))
        provider_var = StringVar(value=self.re_ai_provider_var.get())
        model_var = StringVar(value=self.re_model_var.get())
        ttk.Label(body, text="AI 服务商").grid(row=2, column=0, sticky="w", pady=6)
        provider_box = ttk.Combobox(body, textvariable=provider_var, values=list(AI_LABEL_TO_PROVIDER.keys()), width=28, state="readonly")
        provider_box.grid(row=2, column=1, sticky="w", pady=6)
        ttk.Label(body, text="模型").grid(row=3, column=0, sticky="w", pady=6)
        model_box = ttk.Combobox(body, textvariable=model_var, width=32)
        model_box.grid(row=3, column=1, sticky="w", pady=6)

        def apply_provider(_event=None):
            key = AI_LABEL_TO_PROVIDER.get(provider_var.get(), "openai_responses")
            preset = AI_PROVIDER_PRESETS[key]
            model_var.set(preset["model"])
            model_box.configure(values=preset["models"])

        provider_box.bind("<<ComboboxSelected>>", apply_provider)
        apply_provider()

        self.ai_window_status_var = StringVar(value="就绪：选择模型后点击重新分析。")
        self.ai_window_elapsed_var = StringVar(value="耗时：0.0s")
        ttk.Label(body, textvariable=self.ai_window_status_var, style="Feedback.TLabel").grid(row=4, column=0, columnspan=2, sticky="we", pady=(12, 4))
        ttk.Label(body, textvariable=self.ai_window_elapsed_var, style="Muted.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 4))

        buttons = ttk.Frame(body)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(18, 0))
        self._button(buttons, "关闭", close_dialog, "关闭 AI 分析窗口", "关闭窗口，不执行重新分析。").pack(side=RIGHT, padx=(6, 0))

        def run_from_window():
            self.re_ai_provider_var.set(provider_var.get())
            self.re_model_var.set(model_var.get())
            self.reanalyze_selected_alert()

        self._button(buttons, "重新分析", run_from_window, "重新分析", "后台重新生成当前预警的 AI 语义分析。", "Primary.TButton").pack(side=RIGHT)

    def _start_ai_window_timer(self, provider_label, model, timeout_seconds):
        self.ai_window_started_at = time.time()
        self.ai_window_timeout_seconds = timeout_seconds
        if self.ai_window_status_var is not None:
            self.ai_window_status_var.set(f"AI 正在运行：{provider_label} / {model}。最长等待 {timeout_seconds} 秒，完成后自动更新。")
        self._tick_ai_window_timer()

    def _tick_ai_window_timer(self):
        if self.ai_window_started_at is None or self.ai_window_elapsed_var is None:
            return
        elapsed = time.time() - self.ai_window_started_at
        if self.ai_window_timeout_seconds:
            self.ai_window_elapsed_var.set(f"耗时：{elapsed:.1f}s / 最长 {self.ai_window_timeout_seconds}s")
        else:
            self.ai_window_elapsed_var.set(f"耗时：{elapsed:.1f}s")
        self.ai_window_timer_after = self.root.after(500, self._tick_ai_window_timer)

    def _stop_ai_window_timer(self):
        if self.ai_window_timer_after:
            try:
                self.root.after_cancel(self.ai_window_timer_after)
            except Exception:
                pass
            self.ai_window_timer_after = None
        self.ai_window_started_at = None

    def reanalyze_selected_alert(self):
        if self.reanalysis_running:
            self.set_status("重新分析正在进行，请等待当前任务完成。")
            self.set_home_feedback("重新分析正在后台运行，完成后会自动更新当前预警。")
            return
        if not self.selected_alert:
            self.set_status("重新分析失败：请先选中一条预警。")
            self.set_home_feedback("重新分析失败：请先在实时预警列表中选中一条预警。")
            messagebox.showinfo("没有选中预警", "请先选中一条预警，再重新生成语义分析。")
            return
        provider_key = AI_LABEL_TO_PROVIDER.get(self.re_ai_provider_var.get(), "openai_responses")
        model = self.re_model_var.get().strip()
        if not model:
            self.set_status("重新分析失败：请选择或输入模型名。")
            messagebox.showerror("缺少模型", "请先选择或输入用于重新分析的模型名。")
            return
        if not (self.config.get("ai_api_key") or self.config.get("openai_api_key")):
            self.set_status("重新分析失败：请先在设置页填写 AI API Key 并保存。")
            messagebox.showerror("缺少 AI API Key", "请先在设置页填写 AI API Key 并保存。")
            return
        post = self.store.post_for_alert(self.selected_alert["id"])
        if not post:
            self.set_status("重新分析失败：找不到原始帖子文本。")
            messagebox.showerror("找不到原文", "本地数据库中找不到这条预警对应的原始文本。")
            return
        preset = AI_PROVIDER_PRESETS[provider_key]
        cfg = self.config.copy()
        cfg.update(
            {
                "use_gpt": True,
                "ai_provider": provider_key,
                "ai_model": model,
                "ai_base_url": self.config.get("ai_base_url") if provider_key == self.config.get("ai_provider") else preset["base_url"],
            }
        )
        effective_timeout = effective_ai_timeout_seconds(cfg, preset)
        alert_id = self.selected_alert["id"]
        self.set_status(f"正在使用 {preset['label']} / {model} 重新分析当前预警，最长等待 {effective_timeout} 秒...", temporary=False)
        self.set_home_feedback(f"正在后台使用 {preset['label']} / {model} 重新分析当前预警，最长等待 {effective_timeout} 秒，界面可以继续操作。")
        self.reanalysis_running = True
        self._start_ai_window_timer(preset["label"], model, effective_timeout)
        if hasattr(self, "reanalyze_button"):
            self.reanalyze_button.configure(state="disabled")
        threading.Thread(
            target=self._reanalyze_worker,
            args=(alert_id, post, cfg, provider_key, preset["label"], model),
            daemon=True,
        ).start()

    def _reanalyze_worker(self, alert_id, post, cfg, provider_key, provider_label, model):
        try:
            analysis = MultiAIAnalyzer(cfg).analyze(post.text, post.account)
            analysis["source"] = f"reanalyzed_{analysis.get('source', provider_key)}"
            analysis = annotate_x_filter_state(post, analysis, cfg)
            self.store.update_alert_analysis(alert_id, analysis)
            self.outbox.put(("reanalysis_done", {"alert_id": alert_id, "provider": provider_label, "model": model}))
        except Exception as exc:
            self.outbox.put(("reanalysis_error", {"provider": provider_label, "model": model, "error": str(exc)}))

    def start_monitor(self):
        if not self.save_settings(require_x=True):
            self.set_home_feedback("开始监控失败：请先补齐必填设置。")
            return
        if self.worker and self.worker.is_alive():
            self.log("监控已经在运行。")
            self.set_status("监控已经在运行，不需要重复启动。")
            self.set_home_feedback("监控已经在运行。软件会继续自动检查新帖子。")
            return
        self.stop_event.clear()
        self.worker = MonitorWorker(self.config, self.store, self.outbox, self.stop_event)
        self.worker.start()
        self.log("监控已启动。")
        self.set_status("监控已启动：软件会按轮询间隔自动检查新帖子。")
        self.set_home_feedback(f"监控已启动：每 {self.config['poll_seconds']} 秒检查 {len(self.config['accounts'])} 个账号的新帖子。")

    def stop_monitor(self):
        self.stop_event.set()
        self.log("已请求停止监控。")
        self.set_status("已请求停止监控；当前轮询若正在执行会先结束。")
        self.set_home_feedback("监控停止请求已发送。已有预警会保留在列表中。")

    def poll_now(self):
        if not self.save_settings(require_x=True):
            self.set_home_feedback("立即轮询失败：请先补齐必填设置。")
            return
        worker = MonitorWorker(self.config, self.store, self.outbox, threading.Event(), force_readd_inactive=True)
        threading.Thread(target=worker.poll_once, daemon=True).start()
        self.set_status("已发起一次立即轮询；回收站中已移除的同帖内容也会重新添加。")
        self.set_home_feedback("已发起立即轮询：正在请求 X API，已进回收站且不在活动列表的同帖内容会重新添加。")

    def add_demo_alert(self):
        demo = Post(
            post_id=f"demo-{int(time.time())}",
            account="demo",
            created_at=now_iso(),
            text=(
                "We are considering major new tariffs on imported chips and autos, "
                "especially from China and Mexico. A decision could come soon."
            ),
            url="https://x.com/",
            raw={"demo": True},
        )
        analyzer = build_analyzer(self.config)
        analysis = analyzer.analyze(demo.text, demo.account)
        self.store.add_post_and_alert(demo, analysis)
        self.refresh_alerts()
        self.select_latest_alert()
        self.log("已添加演示预警。")
        self.set_status("已添加演示预警，并在列表中选中最新结果。")
        self.set_home_feedback("演示预警已生成：右侧展示了事件摘要和股票/ETF 判断。")

    def analyze_pasted_post(self):
        if not self.save_settings():
            return
        text = self.paste_text.get("1.0", END).strip()
        if not text:
            self.set_status("分析失败：请先粘贴帖子正文。")
            messagebox.showerror("缺少正文", "请先粘贴要分析的帖子正文。")
            return
        account = clean_account(self.paste_account_var.get()) or "manual"
        url = self.paste_url_var.get().strip()
        post = Post(
            post_id=f"manual-{int(time.time() * 1000)}",
            account=account,
            created_at=now_iso(),
            text=text,
            url=url,
            raw={"manual": True, "source_url": url},
        )
        analyzer = build_analyzer(self.config)
        analysis = analyzer.analyze(post.text, post.account)
        if not analysis.get("source", "").startswith("manual_"):
            analysis["source"] = f"manual_{analysis.get('source', 'analysis')}"
        self.store.add_post_and_alert(post, analysis, bucket="new")
        self.refresh_alerts()
        self.select_latest_alert()
        self.notebook.select(self.monitor_tab)
        self.log("已分析粘贴内容并加入预警列表。")
        self.set_status("粘贴内容已分析完成，结果已加入实时预警并选中。")
        self.set_home_feedback("粘贴内容已分析完成：已加入实时预警列表并选中。")

    def clear_paste_form(self):
        self.paste_account_var.set("manual")
        self.paste_url_var.set("")
        self.paste_text.delete("1.0", END)
        self.set_status("粘贴分析表单已清空。")

    def refresh_alerts_with_feedback(self):
        self.refresh_alerts()
        self.set_status(f"预警列表已刷新：当前活动内容显示 {self.active_display_count} 条，回收站不计入。")
        self.set_home_feedback(f"预警列表已刷新：当前活动内容显示 {self.active_display_count} 条，回收站内容不计入该数字。")

    def refresh_alerts(self):
        new_alerts = self.store.latest_alerts(200, bucket="new")
        self._fill_alert_tree(self.alert_tree, new_alerts)
        self.active_display_count = len(new_alerts)
        if hasattr(self, "past_tree"):
            past_alerts = self.store.latest_alerts(300, bucket="past_day")
            self._fill_alert_tree(self.past_tree, past_alerts)
            self.active_display_count += len(past_alerts)
            self._fill_alert_tree(self.favorite_tree, self.store.latest_alerts(300, favorite=True))
            self._fill_alert_tree(self.recycle_tree, self.store.latest_alerts(300, status="deleted"))

    def _fill_alert_tree(self, tree, alerts):
        tree.delete(*tree.get_children())
        if tree is self.alert_tree:
            self.alert_rows.clear()
        for alert in alerts:
            values = (
                self._display_time(alert.get("created_at")),
                f"@{alert.get('account', '')}",
                alert.get("category", ""),
                alert.get("severity", ""),
                f"{float(alert.get('confidence') or 0):.2f}",
                ("★ " if alert.get("favorite") else "") + alert.get("headline", ""),
            )
            row_id = str(alert["id"])
            tags = []
            analysis = alert.get("analysis", {})
            if analysis.get("filtered_by_settings"):
                tags.append("filtered_by_settings")
            tree.insert("", END, iid=row_id, values=values, tags=tuple(tags))
            self.alert_rows[row_id] = alert

    def _selected_ids(self, tree):
        return [int(item) for item in tree.selection()]

    def select_alert_from_tree(self, tree):
        selected = tree.selection()
        if not selected:
            return
        row_id = selected[0]
        if row_id not in self.alert_rows:
            self.refresh_alerts()
        if row_id in self.alert_rows:
            alert = self.alert_rows[row_id]
            detail_text = self.secondary_detail_texts.get(tree)
            ticker_tree = self.secondary_ticker_trees.get(tree)
            if detail_text and ticker_tree:
                self.selected_alert = alert
                self.display_alert_in_widgets(alert, detail_text, ticker_tree)
            else:
                self.display_alert(alert)

    def trash_from_tree(self, tree):
        ids = self._selected_ids(tree)
        if not ids:
            messagebox.showinfo("没有选中内容", "请先选择要移入回收站的内容。")
            return
        count = self.store.move_alert_ids_to_trash(ids)
        self.refresh_alerts()
        self.set_home_feedback(f"已将 {count} 条内容移入回收站，可在回收站恢复。")

    def favorite_from_tree(self, tree, favorite=True):
        ids = self._selected_ids(tree)
        if not ids:
            messagebox.showinfo("没有选中内容", "请先选择要操作的内容。")
            return
        count = self.store.set_favorite(ids, favorite=favorite)
        self.refresh_alerts()
        self.set_home_feedback(("已收藏 " if favorite else "已取消收藏 ") + f"{count} 条内容。")

    def restore_from_recycle(self):
        ids = self._selected_ids(self.recycle_tree)
        if not ids:
            messagebox.showinfo("没有选中内容", "请先选择要恢复的内容。")
            return
        count = self.store.restore_alert_ids(ids)
        self.refresh_alerts()
        self.set_home_feedback(f"已从回收站恢复 {count} 条内容。")

    def permanent_delete_from_recycle(self):
        ids = self._selected_ids(self.recycle_tree)
        if not ids:
            messagebox.showinfo("没有选中内容", "请先选择要永久删除的内容。")
            return
        if not messagebox.askyesno("确认永久删除", f"确定永久删除 {len(ids)} 条内容吗？此操作无法恢复。"):
            return
        count = self.store.delete_alert_ids(ids)
        self.refresh_alerts()
        self.set_home_feedback(f"已永久删除 {count} 条内容。")

    def toggle_selected_favorite(self):
        ids = self._selected_ids(self.alert_tree)
        if not ids:
            messagebox.showinfo("没有选中内容", "请先选择要收藏的内容。")
            return
        count = self.store.set_favorite(ids, favorite=True)
        self.refresh_alerts()
        self.set_home_feedback(f"已收藏 {count} 条内容，可在收藏夹查看。")

    def _old_refresh_alerts_unused(self):
        self.alert_tree.delete(*self.alert_tree.get_children())
        self.alert_rows.clear()
        for alert in self.store.latest_alerts(200):
            values = (
                self._display_time(alert.get("created_at")),
                f"@{alert.get('account', '')}",
                alert.get("category", ""),
                alert.get("severity", ""),
                f"{float(alert.get('confidence') or 0):.2f}",
                alert.get("headline", ""),
            )
            row_id = str(alert["id"])
            severity = int(alert.get("severity") or 0)
            if severity >= 4:
                tag = "severity_high"
            elif severity >= 2:
                tag = "severity_medium"
            else:
                tag = "severity_low"
            self.alert_tree.insert("", END, iid=row_id, values=values, tags=(tag,))
            self.alert_rows[row_id] = alert

    def select_latest_alert(self):
        children = self.alert_tree.get_children()
        if not children:
            return
        latest = children[0]
        self.alert_tree.selection_set(latest)
        self.alert_tree.focus(latest)
        self.alert_tree.see(latest)
        self.on_alert_select()

    def delete_selected_alerts(self):
        selected = self.alert_tree.selection()
        if not selected:
            self.set_status("删除失败：请先选中一条或多条预警。")
            messagebox.showinfo("没有选中预警", "请先在实时预警列表中选中要删除的预警。")
            return
        count = len(selected)
        if not messagebox.askyesno("确认删除", f"确定删除选中的 {count} 条预警吗？"):
            self.set_status("已取消删除选中预警。")
            return
        deleted = self.store.move_alert_ids_to_trash(selected)
        self.refresh_alerts()
        self.clear_alert_detail()
        self.log(f"已将 {deleted} 条选中预警移入回收站。")
        self.set_status(f"已将 {deleted} 条选中预警移入回收站，可恢复。")

    def open_delete_dialog(self):
        dialog = Toplevel(self.root)
        dialog.title("自定义删除预警")
        dialog.geometry("430x300")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        account_var = StringVar(value="")
        category_var = StringVar(value="")
        severity_var = StringVar(value="")
        manual_var = BooleanVar(value=False)

        body = ttk.Frame(dialog, padding=14)
        body.pack(fill=BOTH, expand=True)

        ttk.Label(body, text="账号/来源包含").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(body, textvariable=account_var, width=32).grid(row=0, column=1, sticky="we", pady=6, padx=(8, 0))

        ttk.Label(body, text="类别包含").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(body, textvariable=category_var, width=32).grid(row=1, column=1, sticky="we", pady=6, padx=(8, 0))

        ttk.Label(body, text="删除级别小于等于").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(body, textvariable=severity_var, width=10).grid(row=2, column=1, sticky="w", pady=6, padx=(8, 0))

        ttk.Checkbutton(body, text="只删除粘贴分析产生的预警", variable=manual_var).grid(row=3, column=1, sticky="w", pady=6, padx=(8, 0))

        note = (
            "留空代表不限制该条件。所有条件都留空会删除全部预警，"
            "程序会再次要求确认。删除只影响预警历史，不会删除配置。"
        )
        ttk.Label(body, text=note, style="Warning.TLabel", wraplength=380).grid(row=4, column=0, columnspan=2, sticky="we", pady=(10, 8))

        buttons = ttk.Frame(body)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=(8, 0))
        self._button(buttons, "取消", dialog.destroy, "关闭自定义删除", "关闭窗口，不删除任何预警。").pack(side=RIGHT, padx=(6, 0))
        self._button(
            buttons,
            "删除匹配预警",
            lambda: self.delete_alerts_by_dialog(dialog, account_var, category_var, severity_var, manual_var),
            "删除匹配预警",
            "按当前条件批量删除本地预警历史；删除前会再次确认。",
            "Danger.TButton",
        ).pack(side=RIGHT)

    def delete_alerts_by_dialog(self, dialog, account_var, category_var, severity_var, manual_var):
        max_severity = severity_var.get().strip()
        if max_severity:
            try:
                value = int(max_severity)
            except ValueError:
                self.set_status("自定义删除失败：级别必须是 1 到 5 的整数。")
                messagebox.showerror("级别错误", "级别必须是 1 到 5 的整数。")
                return
            if value < 1 or value > 5:
                self.set_status("自定义删除失败：级别必须在 1 到 5 之间。")
                messagebox.showerror("级别错误", "级别必须是 1 到 5 的整数。")
                return

        account = account_var.get().strip()
        category = category_var.get().strip()
        manual_only = bool(manual_var.get())
        has_filter = bool(account or category or max_severity or manual_only)
        if has_filter:
            prompt = "确定删除所有匹配条件的预警吗？"
        else:
            prompt = "没有设置任何过滤条件，这会删除全部预警。确定继续吗？"
        if not messagebox.askyesno("确认删除", prompt):
            self.set_status("已取消自定义删除。")
            return

        deleted = self.store.delete_alerts_matching(
            account=account,
            category=category,
            max_severity=max_severity,
            manual_only=manual_only,
        )
        self.refresh_alerts()
        self.clear_alert_detail()
        dialog.destroy()
        self.log(f"自定义删除完成，已将 {deleted} 条预警移入回收站。")
        self.set_status(f"自定义删除完成：已将 {deleted} 条预警移入回收站。")

    def clear_alert_detail(self):
        self.selected_alert = None
        self.detail_text.delete("1.0", END)
        self.ticker_tree.delete(*self.ticker_tree.get_children())

    def on_alert_select(self, _event=None):
        selected = self.alert_tree.selection()
        if not selected:
            return
        alert = self.alert_rows.get(selected[0])
        if not alert:
            return
        self.display_alert(alert)

    def display_alert(self, alert):
        self.selected_alert = alert
        self.display_alert_in_widgets(alert, self.detail_text, self.ticker_tree)
        self.set_status(f"已选中预警：@{alert.get('account', '')} / {alert.get('category', '')}")
        return
        analysis = alert["analysis"]
        self.detail_text.delete("1.0", END)
        detail = (
            f"标题: {analysis.get('headline', '')}\n"
            f"类别: {analysis.get('category', '')}  级别: {analysis.get('severity', '')}  "
            f"置信度: {float(analysis.get('confidence') or 0):.2f}\n"
            f"时间跨度: {analysis.get('time_horizon', '')}  新颖度: {analysis.get('novelty', '')}\n"
            f"来源: {analysis.get('source', '')}\n\n"
            f"{analysis.get('summary', '')}\n\n"
            f"风险提示: {analysis.get('risk_note', '')}"
        )
        self.detail_text.insert("1.0", detail)
        self.set_status(f"已选中预警：@{alert.get('account', '')} / {alert.get('category', '')}")

        self.ticker_tree.delete(*self.ticker_tree.get_children())
        for ticker in analysis.get("tickers", []):
            direction = ticker.get("direction", "")
            self.ticker_tree.insert(
                "",
                END,
                values=(
                    ticker.get("symbol", ""),
                    direction,
                    ticker.get("asset_class", ""),
                    ticker.get("reason", ""),
                ),
                tags=(direction if direction in {"bullish", "bearish", "mixed"} else "",),
            )

    def display_alert_in_widgets(self, alert, detail_text, ticker_tree):
        analysis = alert["analysis"]
        detail_text.delete("1.0", END)
        filter_line = ""
        if analysis.get("filtered_by_settings"):
            filter_line = f"内容标记: 原设置会筛选掉的{analysis.get('filter_note', '')}，已保留展示。\n"
        elif analysis.get("x_content_type"):
            filter_line = f"内容类型: {analysis.get('x_content_type', '')}\n"
        detail = (
            f"{self.analysis_section_title(analysis)}\n"
            f"标题: {analysis.get('headline', '')}\n"
            f"类别: {analysis.get('category', '')}  级别: {analysis.get('severity', '')}  "
            f"置信度: {float(analysis.get('confidence') or 0):.2f}\n"
            f"时间跨度: {analysis.get('time_horizon', '')}  新颖度: {analysis.get('novelty', '')}\n"
            f"来源: {analysis.get('source', '')}\n\n"
            f"{filter_line}"
            f"{analysis.get('summary', '')}"
        )
        detail_text.insert("1.0", detail)

        ticker_tree.delete(*ticker_tree.get_children())
        for ticker in analysis.get("tickers", []):
            direction = ticker.get("direction", "")
            ticker_tree.insert(
                "",
                END,
                values=(
                    ticker.get("symbol", ""),
                    direction,
                    ticker.get("asset_class", ""),
                    ticker.get("reason", ""),
                ),
                tags=(direction if direction in {"bullish", "bearish", "mixed"} else "",),
            )
        return
        detail = (
            f"标题: {analysis.get('headline', '')}\n"
            f"类别: {analysis.get('category', '')}  级别: {analysis.get('severity', '')}  "
            f"置信度: {float(analysis.get('confidence') or 0):.2f}\n"
            f"时间跨度: {analysis.get('time_horizon', '')}  新颖度: {analysis.get('novelty', '')}\n"
            f"来源: {analysis.get('source', '')}\n\n"
            f"{analysis.get('summary', '')}\n\n"
            f"风险提示: {analysis.get('risk_note', '')}"
        )
        detail_text.insert("1.0", detail)

        ticker_tree.delete(*ticker_tree.get_children())
        for ticker in analysis.get("tickers", []):
            direction = ticker.get("direction", "")
            ticker_tree.insert(
                "",
                END,
                values=(
                    ticker.get("symbol", ""),
                    direction,
                    ticker.get("asset_class", ""),
                    ticker.get("reason", ""),
                ),
                tags=(direction if direction in {"bullish", "bearish", "mixed"} else "",),
            )

    @staticmethod
    def analysis_section_title(analysis):
        source = str(analysis.get("source", ""))
        if analysis.get("filtered_by_settings"):
            return "【原筛选内容 - 已保留展示】"
        if source.startswith("ai_") or source.startswith("reanalyzed_ai_") or "_ai_" in source:
            return "【AI 分析结果】"
        if source.startswith("manual_"):
            return "【粘贴内容分析】"
        return "【本地规则分析】"

    def open_source(self):
        if not self.selected_alert:
            self.set_status("没有可打开的原帖：请先选中一条预警。")
            return
        url = self.selected_alert.get("source_url")
        if url:
            webbrowser.open(url)
            self.set_status("已在浏览器中打开原帖/来源链接。")
        else:
            self.set_status("当前预警没有原帖链接。")

    def open_trade_link_from_ticker_tree(self, ticker_tree):
        selected = ticker_tree.selection()
        if not selected:
            children = ticker_tree.get_children()
            if not children:
                self.set_status("没有可打开的股票/ETF：请先选中预警或代码。")
                return
            selected = [children[0]]
        symbol = ticker_tree.item(selected[0], "values")[0]
        if not symbol:
            self.set_status("没有可打开的股票/ETF 代码。")
            return
        url = trade_link(symbol, self.config.get("trade_link_template", DEFAULT_CONFIG["trade_link_template"]))
        webbrowser.open(url)
        self.set_status(f"已打开 {symbol} 的交易/看盘链接。")

    def open_selected_trade_link(self):
        selected = self.ticker_tree.selection()
        if not selected:
            children = self.ticker_tree.get_children()
            if not children:
                self.set_status("没有可打开的股票/ETF：请先选中预警或代码。")
                return
            selected = [children[0]]
        symbol = self.ticker_tree.item(selected[0], "values")[0]
        if not symbol:
            self.set_status("没有可打开的股票/ETF 代码。")
            return
        url = trade_link(symbol, self.config.get("trade_link_template", DEFAULT_CONFIG["trade_link_template"]))
        webbrowser.open(url)
        self.set_status(f"已打开 {symbol} 的交易/看盘链接。")

    def open_config_dir(self):
        ensure_app_dir()
        webbrowser.open(str(APP_DIR))
        self.set_status("已打开配置目录。")

    def _process_outbox(self):
        try:
            while True:
                kind, payload = self.outbox.get_nowait()
                if kind == "log":
                    self.log(payload)
                    self.set_status(payload)
                elif kind == "alert":
                    self.refresh_alerts()
                    self.select_latest_alert()
                    self.set_status("发现新帖子并已生成预警。")
                elif kind == "reanalysis_done":
                    self.reanalysis_running = False
                    self._stop_ai_window_timer()
                    if self.ai_window_status_var is not None:
                        self.ai_window_status_var.set(f"完成：{payload['provider']} / {payload['model']} 已生成分析。")
                    if hasattr(self, "reanalyze_button"):
                        self.reanalyze_button.configure(state="normal")
                    self.refresh_alerts()
                    row_id = str(payload["alert_id"])
                    if row_id in self.alert_rows:
                        self.selected_alert = self.alert_rows[row_id]
                        if row_id in self.alert_tree.get_children():
                            self.alert_tree.selection_set(row_id)
                            self.alert_tree.focus(row_id)
                            self.alert_tree.see(row_id)
                            self.on_alert_select()
                        for tree, detail_text in self.secondary_detail_texts.items():
                            if row_id in tree.get_children():
                                tree.selection_set(row_id)
                                tree.focus(row_id)
                                tree.see(row_id)
                                self.display_alert_in_widgets(self.alert_rows[row_id], detail_text, self.secondary_ticker_trees[tree])
                                break
                    message = f"已使用 {payload['provider']} / {payload['model']} 重新生成预警分析。"
                    self.log(message)
                    self.set_status(message)
                    self.set_home_feedback(message)
                elif kind == "reanalysis_error":
                    self.reanalysis_running = False
                    self._stop_ai_window_timer()
                    if self.ai_window_status_var is not None:
                        self.ai_window_status_var.set(f"失败：{payload['provider']} / {payload['model']}。请查看日志或调整超时。")
                    if hasattr(self, "reanalyze_button"):
                        self.reanalyze_button.configure(state="normal")
                    message = f"重新分析失败：{payload['provider']} / {payload['model']} - {payload['error']}"
                    self.log(message)
                    self.set_status(message)
                    self.set_home_feedback(message)
                elif kind == "workflow_start":
                    self.workflow_items[payload["id"]] = {
                        "name": payload.get("name", ""),
                        "status": "运行中",
                        "started": time.time(),
                        "ended": None,
                        "detail": payload.get("detail", ""),
                    }
                    self.refresh_workflow_tree()
                elif kind == "workflow_end":
                    item = self.workflow_items.setdefault(payload["id"], {"name": payload["id"], "started": time.time()})
                    item["status"] = payload.get("status", "完成")
                    item["ended"] = time.time()
                    item["detail"] = payload.get("detail", "")
                    self.refresh_workflow_tree()
        except queue.Empty:
            pass
        self.root.after(500, self._process_outbox)

    def refresh_workflow_tree(self):
        if not hasattr(self, "workflow_tree"):
            return
        self.workflow_tree.delete(*self.workflow_tree.get_children())
        now = time.time()
        for op_id, item in sorted(self.workflow_items.items(), key=lambda pair: pair[1].get("started", 0), reverse=True):
            end = item.get("ended") or now
            elapsed = max(0, end - item.get("started", now))
            self.workflow_tree.insert(
                "",
                END,
                iid=op_id,
                values=(item.get("name", op_id), item.get("status", ""), f"{elapsed:.1f}s", item.get("detail", "")),
            )
        self.root.after(1000, self.refresh_workflow_tree)

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(END, f"[{timestamp}] {message}\n")
        self.log_text.see(END)

    def on_tab_changed(self, _event=None):
        current = self.notebook.tab(self.notebook.select(), "text")
        messages = {
            "新发布内容": "新发布内容：只收录本次运行抓取之后发布的新帖子。",
            "过去一天": "过去一天：展示过去 24 小时内的历史内容。",
            "收藏夹": "收藏夹：整理你标记收藏的重要内容。",
            "回收站": "回收站：恢复误删内容或永久删除。",
            "工作流": "工作流：查看当前操作状态和耗时。",
            "粘贴分析": "粘贴分析：手动粘贴帖子或新闻文本，不消耗 X API credits。",
            "设置": "设置：配置 X token、账号、OpenAI、轮询间隔和交易链接模板。",
            "日志": "日志：查看 API 请求、错误和操作记录。",
        }
        self.set_status(messages.get(current, "就绪"), temporary=False)

    @staticmethod
    def _display_time(value):
        if not value:
            return ""
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return value


def main():
    ensure_app_dir()
    root = Tk()
    app = TradeAlertApp(root)

    def on_close():
        app.stop_event.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
