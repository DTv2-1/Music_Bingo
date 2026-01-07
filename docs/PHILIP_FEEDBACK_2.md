# Philip's Feedback 2 - PDF y Lógica de Juego

## Fecha: 7 de enero de 2026

---

## 📋 Comentarios sobre las Tarjetas PDF

### 1. Agregar logo de Perfect DJ y sitio web ✅
**Requerimiento:**
- Agregar logo de Perfect DJ en el espacio central libre de cada tarjeta
- Agregar URL del sitio web
- Posición: Centro de la tarjeta (celda FREE)

**Tareas técnicas:**
- [x] Modificar `backend/generate_cards.py`
- [x] Agregar código para insertar logo en celda FREE
- [x] Agregar URL `www.perfectdj.co.uk` en celda FREE
- [x] Ajustar layout (logo arriba, FREE centro, URL abajo)
- [x] Manejo de errores si falta logo
- [ ] ⏸️ **BLOQUEADO:** Obtener logo de Perfect DJ (archivo PNG)
- [ ] ⏸️ **BLOQUEADO:** Confirmar URL correcta del sitio web

**Estado:** CÓDIGO LISTO - Esperando assets
- Logo path: `frontend/assets/perfectdj_logo.png`
- URL configurada: `www.perfectdj.co.uk`
- Layout de celda FREE:
  ```
  ┌─────────────────┐
  │  [LOGO] (20x8mm)│
  │      FREE       │
  │ www.perfectdj...│
  └─────────────────┘
  ```

**Archivos modificados:**
- ✅ `backend/generate_cards.py` - Código implementado

---

### 2. Agregar nombre del pub/bar en las tarjetas ✅
**Requerimiento:**
- Cada tarjeta debe mostrar el nombre del pub/bar
- Ejemplo: "Music Bingo at The Red Lion Pub"
- Debe ser configurable (diferente para cada cliente)

**Tareas técnicas:**
- [x] Modificar `backend/generate_cards.py` para aceptar parámetro `venue_name`
- [x] Agregar nombre del venue en el header de cada tarjeta
- [x] Leer `VENUE_NAME` desde `.env` por defecto
- [x] Aceptar venue name por línea de comandos
- [x] Crear endpoint API `/api/generate-cards` en backend
- [x] Agregar botón "Generate Cards" en frontend
- [x] Integración completa frontend → backend
- [x] Ajuste dinámico de font size si nombre es muy largo
- [x] Regenerar PDFs con nombre del venue

**Estado:** ✅ COMPLETADO
- Uso por línea de comandos: `python backend/generate_cards.py "The Golden Eagle"`
- Uso desde frontend: Botón "🎴 Generate Cards" en UI
- Header dinámico: "MUSIC BINGO at [Venue Name]"
- Default desde .env: "The Red Lion Pub"

**Archivos modificados:**
- ✅ `backend/generate_cards.py` - Sistema completo
- ✅ `backend/server.py` - Endpoint `/api/generate-cards`
- ✅ `frontend/game.html` - Botón de generación
- ✅ `frontend/game.js` - Función `generateCards()`
- ✅ `frontend/styles.css` - Estilos del botón
- ✅ `backend/.env` - VENUE_NAME existe

---

### 3. No repetir artistas - pero si se repite, mostrar artista + canción ✅
**Requerimiento actual:**
- Evitar repetir el mismo artista en el pool de canciones
- **PERO** si un artista se repite (inevitable con artistas populares):
  - Mostrar formato: "Artist - Song Title" cada vez
  - Ejemplo: "Queen - Bohemian Rhapsody" y "Queen - We Will Rock You"

**Tareas técnicas:**
- [x] Modificar `backend/generate_pool.py` para detectar artistas duplicados
- [x] Crear función `mark_duplicate_artists()` 
- [x] Marcar canciones con flag `has_duplicate_artist: true/false`
- [x] Modificar `backend/generate_cards.py` para usar formato condicional
- [x] Implementar lógica: duplicado → "Artist - Song"
- [x] Guardar info de duplicados en `pool.json`
- [x] Regenerar pool con flags
- [x] Regenerar cards con nuevo formato

**Estado:** ✅ COMPLETADO
- Pool actualizado: 257 canciones, 174 artistas únicos
- 32 artistas con múltiples canciones (115 songs total)
- Ejemplos detectados: Queen (múltiples), Bruno Mars (4), Coldplay (4)
- Flag `has_duplicate_artist` en todas las canciones
- Formato aplicado correctamente en tarjetas

**Archivos modificados:**
- ✅ `backend/generate_pool.py` - Función `mark_duplicate_artists()`
- ✅ `backend/generate_cards.py` - Lógica condicional
- ✅ `data/pool.json` - Estructura actualizada con flags

---

### 4. Si artista y canción son únicos, mostrar solo uno de los dos ✅
**Requerimiento:**
- Si un artista solo tiene UNA canción en el pool completo:
  - A veces mostrar solo el nombre del artista
  - A veces mostrar solo el título de la canción
  - Variar aleatoriamente (50/50)
