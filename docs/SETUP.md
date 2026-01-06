# Setup Instructions

## Initial Setup

### 1. Install Python Dependencies

First, ensure you have Python 3.10 or higher installed:

```bash
python --version  # Should show 3.10 or higher
```

Install required packages:

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `fpdf2==2.7.9` - For PDF generation
- `requests==2.31.0` - For iTunes API calls

### 2. Configure API Keys

Copy the environment template:

```bash
cp .env.example .env
```

Edit `.env` and add your ElevenLabs credentials:

```bash
# ElevenLabs API Configuration
ELEVENLABS_API_KEY=sk_your_actual_api_key_here
VOICE_ID=21m00Tcm4TlvDq8ikWAM  # British male voice
```

**IMPORTANT:** Also update `frontend/game.js` with the same credentials:

```javascript
const CONFIG = {
    ELEVENLABS_API_KEY: 'sk_your_actual_api_key_here',
    VOICE_ID: '21m00Tcm4TlvDq8ikWAM',
    // ...
};
```

See [API_KEYS.md](API_KEYS.md) for detailed instructions on obtaining these keys.

### 3. Generate Game Assets

Run the backend scripts in order:

```bash
cd backend

# Generate song pool (takes 2-3 minutes)
python generate_pool.py

# Generate bingo cards (takes 30 seconds)
python generate_cards.py
```

Expected output:

```
data/
├── pool.json (250+ songs, ~100KB)
└── cards/
    └── music_bingo_cards.pdf (50 pages, ~2-3MB)
```

### 4. Test Game Interface

Open the game interface in your browser:

```bash
# From project root
open frontend/game.html
```

Or simply drag `frontend/game.html` into Chrome/Firefox/Safari.

**Test checklist:**
- [ ] Page loads without errors
- [ ] "NEXT SONG" button works
- [ ] Song preview plays (click page first to unlock audio)
- [ ] Statistics update correctly
- [ ] Called songs list displays

## Deployment to Digital Ocean

### 1. Create Droplet

1. Log in to Digital Ocean
2. Create new Droplet:
   - **OS:** Ubuntu 22.04 LTS
   - **Size:** Basic ($6/mo - 1GB RAM, 25GB SSD)
   - **Region:** London (closest to UK pubs)
3. Add SSH key for secure access
4. Create droplet

### 2. Connect to Server

```bash
ssh root@your_droplet_ip
```

### 3. Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python and Nginx
apt install -y python3 python3-pip nginx

# Install Python packages
pip3 install fpdf2==2.7.9 requests==2.31.0
```

### 4. Upload Project Files

From your local machine:

```bash
# Create project directory on server
ssh root@your_droplet_ip "mkdir -p /var/www/music-bingo"

# Upload files
scp -r backend frontend data docs .env root@your_droplet_ip:/var/www/music-bingo/
```

### 5. Generate Assets on Server

```bash
ssh root@your_droplet_ip

cd /var/www/music-bingo/backend
python3 generate_pool.py
python3 generate_cards.py
```

### 6. Configure Nginx

Create Nginx configuration:

```bash
nano /etc/nginx/sites-available/music-bingo
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name demo.perfectdj-musicbingo.com;  # Replace with your domain
    
    root /var/www/music-bingo/frontend;
    index game.html;
    
    # Main game interface
    location / {
        try_files $uri $uri/ =404;
    }
    
    # Data files (JSON, PDFs)
    location /data/ {
        alias /var/www/music-bingo/data/;
        add_header Access-Control-Allow-Origin *;
        
        # Cache control
        location ~* \.(json)$ {
            expires 1h;
        }
        location ~* \.(pdf)$ {
            expires 1d;
        }
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

Enable the site:

```bash
ln -s /etc/nginx/sites-available/music-bingo /etc/nginx/sites-enabled/
nginx -t  # Test configuration
systemctl restart nginx
```

### 7. Configure Firewall

```bash
ufw allow 'Nginx Full'
ufw allow OpenSSH
ufw enable
```

### 8. Set Up SSL (Optional but Recommended)

Install Certbot:

```bash
apt install -y certbot python3-certbot-nginx
```

Get SSL certificate:

```bash
certbot --nginx -d demo.perfectdj-musicbingo.com
```

Follow prompts to configure automatic renewal.

### 9. Test Deployment

Visit your domain:
```
https://demo.perfectdj-musicbingo.com
```

## Troubleshooting

### Issue: "pool.json not found"
**Solution:** Run `python backend/generate_pool.py` first.

### Issue: "Failed to load Howler.js"
**Solution:** Check internet connection. Howler.js loads from CDN.

### Issue: "ElevenLabs API error: 401"
**Solution:** 
1. Check API key is correct in both `.env` and `frontend/game.js`
2. Verify API key is active in ElevenLabs dashboard
3. Check you have credits remaining

### Issue: "Songs won't play"
**Solution:** 
1. Click anywhere on page first (browser autoplay policy)
2. Check browser console for errors
3. Verify iTunes preview URLs are accessible

### Issue: PDF cards look wrong when printed
**Solution:** 
1. Print at 100% scale (not "Fit to Page")
2. Use A4 paper size
3. Portrait orientation
4. Check printer settings

### Issue: Python module not found
**Solution:**
```bash
pip install -r backend/requirements.txt
```

### Issue: Permission denied when generating files
**Solution:**
```bash
chmod +x backend/generate_pool.py
chmod +x backend/generate_cards.py
```

## Updating the System

### Refresh Song Pool (Weekly Recommended)

```bash
cd backend
python generate_pool.py
```

This fetches the latest songs from iTunes to keep content fresh.

### Generate New Cards

```bash
cd backend
python generate_cards.py
```

### Update Venue Announcements

Edit `data/announcements.json`:

```json
{
  "venue_name": "Your Venue Name",
  "custom_announcements": [
    "Welcome message here",
    "Happy hour announcement",
    "Winner verification message"
  ]
}
```

No restart needed - changes take effect on next page reload.

## Performance Tips

### Local Development
- Use Chrome for best performance
- Keep DevTools closed during demo
- Close other tabs to free memory

### Production Deployment
- Enable Nginx gzip compression
- Set up CloudFlare for CDN (optional)
- Monitor server resources with `htop`
- Set up log rotation for Nginx logs

## Backup Procedures

### Backup Generated Data

```bash
# On server
cd /var/www/music-bingo
tar -czf backup-$(date +%Y%m%d).tar.gz data/
```

### Restore from Backup

```bash
tar -xzf backup-20260106.tar.gz
```

## Next Steps

Once setup is complete:
1. Read [USAGE.md](USAGE.md) for pub operation guide
2. Test with friends before live demo
3. Print extra bingo cards as backup
4. Prepare custom announcements for venue

---

**Need Help?**  
Contact: Juan Diego Gutierrez  
Documentation: See README.md for overview
