# AERO BOT PRO — Guía para Claude

Reglas de desarrollo para este proyecto. Seguirlas siempre, sin excepción.

---

## ⚠️ LEER PRIMERO — PROTOCOLO L99

Existe un segundo documento obligatorio: **`STRATEGY.md`**

Antes de modificar `calcular_score()` o cualquier lógica de indicadores:
1. Leer `STRATEGY.md` completo
2. Identificar el escenario afectado en la sección "Escenarios Canónicos"
3. Verificar que el cambio no rompe los otros 6 escenarios
4. Actualizar `STRATEGY.md` PRIMERO — código DESPUÉS

**Si `STRATEGY.md` y el código no coinciden → el código está mal.**
**Si Eduardo corrige al bot → primero `STRATEGY.md`, luego el código.**

---

## ⚠️ PROTOCOLO DE APRENDIZAJE CONTINUO — LEY PERMANENTE

Eduardo transfiere su conocimiento de trader en tiempo real, conforme el mercado se mueve.
Este conocimiento se acumula en `STRATEGY.md` sección "CONOCIMIENTO DE TRADING DE EDUARDO".

### Reglas que NUNCA se pueden violar:

**NUNCA BORRAR una regla de trading existente.**
Aunque una regla nueva parezca similar a una vieja, son para contextos distintos.
Las reglas coexisten — no se reemplazan, no se fusionan, no se simplifican.

**Cuando Eduardo dicta una regla nueva:**
1. Agregarla a `STRATEGY.md` → sección "CONOCIMIENTO DE TRADING" → nuevo bloque K-N
2. Incluir el contexto exacto: cuándo aplica, cuándo NO aplica
3. **Implementar en código INMEDIATAMENTE — en la misma sesión, sin esperar que Eduardo lo pida**
4. Si el código nuevo requiere un nuevo indicador en `calcular_score()` → agregarlo a la tabla
5. Marcar el bloque K-N como ✅ implementado en STRATEGY.md y HANDOFF_CLAUDE.md

**⚠️ REGLA DE ORO — NUNCA VIOLAR:**
Cuando Eduardo enseña un patrón de trading → STRATEGY.md + código en el MISMO mensaje.
No documentar sin codificar. No codificar sin documentar.
Eduardo NO debería tener que preguntar "¿ya lo pasaste a código?" — debe ser automático.

**El objetivo final:** el bot razona como Eduardo.
No ejecuta reglas mecánicas — pondera múltiples señales con los mismos pesos
que Eduardo usa en su cabeza cuando ve un gráfico.

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

### 5. Volume Profile: mínimas trazas Plotly — nunca 90
El VP tiene 90 bins. Se agrupan en **buckets de color** con separadores `None` — jamás 90 trazas individuales.

**Implementación actual (mayo 2026):** gradiente azul + POC dorado = máximo 6 trazas.
- 5 trazas: bins no-POC agrupados por intensidad de volumen (0–20%, 20–40%, 40–60%, 60–80%, 80–100%)
- 1 traza: bin POC en dorado `#FFD700`

**Posición del panel VP:**
- Panel fijo al **muro derecho**: barras terminan en `t_wall = t_max + candle_s + max_ext_s`
- Barras con **cara izquierda**: cada barra va de `t_wall - bar_width` a `t_wall` (estilo TradingView)
- Ancho máximo proporcional: `max_ext_s = candle_s * len(df) * 0.20` (20% del chart)
- Eje X fijado explícitamente: `fig.update_xaxes(range=[t_left, t_wall])` — VP pegado al eje de precios

