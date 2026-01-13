# 📋 Feedback de Philip Hill - 9 de Enero 2026

## 🐛 Errores Encontrados

### **1. Auto-inicio del Bingo** 🔴
**Problema**: El juego comienza automáticamente antes de que el usuario pueda configurar el nombre del pub.

**Impacto**: Confusión del usuario, experiencia no profesional

**Causa**: No existe pantalla de setup obligatoria. El juego se inicializa inmediatamente en `DOMContentLoaded`

**Solución**: Agregar modal/pantalla de configuración inicial que bloquee el inicio hasta completar setup

---

### **2. No se pueden agregar espacios en el nombre del pub** 🟡
**Problema**: Philip intentó escribir "The Admiral Rodney Southwell" pero no pudo agregar espacios.

**Estado**: ✅ **NO ES BUG DEL CÓDIGO**
- El input es `type="text"` sin restricciones
- La función `saveVenueName()` usa `.trim()` pero preserva espacios internos
- Código permite espacios correctamente

**Causa posible**: Problema del browser/teclado del usuario, no del sistema

**Solución**: Ninguna requerida en el código (probar en otro dispositivo)

---

### **3. Cálculo de canciones invertido** 🔴 CRÍTICO
**Problema**: El sistema calcula MENOS canciones cuando hay MÁS jugadores (lógica invertida)

**Evidencia**:
- Imagen muestra: "48 songs" pero "262 songs left to play"
- 40 jugadores → 36 canciones ❌
- 10 jugadores → 60 canciones ❌

**Comportamiento esperado**: 
- Debería ser ~3x el número de jugadores
- 10 jugadores → ~30 canciones ✅
- 40 jugadores → ~120 canciones ✅

**Causa**: Función `calculateOptimalSongs()` en `game.js` líneas 1045-1066
```javascript
// LÓGICA ACTUAL (INCORRECTA):
if (numPlayers <= 10) {
    baseSongs = 24 * 2.5; // 60 canciones
} else if (numPlayers <= 40) {
    baseSongs = 24 * 1.5; // 36 canciones (¡menos con más jugadores!)
}
```

**Solución**: Cambiar a fórmula `numPlayers × 3`

---

### **4. Voz TTS no es británica** 🟡
**Problema**: La voz actual suena americana, no británica. Los clientes de music bingo son británicos.

**Requerimiento**: Ofrecer voces británicas masculinas y femeninas

**Voces ElevenLabs disponibles**:
- **Male British**: "Daniel", "Callum"
- **Female British**: "Charlotte", "Alice"

**Solución**: Configurar `voice_id` en las llamadas a ElevenLabs API + agregar selector en UI

---

### **5. No hay filtro por período/género de canciones** 🟠
**Problema**: Hay muchas canciones modernas/juveniles, pero los clientes de music bingo son personas mayores.

**Comentario de Philip**:
> "can you send me the text you instructed the AI to do and I can adjust it"

**Prompt AI actual** (NO filtra por edad):
```
You are a professional Music Bingo DJ. Generate 3 SHORT announcements for this song:

Song: "{title}" by {artist} ({release_year})
Genre: {genre}

CRITICAL RULES:
1. NEVER mention the song title
2. NEVER mention the artist name
3. Keep each announcement to 1 short sentence (10-15 words max)
4. Give subtle hints about era, genre, or impact WITHOUT spoiling
```

**El prompt NO considera**:
- Edad del público objetivo
- Filtro por década (60s, 70s, 80s, 90s)
- Filtro por género musical

**Soluciones**:
- **Opción A**: Regenerar AI announcements con contexto de "older audience"
- **Opción B**: Agregar filtro de década en la UI del juego
- **Opción C**: Crear pools de canciones por grupo demográfico

---

### **6. Mejoras en las tarjetas PDF** 🟡
**Problema**: Las tarjetas necesitan mejoras visuales y de contenido.

**Requerimientos detallados** (ver imagen adjunta):

1. **Logo de Perfect DJ centrado** 
   - Debe aparecer en la casilla FREE (centro de la tarjeta)
   - Tamaño visible pero no invasivo

2. **Logo y redes sociales del pub en la parte superior**
   - Espacio en top line para agregar logo del pub
   - Texto: "It would be great if we can add in Pub Logo and how to follow on social media in top line"

3. **Fuente más grande en casillas**
   - Los nombres de artistas necesitan ser más legibles
   - Texto: "larger font"

4. **Bordes redondeados en todas las esquinas**
   - Actualmente las tarjetas tienen bordes cuadrados
   - Texto: "Is it possible to bold around all 4 corners"

