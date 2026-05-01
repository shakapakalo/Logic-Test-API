#!/bin/bash
# ============================================================
#  AI API Server — One-Command Installer for Contabo VPS
#  Tested on: Ubuntu 20.04, 22.04, 24.04
# ============================================================
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/install.sh | bash
# Or after cloning:
#   chmod +x install.sh && sudo ./install.sh
# ============================================================

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
info() { echo -e "${BLUE}[>>]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

echo ""
echo "============================================================"
echo "  AI API Server — Contabo VPS Installer"
echo "============================================================"
echo ""

# ─── Check root ──────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  err "Please run as root: sudo ./install.sh"
fi

# ─── Detect OS ───────────────────────────────────────────────
. /etc/os-release
info "Detected OS: $NAME $VERSION_ID"

# ─── Step 1: System update ───────────────────────────────────
info "Updating system packages..."
apt-get update -qq && apt-get upgrade -y -qq
log "System updated"

# ─── Step 2: Install dependencies ────────────────────────────
info "Installing dependencies..."
apt-get install -y -qq curl wget git build-essential nginx ufw
log "Dependencies installed"

# ─── Step 3: Install Node.js 20 ──────────────────────────────
info "Installing Node.js 20..."
if ! command -v node &>/dev/null || [[ $(node -v | cut -d'v' -f2 | cut -d'.' -f1) -lt 20 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - -qq
  apt-get install -y -qq nodejs
  log "Node.js $(node -v) installed"
else
  log "Node.js $(node -v) already installed"
fi

# ─── Step 4: Install PM2 ─────────────────────────────────────
info "Installing PM2..."
npm install -g pm2 -q
pm2 startup systemd -u root --hp /root
log "PM2 installed"

# ─── Step 5: Build the server ────────────────────────────────
info "Installing server dependencies..."
cd server
npm install -q
log "Dependencies installed"

info "Building TypeScript server..."
npm run build
log "Server built"

cd ..

# ─── Step 6: Setup .env ──────────────────────────────────────
if [ ! -f ".env" ]; then
  info "Creating .env from example..."
  cp .env.example .env
  warn "Edit .env if you want to change the port: nano .env"
fi

# ─── Step 7: Start with PM2 ──────────────────────────────────
info "Starting API server with PM2..."
PORT=$(grep PORT .env | cut -d'=' -f2 | tr -d ' ' || echo 3000)
cd server
PORT=${PORT:-3000} pm2 start dist/index.js --name "ai-api" --time
pm2 save
cd ..
log "API server started on port $PORT"

# ─── Step 8: Configure firewall ──────────────────────────────
info "Configuring UFW firewall..."
ufw allow OpenSSH    -q 2>/dev/null || true
ufw allow 80/tcp     -q 2>/dev/null || true
ufw allow 443/tcp    -q 2>/dev/null || true
ufw allow ${PORT}/tcp -q 2>/dev/null || true
ufw --force enable   2>/dev/null || true
log "Firewall configured"

# ─── Step 9: Configure Nginx ─────────────────────────────────
info "Configuring Nginx reverse proxy..."
cat > /etc/nginx/sites-available/ai-api <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location /api {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /health {
        proxy_pass http://127.0.0.1:${PORT}/api/healthz;
    }
}
EOF

ln -sf /etc/nginx/sites-available/ai-api /etc/nginx/sites-enabled/ai-api
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx && systemctl enable nginx
log "Nginx configured"

# ─── Done ────────────────────────────────────────────────────
VPS_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "============================================================"
echo -e "  ${GREEN}✅ Installation Complete!${NC}"
echo "============================================================"
echo ""
echo "  API Base URL:  http://$VPS_IP/api"
echo "  Direct port:   http://$VPS_IP:$PORT/api"
echo "  Health check:  http://$VPS_IP/api/healthz"
echo ""
echo "  PM2 Commands:"
echo "    pm2 status          — check server status"
echo "    pm2 logs ai-api     — view live logs"
echo "    pm2 restart ai-api  — restart server"
echo "    pm2 stop ai-api     — stop server"
echo ""
echo "  Python test:"
echo "    cd python"
echo "    pip install -r requirements.txt"
echo "    python3 test_all.py http://$VPS_IP/api"
echo ""
echo "============================================================"
