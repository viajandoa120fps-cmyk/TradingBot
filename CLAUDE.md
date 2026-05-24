# AERO BOT PRO — Guía para Claude

Reglas de desarrollo para este proyecto. Seguirlas siempre, sin excepción.

---

## Arquitectura

- **`main.py`** — Dashboard Dash (puerto 8051). Toda la UI, callbacks, bot loop y lógica de indicadores.
- **`bingx.py`** — Módulo de exchange. Solo `verificar_balance()`, `colocar_orden()`, `cerrar_posicion()`.
- **`config.json`** — Configuración del usuario. Leído al arrancar el bot, nunca en hot paths.
- **`iniciar_bot.bat`** — Lanzador Windows. Doble clic para iniciar.

---

## Reglas críticas — bugs que ya ocurrieron, no repetir

### 1. Funciones que devuelven múltiples valores: consistencia total
Cualquier función que devuelva una tupla SIEMPRE debe devolver esa misma forma en TODOS sus paths de retorno.

```python
# MAL — crash al desempacar
def crear_mini_grafico(df_dict):
    if not activos:
        return go.Figure()       # solo Figure
    return fig, rows             # tuple

# BIEN
def crear_mini_grafico(df_dict):
    if not activos:
        return go.Figure(), 1    # siempre (fig, rows)
    return fig, rows
```

### 2. Leer config.json: solo al arrancar, nunca en loops ni callbacks
`config.json` se lee UNA sola vez al iniciar `_bot_loop`. Las credenciales Telegram se guardan en `_tg_token` / `_tg_chatid` a nivel módulo. Nunca hacer `open("config.json")` dentro de:
- `_enviar_telegram()`
- `cb_bot_status()`
- `_pagina_principal()` (solo al primer render, aceptable)
- Cualquier callback que se dispare por `dcc.Interval`

### 3. True Range: calcular una sola vez por llamada
En `obtener_datos()` el TR se calcula como `tr` para Keltner Channels. ADX **reutiliza ese mismo `tr`** — nunca crear `tr14` como una segunda computación idéntica.

```python
# MAL — TR calculado dos veces
tr   = pd.concat([...]).max(axis=1)   # para KC
tr14 = pd.concat([...]).max(axis=1)   # para ADX — DUPLICADO

# BIEN
tr = pd.concat([...]).max(axis=1)     # una sola vez
# KC usa tr, ADX también usa tr
tr_s = tr.ewm(alpha=a, adjust=False).mean()
```

### 4. Constantes del linreg fuera de funciones
`_LR_X`, `_LR_XVAR`, `_LR_XEND` y `_linreg_last` son constantes que dependen solo de `kl=20`. Están definidas a nivel módulo. Nunca moverlas dentro de `obtener_datos()`.

### 5. Volume Profile: máximo 2 trazas Plotly
El VP tiene 90 bins. Se renderizan con **2 trazas** usando separadores `None`, no 90 trazas individuales:
- Traza 1: todos los bins no-POC concatenados con `None` entre cada segmento
- Traza 2: solo el bin POC en dorado

```python
# MAL — 90 fig.add_trace() en un loop
for i, v in enumerate(vols):
    fig.add_trace(go.Scatter(...))

# BIEN — 2 trazas totales
x_vp, y_vp = [], []
for i, v in enumerate(vols):
    if i == poc_idx: continue
    x_vp += [t_ini, t_max, None]
    y_vp += [pmid, pmid, None]
fig.add_trace(go.Scatter(x=x_vp, y=y_vp, ...))   # traza 1
fig.add_trace(go.Scatter(x=[poc_tini, t_max], ...)) # traza 2
```

### 6. Nunca usar time.sleep() dentro de callbacks Dash
Los callbacks de Dash bloquean el thread de Flask. Usar `ThreadPoolExecutor` para fetches paralelos.

