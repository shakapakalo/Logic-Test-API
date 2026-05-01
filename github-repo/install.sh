#!/bin/bash
# ================================================================
#  AI API Server — One-Command Installer for Contabo VPS
#  Tested on: Ubuntu 20.04, 22.04, 24.04
#
#  Usage:
#    chmod +x install.sh
#    sudo ./install.sh
# ================================================================

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[→]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "================================================================"
echo "   AI API Server — Contabo VPS Installer"
echo "================================================================"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then err "Run as root: sudo ./install.sh"; fi

# ── 1. System update ─────────────────────────────────────────────
info "Updating system..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq curl wget git build-essential nginx ufw
log "System updated"

# ── 2. Node.js 20 ────────────────────────────────────────────────
info "Installing Node.js 20..."
if ! command -v node &>/dev/null || [[ $(node -v 2>/dev/null | cut -dv -f2 | cut -d. -f1) -lt 20 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
  apt-get install -y -qq nodejs
fi
log "Node.js $(node -v) ready"

# ── 3. PM2 ───────────────────────────────────────────────────────
info "Installing PM2..."
npm install -g pm2 --quiet
log "PM2 installed"

# ── 4. Build server ──────────────────────────────────────────────
info "Installing server dependencies..."
cd server
npm install --quiet
log "Dependencies installed"

info "Building TypeScript server..."
npm run build
log "Server built successfully"
cd ..

# ── 5. Environment file ──────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  log ".env created"
fi
PORT=$(grep -E "^PORT=" .env | cut -d= -f2 | tr -d ' ')
PORT=${PORT:-3000}

# ── 6. Create logs dir ───────────────────────────────────────────
mkdir -p logs

# ── 7. Start with PM2 ────────────────────────────────────────────
info "Starting API server with PM2..."
pm2 delete ai-api 2>/dev/null || true
PORT=$PORT pm2 start server/dist/index.js \
  --name "ai-api" \
  --time \
  --log logs/out.log \
  --error logs/error.log
pm2 save
log "API server started on port $PORT"

# ── 8. PM2 auto-start on boot ────────────────────────────────────
info "Setting up PM2 to start on reboot..."
env PATH=$PATH:/usr/bin pm2 startup systemd -u root --hp /root > /dev/null 2>&1 || true
log "PM2 startup configured"

# ── 9. Nginx config ──────────────────────────────────────────────
info "Configuring Nginx..."
cat > /etc/nginx/sites-available/ai-api << EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;

    location /api {
        proxy_pass         http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF
ln -sf /etc/nginx/sites-available/ai-api /etc/nginx/sites-enabled/ai-api
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx
log "Nginx configured (port 80 → port $PORT)"

# ── 10. Firewall ─────────────────────────────────────────────────
info "Opening firewall ports..."
ufw allow OpenSSH    > /dev/null 2>&1 || true
ufw allow 80/tcp     > /dev/null 2>&1 || true
ufw allow 443/tcp    > /dev/null 2>&1 || true
ufw allow ${PORT}/tcp > /dev/null 2>&1 || true
ufw --force enable   > /dev/null 2>&1 || true
log "Firewall configured"

# ── 11. Health check ─────────────────────────────────────────────
info "Checking server health..."
sleep 3
HEALTH=$(curl -s --max-time 10 "http://localhost:${PORT}/api/healthz" 2>/dev/null || echo "")
if echo "$HEALTH" | grep -q "ok"; then
  log "Server is healthy!"
else
  warn "Server health check failed — check logs: pm2 logs ai-api"
fi

# ── Done ─────────────────────────────────────────────────────────
VPS_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "================================================================"
echo -e "  ${GREEN}✅  Installation Complete!${NC}"
echo "================================================================"
echo ""
echo "  API URL (via Nginx):  http://$VPS_IP/api"
echo "  API URL (direct):     http://$VPS_IP:$PORT/api"
echo "  Health check:         http://$VPS_IP/api/healthz"
echo ""
echo "  ── Server Management ──────────────────────────────────────"
echo "  pm2 status              → check if running"
echo "  pm2 logs ai-api         → live logs"
echo "  pm2 restart ai-api      → restart"
echo "  pm2 stop ai-api         → stop"
echo ""
echo "  ── Python Test ─────────────────────────────────────────────"
echo "  cd python"
echo "  pip install -r requirements.txt"
echo "  python3 test_all.py http://$VPS_IP/api"
echo ""
echo "  ── Update ──────────────────────────────────────────────────"
echo "  git pull && cd server && npm install && npm run build && cd .."
echo "  pm2 restart ai-api"
echo ""
echo "================================================================"
