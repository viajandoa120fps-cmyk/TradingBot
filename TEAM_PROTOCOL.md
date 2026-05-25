# AERO BOT PRO — Protocolo de Equipo: Claude + Kimi + Eduardo

---

## La visión — por qué existimos

Estamos construyendo un **trading bot profesional de alta calidad** que se va a distribuir como producto. No es un proyecto de garage. Es un sistema que traders reales van a usar con capital real.

La filosofía es simple: **las cosas que realmente valen la pena se construyen con trabajo, criterio y colaboración entre inteligencias distintas.** Eduardo aporta la visión de negocio y la experiencia de mercado. Claude aporta arquitectura y análisis crítico. Kimi aporta velocidad de procesamiento y contexto extenso. Los tres juntos construyen algo que ninguno construiría solo.

---

## Quiénes somos

| Participante | Rol | Fortaleza principal |
|---|---|---|
| **Eduardo** | Dueño del producto y árbitro final | Visión de negocio, experiencia de mercado, decisiones estratégicas |
| **Claude** | Arquitecto y socio de trading | Diseño de sistemas, análisis crítico, calidad de código, decisiones técnicas |
| **Kimi** | Ingeniero de ejecución | Contexto largo, archivos grandes, debugging exhaustivo, velocidad de implementación |

**Regla fundamental:** Ningún AI le da la razón a Eduardo automáticamente. Si el análisis del usuario es incorrecto o riesgoso, se dice directamente y se explica por qué. Somos socios, no asistentes complacientes.

---

## Cómo colaboramos — el modelo de turnos

Ningún AI está conectado directamente al otro. El código, GitHub y este archivo son el canal de comunicación entre todos. El flujo es:

```
Eduardo define qué se trabaja en este turno
        ↓
AI activo lee CLAUDE.md + TEAM_PROTOCOL.md (HANDOFF)
        ↓
AI activo trabaja: resuelve bugs + avanza en roadmap + propone mejoras
        ↓
Al terminar: actualiza HANDOFF + sube a GitHub
        ↓
Eduardo lleva el trabajo al otro AI
        ↓
El otro AI lee el HANDOFF + da su punto de vista + continúa
```

**Cada turno tiene dos responsabilidades:**
1. **Resolver** — El bug o tarea del momento
2. **Construir** — Avanzar en el roadmap a largo plazo y proponer mejoras al producto

---

## Reglas del equipo — no negociables

1. **Leer antes de tocar** — Siempre leer `CLAUDE.md` y el HANDOFF antes de escribir código
2. **GitHub es la única verdad** — Todo cambio se sube a GitHub al terminar. Nunca pasar código por chat
3. **No romper lo que funciona** — Si algo está marcado ✅ no se toca sin razón explícita
4. **Dos perspectivas valen más que una** — Cuando Claude y Kimi tienen enfoques distintos, ambos los exponen con datos. Eduardo decide
5. **Handoff completo siempre** — El AI que termina deja el HANDOFF actualizado antes de cerrar sesión
6. **Roadmap siempre visible** — Cada turno avanza al menos un paso del roadmap, no solo apaga incendios

---

## Ubicación del proyecto

| Recurso | Ruta |
|---|---|
| Carpeta local | `C:\Users\Dell\Desktop\TradingBot\` |
| Repositorio GitHub | `https://github.com/viajandoa120fps-cmyk/TradingBot.git` |
| Archivo principal | `main.py` (puerto 8051, Python Dash) |
| Guía de arquitectura y reglas | `CLAUDE.md` — leer primero, siempre |
| Protocolo de equipo | `TEAM_PROTOCOL.md` (este archivo) |
| Lanzador | `iniciar_bot.bat` → doble clic → `http://localhost:8051` |

---

## Stack técnico

- **Python 3** + **Dash (Plotly)** — Dashboard web puerto 8051
- **ccxt** — Conexión a exchanges (BingX perpetual, Binance spot fallback)
- **Pandas / NumPy / SciPy** — Indicadores técnicos
- **Threading** — Bot loop en background daemon
- **Telegram Bot API** — Notificaciones de operaciones en tiempo real

