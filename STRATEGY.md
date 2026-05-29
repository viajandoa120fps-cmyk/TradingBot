# AERO BOT PRO — STRATEGY.md
## El Cerebro de Eduardo Andrade — Fuente de Verdad Absoluta

> **Este documento ES el árbitro de todo el sistema.**
> Cuando el código y este documento no coinciden → el código está mal.
> Cuando Eduardo corrige al bot → primero este documento, luego el código.
> Ninguna IA puede cambiar el scoring sin pasar primero por aquí.
> **NUNCA borrar contenido. Solo agregar y reorganizar.**

---

## ÍNDICE

- [PARTE 0 — PROTOCOLO L99](#parte-0)
- [PARTE I — FILOSOFÍA Y PRINCIPIOS](#parte-i)
- [PARTE II — INDICADORES](#parte-ii)
  - [II-A. Squeeze Momentum](#ii-a-squeeze-momentum)
  - [II-B. EMAs (Medias Móviles)](#ii-b-emas)
  - [II-C. ADX](#ii-c-adx)
  - [II-D. Volumen — Volume Profile](#ii-d-volumen)
  - [II-E. Soportes](#ii-e-soportes)
  - [II-F. Resistencias / Techos](#ii-f-resistencias--techos)
  - [II-G. Trendlines Diagonales](#ii-g-trendlines-diagonales)
- [PARTE III — TIMEFRAMES](#parte-iii)
- [PARTE IV — SETUPS DE ENTRADA](#parte-iv)
  - [IV-A. Entradas SHORT](#iv-a-entradas-short)
  - [IV-B. Entradas LONG](#iv-b-entradas-long)
  - [IV-C. Método Ráfaga](#iv-c-metodo-rafaga)
  - [IV-D. Órdenes en Espera — Límites](#iv-d-rdenes-en-espera)
  - [IV-E. Movimientos Flash](#iv-e-movimientos-flash)
- [PARTE V — GESTIÓN DE POSICIÓN](#parte-v)
- [PARTE VI — SISTEMA TÉCNICO DE SCORING](#parte-vi)
- [PARTE VII — PREGUNTAS PENDIENTES](#parte-vii)
- [PARTE VIII — EXPERIMENTOS](#parte-viii)

---

<a name="parte-0"></a>
## PARTE 0 — PROTOCOLO L99 (El Árbitro)

**L99 = Nivel 99 de estabilidad.** Llegamos aquí después de muchas iteraciones.
Los cambios son quirúrgicos, no reactivos.

### Regla principal
```
OBSERVACIÓN DE ERROR → STRATEGY.md (actualizar primero) → CÓDIGO (después)
Nunca al revés. Sin excepciones.
```

### Protocolo de cambios en calcular_score()
```
PASO 1 — Observar: ¿qué activo, timeframe, hora? ¿Qué indicador falló?
PASO 2 — Diagnosticar en este documento: ¿viola la tabla de scoring?
PASO 3 — Proponer aquí en plain English. ¿Contradice algo existente?
PASO 4 — Verificar los 7 Escenarios Canónicos (Parte VI). ¿Alguno falla?
PASO 5 — Actualizar el código con lo definido aquí.
PASO 6 — Actualizar tabla de scoring e historial de versiones aquí.
```

### Lo que NUNCA se hace
```
❌ Cambiar un peso sin verificar los 7 escenarios canónicos.
❌ Agregar excepciones condicionales complejas — eso es código espagueti.
❌ Cambiar el código y LUEGO documentar aquí.
❌ Dos indicadores midiendo lo mismo con pesos acumulativos (doble conteo).
❌ Borrar una regla de Eduardo aunque parezca redundante — nunca son lo mismo.
```

### Protocolo de Aprendizaje Continuo
> **"Te tengo que educar conforme el precio se vaya moviendo. Registra todo
> mi conocimiento, guárdalo y aplícalo en código SIN BORRAR nada — tengo
> muchas reglas diferentes para tácticas que se parecen mucho."**
> — Eduardo Andrade

```
Cuando Eduardo enseña → STRATEGY.md + código en el MISMO momento.
No documentar sin codificar. No codificar sin documentar.
Eduardo NO debería preguntar "¿ya lo pasaste a código?" — es automático.
```

---

<a name="parte-i"></a>
## PARTE I — FILOSOFÍA Y PRINCIPIOS
### (Eduardo Andrade — dictados en sesiones reales, mayo 2026)

1. **El bot predice el futuro, no describe el presente.**
   No importa si los indicadores están en verde ahora — lo que importa es hacia dónde van.

2. **El Squeeze Momentum en techo es la señal más anticipatoria de SHORT.**
   Cuando el momentum llega a su máximo local y empieza a bajar, el movimiento bajista
   ya comenzó aunque el precio no lo muestre todavía.

3. **Soporte testeado múltiples veces → ruptura = caída más fuerte y sostenida.**
   Tiene "peso emocional". Cuando se rompe, todos los que compraron ahí salen al mismo tiempo.

4. **Techo roto hacia arriba = LONG abierto. El techo se convierte en soporte.**
   Si el precio rompe con fuerza una resistencia, esa resistencia ya no existe — ahora es soporte.
   El bot NO sigue en SHORT después de un breakout alcista.

5. **ADX mide FUERZA de tendencia, no DIRECCIÓN.**
   ADX alto con precio bajando = SHORT fuerte. ADX alto con precio subiendo = LONG fuerte.
   ADX nunca suma puntos positivos por default.

6. **EMA es un indicador reactivo — no debe dominar el score.**
   Solo pesa fuerte cuando su slope está acelerando. EMA leve + squeeze cayendo ≠ señal alcista.

7. **La salida la maneja el Trailing Stop — no la perfección técnica.**
   El valle del squeeze es confirmación visual de que la tesis fue correcta, no el momento exacto de salida.

8. **No operar con emociones, problemas familiares, o bajo efectos de sustancias.**
   *(Aplica a decisiones humanas, no al bot.)*

9. **La venganza no existe en el trading.** Perder un trade no justifica doblar la apuesta.

10. **La paciencia paga, la desesperación pega.** ESPERAR es una posición válida.

---

<a name="parte-ii"></a>
## PARTE II — INDICADORES
### Cómo leer e interpretar cada indicador

---

<a name="ii-a-squeeze-momentum"></a>
### II-A. SQUEEZE MOMENTUM — Todas las reglas

> **El indicador principal de Eduardo. Sin squeeze claro → sin entrada.**

#### Cómo leerlo
```
Squeeze positivo y subiendo  → sesgo LONG (el mercado tiene fuerza alcista)
Squeeze negativo y bajando   → sesgo SHORT (el mercado tiene fuerza bajista)
Squeeze cerca de cero        → ESPERAR — el mercado no tiene dirección
```

#### Señales por tipo (de más a menos anticipatorio)

| Señal | Descripción | Puntos en score |
|-------|-------------|-----------------|
| `bear_peak` | Máximo local exacto del momentum → giro bajista | −40 |
| `bull_valley` | Mínimo local exacto del momentum → giro alcista | +40 |
| `bear_post_peak` | 3 barras declinando, todavía positivo | −25 |
| `bull_post_valley` | 3 barras subiendo, todavía negativo | +25 |
| `bear_accel` | Momentum < 0 y acelerando hacia abajo | −30 |
| `bull_accel` | Momentum > 0 y acelerando hacia arriba | +30 |
| Positivo creciendo | mom > 0 y subiendo | +10 |
| **Positivo cayendo** | mom > 0 pero bajando = perdiendo fuerza = BAJISTA | **−10** |
| Negativo subiendo | mom < 0 pero recuperándose = posible giro | +10 |
| Negativo cayendo | mom < 0 y siguiendo abajo | −10 |

#### Regla crítica — Positivo cayendo NO es alcista
```python
# Si el squeeze sube pero empieza a bajar, el toro se está cansando.
# Eso es BAJISTA, no alcista. El bot lo penaliza.
elif mom_now > 0 and growing: pts += 10   # creciendo = alcista
elif mom_now > 0:             pts -= 10   # cayendo = bajista (pierde fuerza)
```

#### Cómo usar el squeeze con otros indicadores
```
Squeeze solo (sin S/R ni EMA cruce) → señal mínima, esperar confirmación
Squeeze + trendline acompañando     → señal fuerte (K-1.2)
Squeeze + precio rebota en trendline → ENTRAR (K-1.3)
Squeeze + precio toca resistencia   → SHORT fuerte (K-8)
Squeeze + EMA cruce confirmado      → segunda confirmación válida (K-9)
```

#### Valle desarrollado = objetivo de salida
```
La posición SHORT ideal dura hasta que el squeeze desarrolle un VALLE ROJO bien formado
(momentum muy negativo, barras creciendo en tamaño = impulso bajista en su máximo).
En la práctica: el trailing stop captura la ganancia antes de llegar al valle perfecto.
El valle es confirmación visual de que la tesis fue correcta.
```

---

<a name="ii-b-emas"></a>
### II-B. EMAs (MEDIAS MÓVILES) — Todas las reglas

> **Las EMAs confirman tendencia. Reaccionan tarde — no deben dominar el score.**

#### Las dos EMAs del sistema
```
EMA 10 (azul)  → corto plazo, reactiva, sigue el precio de cerca
EMA 55 (roja)  → largo plazo, lenta, actúa como imán del precio
```

#### Regla de slope (pendiente)
```
Solo pesa fuerte cuando el slope está ACELERANDO.
EMA slope acelerando al alza   → +30 pts (tendencia establecida y ganando fuerza)
EMA slope positivo sin acelerar → +8 pts (reactiva, peso reducido)
EMA slope acelerando a la baja  → −30 pts
EMA slope negativo sin acelerar → −8 pts
```

#### Cruce de EMAs — K-4 (Eduardo, 26 mayo 2026)
```
CRUCE BAJISTA: EMA roja (55) cruza por ENCIMA de azul (10)
→ estructura bajista CONFIRMADA
→ señal MÁS FUERTE que el slope solo
→ el cruce EN SÍ MISMO es la señal — no solo la posición relativa

CRUCE ALCISTA: EMA azul (10) cruza por ENCIMA de roja (55)
→ estructura alcista CONFIRMADA

DIFERENCIA con slope:
  Slope negativo = la EMA está bajando (puede ser leve, transitorio)
  Cruce          = el momentum cambió de dirección definitivamente
```

**Implementación:** cruce reciente (últimas 3 velas) + squeeze confirmando → bonus score
*(K-4 pendiente de implementar en calcular_score())*

#### EMA 55 como imán de precio — K-2 (Eduardo, 26 mayo 2026)
```
En cualquier tendencia, el precio NO cae en línea recta.
Cae en zigzag: baja → toca EMA55 → rebota → sigue bajando → toca EMA55 → rebota...

La EMA 55 (roja) actúa como imán. Probabilidad de rebote al tocarla: ~90%.
```

#### Qué hacer cuando estás en SHORT y el precio toca EMA55
```
Acción: CERRAR la posición SHORT — SIEMPRE. Sin importar:
  - Si está en ganancia o en pérdida
  - La distancia recorrida (puede ser 2%, 5%, 10%)
  - Lo que diga el squeeze en ese momento

Razón: la EMA55 produce rebote ~90% del tiempo.
       El rebote moverá el precio EN CONTRA de la posición SHORT.

Ejemplo real (Eduardo, 26 mayo 2026):
  Entrada SHORT: ~$78,000 | Cierre en EMA55: ~$73,900
  Distancia: −5.22% precio / ~52% profit con 10x / 4 velas 4H (16h)

Parámetro de toque: precio dentro del 0.5% de EMA55 = "tocó la EMA55"
Prioridad en bot loop: después del Stop Loss, ANTES del trailing stop ✅ IMPLEMENTADO
```

#### Cómo distinguir rebote de EMA55 vs giro real de tendencia
```
REBOTE temporal (seguir el plan SHORT):
- Squeeze momentum sigue negativo después del toque
- El rebote llega a EMA55 pero NO la supera con fuerza
- Las trendlines de resistencia siguen intactas

GIRO real de tendencia (NO re-entrar en SHORT):
- Squeeze momentum gira de negativo a positivo (bull_valley)
- El precio rompe la EMA55 hacia arriba con fuerza (cierra por encima)
- La trendline de resistencia también se rompe al alza
→ Cerrar SHORT. No re-entrar. Esperar nueva señal.
```

---

<a name="ii-c-adx"></a>
### II-C. ADX — Todas las reglas

> **ADX mide FUERZA de tendencia, NUNCA dirección. Este error ya ocurrió — no repetir.**

#### Cómo leerlo correctamente
```
ADX alto y creciendo + precio bajando = SHORT FUERTE
ADX alto y creciendo + precio subiendo = LONG FUERTE
ADX bajo (<20) = el mercado no tiene tendencia clara → penalizar score

ADX NO suma puntos positivos por default.
ADX amplifica lo que el precio ya está haciendo.
```

#### Reglas de puntuación
```
ADX emergente (min10 < 20 y ahora creciendo) → ±10 pts  (tendencia naciendo)
ADX fuerte (≥25 y creciendo)                → ±5 pts   (tendencia madura)
ADX < 20 (sin fuerza)                        → −5 pts   (penaliza — mercado sin dirección)
```

#### Implementación direction-aware (regla crítica)
```python
# NUNCA hacer adx_bonus incondicional — eso anula señales SHORT
if pts >= 0:
    pts += adx_bonus   # amplifica bullish
else:
    pts -= adx_bonus   # amplifica bearish
```

---

<a name="ii-d-volumen"></a>
### II-D. VOLUMEN — Volume Profile — Todas las reglas

> **El POC (Point of Control) es el precio con mayor volumen histórico negociado.**

#### Cómo leerlo
```
Precio SOBRE el POC → zona de soporte por volumen → +10 pts
Precio BAJO el POC  → zona de resistencia por volumen → −10 pts
```

#### Reglas de visualización
```
Volume Profile: 90 bins en el período cargado
POC: bin con mayor volumen → color dorado
Renderizado: 2 trazas Plotly (no 90) para no degradar performance
```

#### Nota de Eduardo
```
El volumen confirma — no lidera. Una zona de alto volumen sin squeeze ni S/R
no es suficiente para entrar. Es información de contexto.
```

---

<a name="ii-e-soportes"></a>
### II-E. SOPORTES — Todas las reglas

> **Un soporte es un piso donde el precio ha rebotado antes. Cuantas más veces, más fuerte.**

#### Cómo se forman y qué significan
```
El precio toca un nivel y rebota hacia arriba → ese nivel queda marcado como soporte.
Cuantas más veces el precio respete ese nivel, más "peso emocional" tiene.
Los traders recuerdan ese nivel — muchos ponen órdenes de compra ahí.
```

#### Reglas de scoring según posición del precio

| Situación | Distancia | Puntos | Descripción |
|-----------|-----------|--------|-------------|
| Precio sobre soporte | 0–1.5% encima | +20 | Zona de rebote probable |
| Precio rompió soporte | 0–5% debajo | −25 | Breakout bajista — caída más fuerte |

#### Soporte testeado múltiples veces (Eduardo, mayo 2026)
```
Soporte tocado 2+ veces sin romper → nivel MÁS SIGNIFICATIVO que uno nuevo.
Cuando ese soporte SE ROMPE → la caída siguiente es más fuerte y sostenida.
Razón: todos los que compraron en esas 2+ ocasiones salen al mismo tiempo = presión vendedora masiva.
```

#### Soporte roto = SHORT reforzado
```
SI soporte testeado múltiples veces ES ROTO hacia abajo:
→ −25 pts (breakout bajista) + contexto de caída sostenida
→ Más bajista que simplemente "estar cerca de resistencia"
→ El bot lo identifica como "BREAK↓ XXXXX" en el guardarrail S/R
```

#### Soporte como exit target de SHORT — K-6
```
La trendline de soporte inferior es donde termina el movimiento bajista.
Cuando el precio la toca → CERRAR SHORT (ver Parte V para prioridad completa).
```

---

<a name="ii-f-resistencias--techos"></a>
### II-F. RESISTENCIAS / TECHOS — Todas las reglas

> **Un techo es un techo donde el precio ha sido rechazado antes. El mercado lo recuerda.**

#### Cómo se forman y qué significan
```
El precio sube hasta un nivel y baja → ese nivel queda marcado como resistencia.
Los traders recuerdan ese nivel — muchos ponen órdenes de venta ahí.
El precio tiende a ser rechazado al llegar.
```

#### Reglas de scoring según posición del precio

| Situación | Distancia | Puntos | Descripción |
|-----------|-----------|--------|-------------|
| Precio bajo resistencia | 0–1.5% debajo | −20 | Zona de rechazo probable |
| Precio rompió resistencia | 0–5% encima | +25 | Breakout alcista — techo → soporte |

#### Techo roto = LONG, no SHORT
```
Si el precio rompe con fuerza una resistencia que lo bloqueaba:
→ +25 pts (breakout alcista)
→ La resistencia ahora ES soporte — el camino está despejado
→ El bot NO sigue en SHORT después de este evento
```

#### El Último Estirón — K-8 (Eduardo, 27 mayo 2026) ✅ IMPLEMENTADO v3.4
```
PATRÓN: el precio viene cayendo → da un último empujón hacia arriba → toca la resistencia → cae.

El mercado ENGAÑA: hace pensar que ya no llegará al techo.
Pero SIEMPRE existe la posibilidad de ese último estirón.
ESTRATEGIA: colocar orden límite SHORT en la resistencia, esperando ese toque.

CUÁNDO APLICA:
  - Tendencia bajista activa (EMA10 < EMA55 O squeeze negativo)
  - Precio venía bajando y rebotó hacia arriba
  - El rebote lleva el precio a tocar la resistencia conocida
  → Ese toque en contexto bajista = TRAMPA. Señal SHORT reforzada.

CUÁNDO NO APLICA:
  - Tendencia alcista activa — puede ser breakout, no rechazo
  - Sin contexto bajista previo

SCORING: resistencia base (−20) + K-8 bonus (−20) = −40 pts total
Guardarrail muestra: "K8 R XXXXX"

Forma MÁS FUERTE de K-8:
  Squeeze ya negativo ANTES del último estirón.
  → El indicador principal y el S/R apuntan al mismo lado simultáneamente.
  → Máxima convicción SHORT.

Ejemplo real (Eduardo, 27 mayo 2026):
  BTCUSDT cayendo → rebote → precio toca resistencia (flecha) → caída fuerte.
```

#### Cross-confirm — Squeeze peak + Resistencia (ya existente)
```
bear_peak + precio en resistencia = −18 pts adicionales (bonus cross-confirm)
El squeeze gira EXACTAMENTE en un nivel clave = señal combinada más fuerte.
```

---

<a name="ii-g-trendlines-diagonales"></a>
### II-G. TRENDLINES DIAGONALES — Reglas de visualización

> **Las trendlines muestran DIRECCIÓN, no solo niveles. Eduardo ve el gráfico en 3D.**

#### Por qué diagonales y no horizontales
```
Línea horizontal: solo dice "precio estuvo aquí antes" — no revela intención.
Línea diagonal:   conecta los máximos entre sí y los mínimos entre sí
                  → revela si el precio quiere subir o bajar
                  → muestra si la estructura es alcista, bajista, o compresión
```

#### Reglas de construcción
```
Trendline resistencia: regresión lineal por TODOS los pivots de máximos del período
  → Pendiente negativa = techos bajando = estructura bajista
  → Pendiente positiva = techos subiendo = precio intentando romper al alza

Trendline soporte: regresión lineal por TODOS los pivots de mínimos del período
  → Pendiente positiva = pisos subiendo = estructura alcista
  → Pendiente negativa = pisos bajando = presión vendedora

Cuando ambas convergen → cuña/triángulo → rotura inminente
```

#### Parámetros técnicos
```
Colores: soporte = verde #00e676 | resistencia = rojo #ff4444
Grosor: 1.2px — delgada, no intrusiva sobre las velas
Estilo: dash="dot" — punteada, distinguible de las EMAs (continuas)
Pivots: order=10 (ventana 10 velas a cada lado para ser pivot significativo)
Una de cada: 1 trendline soporte + 1 trendline resistencia = 2 líneas en pantalla
```

#### Persistencia por timeframe
```
4H → _SR_LOOKBACK = 280 velas (45 días)
1D → _SR_LOOKBACK = 160 velas (150 días)
1W → _SR_LOOKBACK = 55 velas  (1 año)
```

#### Separación de responsabilidades (L99)
```
_detectar_trendlines(df)      → SOLO para crear_grafico() (visualización)
_detectar_sr_persistentes(df) → SOLO para calcular_score() (scoring)
El chart muestra DIRECCIÓN. El score evalúa NIVELES. Son preguntas distintas.
```

---

<a name="parte-iii"></a>
## PARTE III — TIMEFRAMES
### Cómo se relacionan 1W, 1D, 4H y 2H entre sí

> **Cada timeframe tiene un rol distinto. Entender la jerarquía es clave.**

#### Jerarquía y rol de cada timeframe

| Timeframe | Rol | Decisión |
|-----------|-----|----------|
| 1W (semanal) | Dirección maestra | ¿Cuál es la tendencia grande? |
| 1D (diario) | Contexto intermedio | ¿La tendencia semanal sigue activa hoy? |
| 4H | Señal de entrada | ¿Cuándo entrar exactamente? |
| 2H | Confirmación | ¿La señal 4H tiene fuerza adicional? |

#### Cómo se leen juntos (K-3 — Eduardo, 26 mayo 2026)
```
Timeframe de operación: 4H (principal para Eduardo)
  - Las entradas se ejecutan en 4H
  - Los rebotes se confirman en 4H (no en 1H ni en 15m)
  - Una vela 4H que toca la EMA y cierra lejos = rebote confirmado

Timeframe de contexto: 1D y 1W (dirección maestra)
  - 1D bajista + 4H bajista → trade de alta convicción
  - 1W alcista + 4H bajista → trade posible, pero con precaución extra

Regla: Eduardo opera en 4H y confía en lo que VE en 4H.
El 1H puede mostrar algo diferente — eso no invalida la señal 4H.
```

#### MTF Guardarrail v3 (sistema actual del bot)

**Filosofía: 4H predice, 2H confirma, 1W/1D advierten (no bloquean)**

```
4H → PREDICE:
  sep_4h > +1% Y mom_4h > 0  → long_ok = True
  sep_4h < −1% Y mom_4h < 0  → short_ok = True

2H → CONFIRMA:
  Si 2H alinea con 4H → fuerza = "fuerte"
  Si 2H no alinea     → fuerza = "débil" + penalización 8 pts

1W → ADVIERTE (no bloquea):
  Si diverge de señal 4H → penalización 15 pts

1D → ADVIERTE (no bloquea):
  Si diverge de señal 4H → penalización 10 pts
```

#### Alta convicción multi-timeframe — K-7 (Eduardo, 26 mayo 2026)
```
SETUP DE MÁXIMA CONVICCIÓN (las 3 señales alineadas):
  4H: squeeze momentum bajista (señal principal)
  2H: EMA roja cruza encima de azul (cruce bajista confirmado)
  2H: precio rompe último fractal hacia abajo (fuerza confirmada)
  → AMBOS timeframes dicen lo mismo = trade de máxima convicción

Diferencia con MTF guardarrail:
  MTF:            1W/1D dan dirección maestra, 4H/2H confirman
  Alta convicción: 4H da señal, 2H confirma con cruce EMA + ruptura fractal
  Son capas distintas — se acumulan, no se reemplazan.
```
*(K-7 pendiente de implementar en calcular_score())*

#### Las EMAs en el MTF — cómo detectar tendencia viva
```
sep = (EMA10 − EMA55) / EMA55 × 100   ← separación porcentual

sep > +1% Y mom > 0  → tendencia alcista VIVA
sep < −1% Y mom < 0  → tendencia bajista VIVA
abs(sep) < 1%        → compresión (la fiesta terminando)

Las EMAs NO se usan para detectar el cruce (eso llega tarde).
Se usan para saber si la tendencia sigue activa.
```

---

<a name="parte-iv"></a>
## PARTE IV — SETUPS DE ENTRADA

---

<a name="iv-a-entradas-short"></a>
### IV-A. ENTRADAS SHORT — Todos los patrones

> **Jerarquía de entradas SHORT de mayor a menor convicción:**

#### Nivel 1 — MÁXIMA CONVICCIÓN: K-8 Último Estirón ✅ Implementado v3.4
```
Señales: squeeze ya negativo + precio toca resistencia
Score esperado: ≤ −70 (casi garantizado SHORT)
Acción: entrar SHORT inmediatamente o tener orden límite en la resistencia
```

#### Nivel 2 — ALTA CONVICCIÓN: La Trinidad (K-1)
```
Señales: squeeze negativo + trendline acompañando + precio rebota en trendline
Secuencia exacta:
  1. Squeeze momentum indica SHORT
  2. Trendline de resistencia está cerca del precio
  3. Precio toca la trendline y en 4H se ve el rechazo (mecha o cierre lejos)
  4. → ENTRAR SHORT inmediatamente
```

#### Nivel 3 — ALTA CONVICCIÓN: K-7 Multi-timeframe
```
Señales: 4H squeeze bajista + 2H EMA cruce + 2H fractal roto
Cuando los 3 timeframes confirman → entrar con mayor confianza
```
*(K-7 pendiente en calcular_score())*

#### Nivel 4 — VÁLIDA CON CUIDADO: K-9 Segunda Confirmación ✅ Implementado v3.4
```
Señales: EMA cruce bajista (roja > azul) + squeeze negativo
Nota: entrada más tardía → el precio ya cayó algo → menor profit potencial
"Ya vamos con más cuidado" — Eduardo
Score adicional: −15 pts

CUÁNDO NO APLICA K-9:
  - Si el precio ya recorrió la mayor parte de la caída esperada
  - Si ya tocó la trendline de soporte inferior (objetivo K-6)
  - Si el squeeze está en valle profundo (impulso bajista agotándose)
```

#### Nivel 5 — MÍNIMA: Solo squeeze negativo
```
Sin S/R, sin EMA cruce → esperar más señales antes de entrar
El squeeze solo no es suficiente para una entrada de alta convicción
```

---

<a name="iv-b-entradas-long"></a>
### IV-B. ENTRADAS LONG — Todos los patrones

#### Nivel 1 — MÁXIMA CONVICCIÓN: La Trinidad alcista (K-1 espejo)
```
Señales: squeeze positivo + trendline de soporte acompañando + precio rebota en soporte
Secuencia:
  1. Squeeze momentum indica LONG (bull_valley o bull_accel)
  2. Trendline de soporte está cerca del precio actual
  3. Precio toca el soporte y rebota (mecha o cierre alejado del nivel)
  4. → ENTRAR LONG inmediatamente
```

#### Nivel 2 — ALTA CONVICCIÓN: Resistencia rota
```
Señales: precio rompe resistencia hacia arriba + squeeze positivo
Score adicional: +25 pts (breakout alcista)
Nota: el techo roto se convierte en soporte — el camino queda despejado
```

#### Nivel 3 — VÁLIDA: Segunda confirmación alcista
```
Señales: EMA azul (10) cruza encima de roja (55) + squeeze positivo
Mismo principio que K-9 pero para LONG
```

---

<a name="iv-c-metodo-rafaga"></a>
### IV-C. MÉTODO RÁFAGA — Entradas escalonadas en soporte con apalancamiento alto
*(Creado por Eduardo Andrade, 28 mayo 2026 — validado en experimento real BTCUSDT)*

#### Concepto
```
En lugar de entrar con todo el capital en un solo precio,
se programan 5 entradas escalonadas entre el precio actual y el soporte.
Si el precio baja antes de rebotar → las entradas adicionales mejoran el promedio.
Si el precio sube directo → solo E1 se llena → pérdida de oportunidad controlada.
```

#### Parámetros fijos del método
| Parámetro | Valor |
|---|---|
| Número de entradas | **5** |
| Capital total | **50%** del capital disponible |
| Apalancamiento | **70x** |
| Distribución | Escalonadas desde precio actual hasta el soporte |
| SL | Por debajo del soporte — **mismo nivel para todas** |
| TP | Nivel técnico real (EMA55 o resistencia) — **mismo para todas** |
| SL/TP | **Integrados en cada orden LIMIT desde el momento de programarlas** |

#### Condiciones obligatorias para activar el método
```
1. Soporte claro y probado debajo del precio actual
   → Sin soporte definido = NO usar el método
2. SL por debajo de ese soporte (si el soporte rompe = salir)
3. TP en un nivel técnico real hacia arriba (EMA55, resistencia)
   → Sin TP técnico definido = NO usar el método
4. Contexto alcista activo (K-2.5, K-10 o acumulación visible)
5. Capital disponible suficiente para las 5 entradas al 50%
```

#### Cómo se programa
```
PASO 1: Identificar soporte y resistencia/target
PASO 2: E1 = precio actual (entrada inmediata, puede ser manual)
PASO 3: Dividir la distancia entre E1 y el soporte en 4 partes iguales
         → E2, E3, E4, E5 espaciadas uniformemente
PASO 4: Calcular tamaño de cada entrada:
         (50% capital × apalancamiento) / precio / 5 entradas
PASO 5: Programar E2-E5 como órdenes LIMIT con SL y TP integrados
PASO 6: El SL de E1 (si es manual) se pone desde la app inmediatamente
```

#### Ejemplo real validado (28 mayo 2026 — BTCUSDT)
```
Soporte:  $72,000  |  Target (EMA55 1W): $84,000
E1: $73,401.7 — manual
E2: $73,101.3 — limit
E3: $72,800.9 — limit  ← se llenó (BTC bajó hasta aquí)
E4: $72,500.5 — limit  ← no se llenó
E5: $72,200.0 — limit  ← no se llenó

Resultado: 3 de 5 entradas llenadas → promedio bajó de $73,401 a $73,063
           PnL con BTC en $73,710: +$3.64 USDT (+62.37% apalancado)
           Sin la ráfaga: E1 sola hubiera estado en breakeven
```

#### Gestión de la posición una vez activa — PARTE OBLIGATORIA del método
```
FASE 1 — Gestión del SL según estado del Squeeze Momentum

  ⚠️ REGLA CRÍTICA (Eduardo, 29 mayo 2026 — lección del Experimento #1):
  "Si el Squeeze Momentum sigue señalando continuación en la dirección del trade,
   NO mover el SL tan ajustado. La espera vale la pena."

  SI el Squeeze sigue alcista (para LONG) / bajista (para SHORT):
  → Mantener el SL en el nivel de soporte original (aunque implique pequeña pérdida)
  → NO mover el SL solo para "asegurar $1" — el squeeze dice que el trade tiene más recorrido
  → Mover el SL ajustado en este momento = salir justo antes del movimiento grande

  SI el Squeeze empieza a GIRAR contra la posición:
  → Ahora sí mover el SL para proteger ganancia o minimizar pérdida
  → El giro del squeeze es la señal de que la tesis del trade está terminando

  REGLA CONCRETA:
  → Squeeze aún a favor  → SL en soporte original (puede ser pequeña pérdida)
  → Squeeze girando en contra → mover SL a breakeven o a +$1 neto
  → Squeeze claramente en contra → cerrar o dejar que SL actúe

FASE 2 — Asegurar ganancia mínima (solo cuando Squeeze gira)
  Cuando el squeeze empieza a debilitarse o girar:
  → Mover el SL por encima del breakeven
  → Objetivo: garantizar mínimo +$1 neto
  → Cálculo: SL = (1.0 + entry_avg × contracts) / (contracts × 0.9995)

FASE 3 — Dejar correr con trailing stop (si el mercado sigue fuerte)
  Si el squeeze sigue fuerte a favor:
  → Activar trailing stop para capturar más ganancia
  → El trailing stop sube con el precio y protege ganancias crecientes
  → Sin trailing → mantener el TP fijo en el nivel técnico

FILOSOFÍA:
  "Primero nos aseguramos una pequeña ganancia,
   luego vemos si podemos asegurar más." — Eduardo Andrade
  PERO: si el squeeze sigue a favor, la paciencia vale más que el $1 asegurado.
```

#### Lo que NO es el Método Ráfaga
```
✗ No es para entrar sin soporte definido
✗ No es para usar con todo el capital (máx 50%)
✗ No es para apalancamientos bajos (el beneficio del promedio es mayor con alto leverage)
✗ No es para mercados en tendencia bajista confirmada (solo en rebotes de soporte)
```

#### Fase de autonomía actual
```
FASE ACTUAL: Ejecución conjunta Eduardo + Claude.
Eduardo identifica el setup → avisa → Claude programa las 5 entradas.
La autonomía total (bot ejecuta solo) se activa cuando Eduardo lo autorice.
Hasta ese momento: ninguna Ráfaga se lanza sin instrucción directa de Eduardo.
```

#### Experimentos registrados
```
Experimento #1 — 28-29 mayo 2026 — CERRADO → ver PARTE VIII
Experimento #2 — 29 mayo 2026    — EN CURSO (E1 @ $73,751.6 | SL $72,500 | TP $75,600)
```

---

<a name="iv-d-rdenes-en-espera"></a>
### IV-D. ÓRDENES EN ESPERA — Cómo colocar órdenes límite

> **Eduardo enseñó (27 mayo 2026): la orden límite es la forma inteligente de entrar.**

#### Concepto
```
En lugar de entrar al precio actual (orden market), se pone una orden LÍMITE
en el nivel exacto donde se espera que llegue el precio.
Beneficio: si el precio llega → ejecución automática al precio ideal.
           si no llega → no se entra → se evita una entrada mala.
```

#### Cuándo usar órdenes en espera — SHORT
```
Situación: precio viene cayendo, da un rebote, se aproxima a la resistencia.
           Se sabe que hay posibilidad de que toque la resistencia (K-8).

Acción: colocar orden LÍMITE SHORT en el nivel exacto de la resistencia.
        Si el precio llega y toca → SHORT se activa automáticamente.
        Si el precio no llega y gira antes → la orden no se ejecuta (sin pérdida).

Ventaja: Eduardo no tiene que estar mirando el gráfico en ese momento exacto.
         El bot ya tiene la orden puesta esperando.
```

#### Cuándo usar órdenes en espera — LONG
```
Situación: precio en caída, se aproxima a un soporte conocido.
           Se espera rebote en el soporte.

Acción: colocar orden LÍMITE LONG en el nivel del soporte.
        Si el precio toca y rebota → LONG se activa.
```

#### Regla de seguridad
```
La orden en espera SIEMPRE lleva su Stop Loss definido antes de colocarla.
Sin Stop Loss definido → no se coloca la orden.
```

*(Implementación de órdenes límite automáticas: pendiente en bot loop)*

---

<a name="iv-d-movimientos-flash"></a>
### IV-D. MOVIMIENTOS FLASH — Precio toca S/R rápidamente

> **Eduardo enseñó (27 mayo 2026): el flash es cuando el precio llega rápido al nivel donde ya tienes tu orden.**

#### Concepto
```
Un movimiento flash es cuando el precio sube o baja bruscamente y rápidamente
hasta tocar una resistencia o un soporte — y YA TIENES una posición o una orden
colocada en ese nivel exacto.

Ejemplo SHORT:
  Tienes orden límite SHORT en la resistencia en $95,000.
  El precio sube de $91,000 a $95,000 en 1 vela (flash alcista).
  Tu orden se ejecuta automáticamente en el techo.
  El flash te da la entrada perfecta sin tener que reaccionar.

Ejemplo LONG:
  Tienes orden límite LONG en el soporte en $88,000.
  El precio cae rápido de $92,000 a $88,000 (flash bajista).
  Tu orden se ejecuta en el piso.
```

#### Por qué los flashes son oportunidades
```
El precio que se mueve rápido hacia un nivel de S/R no lo "rompe" de verdad —
llega en pánico o euforia, toca el nivel, y rebota.
Si ya tienes la orden puesta → captura exactamente ese toque.
Si no tienes la orden → ya es tarde para entrar cuando lo ves.

Por eso Eduardo prepara sus órdenes ANTES de que el precio llegue.
```

#### Regla del bot para flashes
```
Si el precio llega a la resistencia/soporte en menos de 2 velas (movimiento rápido)
Y la tendencia previa era contraria → el toque es aún más probable de rebotar.
El flash confirma el nivel como válido.
```

*(Detección de movimiento flash: pendiente en bot loop)*

---

<a name="parte-v"></a>
## PARTE V — GESTIÓN DE POSICIÓN
### Stop Loss, Trailing, Salidas y Re-entradas

#### Prioridad de salidas (orden en bot loop)
```
1. STOP LOSS FIJO          → protección máxima pérdida (configurado por usuario)
2. EMA55 TOQUE (K-2.2)     → siempre cerrar SHORT si precio toca EMA55
3. TRENDLINE SOPORTE (K-6) → objetivo de precio alcanzado (pendiente de implementar)
4. TRAILING STOP           → captura ganancia cuando el precio rebota
5. CIERRE COMPRESIÓN EMA   → EMAs apretándose = "la fiesta termina"
6. CIERRE ZONA WAIT        → score entre −70 y +70 = señal débil
```

#### Stop Loss
```
Parámetro: stop_loss_pct (default: 5%)
Regla del 2%: con pct_capital=5%, stop_loss=5%, apalancamiento=10x
              → riesgo real por trade = 5% × 5% × 10 = 2.5% del capital total
              → dentro del rango profesional de gestión de riesgo
```

#### EMA55 como exit — K-2.2 ✅ Implementado
```
Tolerancia de toque: precio dentro del 0.5% de EMA55 = "tocó"
Aplica: SOLO para posiciones SHORT
Siempre: sin condiciones de distancia ni de ganancia
```

#### Trendline de soporte como exit target — K-6 (Eduardo, 26 mayo 2026)
```
Al abrir SHORT: identificar la trendline de soporte más cercana DEBAJO del precio.
Cuando precio toque esa trendline → cerrar SHORT (es el "impacto" esperado).

Setup visual:
  ─ ─ ─ ─ ─ ─ ─  resistencia  ← ENTRADA SHORT aquí
       │
       │  precio viaja dentro del canal
        ╲
         ╲  trendline soporte ← OBJETIVO DE SALIDA (impacto)
```
*(K-6 pendiente de implementar en bot loop)*

#### Trailing Stop
```
Se activa cuando: profit ≥ trailing_activacion%
Se cierra cuando: retroceso ≥ trailing_distancia%
Parámetros actuales: activacion=3%, distancia=1.5%
Filosofía: captura la ganancia cuando el precio rebota, sin esperar el valle perfecto.
```

#### K-2.5 — EMA 55 como OBJETIVO cuando el precio está DEBAJO de ella
*(Dictado por Eduardo, 27 mayo 2026 — análisis en vivo BTCUSDT 1W)*

```
CONCEPTO: El imán de la EMA 55 funciona en AMBAS DIRECCIONES.

Ya sabíamos (K-2.2): precio ENCIMA de EMA55 + tendencia bajista
→ el precio cae y TOCA la EMA55 → rebote ~90% → cerrar SHORT ahí

NUEVO (K-2.5): precio DEBAJO de EMA55 + acumulación de longs (K-10)
→ la EMA55 ATRAE el precio desde abajo → es el OBJETIVO del LONG

REGLA:
  Cuando el precio está debajo de la EMA 55:
  → La EMA 55 en el timeframe relevante ES el target del movimiento LONG
  → No esperar más allá de ese nivel — ahí el precio probablemente se frena

TARGETS POR TIMEFRAME:
  4H EMA55: target a corto plazo (horas)
  1D EMA55: target a mediano plazo (días)
  1W EMA55: target a largo plazo (semanas) — movimiento más grande

EJEMPLO REAL (Eduardo, 27 mayo 2026):
  BTCUSDT 1W — precio actual ~$75,000
  EMA 55 semanal (roja): ~$84,000
  → Eduardo entra LONG desde ~$75,000
  → Target: ~$84,000 (toque de EMA55 semanal)
  → Movimiento esperado: ~+12% en precio

La lógica completa del trade de Eduardo:
  1. Precio debajo de EMA55 semanal (imán activo hacia arriba)
  2. Longs acumulando en $75,000 con volumen (K-10)
  3. Fuerza vendedora insuficiente para romper hacia abajo
  4. Target natural: EMA55 semanal en ~$84,000

La misma física del mercado en ambos lados:
  K-2.2: precio encima → cae a tocar EMA55 (imán desde arriba)
  K-2.5: precio debajo → sube a tocar EMA55 (imán desde abajo)
```

*(K-2.5 pendiente en bot loop: calcular EMA55 del TF de contexto como take profit automático)*

---

#### Re-entrada después de EMA55 — K-2.3
```
Situación: cerré SHORT en EMA55. El precio rebotó (como esperaba). El rebote termina.
Acción: RE-ENTRAR en SHORT si el squeeze sigue negativo (tendencia principal intacta).
Razón: el rebote fue un respiro, no un giro. Re-entrar da un precio MEJOR que el original.
Confirmación: squeeze momentum NO giró al alza durante el rebote.
```
*(K-2.3 pendiente de implementar en bot loop)*

---

<a name="parte-vi"></a>
## PARTE VI — SISTEMA TÉCNICO DE SCORING

### Tabla de Scoring Congelada — v3.4
*(Esta tabla es la ley. Cambiarla requiere Protocolo L99 completo.)*

| # | Indicador | Condición | Puntos | Justificación |
|---|-----------|-----------|--------|---------------|
| 1 | EMA slope fuerte | Acelerando al alza | +30 | Tendencia ganando fuerza |
| 2 | EMA slope fuerte | Acelerando a la baja | −30 | Tendencia ganando fuerza |
| 3 | EMA slope débil | Positivo sin acelerar | +8 | EMA reactiva, peso reducido |
| 4 | EMA slope débil | Negativo sin acelerar | −8 | EMA reactiva, peso reducido |
| 5 | Squeeze bear_peak | Máximo local de momentum | −40 | Señal MÁS anticipatoria de SHORT |
| 6 | Squeeze bull_valley | Mínimo local de momentum | +40 | Señal MÁS anticipatoria de LONG |
| 7 | Squeeze bear_post_peak | 3 barras declinando, positivo | −25 | Post-techo: giro ya pasó |
| 8 | Squeeze bull_post_valley | 3 barras subiendo, negativo | +25 | Post-fondo: giro ya pasó |
| 9 | Squeeze bear_accel | Momentum < 0 y acelerando | −30 | Caída confirmada |
| 10 | Squeeze bull_accel | Momentum > 0 y acelerando | +30 | Subida confirmada |
| 11 | Squeeze positivo creciendo | mom > 0 y subiendo | +10 | Fuerza alcista leve |
| 12 | **Squeeze positivo cayendo** | mom > 0 y bajando | **−10** | Perdiendo fuerza = bajista |
| 13 | Squeeze negativo subiendo | mom < 0 y recuperándose | +10 | Posible giro alcista |
| 14 | Squeeze negativo cayendo | mom < 0 y bajando | −10 | Bajista leve |
| 15 | S/R soporte cercano | Precio 0–1.5% sobre soporte | +20 | Rebote probable |
| 16 | S/R resistencia cercana | Precio 0–1.5% bajo resistencia | −20 | Rechazo probable |
| 17 | S/R breakout bajista | Soporte roto (0–5% abajo) | −25 | Caída más fuerte y sostenida |
| 18 | S/R breakout alcista | Resistencia rota (0–5% arriba) | +25 | Techo = nuevo soporte |
| 19 | Volume Profile POC | Precio sobre POC | +10 | Zona de mayor volumen = soporte |
| 20 | Volume Profile POC | Precio bajo POC | −10 | Zona de mayor volumen = resistencia |
| 21 | Cross-confirm SHORT | bear_peak + resistencia | −18 | Squeeze gira EN nivel clave |
| 22 | Cross-confirm LONG | bull_valley + soporte | +18 | Squeeze gira EN nivel clave |
| 23 | ADX emergente | min10 < 20, ahora creciendo | ±10 | Tendencia naciendo |
| 24 | ADX fuerte | ≥25 y creciendo | ±5 | Tendencia madura |
| 25 | ADX sin fuerza | < 20 | −5 | Sin tendencia |
| 26 | **K-8 Último estirón** | Resistencia + tendencia bajista | **−20** | Trampa confirmada |
| 27 | **K-9 Segunda confirmación** | EMA cruce + squeeze negativo | **−15** | Entrada tardía válida |

**Umbral de entrada:** score ≥ +70 → LONG / score ≤ −70 → SHORT

---

### Escenarios Canónicos — Los 7 casos que SIEMPRE deben pasar

#### Escenario 1 — SHORT en techo (el caso original de Eduardo)
```
Situación:  BTC 4H. bear_peak exacto. Precio en resistencia. EMA débil. ADX ~18.
Esperado:   Score ≤ −70 → CORTO
Cálculo:    +8 (EMA) −40 (bear_peak) +10 (POC) −20 (resistencia) −18 (cross) −10 (ADX) = −70
```

#### Escenario 2 — SHORT post-techo
```
Situación:  Peak fue hace 1-2 barras. Momentum positivo pero declinando. Precio en resistencia.
Esperado:   Score entre −30 y −55 → ESPERAR con sesgo bajista
Cálculo:    +8 (EMA) −25 (post_peak) +10 (POC) −20 (resistencia) −5 (ADX) = −32
```

#### Escenario 3 — SHORT con soporte roto
```
Situación:  Squeeze bear_accel. Precio rompió soporte testeado 2-3 veces. EMA negativa.
Esperado:   Score ≤ −70 → CORTO
Cálculo:    −8 (EMA) −30 (bear_accel) −10 (POC) −25 (breakout) = −73
```

#### Escenario 4 — LONG con resistencia rota
```
Situación:  Squeeze bull_accel. Precio rompió resistencia. EMA acelerando al alza.
Esperado:   Score ≥ +70 → LARGO
Cálculo:    +30 (EMA fuerte) +30 (bull_accel) +10 (POC) +25 (breakout) = +95
```

#### Escenario 5 — ESPERAR (compresión neutral)
```
Situación:  Squeeze cerca de cero. EMAs juntas. ADX < 20. Sin S/R relevante.
Esperado:   Score entre −25 y +25 → ESPERAR
```

#### Escenario 6 — LONG fuerte en fondo de squeeze
```
Situación:  bull_valley exacto. Precio en soporte. ADX emergente.
Esperado:   Score ≥ +70 → LARGO
Cálculo:    +8 (EMA) +40 (bull_valley) +10 (POC) +20 (soporte) +18 (cross) +10 (ADX) = +106 → cap +100
```

#### Escenario 7 — Precio probando soporte, mercado indeciso
```
Situación:  Precio sobre soporte. Squeeze positivo pero cayendo. Sin ADX.
Esperado:   Score entre +10 y +30 → ESPERAR (no suficiente para LONG)
Cálculo:    −10 (squeeze positivo cayendo) +20 (soporte) −10 (POC) = 0
Regla:      El soporte solo (+20) no basta para llegar a +70. Necesita más señales.
```

---

### Conflictos conocidos y su resolución

| Conflicto | Regla A | Regla B | Resolución |
|-----------|---------|---------|------------|
| EMA positivo + Squeeze cayendo | +8 | −10 | Net −2. CORRECTO — mercado mixto. |
| Soporte + bear_peak | +20 | −40 | Net −20. CORRECTO — momentum gana sobre precio estático. |
| ADX fuerte con score = 0 | ±5 | Score neutral | ADX no amplifica sin dirección. CORRECTO. |

---

### Historial de versiones del score

| Versión | Fecha | Cambio | Motivo |
|---------|-------|--------|--------|
| v1.0 | Mar 2026 | Score básico EMA + ADX + POC | Primera versión |
| v2.0 | Abr 2026 | Squeeze Momentum | Bot no detectaba giros |
| v3.0 | May 2026 | MTF guardarrail + score anticipatorio | Entradas tardías |
| v3.1 | May 2026 | bear_peak −40, ADX direction-aware, S/R 1.5% | BTC SHORT tarde |
| v3.2 | May 2026 | bear_post_peak −25, positivo-cayendo = −10 | Score +3 cuando debía ser −32 |
| v3.3 | May 2026 | S/R breakout: −25 / +25 | "Si rompe el soporte, caída más fuerte" |
| v3.4 | May 2026 | K-8 último estirón −20, K-9 segunda conf. −15 | Eduardo: patrones reales BTCUSDT |

---

<a name="parte-vii"></a>
## PARTE VII — PREGUNTAS PENDIENTES

---

## CONOCIMIENTO ADICIONAL — BLOQUES K (continuación)

---

### BLOQUE K-10: VOLUMEN DE ACUMULACIÓN EN SOPORTE — LONGS POSICIONÁNDOSE
*(Dictado por Eduardo, 27 mayo 2026 — análisis en vivo BTCUSDT ~$75,000)*

```
CONCEPTO: El volumen revela la INTENCIÓN del mercado, no solo la dirección.

PATRÓN: precio llega a un nivel + volumen razonable en esa zona + longs acumulando
→ El nivel va a aguantar → el precio va a subir → LONG

SEÑAL CONCRETA:
  1. El precio llega a una zona de soporte o nodo de alto volumen (Volume Profile)
  2. Se observa volumen significativo de operaciones en ese nivel exacto
  3. Los compradores (longs) se están "acomodando" — posicionándose para entrar
  → Esto indica que el dinero real está comprando ahí
  → El nivel tiene soporte real, no solo técnico

POR QUÉ ES IMPORTANTE:
  Los timeframes altos (1W, 1D) pueden mostrar squeeze bajista.
  Pero si el VOLUMEN en el precio actual muestra acumulación de longs:
  → La fuerza vendedora NO es suficiente para romper ese nivel
  → Los compradores absorben la presión vendedora
  → El precio va a rebotar desde ahí

CÓMO SE VE EN EL GRÁFICO:
  - Volume Profile (VRVP) muestra un nodo de alto volumen en el nivel actual
  - Velas de consolidación (no de caída libre) en ese nivel
  - Precio toca el nivel y NO lo rompe con fuerza — se mantiene

CUÁNDO APLICA:
  - Precio en zona de soporte conocido O en nodo de alto volumen del VP
  - Volumen razonable de operaciones en ese precio exacto
  - Señal de acumulación visible (longs entrando, no saliendo)

CUÁNDO NO APLICA:
  - Volumen bajo en el nivel → nadie está comprando → el soporte no es real
  - Precio rompe el nivel con volumen alto → capitulación → NO es acumulación
  - Tendencia macro extremadamente fuerte en contra (ej. 1W crash)

REGLA DE EDUARDO (27 mayo 2026):
  "Los que van en LONG se están acomodando para entrar y creo que voy a entrar yo también.
   El volumen también lo está confirmando — justo ahí donde está el precio hay
   un volumen razonable de operaciones."

EJEMPLO REAL (Eduardo, 27 mayo 2026):
  BTCUSDT ~$75,000
  1W squeeze: profundamente negativo (bajista macro)
  1D squeeze: post-peak, girando a negativo
  4H squeeze: rebotó, tocó resistencia, ahora pequeñas barras rojas
  2H squeeze: girando negativo
  → Análisis solo por squeeze = SHORT (lo que dijo Claude)
  → Eduardo corrige: el VOLUMEN muestra acumulación de longs en $75,000
  → La fuerza vendedora no es suficiente para llegar a $70-71k
  → Eduardo entra LONG desde $75,000
  LECCIÓN: el volumen pesa más que los timeframes altos cuando muestra acumulación activa
```

**Cómo afecta al scoring — implementación pendiente:**
```
Condición nueva:
  SI precio está en nodo de alto volumen (±1% del POC) Y precio en soporte:
  → bonus LONG adicional (el volumen confirma que el soporte es real)
  → reducir peso de señales SHORT de timeframes altos cuando hay acumulación visible

Posibles puntos: +15 a +20 pts cuando precio en POC + soporte simultáneamente
(actualmente el POC ya da +10 pts — este bonus sería ADICIONAL por confluencia)
```
*(K-10 pendiente de implementar — requiere detectar acumulación vs distribución en volumen)*
*(Se responden conforme Eduardo las dicte en sesiones reales)*

- [ ] ¿La EMA 10 (azul) también da rebotes o solo la EMA 55 (roja)?
- [ ] ¿Qué pasa si squeeze y trendline van en direcciones opuestas? ¿Cuál gana?
- [ ] Tamaño de posición en re-entrada vs entrada original — ¿igual o diferente?
- [ ] ¿Cómo manejar múltiples activos cuando todos dan señal al mismo tiempo?

---

## IMPLEMENTACIONES PENDIENTES EN CÓDIGO

| Bloque | Descripción | Archivo | Estado |
|--------|-------------|---------|--------|
| K-4 | Cruce de EMAs como bonus en calcular_score() | main.py | ⏳ Pendiente |
| K-5 | Ruptura de fractal como confirmación | main.py | ⏳ Pendiente |
| K-6 | Trendline soporte como exit target en bot loop | main.py | ⏳ Pendiente |
| K-2.3 | Re-entrada SHORT después de rebote EMA55 | main.py | ⏳ Pendiente |
| K-2.5 | EMA55 como target LONG cuando precio está debajo — TF contexto (1D/1W) | main.py | ⏳ Pendiente |
| K-10 | Volumen acumulación en soporte — longs posicionándose = bonus LONG | main.py | ⏳ Pendiente |
| K-7 | Alta convicción 4H+2H como bonus de score | main.py | ⏳ Pendiente |
| IV-C | Órdenes límite automáticas en resistencia/soporte | main.py | ⏳ Pendiente |
| IV-D | Detección de movimiento flash | main.py | ⏳ Pendiente |

---

<a name="parte-viii"></a>
## PARTE VIII — EXPERIMENTOS

> **Un experimento es una táctica nueva que se prueba en condiciones reales antes de convertirse en regla.**
> Se registra con: hipótesis, configuración exacta, resultado y lección aprendida.
> Los experimentos exitosos pasan a PARTE IV. Los fallidos se conservan como lección.

---

### EXPERIMENTO #1 — Método Ráfaga 50%-70x
*(Iniciado por Eduardo Andrade, 27-28 mayo 2026)*

#### Hipótesis
```
Si el precio va a rebotar desde una zona de soporte importante,
escalonar 5 entradas LONG entre el precio actual y el soporte
permite capturar el movimiento aunque el precio caiga un poco más
antes de rebotar. El promedio de entrada mejora con cada llenado.
```

#### Configuración del experimento
```
Activo:        BTC/USDT perpetuo (BingX)
Dirección:     LONG
Apalancamiento: 70x
Capital:       ~50% del capital disponible
N° entradas:   5 (E1 manual + E2-E5 limit automáticas)
SL global:     $72,000 (para todas las entradas)
TP global:     $84,000 (para todas las entradas) ← EMA55 semanal (K-2.5)
```

| Entrada | Precio | Tamaño | Tipo | Estado |
|---------|--------|--------|------|--------|
| E1 | $73,401.7 | 0.0014 BTC | Manual (Eduardo) | ✅ Abierta |
| E2 | $73,101.3 | 0.0021 BTC | Limit + SL/TP integrados | ⏳ Esperando |
| E3 | $72,800.9 | 0.0021 BTC | Limit + SL/TP integrados | ⏳ Esperando |
| E4 | $72,500.5 | 0.0021 BTC | Limit + SL/TP integrados | ⏳ Esperando |
| E5 | $72,200.0 | 0.0021 BTC | Limit + SL/TP integrados | ⏳ Esperando |

#### Lógica de las entradas
```
La separación entre entradas es ~$300 — suficiente para que
cada una capture un nivel distinto de la caída.
Si el precio llega a E5 ($72,200) y no rompe $72,000 →
el soporte es real y todas las entradas activas están bien posicionadas.
Si el SL ($72,000) se activa → pérdida controlada en cada entrada.
```

#### Contexto de mercado al iniciar
```
BTC precio: ~$73,355
Contexto:   Precio debajo de EMA55 semanal (~$84,000) → imán activo hacia arriba (K-2.5)
            Longs acumulando en zona $72,000-$73,500 (K-10)
            Soporte conocido: $72,000-$72,200
TP target:  EMA55 semanal ~$84,000 (+14.8% desde zona de entrada)
Riesgo:     SL en $72,000 → máx pérdida si todas se llenan = pérdida controlada
```

#### Lecciones técnicas durante setup
```
1. BingX permite SL/TP integrados en órdenes LIMIT desde el API
   → Colocarlos siempre en el mismo llamado, no en monitor separado
2. Las órdenes SL/TP de una posición YA ABIERTA requieren llamadas separadas
   (no se pueden adjuntar retroactivamente a una posición existente)
3. El monitor automático post-llenado fue un workaround incorrecto
   → La solución correcta: integrar SL/TP en cada limit order desde el origen
```

#### Resultado
```
Estado:    CERRADO (29 mayo 2026 — 02:42)
Validado:  SÍ — táctica graduada a oficial

PnL neto:  +$0.895 USDT (ganancia pequeña)
Cierre:    SL activado en $73,300 → precio bajó a $72,563 → rebotó a $73,779
           = Stop hunt clásico. Nos sacaron justo antes del rebote.

LECCIÓN CLAVE (Eduardo, 29 mayo 2026):
  El Squeeze Momentum seguía señalando alcista cuando movimos el SL a $73,300.
  Esa fue la señal de que el trade tenía más recorrido.
  Si el squeeze sigue a favor → mantener SL en soporte original, no ajustar.
  Solo ajustar el SL cuando el squeeze empiece a girar en contra.
  La paciencia cuando el squeeze confirma vale más que asegurar $1.
```

---

### EXPERIMENTO #2 — Método Ráfaga #2
*(Iniciado por Eduardo Andrade, 29 mayo 2026)*

#### Contexto
```
Después del Experimento #1 (stop hunt en $73,300), BTC rebotó desde $72,563.
Eduardo ve señal alcista en 4H: Squeeze girando + ADX con fuerza + rebote de trendline.
Decisión: aplicar Ráfaga de nuevo con SL más amplio (lección aprendida del #1).
```

#### Configuración
```
SL: $72,500  |  TP: $75,600  |  Apalancamiento: 70x  |  Capital: 50%
```

| Entrada | Precio | Tamaño | Tipo | Estado |
|---------|--------|--------|------|--------|
| E1 | $73,751.6 | 0.0019 BTC | Market inmediato | ✅ Abierta |
| E2 | $73,104.2 | 0.0019 BTC | Limit + SL/TP integrados | ⏳ Esperando |
| E3 | $72,936.2 | 0.0019 BTC | Limit + SL/TP integrados | ⏳ Esperando |
| E4 | $72,768.2 | 0.0019 BTC | Limit + SL/TP integrados | ⏳ Esperando |
| E5 | $72,600.2 | 0.0019 BTC | Limit + SL/TP integrados | ⏳ Esperando |

#### Diferencias respecto al Experimento #1
```
1. SL más amplio ($72,500 vs $72,000 original) — aplica lección del squeeze
2. E1 entró a mercado (no manual desde app)
3. E2-E5 con espaciado comprimido (~$168 por bug de detección de fill)
   → En próxima Ráfaga: verificar fill real de E1 antes de calcular E2-E5
4. TP más conservador ($75,600 vs $84,000) — objetivo técnico más cercano
```

#### Escenario de contingencia — Lateral (Eduardo, 29 mayo 2026)
```
Si el precio NO rompe al alza desde la zona actual (~$73,700):
→ Puede hacer un LATERAL dentro del rango $72,800 — $73,900
→ En ese caso: salir en la parte ALTA del lateral (~$73,900)
→ No esperar el TP original ($75,600) si el precio se atasca en el rango

SEÑAL DE LATERAL:
  Precio oscila varias velas entre $72,800 y $73,900 sin romper ningún lado
  Squeeze se estabiliza sin girar al alza claramente

ACCIÓN SI HAY LATERAL:
  → Cerrar E1 (y las que hayan llenado) cuando precio toque $73,900 (techo del rango)
  → Cancelar E2-E5 pendientes si el lateral se confirma
  → No quedarse atrapado esperando $75,600 si el mercado no tiene fuerza

BIAS ACTUAL: Alcista — pero vigilando el recuadro $72,800-$73,900
```

#### Resultado
```
Estado:   EN CURSO (iniciado 29 mayo 2026)
Resultado: Pendiente
```

---

*Documento creado: mayo 2026 | Protocolo: L99*
*Autor del conocimiento: Eduardo Andrade — 10 años de trading profesional*
*Mantenedor técnico: Claude (Anthropic)*
*Última actualización: 28 mayo 2026 — Experimento #1 Método Ráfaga 50%-70x*
*Estructura reorganizada: 27 mayo 2026 — por orden de Eduardo Andrade*
