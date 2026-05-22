import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import datetime
from plotly.subplots import make_subplots
from scipy.signal import argrelextrema

SIMBOLO = 'BTC/USDT'
TEMPORALIDAD = '4h'
VELAS = 200

def obtener_datos():
    exchange = ccxt.binance()
    velas = exchange.fetch_ohlcv(SIMBOLO, TEMPORALIDAD, limit=VELAS)
    df = pd.DataFrame(velas, columns=['tiempo','open','high','low','close','volumen'])
    df['tiempo'] = pd.to_datetime(df['tiempo'], unit='ms')
    df['EMA10'] = df['close'].ewm(span=10).mean()
    df['EMA55'] = df['close'].ewm(span=55).mean()

    # Squeeze Momentum
    bb_length, bb_mult = 20, 2.0
    kc_length, kc_mult = 20, 1.5
    df['BB_mid'] = df['close'].rolling(bb_length).mean()
    df['BB_std'] = df['close'].rolling(bb_length).std()
    df['BB_upper'] = df['BB_mid'] + bb_mult * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - bb_mult * df['BB_std']
    df['TR'] = pd.concat([df['high']-df['low'], (df['high']-df['close'].shift()).abs(), (df['low']-df['close'].shift()).abs()], axis=1).max(axis=1)
    df['KC_mid'] = df['close'].rolling(kc_length).mean()
    df['KC_range'] = df['TR'].rolling(kc_length).mean()
    df['KC_upper'] = df['KC_mid'] + kc_mult * df['KC_range']
    df['KC_lower'] = df['KC_mid'] - kc_mult * df['KC_range']
    df['squeeze'] = (df['BB_lower'] > df['KC_lower']) & (df['BB_upper'] < df['KC_upper'])
    highest_high = df['high'].rolling(kc_length).max()
    lowest_low = df['low'].rolling(kc_length).min()
    mid = (highest_high + lowest_low) / 2
    df['momentum'] = df['close'] - (mid + df['KC_mid']) / 2
    df['momentum'] = df['momentum'].rolling(kc_length).mean()

    # DMI / ADX
    length = 14
    df['H-L'] = df['high'] - df['low']
    df['H-PC'] = (df['high'] - df['close'].shift()).abs()
    df['L-PC'] = (df['low'] - df['close'].shift()).abs()
    df['TR14'] = pd.concat([df['H-L'], df['H-PC'], df['L-PC']], axis=1).max(axis=1)
    df['DM+'] = ((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low'])).astype(float) * (df['high'] - df['high'].shift()).clip(lower=0)
    df['DM-'] = ((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift())).astype(float) * (df['low'].shift() - df['low']).clip(lower=0)
    df['TR14s'] = df['TR14'].ewm(alpha=1/length, adjust=False).mean()
    df['DM+s'] = df['DM+'].ewm(alpha=1/length, adjust=False).mean()
    df['DM-s'] = df['DM-'].ewm(alpha=1/length, adjust=False).mean()
    df['DI+'] = 100 * df['DM+s'] / df['TR14s']
    df['DI-'] = 100 * df['DM-s'] / df['TR14s']
    df['DX'] = 100 * (df['DI+'] - df['DI-']).abs() / (df['DI+'] + df['DI-'])
    df['ADX'] = df['DX'].ewm(alpha=1/length, adjust=False).mean()

    return df

def calcular_volume_profile(df, bins=90):
    precio_min = df['low'].min()
    precio_max = df['high'].max()
    niveles = np.linspace(precio_min, precio_max, bins+1)
    volumen_por_nivel = []
    for i in range(len(niveles)-1):
        mask = (df['close'] >= niveles[i]) & (df['close'] < niveles[i+1])
        vol = df.loc[mask, 'volumen'].sum()
        volumen_por_nivel.append(vol)
    poc_idx = np.argmax(volumen_por_nivel)
    poc_precio = (niveles[poc_idx] + niveles[poc_idx+1]) / 2
    return niveles, volumen_por_nivel, poc_precio

def detectar_tendencias(df, orden=10):
    maximos_idx = argrelextrema(df['high'].values, np.greater, order=orden)[0]
    minimos_idx = argrelextrema(df['low'].values, np.less, order=orden)[0]
    lineas = []
    if len(maximos_idx) >= 2:
        idx1, idx2 = maximos_idx[-2], maximos_idx[-1]
        x1 = df['tiempo'].iloc[idx1]
        y1, y2 = df['high'].iloc[idx1], df['high'].iloc[idx2]
        pendiente = (y2 - y1) / (idx2 - idx1)
        pasos = len(df) - 1 - idx2
        y_extendido = y2 + pendiente * pasos
        lineas.append({'tipo': 'Resistencia', 'x': [x1, df['tiempo'].iloc[-1]], 'y': [y1, y_extendido], 'color': '#ff4444'})
    if len(minimos_idx) >= 2:
        idx1, idx2 = minimos_idx[-2], minimos_idx[-1]
        x1 = df['tiempo'].iloc[idx1]
        y1, y2 = df['low'].iloc[idx1], df['low'].iloc[idx2]
        pendiente = (y2 - y1) / (idx2 - idx1)
        pasos = len(df) - 1 - idx2
        y_extendido = y2 + pendiente * pasos
        lineas.append({'tipo': 'Soporte', 'x': [x1, df['tiempo'].iloc[-1]], 'y': [y1, y_extendido], 'color': '#00e676'})
    return lineas

def crear_grafico(df):
    precio_actual = df['close'].iloc[-1]
    precio_anterior = df['close'].iloc[-7]
    cambio_pct = ((precio_actual - precio_anterior) / precio_anterior) * 100
    hora = datetime.datetime.now().strftime('%H:%M:%S')

    niveles, volumen_por_nivel, poc_precio = calcular_volume_profile(df)
    lineas_tendencia = detectar_tendencias(df)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.02)

    # Velas
    fig.add_trace(go.Candlestick(
        x=df['tiempo'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name='BTC/USDT',
        increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
        decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
    ), row=1, col=1)

    # EMAs
    fig.add_trace(go.Scatter(x=df['tiempo'], y=df['EMA10'],
        line=dict(color='#2196F3', width=1.5), name='EMA 10'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['tiempo'], y=df['EMA55'],
        line=dict(color='#ef5350', width=1.8), name='EMA 55'), row=1, col=1)

    # Líneas de tendencia
    for linea in lineas_tendencia:
        fig.add_trace(go.Scatter(
            x=linea['x'], y=linea['y'],
            mode='lines',
            line=dict(color=linea['color'], width=1.5, dash='dot'),
            name=linea['tipo'], showlegend=True
        ), row=1, col=1)

    # Volume Profile
    vol_max = max(volumen_por_nivel)
    tiempo_max = df['tiempo'].max()
    tiempo_min = df['tiempo'].min()
    rango_tiempo = (tiempo_max - tiempo_min).total_seconds()
    for i in range(len(volumen_por_nivel)):
        precio_mid = (niveles[i] + niveles[i+1]) / 2
        es_poc = (i == np.argmax(volumen_por_nivel))
        color = '#FFD700' if es_poc else 'rgba(33, 150, 243, 0.3)'
        ancho = volumen_por_nivel[i] / vol_max
        tiempo_inicio = tiempo_max - pd.Timedelta(seconds=rango_tiempo * ancho * 0.15)
        fig.add_trace(go.Scatter(
            x=[tiempo_inicio, tiempo_max], y=[precio_mid, precio_mid],
            mode='lines', line=dict(color=color, width=3 if es_poc else 1.5),
            showlegend=False, hoverinfo='skip'
        ), row=1, col=1)

    fig.add_hline(y=poc_precio, line_dash='dot', line_color='#FFD700', line_width=1, row=1, col=1)

    # Squeeze Momentum
    colores = []
    for i in range(len(df)):
        val = df['momentum'].iloc[i]
        prev = df['momentum'].iloc[i-1] if i > 0 else val
        if val >= 0:
            colores.append('#00e676' if val > prev else '#26a69a')
        else:
            colores.append('#ef5350' if val < prev else '#b71c1c')

    fig.add_trace(go.Bar(x=df['tiempo'], y=df['momentum'],
        marker_color=colores, name='Squeeze Momentum'), row=2, col=1)
    squeeze_dots = df[df['squeeze']]
    fig.add_trace(go.Scatter(
        x=squeeze_dots['tiempo'], y=[0]*len(squeeze_dots),
        mode='markers', marker=dict(color='#2196F3', size=4),
        name='Squeeze ON'), row=2, col=1)

    # ADX
    adx_actual = df['ADX'].iloc[-1]
    color_adx = '#00e676' if adx_actual >= 23 else '#888888'
    fig.add_trace(go.Scatter(x=df['tiempo'], y=df['ADX'],
        line=dict(color=color_adx, width=1.5),
        name=f'ADX ({adx_actual:.1f})'), row=3, col=1)
    fig.add_hline(y=23, line_dash='dash', line_color='#FFD700', line_width=1, row=3, col=1)

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#131722',
        plot_bgcolor='#131722',
        xaxis=dict(gridcolor='#1e2130', rangeslider=dict(visible=False), color='#888'),
        xaxis2=dict(gridcolor='#1e2130', color='#888'),
        xaxis3=dict(gridcolor='#1e2130', color='#888'),
        yaxis=dict(gridcolor='#1e2130', color='#888', side='right'),
        yaxis2=dict(gridcolor='#1e2130', color='#888', side='right'),
        yaxis3=dict(gridcolor='#1e2130', color='#888', side='right'),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='white')),
        margin=dict(l=10, r=70, t=20, b=40),
        # CROSSHAIR horizontal y vertical
        hovermode='x',
        hoverdistance=100,
        spikedistance=1000,
        xaxis_showspikes=True,
        xaxis_spikemode='across',
        xaxis_spikesnap='cursor',
        xaxis_spikecolor='#888888',
        xaxis_spikethickness=1,
        xaxis_spikedash='dot',
        yaxis_showspikes=True,
        yaxis_spikemode='across',
        yaxis_spikesnap='cursor',
        yaxis_spikecolor='#888888',
        yaxis_spikethickness=1,
        yaxis_spikedash='dot',
    )
    return fig, precio_actual, cambio_pct, hora