```python
# MAL — bloquea ~900ms con 6 activos
for a in activos:
    df_dict[a] = obtener_datos(a, tf, 100)
    time.sleep(0.15)

# BIEN — fetch paralelo
with ThreadPoolExecutor(max_workers=min(len(activos), 6)) as pool:
    futures = {pool.submit(obtener_datos, a, tf, 100): a for a in activos}
    for fut in as_completed(futures):
        df_dict[futures[fut]] = fut.result()
```

### 7. `verificar_balance()` siempre devuelve float o None
Nunca `(None, str)`. El caller usa directamente el valor sin `isinstance` checks.

```python
# MAL
except Exception as e:
    return None, str(e)

# BIEN
except Exception:
    return None
```

### 8. Actualizar precio_extremo ANTES de cualquier check de exit
En el bot loop, `precio_extremo` se actualiza al inicio del bloque de posición, antes del stop loss y antes del trailing stop. Nunca dentro del bloque de trailing stop únicamente.

### 9. Helpers compartidos a nivel módulo, nunca duplicados en callbacks
`_gr(est, val)` es una función de módulo. No redefinirla como función local dentro de `cb_btc_dashboard` o `cb_detail`.

```python
# MAL — definida dos veces en dos callbacks distintos
def cb_btc_dashboard(...):
    def _gr(est, val): ...   # local

def cb_detail(...):
    def _gr(est, val): ...   # otra vez

# BIEN — una sola vez a nivel módulo
def _gr(est, val):
    return f"guardarrail-card {est}", f"guardarrail-indicador {est}", val
```

### 10. Trim del log siempre a `[:8]` en todos los paths
Cada vez que se hace `.insert(0, ...)` en `_bot_status["log"]`, la línea siguiente debe ser:
```python
_bot_status["log"] = _bot_status["log"][:8]
```
Sin excepción, incluyendo el bloque de max-pérdida diaria.

### 11. Fallback de capital_pct: usar el valor del slider, no el viejo default
El slider tiene `value=5`. El fallback en `cb_bot` debe ser `capital_pct or 5`, no `or 20`.

### 12. ccxt.bingx() SIEMPRE con API keys — nunca instancia vacía
`obtener_datos()` crea la instancia BingX con las credenciales del módulo. Sin keys, BingX falla silenciosamente y TODOS los datos vienen de Binance spot (precios distintos). Este bug es invisible si no hay logging.

```python
# MAL — falla silenciosa, cae a Binance sin avisar
ex = ccxt.bingx({"enableRateLimit": True})

# BIEN — usa credenciales del módulo + logging explícito
ex = ccxt.bingx({
    "apiKey": _bx_api_key,
    "secret": _bx_api_secret,
    "enableRateLimit": True,
})
```

Las credenciales BingX se cargan a nivel módulo al inicio del proceso (no en el bot loop):
```python
_bx_api_key:    str = ""
_bx_api_secret: str = ""
try:
    with open("config.json") as _f_ini:
        _ini_cfg = json.load(_f_ini)
    _bx_api_key    = str(_ini_cfg.get("api_key",    ""))
    _bx_api_secret = str(_ini_cfg.get("api_secret", ""))
except Exception:
    pass
```

### 13. Fallback a Binance: siempre loggear, nunca silencioso
Cuando BingX falla y el sistema cae a Binance, DEBE aparecer un mensaje en consola. Un fallback silencioso hace imposible diagnosticar de qué fuente vienen los datos.

```python
# MAL — el usuario nunca sabe si está usando Binance
except Exception:
    pass
if not raw:
    ex = ccxt.binance(...)

# BIEN — log explícito en cada error y en el fallback
except Exception as e:
    print(f"[⚠ BingX OHLCV] {activo} {temporalidad}: {e}")
if not raw:
    print(f"[⚠ FALLBACK Binance] {activo} {temporalidad} — BingX no respondió.")
```

