"""
AERO BOT PRO - Dashboard Elite v3.3
Puerto 8051 | Multi-pagina | MTF v3 predictivo
AERO LADDER v2 | calcular_score v3.3 anticipatorio
"""

import sys
import io
# Forzar UTF-8 en consola Windows (evita UnicodeEncodeError con emojis en print)
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
                print("[CICLO RESET] 30 dias transcurridos. Nuevo ciclo AERO LADDER.")
                return default
        except Exception:
            pass
        # Reset si racha llegó a 0 con 2 pérdidas seguidas
        if state.get("racha_ganadora", 0) == 0 and state.get("perdidas_consecutivas_nivel_actual", 0) >= _MAX_PERDIDAS_RESET:
            print("[CICLO RESET] Racha perdida. Nuevo ciclo AERO LADDER.")
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
            print(f"[Profit Lock] +${profit_congelar:.2f} congelado al subir a {nuevo_apal}X")

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
            print("[RESET AERO LADDER] 2 perdidas seguidas en mismo nivel. Vuelta a 2X.")

        # Cooldown 24h si pérdida en 5X > 2% del capital total
        if apalancamiento_usado >= 5 and abs(pnl_pct) >= 2.0:
            state["cooldown_hasta"] = (datetime.now() + timedelta(hours=_MAX_COOLDOWN_HORAS)).isoformat()
            print(f"[COOLDOWN] 24h en 2X por perdida grande ({abs(pnl_pct):.2f}%) en 5X.")

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
        "connected": "CONECTADO", "disconnected": "DESCONECTADO", "connecting": "CONECTANDO...",
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
        "connected": "CONNECTED", "disconnected": "DISCONNECTED", "connecting": "CONNECTING...",
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
        "connected": "CONNESSO", "disconnected": "DISCONNESSO", "connecting": "CONNESSIONE...",
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
        "connected": "CONNECTÉ", "disconnected": "DÉCONNECTÉ", "connecting": "CONNEXION...",
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
        "connected": "VERBUNDEN", "disconnected": "GETRENNT", "connecting": "VERBINDE...",
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
        "connected": "已连接", "disconnected": "未连接", "connecting": "连接中...",
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
        "connected": "연결됨", "disconnected": "연결 안됨", "connecting": "연결 중...",
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
        "connected": "接続済み", "disconnected": "未接続", "connecting": "接続中...",
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
    "1W": "1w", "1D": "1d", "4H": "4h", "2H": "2h", "1H": "1h", "15m": "15m",
}

# ─── S/R LOOKBACK (velas mínimas por TF para persistencia garantizada) ────────
# STRATEGY.md Regla V3: 4H=45 días, 1D=150 días, 1W=365 días
_SR_LOOKBACK = {
    "1W":  55,   # 365 días / 7 ≈ 52 semanas + buffer
    "1D": 160,   # 150 días + buffer
    "4H": 280,   # 45 días × 6 velas/día + buffer
    "2H": 300,   # 45 días × 12 velas/día (cap por rendimiento)
    "1H": 300,   # cap por rendimiento
    "15m": 200,  # default
}

# ─── BOT GLOBAL STATE ─────────────────────────────────────────────────────────

_bot_thread = None
_bot_stop = threading.Event()
_bot_lock = threading.Lock()
_bot_status = {"balance": None, "posicion": {}, "log": [], "mtf": {}, "scores": {}, "activos": [], "pnl": {}}

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

def _detectar_sr_persistentes(df, n_soporte=5, n_resistencia=5, tolerancia_pct=0.015):
    """
    STRATEGY.md Reglas V1-V7 — Detección de S/R persistentes.

    Parámetros calibrados para encontrar ZONAS REALES (no precios aleatorios):
      - order=15: solo pivots con ventana de 15 barras a cada lado (muy significativos)
      - tolerancia=1.5%: agrupa precios dentro del 1.5% como una sola zona
      - n=5+5: candidatos; en el chart solo se dibujan los de fuerza>=2 (2+ toques)
      - fuerza=1 → precio visitado una sola vez → no es S/R, ignorar en chart

    Retorna: lista de dicts {precio, tipo, fuerza}
      - tipo:   'soporte' | 'resistencia'
      - fuerza: número de pivots agrupados en ese nivel (1=fresco, 2+=zona real)
      - STRATEGY.md V6: misma función usada por chart Y calcular_score()
    """
    max_idx = argrelextrema(df["high"].values, np.greater, order=15)[0]
    min_idx = argrelextrema(df["low"].values,  np.less,   order=15)[0]
    precio_actual = float(df["close"].iloc[-1])

    def _agrupar(indices, columna):
        if len(indices) == 0:
            return []
        precios = sorted(float(df[columna].iloc[i]) for i in indices)
        grupos, grupo = [], [precios[0]]
        for p in precios[1:]:
            if (p - grupo[0]) / grupo[0] < tolerancia_pct:
                grupo.append(p)
            else:
                grupos.append(grupo)
                grupo = [p]
        grupos.append(grupo)
        return [{"precio": float(np.mean(g)), "fuerza": len(g)} for g in grupos]

    todos_res = _agrupar(max_idx, "high")
    todos_sop = _agrupar(min_idx, "low")

    # Resistencias: estrictamente por ENCIMA del precio actual
    resistencias = sorted(
        [r for r in todos_res if r["precio"] > precio_actual],
        key=lambda x: x["precio"]          # ascendente → los 2 más cercanos primero
    )[:n_resistencia]

    # Soportes: estrictamente por DEBAJO del precio actual
    soportes = sorted(
        [s for s in todos_sop if s["precio"] < precio_actual],
        key=lambda x: x["precio"], reverse=True  # descendente → los 2 más cercanos primero
    )[:n_soporte]

    return [{"tipo": "resistencia", **r} for r in resistencias] + \
           [{"tipo": "soporte",     **s} for s in soportes]


def _detectar_trendlines(df, order=10, n_pivots=4):
    """
    Detecta trendlines DIAGONALES usando solo los ÚLTIMOS N pivots significativos.

    L99 Eduardo (mayo 2026): usar todos los pivots históricos producía líneas casi
    planas. Con los últimos N pivots se obtiene el CANAL REAL del precio actual.

    Fix fractal borde derecho: argrelextrema no detecta pivots dentro de las últimas
    `order` barras (no hay suficientes barras después para confirmar). Si el último
    pivot confirmado está a más de `order` barras del borde, se agrega el mínimo/máximo
    de esa ventana final como punto adicional de la regresión.

    Retorna dict con keys 'soporte' y 'resistencia', cada uno:
      {"x": [t_inicio, t_fin], "y": [y_inicio, y_fin], "slope": float}
      o None si no hay suficientes pivots.
    """
    max_idx = argrelextrema(df["high"].values, np.greater, order=order)[0]
    min_idx = argrelextrema(df["low"].values,  np.less,   order=order)[0]
    result  = {"soporte": None, "resistencia": None}
    n       = len(df)

    def _agregar_borde_bajo(idx_arr):
        """Si el último pivot detectado está lejos del borde, añade el mínimo reciente."""
        if len(idx_arr) == 0:
            return idx_arr
        ultimo = idx_arr[-1]
        if n - 1 - ultimo > order:          # hay al menos `order` barras sin pivot
            ventana = df["low"].values[ultimo + 1:]
            if len(ventana) > 0:
                pos_rel = int(np.argmin(ventana))
                pos_abs = ultimo + 1 + pos_rel
                # Solo añadir si es realmente más bajo que el último pivot confirmado
                if df["low"].values[pos_abs] < df["low"].values[ultimo]:
                    return np.append(idx_arr, pos_abs)
        return idx_arr

    def _agregar_borde_alto(idx_arr):
        """Si el último pivot detectado está lejos del borde, añade el máximo reciente."""
        if len(idx_arr) == 0:
            return idx_arr
        ultimo = idx_arr[-1]
        if n - 1 - ultimo > order:
            ventana = df["high"].values[ultimo + 1:]
            if len(ventana) > 0:
                pos_rel = int(np.argmax(ventana))
                pos_abs = ultimo + 1 + pos_rel
                if df["high"].values[pos_abs] > df["high"].values[ultimo]:
                    return np.append(idx_arr, pos_abs)
        return idx_arr

    max_idx = _agregar_borde_alto(max_idx)
    min_idx = _agregar_borde_bajo(min_idx)

    # ── TRENDLINE RESISTENCIA — últimos N máximos ──────────────────────────
    if len(max_idx) >= 2:
        recientes = max_idx[-min(n_pivots, len(max_idx)):]
        xs   = recientes.astype(float)
        ys   = df["high"].values[recientes].astype(float)
        m, b = np.polyfit(xs, ys, 1)
        x0   = int(recientes[0])
        x1   = n - 1
        result["resistencia"] = {
            "x": [df["tiempo"].iloc[x0], df["tiempo"].iloc[x1]],
            "y": [m * x0 + b,            m * x1 + b],
            "slope": m,
        }

    # ── TRENDLINE SOPORTE — últimos N mínimos ─────────────────────────────
    if len(min_idx) >= 2:
        recientes = min_idx[-min(n_pivots, len(min_idx)):]
        xs   = recientes.astype(float)
        ys   = df["low"].values[recientes].astype(float)
        m, b = np.polyfit(xs, ys, 1)
        x0   = int(recientes[0])
        x1   = n - 1
        result["soporte"] = {
            "x": [df["tiempo"].iloc[x0], df["tiempo"].iloc[x1]],
            "y": [m * x0 + b,            m * x1 + b],
            "slope": m,
        }

    return result


