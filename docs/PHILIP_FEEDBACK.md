# Feedback de Philip - Cambios Requeridos

## Fecha: 7 de enero de 2026

---

## 🎯 Cambios Principales Solicitados

### 1. ❌ ELIMINAR Nombre de Canción de los Anuncios
**Comportamiento actual:**
- "Next up, [Track Name]"

**Requerido:**
- NO anunciar nombre de canción ni artista
- Los jugadores deben identificar canciones solo de oído

---

### 2. 🎤 NUEVOS Estilos de Anuncios (3 Tipos - Rotar Aleatoriamente)

#### Tipo A: Contexto de Era/Década (33%)
**Ejemplos:**
- "Let's go straight to the 1980s for a couple of songs"
- "Coming up: A massive hit from the swinging 1960s"
- "Next track: Straight out of the disco-fueled 1970s"
- "Here's an iconic banger from the hair metal 1980s"
- "Listen up for this gem from the grunge and pop explosion of the 1990s"
- "Get ready for this modern classic from the 2010s"

#### Tipo B: Datos Curiosos/Trivia (33% - 1 de cada 3 canciones)
**Ejemplos:**
- "This artist appeared at Glastonbury in 2019"
- "This song was featured in a James Bond film"
- "This track spent 12 weeks at number one"
- "This artist won a Grammy for this album"
- "This song was written in just 20 minutes"

**Nota:** Los datos NO deben revelar título de canción o artista directamente

#### Tipo C: Genérico Simple (33%)
**Ejemplos:**
- "Next song"
- "Here we go"
- "Coming up"
- "Let's keep it going"
- "Another one coming your way"

---

### 3. 🏠 Agregar Personalización con Nombre del Pub/Bar

**El anuncio de bienvenida debe incluir:**
- "Welcome to Music Bingo at [NOMBRE DEL PUB]"
- Hacerlo configurable (variable de entorno o archivo config)

**Ejemplo:**
```
"Good evening everyone! Welcome to Music Bingo at The Red Lion Pub! 
Tonight we're dropping beats instead of balls. Grab your cards, 
your markers, and get ready to mark off those songs as we play 
short clips. No titles or artists will be announced—just listen 
closely, sing along if you know it, and shout 'Bingo!' when you 
get a line or full house. Let's kick things off!"
```

---

### 4. 📋 Scripts de Bienvenida Mejorados

Usar anuncios de bienvenida energéticos, estilo DJ del documento:

**Option 1:**
```
"Ladies and gentlemen, welcome to Music Bingo at [PUB NAME]! 
Tonight, we're dropping beats instead of balls. Grab your cards, 
your markers, and get ready to mark off those songs as we play 
short clips. No titles or artists will be announced—just listen 
closely, sing along if you know it, and shout 'Bingo!' when you 
get a line or full house. We've got great prizes up for grabs, 
so let's kick things off with some classic tunes!"
```

**Option 2:**
```
"Hello everyone and welcome to the ultimate Music Bingo night at [PUB NAME]! 
Get those dabbers ready because we're about to play hits from across 
the decades. I'll spin the tracks, you identify them on your card—without 
any hints on the name or who sings it. First to a full line wins! 
Are you ready to test your music knowledge? Let's get this party started!"
```

**Option 3:**
```
"Good evening, music lovers! It's time for Music Bingo extravaganza at [PUB NAME]. 
Rules are simple: We play a snippet, you spot the song on your card and 
mark it off. No song titles or artists given—just pure ear power. 
Prizes for the quickest bingos, so stay sharp. Here comes the first track—good luck!"
```

---

### 5. 🎊 Anuncios de Mitad de Juego

Agregar potenciadores de energía a mitad de partida:

**Option 1:**
```
"Alright, everyone—we're halfway through this round! How's everyone doing? 
A few close calls out there? Keep those ears open because the hits are 
just getting better. Remember, no peeking at your phones for lyrics! 
Next track coming up—let's see who gets closer to that bingo!"
```

