# AERO BOT PRO — Protocolo de Equipo: Claude + Kimi + Humano

---

## Quiénes somos y cómo trabajamos

Este proyecto es una colaboración activa entre tres participantes:

- **Eduardo (Humano)** — Dueño del producto. Toma decisiones finales. Define la visión y las prioridades. Es el árbitro cuando Claude y Kimi tienen opiniones distintas.
- **Claude (Anthropic)** — Especialista en arquitectura, decisiones técnicas, análisis de trading, documentación y calidad de código.
- **Kimi (Moonshot AI)** — Especialista en contexto largo, archivos grandes, generación rápida de código y debugging exhaustivo.

Ningún AI está conectado directamente al otro. **El código, GitHub y este archivo son el canal de comunicación entre todos.**

---

## Reglas del equipo — no negociables

1. **Leer antes de tocar** — Antes de escribir una sola línea, el AI que entra lee `CLAUDE.md` completo. Ahí está toda la arquitectura, bugs conocidos y reglas críticas.
2. **GitHub es la única verdad** — Todo cambio se sube a GitHub al terminar el turno. Nunca se pasa trabajo por chat o texto plano.
3. **No romper lo que funciona** — Si algo está marcado como ✅ en `CLAUDE.md`, no se toca sin razón explícita.
4. **El humano decide** — Si Claude y Kimi proponen soluciones distintas, Eduardo elige. Ambos AIs exponen su razonamiento con datos, no con opiniones.
5. **Cada turno termina con handoff completo** — El AI que termina deja el HANDOFF actualizado (ver sección abajo) antes de cerrar sesión.

---

## Ubicación del proyecto

| Recurso | Ruta |
|---|---|
| Carpeta local | `C:\Users\Dell\Desktop\TradingBot\` |
| Repositorio GitHub | `https://github.com/viajandoa120fps-cmyk/TradingBot.git` |
| Archivo principal | `main.py` (puerto 8051, Python Dash) |
| Guía de arquitectura | `CLAUDE.md` — leer primero, siempre |
| Protocolo de equipo | `TEAM_PROTOCOL.md` (este archivo) |
| Lanzador | `iniciar_bot.bat` → doble clic → `http://localhost:8051` |

---

## Stack técnico

- **Python 3** + **Dash** (Plotly) — Dashboard web puerto 8051
- **ccxt** — Conexión a BingX perpetual swaps
- **Pandas / NumPy / SciPy** — Indicadores técnicos
- **Threading** — Bot loop en background
- **Telegram Bot API** — Notificaciones de operaciones

---

## Estado del proyecto al inicio de esta sesión

### ✅ Completado y funcionando
- Bot loop con señales LONG/SHORT (score ±70), Stop Loss, Trailing Stop, Max Pérdida Diaria
- Indicadores: EMA 10/55, Squeeze Momentum LazyBear, ADX, Volume Profile, S/R
- MTF Guardarrail cascade 1W → 1D → 4H
- Notificaciones Telegram completas
- Conexión BingX con API keys correctas + fallback Binance con logging
- Mini gráficos por activo seleccionado
- Balance en tiempo real, log de actividad

### 🔴 Bug activo — PRIORIDAD 1
**Panel `panel-senales-mini` no se renderiza visualmente.**

El panel existe en el código y está registrado correctamente. El bot calcula scores (visible en log: `LINK: ▼ SHORT score=-70`). Las tarjetas de señal no aparecen en el browser.

**Código relevante:**
```python
# HTML — en _pagina_principal()
html.Div(id="panel-senales-mini", style={"marginTop": "8px"})

# Helper
def _senal_card(ticker, score): ...

# Callback — cb_bot_status() — 9 outputs, sin State
Output("panel-senales-mini", "children")

# Scores guardados en bot loop
_bot_status["scores"][activo] = score

# Activos guardados al iniciar bot
_bot_status["activos"] = [a for a in activos_lista if a != "BTC"]
```

**Lo que ya se intentó sin éxito:**
- Eliminar caché Python (`__pycache__`) ✅
- Modo InPrivate en Edge ✅
- Renombrar IDs con ñ a ASCII (`panel-señales-mini` → `panel-senales-mini`) ✅
- Mover lectura de activos de `State(checklist)` a `_bot_status["activos"]` ✅
- Placeholder con colores visibles ✅

**Hipótesis más probable:** Conflicto entre el callback `render_page` (que carga `_pagina_principal()` en `page-content`) y `cb_bot_status` (que intenta actualizar `panel-senales-mini` dentro de ese layout dinámico). Dash puede tener race condition al actualizar componentes dentro de layouts generados por otro callback.

