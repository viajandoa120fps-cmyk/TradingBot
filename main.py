"""
AERO BOT PRO - Dashboard Elite v2.0
Puerto 8051 | Multi-pagina | Top 20 CoinMarketCap
"""

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import random
import time
import ccxt
from scipy.signal import argrelextrema
import threading
import json
import urllib.request
import bingx as bx

# ─── TRADUCCIONES ─────────────────────────────────────────────────────────────

TRANSLATIONS = {
    "es": {
        "title": "AERO BOT PRO", "subtitle": "Trading Bot Profesional",
        "connected": "CONECTADO", "disconnected": "DESCONECTADO",
        "language": "Idioma", "timeframe": "Temporalidad",
        "assets": "Activos (máx. 6)", "capital": "Capital por Op.",
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
        "assets": "Assets (max. 6)", "capital": "Capital per Op.",
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
        "assets": "Asset (max. 6)", "capital": "Capitale per Op.",
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
        "assets": "Actifs (max. 6)", "capital": "Capital par Op.",
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
        "assets": "Assets (max. 6)", "capital": "Kapital pro Op.",
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
        "assets": "资产（最多6个）", "capital": "每次资金",
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
        "assets": "자산 (최대 6개)", "capital": "거래당 자본",
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
        "assets": "資産（最大6個）", "capital": "取引資金",
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
    "BTC":  "BTC/USDT",
    "ETH":  "ETH/USDT",
    "BNB":  "BNB/USDT",
    "XRP":  "XRP/USDT",
    "SOL":  "SOL/USDT",
    "TRX":  "TRX/USDT",
    "DOGE": "DOGE/USDT",
    "ADA":  "ADA/USDT",
    "BCH":  "BCH/USDT",
    "LINK": "LINK/USDT",
    "TON":  "TON/USDT",
    "XLM":  "XLM/USDT",
    "SUI":  "SUI/USDT",
    "LTC":  "LTC/USDT",
    "AVAX": "AVAX/USDT",
    "HBAR": "HBAR/USDT",
    "SHIB": "SHIB/USDT",
    "DOT":  "DOT/USDT",
    "NEAR": "NEAR/USDT",
    "ARB":  "ARB/USDT",
}

# Checklist: top 20 incluyendo BTC
ACTIVOS_GRID = [
    ("BTC",  "BTC/USDT"),
    ("ETH",  "ETH/USDT"),  ("BNB",  "BNB/USDT"),  ("XRP",  "XRP/USDT"),
    ("SOL",  "SOL/USDT"),  ("TRX",  "TRX/USDT"),  ("DOGE", "DOGE/USDT"),
    ("ADA",  "ADA/USDT"),  ("BCH",  "BCH/USDT"),  ("LINK", "LINK/USDT"),
    ("TON",  "TON/USDT"),  ("XLM",  "XLM/USDT"),  ("SUI",  "SUI/USDT"),
    ("LTC",  "LTC/USDT"),  ("AVAX", "AVAX/USDT"), ("HBAR", "HBAR/USDT"),
    ("SHIB", "SHIB/USDT"), ("DOT",  "DOT/USDT"),  ("NEAR", "NEAR/USDT"),
    ("ARB",  "ARB/USDT"),
]

TF_MAP = {
    "1W": "1w", "1D": "1d", "4H": "4h", "1H": "1h", "15m": "15m",
}

# ─── BOT GLOBAL STATE ─────────────────────────────────────────────────────────

_bot_thread = None
_bot_stop   = threading.Event()
_bot_lock   = threading.Lock()
_bot_status = {"balance": None, "posicion": {}, "log": []}


# ─── DATOS E INDICADORES ──────────────────────────────────────────────────────

def obtener_datos(activo="BTC", temporalidad="4H", velas=200):
    simbolo = SYMBOL_MAP.get(activo, "BTC/USDT")
    tf      = TF_MAP.get(temporalidad, "4h")
    raw     = None
    # Prefer BingX perpetual (matches TradingView BingX charts exactly)
    try:
        ex  = ccxt.bingx({"enableRateLimit": True})
        raw = ex.fetch_ohlcv(simbolo + ":USDT", tf, limit=velas + 300)
    except Exception:
        pass
    # Fallback: Binance spot
    if not raw:
        try:
            ex  = ccxt.binance({"enableRateLimit": False})
            raw = ex.fetch_ohlcv(simbolo, tf, limit=velas + 300)
        except Exception:
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
    df["BB_u"]   = df["BB_mid"] + bm * df["BB_std"]
    df["BB_l"]   = df["BB_mid"] - bm * df["BB_std"]

    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"]  - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)

    # KC: midline = EMA(close), range = SMA(TR) — fórmula exacta LazyBear v4_pine
    df["KC_mid"] = df["close"].ewm(span=kl, adjust=False).mean()
    df["KC_r"]   = tr.rolling(kl).mean()
    df["KC_u"]   = df["KC_mid"] + km * df["KC_r"]
    df["KC_l"]   = df["KC_mid"] - km * df["KC_r"]
    df["squeeze"] = (df["BB_l"] > df["KC_l"]) & (df["BB_u"] < df["KC_u"])

    # Momentum: linreg(close - avg(avg(high_max, low_min), sma_close), kl, 0)
    sma_close = df["close"].rolling(kl).mean()
    highest   = df["high"].rolling(kl).max()
    lowest    = df["low"].rolling(kl).min()
    delta     = df["close"] - ((highest + lowest) / 2 + sma_close) / 2

    _x     = np.arange(kl, dtype=float) - (kl - 1) / 2  # centered x
    _x_var = (_x ** 2).sum()
    _x_end = _x[-1]

    def _linreg_last(y):
        slope = (_x * (y - y.mean())).sum() / _x_var
        return y.mean() + slope * _x_end

    df["momentum"] = delta.rolling(kl).apply(_linreg_last, raw=True)

    # ADX (Wilder smoothing — matches TradingView DMI)
    ln, a = 14, 1 / 14
    tr14 = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"]  - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    dm_p = ((df["high"] - df["high"].shift()) > (df["low"].shift() - df["low"])).astype(float) * \
           (df["high"] - df["high"].shift()).clip(lower=0)
    dm_m = ((df["low"].shift() - df["low"]) > (df["high"] - df["high"].shift())).astype(float) * \
           (df["low"].shift() - df["low"]).clip(lower=0)
    tr14s      = tr14.ewm(alpha=a, adjust=False).mean()
    df["DI_p"] = 100 * dm_p.ewm(alpha=a, adjust=False).mean() / tr14s
    df["DI_m"] = 100 * dm_m.ewm(alpha=a, adjust=False).mean() / tr14s
    dx         = 100 * (df["DI_p"] - df["DI_m"]).abs() / (df["DI_p"] + df["DI_m"])
    df["ADX"]  = dx.ewm(alpha=a, adjust=False).mean()

    # Return only the requested candles (warmup discarded)
    return df.tail(velas).reset_index(drop=True)


def _volume_profile(df, bins=90):
    lo, hi  = df["low"].min(), df["high"].max()
    niveles = np.linspace(lo, hi, bins + 1)
    vols    = [df.loc[(df["close"] >= niveles[i]) & (df["close"] < niveles[i+1]), "volumen"].sum()
               for i in range(bins)]
    poc_idx = int(np.argmax(vols))
    poc     = (niveles[poc_idx] + niveles[poc_idx + 1]) / 2
    return niveles, vols, poc


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

    _, _, poc   = _volume_profile(df)
    sobre_poc   = bool(u["close"] > poc)
    pct_poc     = (u["close"] - poc) / poc * 100
    pts += 10 if sobre_poc else -10
    gr["VOL PROFILE"] = {"estado": "on" if sobre_poc else "war",
                          "valor": f"{'↑' if sobre_poc else '↓'}{abs(pct_poc):.1f}%"}

    max_idx = argrelextrema(df["high"].values, np.greater, order=10)[0]
    min_idx = argrelextrema(df["low"].values,  np.less,    order=10)[0]
    precio  = float(u["close"])
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
    simbolo         = SYMBOL_MAP.get(activo, "BTC/USDT")
    niveles, vols, poc = _volume_profile(df)
    poc_idx         = int(np.argmax(vols))
    vol_max         = max(vols) or 1

    lineas = []
    for idx_arr, col, color, name in [
        (argrelextrema(df["high"].values, np.greater, order=10)[0], "high", "#ff4444", "Resistencia"),
        (argrelextrema(df["low"].values,  np.less,    order=10)[0], "low",  "#00e676", "Soporte"),
    ]:
        if len(idx_arr) >= 2:
            i1, i2 = idx_arr[-2], idx_arr[-1]
            y1, y2 = df[col].iloc[i1], df[col].iloc[i2]
            pend   = (y2 - y1) / (i2 - i1)
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

    t_max   = df["tiempo"].max()
    rango_s = (t_max - df["tiempo"].min()).total_seconds()
    for i, v in enumerate(vols):
        pmid  = (niveles[i] + niveles[i + 1]) / 2
        color = "#FFD700" if i == poc_idx else "rgba(33,150,243,0.22)"
        t_ini = t_max - pd.Timedelta(seconds=rango_s * (v / vol_max) * 0.15)
        fig.add_trace(go.Scatter(x=[t_ini, t_max], y=[pmid, pmid], mode="lines",
            line=dict(color=color, width=3 if i == poc_idx else 1),
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
        name=f"ADX  {adx_val:.1f}", showlegend=True), row=3, col=1)
    fig.add_hline(y=23, line_dash="dash", line_color="#FFD700", line_width=1.2, row=3, col=1)

    ax  = dict(gridcolor="#1a1a28", color="#6b6b80", showspikes=True,
               spikecolor="#555", spikethickness=1, spikedash="dot", fixedrange=False)
    yax = dict(**ax, side="right")
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
        margin=dict(l=5, r=65, t=8, b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#a0a8c0", size=11),
                    orientation="h", x=0, y=1.02),
        hovermode="x unified", xaxis_rangeslider_visible=False,
        dragmode="pan",          # arrastrar = mover (como TradingView)
        xaxis=dict(**ax),  xaxis2=dict(**ax),  xaxis3=dict(**ax),
        yaxis=yax,         yaxis2=yax,         yaxis3=yax,
    )
    return fig


