# 🤖 HANDOFF PARA CLAUDE — AERO BOT PRO
## Escrito por Claude (sesión 26 mayo 2026) para Claude (próxima sesión)

---

## QUIÉN ERES EN ESTE PROYECTO

Eres el co-desarrollador de **AERO BOT PRO**, un bot de trading algorítmico para futuros perpetuos en BingX. El dueño del proyecto es **Eduardo Andrade**, trader profesional. Eduardo te transfiere su conocimiento de trading en tiempo real y tú lo transformas en código. Lleváis varias sesiones largas construyendo esto juntos.

---

## LECTURA OBLIGATORIA AL INICIAR SESIÓN

**Lee estos 3 archivos ANTES de tocar cualquier código:**

1. `C:\Users\Dell\Desktop\TradingBot\CLAUDE.md` — Reglas críticas del proyecto, bugs ya ocurridos, protocolo L99
2. `C:\Users\Dell\Desktop\TradingBot\STRATEGY.md` — Toda la estrategia de trading, tabla de scoring congelada, conocimiento acumulado de Eduardo
3. `C:\Users\Dell\Desktop\TradingBot\main.py` — Archivo principal (~3000 líneas), UI + bot loop + indicadores

---

## STACK TÉCNICO

- **Python:** `python3.11` (Microsoft Store) — NUNCA usar `python` a secas, no existe en esta máquina
- **Framework UI:** Dash 4.1.0 en puerto **8051**
- **Exchange:** BingX perpetual futures via ccxt
- **OS:** Windows 11 (Dell)
- **Directorio:** `C:\Users\Dell\Desktop\TradingBot\`

### Archivos del proyecto
```
TradingBot/
├── main.py          ← TODO: UI, callbacks, bot loop, indicadores (~3000 líneas)
├── bingx.py         ← Exchange: verificar_balance(), colocar_orden(), cerrar_posicion()
├── config.json      ← Configuración: API keys, parámetros del bot
├── iniciar_bot.bat  ← Lanzador Windows (usa python3.11 -B main.py)
├── assets/
│   └── centurion.css  ← Estilos del dashboard
├── CLAUDE.md        ← Reglas de desarrollo (este archivo es la ley)
├── STRATEGY.md      ← Estrategia de trading (árbitro de todos los cambios de scoring)
└── HANDOFF_CLAUDE.md  ← Este archivo (puedes borrarlo una vez leído)
```

### Comandos clave en PowerShell
```powershell
# Matar servidor existente
Get-Process python3.11 -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false

# Limpiar caché Python
Remove-Item "C:\Users\Dell\Desktop\TradingBot\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue

# Arrancar servidor
Start-Process cmd -ArgumentList "/k cd /d C:\Users\Dell\Desktop\TradingBot && python3.11 -B main.py"

