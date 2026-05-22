"""
AERO BOT PRO - PLANIFICADOR PRINCIPAL
Puerto 8051 | Version 1.0 | Eduardo Andrade
"""

import dash
from dash import dcc, html, Input, Output, State
from datetime import datetime
import pytz
import random

TRANSLATIONS = {
    "es": {
        "title": "AERO BOT PRO",
        "subtitle": "Trading Bot Profesional",
        "connected": "CONECTADO",
        "disconnected": "DESCONECTADO",
        "language": "Idioma",
        "timeframe": "Temporalidad",
        "assets": "Activos",
        "capital": "Capital por Op.",
        "score": "PUNTUACION GLOBAL",
        "long": "LARGO",
        "short": "CORTO",
        "wait": "ESPERAR",
        "stats": "Estadisticas en Tiempo Real",
        "guardrails": "Guardarrailes",
        "start": "INICIAR BOT",
        "stop": "DETENER BOT",
    },
    "en": {
        "title": "AERO BOT PRO",
        "subtitle": "Professional Trading Bot",
        "connected": "CONNECTED",
        "disconnected": "DISCONNECTED",
        "language": "Language",
        "timeframe": "Timeframe",
        "assets": "Assets",
        "capital": "Capital per Op.",
        "score": "GLOBAL SCORE",
        "long": "LONG",
        "short": "SHORT",
        "wait": "WAIT",
        "stats": "Real-Time Statistics",
        "guardrails": "Guardrails",
        "start": "START BOT",
        "stop": "STOP BOT",
    },
    "it": {
        "title": "AERO BOT PRO",
        "subtitle": "Bot di Trading Professionale",
        "connected": "CONNESSO",
        "disconnected": "DISCONNESSO",
        "language": "Lingua",
        "timeframe": "Temporalita",
        "assets": "Asset",
        "capital": "Capitale per Op.",
        "score": "PUNTEGGIO GLOBALE",
        "long": "LUNGO",
        "short": "CORTO",
        "wait": "ATTENDI",
        "stats": "Statistiche in Tempo Reale",
        "guardrails": "Guardrail",
        "start": "AVVIA BOT",
        "stop": "FERMA BOT",
    },
    "fr": {
        "title": "AERO BOT PRO",
        "subtitle": "Bot de Trading Professionnel",
        "connected": "CONNECTE",
        "disconnected": "DECONNECTE",
        "language": "Langue",
        "timeframe": "Temporalite",
        "assets": "Actifs",
        "capital": "Capital par Op.",
        "score": "SCORE GLOBAL",
        "long": "LONG",
        "short": "COURT",
        "wait": "ATTENDRE",
        "stats": "Statistiques en Temps Reel",
        "guardrails": "Garde-fous",
        "start": "DEMARRER BOT",
        "stop": "ARRETER BOT",
    },
    "de": {
        "title": "AERO BOT PRO",
        "subtitle": "Professioneller Trading Bot",
        "connected": "VERBUNDEN",
        "disconnected": "GETRENNT",
        "language": "Sprache",
        "timeframe": "Zeitrahmen",
        "assets": "Assets",
        "capital": "Kapital pro Op.",
        "score": "GESAMTPUNKTZAHL",
        "long": "LONG",
        "short": "SHORT",
        "wait": "WARTEN",
        "stats": "Echtzeit-Statistiken",
        "guardrails": "Leitplanken",
        "start": "BOT STARTEN",
        "stop": "BOT STOPPEN",
    },
}

