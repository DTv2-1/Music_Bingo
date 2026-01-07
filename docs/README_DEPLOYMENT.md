# 🎵 Music Bingo - Deployment con GitHub Actions

## 🚀 Configuración Rápida (3 pasos)

### 1️⃣ Subir el código a GitHub

```bash
# Desde tu Mac, en el directorio del proyecto
cd /Users/1di/Music_Bingo

# Crear repositorio en GitHub (ve a github.com y crea un repo nuevo)
# Luego ejecuta:

git init
git add .
git commit -m "Initial commit: Music Bingo with auto-deployment"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/Music_Bingo.git
git push -u origin main
```

### 2️⃣ Configurar el servidor (una sola vez)

```bash
# Conectar al servidor
ssh root@134.209.183.139

# Ejecutar script de configuración
cd /var/www/music-bingo
bash setup_server.sh
```

El script te pedirá la URL de tu repo GitHub.

### 3️⃣ Configurar GitHub Secrets

Ve a tu repositorio en GitHub:
1. **Settings** → **Secrets and variables** → **Actions**
2. Click en **New repository secret**
3. Crea estos 3 secrets:

| Secret Name | Value |
|-------------|-------|
| `SERVER_IP` | `134.209.183.139` |
| `SERVER_USER` | `root` |
| `SSH_PRIVATE_KEY` | Tu clave SSH privada completa |

**Para obtener tu SSH_PRIVATE_KEY:**
```bash
cat ~/.ssh/id_rsa
```
Copia TODO (desde `-----BEGIN` hasta `-----END`)

---

## ✅ ¡Listo! Ahora cada push despliega automáticamente

```bash
# Haz cambios en tu código local
git add .
git commit -m "Nuevo feature"
git push origin main

# GitHub Actions despliega automáticamente a:
# http://134.209.183.139
```

---

## 📊 Ver el Deployment en Acción

1. Ve a tu repo en GitHub
2. Click en la pestaña **Actions**
3. Verás el workflow "Deploy to Digital Ocean" ejecutándose
4. Click en el workflow para ver los logs en tiempo real

---

## 🔧 Comandos Útiles

### Deployment manual (sin push)
```bash
ssh root@134.209.183.139 'cd /var/www/music-bingo && git pull && sudo supervisorctl restart music-bingo'
```

### Ver logs del servidor
```bash
ssh root@134.209.183.139
tail -f /var/log/music-bingo/music-bingo.log
```

### Regenerar pool de canciones
```bash
ssh root@134.209.183.139
cd /var/www/music-bingo
python backend/generate_pool.py
```

### Ver estado del servidor
```bash
ssh root@134.209.183.139
sudo supervisorctl status music-bingo
```

---

## 📂 Estructura del Proyecto

```
Music_Bingo/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow
├── backend/
│   ├── server.py               # Flask API
│   ├── generate_pool.py        # Generador de canciones
│   ├── generate_cards.py       # Generador de tarjetas PDF
│   ├── requirements.txt        # Dependencias Python
│   └── .env                    # Variables de entorno (NO en git)
├── frontend/
│   ├── game.html              # UI del juego
│   ├── game.js                # Lógica del juego
│   └── styles.css             # Estilos
├── data/
│   ├── pool.json              # Pool de canciones (generado)
│   └── cards/                 # Tarjetas PDF (generadas)
├── setup_server.sh            # Script de configuración del servidor
├── DEPLOYMENT.md              # Guía de deployment
└── .gitignore                 # Archivos a ignorar
```

---

## ⚠️ Archivos que NO están en Git

Estos archivos se generan dinámicamente y NO se suben a GitHub:

- `backend/.env` - Variables de entorno (secrets)
- `data/pool.json` - Pool de canciones (regenerar en servidor)
- `data/cards/*.pdf` - Tarjetas (generar bajo demanda)

---

## 🎮 Funcionalidades Implementadas

✅ **1. Nombre del venue personalizable**
- UI con campo de texto
- Generación de tarjetas desde frontend
- Se muestra en header: "MUSIC BINGO at [Venue Name]"

✅ **2. Detección de artistas duplicados**
- 257 canciones en pool
- 32 artistas con múltiples canciones detectados
- Flag `has_duplicate_artist` en cada canción

✅ **3. Formato condicional inteligente**
- Artistas duplicados: SIEMPRE "Artist - Song"
- Artistas únicos: 50/50 solo artista O solo canción
- Variedad visual en las tarjetas

✅ **4. Clips de audio de 8 segundos**
- Extendido de 5s a 8s
- Suficiente para reconocer la canción

✅ **5. Sistema de cálculo inteligente por jugadores**
- 10 jugadores → 60 canciones (~30 min)
- 25 jugadores → 48 canciones (~24 min)
- 50 jugadores → 31 canciones (~15 min)
- Estimación en tiempo real en UI

✅ **6. Logo y branding de Perfect DJ**
- Código listo para logo en celda FREE
- URL `www.perfectdj.co.uk` en tarjetas
- Footer con branding

---

## 🐛 Troubleshooting

### Error: "Permission denied" en GitHub Actions
→ Verifica que `SSH_PRIVATE_KEY` esté correcto en GitHub Secrets

### Error: "git pull failed"
→ SSH al servidor y resuelve conflictos manualmente:
```bash
cd /var/www/music-bingo
git status
git stash
git pull
```

### Error: "supervisorctl: command not found"
→ Instala supervisor:
```bash
sudo apt-get install supervisor
```

### El sitio no carga después del deployment
→ Verifica los logs:
```bash
ssh root@134.209.183.139
tail -50 /var/log/music-bingo/music-bingo.log
```

---

## 📝 TODO

- [ ] Agregar logo de Perfect DJ (`frontend/assets/perfectdj_logo.png`)
- [ ] Confirmar URL del sitio web (actual: `www.perfectdj.co.uk`)
- [ ] Testing exhaustivo con diferentes números de jugadores

---

## 🎉 ¡Deployment Automático Configurado!

Ahora puedes desarrollar localmente y cada push a `main` desplegará automáticamente a producción.

**Happy coding! 🚀**