5. **Información de premios**
   - Agregar texto en la tarjeta con:
     - "Prizes For All 4 Corners"
     - "First Line"
     - "Full House!"

**Archivo a modificar**: `backend/generate_cards.py`

**Solución**: 
- Modificar generación de PDF con ReportLab
- Agregar header section para pub branding + social media
- Aumentar font size en celdas (actualmente muy pequeño)
- Cambiar borders a rounded corners
- Agregar footer/lateral con prizes info
- Centrar logo Perfect DJ en casilla FREE

---

### **7. Background music no se silencia correctamente** 🔴
**Problema**: La música de fondo sigue sonando durante la reproducción del track y los anuncios.

**Comportamiento actual**:
- Background music: 15% constante
- Durante anuncios: reduce a 4.5% (15% × 0.3)
- Durante track preview: **NO SE SILENCIA** ❌

**Comportamiento esperado**:
- Durante track preview: **0% (silencio total)** ✅
- Durante anuncios: 5-8% (muy bajo) ✅
- Resto del tiempo: 15% ✅

**Causa**: En `game.js`, las funciones `playNextSong()` y `playPreview()` solo reducen volumen, no silencian

**Solución**: Cambiar fade a 0% durante tracks

---

### **8. Tiempo de reproducción muy corto** 🟠
**Problema**: Los tracks solo se reproducen 8 segundos, es muy poco tiempo.

**Valor actual**: `PREVIEW_DURATION_MS: 8000` (8 segundos)

**Sugerencia**: Extender a 15-20 segundos

**Archivo**: `frontend/game.js` línea 25

**Solución**: Cambiar a `PREVIEW_DURATION_MS: 18000` (18 segundos)

---

### **9. No hay fade in/out en los tracks** 🟢
**Problema**: Los tracks empiezan y terminan abruptamente, no suena profesional.

**Requerimiento**: Agregar transiciones suaves (fade in/fade out)

**Beneficio**: Experiencia más profesional y pulida

**Solución**: Implementar fade con Howler.js:
- Fade in: 0% → 100% en 1000ms al iniciar
- Fade out: 100% → 0% en 1000ms antes de terminar

---

## 📊 Resumen de Prioridades

| # | Error | Severidad | Impacto | Dificultad |
|---|-------|-----------|---------|------------|
| 3 | Cálculo invertido canciones | 🔴 Crítico | Rompe jugabilidad | Fácil |
| 7 | Background no se silencia | 🔴 Crítico | Experiencia pobre | Media |
| 1 | Auto-inicio | 🔴 Alto | Confusión usuario | Media |
| 8 | Track muy corto | 🟠 Medio | Jugabilidad | Fácil |
| 4 | Voz no británica | 🟡 Bajo | Localización | Media |
| 5 | Sin filtro edad/género | 🟡 Bajo | Target audience | Complejo |
| 9 | Sin fade in/out | 🟢 Polish | Profesionalismo | Media |
| 6 | Logo en PDF | 🟢 Polish | Branding | Media |
| 2 | Espacios en pub name | ✅ NO ES BUG | N/A | N/A |

---

## 🎯 Plan de Acción Sugerido

### **Fase 1 - Fixes Críticos (Hoy, 1-2 horas)**
1. ✅ Fix #3: Cambiar cálculo a `numPlayers × 3`
2. ✅ Fix #7: Silenciar background a 0% durante tracks
3. ✅ Fix #8: Extender preview a 18 segundos
4. ✅ Fix #9: Agregar fade in/out

### **Fase 2 - UX Improvements (Mañana, 2-3 horas)**
5. ✅ Fix #1: Pantalla de setup obligatoria
6. ✅ Fix #4: Voces británicas + selector

### **Fase 3 - Features Avanzadas (Esta semana, 4-6 horas)**
7. ✅ Fix #5: Filtro de década/género
8. ✅ Fix #6: Logo en PDF + logo del pub
9. ✅ Regenerar AI announcements para público mayor

---

## 💬 Comentarios Adicionales de Philip

> "otherwise it is getting really good, good job, i have another job as soon as this demo is complete"

**Estado general**: ✅ Philip está contento con el progreso

**Próximo proyecto**: Confirmado cuando se complete este demo

---

## 📸 Evidencia Visual

**Imagen adjunta**: Muestra discrepancia entre "48 songs" calculados y "262 songs left to play" en el pool completo.

Esto confirma que el cálculo de canciones óptimas está fallando y solo usa una fracción pequeña del pool disponible.