```python
# MAL — 90 fig.add_trace() en un loop
for i, v in enumerate(vols):
    fig.add_trace(go.Scatter(...))

# BIEN — buckets de color (≤6 trazas), cara izquierda, muro derecho
def _vp_color(ratio):
    if ratio >= 0.80: return "rgba(21,  101, 192, 0.95)"   # azul oscuro intenso
    if ratio >= 0.60: return "rgba(33,  150, 243, 0.88)"   # azul fuerte
    if ratio >= 0.40: return "rgba(66,  165, 245, 0.78)"   # azul medio
    if ratio >= 0.20: return "rgba(100, 181, 246, 0.68)"   # azul cielo
    return                   "rgba(144, 202, 249, 0.55)"   # azul cielo muy claro

_vp_buckets = {}
for i, v in enumerate(vols):
    if i == poc_idx: continue
    t_start = t_wall - pd.Timedelta(seconds=max_ext_s * (v / vol_max))
    col = _vp_color(v / vol_max)
    if col not in _vp_buckets: _vp_buckets[col] = ([], [])
    _vp_buckets[col][0].extend([t_start, t_wall, None])
    _vp_buckets[col][1].extend([pmid, pmid, None])
for col, (xb, yb) in _vp_buckets.items():
    fig.add_trace(go.Scatter(x=xb, y=yb, mode="lines",
                             line=dict(color=col, width=1), ...), row=1, col=1)
# POC dorado
fig.add_trace(go.Scatter(x=[poc_tstart, t_wall], y=[poc_pmid, poc_pmid],
                         line=dict(color="#FFD700", width=3), ...), row=1, col=1)
# Fijar borde derecho del eje
fig.update_xaxes(range=[t_left, t_wall])
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

### 14. Panel de señales — `_bot_status["activos"]` usa `activos_sel` directamente
El panel de señales muestra exactamente lo que el usuario chequeó en el checklist.
`_bot_status["activos"]` = `activos_sel or []` — NO se filtra BTC, NO se usa `activos_lista`.
Si el usuario checkea BTC, aparece en el panel. Si no lo checkea, no aparece.
El bot loop sigue usando `activos_lista` (que siempre incluye BTC) para el trading — eso no cambia.

```python
# cb_bot — al iniciar el bot
activos_lista = ["BTC"] + [a for a in (activos_sel or []) if a != "BTC"]  # bot loop siempre incluye BTC
with _bot_lock:
    _bot_status["activos"] = activos_sel or []  # panel muestra exactamente lo chequeado