**Option 2:**
```
"We're at the halfway mark, folks! Time for a quick breather. 
Anyone got a line yet? Shout out if you're one away! We've got some 
absolute bangers left, so don't give up now. Grab a drink, stretch 
those vocal cords for singing along, and let's dive back in!"
```

**Option 3:**
```
"Halfway there, music bingo fans! You're all doing amazing—I've heard 
some epic sing-alongs already. Prizes are waiting for those full cards, 
so stay focused. If you're stuck on a song, maybe the next one will 
jog your memory. Here we go with more tunes!"
```

---

## 🔧 Tareas de Implementación Técnica

### Tarea 1: Actualizar `backend/server.py`
- [ ] Eliminar nombre de canción del endpoint `/api/announcements`
- [ ] Agregar sistema de rotación de 3 tipos de anuncios
- [ ] Implementar lógica de selección aleatoria (33% cada tipo)
- [ ] Agregar configuración de nombre del pub

### Tarea 2: Crear Plantillas de Anuncios
- [ ] Plantillas de era/década (por año de lanzamiento de datos iTunes)
- [ ] Array de frases genéricas simples
- [ ] Base de datos de datos curiosos (opcional - puede ser manual o de datos iTunes)

### Tarea 3: Agregar Configuración
- [ ] Agregar `PUB_NAME` al archivo `.env`
- [ ] Agregar `HALFWAY_ANNOUNCEMENT_INTERVAL` (opcional)
- [ ] Agregar toggle para tipos de anuncios en frontend

### Tarea 4: Actualizar Frontend (`frontend/game.js`)
- [ ] Eliminar nombre de canción del UI si está presente
- [ ] Agregar trigger de anuncio de mitad (después del 50% de canciones)
- [ ] Probar rotación de anuncios

### Tarea 5: Mejorar Datos de iTunes (`backend/generate_pool.py`)
- [ ] Extraer año de lanzamiento de iTunes API
- [ ] Mapear años a décadas (1960s, 1970s, 1980s, etc.)
- [ ] Guardar info de década en `pool.json`

### Tarea 6: Testing
- [ ] Probar que funcionan los 3 tipos de anuncios
- [ ] Verificar que NO se revelan nombres de canciones
- [ ] Probar que nombre del pub aparece en bienvenida
- [ ] Probar que anuncios de mitad se activan correctamente
- [ ] Probar que TTS suena natural con nuevos scripts

---

## 📊 Ejemplo de Distribución de Anuncios

Para un juego de 50 canciones:
- **17 canciones** → Contexto de era/década ("Let's go to the 80s...")
- **17 canciones** → Datos curiosos ("This artist appeared at...")
- **16 canciones** → Genérico simple ("Next song")

---

## 🎯 Orden de Prioridad

1. **ALTA** - Eliminar nombre de canción de todos los anuncios
2. **ALTA** - Agregar nombre del pub a la bienvenida
3. **ALTA** - Implementar sistema de 3 tipos de anuncios
4. **MEDIA** - Agregar scripts de bienvenida mejorados
5. **MEDIA** - Agregar anuncios de mitad de juego
6. **BAJA** - Construir base de datos extensa de datos curiosos

---

## 📎 Documento de Referencia

Philip proporcionó: `TTS Announcments During Music Bingo.pdf`
- Scripts completos para anuncios de bienvenida
- Ejemplos de pistas basadas en era
- Pistas de datos curiosos/snippets interesantes
- Plantillas de anuncios de mitad de juego

---

## ✅ Criterios de Éxito

- ✅ Cero nombres de canciones o artistas mencionados
- ✅ Nombre del pub aparece en bienvenida
- ✅ Anuncios rotan entre 3 tipos naturalmente
- ✅ Se siente como un DJ real presentando
- ✅ Tono energético y atractivo
- ✅ No repetitivo (variedad en las frases)