### 14. Panel de señales por activo — patrón `_señal_card()`
El panel `panel-señales-mini` muestra una tarjeta por activo seleccionado con barra de progreso hacia el umbral ±70. Los scores se almacenan en `_bot_status["scores"]` (dict `{activo: float}`). El callback `cb_bot_status` recibe `State("checklist-activos", "value")` para saber qué activos renderizar.

```python
# Score guardado en bot loop (después de calcular_score, antes de MTF)
with _bot_lock:
    _bot_status["scores"][activo] = score

# Lógica de porcentaje
pct = min(abs(score) / 70 * 100, 100)  # 0% = neutral, 100% = umbral alcanzado
```

---

## Estructura del bot loop

El orden correcto de checks dentro de `for activo in activos_lista` es:

```
1. obtener_datos() + calcular_score()
2. _analizar_mtf(activo, ema_comp_pct)  →  mtf dict
3. Actualizar precio_extremo (incondicional, antes de todo)
4. STOP LOSS FIJO (si pérdida >= stop_loss_pct%)
5. TRAILING STOP (si profit >= ts_activacion% y retroceso >= ts_distancia%)
6. CIERRE COMPRESION EMA (si abs(mtf["4H"]["sep"]) < ema_comp_pct)
7. CIERRE ZONA WAIT (si -70 < score < 70)
8. ENTRADA LONG/SHORT — filtrada por mtf["long_ok"] / mtf["short_ok"]
```

---

## MTF Guardarrail — lógica de cascada

```
1W define la dirección maestra:
  - sep > +ema_comp_pct AND mom > 0  →  "alcista"  (solo LONGS)
  - sep < -ema_comp_pct AND mom < 0  →  "bajista"  (solo SHORTS)
  - cualquier otro caso               →  "compresion" (sin entradas)

1D filtra: mom_1d debe estar en la misma dirección que 1W
  - dir_1w="alcista"  → mom_1d > 0  para habilitar
  - dir_1w="bajista"  → mom_1d < 0  para habilitar

4H confirma la entrada:
  - sep_4h > +ema_comp_pct AND mom_4h > 0  →  long_ok = True
  - sep_4h < -ema_comp_pct AND mom_4h < 0  →  short_ok = True

Cierre por compresión: abs(sep_4h) < ema_comp_pct → cerrar posición abierta
  (las EMAs se están apretando: "la fiesta ya no puede continuar")
```

### Regla clave de EMAs en MTF
Las EMAs NO se usan para detectar el cruce (eso llegaría tarde).
Se usan para saber si **la tendencia sigue viva** (separación > umbral).
El momentum cruzando cero detecta el **inicio** del giro.

```python
sep = (EMA10 - EMA55) / EMA55 * 100   # separación porcentual
# sep > +1%  AND  mom > 0  →  tendencia alcista viva
# sep < -1%  AND  mom < 0  →  tendencia bajista viva
# abs(sep) < 1%             →  compresión (fiesta terminando)
```

### _analizar_mtf() fetch paralelo
Siempre usa `ThreadPoolExecutor(max_workers=3)` para los 3 TF.
Nunca en serie para no bloquear el bot loop.

---

## Estado global del bot

```python
_bot_thread = None
_bot_stop   = threading.Event()
_bot_lock   = threading.Lock()
_bot_status = {"balance": None, "posicion": {}, "log": [], "mtf": {}, "scores": {}}
_tg_token:      str = ""   # cargado al iniciar _bot_loop
_tg_chatid:     str = ""   # cargado al iniciar _bot_loop
_bx_api_key:    str = ""   # cargado al iniciar el proceso (nivel módulo)
_bx_api_secret: str = ""   # cargado al iniciar el proceso (nivel módulo)
```