- Objetivo: Hacer las tarjetas más interesantes y variadas

**Tareas técnicas:**
- [x] En `backend/generate_cards.py`, implementar lógica:
  - Si `has_duplicate_artist == false`: 50/50 artista o canción
  - Si `has_duplicate_artist == true`: SIEMPRE "Artist - Song"
- [x] Modificar función `format_song_for_card(song)` completa
- [x] Asegurar variedad en cada tarjeta
- [x] Testing con diferentes combinaciones
- [x] Regenerar cards con nuevo formato

**Estado:** ✅ COMPLETADO
- Lógica implementada en `format_song_for_card()`
- Artistas únicos: random.choice([artista, canción])
- Artistas duplicados: siempre "Artist - Song"
- Tarjetas tienen mezcla visual atractiva
- Testing realizado: funciona correctamente

**Ejemplo de resultado:**
```
Tarjeta típica:
┌──────────────────────┐
│ Queen - Bohemian...  │ ← Duplicado (siempre completo)
│ Aerosmith            │ ← Único (solo artista)
│ Dream On             │ ← Único (solo canción)
│ Bruno Mars - Uptown  │ ← Duplicado (siempre completo)
│ a-ha                 │ ← Único (solo artista)
└──────────────────────┘
```

**Archivos modificados:**
- ✅ `backend/generate_cards.py` - Función completa reescrita

---

### 5. Extender duración del clip de audio ✅
**Requerimiento:**
- Actual: 5 segundos por canción
- Solicitud: Extender un poco más
- **Duración confirmada: 8 segundos**

**Tareas técnicas:**
- [x] Confirmar con Philip duración deseada → 8 segundos
- [x] Modificar `frontend/game.js`:
  - Cambiar `CONFIG.PREVIEW_DURATION_MS` de 5000 a 8000 ms
- [x] Actualizar comentarios en código
- [x] Considerar límite iTunes preview (30 segundos máximo)

**Estado:** ✅ COMPLETADO
- Duración actualizada: 8 segundos por canción
- Compatible con iTunes preview (max 30s)
- Suficiente tiempo para reconocer la canción
- No demasiado largo para mantener ritmo del juego

**Archivos modificados:**
- ✅ `frontend/game.js` - `PREVIEW_DURATION_MS: 8000`

---

### 6. Sistema inteligente de cálculo de canciones según jugadores ✅
**Requerimiento:**
- Problema actual: 50 tarjetas con pocos jugadores = juego muy largo
- Solución: Calcular número óptimo de canciones según jugadores
- Ejemplos reales del sistema:
  - 10 jugadores → 60 canciones (~30 min)
  - 25 jugadores → 48 canciones (~24 min)
  - 40 jugadores → 36 canciones (~18 min)
  - 50 jugadores → 31 canciones (~15 min)

**Lógica implementada:**
```python
- Cada tarjeta tiene 24 números únicos (25 - 1 FREE)
- Pocos jugadores (≤10): 2.5x canciones por tarjeta = ~60 songs
- Grupo mediano (≤25): 2.0x canciones = ~48 songs
- Grupo grande (≤40): 1.5x canciones = ~36 songs
- Grupo muy grande (>40): 1.3x canciones = ~31 songs
- Ajuste por duración objetivo (default 45 min)
- Mínimo garantizado: 20 canciones
```

**Tareas técnicas:**
- [x] Crear función `calculate_optimal_songs()` en `generate_cards.py`
- [x] Crear función `estimate_game_duration()` para cálculo de tiempo
- [x] Agregar campo "Number of Players" en `frontend/game.html`
- [x] Mostrar estimación en tiempo real en UI
- [x] Actualizar función `generateCards()` para enviar num_players
- [x] Actualizar endpoint `/api/generate-cards` para recibir parámetros
- [x] Crear endpoint `/api/calculate-songs` para cálculos sin generar cards
- [x] Agregar event listener para actualizar estimación automáticamente
- [x] Validación (min 5, max 100 jugadores)
- [x] Testing con diferentes números de jugadores

**Estado:** ✅ COMPLETADO
- Sistema de cálculo implementado y probado
- UI muestra estimación en tiempo real: "~48 songs, 24 min"
- Actualización automática al cambiar número de jugadores
- Lógica basada en probabilidades de bingo reales
- Ajuste dinámico según tamaño del grupo
- Duración promedio: 30 segundos por canción (8s clip + 22s anuncio/pausa)

**Archivos modificados:**
- ✅ `backend/generate_cards.py` - Funciones de cálculo
- ✅ `backend/server.py` - Endpoints `/api/generate-cards` y `/api/calculate-songs`
- ✅ `frontend/game.html` - Campo de jugadores + estimación
- ✅ `frontend/game.js` - Cálculo y actualización automática
- ✅ `frontend/styles.css` - Estilos para campo numérico

---

## 📊 Resumen de Estado

