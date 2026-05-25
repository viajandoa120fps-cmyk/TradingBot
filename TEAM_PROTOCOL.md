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

**Fecha:** 25 mayo 2026 (turno 4 — mismo día)
**AI que trabajó:** Claude (Anthropic)
**Commit GitHub:** `74915f9`

**Qué se resolvió en este turno:**

1. **AERO BOT PRO v3.0 — Rediseño predictivo — IMPLEMENTADO ✅**

   **`calcular_score()` v3 — Anticipatorio:**
   - EMA: mide slope (pendiente %) en las últimas 3 velas + aceleración (slope actual > slope anterior)
   - Squeeze: detecta valleys (mínimo local → giro alcista) y peaks (máximo local → giro bajista)
   - ADX: busca "fuerza naciente" — ADX estuvo bajo 20 en las últimas 10 velas y ahora sube (tendencia nueva)
   - VOL Profile y S/R sin cambios

   **`_analizar_mtf()` v3 — 4H predice, 2H confirma, 1W/1D advierten:**
   - Antes: 1W bloqueaba entradas si estaba en compresión o contrario. Bot paralizaba frecuentemente.
   - Ahora: 4H sola determina `long_ok`/`short_ok` — opera en la realidad actual del mercado
   - 2H confirma fuerza: "fuerte" si alinea con 4H, "débil" si no (+ penalización 8 pts)
   - 1W divergente: penalización 15 pts al score (advierte pero NO bloquea)
   - 1D divergente: penalización 10 pts al score (advierte pero NO bloquea)
   - Penalización máxima posible: 33 pts (raro que todos diverjan)

   **Penalización en bot loop:**
   - Score se calcula primero, luego MTF, luego se aplica la penalización
   - Si score > 0: `score = max(0, score - pen)` (protege de ir negativo)
   - Si score < 0: `score = min(0, score + pen)` (protege de ir positivo)
   - Score ajustado se guarda en `_bot_status["scores"]`

   **UI actualizada:**
   - Sección "Dirección MTF v3" — 4H y 2H aparecen primero (amarillo, son los que deciden)
   - 1D y 1W debajo (gris, solo informativo)
   - `mtf-2h` — nuevo span para el timeframe 2H
   - `mtf-advertencia` — banner amarillo que aparece solo cuando hay advertencias activas
   - `mtf-direccion` muestra: "🟢 LONG 4H 💪 2H FUERTE" o "🔴 SHORT 4H ⚡ 2H DÉBIL (−18pts)"

   **`cb_bot_status` — 15 outputs** (antes 12):
   Agregados: `mtf-2h` children, `mtf-advertencia` children, `mtf-advertencia` style

**Qué avanzó en el roadmap:**
- Item #1 (panel señales): ✅ COMPLETO (turno anterior)
- v3.0 predictivo: ✅ COMPLETO — `calcular_score` + `_analizar_mtf` + UI + bot loop

**Estado al cerrar:**
- Código subido y sintaxis verificada (python3.11 -c "import ast; ...")
- GitHub: pendiente push (ver abajo)
- Servidor: reiniciar para aplicar cambios

**Para el próximo AI — tarea inmediata:**
Item #2 del roadmap: **Historial de trades persistente**
- `trades_history.json` y `_registrar_trade()` ya existen en main.py
- Falta: panel visual en el dashboard (propuesta: tab separado "📋 Historial" o sección en panel derecho con los últimos 10 trades — activo, tipo, precio entrada/salida, P&L, fecha)
- Verificar primero si el v3.0 funciona bien (pedir a Eduardo que inicie el bot y confirme que el panel MTF v3 muestra datos)

**Para el próximo AI — comando correcto para matar el servidor en esta máquina:**
```powershell
Get-Process python3.11 -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false
```

**Punto de vista de Claude para Kimi:**
El cambio v3.0 es arquitectónico, no cosmético. La lógica anterior bloqueaba entradas cuando 1W estaba en compresión — lo cual es común (el semanal tarda semanas en moverse). Resultado: el bot rara vez entraba aunque el 4H y 2H tuvieran señal clara. El nuevo modelo invierte la jerarquía: el 4H ve la realidad actual, el 1W solo da contexto. Esto debería aumentar la frecuencia de señales válidas sin sacrificar calidad.

La penalización es conservadora intencionalmente: máximo 33 pts. El umbral de entrada es 70 pts. Un score v3 típico en señal fuerte vale ~70-80 pts. Con 33 de penalización baja a ~37-47 — no entra. Esto fuerza al bot a buscar señales bien alineadas incluso dentro del nuevo modelo permisivo. Eduardo puede ajustar los valores (15/10/8) en el código si quiere más o menos agresividad.

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
