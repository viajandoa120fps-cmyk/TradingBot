"""
AERO BOT PRO - Dashboard Elite v2.1
Puerto 8051 | Multi-pagina | Top 20 CoinMarketCap
AERO LADDER v2 implementado — apalancamiento dinámico por racha
"""

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import random
import time
import ccxt
from scipy.signal import argrelextrema
import threading
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import bingx as bx
import os

# ─── LINREG CONSTANTS (LazyBear Squeeze kl=20, computed once at import) ──────
_LR_KL = 20
_LR_X = np.arange(_LR_KL, dtype=float) - (_LR_KL - 1) / 2
_LR_XVAR = float((_LR_X ** 2).sum())
_LR_XEND = float(_LR_X[-1])

def _linreg_last(y: np.ndarray) -> float:
    slope = (_LR_X * (y - y.mean())).sum() / _LR_XVAR
    return y.mean() + slope * _LR_XEND

# ─── AERO LADDER v2 — Estado persistente ────────────────────────────────────
_BOT_STATE_FILE = "bot_state.json"
_TRADES_FILE = "trades_history.json"
_MAX_DIAS_CICLO = 30
_MAX_PERDIDAS_RESET = 2
_MAX_COOLDOWN_HORAS = 24
_MAX_EXPOSICION_PCT = 50.0

def _load_bot_state():
    default = {
        "racha_ganadora": 0,
        "apalancamiento_actual": 2,
        "profit_lock_acumulado": 0.0,
        "ultimo_trade_resultado": None,
        "ultimo_trade_timestamp": None,
        "perdidas_consecutivas_nivel_actual": 0,
        "cooldown_hasta": None,
        "ciclo_inicio": datetime.now().isoformat(),
        "version": "aero-ladder-v2",
    }
    try:
        with open(_BOT_STATE_FILE) as f:
            state = json.load(f)
        # Reset si pasaron 30 días
        try:
            ciclo = datetime.fromisoformat(state.get("ciclo_inicio", datetime.now().isoformat()))
            if (datetime.now() - ciclo).days >= _MAX_DIAS_CICLO:
                print("[🔄 CICLO RESET] 30 días transcurridos. Nuevo ciclo AERO LADDER.")
                return default
        except Exception:
            pass
        # Reset si racha llegó a 0 con 2 pérdidas seguidas
        if state.get("racha_ganadora", 0) == 0 and state.get("perdidas_consecutivas_nivel_actual", 0) >= _MAX_PERDIDAS_RESET:
            print("[🔄 CICLO RESET] Racha perdida. Nuevo ciclo AERO LADDER.")
            return default
        return state
    except Exception:
        return default