### ✅ Tareas Completadas (6/6) - TODAS LAS FUNCIONALIDADES IMPLEMENTADAS:
1. ✅ **Nombre del venue en tarjetas** - Sistema completo con UI frontend
2. ✅ **Detección de artistas duplicados** - 32 artistas detectados, 115 canciones marcadas
3. ✅ **Formato condicional artistas únicos/duplicados** - Variedad visual en tarjetas
4. ✅ **Integración frontend-backend** - Generación de cards desde UI
5. ✅ **Duración de clips extendida** - 5s → 8s confirmado
6. ✅ **Sistema inteligente de cálculo jugadores→canciones** - Implementado y probado

### ⏳ Tareas Parcialmente Completas (esperando assets):
1. ⏳ **Logo y URL de Perfect DJ** - Código listo, esperando assets:
   - Necesita: archivo logo PNG (`frontend/assets/perfectdj_logo.png`)
   - Necesita: confirmar URL (`www.perfectdj.co.uk` configurada)

---

## 🎯 Orden de Implementación Sugerido

### ✅ Fase 1: COMPLETADA - TODAS LAS FUNCIONALIDADES CORE (6/6)
1. ✅ Implementar detección de artistas duplicados (`generate_pool.py`)
2. ✅ Implementar formato condicional en tarjetas (`generate_cards.py`)
3. ✅ Agregar nombre del venue en tarjetas (`generate_cards.py`)
4. ✅ Integración frontend con botón de generación
5. ✅ Extender duración de clips a 8 segundos
6. ✅ Sistema inteligente de cálculo de jugadores

### ⏳ Fase 2: Esperando assets de Philip (opcional)
7. ⏳ Agregar logo de Perfect DJ (código listo, necesita archivo PNG)
8. ⏳ Confirmar/actualizar URL del sitio web (actualmente: `www.perfectdj.co.uk`)

---

## 📝 Información Pendiente de Philip (opcional)

**Para completar logo/website:**
- [ ] Archivo de logo de Perfect DJ (.png recomendado, ~400x160 pixels)
- [ ] Confirmar URL del sitio web (actualmente configurada: `www.perfectdj.co.uk`)

**Opcional (mejoras visuales):**
- [ ] Tamaño/posición preferida del logo en tarjetas (actual: 20x8mm en celda FREE)
- [ ] Color/estilo de texto para URL del sitio web (actual: morado #667EEA, 5pt)

---

## 🔧 Archivos Modificados

**Backend:**
1. ✅ `backend/generate_pool.py` - Detectar artistas duplicados
2. ✅ `backend/generate_cards.py` - Logo, venue, formato condicional, cálculo de canciones
3. ✅ `backend/server.py` - Endpoints `/api/generate-cards` y `/api/calculate-songs`
4. ✅ `backend/.env` - VENUE_NAME configurado

**Frontend:**
5. ✅ `frontend/game.html` - Botón "Generate Cards", campo de jugadores, estimación
6. ✅ `frontend/game.js` - Funciones de cálculo, generación, duración 8s
7. ✅ `frontend/styles.css` - Estilos completos

**Data:**
8. ✅ `data/pool.json` - Estructura con flags `has_duplicate_artist`
9. ✅ `data/cards/music_bingo_cards.pdf` - Regenerado con nuevo formato

**Assets pendientes:**
10. ⏸️ `frontend/assets/perfectdj_logo.png` - Logo de Perfect DJ (esperando archivo)

---

## ✅ Criterios de Éxito

**✅ TODOS LOS CRITERIOS COMPLETADOS:**
- ✅ Tarjetas incluyen nombre del pub/bar (configurable desde UI)
- ✅ Artistas duplicados SIEMPRE muestran "Artist - Song"
- ✅ Artistas únicos muestran SOLO artista O SOLO canción (50/50 random)
- ✅ Pool actualizado: 257 canciones, 174 artistas únicos, 32 con duplicados
- ✅ Sistema de generación integrado en frontend
- ✅ Código para logo/website listo (esperando assets)
- ✅ Duración de clips ajustada: 8 segundos (confirmado por Philip)
- ✅ Sistema calcula canciones óptimas según jugadores
- ✅ Estimación de duración visible en la UI en tiempo real
- ✅ Juegos no son excesivamente largos con pocos jugadores
- ✅ Juegos tienen suficientes canciones para asegurar ganador

**Pendientes (solo assets opcionales):**
- ⏸️ Logo de Perfect DJ visible en tarjetas (código listo)
- ⏸️ URL confirmada del sitio web (configurada por defecto)

**Resultados actuales:**
- 50 tarjetas únicas generadas
- Tarjetas personalizables por venue desde UI
- Formato visual variado y atractivo
- Pool con detección inteligente de duplicados
- Footer con "Powered by Perfect DJ - perfectdj.co.uk"
- Clips de 8 segundos (60% más largo que antes)
- Sistema inteligente: 10 players=60 songs, 25 players=48 songs, 50 players=31 songs
- Estimación visible: "~48 songs, 24 min" actualizada automáticamente