app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.Span('⚡ Aero TradingBot Pro', style={'color':'#2196F3', 'fontSize':'22px', 'fontWeight':'bold', 'marginRight':'20px'}),
        html.Span(id='precio', style={'fontSize':'26px', 'fontWeight':'bold', 'marginRight':'15px', 'color':'white'}),
        html.Span(id='cambio', style={'fontSize':'18px', 'marginRight':'20px'}),
        html.Span(id='hora', style={'color':'#888', 'fontSize':'13px'}),
    ], style={'backgroundColor':'#131722', 'padding':'10px 20px', 'fontFamily':'Arial'}),
    dcc.Graph(id='grafico', style={'height':'88vh'}),
    dcc.Interval(id='intervalo', interval=5*60*1000, n_intervals=0)
], style={'backgroundColor':'#131722'})

@app.callback(
    Output('grafico', 'figure'),
    Output('precio', 'children'),
    Output('cambio', 'children'),
    Output('cambio', 'style'),
    Output('hora', 'children'),
    Input('intervalo', 'n_intervals')
)
def actualizar(n):
    df = obtener_datos()
    fig, precio_actual, cambio_pct, hora = crear_grafico(df)
    signo = '+' if cambio_pct >= 0 else ''
    color = '#00ff88' if cambio_pct >= 0 else '#ff4444'
    return (
        fig,
        f'${precio_actual:,.2f}',
        f'{signo}{cambio_pct:.2f}%',
        {'fontSize':'18px', 'color':color},
        f'Actualizado: {hora}'
    )

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')