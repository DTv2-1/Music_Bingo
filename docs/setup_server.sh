#!/bin/bash
# 
# setup_server.sh - Configuración inicial del servidor (ejecutar UNA SOLA VEZ)
# Uso: bash setup_server.sh
#

set -e  # Exit on error

echo "🚀 Configurando Music Bingo en el servidor..."
echo "=============================================="
echo ""

# 1. Instalar Git si no está instalado
echo "📦 Verificando Git..."
if ! command -v git &> /dev/null; then
    echo "Instalando Git..."
    sudo apt-get update
    sudo apt-get install -y git
else
    echo "✓ Git ya instalado"
fi

# 2. Configurar Git en el directorio del proyecto
echo ""
echo "🔧 Configurando Git..."
cd /var/www/music-bingo

# Inicializar repo si no existe
if [ ! -d .git ]; then
    git init
    echo "✓ Git inicializado"
fi

# Agregar remote (cambiar por tu repo)
git remote remove origin 2>/dev/null || true
echo ""
echo "📝 Ingresa la URL de tu repositorio GitHub:"
echo "   Ejemplo: https://github.com/tu_usuario/Music_Bingo.git"
read -p "URL del repo: " REPO_URL

git remote add origin "$REPO_URL"
echo "✓ Remote agregado: $REPO_URL"

# Configurar pull
git config pull.rebase false
echo "✓ Git configurado"

# 3. Hacer el primer pull
echo ""
echo "📥 Descargando código desde GitHub..."
git fetch origin
git branch --set-upstream-to=origin/main main 2>/dev/null || \
git branch --set-upstream-to=origin/master master 2>/dev/null || true

# Si hay archivos, hacer stash primero
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Hay cambios locales, guardándolos con stash..."
    git stash
fi

git pull origin main 2>/dev/null || git pull origin master 2>/dev/null
echo "✓ Código descargado"

# 4. Instalar dependencias Python
echo ""
echo "🐍 Instalando dependencias Python..."
pip3 install -r backend/requirements.txt
echo "✓ Dependencias instaladas"

# 5. Verificar que .env existe
echo ""
if [ -f backend/.env ]; then
    echo "✓ Archivo .env encontrado"
else
    echo "⚠️  ATENCIÓN: Falta backend/.env"
    echo "   Créalo con:"
    echo "   nano backend/.env"
fi

# 6. Reiniciar servicios
echo ""
echo "🔄 Reiniciando servicios..."
sudo supervisorctl restart music-bingo
sudo systemctl reload nginx
echo "✓ Servicios reiniciados"

# 7. Verificar estado
echo ""
echo "🔍 Verificando estado..."
sudo supervisorctl status music-bingo
echo ""

# 8. Resumen
echo "=============================================="
echo "✅ ¡Configuración completada!"
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Asegúrate de tener backend/.env con:"
echo "   - ELEVENLABS_API_KEY"
echo "   - ELEVENLABS_VOICE_ID"
echo "   - VENUE_NAME"
echo ""
echo "2. Configura GitHub Secrets en tu repositorio:"
echo "   - SERVER_IP: 134.209.183.139"
echo "   - SERVER_USER: root"
echo "   - SSH_PRIVATE_KEY: (tu clave privada SSH)"
echo ""
echo "3. Haz un push desde tu local y verás el deployment automático:"
echo "   git push origin main"
echo ""
echo "4. Tu sitio está en: http://$(curl -s ifconfig.me)"
echo ""
echo "=============================================="