QUOTES = {
    "es": [
        ("No operes nunca el mercado por aburrimiento.", "Eduardo Andrade"),
        ("Si hay problemas familiares, tomaté una pausa y no operes.", "Eduardo Andrade"),
        ("La venganza no existe en el trading.", "Eduardo Andrade"),
        ("Jamas operes bajo los estimulos del alcohol o de alguna otra droga.", "Eduardo Andrade"),
        ("La paciencia paga y la desesperacion pega.", "Eduardo Andrade"),
        ("Jamas te sientas ansioso si el precio se te escapa, el mercado es una marea de oportunidades infinita.", "Eduardo Andrade"),
        ("Nunca juegues a improvisar, apegate 100% a tu estrategia y se fiel a ella.", "Eduardo Andrade"),
        ("El mercado recompensa la paciencia, no la prisa.", "Jesse Livermore"),
        ("Corta tus perdidas y deja correr tus ganancias.", "Paul Tudor Jones"),
        ("El riesgo viene de no saber lo que estas haciendo.", "Warren Buffett"),
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
        ("Non sentirti mai ansioso se il prezzo ti sfugge, il mercato e una marea infinita di opportunita.", "Eduardo Andrade"),
        ("Non improvvisare mai, attieniti al 100% alla tua strategia.", "Eduardo Andrade"),
        ("Il mercato premia la pazienza, non la fretta.", "Jesse Livermore"),
        ("Taglia le perdite e lascia correre i profitti.", "Paul Tudor Jones"),
        ("Il rischio deriva dal non sapere cosa stai facendo.", "Warren Buffett"),
    ],
    "fr": [
        ("Ne tradez jamais par ennui.", "Eduardo Andrade"),
        ("Si vous avez des problemes familiaux, faites une pause et ne tradez pas.", "Eduardo Andrade"),
        ("La vengeance n'existe pas dans le trading.", "Eduardo Andrade"),
        ("Ne tradez jamais sous l'influence de l'alcool ou d'une autre drogue.", "Eduardo Andrade"),
        ("La patience paie et le desespoir fait mal.", "Eduardo Andrade"),
        ("Ne vous sentez jamais anxieux si le prix vous echappe, le marche est une maree infinie d'opportunites.", "Eduardo Andrade"),
        ("N'improvisez jamais, respectez 100% votre strategie.", "Eduardo Andrade"),
        ("Le marche recompense la patience, pas la hate.", "Jesse Livermore"),
        ("Coupez vos pertes et laissez courir vos profits.", "Paul Tudor Jones"),
        ("Le risque vient de ne pas savoir ce que vous faites.", "Warren Buffett"),
    ],
    "de": [
        ("Handle nie aus Langeweile.", "Eduardo Andrade"),
        ("Bei Familienproblemen mach eine Pause und handle nicht.", "Eduardo Andrade"),
        ("Rache existiert im Trading nicht.", "Eduardo Andrade"),
        ("Handle nie unter dem Einfluss von Alkohol oder anderen Drogen.", "Eduardo Andrade"),
        ("Geduld zahlt sich aus, Verzweiflung schadet.", "Eduardo Andrade"),
        ("Sei nie angstlich, wenn der Preis dir entgeht, der Markt ist eine unendliche Flut von Chancen.", "Eduardo Andrade"),
        ("Improvisiere nie, halte dich 100% an deine Strategie.", "Eduardo Andrade"),
        ("Der Markt belohnt Geduld, nicht Eile.", "Jesse Livermore"),
        ("Kurze deine Verluste und lass deine Gewinne laufen.", "Paul Tudor Jones"),
        ("Risiko entsteht durch Unwissenheit.", "Warren Buffett"),
    ],
}

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="AERO BOT PRO",
    update_title=None,
)
server = app.server


def crear_reloj(ciudad, codigo):
    return html.Div(className="reloj-ciudad", children=[
        html.Div(ciudad, className="ciudad-nombre"),
        html.Div("--:--:--", id=f"reloj-{codigo}", className="ciudad-hora"),
        html.Div(codigo, className="ciudad-sesion"),
    ])


def crear_guardarrailes_demo():
    guardarrailes = [
        ("SQUEEZE", "Momentum", "off", "-"),
        ("ADX", "Direccion", "off", "-"),
        ("EMA", "10 / 55", "off", "-"),
        ("S/R", "Soporte/Res.", "off", "-"),
        ("VOL PROFILE", "Emergencia", "off", "-"),
        ("MTF", "Multi-TF", "off", "-"),
    ]
    cards = []
    for nombre, tipo, estado, valor in guardarrailes:
        cards.append(
            html.Div(className=f"guardarrail-card {estado}", children=[
                html.Div(children=[
                    html.Span(className=f"guardarrail-indicador {estado}"),
                    html.Span(nombre, className="guardarrail-nombre"),
                ]),
                html.Div(tipo, style={"fontSize": "10px", "color": "#6b5520",
                                      "letterSpacing": "0.1em", "marginTop": "2px"}),
                html.Div(valor, className="guardarrail-valor"),
            ])
        )
    return cards