def _detectar_ondas_elliott(df, order=6):
    """
    Detecta y etiqueta Ondas de Elliott automáticamente.

    Secuencia buscada: W0 → W1 → W2 → W3 → W4 → W5 → Wa → Wb → Wc
    Patrón alcista:  L(0) H(1) L(2) H(3) L(4) H(5) L(a) H(b) L(c)
    Patrón bajista:  H(0) L(1) H(2) L(3) H(4) L(5) H(a) L(b) H(c)

    Reglas Elliott aplicadas:
    - Alcista: W2>W0 (no retrocede 100%), W3>W1 (nuevo máximo), W4>W0, W5>W3
    - Bajista: invertidas
    - Si no se encuentra patrón válido: etiqueta los últimos N pivots (best-effort)

    Retorna: lista de dicts {tiempo, precio, label, tipo} o []
    """
    if len(df) < order * 4:
        return []

    highs_idx = argrelextrema(df["high"].values, np.greater, order=order)[0]
    lows_idx  = argrelextrema(df["low"].values,  np.less,   order=order)[0]

    if len(highs_idx) < 3 or len(lows_idx) < 3:
        return []

    # Combinar y ordenar todos los pivots cronológicamente
    pivots = []
    for i in highs_idx:
        pivots.append({"idx": i, "tipo": "H",
                       "precio": float(df["high"].iloc[i]),
                       "tiempo": df["tiempo"].iloc[i]})
    for i in lows_idx:
        pivots.append({"idx": i, "tipo": "L",
                       "precio": float(df["low"].iloc[i]),
                       "tiempo": df["tiempo"].iloc[i]})
    pivots.sort(key=lambda x: x["idx"])

    # Limpiar: alternar H/L estrictamente, más extremo gana si hay consecutivos
    clean = []
    for p in pivots:
        if not clean or clean[-1]["tipo"] != p["tipo"]:
            clean.append(dict(p))
        else:
            if p["tipo"] == "H" and p["precio"] > clean[-1]["precio"]:
                clean[-1] = dict(p)
            elif p["tipo"] == "L" and p["precio"] < clean[-1]["precio"]:
                clean[-1] = dict(p)

    if len(clean) < 6:
        return []

    wave_labels = ["W0", "W1", "W2", "W3", "W4", "W5", "Wa", "Wb", "Wc"]
    n_take      = min(9, len(clean))
    best        = None

    # Buscar patrón válido desde los pivots más recientes hacia atrás
    for start in range(max(0, len(clean) - 14), len(clean) - 5):
        seg     = clean[start : start + n_take]
        if len(seg) < 6:
            continue

        is_bull = seg[0]["tipo"] == "L"
        exp     = (["L","H"] * 5)[:len(seg)] if is_bull else (["H","L"] * 5)[:len(seg)]
        if not all(p["tipo"] == e for p, e in zip(seg, exp)):
            continue

        n  = min(6, len(seg))
        pp = [seg[i]["precio"] for i in range(n)]

        if is_bull:
            ok = (
                (n < 3 or pp[2] > pp[0]) and   # W2 no retrocede al inicio
                (n < 4 or pp[3] > pp[1]) and   # W3 nuevo máximo
                (n < 5 or pp[4] > pp[0]) and   # W4 sobre W0
                (n < 6 or pp[5] > pp[3])        # W5 nuevo máximo
            )
        else:
            ok = (
                (n < 3 or pp[2] < pp[0]) and
                (n < 4 or pp[3] < pp[1]) and
                (n < 5 or pp[4] < pp[0]) and
                (n < 6 or pp[5] < pp[3])
            )

        if ok:
            best = seg[:n_take]
            break   # más reciente que cumpla reglas

    if best is None:
        # Fallback: últimos pivots sin validación (best-effort)
        best = clean[-(min(8, len(clean))):]

    labels = wave_labels[:len(best)]
    return [{**p, "label": lb} for p, lb in zip(best, labels)]


def _analizar_mtf(activo, ema_comp_pct=1.0):
    """
    MTF v3 — Predictivo: 4H predice, 2H confirma, 1W/1D advierten.
    Filosofía v3:
    - 4H: determina long_ok / short_ok — sola, sin depender de 1W/1D
    - 2H: confirma fuerza ("fuerte" si alineado con 4H, "débil" si no)
    - 1W divergente: penalización 15 pts al score — advierte pero NO bloquea
    - 1D divergente: penalización 10 pts al score — advierte pero NO bloquea
    - 2H no confirma: penalización 8 pts adicionales
    El bot opera en la realidad actual (4H+2H), no espera alineación global.
    """
    _default = {
        "activo": activo,
        "1W": {"estado": "–", "sep": 0.0, "mom": 0.0},
        "1D": {"estado": "–", "sep": 0.0, "mom": 0.0},
        "4H": {"estado": "–", "sep": 0.0, "mom": 0.0},
        "2H": {"estado": "–", "sep": 0.0, "mom": 0.0},
        "direccion": "esperar",
        "long_ok": False,
        "short_ok": False,
        "fuerza": "–",
        "advertencia": "",
        "penalizacion": 0,
    }
    try:
        # Fetch paralelo: 4 TF a la vez
        with ThreadPoolExecutor(max_workers=4) as pool:
            f1w = pool.submit(obtener_datos, activo, "1W", 100)
            f1d = pool.submit(obtener_datos, activo, "1D", 100)
            f4h = pool.submit(obtener_datos, activo, "4H", 100)
            f2h = pool.submit(obtener_datos, activo, "2H", 100)
            df_1w = f1w.result()
            df_1d = f1d.result()
            df_4h = f4h.result()
            df_2h = f2h.result()

        if any(df is None or df.empty for df in [df_1w, df_1d, df_4h, df_2h]):
            return _default

        def _tf_info(df):
            """Devuelve dict con estado, sep% y mom del último cierre."""
            u = df.iloc[-1]
            sep = (float(u["EMA10"]) - float(u["EMA55"])) / float(u["EMA55"]) * 100
            mom = float(u["momentum"])
            if sep > ema_comp_pct and mom > 0:
                estado = "alcista"
            elif sep < -ema_comp_pct and mom < 0:
                estado = "bajista"
            else:
                estado = "compresion"
            return {"estado": estado, "sep": round(sep, 2), "mom": round(mom, 2)}

        r1w = _tf_info(df_1w)
        r1d = _tf_info(df_1d)
        r4h = _tf_info(df_4h)
        r2h = _tf_info(df_2h)

        result = {**_default, "1W": r1w, "1D": r1d, "4H": r4h, "2H": r2h}

        # ── PASO 1: 4H PREDICE — única fuente de long_ok / short_ok ───────────
        if r4h["estado"] == "alcista":
            result["long_ok"]    = True
            result["direccion"]  = "long"
        elif r4h["estado"] == "bajista":
            result["short_ok"]   = True
            result["direccion"]  = "short"
        else:
            result["direccion"]  = "esperar"

        # ── PASO 2: 2H CONFIRMA — fuerza de la señal ──────────────────────────
        penalizacion = 0
        advertencias = []

        if result["long_ok"]:
            if r2h["estado"] == "alcista":
                result["fuerza"] = "fuerte"
            else:
                result["fuerza"] = "débil"
                penalizacion += 8
                advertencias.append("2H sin confirmar")
        elif result["short_ok"]:
            if r2h["estado"] == "bajista":
                result["fuerza"] = "fuerte"
            else:
                result["fuerza"] = "débil"
                penalizacion += 8
                advertencias.append("2H sin confirmar")

        # ── PASO 3: 1W ADVIERTE — no bloquea, solo penaliza ───────────────────
        if result["long_ok"] and r1w["estado"] == "bajista":
            penalizacion += 15
            advertencias.append("⚠ 1W bajista")
        elif result["short_ok"] and r1w["estado"] == "alcista":
            penalizacion += 15
            advertencias.append("⚠ 1W alcista")

        # ── PASO 4: 1D ADVIERTE — no bloquea, solo penaliza ───────────────────
        if result["long_ok"] and r1d["estado"] == "bajista":
            penalizacion += 10
            advertencias.append("⚠ 1D bajista")
        elif result["short_ok"] and r1d["estado"] == "alcista":
            penalizacion += 10
            advertencias.append("⚠ 1D alcista")

        result["penalizacion"] = penalizacion
        result["advertencia"]  = " | ".join(advertencias) if advertencias else ""

        return result

    except Exception as e:
        print(f"[⚠ MTF] {activo}: {e}")
        return _default

