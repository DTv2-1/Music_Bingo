# AI Announcement System 🤖

Sistema de anuncios personalizados generados por OpenAI para Music Bingo.

## 📖 Descripción

En lugar de usar anuncios genéricos, este sistema genera **3 anuncios únicos** para cada canción del pool usando OpenAI GPT-4o-mini. Los anuncios se generan **una sola vez** y luego se usan offline durante los juegos.

### Tipos de Anuncios

Cada canción obtiene 3 variantes:
- **Decade**: Contexto de era/década (ej: "Here's a synth-driven anthem from the electronic 80s")
- **Trivia**: Dato curioso genérico (ej: "This track revolutionized music videos")
- **Simple**: Frase corta (ej: "Next up" o "Coming up")

## 🚀 Uso

### Paso 1: Configurar API Key

1. Obtén tu API key de OpenAI: https://platform.openai.com/api-keys
2. Agrégala al archivo `backend/.env`:

```env
OPENAI_API_KEY=sk-proj-...
```

### Paso 2: Instalar Dependencias

```bash
pip install openai
```

O usando requirements:

```bash
pip install -r backend/requirements.txt
```

### Paso 3: Generar Anuncios

```bash
cd /Users/1di/Music_Bingo
python backend/generate_announcements_ai.py
```

**Costo estimado**: $2-5 (una sola vez para 257 canciones)
**Tiempo**: 5-10 minutos

### Paso 4: Desplegar

Los anuncios se guardan en `data/announcements_ai.json`. Incluye este archivo en tu deployment:

```bash
git add data/announcements_ai.json
git commit -m "Add AI-generated announcements"
git push origin main
```

## 📊 Resultado

- **Archivo**: `data/announcements_ai.json` (~50-100 KB)
- **Anuncios totales**: 771 (3 × 257 canciones)
- **Uso en juego**: Automático y offline (sin latencia)

## 🎮 Comportamiento en el Juego

1. Si `announcements_ai.json` existe → Usa anuncios AI personalizados
2. Si no existe → Fallback a sistema de plantillas (29 frases genéricas)

Ejemplo de log:
```
✓ Loaded 257 songs from pool
✓ Loaded 257 AI announcements
🎙️ Announcing: "Here's a synth-driven anthem from the electronic 80s"
```

## 🔧 Re-generación

Si agregas nuevas canciones al pool:

```bash
python backend/generate_announcements_ai.py
```

El script procesará solo las canciones nuevas (detecta IDs existentes).

## 💡 Ventajas vs Sistema Genérico

| Aspecto | Genérico | AI |
|---------|----------|-----|
| Variedad | 29 frases | 771 frases |
| Personalización | Baja | Alta |
| Costo | Gratis | $2-5 (una vez) |
| Latencia juego | 0ms | 0ms |
| Calidad | Buena | Excelente |

## ⚠️ Notas

- **No spoilea**: OpenAI está configurado para NUNCA mencionar título o artista
- **Fallback automático**: Si falla la generación, usa plantillas genéricas
- **Offline después**: Una vez generado, no requiere internet ni API calls durante el juego
- **Costo único**: Solo pagas la primera vez que generas

## 🐛 Troubleshooting

**Error: "OPENAI_API_KEY not found"**
→ Agrega la key en `backend/.env`

**Error: "openai package not installed"**
→ `pip install openai`

**Quiero regenerar anuncios para canciones específicas**
→ Elimina las entradas en `announcements_ai.json` y vuelve a correr el script

**Los anuncios no aparecen en el juego**
→ Verifica que `data/announcements_ai.json` exista y esté en el servidor
