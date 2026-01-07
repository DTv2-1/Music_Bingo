# 🚀 Deployment Automático - GitHub Actions

## 📋 Configuración Inicial

### 1. Preparar el servidor (una sola vez)

SSH al servidor y configurar git:

```bash
# Conectar al servidor
ssh root@134.209.183.139

# Ir al directorio del proyecto
cd /var/www/music-bingo

# Inicializar git si no está inicializado
git init
git remote add origin https://github.com/TU_USUARIO/Music_Bingo.git

# Configurar para pull sin problemas
git config pull.rebase false
```

### 2. Configurar GitHub Secrets

Ve a tu repositorio en GitHub → Settings → Secrets and variables → Actions

Crea estos 3 secrets:

#### `SERVER_IP`
```
134.209.183.139
```

#### `SERVER_USER`
```
root
```

#### `SSH_PRIVATE_KEY`
Tu clave privada SSH (la que usas para conectarte al servidor).

Para obtenerla:
```bash
# En tu Mac, copia tu clave privada
cat ~/.ssh/id_rsa
# O si usas otra clave:
cat ~/.ssh/tu_clave_privada
```

Copia TODO el contenido (desde `-----BEGIN RSA PRIVATE KEY-----` hasta `-----END RSA PRIVATE KEY-----`) y pégalo en el secret.

---

## 🎯 Cómo Funciona

Una vez configurado:

1. **Haces cambios localmente**
   ```bash
   git add .
   git commit -m "Nuevo feature"
   git push origin main
   ```

2. **GitHub Actions se ejecuta automáticamente**
   - Conecta al servidor vía SSH
   - Hace `git pull` para traer los cambios
   - Instala dependencias si hay nuevas
   - Reinicia el servidor Flask
   - Recarga nginx

3. **Tu sitio se actualiza automáticamente** 🎉
   - http://134.209.183.139

---

## 📂 Estructura del Workflow

El archivo `.github/workflows/deploy.yml` contiene:

- **Trigger**: Se ejecuta en cada push a `main` o `master`
- **Pasos**:
  1. Checkout del código
  2. SSH al servidor
  3. Git pull
  4. Instalar dependencias
  5. Reiniciar supervisor
  6. Recargar nginx

---

## 🔧 Comandos Útiles

### Ver el log de deployment en GitHub:
1. Ve a tu repo → Actions
2. Click en el último workflow run
3. Verás el progreso en tiempo real

### Deployment manual desde local:
Si necesitas desplegar sin hacer push:

```bash
ssh root@134.209.183.139 'cd /var/www/music-bingo && git pull && sudo supervisorctl restart music-bingo'
```

### Ver logs del servidor:
```bash
ssh root@134.209.183.139
tail -f /var/log/music-bingo/music-bingo.log
```

---

## ⚠️ Importante

### Archivos que NO se sincronizan automáticamente:

1. **`.env`** - Variables de entorno
   - No se sube a GitHub por seguridad
   - Ya está en el servidor en `/var/www/music-bingo/backend/.env`
   - Si cambias algo, actualízalo manualmente en el servidor

2. **`data/pool.json`** - Pool de canciones
   - Regenerar en el servidor si es necesario:
   ```bash
   ssh root@134.209.183.139
   cd /var/www/music-bingo
   python backend/generate_pool.py
   ```

3. **`data/cards/*.pdf`** - Tarjetas generadas
   - Se generan bajo demanda desde el frontend
   - No necesitan estar en git

### Añadir al `.gitignore`:

```bash
# Ya deberías tener esto en .gitignore
backend/.env
data/pool.json
data/cards/*.pdf
__pycache__/
*.pyc
.DS_Store
```

---

## 🧪 Testing

### Probar el workflow:

1. Haz un cambio pequeño (ej: comentario en el código)
2. Commit y push:
   ```bash
   git add .
   git commit -m "Test: deployment automático"
   git push origin main
   ```
3. Ve a GitHub → Actions y observa el proceso
4. Verifica en http://134.209.183.139 que los cambios se aplicaron

---

## 🐛 Troubleshooting

### Error: "Permission denied (publickey)"
- Verifica que el `SSH_PRIVATE_KEY` en GitHub Secrets sea correcto
- Asegúrate de copiar la clave completa incluyendo BEGIN y END

### Error: "git pull failed"
- Puede haber conflictos en el servidor
- SSH al servidor y resuelve manualmente:
  ```bash
  cd /var/www/music-bingo
  git status
  git stash  # Si hay cambios locales
  git pull
  ```

### Error: "supervisorctl restart failed"
- Verifica que supervisor esté corriendo:
  ```bash
  ssh root@134.209.183.139
  sudo supervisorctl status
  ```

---

## 🎉 ¡Listo!

Ahora tienes deployment automático. Cada vez que hagas push, tu aplicación se actualiza sola en el servidor.

**Próximo push → Deployment automático → Sitio actualizado** 🚀
