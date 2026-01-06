# 🚀 QUICK DEPLOYMENT GUIDE

## Prerequisites
- [ ] Digital Ocean account
- [ ] Domain name (optional, can use IP)
- [ ] ElevenLabs API key
- [ ] SSH key configured

## Step 1: Create Droplet on Digital Ocean

1. Go to: https://cloud.digitalocean.com/droplets/new
2. Choose configuration:
   - **Image:** Ubuntu 22.04 LTS
   - **Plan:** Basic ($6/month - 1GB RAM)
   - **Region:** London (closest to UK)
   - **Authentication:** SSH Key
3. Create droplet
4. Note the IP address (e.g., `157.230.45.123`)

## Step 2: Initial Server Setup

SSH into your server:
```bash
ssh root@YOUR_SERVER_IP
```

Update system and install dependencies:
```bash
# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y python3 python3-pip nginx supervisor git

# Install Python packages globally
pip3 install flask flask-cors gunicorn requests python-dotenv fpdf2
```

## Step 3: Deploy Using Automated Script

From your **local machine** (Mac):

```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment (replace with your server IP)
./deploy.sh YOUR_SERVER_IP

# Or with domain:
./deploy.sh YOUR_SERVER_IP musicbingo.perfectdj.co.uk
```

The script will:
- ✅ Upload all files to server
- ✅ Install dependencies
- ✅ Generate song pool and bingo cards

## Step 4: Configure Environment Variables

SSH into server and edit .env:
```bash
ssh root@YOUR_SERVER_IP
cd /var/www/music-bingo/backend
nano .env
```

Add:
```bash
# ElevenLabs TTS Configuration
ELEVENLABS_API_KEY=sk_your_actual_key_here
ELEVENLABS_VOICE_ID=cgSgspJ2msm6clMCkdW9

# iTunes API Configuration
ITUNES_COUNTRY=GB
ITUNES_TARGET_SONGS=250

# PDF Generation
PDF_NUM_CARDS=50
PDF_GRID_SIZE=5

# Perfect DJ Branding
PERFECT_DJ_PRIMARY_COLOR=#667eea
PERFECT_DJ_SECONDARY_COLOR=#764ba2
```

Save: `Ctrl+X`, `Y`, `Enter`

## Step 5: Setup Supervisor (Keep App Running)

```bash
# Create log directory
mkdir -p /var/log/music-bingo

# Copy supervisor config
cp /var/www/music-bingo/supervisor.conf /etc/supervisor/conf.d/music-bingo.conf

# Reload and start
supervisorctl reread
supervisorctl update
supervisorctl start music-bingo

# Check status
supervisorctl status music-bingo
```

Should show: `music-bingo RUNNING`

## Step 6: Setup Nginx (Web Server)

```bash
# Copy nginx config
cp /var/www/music-bingo/nginx.conf /etc/nginx/sites-available/music-bingo

# Edit config to add your domain/IP
nano /etc/nginx/sites-available/music-bingo
# Change: server_name YOUR_DOMAIN_OR_IP;
# To: server_name 157.230.45.123;  (your IP)
# Or: server_name musicbingo.perfectdj.co.uk;  (your domain)

# Enable site
ln -s /etc/nginx/sites-available/music-bingo /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default  # Remove default site

# Test config
nginx -t

# Restart nginx
systemctl restart nginx
```

## Step 7: Configure Firewall

```bash
# Allow SSH, HTTP, HTTPS
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable

# Check status
ufw status
```

## Step 8: Test Deployment

Open browser and go to:
```
http://YOUR_SERVER_IP
```

Or:
```
http://musicbingo.perfectdj.co.uk
```

You should see the Music Bingo game interface!

## Step 9: SSL Certificate (Optional but Recommended)

Only if you have a domain:

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d musicbingo.perfectdj.co.uk

# Follow prompts
# Certificate will auto-renew every 90 days
```

Now access via HTTPS:
```
https://musicbingo.perfectdj.co.uk
```

## Step 10: Configure Domain DNS (if using custom domain)

Go to your domain registrar and add:

**A Record:**
- Host: `@` or `musicbingo`
- Points to: `YOUR_SERVER_IP`
- TTL: 300

Wait 5-30 minutes for DNS propagation.

---

## 🎉 DEPLOYMENT COMPLETE!

Your Music Bingo is now live at:
- **With IP:** http://YOUR_SERVER_IP
- **With Domain:** http://musicbingo.perfectdj.co.uk
- **With SSL:** https://musicbingo.perfectdj.co.uk

## Quick Commands Reference

```bash
# Restart backend
supervisorctl restart music-bingo

# View backend logs
tail -f /var/log/music-bingo/access.log
tail -f /var/log/music-bingo/error.log

# View nginx logs
tail -f /var/log/nginx/music-bingo-access.log
tail -f /var/log/nginx/music-bingo-error.log

# Restart nginx
systemctl restart nginx

# Check backend status
supervisorctl status

# Regenerate songs
cd /var/www/music-bingo
python3 backend/generate_pool.py

# Update code
cd /var/www/music-bingo
git pull  # if using git
supervisorctl restart music-bingo
```

## Troubleshooting

### Issue: "502 Bad Gateway"
```bash
# Check if backend is running
supervisorctl status music-bingo

# If not running
supervisorctl start music-bingo

# Check logs
tail -n 50 /var/log/music-bingo/error.log
```

### Issue: "TTS not working"
```bash
# Check API key
cat /var/www/music-bingo/backend/.env

# Make sure it's set correctly
nano /var/www/music-bingo/backend/.env

# Restart backend
supervisorctl restart music-bingo
```

### Issue: "Cannot connect to server"
```bash
# Check firewall
ufw status

# Check nginx
systemctl status nginx

# Check backend
supervisorctl status music-bingo
```

---

## Monthly Cost: $6 USD

✅ **Your Music Bingo is ready for the client to test!**