def _grid_cols(n):
    if n <= 3: return n
    if n == 4: return 2
    return 3


def crear_mini_grafico(df_dict):
    activos = [a for a, df in df_dict.items() if df is not None and not df.empty]
    if not activos:
        return go.Figure()
    n    = len(activos)
    cols = _grid_cols(n)
    rows = -(-n // cols)

    titulos = [SYMBOL_MAP.get(a, a) for a in activos]
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=titulos,
                        vertical_spacing=0.08, horizontal_spacing=0.04)

    for i, activo in enumerate(activos):
        row = i // cols + 1
        col = i % cols + 1
        df  = df_dict[activo]
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
        # ADX label en el título
        adx_val = float(df["ADX"].iloc[-1])
        adx_col = "#00e676" if adx_val >= 23 else "#888"

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
    """Envía un mensaje via Telegram Bot API. Silencioso si no está configurado."""
    try:
        with open("config.json") as f:
            cfg = json.load(f)
        token   = cfg.get("telegram_token")
        chat_id = cfg.get("telegram_chatid")
        if not token or not chat_id:
            return
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({
            "chat_id":    str(chat_id),
            "text":       mensaje,
            "parse_mode": "HTML",
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass  # Nunca interrumpir el bot por fallo de Telegram


# ─── BOT LOOP ─────────────────────────────────────────────────────────────────

def _bot_loop(activos_lista, tf, capital_pct):
    try:
        with open("config.json") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    modo           = cfg.get("modo", "demo")
    apalancamiento = cfg.get("apalancamiento", 10)
    posicion       = {a: None for a in activos_lista}

    while not _bot_stop.is_set():
        bal = bx.verificar_balance()
        with _bot_lock:
            _bot_status["balance"] = bal if not isinstance(bal, tuple) else None

        for activo in activos_lista:
            if _bot_stop.is_set():
                break
            try:
                df = obtener_datos(activo, tf, velas=200)
                if df is None or df.empty:
                    continue
                score, _  = calcular_score(df)
                simbolo    = SYMBOL_MAP.get(activo, f"{activo}/USDT")
                pos_actual = posicion.get(activo)
                accion     = None

                precio = float(df.iloc[-1]["close"])

                if score >= 70 and pos_actual != "long":
                    if pos_actual == "short":
                        bx.cerrar_posicion(simbolo, "short")
                        _enviar_telegram(
                            f"🔄 <b>CIERRE SHORT → LONG</b>\n"
                            f"Par: <b>{simbolo}</b>  |  Precio: <b>${precio:,.2f}</b>"
                        )
                    with _bot_lock:
                        bal_v = _bot_status["balance"] or 0
                    capital = bal_v * (capital_pct / 100) if bal_v else 10
                    bx.colocar_orden(simbolo, "long", capital, apalancamiento, modo)
                    posicion[activo] = "long"
                    accion = f"▲ LONG  score={score}"
                    _enviar_telegram(
                        f"🟢 <b>ENTRADA LONG</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Par:      <b>{simbolo}</b>\n"
                        f"Precio:   <b>${precio:,.2f}</b>\n"
                        f"Score:    <b>{score:+d}</b>\n"
                        f"Capital:  <b>${capital:.2f} USDT</b>\n"
                        f"Apalancamiento: <b>x{apalancamiento}</b>\n"
                        f"Modo:     <b>{modo.upper()}</b>"
                    )

                elif score <= -70 and pos_actual != "short":
                    if pos_actual == "long":
                        bx.cerrar_posicion(simbolo, "long")
                        _enviar_telegram(
                            f"🔄 <b>CIERRE LONG → SHORT</b>\n"
                            f"Par: <b>{simbolo}</b>  |  Precio: <b>${precio:,.2f}</b>"
                        )
                    with _bot_lock:
                        bal_v = _bot_status["balance"] or 0
                    capital = bal_v * (capital_pct / 100) if bal_v else 10
                    bx.colocar_orden(simbolo, "short", capital, apalancamiento, modo)
                    posicion[activo] = "short"
                    accion = f"▼ SHORT score={score}"
                    _enviar_telegram(
                        f"🔴 <b>ENTRADA SHORT</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Par:      <b>{simbolo}</b>\n"
                        f"Precio:   <b>${precio:,.2f}</b>\n"
                        f"Score:    <b>{score:+d}</b>\n"
                        f"Capital:  <b>${capital:.2f} USDT</b>\n"
                        f"Apalancamiento: <b>x{apalancamiento}</b>\n"
                        f"Modo:     <b>{modo.upper()}</b>"
                    )

                if accion:
                    ts  = datetime.now().strftime("%H:%M:%S")
                    msg = f"[{ts}] {activo}: {accion}"
                    with _bot_lock:
                        _bot_status["posicion"][activo] = posicion[activo]
                        _bot_status["log"].insert(0, msg)
                        _bot_status["log"] = _bot_status["log"][:8]

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
        html.Div(id=f"{prefix}sc-numero",   className="sc-numero",   children="–"),
        html.Div(className="sc-barra-wrap", children=[
            html.Div(id=f"{prefix}sc-barra", className="sc-barra",
                     style={"width": "50%", "background": "#2a2a3a"}),
        ]),
        html.Div(id=f"{prefix}sc-etiqueta", className="sc-etiqueta",
                 children="–", style={"color": "#a0a8c0"}),
    ])