def _save_bot_state(state):
    try:
        with open(_BOT_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        print(f"[⚠ bot_state] Error guardando: {e}")

def _calcular_apalancamiento(state):
    """AERO LADDER v2: devuelve apalancamiento basado en racha global."""
    # Check cooldown activo
    cd_hasta = state.get("cooldown_hasta")
    if cd_hasta:
        try:
            cd = datetime.fromisoformat(cd_hasta)
            if datetime.now() < cd:
                return 2
        except Exception:
            pass
        state["cooldown_hasta"] = None

    racha = state.get("racha_ganadora", 0)
    if racha <= 1:
        return 2
    elif racha <= 3:
        return 3
    elif racha <= 5:
        return 4
    else:
        return 5

def _actualizar_racha(state, pnl_pct, apalancamiento_usado, capital_total):
    """Actualiza estado tras cierre de posición. pnl_pct es P&L bruto sobre capital expuesto."""
    es_ganador = pnl_pct > 0
    state["ultimo_trade_timestamp"] = datetime.now().isoformat()

    if es_ganador:
        state["racha_ganadora"] = state.get("racha_ganadora", 0) + 1
        state["perdidas_consecutivas_nivel_actual"] = 0
        state["ultimo_trade_resultado"] = "ganador"

        # Profit lock al subir de nivel
        nuevo_apal = _calcular_apalancamiento(state)
        anterior_apal = state.get("apalancamiento_actual", 2)
        if nuevo_apal > anterior_apal:
            profit_congelar = (abs(pnl_pct) / 100) * capital_total * 0.5
            state["profit_lock_acumulado"] = state.get("profit_lock_acumulado", 0.0) + profit_congelar
            print(f"[🔒 Profit Lock] +${profit_congelar:.2f} congelado al subir a {nuevo_apal}X")

        state["apalancamiento_actual"] = nuevo_apal
        print(f"[📈 AERO LADDER] Ganador — Racha: {state['racha_ganadora']} | Apalancamiento: {nuevo_apal}X")

    else:
        state["ultimo_trade_resultado"] = "perdedor"
        state["perdidas_consecutivas_nivel_actual"] = state.get("perdidas_consecutivas_nivel_actual", 0) + 1
        state["racha_ganadora"] = 0

        # Descenso suave: bajar 1 nivel
        apal_actual = state.get("apalancamiento_actual", 2)
        if apal_actual > 2:
            state["apalancamiento_actual"] = apal_actual - 1
        else:
            state["apalancamiento_actual"] = 2

        print(f"[📉 AERO LADDER] Perdedor — Descenso a {state['apalancamiento_actual']}X | "
              f"Pérdidas seguidas en nivel: {state['perdidas_consecutivas_nivel_actual']}")

        # Reset completo tras 2 pérdidas seguidas
        if state["perdidas_consecutivas_nivel_actual"] >= _MAX_PERDIDAS_RESET:
            state["apalancamiento_actual"] = 2
            state["perdidas_consecutivas_nivel_actual"] = 0
            state["profit_lock_acumulado"] = 0.0
            print("[🔄 RESET AERO LADDER] 2 pérdidas seguidas en mismo nivel. Vuelta a 2X.")

        # Cooldown 24h si pérdida en 5X > 2% del capital total
        if apalancamiento_usado >= 5 and abs(pnl_pct) >= 2.0:
            state["cooldown_hasta"] = (datetime.now() + timedelta(hours=_MAX_COOLDOWN_HORAS)).isoformat()
            print(f"[❄️ COOLDOWN] 24h en 2X por pérdida grande ({abs(pnl_pct):.2f}%) en 5X.")

    _save_bot_state(state)
    return state

def _registrar_trade(trade_dict):
    """Persiste un trade en trades_history.json (máximo 200 registros)."""
    try:
        trades = []
        if os.path.exists(_TRADES_FILE):
            with open(_TRADES_FILE) as f:
                trades = json.load(f)
        trades.insert(0, trade_dict)
        trades = trades[:200]
        with open(_TRADES_FILE, "w") as f:
            json.dump(trades, f, indent=2, default=str)
    except Exception as e:
        print(f"[⚠ trades_history] Error: {e}")

def _calcular_exposicion_total(posicion, precio_entrada, capital_usado):
    """Suma el notional de todas las posiciones abiertas."""
    total = 0.0
    for a, side in posicion.items():
        if side and capital_usado.get(a):
            total += capital_usado[a]
    return total

# ─── TELEGRAM STATE (set once when bot starts) ────────────────────────────────
_tg_token: str = ""
_tg_chatid: str = ""

# ─── CREDENCIALES BINGX (cargadas al iniciar el proceso, disponibles siempre) ─
_bx_api_key: str = ""
_bx_api_secret: str = ""
try:
    with open("config.json") as _f_ini:
        _ini_cfg = json.load(_f_ini)
    _bx_api_key = str(_ini_cfg.get("api_key", ""))
    _bx_api_secret = str(_ini_cfg.get("api_secret", ""))
except Exception:
    pass

# ─── TRADUCCIONES ─────────────────────────────────────────────────────────────

TRANSLATIONS = {
    "es": {
        "title": "AERO BOT PRO", "subtitle": "Trading Bot Profesional",
        "connected": "CONECTADO", "disconnected": "DESCONECTADO",
        "language": "Idioma", "timeframe": "Temporalidad",
        "assets": "Cripto BingX (max. 6)", "capital": "Capital por Op.",
        "score": "PUNTUACIÓN GLOBAL",
        "long": "LARGO", "short": "CORTO", "wait": "ESPERAR",
        "stats": "Estadísticas en Tiempo Real", "guardrails": "Guardarrailes",
        "start": "INICIAR BOT", "stop": "DETENER BOT",
        "detail": "↗ Ver Detalle", "back": "← Inicio",
    },
    "en": {
        "title": "AERO BOT PRO", "subtitle": "Professional Trading Bot",
        "connected": "CONNECTED", "disconnected": "DISCONNECTED",
        "language": "Language", "timeframe": "Timeframe",
        "assets": "Crypto BingX (max. 6)", "capital": "Capital per Op.",
        "score": "GLOBAL SCORE",
        "long": "LONG", "short": "SHORT", "wait": "WAIT",
        "stats": "Real-Time Statistics", "guardrails": "Guardrails",
        "start": "START BOT", "stop": "STOP BOT",
        "detail": "↗ Detail View", "back": "← Home",
    },
    "it": {
        "title": "AERO BOT PRO", "subtitle": "Bot di Trading Professionale",
        "connected": "CONNESSO", "disconnected": "DISCONNESSO",
        "language": "Lingua", "timeframe": "Temporalità",
        "assets": "Cripto BingX (max. 6)", "capital": "Capitale per Op.",
        "score": "PUNTEGGIO GLOBALE",
        "long": "LUNGO", "short": "CORTO", "wait": "ATTENDI",
        "stats": "Statistiche in Tempo Reale", "guardrails": "Guardrail",
        "start": "AVVIA BOT", "stop": "FERMA BOT",
        "detail": "↗ Dettaglio", "back": "← Home",
    },
    "fr": {
        "title": "AERO BOT PRO", "subtitle": "Bot de Trading Professionnel",
        "connected": "CONNECTÉ", "disconnected": "DÉCONNECTÉ",
        "language": "Langue", "timeframe": "Temporalité",
        "assets": "Crypto BingX (max. 6)", "capital": "Capital par Op.",
        "score": "SCORE GLOBAL",
        "long": "LONG", "short": "COURT", "wait": "ATTENDRE",
        "stats": "Statistiques en Temps Réel", "guardrails": "Garde-fous",
        "start": "DÉMARRER BOT", "stop": "ARRÊTER BOT",
        "detail": "↗ Détail", "back": "← Accueil",
    },
    "de": {
        "title": "AERO BOT PRO", "subtitle": "Professioneller Trading Bot",
        "connected": "VERBUNDEN", "disconnected": "GETRENNT",
        "language": "Sprache", "timeframe": "Zeitrahmen",
        "assets": "Krypto BingX (max. 6)", "capital": "Kapital pro Op.",
        "score": "GESAMTPUNKTZAHL",
        "long": "LONG", "short": "SHORT", "wait": "WARTEN",
        "stats": "Echtzeit-Statistiken", "guardrails": "Leitplanken",
        "start": "BOT STARTEN", "stop": "BOT STOPPEN",
        "detail": "↗ Details", "back": "← Start",
    },
    "zh": {
        "title": "AERO BOT PRO", "subtitle": "专业交易机器人",
        "connected": "已连接", "disconnected": "未连接",
        "language": "语言", "timeframe": "时间框架",
        "assets": "加密货币 BingX（最多6个）", "capital": "每次资金",
        "score": "综合评分",
        "long": "做多", "short": "做空", "wait": "等待",
        "stats": "实时统计", "guardrails": "防护栏",
        "start": "启动机器人", "stop": "停止机器人",
        "detail": "↗ 详情", "back": "← 首页",
    },
    "ko": {
        "title": "AERO BOT PRO", "subtitle": "전문 트레이딩 봇",
        "connected": "연결됨", "disconnected": "연결 안됨",
        "language": "언어", "timeframe": "시간대",
        "assets": "암호화폐 BingX (최대 6개)", "capital": "거래당 자본",
        "score": "종합 점수",
        "long": "롱", "short": "숏", "wait": "대기",
        "stats": "실시간 통계", "guardrails": "가드레일",
        "start": "봇 시작", "stop": "봇 중지",
        "detail": "↗ 상세보기", "back": "← 홈",
    },
    "ja": {
        "title": "AERO BOT PRO", "subtitle": "プロトレーディングボット",
        "connected": "接続済み", "disconnected": "未接続",
        "language": "言語", "timeframe": "時間軸",
        "assets": "暗号資産 BingX（最大6個）", "capital": "取引資金",
        "score": "総合スコア",
        "long": "ロング", "short": "ショート", "wait": "待機",
        "stats": "リアルタイム統計", "guardrails": "ガードレール",
        "start": "ボット起動", "stop": "ボット停止",
        "detail": "↗ 詳細", "back": "← ホーム",
    },
}

QUOTES = {
    "es": [
        ("No operes nunca el mercado por aburrimiento.", "Eduardo Andrade"),
        ("Si hay problemas familiares, tómate una pausa y no operes.", "Eduardo Andrade"),
        ("La venganza no existe en el trading.", "Eduardo Andrade"),
        ("Jamás operes bajo los estímulos del alcohol o de alguna otra droga.", "Eduardo Andrade"),
        ("La paciencia paga y la desesperación pega.", "Eduardo Andrade"),
        ("Jamás te sientas ansioso si el precio se te escapa, el mercado es una marea infinita de oportunidades.", "Eduardo Andrade"),
        ("Nunca juegues a improvisar, apégate 100% a tu estrategia y sé fiel a ella.", "Eduardo Andrade"),
        ("El mercado recompensa la paciencia, no la prisa.", "Jesse Livermore"),
        ("Corta tus pérdidas y deja correr tus ganancias.", "Paul Tudor Jones"),
        ("El riesgo viene de no saber lo que estás haciendo.", "Warren Buffett"),
    ],
    "en": [
        ("Never trade the market out of boredom.", "Eduardo Andrade"),
        ("If you have family problems, take a break and don't trade.", "Eduardo Andrade"),
        ("Revenge does not exist in trading.", "Eduardo Andrade"),
        ("Never trade under the influence of alcohol or any other drug.", "Eduardo Andrade"),
        ("Patience pays and desperation hurts.", "Eduardo Andrade"),
        ("Never feel anxious if the price escapes you, the market is an infinite tide of opportunities.", "Eduardo Andrade"),
        ("Never improvise, stick 100% to your strategy and be faithful to it.", "Eduardo Andrade"),
        ("The market rewards patience, not haste.", "Jesse Livermore"),
        ("Cut your losses and let your profits run.", "Paul Tudor Jones"),
        ("Risk comes from not knowing what you are doing.", "Warren Buffett"),
    ],
    "it": [
        ("Non fare mai trading per noia.", "Eduardo Andrade"),
        ("Se hai problemi familiari, prenditi una pausa e non operare.", "Eduardo Andrade"),
        ("La vendetta non esiste nel trading.", "Eduardo Andrade"),
        ("Non operare mai sotto l'influenza di alcol o altre droghe.", "Eduardo Andrade"),
        ("La pazienza paga e la disperazione colpisce.", "Eduardo Andrade"),
        ("Non sentirti mai ansioso se il prezzo ti sfugge.", "Eduardo Andrade"),
        ("Non improvvisare mai, attieniti al 100% alla tua strategia.", "Eduardo Andrade"),
        ("Il mercato premia la pazienza, non la fretta.", "Jesse Livermore"),
        ("Taglia le perdite e lascia correre i profitti.", "Paul Tudor Jones"),
        ("Il rischio deriva dal non sapere cosa stai facendo.", "Warren Buffett"),
    ],
    "fr": [
        ("Ne tradez jamais par ennui.", "Eduardo Andrade"),
        ("Faites une pause si vous avez des problèmes familiaux.", "Eduardo Andrade"),
        ("La vengeance n'existe pas dans le trading.", "Eduardo Andrade"),
        ("Ne tradez jamais sous l'influence de l'alcool.", "Eduardo Andrade"),
        ("La patience paie et le désespoir fait mal.", "Eduardo Andrade"),
        ("Le marché est une marée infinie d'opportunités.", "Eduardo Andrade"),
        ("Respectez 100% votre stratégie, sans improviser.", "Eduardo Andrade"),
        ("Le marché récompense la patience, pas la hâte.", "Jesse Livermore"),
        ("Coupez vos pertes et laissez courir vos profits.", "Paul Tudor Jones"),
        ("Le risque vient de ne pas savoir ce que vous faites.", "Warren Buffett"),
    ],
    "de": [
        ("Handle nie aus Langeweile.", "Eduardo Andrade"),
        ("Bei Familienproblemen mach eine Pause und handle nicht.", "Eduardo Andrade"),
        ("Rache existiert im Trading nicht.", "Eduardo Andrade"),
        ("Handle nie unter Alkohol- oder Drogeneinfluss.", "Eduardo Andrade"),
        ("Geduld zahlt sich aus, Verzweiflung schadet.", "Eduardo Andrade"),
        ("Der Markt ist eine unendliche Flut von Chancen.", "Eduardo Andrade"),
        ("Halte dich 100% an deine Strategie, niemals improvisieren.", "Eduardo Andrade"),
        ("Der Markt belohnt Geduld, nicht Eile.", "Jesse Livermore"),
        ("Kurze deine Verluste und lass deine Gewinne laufen.", "Paul Tudor Jones"),
        ("Risiko entsteht durch Unwissenheit.", "Warren Buffett"),
    ],
    "zh": [
        ("永远不要因为无聊而交易。", "Eduardo Andrade"),
        ("如果有家庭问题，休息一下，不要交易。", "Eduardo Andrade"),
        ("交易中没有复仇。", "Eduardo Andrade"),
        ("永远不要在酒精或其他药物影响下交易。", "Eduardo Andrade"),
        ("耐心有回报，绝望有代价。", "Eduardo Andrade"),
        ("如果价格错过了也不要焦虑，市场是无限机会的潮流。", "Eduardo Andrade"),
        ("永远不要即兴发挥，100%坚守你的策略。", "Eduardo Andrade"),
        ("市场奖励耐心，而非仓促。", "Jesse Livermore"),
        ("截断亏损，让利润奔跑。", "Paul Tudor Jones"),
        ("风险来自于不知道自己在做什么。", "Warren Buffett"),
    ],
    "ko": [
        ("지루함으로 시장을 거래하지 마세요.", "Eduardo Andrade"),
        ("가족 문제가 있다면 휴식을 취하고 거래하지 마세요.", "Eduardo Andrade"),
        ("트레이딩에는 복수가 없습니다.", "Eduardo Andrade"),
        ("술이나 다른 약물의 영향 아래 절대 거래하지 마세요.", "Eduardo Andrade"),
        ("인내는 보상을 주고 절망은 상처를 줍니다.", "Eduardo Andrade"),
        ("가격이 도망가도 불안해하지 마세요, 시장은 무한한 기회의 물결입니다.", "Eduardo Andrade"),
        ("절대 즉흥적으로 하지 말고 전략에 100% 충실하세요.", "Eduardo Andrade"),
        ("시장은 인내를 보상하고 서두름을 벌합니다.", "Jesse Livermore"),
        ("손실은 줄이고 수익은 키우세요.", "Paul Tudor Jones"),
        ("위험은 자신이 무엇을 하는지 모르는 것에서 옵니다.", "Warren Buffett"),
    ],
    "ja": [
        ("退屈でマーケットを取引してはいけません。", "Eduardo Andrade"),
        ("家族の問題があれば、休んで取引しないでください。", "Eduardo Andrade"),
        ("トレーディングに復讐は存在しません。", "Eduardo Andrade"),
        ("アルコールや他の薬物の影響下では絶対に取引しないでください。", "Eduardo Andrade"),
        ("忍耐は報われ、焦りは傷つきます。", "Eduardo Andrade"),
        ("価格が逃げても不安にならないでください、市場は無限のチャンスの波です。", "Eduardo Andrade"),
        ("即興で動かず、戦略に100%忠実でいてください。", "Eduardo Andrade"),
        ("市場は忍耐を報い、急ぎを罰します。", "Jesse Livermore"),
        ("損失を切り、利益を伸ばしてください。", "Paul Tudor Jones"),
        ("リスクは自分が何をしているかを知らないことから来ます。", "Warren Buffett"),
    ],
}

# ─── ACTIVOS TOP 20 CMC ───────────────────────────────────────────────────────

SYMBOL_MAP = {
    "BTC": "BTC/USDT",
    "ETH": "ETH/USDT",
    "BNB": "BNB/USDT",
    "XRP": "XRP/USDT",
    "SOL": "SOL/USDT",
    "TRX": "TRX/USDT",
    "DOGE": "DOGE/USDT",
    "ADA": "ADA/USDT",
    "BCH": "BCH/USDT",
    "LINK": "LINK/USDT",
    "TON": "TON/USDT",
    "XLM": "XLM/USDT",
    "SUI": "SUI/USDT",
    "LTC": "LTC/USDT",
    "AVAX": "AVAX/USDT",
    "HBAR": "HBAR/USDT",
    "SHIB": "SHIB/USDT",
    "DOT": "DOT/USDT",
    "NEAR": "NEAR/USDT",
    "ARB": "ARB/USDT",
}

# Checklist: top 20 incluyendo BTC
ACTIVOS_GRID = [
    ("BTC", "BTC/USDT"),
    ("ETH", "ETH/USDT"), ("BNB", "BNB/USDT"), ("XRP", "XRP/USDT"),
    ("SOL", "SOL/USDT"), ("TRX", "TRX/USDT"), ("DOGE", "DOGE/USDT"),
    ("ADA", "ADA/USDT"), ("BCH", "BCH/USDT"), ("LINK", "LINK/USDT"),
    ("TON", "TON/USDT"), ("XLM", "XLM/USDT"), ("SUI", "SUI/USDT"),
    ("LTC", "LTC/USDT"), ("AVAX", "AVAX/USDT"), ("HBAR", "HBAR/USDT"),
    ("SHIB", "SHIB/USDT"), ("DOT", "DOT/USDT"), ("NEAR", "NEAR/USDT"),
    ("ARB", "ARB/USDT"),
]

TF_MAP = {
    "1W": "1w", "1D": "1d", "4H": "4h", "1H": "1h", "15m": "15m",
}

# ─── BOT GLOBAL STATE ─────────────────────────────────────────────────────────

_bot_thread = None
_bot_stop = threading.Event()
_bot_lock = threading.Lock()
_bot_status = {"balance": None, "posicion": {}, "log": [], "mtf": {}, "scores": {}, "activos": []}

# ─── DATOS E INDICADORES ──────────────────────────────────────────────────────

def obtener_datos(activo="BTC", temporalidad="4H", velas=200):
    simbolo = SYMBOL_MAP.get(activo, "BTC/USDT")
    tf = TF_MAP.get(temporalidad, "4h")
    raw = None
    # ── Fuente primaria: BingX perpetual ──────────────────────────────────────
    try:
        ex = ccxt.bingx({
            "apiKey": _bx_api_key,
            "secret": _bx_api_secret,
            "enableRateLimit": True,
        })
        raw = ex.fetch_ohlcv(simbolo + ":USDT", tf, limit=velas + 300)
        if raw:
            pass # BingX OK
    except Exception as e:
        print(f"[⚠ BingX OHLCV] {activo} {temporalidad}: {e}")
    # ── Fallback: Binance spot (precios ligeramente distintos — solo emergencia) ─
    if not raw:
        print(f"[⚠ FALLBACK Binance] {activo} {temporalidad} — BingX no respondió. Señales basadas en Binance spot.")
        try:
            ex = ccxt.binance({"enableRateLimit": True})
            raw = ex.fetch_ohlcv(simbolo, tf, limit=velas + 300)
        except Exception as e:
            print(f"[⚠ Binance OHLCV] {activo} {temporalidad}: {e}")
            return None
    df = pd.DataFrame(raw, columns=["tiempo", "open", "high", "low", "close", "volumen"])
    df["tiempo"] = pd.to_datetime(df["tiempo"], unit="ms")

    # EMA — warmup converges with 300 extra bars (matches TradingView)
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA55"] = df["close"].ewm(span=55, adjust=False).mean()

    # Squeeze Momentum (LazyBear — exact TradingView formula)
    bl, bm, kl, km = 20, 2.0, 20, 1.5

    df["BB_mid"] = df["close"].rolling(bl).mean()
    df["BB_std"] = df["close"].rolling(bl).std()
    df["BB_u"] = df["BB_mid"] + bm * df["BB_std"]
    df["BB_l"] = df["BB_mid"] - bm * df["BB_std"]

    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)

    # KC: midline = EMA(close), range = SMA(TR) — fórmula exacta LazyBear v4_pine
    df["KC_mid"] = df["close"].ewm(span=kl, adjust=False).mean()
    df["KC_r"] = tr.rolling(kl).mean()
    df["KC_u"] = df["KC_mid"] + km * df["KC_r"]
    df["KC_l"] = df["KC_mid"] - km * df["KC_r"]
    df["squeeze"] = (df["BB_l"] > df["KC_l"]) & (df["BB_u"] < df["KC_u"])

    # Momentum: linreg(close - avg(avg(high_max, low_min), sma_close), kl, 0)
    sma_close = df["close"].rolling(kl).mean()
    highest = df["high"].rolling(kl).max()
    lowest = df["low"].rolling(kl).min()
    delta = df["close"] - ((highest + lowest) / 2 + sma_close) / 2
    df["momentum"] = delta.rolling(kl).apply(_linreg_last, raw=True)

    # ADX (Wilder smoothing — matches TradingView DMI)
    # reuses `tr` from the KC block above — no recomputation needed
    a = 1 / 14
    dm_p = ((df["high"] - df["high"].shift()) > (df["low"].shift() - df["low"])).astype(float) *            (df["high"] - df["high"].shift()).clip(lower=0)
    dm_m = ((df["low"].shift() - df["low"]) > (df["high"] - df["high"].shift())).astype(float) *            (df["low"].shift() - df["low"]).clip(lower=0)
    tr_s = tr.ewm(alpha=a, adjust=False).mean()
    df["DI_p"] = 100 * dm_p.ewm(alpha=a, adjust=False).mean() / tr_s
    df["DI_m"] = 100 * dm_m.ewm(alpha=a, adjust=False).mean() / tr_s
    dx = 100 * (df["DI_p"] - df["DI_m"]).abs() / (df["DI_p"] + df["DI_m"])
    df["ADX"] = dx.ewm(alpha=a, adjust=False).mean()

    # Return only the requested candles (warmup discarded)
    return df.tail(velas).reset_index(drop=True)

