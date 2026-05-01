# Installation Guide

## Method 1 — One-Command Install (Recommended for Contabo VPS)

### Requirements
- Contabo VPS with Ubuntu 20.04 / 22.04 / 24.04
- Root access

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO

# 2. Run the installer (as root)
chmod +x install.sh
sudo ./install.sh
```

The script will automatically:
- Update the system
- Install Node.js 20
- Install PM2 (process manager)
- Build the TypeScript server
- Set up Nginx reverse proxy
- Configure the firewall
- Start the server

After install, your API will be available at:
- `http://YOUR_VPS_IP/api` (via Nginx on port 80)
- `http://YOUR_VPS_IP:3000/api` (direct)

---

## Method 2 — Docker (Easiest)

### Requirements
- Docker + Docker Compose installed

```bash
# Clone repo
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO

# Start with Docker
docker compose up -d

# Check logs
docker compose logs -f

# Stop
docker compose down
```

API will be available at `http://YOUR_VPS_IP:3000/api`

---

## Method 3 — Manual Setup

### Step 1: Install Node.js 20
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Step 2: Install PM2
```bash
sudo npm install -g pm2
```

### Step 3: Build the server
```bash
cd server
npm install
npm run build
cd ..
```

### Step 4: Set up environment
```bash
cp .env.example .env
# Edit if needed:
nano .env
```

### Step 5: Start with PM2
```bash
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup
```

### Step 6: Verify
```bash
curl http://localhost:3000/api/healthz
# Expected: {"status":"ok"}
```

---

## PM2 Management Commands

```bash
pm2 status              # Check all processes
pm2 logs ai-api         # Live logs
pm2 logs ai-api --lines 100  # Last 100 lines
pm2 restart ai-api      # Restart server
pm2 stop ai-api         # Stop server
pm2 delete ai-api       # Remove from PM2
```

---

## Updating to Latest Version

```bash
git pull origin main
cd server
npm install
npm run build
cd ..
pm2 restart ai-api
```

---

## Nginx Configuration

The install script sets up Nginx to proxy `/api` to the Node.js server on port 3000.

To view the Nginx config:
```bash
cat /etc/nginx/sites-available/ai-api
```

To test Nginx config:
```bash
sudo nginx -t
```

To reload Nginx after changes:
```bash
sudo systemctl reload nginx
```

---

## Troubleshooting

### Server not starting
```bash
pm2 logs ai-api --lines 50
```

### Port already in use
```bash
sudo lsof -i :3000
# Change PORT in .env and restart
```

### Nginx issues
```bash
sudo nginx -t
sudo journalctl -u nginx -n 50
```

### Permission denied
```bash
sudo chown -R $USER:$USER .
```