---

## Visión del producto — hacia dónde vamos

### Arquitectura objetivo (modular por capas)

```
CAPA 1 — Control (UI/Dashboard)
  └── Panel de activos por exchange (Cripto BingX, Forex, Commodities)
  └── Parámetros del trader (capital, SL, trailing, etc.)
  └── Panel de señales en vivo por activo
  └── Log de actividad y balance

CAPA 2 — Indicadores
  └── EMA, Squeeze Momentum, ADX, Volume Profile, S/R
  └── MTF Guardarrail (1W → 1D → 4H)

CAPA 3 — Gráficos
  └── Interactivos, multi-activo, multi-exchange

CAPA 4 — Exchanges (conectores modulares)
  └── BingX (perpetual, crypto) — ACTIVO
  └── Binance (spot, fallback) — ACTIVO
  └── Forex broker (futuro)
  └── Commodities broker (futuro)
```

### Modelo de distribución
El producto se distribuye como **aplicación descargable** — cada trader lo instala localmente, configura sus propias API keys y opera su propio capital. No es SaaS. Las API keys nunca salen de la máquina del usuario.

---

## Estado actual del proyecto

### ✅ Funcionando sólidamente
- Bot loop: señales LONG/SHORT (score ±70), Stop Loss fijo, Trailing Stop, Max Pérdida Diaria
- Indicadores: EMA 10/55, Squeeze Momentum LazyBear (exacto vs TradingView), ADX, Volume Profile 90 bins, S/R
- MTF Guardarrail cascade 1W → 1D → 4H con cierre por compresión EMA
- Notificaciones Telegram: entrada, salida, stop loss, trailing, max pérdida
- Conexión BingX con API keys correctas + fallback Binance con logging explícito
- Mini gráficos por activo seleccionado
- Balance BingX en tiempo real, log de actividad

### 🔴 Bug activo — PRIORIDAD INMEDIATA
**`panel-senales-mini` no se renderiza en browser (Edge)**

El panel existe en código, el bot calcula scores (log muestra `LINK: ▼ SHORT score=-70`), pero las tarjetas de señal no aparecen visualmente.

Código relevante en `main.py`:
```python
# En _pagina_principal() — el div contenedor
html.Div(id="panel-senales-mini", style={"marginTop": "8px"})

# Helper que genera cada tarjeta
def _senal_card(ticker, score): ...

# En cb_bot_status() — el output
Output("panel-senales-mini", "children")

# En bot loop — donde se guardan los scores
_bot_status["scores"][activo] = score

# En cb_bot() — donde se guardan los activos al iniciar
_bot_status["activos"] = [a for a in activos_lista if a != "BTC"]
```

Lo ya intentado: caché Python eliminado, InPrivate Edge, IDs renombrados a ASCII, lectura de activos desde `_bot_status` en vez de State del checklist, colores más visibles.

**Hipótesis de Claude:** Race condition entre `render_page` callback (que genera `_pagina_principal()` en `page-content`) y `cb_bot_status` (que actualiza `panel-senales-mini` dentro de ese layout dinámico). Edge puede estar procesando los updates en orden incorrecto.

**Solución sugerida por Claude para el próximo turno:** Mover `panel-senales-mini` del layout dinámico (`_pagina_principal()`) al layout estático (`app.layout`) directamente, para que Dash siempre sepa dónde está y no dependa del routing de páginas.

### ⚠️ Bugs secundarios (mismo patrón de rendering)
- `Sin Stop Fijo OK` en vez de `Stop Loss −5.0%`
- Slider capital muestra 20% aunque config tiene `pct_capital: 5`
- Label activos no refleja cambios de `TRANSLATIONS["es"]["assets"]`

### 📋 Roadmap completo — en orden de prioridad