def _volume_profile(df, bins=90):
    lo, hi = df["low"].min(), df["high"].max()
    niveles = np.linspace(lo, hi, bins + 1)
    vols = [df.loc[(df["close"] >= niveles[i]) & (df["close"] < niveles[i+1]), "volumen"].sum()
            for i in range(bins)]
    poc_idx = int(np.argmax(vols))
    poc = (niveles[poc_idx] + niveles[poc_idx + 1]) / 2
    return niveles, vols, poc

def _analizar_mtf(activo, ema_comp_pct=1.0):
    """
    Cascade MTF: 1W (master direction) → 1D (filter) → 4H (entry trigger).
    Reglas:
    - 1W bullish (sep > +ema_comp_pct AND mom > 0) → solo LONGS permitidos
    - 1W bearish (sep < -ema_comp_pct AND mom < 0) → solo SHORTS permitidos
    - 1W compresión → esperar, sin entradas
    - 1D debe confirmar: momentum en la misma dirección que 1W
    - 4H debe confirmar: sep > umbral AND momentum en la misma dirección
    - long_ok / short_ok son True solo cuando los 3 TF están alineados
    """
    _default = {
        "activo": activo,
        "1W": {"estado": "–", "sep": 0.0, "mom": 0.0},
        "1D": {"estado": "–", "sep": 0.0, "mom": 0.0},
        "4H": {"estado": "–", "sep": 0.0, "mom": 0.0},
        "direccion": "esperar",
        "long_ok": False,
        "short_ok": False,
    }
    try:
        # Fetch paralelo: 3 TF a la vez
        with ThreadPoolExecutor(max_workers=3) as pool:
            f1w = pool.submit(obtener_datos, activo, "1W", 100)
            f1d = pool.submit(obtener_datos, activo, "1D", 100)
            f4h = pool.submit(obtener_datos, activo, "4H", 100)
            df_1w, df_1d, df_4h = f1w.result(), f1d.result(), f4h.result()

        if any(df is None or df.empty for df in [df_1w, df_1d, df_4h]):
            return _default

        def _tf_info(df):
            """Devuelve estado, sep% y mom del último cierre."""
            u = df.iloc[-1]
            sep = (float(u["EMA10"]) - float(u["EMA55"])) / float(u["EMA55"]) * 100
            mom = float(u["momentum"])
            if sep > ema_comp_pct and mom > 0:
                estado = "alcista"
            elif sep < -ema_comp_pct and mom < 0:
                estado = "bajista"
            else:
                estado = "compresion"
            return {"estado": estado, "sep": round(sep, 2), "mom": round(mom, 2)}, mom

        r1w, mom_1w = _tf_info(df_1w)
        r1d, mom_1d = _tf_info(df_1d)
        r4h, mom_4h = _tf_info(df_4h)

        result = {**_default, "1W": r1w, "1D": r1d, "4H": r4h}

        dir_1w = r1w["estado"]

        if dir_1w == "alcista":
            result["direccion"] = "long"
            # 1D: momentum positivo (giro iniciado o confirmado)
            if mom_1d > 0:
                # 4H: EMAs separadas alcistas Y momentum positivo
                if r4h["sep"] > ema_comp_pct and mom_4h > 0:
                    result["long_ok"] = True

        elif dir_1w == "bajista":
            result["direccion"] = "short"
            # 1D: momentum negativo
            if mom_1d < 0:
                # 4H: EMAs separadas bajistas Y momentum negativo
                if r4h["sep"] < -ema_comp_pct and mom_4h < 0:
                    result["short_ok"] = True
            # else: 1W en compresión → esperar (ambos False)

        return result

    except Exception:
        return _default

def calcular_score(df):
    u, prev = df.iloc[-1], df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    pts, gr = 0, {}

    bull_ema = bool(u["EMA10"] > u["EMA55"])
    pts += 30 if bull_ema else -30
    gr["EMA"] = {"estado": "on" if bull_ema else "war",
                 "valor": f"{'▲' if bull_ema else '▼'} {u['EMA10']:.0f}"}

    mom, growing = float(u["momentum"]), bool(u["momentum"] > float(prev["momentum"]))
    bull_mom = mom > 0
    pts += 25 if bull_mom else -25
    gr["SQUEEZE"] = {"estado": "on" if (bull_mom and growing) else "war" if not bull_mom else "off",
                     "valor": f"{'▲' if growing else '▼'} {mom:.1f}"}

    adx = float(u["ADX"])
    pts += 10 if adx >= 23 else -10
    gr["ADX"] = {"estado": "on" if adx >= 23 else "off", "valor": f"{adx:.1f}"}

    _, _, poc = _volume_profile(df)
    sobre_poc = bool(u["close"] > poc)
    pct_poc = (u["close"] - poc) / poc * 100
    pts += 10 if sobre_poc else -10
    gr["VOL PROFILE"] = {"estado": "on" if sobre_poc else "war",
                         "valor": f"{'↑' if sobre_poc else '↓'}{abs(pct_poc):.1f}%"}

    max_idx = argrelextrema(df["high"].values, np.greater, order=10)[0]
    min_idx = argrelextrema(df["low"].values, np.less, order=10)[0]
    precio = float(u["close"])
    sr_pts, sr_val, sr_est = 0, "-", "off"
    if len(min_idx):
        s = df["low"].iloc[min_idx].values
        c = s[np.argmin(np.abs(s - precio))]
        if abs(precio - c) / precio < 0.005:
            sr_pts, sr_val, sr_est = 15, f"S {c:.0f}", "on"
    if len(max_idx):
        r = df["high"].iloc[max_idx].values
        c = r[np.argmin(np.abs(r - precio))]
        if abs(precio - c) / precio < 0.005:
            sr_pts, sr_val, sr_est = -15, f"R {c:.0f}", "war"
    pts += sr_pts
    gr["S/R"] = {"estado": sr_est, "valor": sr_val}
    gr["MTF"] = {"estado": "off", "valor": "-"}
    return max(-100, min(100, int(pts))), gr