def crear_stats_demo():
    return [
        html.Div(className="stat-fila", children=[
            html.Span("Tasa de Exito", className="stat-nombre"),
            html.Span("-", className="stat-valor"),
        ]),
        html.Div(className="stat-fila", children=[
            html.Span("Operaciones", className="stat-nombre"),
            html.Span("0", className="stat-valor"),
        ]),
        html.Div(className="stat-fila", children=[
            html.Span("Beneficio", className="stat-nombre"),
            html.Span("$0.00", className="stat-valor"),
        ]),
        html.Div(className="stat-fila", children=[
            html.Span("Drawdown Max.", className="stat-nombre"),
            html.Span("0.0%", className="stat-valor", style={"color": "#ff3355"}),
        ]),
        html.Div(className="stat-fila", children=[
            html.Span("En operacion", className="stat-nombre"),
            html.Span("No", className="stat-valor", style={"color": "#a0a8c0"}),
        ]),
    ]


def crear_layout():
    return html.Div([
        dcc.Store(id="store-idioma", data="es"),
        dcc.Store(id="store-bot-activo", data=False),
        dcc.Interval(id="intervalo-relojes", interval=1000, n_intervals=0),
        dcc.Interval(id="intervalo-scoring", interval=5000, n_intervals=0),

        html.Div(id="header-main", children=[
            html.Div(className="logo-area", children=[
                html.Div("A", className="logo-icono"),
                html.Div(className="logo-texto", children=[
                    html.H1(id="titulo-h1", children="AERO BOT PRO"),
                    html.P(id="subtitulo-p", children="Trading Bot Profesional"),
                ]),
            ]),
            html.Div(id="led-container", className="led-indicator", children=[
                html.Div(id="led-dot", className="led-dot desconectado"),
                html.Span(id="led-texto", className="led-texto", children="DESCONECTADO"),
            ]),
        ]),

        html.Div(id="relojes-barra", children=[
            crear_reloj("NEW YORK", "NY"),
            crear_reloj("LONDON", "LON"),
            crear_reloj("TOKYO", "TYO"),
            crear_reloj("DUBAI", "DXB"),
        ]),

        html.Div(id="frase-barra", children=[
            "El mercado recompensa la paciencia, no la prisa.",
            html.Span("- Jesse Livermore", className="autor"),
        ]),

        html.Div(id="contenido-principal", children=[

            html.Div(className="panel-lateral", children=[
                html.Div(className="seccion-control", children=[
                    html.Div(id="label-idioma", className="seccion-titulo", children="Idioma"),
                    dcc.RadioItems(
                        id="radio-idioma",
                        options=[
                            {"label": "ES", "value": "es"},
                            {"label": "EN", "value": "en"},
                            {"label": "IT", "value": "it"},
                            {"label": "FR", "value": "fr"},
                            {"label": "DE", "value": "de"},
                        ],
                        value="es",
                        className="radio-idiomas",
                        inputStyle={"display": "none"},
                    ),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(id="label-temporalidad", className="seccion-titulo", children="Temporalidad"),
                    dcc.RadioItems(
                        id="radio-temporalidad",
                        options=[
                            {"label": "1 Semana",   "value": "1W"},
                            {"label": "1 Dia",      "value": "1D"},
                            {"label": "4 Horas",    "value": "4H"},
                            {"label": "1 Hora",     "value": "1H"},
                            {"label": "15 Minutos", "value": "15m"},
                        ],
                        value="4H",
                        className="radio-grupo",
                        labelStyle={"display": "flex", "alignItems": "center", "gap": "10px"},
                    ),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(id="label-capital", className="seccion-titulo", children="Capital por Op."),
                    html.Div(style={"textAlign": "center", "marginBottom": "8px"}, children=[
                        html.Span(id="valor-capital", style={
                            "fontFamily": "Cinzel, serif",
                            "fontSize": "22px",
                            "color": "#f0c040",
                        }, children="20%"),
                    ]),
                    dcc.Slider(
                        id="slider-capital",
                        min=5, max=50, step=5, value=20,
                        marks={5: "5%", 20: "20%", 35: "35%", 50: "50%"},
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ]),
            ]),

            html.Div(id="panel-central", children=[
                html.Div(className="scoring-container", children=[
                    html.Div(id="scoring-titulo", className="scoring-titulo", children="PUNTUACION GLOBAL"),
                    html.Div(id="scoring-numero", className="scoring-numero", children="0"),
                    html.Div(id="scoring-etiqueta", className="scoring-etiqueta",
                             children="ESPERAR", style={"color": "#a0a8c0"}),
                    html.Div(className="scoring-barra-contenedor", children=[
                        html.Div(id="scoring-barra", className="scoring-barra",
                                 style={"width": "50%", "background": "#2a2a3a"}),
                    ]),
                ]),
                html.Div(className="seccion-control", children=[
                    html.Div(id="label-guardarrailes", className="seccion-titulo", children="Guardarrailes"),
                    html.Div(className="guardarrail-grid", id="guardarrail-grid",
                             children=crear_guardarrailes_demo()),
                ]),
                html.Div(className="stats-container", children=[
                    html.Div(id="label-stats", className="seccion-titulo",
                             children="Estadisticas en Tiempo Real"),
                    html.Div(id="stats-contenido", children=crear_stats_demo()),
                ]),
            ]),

            html.Div(className="panel-lateral derecho", children=[
                html.Div(className="seccion-control", children=[
                    html.Div(id="label-activos", className="seccion-titulo", children="Activos"),
                    dcc.Checklist(
                        id="checklist-activos",
                        options=[
                            {"label": "BTC/USDT",  "value": "BTC"},
                            {"label": "ETH/USDT",  "value": "ETH"},
                            {"label": "XRP/USDT",  "value": "XRP"},
                            {"label": "BNB/USDT",  "value": "BNB"},
                            {"label": "SOL/USDT",  "value": "SOL"},
                            {"label": "TRX/USDT",  "value": "TRX"},
                            {"label": "ADA/USDT",  "value": "ADA"},
                            {"label": "HYPE/USDT", "value": "HYPE"},
                            {"label": "DOGE/USDT", "value": "DOGE"},
                            {"label": "AVAX/USDT", "value": "AVAX"},
                        ],
                        value=["BTC", "ETH"],
                        className="checklist-activos",
                        labelStyle={"display": "flex", "alignItems": "center", "gap": "10px"},
                    ),
                ]),
                html.Div(className="separador-dorado"),
                html.Div(className="seccion-control", children=[
                    html.Div(className="seccion-titulo", children="Trailing Stop"),
                    html.Div([
                        html.Div(className="stat-fila", children=[
                            html.Span("Activacion",    className="stat-nombre"),
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
                    html.Div(className="seccion-titulo", children="Gestion de Racha"),
                    html.Div([
                        html.Div(className="stat-fila", children=[
                            html.Span("Perdidas (2+)",  className="stat-nombre"),
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
                html.Button(
                    id="btn-bot",
                    children="INICIAR BOT",
                    className="btn-principal",
                    n_clicks=0,
                ),
                html.Div(className="seccion-control", style={"marginTop": "8px"}, children=[
                    html.Div(className="seccion-titulo", children="Telegram"),
                    html.Div(className="stat-fila", children=[
                        html.Span("Estado", className="stat-nombre"),
                        html.Span("No configurado", id="telegram-estado",
                                  style={"color": "#a0a8c0", "fontSize": "12px"}),
                    ]),
                ]),
            ]),
        ]),
    ])


@app.callback(
    [Output("reloj-NY",  "children"),
     Output("reloj-LON", "children"),
     Output("reloj-TYO", "children"),
     Output("reloj-DXB", "children")],
    Input("intervalo-relojes", "n_intervals"),
)
def actualizar_relojes(n):
    zonas = ["America/New_York", "Europe/London", "Asia/Tokyo", "Asia/Dubai"]
    return [datetime.now(pytz.timezone(z)).strftime("%H:%M:%S") for z in zonas]


@app.callback(
    [Output("store-idioma",        "data"),
     Output("titulo-h1",           "children"),
     Output("subtitulo-p",         "children"),
     Output("label-idioma",        "children"),
     Output("label-temporalidad",  "children"),
     Output("label-capital",       "children"),
     Output("label-activos",       "children"),
     Output("label-guardarrailes", "children"),
     Output("label-stats",         "children"),
     Output("scoring-titulo",      "children"),
     Output("frase-barra",         "children")],
    Input("radio-idioma", "value"),
)
def cambiar_idioma(idioma):
    t = TRANSLATIONS.get(idioma, TRANSLATIONS["es"])
    frase, autor = random.choice(QUOTES.get(idioma, QUOTES["es"]))
    frase_div = [frase, html.Span(f"- {autor}", className="autor")]
    return (
        idioma, t["title"], t["subtitle"], t["language"],
        t["timeframe"], t["capital"], t["assets"],
        t["guardrails"], t["stats"], t["score"], frase_div,
    )


@app.callback(
    Output("valor-capital", "children"),
    Input("slider-capital", "value"),
)
def actualizar_capital(valor):
    return f"{valor}%"


@app.callback(
    [Output("btn-bot",          "children"),
     Output("btn-bot",          "className"),
     Output("led-dot",          "className"),
     Output("led-texto",        "children"),
     Output("store-bot-activo", "data")],
    Input("btn-bot", "n_clicks"),
    State("store-bot-activo", "data"),
    State("store-idioma",     "data"),
)
def toggle_bot(n_clicks, activo, idioma):
    t = TRANSLATIONS.get(idioma, TRANSLATIONS["es"])
    if not n_clicks:
        return t["start"], "btn-principal", "led-dot desconectado", t["disconnected"], False
    nuevo = not activo
    if nuevo:
        return t["stop"], "btn-principal stop", "led-dot", t["connected"], True
    return t["start"], "btn-principal", "led-dot desconectado", t["disconnected"], False


@app.callback(
    [Output("scoring-numero",   "children"),
     Output("scoring-numero",   "className"),
     Output("scoring-etiqueta", "children"),
     Output("scoring-etiqueta", "style"),
     Output("scoring-barra",    "style")],
    Input("intervalo-scoring", "n_intervals"),
    State("store-bot-activo",  "data"),
    State("store-idioma",      "data"),
)
def actualizar_scoring(n, activo, idioma):
    t = TRANSLATIONS.get(idioma, TRANSLATIONS["es"])
    if not activo:
        return "0", "scoring-numero", t["wait"], {"color": "#a0a8c0"}, \
               {"width": "50%", "background": "#2a2a3a"}
    score = random.randint(-100, 100)
    pct = f"{((score + 100) / 200) * 100:.0f}%"
    if score >= 70:
        return str(score), "scoring-numero long", t["long"], \
               {"color": "#00ff88"}, {"width": pct, "background": "#00ff88", "transition": "width 0.8s ease"}
    elif score <= -70:
        return str(score), "scoring-numero short", t["short"], \
               {"color": "#ff3355"}, {"width": pct, "background": "#ff3355", "transition": "width 0.8s ease"}
    return str(score), "scoring-numero", t["wait"], \
           {"color": "#a0a8c0"}, {"width": pct, "background": "#c8a84b", "transition": "width 0.8s ease"}


app.layout = crear_layout()

if __name__ == "__main__":
    print("AERO BOT PRO - Puerto 8051")
    app.run(debug=True, port=8051, host="0.0.0.0")