def calcular_score(df):
    """
    Score anticipatorio v3.1 — predice dirección futura, no describe el presente.

    Cambios v3.1 (mayo 2026):
    - Squeeze peak/valley: pesos +/-40 (era 25). Peak es la señal más anticipatoria.
    - Squeeze accel: +/-30 (era 25). Diferencia peak vs accel porque peak es más temprano.
    - EMA slope sin aceleración: +/-8 (era 12). EMA es reactiva — no debe dominar.
    - ADX direction-aware: amplifica la señal dominante, no siempre suma positivo.
      ADX mide FUERZA, no dirección. Si el bot está en short, ADX creciente confirma short.
    - S/R tolerancia 1.5% (era 0.5%). Detecta rechazo cerca de resistencia/soporte.
    - S/R peso +/-20 (era 15). Rechazo en resistencia es señal de entrada fuerte.
    - S/R order=5 (era 10). Detecta niveles más recientes y relevantes.

    Cambios v3.2 (mayo 2026):
    - Squeeze bear_post_peak: +/-25 — squeeze cayendo en terreno positivo (1-2 barras post-techo).
      Soluciona el caso donde el peak ya paso pero el momentum sigue cayendo y positivo.
    - Squeeze bull_post_valley: +/-25 — squeeze subiendo en terreno negativo (1-2 barras post-fondo).
    - Fallback direction-aware: positivo-cayendo = -10 (era +10). Perder fuerza es bajista, no alcista.
      negativo-subiendo = +10 (era -10). Recuperarse es alcista aunque siga negativo.

    Cambios v3.3 (mayo 2026):
    - S/R breakout detection (Eduardo Andrade):
      Si soporte testeado se rompe hacia abajo → -25 (breakout bajista, mas fuerte que rechazo)
      Si resistencia se rompe hacia arriba → +25 (breakout alcista, techo se convierte en soporte)
      Rango de deteccion breakout: 0-5% mas alla del nivel.
      Zonas de rebote/rechazo mantienen +-20 con distancia direccional (no abs).
      Si soporte y resistencia dan senales, gana la de mayor peso absoluto.

    Cambios v3.4 (mayo 2026):
    - K-8: Ultimo estiron (Eduardo Andrade, 27 mayo 2026):
      Si precio toca resistencia (-20 S/R base) Y tendencia es bajista (EMA10<EMA55 o squeeze<0)
      → bonus adicional -20 pts. Total: -40 pts solo de S/R.
      El mercado engana: parece que no llegara al techo, pero lo toca y cae.
      Guardarrail S/R muestra prefijo "K8" cuando activo.
    - K-9: Segunda confirmacion (Eduardo Andrade, 27 mayo 2026):
      Si EMA10 < EMA55 (cruce bajista establecido) Y squeeze < 0 Y precio NO esta en resistencia
      → -15 pts. Entrada mas tardia pero valida. "Con mas cuidado" (menor peso que K-8).
      Mutuamente exclusivo con K-8.
    """
    if len(df) < 10:
        return 0, {}

    u = df.iloc[-1]
    pts, gr = 0, {}

    # ── EMA SLOPE ANTICIPATORIO ───────────────────────────────────────────────
    # Pendiente = cambio % de EMA10 en 3 velas. Solo pesa fuerte si acelera.
    ema10_now  = float(df.iloc[-1]["EMA10"])
    ema10_p3   = float(df.iloc[-4]["EMA10"])
    ema10_p6   = float(df.iloc[-7]["EMA10"])
    slope_now  = (ema10_now - ema10_p3) / ema10_p3 * 100
    slope_prev = (ema10_p3  - ema10_p6) / ema10_p6 * 100

    bull_ema_strong = slope_now > 0 and slope_now > slope_prev
    bear_ema_strong = slope_now < 0 and slope_now < slope_prev

    if bull_ema_strong:
        pts += 30; ema_est = "on";  ema_val = f"▲ slope {slope_now:+.3f}%"
    elif slope_now > 0:
        pts +=  8; ema_est = "off"; ema_val = f"↗ slope {slope_now:+.3f}%"
    elif bear_ema_strong:
        pts -= 30; ema_est = "war"; ema_val = f"▼ slope {slope_now:+.3f}%"
    else:
        pts -=  8; ema_est = "war"; ema_val = f"↘ slope {slope_now:+.3f}%"
    gr["EMA"] = {"estado": ema_est, "valor": ema_val}

    # ── SQUEEZE MOMENTUM — PEAK/VALLEY + ACELERACIÓN (v3.2) ─────────────────
    # Peak/Valley: giro exacto — señal más anticipatoria (±40).
    # Post-peak/valley: 3 barras consecutivas declinando — todavía en terreno positivo/negativo (±25).
    # Accel: ya cruzó cero, acelerando en nueva dirección (±30).
    # Fallback: positivo-creciendo +10 / positivo-cayendo -10 / negativo-subiendo +10 / negativo-cayendo -10.
    mom_now   = float(df.iloc[-1]["momentum"])
    mom_prev  = float(df.iloc[-2]["momentum"])
    mom_prev2 = float(df.iloc[-3]["momentum"])

    bull_valley     = mom_prev2 > mom_prev and mom_prev < mom_now                   # min local → giro alcista
    bull_post_valley= mom_prev2 < mom_prev < mom_now and mom_now < 0               # post-fondo subiendo, aún negativo
    bull_accel      = mom_now > mom_prev and mom_prev > 0                           # acelerando positivo
    bear_peak       = mom_prev2 < mom_prev and mom_prev > mom_now                   # max local → giro bajista
    bear_post_peak  = mom_prev2 > mom_prev > mom_now and mom_now > 0               # post-techo cayendo, aún positivo
    bear_accel      = mom_now < mom_prev and mom_prev < 0                           # acelerando negativo

    growing = bool(mom_now > mom_prev)
    if bear_peak:
        pts -= 40; mom_est = "war"      # techo exacto: señal más anticipatoria SHORT
    elif bull_valley:
        pts += 40; mom_est = "on"       # fondo exacto: señal más anticipatoria LONG
    elif bear_post_peak:
        pts -= 25; mom_est = "war"      # post-techo: squeeze cayendo aún positivo = SHORT fuerte
    elif bull_post_valley:
        pts += 25; mom_est = "on"       # post-fondo: squeeze subiendo aún negativo = LONG fuerte
    elif bear_accel:
        pts -= 30; mom_est = "war"      # ya negativo y acelerando = confirmación SHORT
    elif bull_accel:
        pts += 30; mom_est = "on"       # ya positivo y acelerando = confirmación LONG
    elif mom_now > 0 and growing:
        pts += 10; mom_est = "off"      # positivo creciendo = leve alcista
    elif mom_now > 0:
        pts -= 10; mom_est = "war"      # positivo pero cayendo = perdiendo fuerza = bajista
    elif mom_now < 0 and not growing:
        pts -= 10; mom_est = "war"      # negativo cayendo = leve bajista
    else:
        pts += 10; mom_est = "off"      # negativo subiendo = posible recuperación
    gr["SQUEEZE"] = {"estado": mom_est, "valor": f"{'▲' if growing else '▼'} {mom_now:.1f}"}

    # ── VOLUME PROFILE POC ────────────────────────────────────────────────────
    _, _, poc = _volume_profile(df)
    sobre_poc = bool(u["close"] > poc)
    pct_poc   = (u["close"] - poc) / poc * 100
    pts += 10 if sobre_poc else -10
    gr["VOL PROFILE"] = {"estado": "on" if sobre_poc else "war",
                         "valor": f"{'↑' if sobre_poc else '↓'}{abs(pct_poc):.1f}%"}

    # ── SOPORTE / RESISTENCIA + BREAKOUT (v3.3) ─────────────────────────────
    # 4 casos posibles:
    #   precio SOBRE soporte  (0–1.5% encima)  → +20 (zona de rebote)
    #   precio ROMPIÓ soporte (0–5%  debajo)   → -25 (breakout bajista — más fuerte que el rechazo)
    #   precio BAJO resistencia (0–1.5% debajo) → -20 (zona de rechazo)
    #   precio ROMPIÓ resistencia (0–5% encima) → +25 (breakout alcista — soporte anterior)
    # Si ambos niveles dan señal, gana el de mayor abs(pts) para reflejar el más relevante.
    # S/R via función compartida — STRATEGY.md V6 (única fuente de verdad)
    precio  = float(u["close"])
    sr_pts, sr_val, sr_est = 0, "-", "off"

    _niveles_sc      = _detectar_sr_persistentes(df)
    _soportes_sc     = [n for n in _niveles_sc if n["tipo"] == "soporte"]
    _resistencias_sc = [n for n in _niveles_sc if n["tipo"] == "resistencia"]

    if _soportes_sc:
        s_near = min(_soportes_sc, key=lambda n: abs(n["precio"] - precio))["precio"]
        dist_s = (precio - s_near) / precio
        if 0 <= dist_s < 0.015:
            sr_pts, sr_val, sr_est = 20, f"S {s_near:.0f}", "on"
        elif -0.05 < dist_s < 0:
            sr_pts, sr_val, sr_est = -25, f"BREAK↓ {s_near:.0f}", "war"

    if _resistencias_sc:
        r_near = min(_resistencias_sc, key=lambda n: abs(n["precio"] - precio))["precio"]
        dist_r = (precio - r_near) / precio
        r_pts_new, r_val_new, r_est_new = 0, "-", "off"
        if -0.015 < dist_r <= 0:
            r_pts_new, r_val_new, r_est_new = -20, f"R {r_near:.0f}", "war"
        elif 0 < dist_r < 0.05:
            r_pts_new, r_val_new, r_est_new = 25, f"BREAK↑ {r_near:.0f}", "on"
        if abs(r_pts_new) >= abs(sr_pts):
            sr_pts, sr_val, sr_est = r_pts_new, r_val_new, r_est_new

    pts += sr_pts
    gr["S/R"] = {"estado": sr_est, "valor": sr_val}

    # ── CONFIRMACIÓN CRUZADA — Squeeze peak/valley + S/R alineados ───────────
    # Cuando el squeeze gira EN un nivel clave, la señal combinada es más fuerte
    # que cada indicador por separado. Bonus adicional de ±15 pts.
    if bear_peak and sr_est == "war":
        pts -= 18   # squeeze en techo + rechazo de resistencia = setup SHORT fuerte
    elif bull_valley and sr_est == "on":
        pts += 18   # squeeze en fondo + rebote de soporte = setup LONG fuerte

    # ── K-8: ÚLTIMO ESTIRÓN — resistencia tocada en tendencia bajista ─────────
    # Eduardo K-8 (27 mayo 2026): el mercado engaña — parece que no llegará al techo
    # pero da un último empujón y lo toca. Si la tendencia ya es bajista (EMA o squeeze),
    # ese toque es una TRAMPA. Bonus SHORT -20 adicionales (total con base S/R: -40).
    ema55_now         = float(df.iloc[-1]["EMA55"])
    _contexto_bajista = (ema10_now < ema55_now) or (mom_now < 0)
    _en_resistencia   = (sr_pts == -20)   # precio tocando resistencia (no breakout)

    if _en_resistencia and _contexto_bajista:
        pts -= 20   # K-8: último estirón — resistencia + tendencia bajista = SHORT fuerte
        gr["S/R"]["valor"] = "K8 " + gr["S/R"]["valor"]

    # ── K-9: SEGUNDA CONFIRMACIÓN — cruce EMA bajista + squeeze negativo ──────
    # Eduardo K-9 (27 mayo 2026): entrada más tardía pero válida.
    # EMA roja (55) ya cruzó encima de azul (10) Y squeeze ya es negativo.
    # "Ya vamos con más cuidado" — Eduardo. Peso -15 (menor que K-8).
    # Mutuamente exclusivo con K-8: si el precio está en resistencia es K-8 (más temprano).
    elif not _en_resistencia and (ema10_now < ema55_now) and (mom_now < 0):
        pts -= 15   # K-9: segunda confirmación bajista

    # ── ADX — AMPLIFICADOR DE DIRECCIÓN (calculado al final) ─────────────────
    # ADX mide FUERZA de tendencia, no dirección.
    # Se calcula DESPUÉS de los demás para amplificar la señal dominante.
    adx_now   = float(df.iloc[-1]["ADX"])
    adx_prev  = float(df.iloc[-2]["ADX"])
    adx_min10 = float(df["ADX"].iloc[-10:].min())

    adx_emerging = adx_min10 < 20 and adx_now > adx_prev
    adx_strong   = adx_now >= 25 and adx_now > adx_prev
    adx_bonus    = 10 if adx_emerging else (5 if adx_strong else 0)

    if adx_bonus > 0:
        # Direction-aware: amplifica lo que ya domina (pts antes de ADX)
        if pts >= 0:
            pts += adx_bonus; adx_est = "on"
        else:
            pts -= adx_bonus; adx_est = "on"
        adx_txt = f"↑ {adx_now:.1f} ({'naciendo' if adx_emerging else 'fuerte'})"
    elif adx_now < 20:
        pts -= 5; adx_est = "off"; adx_txt = f"↓ {adx_now:.1f} (sin fuerza)"
    else:
        adx_est = "off"; adx_txt = f"{adx_now:.1f}"
    gr["ADX"] = {"estado": adx_est, "valor": adx_txt}

    gr["MTF"] = {"estado": "off", "valor": "-"}
    return max(-100, min(100, int(pts))), gr