def crear_grafico(df, activo="BTC", compacto=False):
    simbolo = SYMBOL_MAP.get(activo, "BTC/USDT")
    niveles, vols, poc = _volume_profile(df)
    poc_idx = int(np.argmax(vols))
    vol_max = max(vols) or 1

    lineas = []
    for idx_arr, col, color, name in [
        (argrelextrema(df["high"].values, np.greater, order=10)[0], "high", "#ff4444", "Resistencia"),
        (argrelextrema(df["low"].values, np.less, order=10)[0], "low", "#00e676", "Soporte"),
    ]:
        if len(idx_arr) >= 2:
            i1, i2 = idx_arr[-2], idx_arr[-1]
            y1, y2 = df[col].iloc[i1], df[col].iloc[i2]
            pend = (y2 - y1) / (i2 - i1)
            lineas.append({
                "x": [df["tiempo"].iloc[i1], df["tiempo"].iloc[-1]],
                "y": [y1, y2 + pend * (len(df) - 1 - i2)],
                "color": color, "name": name,
            })

    # Más espacio para ADX en vista detalle
    heights = [0.55, 0.20, 0.25] if not compacto else [0.60, 0.20, 0.20]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=heights, vertical_spacing=0.02)

    fig.add_trace(go.Candlestick(
        x=df["tiempo"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name=simbolo,
        increasing_line_color="#26a69a", increasing_fillcolor="#26a69a",
        decreasing_line_color="#ef5350", decreasing_fillcolor="#ef5350",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df["tiempo"], y=df["EMA10"],
                             line=dict(color="#2196F3", width=1.5), name="EMA 10"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["tiempo"], y=df["EMA55"],
                             line=dict(color="#ef5350", width=1.8), name="EMA 55"), row=1, col=1)

    for l in lineas:
        fig.add_trace(go.Scatter(x=l["x"], y=l["y"], mode="lines",
                                 line=dict(color=l["color"], width=1.5, dash="dot"), name=l["name"]), row=1, col=1)

    t_max = df["tiempo"].max()
    rango_s = (t_max - df["tiempo"].min()).total_seconds()
    # Volume profile: batch 88 non-POC bars into ONE Scatter (was 90 separate traces)
    x_vp, y_vp = [], []
    for i, v in enumerate(vols):
        if i == poc_idx:
            continue
        pmid = (niveles[i] + niveles[i + 1]) / 2
        t_ini = t_max - pd.Timedelta(seconds=rango_s * (v / vol_max) * 0.15)
        x_vp += [t_ini, t_max, None]
        y_vp += [pmid, pmid, None]
    if x_vp:
        fig.add_trace(go.Scatter(x=x_vp, y=y_vp, mode="lines",
                                 line=dict(color="rgba(33,150,243,0.22)", width=1),
                                 showlegend=False, hoverinfo="skip"), row=1, col=1)
    # POC bar in gold (separate trace for distinct color/width)
    poc_pmid = (niveles[poc_idx] + niveles[poc_idx + 1]) / 2
    poc_tini = t_max - pd.Timedelta(seconds=rango_s * (vols[poc_idx] / vol_max) * 0.15)
    fig.add_trace(go.Scatter(x=[poc_tini, t_max], y=[poc_pmid, poc_pmid], mode="lines",
                             line=dict(color="#FFD700", width=3),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_hline(y=poc, line_dash="dot", line_color="#FFD700", line_width=1, row=1, col=1)

    colores_m = []
    for i in range(len(df)):
        v = df["momentum"].iloc[i]
        p = df["momentum"].iloc[i - 1] if i else v
        colores_m.append("#00e676" if v >= 0 and v >= p else
                         "#26a69a" if v >= 0 else
                         "#ef5350" if v <= p else "#b71c1c")
    fig.add_trace(go.Bar(x=df["tiempo"], y=df["momentum"],
                         marker_color=colores_m, name="Squeeze", showlegend=False), row=2, col=1)
    sq = df[df["squeeze"]]
    fig.add_trace(go.Scatter(x=sq["tiempo"], y=[0] * len(sq), mode="markers",
                             marker=dict(color="#2196F3", size=4), showlegend=False), row=2, col=1)

    adx_val = float(df["ADX"].iloc[-1])
    fig.add_trace(go.Scatter(x=df["tiempo"], y=df["ADX"],
                             line=dict(color="#00e676" if adx_val >= 23 else "#888888", width=1.8),
                             name=f"ADX {adx_val:.1f}", showlegend=True), row=3, col=1)
    fig.add_hline(y=23, line_dash="dash", line_color="#FFD700", line_width=1.2, row=3, col=1)

    ax = dict(gridcolor="#1a1a28", color="#6b6b80", showspikes=True,
              spikecolor="#555", spikethickness=1, spikedash="dot", fixedrange=False)
    yax = dict(**ax, side="right")
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
        margin=dict(l=5, r=65, t=8, b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#a0a8c0", size=11),
                    orientation="h", x=0, y=1.02),
        hovermode="x unified", xaxis_rangeslider_visible=False,
        dragmode="pan", # arrastrar = mover (como TradingView)
        xaxis=dict(**ax), xaxis2=dict(**ax), xaxis3=dict(**ax),
        yaxis=yax, yaxis2=yax, yaxis3=yax,
    )
    return fig

def _grid_cols(n):
    if n <= 3: return n
    if n == 4: return 2
    return 3

def crear_mini_grafico(df_dict):
    activos = [a for a, df in df_dict.items() if df is not None and not df.empty]
    if not activos:
        return go.Figure(), 1 # callers always unpack (fig, rows)
    n = len(activos)
    cols = _grid_cols(n)
    rows = -(-n // cols)

    titulos = [SYMBOL_MAP.get(a, a) for a in activos]
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=titulos,
                        vertical_spacing=0.08, horizontal_spacing=0.04)

    for i, activo in enumerate(activos):
        row = i // cols + 1
        col = i % cols + 1
        df = df_dict[activo]
        if df is None or df.empty:
            continue
        fig.add_trace(go.Candlestick(
            x=df["tiempo"], open=df["open"], high=df["high"],
            low=df["low"], close=df["close"], showlegend=False,
            increasing_line_color="#26a69a", increasing_fillcolor="#26a69a",
            decreasing_line_color="#ef5350", decreasing_fillcolor="#ef5350",
        ), row=row, col=col)
        fig.add_trace(go.Scatter(x=df["tiempo"], y=df["EMA10"],
                                 line=dict(color="#2196F3", width=1), showlegend=False), row=row, col=col)
        fig.add_trace(go.Scatter(x=df["tiempo"], y=df["EMA55"],
                                 line=dict(color="#ef5350", width=1), showlegend=False), row=row, col=col)

    fig.update_xaxes(rangeslider_visible=False, gridcolor="#1a1a28",
                     color="#6b6b80", showticklabels=False)
    fig.update_yaxes(gridcolor="#1a1a28", color="#6b6b80", side="right")
    fig.update_annotations(font=dict(color="#c8a84b", size=11))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
        margin=dict(l=5, r=50, t=32, b=5), showlegend=False,
    )
    return fig, rows

# ─── TELEGRAM ─────────────────────────────────────────────────────────────────

def _enviar_telegram(mensaje):
    """Envía un mensaje via Telegram Bot API. Usa credenciales cargadas al iniciar el bot."""
    try:
        if not _tg_token or not _tg_chatid:
            return
        url = f"https://api.telegram.org/bot{_tg_token}/sendMessage"
        data = json.dumps({
            "chat_id": str(_tg_chatid),
            "text": mensaje,
            "parse_mode": "HTML",
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass # Nunca interrumpir el bot por fallo de Telegram

# ─── BOT LOOP ─────────────────────────────────────────────────────────────────

def _bot_loop(activos_lista, tf, capital_pct):
    global _tg_token, _tg_chatid
    try:
        with open("config.json") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    # Cache Telegram credentials at bot start — no per-message disk reads
    _tg_token = cfg.get("telegram_token", "")
    _tg_chatid = cfg.get("telegram_chatid", "")
    modo = cfg.get("modo", "demo")
    # AERO LADDER: apalancamiento dinámico — el config.json solo define máximo (5X)
    apalancamiento_max = min(int(cfg.get("apalancamiento", 5)), 5)  # HARD CAP 5X
    ts_activacion = float(cfg.get("trailing_activacion", 3.0))
    ts_distancia = float(cfg.get("trailing_distancia", 1.5))
    stop_loss_pct = float(cfg.get("stop_loss_pct", 5.0))
    max_perd_diaria = float(cfg.get("max_perdida_diaria", 10.0))
    ema_comp_pct = float(cfg.get("ema_compresion_pct", 1.0))

    # ── CARGAR ESTADO AERO LADDER ─────────────────────────────────────────────
    bot_state = _load_bot_state()
    apalancamiento_actual = _calcular_apalancamiento(bot_state)
    print(f"[🪜 AERO LADDER] Inicio — Racha: {bot_state['racha_ganadora']} | Apalancamiento: {apalancamiento_actual}X")

    # Tracking por activo
    posicion = {a: None for a in activos_lista}
    precio_entrada = {a: None for a in activos_lista}
    precio_extremo = {a: None for a in activos_lista}
    trailing_activo = {a: False for a in activos_lista}
    capital_usado = {a: 0.0 for a in activos_lista}  # para tracking de exposición

    # Tracking diario de pérdidas
    perdida_acum = 0.0
    fecha_hoy = datetime.now().date()

    # ── PRIORIDAD 3: Detectar posiciones abiertas en BingX al arrancar ──────────
    if modo == "real":
        try:
            ex = ccxt.bingx({
                "apiKey": cfg.get("api_key", ""), "secret": cfg.get("api_secret", ""),
                "enableRateLimit": True,
            })
            for p in (ex.fetch_positions() or []):
                if abs(float(p.get("contracts") or 0)) == 0:
                    continue
                for a in activos_lista:
                    sym = SYMBOL_MAP.get(a, f"{a}/USDT") + ":USDT"
                    if p.get("symbol") == sym and p.get("side") in ("long", "short"):
                        posicion[a] = p["side"]
                        precio_entrada[a] = float(p.get("entryPrice") or 0)
                        precio_extremo[a] = precio_entrada[a]
                        msg = f"Posicion previa: {a} {p['side'].upper()} @ ${precio_entrada[a]:,.2f}"
                        with _bot_lock:
                            _bot_status["log"].insert(0, msg)
                        _enviar_telegram(f"⚡ **Posición previa detectada**\nPar: **{a}** | {p['side'].upper()} @ **${precio_entrada[a]:,.2f}**")
        except Exception:
            pass

    def _registrar(activo, accion, posicion_nueva):
        ts = datetime.now().strftime("%H:%M:%S")
        with _bot_lock:
            _bot_status["posicion"][activo] = posicion_nueva
            _bot_status["log"].insert(0, f"[{ts}] {activo}: {accion}")
            _bot_status["log"] = _bot_status["log"][:8]

    while not _bot_stop.is_set():
        # ── RESET DIARIO ──────────────────────────────────────────────────────
        hoy = datetime.now().date()
        if hoy != fecha_hoy:
            perdida_acum = 0.0
            fecha_hoy = hoy

        # ── STOP POR MAX PÉRDIDA DIARIA ───────────────────────────────────────
        if max_perd_diaria > 0 and perdida_acum >= max_perd_diaria:
            _enviar_telegram(
                f"🚫 **MÁXIMA PÉRDIDA DIARIA ALCANZADA**\n"
                f"Pérdida acumulada: **-{perdida_acum:.2f}%**\n"
                f"Límite: **-{max_perd_diaria:.0f}%**\n"
                f"El bot se detiene hasta mañana."
            )
            with _bot_lock:
                _bot_status["log"].insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] BOT DETENIDO — Max pérdida diaria ({perdida_acum:.1f}%)")
                _bot_status["log"] = _bot_status["log"][:8]
            _bot_stop.set()
            break

        bal = bx.verificar_balance()
        with _bot_lock:
            _bot_status["balance"] = bal # None on failure (bingx.py normalised)

        # ── RECALCULAR APALANCAMIENTO AERO LADDER ──────────────────────────────
        apalancamiento_actual = _calcular_apalancamiento(bot_state)
        with _bot_lock:
            _bot_status["apalancamiento"] = apalancamiento_actual

        for activo in activos_lista:
            if _bot_stop.is_set():
                break
            try:
                df = obtener_datos(activo, tf, velas=200)
                if df is None or df.empty:
                    continue
                score, _ = calcular_score(df)
                with _bot_lock:
                    _bot_status["scores"][activo] = score
                mtf = _analizar_mtf(activo, ema_comp_pct)
                with _bot_lock:
                    _bot_status["mtf"] = mtf
                simbolo = SYMBOL_MAP.get(activo, f"{activo}/USDT")
                pos_actual = posicion[activo]
                precio = float(df.iloc[-1]["close"])

                # ── ACTUALIZAR PRECIO EXTREMO (antes de cualquier exit check) ──
                if pos_actual and precio_entrada[activo]:
                    if pos_actual == "long" and precio > (precio_extremo[activo] or precio):
                        precio_extremo[activo] = precio
                    elif pos_actual == "short" and precio < (precio_extremo[activo] or precio):
                        precio_extremo[activo] = precio

                # ── STOP LOSS FIJO ────────────────────────────────────────────
                if pos_actual and precio_entrada[activo] and stop_loss_pct > 0:
                    ep = precio_entrada[activo]
                    perdida = ((ep - precio) / ep * 100) if pos_actual == "long"                               else ((precio - ep) / ep * 100)
                    if perdida >= stop_loss_pct:
                        # Calcular P&L bruto para AERO LADDER
                        pnl_pct = -stop_loss_pct  # bruto, negativo
                        bx.cerrar_posicion(simbolo, pos_actual)
                        _enviar_telegram(
                            f"🚨 **STOP LOSS ACTIVADO**\n"
                            f"Par: **{simbolo}** | {pos_actual.upper()}\n"
                            f"Entrada: **${ep:,.2f}** Cierre: **${precio:,.2f}**\n"
                            f"Pérdida: **-{perdida:.2f}%**"
                        )
                        perdida_acum += perdida
                        # Actualizar AERO LADDER
                        bot_state = _actualizar_racha(bot_state, pnl_pct, apalancamiento_actual, bal or 1000)
                        # Registrar trade
                        _registrar_trade({
                            "timestamp": datetime.now().isoformat(),
                            "activo": activo,
                            "side": pos_actual,
                            "entrada": ep,
                            "salida": precio,
                            "pnl_pct": round(pnl_pct, 2),
                            "apalancamiento": apalancamiento_actual,
                            "motivo": "STOP LOSS",
                            "modo": modo,
                        })
                        posicion[activo] = precio_entrada[activo] = precio_extremo[activo] = None
                        trailing_activo[activo] = False
                        capital_usado[activo] = 0.0
                        _registrar(activo, f"STOP LOSS -{perdida:.1f}%", None)
                        continue

                # ── TRAILING STOP ─────────────────────────────────────────────
                if pos_actual and precio_entrada[activo]:
                    ep = precio_entrada[activo]

                    if pos_actual == "long":
                        profit_pct = (precio - ep) / ep * 100
                        if profit_pct >= ts_activacion:
                            trailing_activo[activo] = True
                        if trailing_activo[activo]:
                            retroceso = (precio_extremo[activo] - precio) / precio_extremo[activo] * 100
                            if retroceso >= ts_distancia:
                                pnl_pct = profit_pct  # bruto, positivo
                                bx.cerrar_posicion(simbolo, "long")
                                _enviar_telegram(
                                    f"🛑 **TRAILING STOP — LONG**\n"
                                    f"Par: **{simbolo}**\n"
                                    f"Entrada: **${ep:,.2f}** Cierre: **${precio:,.2f}**\n"
                                    f"Ganancia aprox: **+{profit_pct:.2f}%**"
                                )
                                bot_state = _actualizar_racha(bot_state, pnl_pct, apalancamiento_actual, bal or 1000)
                                _registrar_trade({
                                    "timestamp": datetime.now().isoformat(),
                                    "activo": activo,
                                    "side": "long",
                                    "entrada": ep,
                                    "salida": precio,
                                    "pnl_pct": round(pnl_pct, 2),
                                    "apalancamiento": apalancamiento_actual,
                                    "motivo": "TRAILING STOP",
                                    "modo": modo,
                                })
                                accion = f"Trailing Stop LONG +{profit_pct:.1f}%"
                                posicion[activo] = precio_entrada[activo] = precio_extremo[activo] = None
                                trailing_activo[activo] = False
                                capital_usado[activo] = 0.0
                                _registrar(activo, accion, None)
                                continue

                    elif pos_actual == "short":
                        profit_pct = (ep - precio) / ep * 100
                        if profit_pct >= ts_activacion:
                            trailing_activo[activo] = True
                        if trailing_activo[activo]:
                            retroceso = (precio - precio_extremo[activo]) / precio_extremo[activo] * 100
                            if retroceso >= ts_distancia:
                                pnl_pct = profit_pct
                                bx.cerrar_posicion(simbolo, "short")
                                _enviar_telegram(
                                    f"🛑 **TRAILING STOP — SHORT**\n"
                                    f"Par: **{simbolo}**\n"
                                    f"Entrada: **${ep:,.2f}** Cierre: **${precio:,.2f}**\n"
                                    f"Ganancia aprox: **+{profit_pct:.2f}%**"
                                )
                                bot_state = _actualizar_racha(bot_state, pnl_pct, apalancamiento_actual, bal or 1000)
                                _registrar_trade({
                                    "timestamp": datetime.now().isoformat(),
                                    "activo": activo,
                                    "side": "short",
                                    "entrada": ep,
                                    "salida": precio,
                                    "pnl_pct": round(pnl_pct, 2),
                                    "apalancamiento": apalancamiento_actual,
                                    "motivo": "TRAILING STOP",
                                    "modo": modo,
                                })
                                accion = f"Trailing Stop SHORT +{profit_pct:.1f}%"
                                posicion[activo] = precio_entrada[activo] = precio_extremo[activo] = None
                                trailing_activo[activo] = False
                                capital_usado[activo] = 0.0
                                _registrar(activo, accion, None)
                                continue

                # ── CIERRE POR COMPRESIÓN EMA (fiesta terminando) ────────────
                if pos_actual and abs(mtf["4H"]["sep"]) < ema_comp_pct:
                    ep = precio_entrada.get(activo) or precio
                    pnl = ((precio - ep) / ep * 100) if pos_actual == "long"                           else ((ep - precio) / ep * 100)
                    sgn = "+" if pnl >= 0 else ""
                    bx.cerrar_posicion(simbolo, pos_actual)
                    _enviar_telegram(
                        f"🔶 **CIERRE — COMPRESIÓN EMA**\n"
                        f"Par: **{simbolo}** | {pos_actual.upper()}\n"
                        f"Separación EMA 4H: **{mtf['4H']['sep']:+.1f}%** "
                        f"(umbral ±{ema_comp_pct:.1f}%)\n"
                        f"P&L estimado: **{sgn}{pnl:.2f}%**"
                    )
                    bot_state = _actualizar_racha(bot_state, pnl, apalancamiento_actual, bal or 1000)
                    _registrar_trade({
                        "timestamp": datetime.now().isoformat(),
                        "activo": activo,
                        "side": pos_actual,
                        "entrada": ep,
                        "salida": precio,
                        "pnl_pct": round(pnl, 2),
                        "apalancamiento": apalancamiento_actual,
                        "motivo": "COMPRESION EMA",
                        "modo": modo,
                    })
                    accion = f"Cierre COMP EMA {mtf['4H']['sep']:+.1f}% P&L={sgn}{pnl:.1f}%"
                    posicion[activo] = precio_entrada[activo] = precio_extremo[activo] = None
                    trailing_activo[activo] = False
                    capital_usado[activo] = 0.0
                    _registrar(activo, accion, None)
                    continue

                # ── CERRAR SI SCORE VUELVE A ZONA WAIT ───────────────────────
                if pos_actual and -70 < score < 70:
                    ep = precio_entrada.get(activo) or precio
                    pnl = ((precio - ep) / ep * 100) if pos_actual == "long" else ((ep - precio) / ep * 100)
                    sgn = "+" if pnl >= 0 else ""
                    bx.cerrar_posicion(simbolo, pos_actual)
                    _enviar_telegram(
                        f"⬜ **CIERRE — ZONA NEUTRAL**\n"
                        f"Par: **{simbolo}** | {pos_actual.upper()}\n"
                        f"Precio cierre: **${precio:,.2f}**\n"
                        f"P&L estimado: **{sgn}{pnl:.2f}%** | Score: **{score:+d}**"
                    )
                    bot_state = _actualizar_racha(bot_state, pnl, apalancamiento_actual, bal or 1000)
                    _registrar_trade({
                        "timestamp": datetime.now().isoformat(),
                        "activo": activo,
                        "side": pos_actual,
                        "entrada": ep,
                        "salida": precio,
                        "pnl_pct": round(pnl, 2),
                        "apalancamiento": apalancamiento_actual,
                        "motivo": "ZONA NEUTRAL",
                        "modo": modo,
                    })
                    accion = f"Cierre WAIT score={score} P&L={sgn}{pnl:.1f}%"
                    posicion[activo] = precio_entrada[activo] = precio_extremo[activo] = None
                    trailing_activo[activo] = False
                    capital_usado[activo] = 0.0
                    _registrar(activo, accion, None)
                    continue

                # ── SEÑALES DE ENTRADA ───────────────────────────────────────
                with _bot_lock:
                    bal_v = _bot_status["balance"] or 0
                    capital = bal_v * (capital_pct / 100) if bal_v else 10

                # AERO LADDER: recalcular apalancamiento actual
                apalancamiento_actual = _calcular_apalancamiento(bot_state)

                # Tope de exposición: verificar antes de abrir
                exposicion_actual = _calcular_exposicion_total(posicion, precio_entrada, capital_usado)
                exposicion_max = bal_v * (_MAX_EXPOSICION_PCT / 100) if bal_v else 500
                notional_nuevo = capital * apalancamiento_actual
                if exposicion_actual + notional_nuevo > exposicion_max:
                    print(f"[🛡️ TOPE EXPOSICIÓN] {activo}: Exposición actual ${exposicion_actual:.0f} + "
                          f"nuevo ${notional_nuevo:.0f} supera máximo ${exposicion_max:.0f}. Trade bloqueado.")
                    continue

                if score >= 70 and pos_actual != "long":
                    if not mtf["long_ok"]:
                        # MTF bloquea el LONG — dirección incorrecta o aún no alineada
                        pass
                    else:
                        if pos_actual == "short":
                            # Cerrar short primero
                            ep_s = precio_entrada.get(activo) or precio
                            pnl_s = ((ep_s - precio) / ep_s * 100)
                            bx.cerrar_posicion(simbolo, "short")
                            _enviar_telegram(f"🔄 **CIERRE SHORT → LONG**\nPar: **{simbolo}** | Precio: **${precio:,.2f}**")
                            bot_state = _actualizar_racha(bot_state, pnl_s, apalancamiento_actual, bal or 1000)
                            _registrar_trade({
                                "timestamp": datetime.now().isoformat(),
                                "activo": activo,
                                "side": "short",
                                "entrada": ep_s,
                                "salida": precio,
                                "pnl_pct": round(pnl_s, 2),
                                "apalancamiento": apalancamiento_actual,
                                "motivo": "FLIP SHORT→LONG",
                                "modo": modo,
                            })
                        bx.colocar_orden(simbolo, "long", capital, apalancamiento_actual, modo)
                        posicion[activo] = "long"
                        precio_entrada[activo] = precio
                        precio_extremo[activo] = precio
                        trailing_activo[activo] = False
                        capital_usado[activo] = capital
                        _enviar_telegram(
                            f"🟢 **ENTRADA LONG**\n━━━━━━━━━━━━━━━━\n"
                            f"Par: **{simbolo}**\nPrecio: **${precio:,.2f}**\n"
                            f"Score: **{score:+d}**\nCapital: **${capital:.2f} USDT**\n"
                            f"Apalancamiento: **x{apalancamiento_actual}** (AERO LADDER)\nModo: **{modo.upper()}**\n"
                            f"MTF: 1W {mtf['1W']['estado']} | 1D {mtf['1D']['estado']} | 4H {mtf['4H']['estado']}"
                        )
                        _registrar(activo, f"LONG score={score} MTF✅ @{apalancamiento_actual}X", "long")

                elif score <= -70 and pos_actual != "short":
                    if not mtf["short_ok"]:
                        # MTF bloquea el SHORT
                        pass
                    else:
                        if pos_actual == "long":
                            # Cerrar long primero
                            ep_l = precio_entrada.get(activo) or precio
                            pnl_l = ((precio - ep_l) / ep_l * 100)
                            bx.cerrar_posicion(simbolo, "long")
                            _enviar_telegram(f"🔄 **CIERRE LONG → SHORT**\nPar: **{simbolo}** | Precio: **${precio:,.2f}**")
                            bot_state = _actualizar_racha(bot_state, pnl_l, apalancamiento_actual, bal or 1000)
                            _registrar_trade({
                                "timestamp": datetime.now().isoformat(),
                                "activo": activo,
                                "side": "long",
                                "entrada": ep_l,
                                "salida": precio,
                                "pnl_pct": round(pnl_l, 2),
                                "apalancamiento": apalancamiento_actual,
                                "motivo": "FLIP LONG→SHORT",
                                "modo": modo,
                            })
                        bx.colocar_orden(simbolo, "short", capital, apalancamiento_actual, modo)
                        posicion[activo] = "short"
                        precio_entrada[activo] = precio
                        precio_extremo[activo] = precio
                        trailing_activo[activo] = False
                        capital_usado[activo] = capital
                        _enviar_telegram(
                            f"🔴 **ENTRADA SHORT**\n━━━━━━━━━━━━━━━━\n"
                            f"Par: **{simbolo}**\nPrecio: **${precio:,.2f}**\n"
                            f"Score: **{score:+d}**\nCapital: **${capital:.2f} USDT**\n"
                            f"Apalancamiento: **x{apalancamiento_actual}** (AERO LADDER)\nModo: **{modo.upper()}**\n"
                            f"MTF: 1W {mtf['1W']['estado']} | 1D {mtf['1D']['estado']} | 4H {mtf['4H']['estado']}"
                        )
                        _registrar(activo, f"SHORT score={score} MTF✅ @{apalancamiento_actual}X", "short")

            except Exception as e:
                ts = datetime.now().strftime("%H:%M:%S")
                with _bot_lock:
                    _bot_status["log"].insert(0, f"[{ts}] ERROR {activo}: {e}")
                    _bot_status["log"] = _bot_status["log"][:8]

        _bot_stop.wait(timeout=30)

# ─── APP ──────────────────────────────────────────────────────────────────────

app = dash.Dash(__name__, suppress_callback_exceptions=True,
                title="AERO BOT PRO", update_title=None)
server = app.server

# ─── HELPERS DE LAYOUT ────────────────────────────────────────────────────────

def _reloj(ciudad, codigo):
    return html.Div(className="reloj-ciudad", children=[
        html.Div(ciudad, className="ciudad-nombre"),
        html.Div("--:--:--", id=f"reloj-{codigo}", className="ciudad-hora"),
        html.Div(codigo, className="ciudad-sesion"),
    ])

def _gr_card(nombre, tipo, card_id, dot_id, val_id):
    return html.Div(id=card_id, className="guardarrail-card off", children=[
        html.Div(children=[
            html.Span(id=dot_id, className="guardarrail-indicador off"),
            html.Span(nombre, className="guardarrail-nombre"),
        ]),
        html.Div(tipo, style={"fontSize": "10px", "color": "#6b5520",
                              "letterSpacing": "0.1em", "marginTop": "2px"}),
        html.Div(id=val_id, className="guardarrail-valor", children="-"),
    ])

def _scoring_bar(prefix=""):
    return html.Div(id=f"{prefix}scoring-bar", children=[
        html.Div(id=f"{prefix}sc-numero", className="sc-numero", children="–"),
        html.Div(className="sc-barra-wrap", children=[
            html.Div(id=f"{prefix}sc-barra", className="sc-barra",
                     style={"width": "50%", "background": "#2a2a3a"}),
        ]),
        html.Div(id=f"{prefix}sc-etiqueta", className="sc-etiqueta",
                 children="–", style={"color": "#a0a8c0"}),
    ])

# ─── PÁGINAS ──────────────────────────────────────────────────────────────────

def _pagina_principal():
    try:
        with open("config.json") as f:
            _ui_cfg = json.load(f)
        _ts_act = float(_ui_cfg.get("trailing_activacion", 3.0))
        _ts_dist = float(_ui_cfg.get("trailing_distancia", 1.5))
        _sl_pct = float(_ui_cfg.get("stop_loss_pct", 5.0))
        _sl_diario = float(_ui_cfg.get("max_perdida_diaria", 10.0))
    except Exception:
        _ts_act = 3.0; _ts_dist = 1.5; _sl_pct = 5.0; _sl_diario = 10.0
    return [
        html.Div(id="contenido-principal", children=[

            # LEFT
            html.Div(className="panel-lateral", children=[
                html.Div(className="seccion-control", children=[
                    html.Div(id="lbl-idioma", className="seccion-titulo", children="Idioma"),
                    dcc.RadioItems(id="radio-idioma",
                                   options=[{"label": x, "value": x.lower()}
                                            for x in ["ES","EN","IT","FR","DE","ZH","KO","JA"]],
                                   value="es", className="radio-idiomas",
                                   inputStyle={"display": "none"}),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(id="lbl-tf", className="seccion-titulo", children="Temporalidad"),
                    dcc.RadioItems(id="radio-tf",
                                   options=[
                                       {"label": "1 Semana", "value": "1W"},
                                       {"label": "1 Día", "value": "1D"},
                                       {"label": "4 Horas", "value": "4H"},
                                       {"label": "1 Hora", "value": "1H"},
                                       {"label": "15 Minutos", "value": "15m"},
                                   ],
                                   value="4H", className="radio-grupo",
                                   labelStyle={"display": "flex", "alignItems": "center", "gap": "10px"}),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(id="lbl-capital", className="seccion-titulo", children="Capital por Op."),
                    html.Div(style={"textAlign": "center", "marginBottom": "8px"}, children=[
                        html.Span(id="val-capital", style={
                            "fontFamily": "Cinzel, serif", "fontSize": "22px", "color": "#f0c040",
                        }, children="5%"),
                    ]),
                    dcc.Slider(id="slider-capital", min=1, max=20, step=1, value=5,
                               marks={1:"1%", 5:"5%", 10:"10%", 15:"15%", 20:"20%"},
                               tooltip={"placement": "bottom", "always_visible": False}),
                ]),
            ]),

            # CENTER: siempre BTC
            html.Div(id="panel-central", children=[
                _scoring_bar(),
                html.Div(className="chart-action-bar", children=[
                    html.Span("BTC / USDT", className="chart-asset-label"),
                    html.A("↗ Ver Detalle", href="/detail/BTC", target="_blank",
                           className="btn-detalle"),
                ]),
                html.Div(className="grafico-wrap", children=[
                    dcc.Loading(type="dot", color="#c8a84b", children=[
                        dcc.Graph(id="grafico-principal",
                                  config={"displayModeBar": "hover", "scrollZoom": True, "displaylogo": False,
                                          "modeBarButtonsToRemove": ["select2d","lasso2d","toImage","sendDataToCloud"]},
                                  style={"height": "100%"}),
                    ]),
                ]),
                html.Div(className="seccion-control", children=[
                    html.Div(id="lbl-guardarrailes", className="seccion-titulo",
                             children="Guardarrailes"),
                    html.Div(id="gr-grid", className="guardarrail-grid", children=[
                        _gr_card("SQUEEZE", "Momentum", "gr-squeeze-card", "gr-squeeze-dot", "gr-squeeze-val"),
                        _gr_card("ADX", "Dirección", "gr-adx-card", "gr-adx-dot", "gr-adx-val"),
                        _gr_card("EMA", "10 / 55", "gr-ema-card", "gr-ema-dot", "gr-ema-val"),
                        _gr_card("S/R", "Soporte/Res.","gr-sr-card", "gr-sr-dot", "gr-sr-val"),
                        _gr_card("VOL PROFILE", "Emergencia", "gr-vol-card", "gr-vol-dot", "gr-vol-val"),
                        _gr_card("MTF", "Multi-TF", "gr-mtf-card", "gr-mtf-dot", "gr-mtf-val"),
                    ]),
                ]),
                html.Div(className="seccion-control", children=[
                    html.Div(id="lbl-stats", className="seccion-titulo",
                             children="Estadísticas en Tiempo Real"),
                    html.Div(id="stats-contenido", children=[
                        html.Div(className="stat-fila", children=[
                            html.Span("Precio", className="stat-nombre"),
                            html.Span("–", id="stat-precio", className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Cambio 7d", className="stat-nombre"),
                            html.Span("–", id="stat-cambio", className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("ADX", className="stat-nombre"),
                            html.Span("–", id="stat-adx", className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Momentum", className="stat-nombre"),
                            html.Span("–", id="stat-momentum", className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Squeeze ON", className="stat-nombre"),
                            html.Span("–", id="stat-squeeze", className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("EMA 10/55", className="stat-nombre"),
                            html.Span("–", id="stat-ema", className="stat-valor"),
                        ]),
                    ]),
                ]),
            ]),

            # RIGHT
            html.Div(className="panel-lateral derecho", children=[
                html.Div(className="seccion-control", children=[
                    html.Div(id="lbl-activos", className="seccion-titulo",
                             children="Cripto BingX (max. 6)"),
                    html.Div(className="checklist-scroll", children=[
                        dcc.Checklist(
                            id="checklist-activos",
                            options=[{"label": label, "value": key}
                                     for key, label in ACTIVOS_GRID],
                            value=[],
                            className="checklist-activos",
                            labelStyle={"display": "flex", "alignItems": "center", "gap": "10px"},
                        ),
                    ]),
                    html.Div(id="panel-senales-mini", style={"marginTop": "8px"}),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Trailing Stop"),
                    html.Div([
                        html.Div(className="stat-fila", children=[
                            html.Span("Activación", className="stat-nombre"),
                            html.Span(f"+{_ts_act:.1f}%", className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Distancia", className="stat-nombre"),
                            html.Span(f"{_ts_dist:.1f}%", className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Stop Loss", className="stat-nombre"),
                            html.Span(f"−{_sl_pct:.1f}%", className="stat-valor",
                                      style={"color": "#ff3355", "fontWeight": "600"}),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Pérd. Diaria Máx.", className="stat-nombre"),
                            html.Span(f"−{_sl_diario:.0f}%", className="stat-valor",
                                      style={"color": "#f0c040"}),
                        ]),
                    ]),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="AERO LADDER"),
                    html.Div(className="stat-fila", children=[
                        html.Span("Apalancamiento", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em"}),
                        html.Span("–", id="aero-ladder-val", className="stat-valor",
                                  style={"fontSize": "13px", "fontWeight": "700", "color": "#f0c040"}),
                    ]),
                    html.Div(className="stat-fila", children=[
                        html.Span("Racha", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em"}),
                        html.Span("–", id="aero-racha-val", className="stat-valor",
                                  style={"fontSize": "11px", "fontFamily": "monospace"}),
                    ]),
                    html.Div(className="stat-fila", children=[
                        html.Span("Profit Lock", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em"}),
                        html.Span("–", id="aero-lock-val", className="stat-valor",
                                  style={"fontSize": "11px", "fontFamily": "monospace", "color": "#00ff88"}),
                    ]),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Dirección MTF"),
                    html.Div(className="stat-fila", children=[
                        html.Span("1W", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em"}),
                        html.Span("–", id="mtf-1w", className="stat-valor",
                                  style={"fontSize": "11px", "fontFamily": "monospace"}),
                    ]),
                    html.Div(className="stat-fila", children=[
                        html.Span("1D", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em"}),
                        html.Span("–", id="mtf-1d", className="stat-valor",
                                  style={"fontSize": "11px", "fontFamily": "monospace"}),
                    ]),
                    html.Div(className="stat-fila", children=[
                        html.Span("4H", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em"}),
                        html.Span("–", id="mtf-4h", className="stat-valor",
                                  style={"fontSize": "11px", "fontFamily": "monospace"}),
                    ]),
                    html.Div(id="mtf-direccion", style={
                        "textAlign": "center", "marginTop": "6px",
                        "fontSize": "11px", "fontWeight": "700",
                        "letterSpacing": "0.06em", "padding": "5px 4px",
                        "background": "#111120", "borderRadius": "4px",
                        "border": "1px solid #2a2a3a",
                    }, children="⏳ Bot detenido"),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Gestión de Racha"),
                    html.Div([
                        html.Div(className="stat-fila", children=[
                            html.Span("Pérdidas (2+)", className="stat-nombre"),
                            html.Span("Reducir", className="stat-valor",
                                      style={"color": "#ff3355"}),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Ganancias (3+)", className="stat-nombre"),
                            html.Span("Aumentar", className="stat-valor",
                                      style={"color": "#00ff88"}),
                        ]),
                    ]),
                ]),
                html.Div(className="separador-dorado"),
                html.Button(id="btn-bot", children="INICIAR BOT",
                            className="btn-principal", n_clicks=0),
                html.Div(className="seccion-control", style={"marginTop": "8px"}, children=[
                    html.Div(className="seccion-titulo", children="Telegram"),
                    html.Div(className="stat-fila", children=[
                        html.Span("Estado", className="stat-nombre"),
                        html.Span("No configurado", id="telegram-estado",
                                  style={"color": "#a0a8c0", "fontSize": "12px"}),
                    ]),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Balance BingX"),
                    html.Div(className="stat-fila", children=[
                        html.Span("USDT", className="stat-nombre"),
                        html.Span("–", id="bot-balance-val", className="stat-valor"),
                    ]),
                ]),
                html.Div(id="bot-log", style={
                    "marginTop": "6px", "fontSize": "10px",
                    "color": "#6b5520", "lineHeight": "1.7",
                    "fontFamily": "monospace",
                }),
            ]),

            # Grid de activos seleccionados (abajo, ancho completo)
            html.Div(id="asset-grid-section"),
        ])
    ]

def _pagina_detalle(symbol):
    nombre = SYMBOL_MAP.get(symbol, f"{symbol}/USDT")
    return [
        html.Div(className="detail-header", children=[
            html.A("← Inicio", href="/", className="btn-volver"),
            html.Span(nombre, className="detail-titulo"),
            dcc.RadioItems(
                id="detail-tf-radio",
                options=[{"label": k, "value": k} for k in TF_MAP.keys()],
                value="4H", className="radio-grupo detail-tf-radio",
                inline=True,
                labelStyle={"display": "flex", "alignItems": "center",
                            "gap": "8px", "marginRight": "12px"},
            ),
        ]),
        dcc.Interval(id="detail-tick", interval=30_000, n_intervals=0),
        dcc.Loading(type="dot", color="#c8a84b", children=[
            dcc.Graph(id="detail-graph",
                      config={"displayModeBar": "hover", "scrollZoom": True, "displaylogo": False,
                              "modeBarButtonsToRemove": ["select2d","lasso2d","toImage","sendDataToCloud"]},
                      style={"height": "calc(100vh - 290px)"}),
        ]),
        html.Div(className="detail-bottom", children=[
            _scoring_bar("d-"),
            html.Div(className="detail-gr-row", children=[
                _gr_card("SQUEEZE", "Momentum", "d-gr-squeeze-card", "d-gr-squeeze-dot", "d-gr-squeeze-val"),
                _gr_card("ADX", "Dirección", "d-gr-adx-card", "d-gr-adx-dot", "d-gr-adx-val"),
                _gr_card("EMA", "10 / 55", "d-gr-ema-card", "d-gr-ema-dot", "d-gr-ema-val"),
                _gr_card("S/R", "Soporte/Res.","d-gr-sr-card", "d-gr-sr-dot", "d-gr-sr-val"),
                _gr_card("VOL PROFILE", "Emergencia", "d-gr-vol-card", "d-gr-vol-dot", "d-gr-vol-val"),
            ]),
        ]),
    ]

# ─── LAYOUT ESTÁTICO (siempre presente) ───────────────────────────────────────

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="store-idioma", data="es"),
    dcc.Store(id="store-bot", data=False),
    dcc.Store(id="store-tf", data="4H"),
    dcc.Interval(id="tick-relojes", interval=1_000, n_intervals=0),
    dcc.Interval(id="tick-main", interval=30_000, n_intervals=0),
    dcc.Interval(id="tick-bot-status", interval=5_000, n_intervals=0),
    dcc.Interval(id="tick-senales", interval=5_000, n_intervals=0),

    html.Div(id="header-main", children=[
        html.Div(className="logo-area", children=[
            html.Div(className="logo-texto", children=[
                html.H1(id="h-titulo", children="AERO BOT PRO"),
                html.P (id="h-subtitulo", children="Trading Bot Profesional"),
            ]),
        ]),
        html.Div(id="led-container", className="led-indicator", children=[
            html.Div(id="led-dot", className="led-dot desconectado"),
            html.Span(id="led-txt", className="led-texto", children="DESCONECTADO"),
        ]),
    ]),
    html.Div(id="relojes-barra", children=[
        _reloj("NEW YORK", "NY"), _reloj("LONDON", "LON"),
        _reloj("TOKYO", "TYO"), _reloj("DUBAI", "DXB"),
    ]),
    html.Div(id="frase-barra", children=[
        "El mercado recompensa la paciencia, no la prisa.",
        html.Span("- Jesse Livermore", className="autor"),
    ]),
    html.Div(id="page-content"),
])

# ─── HELPERS DE CALLBACK ──────────────────────────────────────────────────────

def _gr(est, val):
    """Retorna los 3 valores Dash Output para una tarjeta guardarrail."""
    return f"guardarrail-card {est}", f"guardarrail-indicador {est}", val

# ─── CALLBACKS ────────────────────────────────────────────────────────────────

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def render_page(pathname):
    if pathname and "/detail/" in pathname:
        symbol = pathname.split("/detail/")[-1].upper()
        return _pagina_detalle(symbol)
    return _pagina_principal()

@app.callback(
    [Output("reloj-NY", "children"), Output("reloj-LON", "children"),
     Output("reloj-TYO", "children"), Output("reloj-DXB", "children")],
    Input("tick-relojes", "n_intervals"),
)
def cb_relojes(_):
    zonas = ["America/New_York", "Europe/London", "Asia/Tokyo", "Asia/Dubai"]
    return [datetime.now(pytz.timezone(z)).strftime("%H:%M:%S") for z in zonas]

@app.callback(
    [Output("store-idioma", "data"),
     Output("h-titulo", "children"),
     Output("h-subtitulo", "children"),
     Output("lbl-idioma", "children"),
     Output("lbl-tf", "children"),
     Output("lbl-capital", "children"),
     Output("lbl-activos", "children"),
     Output("lbl-guardarrailes", "children"),
     Output("lbl-stats", "children"),
     Output("frase-barra", "children")],
    Input("radio-idioma", "value"),
)
def cb_idioma(idioma):
    t = TRANSLATIONS.get(idioma, TRANSLATIONS["es"])
    frase, autor = random.choice(QUOTES.get(idioma, QUOTES["es"]))
    return (idioma, t["title"], t["subtitle"], t["language"],
            t["timeframe"], t["capital"], t["assets"],
            t["guardrails"], t["stats"],
            [frase, html.Span(f"- {autor}", className="autor")])

@app.callback(Output("val-capital", "children"), Input("slider-capital", "value"))
def cb_capital(v): return f"{v}%"

@app.callback(
    [Output("btn-bot", "children"), Output("btn-bot", "className"),
     Output("led-dot", "className"), Output("led-txt", "children"),
     Output("store-bot", "data")],
    Input("btn-bot", "n_clicks"),
    State("store-bot", "data"),
    State("store-idioma", "data"),
    State("checklist-activos", "value"),
    State("store-tf", "data"),
    State("slider-capital", "value"),
)
def cb_bot(n, activo, idioma, activos_sel, tf, capital_pct):
    global _bot_thread, _bot_stop
    t = TRANSLATIONS.get(idioma, TRANSLATIONS["es"])
    if not n:
        return t["start"], "btn-principal", "led-dot desconectado", t["disconnected"], False
    nuevo = not activo
    if nuevo:
        activos_lista = ["BTC"] + [a for a in (activos_sel or []) if a != "BTC"]
        with _bot_lock:
            _bot_status["activos"] = [a for a in activos_lista if a != "BTC"]
        _bot_stop.clear()
        _bot_thread = threading.Thread(
            target=_bot_loop,
            args=(activos_lista, tf or "4H", capital_pct or 5),
            daemon=True,
        )
        _bot_thread.start()
        return t["stop"], "btn-principal stop", "led-dot", t["connected"], True
    _bot_stop.set()
    return t["start"], "btn-principal", "led-dot desconectado", t["disconnected"], False

@app.callback(Output("store-tf", "data"), Input("radio-tf", "value"))
def cb_tf(tf): return tf

@app.callback(
    Output("checklist-activos", "value"),
    Input("checklist-activos", "value"),
    prevent_initial_call=True,
)
def cb_limitar(val):
    if val and len(val) > 6:
        return val[:6]
    return val or []

# ── Gráfico principal BTC (siempre) ──────────────────────────────────────────

@app.callback(
    [Output("grafico-principal", "figure"),
     Output("scoring-bar", "children"),
     Output("gr-squeeze-card", "className"), Output("gr-squeeze-dot", "className"), Output("gr-squeeze-val", "children"),
     Output("gr-adx-card", "className"), Output("gr-adx-dot", "className"), Output("gr-adx-val", "children"),
     Output("gr-ema-card", "className"), Output("gr-ema-dot", "className"), Output("gr-ema-val", "children"),
     Output("gr-sr-card", "className"), Output("gr-sr-dot", "className"), Output("gr-sr-val", "children"),
     Output("gr-vol-card", "className"), Output("gr-vol-dot", "className"), Output("gr-vol-val", "children"),
     Output("gr-mtf-card", "className"), Output("gr-mtf-dot", "className"), Output("gr-mtf-val", "children"),
     Output("stat-precio", "children"), Output("stat-cambio", "children"), Output("stat-cambio", "style"),
     Output("stat-adx", "children"), Output("stat-momentum", "children"),
     Output("stat-squeeze", "children"), Output("stat-ema", "children"),
     ],
    [Input("tick-main", "n_intervals"), Input("store-tf", "data")],
    State("store-idioma", "data"),
)
def cb_btc_dashboard(_, tf, idioma):
    t = TRANSLATIONS.get(idioma, TRANSLATIONS["es"])

    def _fig_err():
        f = go.Figure()
        f.update_layout(paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
                        margin=dict(l=5,r=65,t=8,b=8),
                        annotations=[dict(text="Sin datos", showarrow=False,
                                        font=dict(color="#6b5520",size=16), x=0.5, y=0.5)])
        return f

    df = obtener_datos("BTC", tf or "4H")
    if df is None or df.empty:
        off = _gr("off", "-")
        bar = _scoring_bar_children("–", "sc-numero", t["wait"], {"color":"#a0a8c0"},
                                      {"width":"50%","background":"#2a2a3a"})
        return (_fig_err(), bar, *off,*off,*off,*off,*off,*off,
                "–","–",{"fontSize":"13px","color":"#a0a8c0"},"–","–","–","–")

    score, gr = calcular_score(df)
    fig = crear_grafico(df, "BTC", compacto=True)
    pct = f"{((score+100)/200)*100:.0f}%"

    if score >= 70:
        sc_cls, sc_lbl, sc_sty = "sc-numero long", t["long"], {"color":"#00ff88"}
        sc_bar = {"width":pct,"background":"#00ff88","transition":"width .8s ease"}
    elif score <= -70:
        sc_cls, sc_lbl, sc_sty = "sc-numero short", t["short"], {"color":"#ff3355"}
        sc_bar = {"width":pct,"background":"#ff3355","transition":"width .8s ease"}
    else:
        sc_cls, sc_lbl, sc_sty = "sc-numero", t["wait"], {"color":"#a0a8c0"}
        sc_bar = {"width":pct,"background":"#c8a84b","transition":"width .8s ease"}

    bar = _scoring_bar_children(str(score), sc_cls, sc_lbl, sc_sty, sc_bar)

    u = df.iloc[-1]
    ref = df["close"].iloc[-7] if len(df) >= 7 else df["close"].iloc[0]
    chg = (float(u["close"]) - float(ref)) / float(ref) * 100
    sgn = "+" if chg >= 0 else ""
    cclr = "#00ff88" if chg >= 0 else "#ff3355"

    return (
        fig, bar,
        *_gr(gr["SQUEEZE"]["estado"], gr["SQUEEZE"]["valor"]),
        *_gr(gr["ADX"]["estado"], gr["ADX"]["valor"]),
        *_gr(gr["EMA"]["estado"], gr["EMA"]["valor"]),
        *_gr(gr["S/R"]["estado"], gr["S/R"]["valor"]),
        *_gr(gr["VOL PROFILE"]["estado"], gr["VOL PROFILE"]["valor"]),
        *_gr("off", "-"),
        f"${float(u['close']):,.2f}",
        f"{sgn}{chg:.2f}%", {"fontSize":"13px","fontWeight":"600","color":cclr},
        f"{float(u['ADX']):.1f}", f"{float(u['momentum']):.2f}",
        "Sí" if bool(u["squeeze"]) else "No",
        "▲ Alcista" if u["EMA10"] > u["EMA55"] else "▼ Bajista",
    )

def _scoring_bar_children(numero, cls, etiqueta, sty_etq, sty_barra):
    return [
        html.Div(numero, id="sc-numero", className=cls),
        html.Div(className="sc-barra-wrap", children=[
            html.Div(id="sc-barra", className="sc-barra", style=sty_barra),
        ]),
        html.Div(etiqueta, id="sc-etiqueta", className="sc-etiqueta", style=sty_etq),
    ]

# ── Grid de activos seleccionados ─────────────────────────────────────────────

@app.callback(
    Output("asset-grid-section", "children"),
    [Input("checklist-activos", "value"),
     Input("store-tf", "data"),
     Input("tick-main", "n_intervals")],
)
def cb_asset_grid(activos, tf, _):
    if not activos:
        return []

    tf_ = tf or "4H"
    with ThreadPoolExecutor(max_workers=min(len(activos), 6)) as pool:
        futures = {pool.submit(obtener_datos, a, tf_, 100): a for a in activos}
        df_dict = {}
        for fut in as_completed(futures):
            a = futures[fut]
            try:
                df_dict[a] = fut.result()
            except Exception:
                df_dict[a] = None

    resultado = crear_mini_grafico(df_dict)
    if resultado is None:
        return []
    fig, rows = resultado

    altura = max(280 * rows, 280)

    links = [
        html.A(f"↗ {SYMBOL_MAP.get(a, a)}", href=f"/detail/{a}",
               target="_blank", className="link-detalle-mini")
        for a in activos if df_dict.get(a) is not None
    ]

    return html.Div(className="asset-grid-outer", children=[
        html.Div(className="grid-links-row", children=links),
        dcc.Graph(figure=fig,
                  config={"displayModeBar": "hover", "scrollZoom": True, "displaylogo": False,
                          "modeBarButtonsToRemove": ["select2d","lasso2d","toImage","sendDataToCloud"]},
                  style={"height": f"{altura}px"}),
    ])

# ── Página de Detalle ─────────────────────────────────────────────────────────

@app.callback(
    [Output("detail-graph", "figure"),
     Output("d-scoring-bar", "children"),
     Output("d-gr-squeeze-card", "className"), Output("d-gr-squeeze-dot", "className"), Output("d-gr-squeeze-val", "children"),
     Output("d-gr-adx-card", "className"), Output("d-gr-adx-dot", "className"), Output("d-gr-adx-val", "children"),
     Output("d-gr-ema-card", "className"), Output("d-gr-ema-dot", "className"), Output("d-gr-ema-val", "children"),
     Output("d-gr-sr-card", "className"), Output("d-gr-sr-dot", "className"), Output("d-gr-sr-val", "children"),
     Output("d-gr-vol-card", "className"), Output("d-gr-vol-dot", "className"), Output("d-gr-vol-val", "children"),
     ],
    [Input("detail-tick", "n_intervals"),
     Input("detail-tf-radio", "value")],
    State("url", "pathname"),
)
def cb_detail(_, tf, pathname):
    symbol = "BTC"
    if pathname and "/detail/" in pathname:
        symbol = pathname.split("/detail/")[-1].upper()

    df = obtener_datos(symbol, tf or "4H")
    if df is None or df.empty:
        off = _gr("off", "-")
        bar = _scoring_bar_children("–", "sc-numero", "–",
                                    {"color":"#a0a8c0"},
                                    {"width":"50%","background":"#2a2a3a"})
        f = go.Figure()
        f.update_layout(paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f")
        return (f, bar, *off,*off,*off,*off,*off)

    score, gr = calcular_score(df)
    fig = crear_grafico(df, symbol, compacto=False)
    pct = f"{((score+100)/200)*100:.0f}%"

    if score >= 70:
        sc_cls, sc_lbl, sc_sty = "sc-numero long", "LARGO", {"color":"#00ff88"}
        sc_bar = {"width":pct,"background":"#00ff88","transition":"width .8s ease"}
    elif score <= -70:
        sc_cls, sc_lbl, sc_sty = "sc-numero short", "CORTO", {"color":"#ff3355"}
        sc_bar = {"width":pct,"background":"#ff3355","transition":"width .8s ease"}
    else:
        sc_cls, sc_lbl, sc_sty = "sc-numero", "ESPERAR", {"color":"#a0a8c0"}
        sc_bar = {"width":pct,"background":"#c8a84b","transition":"width .8s ease"}

    bar = _scoring_bar_children(str(score), sc_cls, sc_lbl, sc_sty, sc_bar)

    return (
        fig, bar,
        *_gr(gr["SQUEEZE"]["estado"], gr["SQUEEZE"]["valor"]),
        *_gr(gr["ADX"]["estado"], gr["ADX"]["valor"]),
        *_gr(gr["EMA"]["estado"], gr["EMA"]["valor"]),
        *_gr(gr["S/R"]["estado"], gr["S/R"]["valor"]),
        *_gr(gr["VOL PROFILE"]["estado"], gr["VOL PROFILE"]["valor"]),
    )

# ── Helper: mini tarjeta de señal por activo ──────────────────────────────────
def _senal_card(ticker, score):
    if score is None:
        return html.Div([
            html.Span(ticker, style={"fontWeight": "700", "fontSize": "11px",
                                     "color": "#aaa", "minWidth": "38px"}),
            html.Span("–", style={"color": "#333344", "fontSize": "10px"}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "center", "padding": "3px 0",
                  "borderBottom": "1px solid #12121f"})

    abs_s = abs(score)
    pct = min(abs_s / 70 * 100, 100)

    if score >= 70:
        color, bar_c = "#00ff88", "#00ff88"
        label = "🟢 ENTRANDO"
    elif score > 15:
        color, bar_c = "#00cc66", "#00cc66"
        label = f"🟢 LONG {pct:.0f}%"
    elif score <= -70:
        color, bar_c = "#ff4444", "#ff4444"
        label = "🔴 ENTRANDO"
    elif score < -15:
        color, bar_c = "#cc3333", "#cc3333"
        label = f"🔴 SHORT {pct:.0f}%"
    else:
        color, bar_c = "#555566", "#252535"
        label = "⚪ NEUTRAL"

    return html.Div([
        html.Span(ticker, style={"fontWeight": "700", "fontSize": "11px",
                                 "color": "#e0e0e0", "minWidth": "38px"}),
        html.Div([
            html.Div(style={"height": "4px", "background": "#1a1a2e",
                      "borderRadius": "2px", "marginBottom": "3px",
                      "overflow": "hidden"},
                     children=[html.Div(style={"height": "100%",
                                              "width": f"{pct:.0f}%",
                                              "background": bar_c,
                                              "borderRadius": "2px"})]),
            html.Span(label, style={"fontSize": "9px", "color": color,
                                   "fontWeight": "600", "letterSpacing": "0.04em"}),
        ], style={"flex": "1", "marginLeft": "8px"}),
    ], style={"display": "flex", "alignItems": "center",
              "padding": "4px 0", "borderBottom": "1px solid #12121f"})

@app.callback(
    [Output("bot-balance-val", "children"),
     Output("bot-log", "children"),
     Output("telegram-estado", "children"),
     Output("telegram-estado", "style"),
     Output("mtf-1w", "children"),
     Output("mtf-1d", "children"),
     Output("mtf-4h", "children"),
     Output("mtf-direccion", "children"),
     Output("aero-ladder-val", "children"),
     Output("aero-racha-val", "children"),
     Output("aero-lock-val", "children"),
     Output("panel-senales-mini", "children")],
    Input("tick-bot-status", "n_intervals"),
    prevent_initial_call=True,
)
def cb_bot_status(_):
    with _bot_lock:
        bal = _bot_status["balance"]
        log = list(_bot_status["log"])
        mtf = dict(_bot_status.get("mtf", {}))
        scores = dict(_bot_status.get("scores", {}))
        activos_sel = list(_bot_status.get("activos", []))
        apal = _bot_status.get("apalancamiento", 2)

    bal_txt = f"${bal:,.2f}" if isinstance(bal, float) else "–"
    log_items = [
        html.Div(msg, style={"borderBottom": "1px solid #1a1a28", "paddingBottom": "1px",
                             "marginBottom": "1px"})
        for msg in log[:5]
    ] if log else [html.Div("Sin actividad", style={"color": "#3a3a50"})]

    # Estado Telegram — usa credenciales en memoria (cargadas al iniciar bot)
    tg_ok = bool(_tg_token and _tg_chatid)
    tg_txt = "✅ Conectado" if tg_ok else "⚠ No configurado"
    tg_style = {"color": "#00ff88", "fontSize": "12px"} if tg_ok else                {"color": "#f0c040", "fontSize": "12px"}

    # ── MTF display ────────────────────────────────────────────────────────────
    def _fmt_tf(data):
        if not data:
            return "–"
        est = data.get("estado", "–")
        sep = data.get("sep", 0.0)
        mom = data.get("mom", 0.0)
        ico = "🟢" if est == "alcista" else "🔴" if est == "bajista" else "🟡"
        lbl = {"alcista": "ALCISTA", "bajista": "BAJISTA"}.get(est, "COMP")
        arr = "▲" if mom >= 0 else "▼"
        return f"{ico} {lbl} {arr} sep:{sep:+.1f}%"

    mtf_1w_txt = _fmt_tf(mtf.get("1W"))
    mtf_1d_txt = _fmt_tf(mtf.get("1D"))
    mtf_4h_txt = _fmt_tf(mtf.get("4H"))

    if not mtf:
        mtf_dir = "⏳ Bot detenido"
    else:
        dir_ = mtf.get("direccion", "esperar")
        lo = mtf.get("long_ok", False)
        so = mtf.get("short_ok", False)
        if dir_ == "long":
            mtf_dir = "🟢 BUSCANDO LONG ⛔ SHORT OFF" if lo else "🟡 LONG pendiente 4H ⛔ SHORT OFF"
        elif dir_ == "short":
            mtf_dir = "🔴 BUSCANDO SHORT ⛔ LONG OFF" if so else "🟡 SHORT pendiente 4H ⛔ LONG OFF"
        else:
            mtf_dir = "⏳ ESPERAR — sin dirección clara"

    # ── Panel senales mini ────────────────────────────────────────────────────
    activos_sel = activos_sel or []
    if not activos_sel:
        senales = html.Div("⬆️ Selecciona activos arriba",
            style={"color": "#f0c040", "fontSize": "11px", "padding": "8px 4px",
                   "border": "1px dashed #f0c040", "borderRadius": "4px",
                   "textAlign": "center", "marginTop": "4px"})
    elif not scores:
        senales = html.Div("⏳ Inicia el bot para ver señales",
            style={"color": "#f0c040", "fontSize": "11px", "padding": "8px 4px",
                   "border": "1px dashed #f0c040", "borderRadius": "4px",
                   "textAlign": "center", "marginTop": "4px"})
    else:
        senales = html.Div([_senal_card(a, scores.get(a)) for a in activos_sel],
            style={"padding": "4px", "background": "#0f0f1a", "borderRadius": "4px",
                   "border": "1px solid #1a1a2e"})

    # ── AERO LADDER display ───────────────────────────────────────────────────
    aero_apal = f"{apal}X"
    try:
        st = _load_bot_state()
        aero_racha = f"🔥 {st.get('racha_ganadora', 0)} ganadas"
        aero_lock = f"${st.get('profit_lock_acumulado', 0.0):.2f}"
    except Exception:
        aero_racha = "–"
        aero_lock = "–"

    return bal_txt, log_items, tg_txt, tg_style, mtf_1w_txt, mtf_1d_txt, mtf_4h_txt, mtf_dir, aero_apal, aero_racha, aero_lock, senales
    
if __name__ == "__main__":
    print("=" * 50)
    print(" AERO BOT PRO — Elite v2.1")
    print(" AERO LADDER v2 | Max 5X | Profit Lock | Cooldown")
    print(" http://localhost:8051")
    print(f" [CHECK] Label activos ES: {TRANSLATIONS['es']['assets']}")
    print(f" [CHECK] panel-senales-mini: OK")
    print("=" * 50)
    app.run(debug=False, port=8051, host="0.0.0.0", use_reloader=False, 
        dev_tools_hot_reload=False, dev_tools_props_check=False)