# ─── PÁGINAS ──────────────────────────────────────────────────────────────────

def _pagina_principal():
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
                            {"label": "1 Semana",   "value": "1W"},
                            {"label": "1 Día",      "value": "1D"},
                            {"label": "4 Horas",    "value": "4H"},
                            {"label": "1 Hora",     "value": "1H"},
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
                        }, children="20%"),
                    ]),
                    dcc.Slider(id="slider-capital", min=5, max=50, step=5, value=20,
                               marks={5:"5%", 20:"20%", 35:"35%", 50:"50%"},
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
                        _gr_card("SQUEEZE",     "Momentum",    "gr-squeeze-card", "gr-squeeze-dot", "gr-squeeze-val"),
                        _gr_card("ADX",         "Dirección",   "gr-adx-card",     "gr-adx-dot",     "gr-adx-val"),
                        _gr_card("EMA",         "10 / 55",     "gr-ema-card",     "gr-ema-dot",     "gr-ema-val"),
                        _gr_card("S/R",         "Soporte/Res.","gr-sr-card",      "gr-sr-dot",      "gr-sr-val"),
                        _gr_card("VOL PROFILE", "Emergencia",  "gr-vol-card",     "gr-vol-dot",     "gr-vol-val"),
                        _gr_card("MTF",         "Multi-TF",    "gr-mtf-card",     "gr-mtf-dot",     "gr-mtf-val"),
                    ]),
                ]),
                html.Div(className="seccion-control", children=[
                    html.Div(id="lbl-stats", className="seccion-titulo",
                             children="Estadísticas en Tiempo Real"),
                    html.Div(id="stats-contenido", children=[
                        html.Div(className="stat-fila", children=[
                            html.Span("Precio",     className="stat-nombre"),
                            html.Span("–", id="stat-precio",   className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Cambio 7d",  className="stat-nombre"),
                            html.Span("–", id="stat-cambio",   className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("ADX",        className="stat-nombre"),
                            html.Span("–", id="stat-adx",      className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Momentum",   className="stat-nombre"),
                            html.Span("–", id="stat-momentum", className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Squeeze ON", className="stat-nombre"),
                            html.Span("–", id="stat-squeeze",  className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("EMA 10/55",  className="stat-nombre"),
                            html.Span("–", id="stat-ema",      className="stat-valor"),
                        ]),
                    ]),
                ]),
            ]),

            # RIGHT
            html.Div(className="panel-lateral derecho", children=[
                html.Div(className="seccion-control", children=[
                    html.Div(id="lbl-activos", className="seccion-titulo",
                             children="Activos (máx. 6)"),
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
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Trailing Stop"),
                    html.Div([
                        html.Div(className="stat-fila", children=[
                            html.Span("Activación",    className="stat-nombre"),
                            html.Span("+3.0%",         className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Distancia",     className="stat-nombre"),
                            html.Span("1.5%",          className="stat-valor"),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Sin Stop Fijo", className="stat-nombre"),
                            html.Span("OK",            className="stat-valor"),
                        ]),
                    ]),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Gestión de Racha"),
                    html.Div([
                        html.Div(className="stat-fila", children=[
                            html.Span("Pérdidas (2+)",  className="stat-nombre"),
                            html.Span("Reducir",        className="stat-valor",
                                      style={"color": "#ff3355"}),
                        ]),
                        html.Div(className="stat-fila", children=[
                            html.Span("Ganancias (3+)", className="stat-nombre"),
                            html.Span("Aumentar",       className="stat-valor",
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
        ]),

        # Grid de activos seleccionados (abajo, ancho completo)
        html.Div(id="asset-grid-section"),
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
                _gr_card("SQUEEZE",     "Momentum",    "d-gr-squeeze-card", "d-gr-squeeze-dot", "d-gr-squeeze-val"),
                _gr_card("ADX",         "Dirección",   "d-gr-adx-card",     "d-gr-adx-dot",     "d-gr-adx-val"),
                _gr_card("EMA",         "10 / 55",     "d-gr-ema-card",     "d-gr-ema-dot",     "d-gr-ema-val"),
                _gr_card("S/R",         "Soporte/Res.","d-gr-sr-card",      "d-gr-sr-dot",      "d-gr-sr-val"),
                _gr_card("VOL PROFILE", "Emergencia",  "d-gr-vol-card",     "d-gr-vol-dot",     "d-gr-vol-val"),
            ]),
        ]),
    ]


# ─── LAYOUT ESTÁTICO (siempre presente) ───────────────────────────────────────

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="store-idioma", data="es"),
    dcc.Store(id="store-bot",    data=False),
    dcc.Store(id="store-tf",     data="4H"),
    dcc.Interval(id="tick-relojes",     interval=1_000,  n_intervals=0),
    dcc.Interval(id="tick-main",        interval=30_000, n_intervals=0),
    dcc.Interval(id="tick-bot-status",  interval=5_000,  n_intervals=0),

    html.Div(id="header-main", children=[
        html.Div(className="logo-area", children=[
            html.Div(className="logo-texto", children=[
                html.H1(id="h-titulo",    children="AERO BOT PRO"),
                html.P (id="h-subtitulo", children="Trading Bot Profesional"),
            ]),
        ]),
        html.Div(id="led-container", className="led-indicator", children=[
            html.Div(id="led-dot",  className="led-dot desconectado"),
            html.Span(id="led-txt", className="led-texto", children="DESCONECTADO"),
        ]),
    ]),
    html.Div(id="relojes-barra", children=[
        _reloj("NEW YORK", "NY"), _reloj("LONDON", "LON"),
        _reloj("TOKYO",    "TYO"), _reloj("DUBAI",  "DXB"),
    ]),
    html.Div(id="frase-barra", children=[
        "El mercado recompensa la paciencia, no la prisa.",
        html.Span("- Jesse Livermore", className="autor"),
    ]),
    html.Div(id="page-content"),
])


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
    [Output("reloj-NY",  "children"), Output("reloj-LON", "children"),
     Output("reloj-TYO", "children"), Output("reloj-DXB", "children")],
    Input("tick-relojes", "n_intervals"),
)
def cb_relojes(_):
    zonas = ["America/New_York", "Europe/London", "Asia/Tokyo", "Asia/Dubai"]
    return [datetime.now(pytz.timezone(z)).strftime("%H:%M:%S") for z in zonas]


@app.callback(
    [Output("store-idioma",      "data"),
     Output("h-titulo",          "children"),
     Output("h-subtitulo",       "children"),
     Output("lbl-idioma",        "children"),
     Output("lbl-tf",            "children"),
     Output("lbl-capital",       "children"),
     Output("lbl-activos",       "children"),
     Output("lbl-guardarrailes", "children"),
     Output("lbl-stats",         "children"),
     Output("frase-barra",       "children")],
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
    [Output("btn-bot",   "children"), Output("btn-bot",   "className"),
     Output("led-dot",   "className"), Output("led-txt",   "children"),
     Output("store-bot", "data")],
    Input("btn-bot",           "n_clicks"),
    State("store-bot",         "data"),
    State("store-idioma",      "data"),
    State("checklist-activos", "value"),
    State("store-tf",          "data"),
    State("slider-capital",    "value"),
)
def cb_bot(n, activo, idioma, activos_sel, tf, capital_pct):
    global _bot_thread, _bot_stop
    t = TRANSLATIONS.get(idioma, TRANSLATIONS["es"])
    if not n:
        return t["start"], "btn-principal", "led-dot desconectado", t["disconnected"], False
    nuevo = not activo
    if nuevo:
        activos_lista = ["BTC"] + [a for a in (activos_sel or []) if a != "BTC"]
        _bot_stop.clear()
        _bot_thread = threading.Thread(
            target=_bot_loop,
            args=(activos_lista, tf or "4H", capital_pct or 20),
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
    Input("checklist-activos",  "value"),
    prevent_initial_call=True,
)
def cb_limitar(val):
    if val and len(val) > 6:
        return val[:6]
    return val or []


# ── Gráfico principal BTC (siempre) ──────────────────────────────────────────

@app.callback(
    [Output("grafico-principal", "figure"),
     Output("scoring-bar",  "children"),
     Output("gr-squeeze-card", "className"), Output("gr-squeeze-dot", "className"), Output("gr-squeeze-val", "children"),
     Output("gr-adx-card",     "className"), Output("gr-adx-dot",     "className"), Output("gr-adx-val",     "children"),
     Output("gr-ema-card",     "className"), Output("gr-ema-dot",     "className"), Output("gr-ema-val",     "children"),
     Output("gr-sr-card",      "className"), Output("gr-sr-dot",      "className"), Output("gr-sr-val",      "children"),
     Output("gr-vol-card",     "className"), Output("gr-vol-dot",     "className"), Output("gr-vol-val",     "children"),
     Output("gr-mtf-card",     "className"), Output("gr-mtf-dot",     "className"), Output("gr-mtf-val",     "children"),
     Output("stat-precio",   "children"), Output("stat-cambio",   "children"), Output("stat-cambio",   "style"),
     Output("stat-adx",      "children"), Output("stat-momentum", "children"),
     Output("stat-squeeze",  "children"), Output("stat-ema",      "children"),
    ],
    [Input("tick-main",   "n_intervals"), Input("store-tf", "data")],
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

    def _gr(est, val):
        return f"guardarrail-card {est}", f"guardarrail-indicador {est}", val

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
        sc_cls, sc_lbl, sc_sty = "sc-numero long",  t["long"],  {"color":"#00ff88"}
        sc_bar = {"width":pct,"background":"#00ff88","transition":"width .8s ease"}
    elif score <= -70:
        sc_cls, sc_lbl, sc_sty = "sc-numero short", t["short"], {"color":"#ff3355"}
        sc_bar = {"width":pct,"background":"#ff3355","transition":"width .8s ease"}
    else:
        sc_cls, sc_lbl, sc_sty = "sc-numero",       t["wait"],  {"color":"#a0a8c0"}
        sc_bar = {"width":pct,"background":"#c8a84b","transition":"width .8s ease"}

    bar = _scoring_bar_children(str(score), sc_cls, sc_lbl, sc_sty, sc_bar)

    u    = df.iloc[-1]
    ref  = df["close"].iloc[-7] if len(df) >= 7 else df["close"].iloc[0]
    chg  = (float(u["close"]) - float(ref)) / float(ref) * 100
    sgn  = "+" if chg >= 0 else ""
    cclr = "#00ff88" if chg >= 0 else "#ff3355"

    return (
        fig, bar,
        *_gr(gr["SQUEEZE"]["estado"],     gr["SQUEEZE"]["valor"]),
        *_gr(gr["ADX"]["estado"],         gr["ADX"]["valor"]),
        *_gr(gr["EMA"]["estado"],         gr["EMA"]["valor"]),
        *_gr(gr["S/R"]["estado"],         gr["S/R"]["valor"]),
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
        html.Div(numero,   id="sc-numero",   className=cls),
        html.Div(className="sc-barra-wrap", children=[
            html.Div(id="sc-barra", className="sc-barra", style=sty_barra),
        ]),
        html.Div(etiqueta, id="sc-etiqueta", className="sc-etiqueta", style=sty_etq),
    ]


# ── Grid de activos seleccionados ─────────────────────────────────────────────

@app.callback(
    Output("asset-grid-section", "children"),
    [Input("checklist-activos",  "value"),
     Input("store-tf",           "data"),
     Input("tick-main",          "n_intervals")],
)
def cb_asset_grid(activos, tf, _):
    if not activos:
        return []

    df_dict = {}
    for a in activos:
        df_dict[a] = obtener_datos(a, tf or "4H", velas=100)
        time.sleep(0.15)

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
    [Output("detail-graph",      "figure"),
     Output("d-scoring-bar",     "children"),
     Output("d-gr-squeeze-card", "className"), Output("d-gr-squeeze-dot", "className"), Output("d-gr-squeeze-val", "children"),
     Output("d-gr-adx-card",     "className"), Output("d-gr-adx-dot",     "className"), Output("d-gr-adx-val",     "children"),
     Output("d-gr-ema-card",     "className"), Output("d-gr-ema-dot",     "className"), Output("d-gr-ema-val",     "children"),
     Output("d-gr-sr-card",      "className"), Output("d-gr-sr-dot",      "className"), Output("d-gr-sr-val",      "children"),
     Output("d-gr-vol-card",     "className"), Output("d-gr-vol-dot",     "className"), Output("d-gr-vol-val",     "children"),
    ],
    [Input("detail-tick",       "n_intervals"),
     Input("detail-tf-radio",   "value")],
    State("url", "pathname"),
)
def cb_detail(_, tf, pathname):
    symbol = "BTC"
    if pathname and "/detail/" in pathname:
        symbol = pathname.split("/detail/")[-1].upper()

    def _gr(est, val):
        return f"guardarrail-card {est}", f"guardarrail-indicador {est}", val

    df = obtener_datos(symbol, tf or "4H")
    if df is None or df.empty:
        off = _gr("off", "-")
        bar = [html.Div("–", className="sc-numero"),
               html.Div(className="sc-barra-wrap",
                        children=[html.Div(className="sc-barra",
                                           style={"width":"50%","background":"#2a2a3a"})]),
               html.Div("–", className="sc-etiqueta", style={"color":"#a0a8c0"})]
        f = go.Figure()
        f.update_layout(paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f")
        return (f, bar, *off,*off,*off,*off,*off)

    score, gr = calcular_score(df)
    fig = crear_grafico(df, symbol, compacto=False)
    pct = f"{((score+100)/200)*100:.0f}%"

    if score >= 70:
        sc_cls, sc_lbl, sc_sty = "sc-numero long",  "LARGO",   {"color":"#00ff88"}
        sc_bar = {"width":pct,"background":"#00ff88","transition":"width .8s ease"}
    elif score <= -70:
        sc_cls, sc_lbl, sc_sty = "sc-numero short", "CORTO",   {"color":"#ff3355"}
        sc_bar = {"width":pct,"background":"#ff3355","transition":"width .8s ease"}
    else:
        sc_cls, sc_lbl, sc_sty = "sc-numero",       "ESPERAR", {"color":"#a0a8c0"}
        sc_bar = {"width":pct,"background":"#c8a84b","transition":"width .8s ease"}

    bar = [
        html.Div(str(score), className=sc_cls),
        html.Div(className="sc-barra-wrap",
                 children=[html.Div(className="sc-barra", style=sc_bar)]),
        html.Div(sc_lbl, className="sc-etiqueta", style=sc_sty),
    ]

    return (
        fig, bar,
        *_gr(gr["SQUEEZE"]["estado"],     gr["SQUEEZE"]["valor"]),
        *_gr(gr["ADX"]["estado"],         gr["ADX"]["valor"]),
        *_gr(gr["EMA"]["estado"],         gr["EMA"]["valor"]),
        *_gr(gr["S/R"]["estado"],         gr["S/R"]["valor"]),
        *_gr(gr["VOL PROFILE"]["estado"], gr["VOL PROFILE"]["valor"]),
    )


@app.callback(
    [Output("bot-balance-val",  "children"),
     Output("bot-log",          "children"),
     Output("telegram-estado",  "children"),
     Output("telegram-estado",  "style")],
    Input("tick-bot-status", "n_intervals"),
)
def cb_bot_status(_):
    with _bot_lock:
        bal = _bot_status["balance"]
        log = list(_bot_status["log"])

    bal_txt   = f"${bal:,.2f}" if isinstance(bal, float) else "–"
    log_items = [
        html.Div(msg, style={"borderBottom": "1px solid #1a1a28", "paddingBottom": "1px",
                              "marginBottom": "1px"})
        for msg in log[:5]
    ] if log else [html.Div("Sin actividad", style={"color": "#3a3a50"})]

    # Estado Telegram
    try:
        with open("config.json") as f:
            cfg = json.load(f)
        tg_ok = bool(cfg.get("telegram_token") and cfg.get("telegram_chatid"))
    except Exception:
        tg_ok = False
    tg_txt   = "✅ Conectado" if tg_ok else "⚠ No configurado"
    tg_style = {"color": "#00ff88", "fontSize": "12px"} if tg_ok else \
               {"color": "#f0c040", "fontSize": "12px"}

    return bal_txt, log_items, tg_txt, tg_style


if __name__ == "__main__":
    print("=" * 50)
    print("  AERO BOT PRO  —  Elite v2.0")
    print("  http://localhost:8051")
    print("=" * 50)
    app.run(debug=False, port=8051, host="0.0.0.0", use_reloader=False)