| # | Feature | Estado |
|---|---|---|
| 1 | Panel señales por activo (`panel-senales-mini`) | 🔴 Bug rendering |
| 2 | Historial de trades persistente | ⏳ Pendiente |
| 3 | P&L en tiempo real de posición abierta | ⏳ Pendiente |
| 4 | Refactorizar en módulos (`ui.py`, `indicators.py`, `exchange/`) | ⏳ Pendiente |
| 5 | Setup wizard para nuevos usuarios | ⏳ Pendiente |
| 6 | Segundo exchange conector (Binance completo) | ⏳ Pendiente |
| 7 | Top 20 CoinMarketCap dinámico (API call) | ⏳ Pendiente |
| 8 | Backtesting con datos históricos | ⏳ Pendiente |
| 9 | Métricas de performance (Sharpe, drawdown, win rate) | ⏳ Pendiente |
| 10 | Forex / Commodities (exchanges distintos) | 🔮 Largo plazo |

---

## HANDOFF — Plantilla de traspaso entre AIs

El AI que termina su turno llena esta sección antes de cerrar:

---

### 🔄 ÚLTIMO HANDOFF

**Fecha:** 25 mayo 2026 (turno 3 — mismo día)
**AI que trabajó:** Claude (Anthropic)
**Commit GitHub:** `0552501`

**Qué se resolvió en este turno:**

1. **BTC no aparecía en panel de señales aunque estaba seleccionado — RESUELTO ✅**
   - Causa: `_bot_status["activos"]` excluía BTC siempre (`if a != "BTC"`)
   - Fix: cambiar a `activos_sel or []` — el panel refleja exactamente lo que el usuario chequeó
   - Resultado: BTC aparece con su tarjeta LONG/SHORT/NEUTRAL si está seleccionado ✅
   - El bot loop sigue usando `activos_lista` (BTC siempre incluido) — solo cambia el panel visual

2. **Bug raíz del `panel-senales-mini` — RESUELTO ✅** (turno anterior)
   - Causa real: la variable `senales` se computaba en `cb_bot_status` pero nunca se incluía en el `return`. Era una línea faltante, no un problema de arquitectura.
   - Fix: `panel-senales-mini` reintegrado como output #12 de `cb_bot_status` (que ya actualizaba correctamente 11 componentes). Eliminado el `cb_panel_senales` separado que tenía `prevent_initial_call=True` y quedaba suprimido en Edge.
   - Resultado: tarjetas de señal visibles con barra de progreso y label LONG/SHORT/NEUTRAL ✅

2. **`config.json` malformado — RESUELTO ✅**
   - Causa: `kimi_api_key` fue appended fuera del objeto JSON (después del `}`), rompiendo el parse completo.
   - Consecuencias: `_pagina_principal()` fallaba silenciosamente → "Sin Stop Fijo OK", label "ACTIVOS (MÁX. 6)", capital "20%", todo corrompido.
   - Fix: archivo corregido a JSON válido, línea espuria removida.

3. **13 procesos zombie `python3.11` — RESUELTO ✅**
   - Causa: Python en esta máquina corre como `python3.11` (Microsoft Store), no como `python`. Todos los intentos de `Get-Process python | Stop-Process` no mataban nada. Los 13 servidores acumulados bloqueaban el puerto 8051, el primero (con código viejo) siempre ganaba.
   - Fix: usar `Get-Process python3.11 | Stop-Process` en esta máquina.
   - **REGLA PERMANENTE para esta máquina:** el proceso Python se llama `python3.11`, no `python`.

**Qué avanzó en el roadmap:**
- Item #1 (panel señales): **✅ COMPLETO** — tarjetas visibles, barra de progreso, LONG/SHORT/NEUTRAL por activo, BTC incluido si está seleccionado

**Estado al cerrar:**
- Panel señales funcionando con BTC incluido: BTC 🔴 SHORT 57%, SOL ⚪ NEUTRAL, BCH 🔴 SHORT 79% — confirmado por Eduardo
- Capital "5%" correcto, Stop Loss "−5.0%" correcto, label "CRIPTO BINGX (MAX. 6)" correcto
- GitHub sincronizado, commit `0552501`
- Servidor limpio: UN solo proceso `python3.11`