# Verificar que está corriendo
Get-Process python3.11 -ErrorAction SilentlyContinue
```
URL del dashboard: **http://localhost:8051**

---

## DÓNDE NOS QUEDAMOS — 26 MAYO 2026

### ✅ Implementado y funcionando

| Componente | Estado | Descripción |
|---|---|---|
| `calcular_score()` v3.3 | ✅ | Score anticipatorio completo con tabla de 18+ condiciones |
| `_analizar_mtf()` v3 | ✅ | 4H predice, 2H confirma, 1W/1D penalizan (fetch paralelo) |
| `_detectar_trendlines(df, order=10)` | ✅ | Trendlines diagonales con polyfit, usa TODOS los pivots del período |
| `_detectar_sr_persistentes(df)` | ✅ | Niveles horizontales para `calcular_score()` (NO para el gráfico) |
| `_SR_LOOKBACK` por timeframe | ✅ | 4H=280, 1D=160, 1W=55 velas en todos los fetch |
| EMA55 exit (Regla K-2) | ✅ | Bot cierra SHORT cuando precio toca EMA55 (±0.5%) |
| S/R breakout | ✅ | Soporte roto = −25pts, resistencia rota = +25pts |
| Panel de señales mini | ✅ | Barra de progreso por activo, umbral ±70 |
| P&L en tiempo real | ✅ | Calcula en bot loop, muestra en "Posición Abierta" |
| Historial de trades | ✅ | Modal con tabla completa y pills de resumen |
| LED 3 estados | ✅ | DESCONECTADO/CONECTANDO/CONECTADO |
| BingX API keys a nivel módulo | ✅ | Con logging explícito de fallback a Binance |
| Slider marks en blanco | ✅ | Regla UI-1: menús siempre color blanco |
| Barra de score ELIMINADA | ✅ | Eduardo la quitó — cambiaba cada 5s, confundía |

### ⏳ Pendiente de implementar (documentado en STRATEGY.md, falta código)

| Bloque | Tarea | Prioridad |
|---|---|---|
| K-4 | EMA Crossover en `calcular_score()`: EMA10 cruza por debajo de EMA55 → bonus SHORT | Media |
| K-5 | Fractal Breakout: precio rompe último pivot low → confirma fuerza bajista | Media |
| K-6 | Trendline inferior como objetivo de salida de SHORT en bot loop | Media |
| K-2.3 | Re-entrada SHORT después del rebote de EMA55 | Baja |
| K-7 | Alta convicción 4H+2H (EMA cruce + fractal): bonus de score | Media |
| K-8 | Último estirón: resistencia tocada en tendencia bajista → −20 pts bonus SHORT. Forma más fuerte: squeeze ya negativo cuando precio toca resistencia | ✅ v3.4 |
| K-9 | Segunda confirmación: EMA cruce (roja>azul) + squeeze negativo = entrada SHORT válida pero "con más cuidado" → −15 pts. Mutuamente exclusivo con K-8 | ✅ v3.4 |

### 🔧 Backlog técnico
- Refactor modular: separar `main.py` (~3000 líneas) en `ui.py`, `indicators.py`, `exchange/`
- Migrar Volume Profile a TradingView Lightweight Charts

---

## PROTOCOLO DE APRENDIZAJE CONTINUO — LEY PERMANENTE

Eduardo transfiere su conocimiento de trader EN TIEMPO REAL conforme el mercado se mueve.

**NUNCA borrar una regla de trading existente.** Las reglas coexisten — no se reemplazan, no se fusionan.

### ⚠️ REGLA DE ORO — NUNCA VIOLAR:
**Cuando Eduardo enseña un patrón → STRATEGY.md + código en el MISMO mensaje.**
No documentar sin codificar. No codificar sin documentar.
Eduardo NO debería tener que preguntar "¿ya lo pasaste a código?" — es AUTOMÁTICO.

Cuando Eduardo dicte una regla nueva:
1. Agregarla a `STRATEGY.md` → sección K-N → nuevo bloque numerado
2. Incluir: cuándo aplica, cuándo NO aplica, contexto de mercado exacto
3. **Implementar en código INMEDIATAMENTE** — en la misma sesión
4. Marcar como ✅ en STRATEGY.md, CLAUDE.md y HANDOFF_CLAUDE.md
5. Actualizar `STRATEGY.md` PRIMERO — código DESPUÉS (Protocolo L99)

---

## ESTADO DEL BOT LOOP (orden crítico)

```
1. obtener_datos() + calcular_score()
2. _analizar_mtf(activo, ema_comp_pct)
3. Actualizar precio_extremo (SIEMPRE antes que todo)
4. STOP LOSS FIJO (si pérdida >= stop_loss_pct%)
5. CIERRE EN EMA55 — Regla K-2 (solo SHORT: si precio toca EMA55 → cerrar)
6. TRAILING STOP (si profit >= ts_activacion% y retroceso >= ts_distancia%)
7. CIERRE COMPRESIÓN EMA (abs(sep_4h) < ema_comp_pct)
8. CIERRE ZONA WAIT (-70 < score < 70)
9. ENTRADA LONG/SHORT (filtrada por mtf["long_ok"] / mtf["short_ok"])
```

---

## REGLAS CRÍTICAS — NO REPETIR ESTOS BUGS

1. Funciones con múltiples returns → siempre devolver la MISMA forma (tuple siempre tuple)
2. `config.json` → leer solo al arrancar, NUNCA en callbacks ni loops
3. True Range → calcular UNA sola vez, ADX reutiliza el mismo `tr`
4. `_LR_X`, `_LR_XVAR`, `_LR_XEND` → constantes a nivel módulo, NUNCA dentro de funciones
5. Volume Profile → máximo 2 trazas Plotly (separadores None), nunca 90 trazas
6. NUNCA `time.sleep()` en callbacks Dash → usar `ThreadPoolExecutor`
7. `verificar_balance()` → siempre retorna `float` o `None`, nunca tuple
8. `precio_extremo` → actualizar ANTES de cualquier check de exit
9. `_gr(est, val)` → función de módulo, nunca redefinir local en callbacks
10. Log trim → siempre `[:8]` en TODOS los paths
11. Fallback capital_pct → `capital_pct or 5` (no `or 20`)
12. `ccxt.bingx()` → SIEMPRE con API keys (`_bx_api_key`, `_bx_api_secret`)
13. Fallback a Binance → SIEMPRE loggear, nunca silencioso
14. `_bot_status["activos"]` = `activos_sel or []` (sin filtrar BTC)
15. `python3.11` en esta máquina — NUNCA `python`
16. `config.json` → nunca agregar líneas fuera del objeto JSON
17. Emojis en `print()` → las primeras 2 líneas de `main.py` son el fix de encoding (NO mover ni borrar)
18. LED 3 estados → `cb_bot_status` es el ÚNICO que transiciona a `"led-dot"` (verde)
19. `btn-historial` → en `app.layout` estático, NUNCA en layout dinámico

---

## PALETA DE COLORES — ÚNICA PERMITIDA

```
Texto de controles/menús  → blanco  #ffffff
Títulos de sección        → dorado  #c8a84b
Valores numéricos clave   → dorado  #c8a84b o color de estado
Señal LONG                → verde   #00ff88
Señal SHORT               → rojo    #ff3355
Neutral/Esperar           → gris    #a0a8c0
Fondo panels              → negro   #0a0a0f / #0d0d1a
```
No inventar colores nuevos. Solo usar estos.

---

## ERRORES DE DISEÑO — NO REPETIR NUNCA

### UI-ERR-1: Barra de score global que se actualiza cada 5 segundos
El score cambia con cada tick → la barra cambia de color y valor constantemente → confunde al usuario.
**Decisión de Eduardo: NUNCA volver a agregar esta barra.**
Si se quiere mostrar el score → panel de señales mini (por activo, ya existe).

### UI-ERR-2: Texto superpuesto sobre barra de progreso
Número + etiqueta como overlay en el centro de una barra → se pisan visualmente.
Siempre: número a la izquierda, barra en el centro (sin texto), etiqueta a la derecha.

### UI-ERR-3: Mezcla de colores
No usar dorado para controles del menú. Usar SOLO la paleta definida arriba.

---

## CONOCIMIENTO DE TRADING DE EDUARDO (resumen de bloques K)

| Bloque | Regla | Implementada |
|---|---|---|
| K-1 | Trinidad de entrada: squeeze + trendline + rebote = señal de máxima convicción | En score v3.3 |
| K-2 | EMA55 rebote: SHORT toca EMA roja → cerrar SIEMPRE, 90% rebote al alza | ✅ Bot loop paso 5 |
| K-2.3 | Re-entrada SHORT después de rebote EMA55 si squeeze sigue negativo | ⏳ Pendiente |
| K-3 | Timeframes: 4H para entradas, 1D/1W para contexto | ✅ MTF v3 |
| K-4 | EMA crossover: roja(55) cruza arriba de azul(10) = estructura bajista confirmada | ⏳ Pendiente |
| K-5 | Fractal breakout: precio rompe último pivot low = fuerza bajista confirmada | ⏳ Pendiente |
| K-6 | Trendline inferior = objetivo de salida de SHORT (el precio "impacta" ahí) | ⏳ Pendiente |
| K-7 | Alta convicción: 4H squeeze + 2H EMA cruce + 2H fractal break = todo alineado | ⏳ Pendiente |
| K-8 | Último estirón: precio toca resistencia en contexto bajista → −20 pts adicionales. Forma más fuerte: squeeze ya negativo en ese mismo momento | ✅ calcular_score() v3.4 |
| K-9 | Segunda confirmación: EMA cruce bajista + squeeze negativo = SHORT válido "con más cuidado" → −15 pts (menor que K-8, entrada más tardía) | ✅ calcular_score() v3.4 |

---

## CONFIG ACTUAL (mayo 2026)

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

---

## NOTA PERSONAL DE CLAUDE → CLAUDE

Eduardo es un excelente maestro. No te limites a ejecutar instrucciones mecánicas — escucha el razonamiento detrás de cada regla que dicta. Cuando diga "te voy a enseñar algo que está ocurriendo ahorita", párate, lee el contexto de mercado, pregunta si necesitas aclarar, y guarda EXACTAMENTE lo que dice con sus propias palabras antes de codificar.

El objetivo no es un bot de reglas — es un bot que **razona como Eduardo**. Hay una diferencia enorme.

Cuando Eduardo muestre una imagen de un trade, siempre pregunta:
- ¿En qué timeframe estás?
- ¿Cuál fue la señal principal que usaste para entrar?
- ¿Qué indicador te dijo que era hora de salir?

Esas respuestas son oro para `calcular_score()` y el bot loop.

---

*Generado automáticamente al final de la sesión del 26 de mayo de 2026.*
*Puedes borrar este archivo después de leerlo — toda la información vive en CLAUDE.md y STRATEGY.md.*