### ⚠️ Bugs secundarios conocidos
- `Sin Stop Fijo OK` aparece en vez de `Stop Loss −5.0%` (mismo patrón de rendering)
- Slider capital muestra 20% aunque config tiene 5% (cosmético)
- Label activos muestra texto viejo aunque `TRANSLATIONS["es"]["assets"]` está actualizado

### 📋 Roadmap (en orden)
1. **[AHORA]** Reparar `panel-senales-mini`
2. Historial de trades persistente (`trades_history.json`)
3. P&L en tiempo real de posición abierta
4. Refactorizar `main.py` en módulos separados (`ui.py`, `indicators.py`, `exchange/`)
5. Setup wizard para nuevos usuarios
6. Soporte multi-exchange (Binance como segundo conector)

---

## HANDOFF — Lo que el AI que termina debe dejar escrito

Al final de cada sesión de trabajo, el AI que estuvo activo actualiza esta sección:

---

### 🔄 ÚLTIMO HANDOFF

**Fecha:** 25 mayo 2026
**AI que trabajó:** Claude (Anthropic)
**Commit GitHub:** `22b21d3`

**Qué se hizo en este turno:**
- Implementé `panel-senales-mini` completo con tarjetas por activo y barra de progreso
- Corregí el bug de BingX sin API keys (datos venían de Binance silenciosamente)
- Añadí logging explícito al fallback Binance
- Renombré todos los IDs con `ñ` a ASCII puro
- Moví la lectura de activos del State del checklist a `_bot_status["activos"]`
- Actualicé `iniciar_bot.bat` con flag `-B`
- Documenté protocolo de debugging en `CLAUDE.md`
- Creé `TEAM_PROTOCOL.md` (este archivo)

**Estado al cerrar turno:**
- Servidor corriendo con código nuevo confirmado por `[CHECK]`
- Panel-senales-mini implementado pero NO visible todavía en browser
- Bug de rendering Dash/Edge sin resolver
- GitHub actualizado y sincronizado

**Qué debe hacer el próximo AI:**
1. Leer `CLAUDE.md` completo
2. Leer este HANDOFF
3. Clonar/pull desde GitHub: `git pull origin main`
4. Reproducir el bug: arrancar servidor → seleccionar activos → iniciar bot → verificar si `panel-senales-mini` aparece
5. Investigar el race condition entre `render_page` y `cb_bot_status` en Dash
6. Proponer y testear solución — posibles enfoques:
   - Usar `dcc.Store` intermedio para pasar scores al panel en vez de callback directo
   - Mover `panel-senales-mini` fuera de `page-content` al layout estático
   - Usar `clientside_callback` para actualizar el panel desde el cliente

**Punto de vista de Claude para el próximo AI:**
El problema central es que Dash tiene dificultades actualizando componentes dentro de layouts dinámicos (generados por otro callback) en Microsoft Edge. El mismo patrón aparece en 3 elementos distintos (`lbl-activos`, `Sin Stop Fijo`, `panel-senales-mini`). La solución más robusta probablemente es **mover los elementos dinámicos fuera del `page-content` callback** y ponerlos en el layout estático (`app.layout`) directamente, para que Dash siempre sepa dónde están.

---

## Cómo el próximo AI comienza su turno

```
1. Lee CLAUDE.md completo
2. Lee TEAM_PROTOCOL.md (este archivo) — especialmente el HANDOFF
3. git pull origin main
4. Reproduce el bug actual
5. Propone solución con razonamiento
6. Implementa, testea, confirma con Eduardo
7. Actualiza HANDOFF al final con: qué hizo, qué estado quedó, qué sigue
8. git add . && git commit && git push
9. Informa a Eduardo que el turno terminó y el repo está actualizado
```

---

## Filosofía del producto

Este no es un proyecto de garage. Es un producto de trading profesional que se va a distribuir. Eso significa:

- **Calidad sobre velocidad** — Mejor hacer menos cosas bien hechas que muchas a medias
- **Sin errores silenciosos** — Todo fallo debe loggearse, nada se traga con `except: pass`
- **Modularidad** — Cada componente separado, comunicándose por interfaces claras
- **El trader primero** — Cada decisión de UI/UX se evalúa desde: "¿Le sirve al trader para operar mejor?"

---

*Última actualización: Claude — 25 mayo 2026*