```

### 15. Panel de señales por activo — patrón `_senal_card()`
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
5. CIERRE EN EMA55 — Regla K-2 (solo SHORT: si precio toca EMA55 → cerrar siempre)
6. TRAILING STOP (si profit >= ts_activacion% y retroceso >= ts_distancia%)
7. CIERRE COMPRESION EMA (si abs(mtf["4H"]["sep"]) < ema_comp_pct)
8. CIERRE ZONA WAIT (si -70 < score < 70)
9. ENTRADA LONG/SHORT — filtrada por mtf["long_ok"] / mtf["short_ok"]
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

### _analizar_mtf() v3 — fetch paralelo 4 TF
Usa `ThreadPoolExecutor(max_workers=4)` para los 4 TF (1W, 1D, 4H, 2H).
Nunca en serie para no bloquear el bot loop.

**Filosofía v3 — Predictivo, no confirmatorio:**
- **4H predice**: `long_ok` / `short_ok` depende SOLO de 4H. Sin esperar alineación 1W/1D.
- **2H confirma**: Si 2H alinea con 4H → `fuerza="fuerte"`. Si no → `fuerza="débil"` + penalización 8 pts.
- **1W advierte**: Si diverge de la señal 4H → penalización 15 pts (NO bloquea).
- **1D advierte**: Si diverge de la señal 4H → penalización 10 pts (NO bloquea).
- La penalización se aplica al score ANTES de guardarlo en `_bot_status["scores"]`.

**Advertencias visibles en UI:**
- Banner `mtf-advertencia` muestra los avisos activos (amarillo, oculto si no hay).
- Display `mtf-direccion` muestra fuerza: 💪 FUERTE o ⚡ DÉBIL + penalización total.

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
Estructura devuelta por `_analizar_mtf()` v3:
```python
{
    "activo":      "BTC",
    "1W":          {"estado": "alcista|bajista|compresion", "sep": float, "mom": float},
    "1D":          {"estado": ..., "sep": float, "mom": float},
    "4H":          {"estado": ..., "sep": float, "mom": float},  # PREDICE
    "2H":          {"estado": ..., "sep": float, "mom": float},  # CONFIRMA
    "direccion":   "long|short|esperar",
    "long_ok":     bool,     # True si 4H alcista — sin depender de 1W/1D
    "short_ok":    bool,     # True si 4H bajista — sin depender de 1W/1D
    "fuerza":      "fuerte|débil|–",  # fuerte si 2H confirma 4H
    "advertencia": str,      # ej. "⚠ 1W bajista | 2H sin confirmar"
    "penalizacion": int,     # pts a restar del abs(score): max 33 (15+10+8)
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

## Reglas de diseño UI — permanentes

### UI-1. Texto de menús y controles SIEMPRE en blanco
Cualquier label, mark, opción o texto de control en el panel lateral
(sliders, checkboxes, dropdowns, marks de sliders) debe usar `color: "#ffffff"`.

```python
# MAL — color oscuro invisible sobre fondo negro
marks={1: "1%", 5: "5%"}

# BIEN — blanco siempre
marks={
    1: {"label": "1%",  "style": {"color": "#ffffff"}},
    5: {"label": "5%",  "style": {"color": "#ffffff"}},
}
```

Razón: el fondo del panel es negro. Colores oscuros o por defecto de Dash
se mezclan con el fondo y no se leen. El blanco es neutro, limpio y elegante.
No usar dorado ni otros colores para texto de controles — reservar el dorado
para títulos de sección y valores numéricos destacados.

---

## Reglas de operación — esta máquina específica

### 15. Python en esta máquina se llama `python3.11`
El proceso Python en Windows con Microsoft Store Python se llama `python3.11`, NO `python`.
Usar SIEMPRE los comandos correctos:

```powershell
# Matar servidor (CORRECTO)
Get-Process python3.11 -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false

# Iniciar servidor (CORRECTO)
Start-Process cmd -ArgumentList "/k cd /d C:\Users\Dell\Desktop\TradingBot && python3.11 -B main.py"

# Verificar que está corriendo (CORRECTO)
Get-Process python3.11 -ErrorAction SilentlyContinue
```

Si usas `Get-Process python` no encontrará nada — proceso equivocado.
Si no matas correctamente, se acumulan servidores zombie que bloquean el puerto 8051.

### 16. config.json — nunca agregar líneas fuera del objeto JSON
El archivo termina con `}`. Nada va después de esa llave.
Si se necesita guardar una API key externa (Kimi, OpenAI, etc.), crear un archivo separado como `keys_externas.json`.

### 17. Emojis en `print()` — PROHIBIDO en Windows (cp1252)
**Síntoma:** El bot loop arranca y muere silenciosamente en el primer `print()` que contiene un emoji.
El thread lanza `UnicodeEncodeError: 'charmap' codec can't encode character` y desaparece sin dejar rastro visible en el dashboard — el panel simplemente dice "Bot detenido" para siempre.

**Causa:** Windows usa cp1252 por defecto en la consola. La mayoría de emojis (🪜📈📉❄️🛡️ etc.) no existen en ese encoding.

**Solución ya aplicada** en la línea 1 del archivo (antes de cualquier import):
```python
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

**Regla permanente:** Estas líneas deben ser siempre las primeras del archivo. No moverlas, no eliminarlas.
Si en el futuro un AI agrega un `print()` con emoji y el bot loop deja de arrancar — esta es la causa. La solución ya está en el archivo, solo hay que verificar que esas líneas siguen al inicio.

---

### 18. LED 3 estados — patrón de control dual con allow_duplicate
El LED tiene 3 estados: `desconectado` (rojo), `conectando` (amarillo parpadeo), `conectado` (verde fijo).

- `cb_bot` pone `"led-dot conectando"` al iniciar el thread — feedback inmediato al click.
- `cb_bot_status` (tick cada 5s) es el **único que transiciona a `"led-dot"` (conectado)**. Usa `Output("led-dot", "className", allow_duplicate=True)` — Dash 4.x lo soporta.
- La lógica en `cb_bot_status`:
  - `_bot_thread` muerto → `"led-dot desconectado"`
  - bot vivo pero `scores` vacío → `"led-dot conectando"`
  - bot vivo y `scores` con datos → `"led-dot"` (verde fijo)
- El color del **texto** LED cambia via CSS sibling selector (`~`), sin output extra:
  ```css
  .led-dot.desconectado ~ .led-texto { color: var(--rojo-led); }
  .led-dot.conectando   ~ .led-texto { color: var(--dorado-vivo); }
  /* base .led-texto ya tiene color: var(--verde-led) */
  ```

### 19. btn-historial — siempre en app.layout (estático), nunca en layout dinámico
`btn-historial` debe vivir en `app.layout`, no en `_pagina_principal()`.
Con Dash 4.x, cuando un componente entra al DOM via callback (layout dinámico), dispara los callbacks que lo tienen como `Input` aunque `prevent_initial_call=True` esté activado.
Fix aplicado: `btn-historial` en `app.layout` con `position: fixed; bottom: 20px; right: 20px` (botón flotante).

### 20. Componentes usados como State en callbacks multi-página — SIEMPRE en app.layout
**Síntoma:** Un callback que funciona en la página principal no funciona en la página de detalle (pestaña nueva). La página se queda en blanco o el callback nunca se dispara.

**Causa:** El callback tiene un `State("componente-x", "value")` pero `componente-x` solo existe en `_pagina_principal()` (layout dinámico). Cuando se abre la página de detalle en una pestaña nueva, `_pagina_principal()` nunca se renderiza → el componente no existe en el DOM → Dash no puede leer su State → el callback falla silenciosamente.

**Regla:** Todo componente referenciado como `State` o `Input` por un callback que puede correr en CUALQUIER página (no solo la principal) DEBE vivir en `app.layout` (estático).

**Patrón aplicado a `toggle-elliott` (mayo 2026):**
```
PROBLEMA: toggle-elliott en _pagina_principal() → cb_detail falla en pestaña nueva

SOLUCIÓN en 3 pasos:
1. app.layout    → toggle-elliott  (id real, display:none — siempre en DOM)
2. _pagina_principal() → toggle-elliott-ui (id visual, el checkbox que ve el usuario)
3. Nuevo callback _sync_elliott():  toggle-elliott-ui → toggle-elliott (copia el valor)
```

```python
# app.layout — componente real, siempre presente, invisible
dcc.Checklist(id="toggle-elliott", options=[...], value=[], style={"display": "none"}),

# _pagina_principal() — UI visible, ID diferente
dcc.Checklist(id="toggle-elliott-ui", options=[...], value=[], ...),

# Callback de sincronización
@app.callback(Output("toggle-elliott", "value"), Input("toggle-elliott-ui", "value"),
              prevent_initial_call=True)
def _sync_elliott(val): return val or []
```

**Verificar SIEMPRE antes de agregar un State a un callback multi-página:**
¿Ese componente está en `app.layout`? Si no → moverlo o aplicar el patrón UI/real + sync.

### 21. calcular_score() v3.2 — filosofía anticipatoria
El bot predice el futuro, no describe el presente. Reglas de diseño del scoring:

**Pesos v3.2 (mayo 2026) — tabla completa:**

| Condición | Puntos | Descripción |
|---|---|---|
| `bear_peak` | −40 | Máximo local de squeeze → giro bajista exacto |
| `bull_valley` | +40 | Mínimo local de squeeze → giro alcista exacto |
| `bear_post_peak` | −25 | Post-pico: 3 barras declinando, aún positivo |
| `bull_post_valley` | +25 | Post-fondo: 3 barras subiendo, aún negativo |
| `bear_accel` | −30 | Squeeze < 0 y acelerando negativo |
| `bull_accel` | +30 | Squeeze > 0 y acelerando positivo |
| Positivo creciendo | +10 | Squeeze > 0 y subiendo |
| **Positivo cayendo** | **−10** | Squeeze > 0 pero perdiendo fuerza = bajista |
| Negativo subiendo | +10 | Squeeze < 0 pero recuperándose = posible giro |
| Negativo cayendo | −10 | Squeeze < 0 y siguiendo abajo |
| `bull_ema_strong` (slope acelerando) | +30 | EMA10 slope acelerando al alza |
| `bear_ema_strong` (slope acelerando) | −30 | EMA10 slope acelerando a la baja |
| EMA slope débil | ±8 | EMA reactiva — no debe dominar |
| S/R resistencia cerca (±1.5%) | −20 | Precio rechazado en resistencia |
| S/R soporte cerca (±1.5%) | +20 | Precio apoyado en soporte |
| Cross-confirm (peak + S/R) | ±18 | Squeeze gira EN un nivel clave = bonus |
| Volume Profile POC | ±10 | Por encima/debajo del POC |
| ADX emergente (<20 → creciendo) | ±10 | Amplifica dirección dominante |
| ADX fuerte (≥25, creciendo) | ±5 | Amplifica dirección dominante |
| ADX < 20 (sin fuerza) | −5 | Penaliza — tendencia débil |

**Regla crítica — ADX es FUERZA, no DIRECCIÓN:**
```python
if pts >= 0: pts += adx_bonus   # amplifica bullish
else:        pts -= adx_bonus   # amplifica bearish
```
Nunca `pts += adx_bonus` incondicionalmente — eso anula señales SHORT.

**Regla crítica — Positivo-cayendo NO es alcista:**
```python
# v3.1 BUG: elif mom_now > 0: pts += 10  ← daba +10 aunque el squeeze bajara
# v3.2 FIX:
elif mom_now > 0 and growing: pts += 10   # creciendo = alcista
elif mom_now > 0:             pts -= 10   # cayendo = bajista (pierde fuerza)
```

**Ejemplos validados:**
- BTC 4H squeeze en techo + resistencia = **score −70 → SHORT** (v3.1)
  `+8 (EMA) −40 (bear_peak) +10 (POC) −20 (S/R) −18 (cross) −10 (ADX) = −70`
- BTC 4H post-pico (1-2 barras después) + resistencia = **score ~−42 → SHORT** (v3.2)
  `+8 (EMA) −25 (post_peak) +10 (POC) −20 (S/R) −5 (ADX) = −32`

### 22. Filosofía de S/R — niveles testeados múltiples veces + breakout (Eduardo Andrade, mayo 2026)

**Reglas dictadas por Eduardo — aprendizaje de mercado real:**

**Soporte testeado múltiples veces:**
Cuando un nivel de soporte ha sido tocado 2 o más veces y el precio lo respeta, ese nivel es más significativo que un soporte recién formado. La significancia se acumula con cada toque.

**Breakout de soporte = SHORT reforzado:**
Si el soporte testeado múltiples veces es ROTO hacia abajo (precio cierra por debajo), la caída siguiente tiende a ser más fuerte y sostenida. Esto es más bajista que simplemente "estar cerca de la resistencia."
→ Implementar: `support_break` en `calcular_score()` = bonus SHORT adicional cuando precio < soporte cercano

**Techo roto = oportunidad LONG:**
Si el precio rompe con fuerza un techo de resistencia que había bloqueado el avance, abre un pequeño camino alcista. El bot debe reconocer esto y NO seguir en SHORT.
→ Implementar: `resistance_break` = bonus LONG cuando precio > resistencia cercana (breakout)

**Objetivo de salida de una posición SHORT:**
La posición ideal dura hasta que el squeeze momentum desarrolle un **valle rojo bien desarrollado** (momentum muy negativo, barras rojas creciendo en tamaño = el impulso bajista alcanza su máximo). Sin embargo, el **trailing stop** es el mecanismo de ejecución — se activa antes si hay ganancia considerable.
- No esperar el valle perfecto: el trailing stop captura la ganancia cuando el precio rebota desde el fondo
- La señal visual del valle es para CONFIRMAR que la tesis bajista estuvo correcta, no para cronometrar la salida

**Tabla de eventos S/R v3.3 (a implementar):**
```
Precio cerca de resistencia (≤1.5%)     → -20 pts  (rechazo probable)
Precio cerca de soporte (≤1.5%)         → +20 pts  (rebote probable)
Precio ROMPE soporte (1.5%–4% debajo)   → -25 pts  (breakout bajista)
Precio ROMPE resistencia (1.5%–4% encima) → +25 pts (breakout alcista)
Bonus: nivel testeado 3+ veces          → ±8 pts adicionales (TODO: contar toques)
```

### 20. P&L en tiempo real — patrón de cálculo en bot loop
El P&L se calcula DESPUÉS del bloque de `precio_extremo` y ANTES del Stop Loss, por activo:
```python
if pos_actual and precio_entrada[activo]:
    ep_live = precio_entrada[activo]
    pnl_pct_live = (precio - ep_live) / ep_live * 100 * apalancamiento_actual  # long
    # (ep_live - precio) / ep_live * 100 * apalancamiento_actual  # short
    with _bot_lock:
        _bot_status["pnl"][activo] = {"pct": ..., "usd": ..., "side": ..., "entrada": ..., "precio": ...}
else:
    with _bot_lock:
        _bot_status["pnl"].pop(activo, None)  # limpiar al cerrar posición
```
`_bot_status["pnl"]` es un dict `{activo: {...}}`. El elemento UI es `id="pnl-posicion"`, output #18 de `cb_bot_status`.

---

## Historial completo — todo lo implementado hasta hoy

### Mayo 2026 — Fundamentos
- [x] calcular_score() v3.0 — score anticipatorio, MTF guardarrail v3
- [x] calcular_score() v3.1 — bear_peak ±40, ADX direction-aware, S/R cross-confirm ±18
- [x] calcular_score() v3.2 — bear_post_peak/bull_post_valley ±25, positivo-cayendo = −10
- [x] calcular_score() v3.3 — S/R breakout: soporte roto −25, resistencia rota +25
- [x] _analizar_mtf() v3 — 4H predice, 2H confirma, 1W/1D penalizan (fetch paralelo)
- [x] BingX data source — API keys a nivel módulo, logging explícito de fallback a Binance
- [x] Panel señales mini por activo — barra de progreso hacia umbral ±70
- [x] Historial de trades — modal con tabla completa y pills de resumen
- [x] LED 3 estados — DESCONECTADO/CONECTANDO/CONECTADO con CSS sibling selector
- [x] P&L en tiempo real — cálculo en bot loop, sección "Posición Abierta"
- [x] STRATEGY.md — creado como fuente de verdad L99 con 7 escenarios canónicos

### Mayo 2026 — Fixes
- [x] Fix lbl-idioma — id faltante, etiqueta no traducía
- [x] Fix S/R order=5 — sincronizado entre chart y score
- [x] Fix _analizar_mtf excepción silenciosa — ahora loggea
- [x] Fix cb_detail hardcoded Spanish — usa State(store-idioma)
- [x] Fix LED CONECTADO falso — store-bot como fuente de verdad
- [x] Fix slider capital — config.json malformado
- [x] Fix btn-historial — movido a app.layout estático

### Mayo 2026 — Sesión 26 mayo (conocimiento de trading Eduardo)
- [x] Trendlines diagonales — reemplazan horizontales en chart, usan todos los pivots del período
- [x] _detectar_sr_persistentes() — función compartida chart+score, order=15, tolerancia 1.5%
- [x] _detectar_trendlines() — regresión lineal por TODOS los pivots, proyección al borde derecho
- [x] _SR_LOOKBACK — velas según timeframe (4H=280, 1D=160, 1W=55) en todos los fetch
- [x] STRATEGY.md v5.0 — reglas de visualización actualizadas a trendlines diagonales
- [x] Cierre SHORT en EMA55 — Regla K-2: si precio toca EMA55 → cerrar siempre (bot loop paso 5)
- [x] STRATEGY.md — Bloques K-1 a K-7 (conocimiento de trading completo de Eduardo)
- [x] Protocolo de Aprendizaje Continuo — CLAUDE.md y STRATEGY.md, nunca borrar reglas
- [x] Slider capital marks en blanco — regla UI-1: menús siempre en color blanco
- [x] Barra de score ELIMINADA — cambiaba cada 5s, confundía, no aportaba valor visual
- [x] cb_btc_dashboard y cb_detail — Output("scoring-bar") y Output("d-scoring-bar") eliminados
- [x] _scoring_bar() y _scoring_bar_children() — funciones eliminadas del código

### Mayo 2026 — Sesión 27 mayo (conocimiento de trading Eduardo)
- [x] K-8: Último estirón — precio toca resistencia en tendencia bajista → −20 pts bonus SHORT
      Forma más fuerte: squeeze ya negativo cuando precio toca resistencia (máxima convicción)
      Implementado en calcular_score() v3.4 — guardarrail S/R muestra prefijo "K8"
- [x] K-9: Segunda confirmación — EMA cruce bajista (EMA10<EMA55) + squeeze negativo → −15 pts
      "Ya vamos con más cuidado" (Eduardo). Mutuamente exclusivo con K-8.
      Implementado en calcular_score() v3.4
- [x] K-10: Volumen de acumulación en soporte — longs posicionándose + nodo VP en precio actual
      El volumen revela INTENCIÓN. Acumulación en soporte pesa más que squeeze bajista de TF altos.
      Documentado en STRATEGY.md. Pendiente de implementar en código.
- [x] STRATEGY.md reestructurado — 7 partes ordenadas por tema (indicadores, TF, entradas, gestión)
- [x] Regla de oro: conocimiento de trading = STRATEGY.md + código en el MISMO momento

### Pendiente de implementar (documentado en STRATEGY.md, falta código)
- [ ] K-4: Cruce de EMAs como señal en calcular_score() — cruce reciente = bonus ±pts
- [ ] K-5: Ruptura de fractal como confirmación de fuerza — último pivote roto
- [ ] K-6: Trendline inferior como objetivo de salida — cerrar SHORT al tocar soporte trendline
- [ ] K-2.3: Re-entrada SHORT después del rebote de EMA55
- [ ] K-7: Alta convicción 4H+2H (cruce EMA + fractal) como bonus de score

### Mayo 2026 — Sesión 27 mayo (fixes de UI)
- [x] Anti-parpadeo de gráficos — 3 capas: uirevision + delay_show=2000 + CSS opacity
- [x] STRATEGY.md reestructurado en 7 partes con índice navegable

### Mayo 2026 — Sesión 30 mayo (Volume Profile rediseño completo)
- [x] VP cara izquierda — barras se extienden hacia la izquierda desde `t_wall` (era hacia la derecha)
- [x] VP muro derecho — panel fijo en `t_max + candle_s + max_ext_s`, separado de las velas
- [x] VP ancho proporcional — `max_ext_s = candle_s * len(df) * 0.20` (20% del chart, restaura tamaño)
- [x] VP eje X fijado — `fig.update_xaxes(range=[t_left, t_wall])` pega el panel al eje de precios
- [x] VP gradiente azul — 5 buckets de color por intensidad de volumen + POC dorado (6 trazas total)
      Alto volumen (80–100%) = `rgba(21,101,192)` azul oscuro intenso
      Bajo volumen  (0–20%)  = `rgba(144,202,249)` azul cielo muy claro
- [x] Fix VER DETALLE (pestaña nueva en blanco) — regla #20: toggle-elliott movido a app.layout
      toggle-elliott (real, display:none) en app.layout + toggle-elliott-ui (visual) en sidebar
      _sync_elliott() callback sincroniza UI → real. cb_detail y cb_btc_dashboard leen del real.

### Backlog técnico
- [ ] Fix selector de idioma — reportado 30 mayo 2026, diferido para fase final del bot
- [ ] Refactor modular — separar en ui.py, indicators.py, exchange/ (main.py ~3000 líneas)
- [ ] Migrar VP a TradingView Lightweight Charts

---

## Errores de diseño UI — no repetir

### UI-ERR-1: Barra de score que cambia cada 5 segundos
**Qué pasó:** Se implementó una barra horizontal (SHORT ◄────► LONG) que mostraba
el score numérico y la etiqueta (CORTO/ESPERAR/LARGO). El score se recalcula cada
5 segundos con datos de mercado, por lo que la barra cambiaba de valor y color
constantemente — confundía al usuario y no aportaba información útil.

**Lección:** Un elemento visual que cambia cada 5 segundos no comunica nada.
O se estabiliza (promedio de N períodos) o se elimina.

**Decisión de Eduardo (26 mayo 2026):** ELIMINAR la barra. No reemplazar.
Los guardarrailes (SQUEEZE, ADX, EMA, S/R) ya comunican la misma información
de forma estable y por indicador separado.

```
❌ NUNCA volver a agregar una barra de score global que se actualice con el tick
✓ Si se quiere mostrar el score → mostrarlo en el panel de señales mini (ya existe)
   donde el contexto por activo lo hace más útil
```

### UI-ERR-2: Texto superpuesto en la barra central
**Qué pasó:** Se puso el número y la etiqueta como overlay encima de la barra.
Con score "-50" y etiqueta "ESPERAR", el texto se pisaba visualmente.

**Lección:** Nunca superponer texto sobre una barra de progreso.
Número a la izquierda, barra en el centro, etiqueta a la derecha — cada uno en su espacio.

### UI-ERR-3: Ensalada de colores
**Qué pasó (preventivo):** Al añadir color dorado al slider, Eduardo señaló que
mezclar muchos colores distintos no se ve elegante.

**Regla:** Paleta de colores controlada:
```
Texto de controles/menús  → blanco  #ffffff
Títulos de sección        → dorado  #c8a84b
Valores numéricos clave   → dorado  #c8a84b o color de estado (verde/rojo)
Señal LONG                → verde   #00ff88
Señal SHORT               → rojo    #ff3355
Neutral/Esperar           → gris    #a0a8c0
Fondo panels              → negro   #0a0a0f / #0d0d1a
```
No inventar colores nuevos. Usar solo los de esta paleta.

### Backlog técnico
- [ ] Refactor modular — separar en ui.py, indicators.py, exchange/ (main.py ~3000 líneas)
- [ ] Migrar VP a TradingView Lightweight Charts