`_bot_status["mtf"]` se actualiza con cada iteración del loop (por activo).
Estructura devuelta por `_analizar_mtf()`:
```python
{
    "activo":    "BTC",
    "1W":        {"estado": "alcista|bajista|compresion", "sep": float, "mom": float},
    "1D":        {"estado": ..., "sep": float, "mom": float},
    "4H":        {"estado": ..., "sep": float, "mom": float},
    "direccion": "long|short|esperar",
    "long_ok":   bool,
    "short_ok":  bool,
}
```

---

## Config actual (mayo 2026)

```json
{
    "pct_capital": 5,
    "apalancamiento": 10,
    "trailing_activacion": 3,
    "trailing_distancia": 1.5,
    "stop_loss_pct": 5,
    "max_perdida_diaria": 10,
    "ema_compresion_pct": 1.0,
    "modo": "demo"
}
```

**Regla del 2%:** Con `pct_capital=5`, `stop_loss_pct=5` y `apalancamiento=10`, el riesgo real por trade es `5% × 5% × 10 = 2.5%` del capital total — dentro del rango profesional.

---

## Debugging — lecciones aprendidas (mayo 2026)

### Problema: cambios en UI no se reflejan en el navegador a pesar de que el servidor está corriendo código nuevo

**Síntomas observados:**
- Label `lbl-activos` mostraba texto viejo ("ACTIVOS (MÁX. 6)") aunque `TRANSLATIONS["es"]["assets"]` estaba actualizado
- Panel `panel-señales-mini` no aparecía aunque el código era correcto
- Ocurría incluso en Edge modo InPrivate

**Protocolo de diagnóstico (en orden):**

1. **Verificar que el archivo fue guardado** — usar grep o read para confirmar que el texto nuevo está en el archivo
2. **Verificar qué código está corriendo** — añadir print en el bloque `if __name__ == "__main__"`:
   ```python
   print(f"  [CHECK] Label activos ES: {TRANSLATIONS['es']['assets']}")
   ```
   Si el terminal muestra el valor viejo → el servidor está corriendo código viejo → reiniciar
   Si muestra el valor nuevo → el problema está en el navegador → limpiar caché

3. **Eliminar caché de Python** antes de reiniciar:
   ```powershell
   Remove-Item "C:\Users\Dell\Desktop\TradingBot\__pycache__" -Recurse -Force
   ```

4. **Usar flag `-B` al arrancar** para evitar bytecode cache:
   ```
   python -B main.py
   ```

5. **Abrir el servidor desde PowerShell** (yo puedo hacerlo):
   ```powershell
   Get-Process python | Stop-Process -Force
   Start-Process cmd -ArgumentList '/k', 'cd /d "C:\...\TradingBot" && python -B main.py'
   ```

6. **En el navegador** — si el CHECK confirma código nuevo pero la UI muestra texto viejo:
   - Usar `http://localhost:8051` (con http://) en InPrivate
   - Presionar F5 para recargar

### Regla permanente: `iniciar_bot.bat` usa `-B`
```bat
python -B main.py
```
No `python main.py`. El flag `-B` evita que Python use bytecode cacheado.

### Regla permanente: las tarjetas de señal requieren bot activo
El `panel-señales-mini` solo muestra tarjetas cuando:
1. Al menos 1 activo está seleccionado en el checklist
2. El bot está corriendo (INICIAR BOT presionado)
Sin ambas condiciones el panel muestra texto invisible o vacío.

---

## Pendiente (próximas sesiones)

- [ ] Bug visual: slider de capital no refleja el cambio a 5% tras reiniciar (investigar)
- [x] MTF guardarrail — IMPLEMENTADO (mayo 2026)
- [x] Panel señales mini por activo (`panel-señales-mini`) — IMPLEMENTADO (mayo 2026)
- [x] BingX data source fix — API keys pasadas correctamente, logging de fallback — IMPLEMENTADO (mayo 2026)
- [ ] Historial de trades persistente
- [ ] P&L en tiempo real de la posición abierta
- [ ] Migrar VP a TradingView Lightweight Charts (mejor interacción Y-axis)