**Para el próximo AI — tarea inmediata:**
Avanzar en el item #2 del roadmap: **historial de trades persistente**.
- El archivo `trades_history.json` ya existe y tiene la estructura básica (ver `_registrar_trade()` en main.py)
- Falta: panel en el dashboard que muestre los últimos trades con P&L, tipo (LONG/SHORT), activo, precio entrada/salida
- Proponer: ¿tab separado? ¿sección en el panel derecho? ¿modal?

**Para el próximo AI — comando correcto para matar el servidor en esta máquina:**
```powershell
Get-Process python3.11 -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false
```

**Punto de vista de Claude para Kimi:**
El sistema está estable ahora. Los bugs que quedaban eran todos consecuencia de dos problemas raíz: config.json roto (que corrompía silenciosamente toda la UI) y el error de nombre de proceso. Con eso resuelto, la arquitectura de callbacks de Dash está funcionando correctamente para el layout dinámico. No hay que mover nada al layout estático — era la hipótesis equivocada. El problema era operacional, no arquitectónico.

**Punto de vista de Claude para Kimi:**
El problema recurrente de rendering en Edge (3 elementos distintos con el mismo síntoma) apunta a que Dash tiene un comportamiento inconsistente con layouts dinámicos en Edge. No es un bug de lógica Python — es un problema de cómo Dash/React sincroniza el DOM en este browser. La solución arquitectónica limpia es sacar los elementos críticos del layout dinámico y ponerlos en el estático.

---

## Cómo comienza el turno de cada AI

```
PASO 1 — Contexto
  └── Leer CLAUDE.md completo
  └── Leer TEAM_PROTOCOL.md (este archivo, especialmente el HANDOFF)
  └── git pull origin main

PASO 2 — Diagnóstico
  └── Revisar el estado actual del bug o tarea asignada
  └── Dar tu punto de vista honesto: ¿estás de acuerdo con la hipótesis del AI anterior?
  └── Si tienes una perspectiva distinta, exponla con razones concretas

PASO 3 — Ejecución
  └── Implementar solución
  └── Verificar que funciona
  └── Confirmar con Eduardo antes de cerrar

PASO 4 — Avance en roadmap
  └── Además del bug, avanzar al menos un paso del roadmap
  └── O proponer con fundamento qué sigue y por qué

PASO 5 — Cierre
  └── Actualizar HANDOFF en este archivo
  └── git add . && git commit -m "descripción clara" && git push origin main
  └── Informar a Eduardo: "Turno terminado. Repo actualizado. Commit: [hash]. Próximo paso: [qué sigue]."
```

---

## Prompt listo para iniciar sesión con cualquier AI

Copia y pega esto al inicio de cada sesión:

> *"Eres parte de un equipo de tres: tú (AI), Claude (Anthropic) y yo, Eduardo. Estamos construyendo AERO BOT PRO, un trading bot profesional en Python Dash. Este es un proyecto serio — no de garage — que se va a distribuir a traders reales.*
>
> *Antes de hacer cualquier cosa, lee estos dos archivos del repositorio:*
> *1. `CLAUDE.md` — arquitectura, reglas críticas, bugs conocidos*
> *2. `TEAM_PROTOCOL.md` — cómo trabajamos en equipo y el último HANDOFF*
>
> *Repositorio: https://github.com/viajandoa120fps-cmyk/TradingBot.git*
> *Carpeta local: `C:\Users\Dell\Desktop\TradingBot\`*
>
> *Una vez que hayas leído ambos archivos:*
> *1. Dime qué entendiste del estado actual del proyecto*
> *2. Da tu punto de vista sobre el bug activo y cómo lo resolverías*
> *3. Propón también cómo avanzarías en el roadmap a largo plazo*
>
> *Actúa como un desarrollador senior con criterio propio. No me des la razón automáticamente. Si algo está mal o hay una mejor forma de hacerlo, dímelo directamente."*

---

*Última actualización: Claude — 25 mayo 2026*