def crear_grafico(df, activo="BTC", compacto=False, tf="4H", show_elliott=False):
    simbolo = SYMBOL_MAP.get(activo, "BTC/USDT")
    niveles, vols, poc = _volume_profile(df)
    poc_idx = int(np.argmax(vols))
    vol_max = max(vols) or 1

    # Trendlines diagonales — STRATEGY.md V1-V6
    # Conectan últimos pivots de máximos (resistencia) y mínimos (soporte).
    # Pendiente negativa en resistencia = techos bajando = estructura bajista.
    # Pendiente positiva en soporte     = pisos subiendo = estructura alcista.
    COLOR_SOPORTE = "#00e676"
    COLOR_RESIST  = "#ff4444"

    # Trendlines desactivadas por decisión de Eduardo (L99, mayo 2026).
    # _detectar_trendlines() queda en el código para uso futuro.

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

    # Trendlines desactivadas — ver nota arriba.

    # S/R horizontales: eliminadas del chart por decisión de Eduardo (L99).
    # _detectar_sr_persistentes() sigue usándose en calcular_score() para el scoring,
    # pero NO se dibujan líneas horizontales en el gráfico.

    # ── Ondas de Elliott (cuando toggle ON) ──────────────────────────────────
    if show_elliott:
        _EW_ORDER = {"1W": 3, "1D": 4, "4H": 6, "2H": 7, "1H": 8, "15m": 5}
        _ew_order = _EW_ORDER.get(tf, 6)
        _ondas    = _detectar_ondas_elliott(df, order=_ew_order)
        if len(_ondas) >= 5:
            # Colores: azul=impulsivas, rojo=correctivas, verde=Wb (rebote)
            _EW_COL = {
                "W0": "#888888",
                "W1": "#2196F3", "W2": "#ef5350",
                "W3": "#2196F3", "W4": "#ef5350",
                "W5": "#2196F3",
                "Wa": "#ef5350", "Wb": "#26a69a", "Wc": "#ef5350",
            }
            # Líneas entre ondas consecutivas
            for _i in range(len(_ondas) - 1):
                _o1, _o2 = _ondas[_i], _ondas[_i + 1]
                _col_ew  = _EW_COL.get(_o2["label"], "#888888")
                fig.add_trace(go.Scatter(
                    x=[_o1["tiempo"], _o2["tiempo"]],
                    y=[_o1["precio"], _o2["precio"]],
                    mode="lines",
                    line=dict(color=_col_ew, width=2.0),
                    showlegend=False, hoverinfo="skip", opacity=0.9,
                ), row=1, col=1)
            # Etiquetas en cada punto de giro
            for _o in _ondas:
                _lbl    = _o["label"].replace("W", "")   # "W1"→"1", "Wa"→"a"
                _yshift = 16 if _o["tipo"] == "H" else -20
                fig.add_annotation(
                    x=_o["tiempo"], y=_o["precio"],
                    text=f"<b>{_lbl}</b>",
                    showarrow=False,
                    font=dict(size=13, color="#FFD700", family="Arial Black"),
                    yshift=_yshift, row=1, col=1,
                )

    t_max = df["tiempo"].max()
    # Intervalo de una vela en segundos
    if len(df) > 1:
        candle_s = (df["tiempo"].iloc[-1] - df["tiempo"].iloc[-2]).total_seconds()
    else:
        candle_s = 14400  # default 4H
    # Ancho máximo del panel VP: 20% del total de velas (proporcional al chart, barras visibles)
    max_ext_s = candle_s * len(df) * 0.20
    # Muro derecho: 1 vela de separación + el ancho máximo → queda exactamente en el borde del eje
    t_wall = t_max + pd.Timedelta(seconds=candle_s + max_ext_s)

    # Volume profile: gradiente azul — más volumen = azul más intenso, menos = azul cielo
    # 5 buckets de color agrupados en sus trazas (mucho mejor que 90 trazas individuales)
    def _vp_color(ratio):
        if ratio >= 0.80: return "rgba(21,  101, 192, 0.95)"   # azul oscuro intenso
        if ratio >= 0.60: return "rgba(33,  150, 243, 0.88)"   # azul fuerte
        if ratio >= 0.40: return "rgba(66,  165, 245, 0.78)"   # azul medio
        if ratio >= 0.20: return "rgba(100, 181, 246, 0.68)"   # azul cielo
        return                   "rgba(144, 202, 249, 0.55)"   # azul cielo muy claro

    _vp_buckets: dict = {}
    for i, v in enumerate(vols):
        if i == poc_idx:
            continue
        pmid = (niveles[i] + niveles[i + 1]) / 2
        t_start = t_wall - pd.Timedelta(seconds=max_ext_s * (v / vol_max))
        col = _vp_color(v / vol_max)
        if col not in _vp_buckets:
            _vp_buckets[col] = ([], [])
        _vp_buckets[col][0].extend([t_start, t_wall, None])
        _vp_buckets[col][1].extend([pmid, pmid, None])

    for col, (xb, yb) in _vp_buckets.items():
        fig.add_trace(go.Scatter(x=xb, y=yb, mode="lines",
                                 line=dict(color=col, width=1),
                                 showlegend=False, hoverinfo="skip"), row=1, col=1)

    # POC bar en dorado — más ancha y visible
    poc_pmid = (niveles[poc_idx] + niveles[poc_idx + 1]) / 2
    poc_tstart = t_wall - pd.Timedelta(seconds=max_ext_s * (vols[poc_idx] / vol_max))
    fig.add_trace(go.Scatter(x=[poc_tstart, t_wall], y=[poc_pmid, poc_pmid], mode="lines",
                             line=dict(color="#FFD700", width=3),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_hline(y=poc, line_dash="dot", line_color="#FFD700", line_width=1, row=1, col=1)

    # Fijar el borde derecho del eje X = t_wall → VP pegado al eje de precios
    # Con shared_xaxes=True esto sincroniza los 3 subplots automáticamente
    _t_left = df["tiempo"].iloc[0] - pd.Timedelta(seconds=candle_s * 2)
    fig.update_xaxes(range=[_t_left, t_wall])

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
        uirevision=f"{activo}-{tf}",   # mismo activo+TF = no parpadea al actualizar datos
        template="plotly_dark", paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
        margin=dict(l=5, r=65, t=8, b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#a0a8c0", size=11),
                    orientation="h", x=0, y=1.02),
        hovermode="x unified", xaxis_rangeslider_visible=False,
        dragmode="pan",
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
    print(f"[AERO LADDER] Inicio | Racha: {bot_state['racha_ganadora']} | Apalancamiento: {apalancamiento_actual}X")

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
                df = obtener_datos(activo, tf, velas=_SR_LOOKBACK.get(tf, 200))
                if df is None or df.empty:
                    continue
                score, _ = calcular_score(df)
                mtf = _analizar_mtf(activo, ema_comp_pct)

                # Aplicar penalización MTF v3: reduce abs(score) sin cambiar signo
                pen = mtf.get("penalizacion", 0)
                if score > 0:
                    score = max(0, score - pen)
                elif score < 0:
                    score = min(0, score + pen)

                with _bot_lock:
                    _bot_status["scores"][activo] = score
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

                # ── P&L EN TIEMPO REAL ────────────────────────────────────────
                if pos_actual and precio_entrada[activo]:
                    ep_live = precio_entrada[activo]
                    if pos_actual == "long":
                        pnl_pct_live = (precio - ep_live) / ep_live * 100 * apalancamiento_actual
                    else:
                        pnl_pct_live = (ep_live - precio) / ep_live * 100 * apalancamiento_actual
                    cap_usado = capital_usado.get(activo) or 0.0
                    pnl_usd_live = cap_usado * pnl_pct_live / 100
                    with _bot_lock:
                        _bot_status["pnl"][activo] = {
                            "pct":     round(pnl_pct_live, 2),
                            "usd":     round(pnl_usd_live, 2),
                            "side":    pos_actual,
                            "entrada": ep_live,
                            "precio":  precio,
                        }
                else:
                    with _bot_lock:
                        _bot_status["pnl"].pop(activo, None)

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

                # ── CIERRE EN EMA55 — Regla K-2 (Eduardo Andrade) ────────────
                # Si estamos en SHORT y el precio toca la EMA55 → cerrar siempre.
                # La EMA55 produce rebote ~90% del tiempo. Sin importar P&L ni distancia.
                if pos_actual == "short" and precio_entrada[activo]:
                    ema55_ahora = float(df["EMA55"].iloc[-1])
                    dist_ema55_pct = abs(precio - ema55_ahora) / ema55_ahora * 100
                    if dist_ema55_pct <= 0.5:   # precio tocó la EMA55 (dentro del 0.5%)
                        ep = precio_entrada[activo]
                        pnl_pct = round((ep - precio) / ep * 100 * apalancamiento_actual, 2)
                        sgn = "+" if pnl_pct >= 0 else ""
                        bx.cerrar_posicion(simbolo, "short")
                        _enviar_telegram(
                            f"EMA55 EXIT SHORT\n"
                            f"Par: {simbolo}\n"
                            f"Entrada: ${ep:,.2f} | Cierre: ${precio:,.2f}\n"
                            f"P&L: {sgn}{pnl_pct:.1f}% | EMA55: ${ema55_ahora:,.2f}"
                        )
                        bot_state = _actualizar_racha(bot_state, pnl_pct / apalancamiento_actual,
                                                      apalancamiento_actual, bal or 1000)
                        _registrar_trade({
                            "timestamp": datetime.now().isoformat(),
                            "activo": activo,
                            "side": "short",
                            "entrada": ep,
                            "salida": precio,
                            "pnl_pct": pnl_pct,
                            "apalancamiento": apalancamiento_actual,
                            "motivo": "EMA55 EXIT",
                            "modo": modo,
                        })
                        posicion[activo] = precio_entrada[activo] = precio_extremo[activo] = None
                        trailing_activo[activo] = False
                        capital_usado[activo] = 0.0
                        _registrar(activo, f"EMA55 EXIT SHORT {sgn}{pnl_pct:.1f}%", None)
                        _bot_status["log"].insert(0, f"EMA55 EXIT {activo} {sgn}{pnl_pct:.1f}%")
                        _bot_status["log"] = _bot_status["log"][:8]
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
                    print(f"[TOPE EXPOSICION] {activo}: Exposicion actual ${exposicion_actual:.0f} + "
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
                               marks={
                                   1:  {"label": "1%",  "style": {"color": "#ffffff"}},
                                   5:  {"label": "5%",  "style": {"color": "#ffffff"}},
                                   10: {"label": "10%", "style": {"color": "#ffffff"}},
                                   15: {"label": "15%", "style": {"color": "#ffffff"}},
                                   20: {"label": "20%", "style": {"color": "#ffffff"}},
                               },
                               tooltip={"placement": "bottom", "always_visible": False}),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Balance BingX"),
                    html.Div(className="stat-fila", children=[
                        html.Span("USDT", className="stat-nombre"),
                        html.Span("–", id="bot-balance-val", className="stat-valor"),
                    ]),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Posicion Abierta"),
                    html.Div(id="pnl-posicion",
                             style={"marginTop": "4px", "lineHeight": "1.8"},
                             children=html.Div("Sin posicion abierta",
                                               style={"color": "#3a3a50", "fontSize": "11px"})),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Telegram"),
                    html.Div(className="stat-fila", children=[
                        html.Span("Estado", className="stat-nombre"),
                        html.Span("No configurado", id="telegram-estado",
                                  style={"color": "#a0a8c0", "fontSize": "12px"}),
                    ]),
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
            ]),

            # CENTER: siempre BTC
            html.Div(id="panel-central", children=[
                html.Div(className="chart-action-bar", children=[
                    html.Span("BTC / USDT", className="chart-asset-label"),
                    html.A("↗ Ver Detalle", href="/detail/BTC", target="_blank",
                           className="btn-detalle"),
                ]),
                html.Div(className="grafico-wrap", children=[
                    dcc.Loading(type="dot", color="#c8a84b", delay_show=2000,
                                style={"height": "calc(100vh - 520px)", "minHeight": "340px"},
                                children=[
                        dcc.Graph(id="grafico-principal",
                                  config={"displayModeBar": "hover", "scrollZoom": True, "displaylogo": False,
                                          "modeBarButtonsToRemove": ["select2d","lasso2d","toImage","sendDataToCloud"]},
                                  style={"height": "calc(100vh - 520px)", "minHeight": "340px"}),
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
                html.Button(id="btn-bot", children="INICIAR BOT",
                            className="btn-principal", n_clicks=0,
                            style={"marginTop": "8px"}),
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
                    html.Div(className="seccion-titulo", children="Dirección MTF v3"),
                    html.Div(className="stat-fila", children=[
                        html.Span("4H", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em", "color": "#f0c040"}),
                        html.Span("–", id="mtf-4h", className="stat-valor",
                                  style={"fontSize": "11px", "fontFamily": "monospace"}),
                    ]),
                    html.Div(className="stat-fila", children=[
                        html.Span("2H", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em", "color": "#f0c040"}),
                        html.Span("–", id="mtf-2h", className="stat-valor",
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
                        html.Span("1W", className="stat-nombre",
                                  style={"fontSize": "10px", "fontWeight": "700",
                                         "letterSpacing": "0.1em"}),
                        html.Span("–", id="mtf-1w", className="stat-valor",
                                  style={"fontSize": "11px", "fontFamily": "monospace"}),
                    ]),
                    html.Div(id="mtf-direccion", style={
                        "textAlign": "center", "marginTop": "6px",
                        "fontSize": "11px", "fontWeight": "700",
                        "letterSpacing": "0.06em", "padding": "5px 4px",
                        "background": "#111120", "borderRadius": "4px",
                        "border": "1px solid #2a2a3a",
                    }, children="⏳ Bot detenido"),
                    html.Div(id="mtf-advertencia", style={
                        "display": "none",
                        "marginTop": "4px", "padding": "4px 6px",
                        "background": "#1a1000", "borderRadius": "4px",
                        "border": "1px solid #f0c040", "fontSize": "10px",
                        "color": "#f0c040", "textAlign": "center",
                        "letterSpacing": "0.04em",
                    }),
                ]),
                html.Div(className="separador-dorado"),
                # Toggle Ondas de Elliott
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Herramientas"),
                    # toggle-elliott-ui: el visible en sidebar — sincroniza al estático via callback
                    dcc.Checklist(
                        id="toggle-elliott-ui",
                        options=[{"label": " Ondas Elliott", "value": "on"}],
                        value=[],
                        className="checklist-activos",
                        labelStyle={"display": "flex", "alignItems": "center",
                                    "gap": "8px", "color": "#ffffff",
                                    "fontSize": "11px", "cursor": "pointer"},
                    ),
                ]),
                html.Div(className="separador-dorado"),
                # btn-historial en app.layout (estático) — fix modal auto-open
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
        html.Div(className="relojes-grupo", children=[
            _reloj("NEW YORK", "NY"), _reloj("LONDON", "LON"),
            _reloj("TOKYO", "TYO"), _reloj("DUBAI", "DXB"),
        ]),
        html.Div(className="idioma-barra", children=[
            html.Span("IDIOMA", id="lbl-idioma", className="idioma-barra-label"),
            dcc.RadioItems(id="radio-idioma",
                           options=[{"label": x, "value": x.lower()}
                                    for x in ["ES","EN","IT","FR","DE","ZH","KO","JA"]],
                           value="es", className="radio-idiomas",
                           inputStyle={"display": "none"}),
        ]),
    ]),
    html.Div(id="frase-barra", children=[
        "El mercado recompensa la paciencia, no la prisa.",
        html.Span("- Jesse Livermore", className="autor"),
    ]),
    html.Div(id="page-content"),

    # ── BTN HISTORIAL — estático para que prevent_initial_call funcione en Edge ──
    html.Button(id="btn-historial", children="📋 Historial de Trades",
                n_clicks=0, style={
                    "position": "fixed", "bottom": "20px", "right": "20px",
                    "zIndex": "900",
                    "padding": "9px 16px", "fontSize": "11px",
                    "fontWeight": "700", "letterSpacing": "0.1em",
                    "background": "#0d0d1a", "color": "#f0c040",
                    "border": "1px solid #f0c040", "borderRadius": "4px",
                    "cursor": "pointer", "boxShadow": "0 0 12px rgba(240,192,64,0.15)",
                }),

    # ── TOGGLE ELLIOTT — estático para que cb_detail funcione en pestaña nueva (regla #19) ──
    # El checklist visible está en _pagina_principal(); este es el componente real que usan los callbacks.
    dcc.Checklist(
        id="toggle-elliott",
        options=[{"label": " Ondas Elliott", "value": "on"}],
        value=[],
        style={"display": "none"},   # oculto — la UI visible está en el sidebar (id diferente: toggle-elliott-ui)
    ),

    # ── MODAL HISTORIAL DE TRADES (siempre en DOM, visible/oculto por callback) ──
    html.Div(id="modal-historial", style={"display": "none"}, children=[
        html.Div(style={
            "position": "fixed", "top": "0", "left": "0",
            "width": "100%", "height": "100%",
            "background": "rgba(0,0,0,0.88)",
            "zIndex": "9999",
            "display": "flex", "alignItems": "center", "justifyContent": "center",
        }, children=[
            html.Div(style={
                "background": "#0d0d1a",
                "border": "1px solid #f0c040",
                "borderRadius": "8px",
                "width": "92%", "maxWidth": "960px",
                "maxHeight": "82vh",
                "display": "flex", "flexDirection": "column",
                "overflow": "hidden",
                "boxShadow": "0 0 40px rgba(240,192,64,0.15)",
            }, children=[
                # Header del modal
                html.Div(style={
                    "display": "flex", "alignItems": "center",
                    "justifyContent": "space-between",
                    "padding": "14px 20px",
                    "borderBottom": "1px solid #1e1e30",
                    "background": "#080812",
                }, children=[
                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px"}, children=[
                        html.Span("📋", style={"fontSize": "18px"}),
                        html.Span("HISTORIAL DE TRADES", style={
                            "fontSize": "13px", "fontWeight": "700",
                            "letterSpacing": "0.15em", "color": "#f0c040",
                        }),
                    ]),
                    html.Button("✕", id="btn-cerrar-historial", n_clicks=0, style={
                        "background": "none", "border": "1px solid #333",
                        "color": "#888", "fontSize": "16px",
                        "cursor": "pointer", "borderRadius": "4px",
                        "padding": "2px 8px", "lineHeight": "1.4",
                    }),
                ]),
                # Cuerpo — tabla de trades
                html.Div(id="historial-tabla", style={
                    "overflowY": "auto", "padding": "12px 16px",
                    "flex": "1",
                }),
            ]),
        ]),
    ]),
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
            _bot_status["activos"] = activos_sel or []  # refleja exactamente lo que el usuario chequeó
        _bot_stop.clear()
        _bot_thread = threading.Thread(
            target=_bot_loop,
            args=(activos_lista, tf or "4H", capital_pct or 5),
            daemon=True,
        )
        _bot_thread.start()
        return t["stop"], "btn-principal stop", "led-dot conectando", t["connecting"], True
    _bot_stop.set()
    with _bot_lock:
        _bot_status["scores"] = {}
        _bot_status["pnl"]    = {}
        _bot_status["mtf"]    = {}
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

# Sincroniza el toggle visual (sidebar) → toggle estático (app.layout)
# Necesario porque toggle-elliott vive en app.layout para que cb_detail funcione en pestaña nueva
@app.callback(
    Output("toggle-elliott", "value"),
    Input("toggle-elliott-ui", "value"),
    prevent_initial_call=True,
)
def _sync_elliott(val):
    return val or []


@app.callback(
    [Output("grafico-principal", "figure"),
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
    [State("store-idioma", "data"), State("toggle-elliott", "value")],
)
def cb_btc_dashboard(_, tf, idioma, elliott_val):
    t = TRANSLATIONS.get(idioma, TRANSLATIONS["es"])

    def _fig_err():
        f = go.Figure()
        f.update_layout(paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
                        margin=dict(l=5,r=65,t=8,b=8),
                        annotations=[dict(text="Sin datos", showarrow=False,
                                        font=dict(color="#6b5520",size=16), x=0.5, y=0.5)])
        return f

    tf_actual = tf or "4H"
    df = obtener_datos("BTC", tf_actual, velas=_SR_LOOKBACK.get(tf_actual, 200))
    if df is None or df.empty:
        off = _gr("off", "-")
        return (_fig_err(), *off,*off,*off,*off,*off,*off,
                "–","–",{"fontSize":"13px","color":"#a0a8c0"},"–","–","–","–")

    score, gr = calcular_score(df)
    _show_ew = bool(elliott_val)   # [] → False, ["on"] → True
    fig = crear_grafico(df, "BTC", compacto=True, tf=tf_actual, show_elliott=_show_ew)

    u = df.iloc[-1]
    ref = df["close"].iloc[-7] if len(df) >= 7 else df["close"].iloc[0]
    chg = (float(u["close"]) - float(ref)) / float(ref) * 100
    sgn = "+" if chg >= 0 else ""
    cclr = "#00ff88" if chg >= 0 else "#ff3355"

    return (
        fig,
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

def _scoring_bar_children(numero, cls, etiqueta, sty_etq, sty_barra, activo="BTC"):
    """
    Barra de score — diseño limpio sin superposición de texto.
    Layout: ACTIVO | NÚMERO | SHORT ◄────bar────► LONG | ETIQUETA
    El número y la etiqueta están FUERA de la barra, sin pisarse.
    """
    try:
        val = int(numero)
    except Exception:
        val = 0

    if val >= 70:
        color = "#00ff88"
    elif val <= -70:
        color = "#ff3355"
    else:
        color = "#c8a84b"

    abs_pct = min(abs(val), 100) / 2
    if val < 0:
        left  = f"{50 - abs_pct:.1f}%"
        width = f"{abs_pct:.1f}%"
    else:
        left  = "50%"
        width = f"{abs_pct:.1f}%"

    return [
        # activo — identifica a qué par pertenece el score
        html.Div(activo, className="sc-activo"),
        # número grande
        html.Span(numero, id="sc-numero", className=cls),
        # etiqueta SHORT fija
        html.Div("SHORT", className="sc-lado sc-lado-short"),
        # barra central — sin texto encima
        html.Div(className="sc-barra-central-wrap", children=[
            html.Div(className="sc-barra-track"),
            html.Div(className="sc-barra-centro"),
            html.Div(className="sc-barra-activa",
                     style={"left": left, "width": width, "background": color}),
        ]),
        # etiqueta LONG fija
        html.Div("LONG", className="sc-lado sc-lado-long"),
        # dirección — CORTO / ESPERAR / LARGO
        html.Span(etiqueta, id="sc-etiqueta", className="sc-etiqueta", style=sty_etq),
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
     Output("d-gr-squeeze-card", "className"), Output("d-gr-squeeze-dot", "className"), Output("d-gr-squeeze-val", "children"),
     Output("d-gr-adx-card", "className"), Output("d-gr-adx-dot", "className"), Output("d-gr-adx-val", "children"),
     Output("d-gr-ema-card", "className"), Output("d-gr-ema-dot", "className"), Output("d-gr-ema-val", "children"),
     Output("d-gr-sr-card", "className"), Output("d-gr-sr-dot", "className"), Output("d-gr-sr-val", "children"),
     Output("d-gr-vol-card", "className"), Output("d-gr-vol-dot", "className"), Output("d-gr-vol-val", "children"),
     ],
    [Input("detail-tick", "n_intervals"),
     Input("detail-tf-radio", "value")],
    [State("url", "pathname"),
     State("store-idioma", "data"),
     State("toggle-elliott", "value")],
)
def cb_detail(_, tf, pathname, idioma, elliott_val):
    symbol = "BTC"
    if pathname and "/detail/" in pathname:
        symbol = pathname.split("/detail/")[-1].upper()
    t = TRANSLATIONS.get(idioma or "es", TRANSLATIONS["es"])

    tf_actual = tf or "4H"
    df = obtener_datos(symbol, tf_actual, velas=_SR_LOOKBACK.get(tf_actual, 200))
    if df is None or df.empty:
        off = _gr("off", "-")
        f = go.Figure()
        f.update_layout(paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f")
        return (f, *off,*off,*off,*off,*off)

    score, gr = calcular_score(df)
    _show_ew = bool(elliott_val)
    fig = crear_grafico(df, symbol, compacto=False, tf=tf_actual, show_elliott=_show_ew)

    return (
        fig,
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
     Output("mtf-2h", "children"),
     Output("mtf-direccion", "children"),
     Output("mtf-advertencia", "children"),
     Output("mtf-advertencia", "style"),
     Output("aero-ladder-val", "children"),
     Output("aero-racha-val", "children"),
     Output("aero-lock-val", "children"),
     Output("panel-senales-mini", "children"),
     Output("led-dot", "className",  allow_duplicate=True),
     Output("led-txt", "children",   allow_duplicate=True),
     Output("pnl-posicion", "children")],
    Input("tick-bot-status", "n_intervals"),
    State("store-idioma", "data"),
    State("store-bot", "data"),
    prevent_initial_call=True,
)
def cb_bot_status(_, idioma, bot_activo):
    with _bot_lock:
        bal = _bot_status["balance"]
        log = list(_bot_status["log"])
        mtf = dict(_bot_status.get("mtf", {}))
        scores = dict(_bot_status.get("scores", {}))
        activos_sel = list(_bot_status.get("activos", []))
        apal = _bot_status.get("apalancamiento", 2)
        pnl_data = dict(_bot_status.get("pnl", {}))

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

    # ── MTF display v3 ─────────────────────────────────────────────────────────
    def _fmt_tf(data):
        if not data or data.get("estado") == "–":
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
    mtf_2h_txt = _fmt_tf(mtf.get("2H"))

    if not mtf:
        mtf_dir = "⏳ Bot detenido"
        mtf_adv_txt  = ""
        mtf_adv_style = {"display": "none"}
    else:
        dir_   = mtf.get("direccion", "esperar")
        lo     = mtf.get("long_ok",   False)
        so     = mtf.get("short_ok",  False)
        fuerza = mtf.get("fuerza",    "–")
        adv    = mtf.get("advertencia", "")
        pen    = mtf.get("penalizacion", 0)
        fuerza_ico = "💪" if fuerza == "fuerte" else "⚡" if fuerza == "débil" else ""
        pen_txt = f"  (−{pen}pts)" if pen > 0 else ""
        if dir_ == "long" and lo:
            mtf_dir = f"🟢 LONG 4H  {fuerza_ico} 2H {fuerza.upper()}{pen_txt}"
        elif dir_ == "short" and so:
            mtf_dir = f"🔴 SHORT 4H  {fuerza_ico} 2H {fuerza.upper()}{pen_txt}"
        else:
            mtf_dir = "⏳ ESPERAR — 4H sin dirección"
        # Advertencia banner
        if adv:
            mtf_adv_txt   = adv
            mtf_adv_style = {
                "display": "block", "marginTop": "4px", "padding": "4px 6px",
                "background": "#1a1000", "borderRadius": "4px",
                "border": "1px solid #f0c040", "fontSize": "10px",
                "color": "#f0c040", "textAlign": "center",
                "letterSpacing": "0.04em",
            }
        else:
            mtf_adv_txt   = ""
            mtf_adv_style = {"display": "none"}

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

    # ── LED 3 estados ─────────────────────────────────────────────────────────
    # store-bot es la fuente de verdad — se pone False al detener el bot
    t_led = TRANSLATIONS.get(idioma or "es", TRANSLATIONS["es"])
    bot_vivo = bool(bot_activo and _bot_thread and _bot_thread.is_alive())
    if not bot_vivo:
        led_class = "led-dot desconectado"
        led_txt_v = t_led["disconnected"]
    elif not scores:
        led_class = "led-dot conectando"
        led_txt_v = t_led["connecting"]
    else:
        led_class = "led-dot"
        led_txt_v = t_led["connected"]

    # ── P&L en tiempo real ────────────────────────────────────────────────────
    if pnl_data:
        pnl_items = []
        for act, p in pnl_data.items():
            pct     = p.get("pct",    0.0)
            usd     = p.get("usd",    0.0)
            side    = p.get("side",   "")
            entrada = p.get("entrada", 0.0)
            precio_v = p.get("precio", 0.0)
            color  = "#00ff88" if pct >= 0 else "#ff3355"
            signo  = "+" if pct >= 0 else ""
            pnl_items.append(html.Div([
                html.Span(f"{act} {side.upper()} ",
                          style={"color": "#f0c040", "fontWeight": "700", "fontSize": "11px"}),
                html.Span(f"{signo}{pct:.2f}%",
                          style={"color": color, "fontWeight": "700", "fontSize": "12px"}),
                html.Br(),
                html.Span(f"${entrada:,.2f} → ${precio_v:,.2f}",
                          style={"color": "#6b5520", "fontSize": "10px", "fontFamily": "monospace"}),
            ], style={"marginBottom": "4px"}))
        pnl_display = html.Div(pnl_items)
    else:
        pnl_display = html.Div("Sin posicion abierta", style={"color": "#3a3a50", "fontSize": "11px"})

    return (bal_txt, log_items, tg_txt, tg_style,
            mtf_1w_txt, mtf_1d_txt, mtf_4h_txt, mtf_2h_txt,
            mtf_dir, mtf_adv_txt, mtf_adv_style,
            aero_apal, aero_racha, aero_lock, senales,
            led_class, led_txt_v, pnl_display)
    
# ─── MODAL HISTORIAL — CALLBACKS ─────────────────────────────────────────────

@app.callback(
    Output("modal-historial", "style"),
    [Input("btn-historial", "n_clicks"),
     Input("btn-cerrar-historial", "n_clicks")],
    prevent_initial_call=True,
)
def toggle_modal_historial(open_clicks, close_clicks):
    """Abre o cierra el modal de historial de trades."""
    from dash import callback_context
    if not callback_context.triggered:
        return {"display": "none"}
    trigger = callback_context.triggered[0]["prop_id"].split(".")[0]
    # Guard: solo abrir si hay al menos 1 click real en el botón
    if trigger == "btn-historial" and open_clicks and open_clicks > 0:
        return {"display": "block"}
    return {"display": "none"}


@app.callback(
    Output("historial-tabla", "children"),
    Input("modal-historial", "style"),
    prevent_initial_call=True,
)
def cargar_historial(modal_style):
    """Carga y renderiza los trades cuando el modal se abre."""
    if not modal_style or modal_style.get("display") == "none":
        from dash.exceptions import PreventUpdate
        raise PreventUpdate

    try:
        trades = []
        if os.path.exists(_TRADES_FILE):
            with open(_TRADES_FILE, encoding="utf-8") as f:
                trades = json.load(f)
    except Exception:
        trades = []

    if not trades:
        return html.Div("Sin trades registrados aún. Los trades aparecerán aquí después de la primera operación.", style={
            "color": "#555", "fontSize": "13px", "textAlign": "center",
            "padding": "40px 20px",
        })

    # ── Resumen en la parte superior ─────────────────────────────────────────
    total    = len(trades)
    ganancias = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
    perdidas  = total - ganancias
    pnl_total = sum(t.get("pnl_pct", 0) for t in trades)
    win_rate  = (ganancias / total * 100) if total else 0

    def _pnl_color(v):
        return "#00ff88" if v > 0 else "#ff3355" if v < 0 else "#888"

    resumen = html.Div(style={
        "display": "flex", "gap": "12px", "marginBottom": "14px",
        "flexWrap": "wrap",
    }, children=[
        _stat_pill("Total Trades", str(total), "#888"),
        _stat_pill("Win Rate", f"{win_rate:.0f}%", "#00ff88" if win_rate >= 50 else "#ff3355"),
        _stat_pill("Ganancias", str(ganancias), "#00ff88"),
        _stat_pill("Pérdidas", str(perdidas), "#ff3355"),
        _stat_pill("P&L Acum.", f"{pnl_total:+.2f}%", _pnl_color(pnl_total)),
    ])

    # ── Cabecera de la tabla ──────────────────────────────────────────────────
    _th = lambda txt, flex=1: html.Div(txt, style={
        "flex": str(flex), "fontSize": "10px", "fontWeight": "700",
        "color": "#555", "letterSpacing": "0.1em", "padding": "4px 6px",
        "textTransform": "uppercase",
    })
    header = html.Div(style={
        "display": "flex", "borderBottom": "1px solid #1e1e30",
        "marginBottom": "4px", "paddingBottom": "4px",
    }, children=[
        _th("Fecha", 1.4), _th("Activo"), _th("Tipo"),
        _th("Entrada"), _th("Salida"), _th("P&L", 0.8),
        _th("Motivo", 1.5), _th("Modo", 0.8),
    ])

    # ── Filas de trades ───────────────────────────────────────────────────────
    def _fila(trade):
        ts_raw  = trade.get("timestamp", "")
        ts      = ts_raw[:16].replace("T", " ") if ts_raw else "–"
        activo  = trade.get("activo", "–")
        side    = trade.get("side", "–").upper()
        entrada = trade.get("entrada")
        salida  = trade.get("salida")
        pnl     = trade.get("pnl_pct", 0)
        motivo  = trade.get("motivo", "–")
        modo    = trade.get("modo", "–").upper()

        side_color = "#00ff88" if side == "LONG" else "#ff3355"
        side_ico   = "🟢" if side == "LONG" else "🔴"
        pnl_color  = "#00ff88" if pnl > 0 else "#ff3355" if pnl < 0 else "#888"
        pnl_txt    = f"{pnl:+.2f}%" if pnl != 0 else "–"
        ent_txt    = f"${entrada:,.2f}" if isinstance(entrada, (int, float)) else "–"
        sal_txt    = f"${salida:,.2f}"  if isinstance(salida,  (int, float)) else "–"
        modo_color = "#f0c040" if modo == "DEMO" else "#00ff88"

        _td = lambda txt, flex=1, color="#aaa", bold=False: html.Div(txt, style={
            "flex": str(flex), "fontSize": "11px", "color": color,
            "padding": "5px 6px", "fontFamily": "monospace",
            "fontWeight": "700" if bold else "400",
        })

        return html.Div(style={
            "display": "flex", "borderBottom": "1px solid #0e0e1c",
            "alignItems": "center",
        }, children=[
            _td(ts, 1.4, "#666"),
            _td(activo, 1, "#e0e0e0", bold=True),
            html.Div(f"{side_ico} {side}", style={
                "flex": "1", "fontSize": "11px", "color": side_color,
                "fontWeight": "700", "padding": "5px 6px",
            }),
            _td(ent_txt),
            _td(sal_txt),
            html.Div(pnl_txt, style={
                "flex": "0.8", "fontSize": "11px", "color": pnl_color,
                "fontWeight": "700", "padding": "5px 6px", "fontFamily": "monospace",
            }),
            _td(motivo, 1.5, "#888"),
            html.Div(modo, style={
                "flex": "0.8", "fontSize": "9px", "color": modo_color,
                "fontWeight": "700", "padding": "5px 6px",
                "letterSpacing": "0.08em",
            }),
        ])

    filas = [_fila(t) for t in trades[:100]]  # máximo 100 en pantalla

    return html.Div([resumen, header] + filas)


def _stat_pill(label, value, color):
    """Pill de resumen para el modal de historial."""
    return html.Div(style={
        "background": "#111120", "border": f"1px solid {color}33",
        "borderRadius": "6px", "padding": "6px 14px",
        "textAlign": "center",
    }, children=[
        html.Div(value, style={"fontSize": "16px", "fontWeight": "700", "color": color}),
        html.Div(label, style={"fontSize": "9px", "color": "#555", "letterSpacing": "0.08em",
                               "textTransform": "uppercase", "marginTop": "2px"}),
    ])


if __name__ == "__main__":
    print("=" * 50)
    print(" AERO BOT PRO — Elite v3.3")
    print(" MTF v3: 4H predice | 2H confirma | 1W/1D advierten")
    print(" http://localhost:8051")
    print(f" [CHECK] Label activos ES: {TRANSLATIONS['es']['assets']}")
    print(f" [CHECK] panel-senales-mini: OK")
    print("=" * 50)
    app.run(debug=False, port=8051, host="0.0.0.0", use_reloader=False, 
        dev_tools_hot_reload=False, dev_tools_props_check=False)
