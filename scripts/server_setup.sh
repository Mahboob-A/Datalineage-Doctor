#!/usr/bin/env bash
# =============================================================================
# server_setup.sh — One-time Linode server provisioning for DataLineage Doctor
#
# Prerequisites already done (skip these):
#   ✅ Docker + Compose plugin installed
#   ✅ dldoctor user created, added to sudo + docker groups
#   ✅ 10 GB swap configured
#
# This script handles the REMAINING one-time steps:
#   1. UFW firewall rules
#   2. Clone the GitHub repo
#   3. Set up the .env file from .env.example
#   4. Add monthly certbot-renew cron job
#
# Run as: dldoctor user with sudo
# =============================================================================

set -euo pipefail

REPO_URL="https://github.com/Mahboob-A/Datalineage-Doctor.git"
APP_DIR="/home/dldoctor/app"

echo ""
echo "============================================"
echo "  DataLineage Doctor — Server Setup"
echo "============================================"
echo ""

# ── 1. UFW Firewall ──────────────────────────────────────────
echo "==> Configuring UFW firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    comment "SSH"
sudo ufw allow 80/tcp    comment "HTTP (redirect to HTTPS)"
sudo ufw allow 443/tcp   comment "HTTPS"
sudo ufw --force enable
echo "    UFW status:"
sudo ufw status verbose
echo ""

# ── 2. Clone the repository ──────────────────────────────────
if [ -d "$APP_DIR/.git" ]; then
    echo "==> Repo already cloned at $APP_DIR. Pulling latest..."
    git -C "$APP_DIR" pull origin main
else
    echo "==> Cloning repository to $APP_DIR..."
    git clone "$REPO_URL" "$APP_DIR"
fi
echo ""

# ── 3. Create .env from .env.example ────────────────────────
if [ -f "$APP_DIR/.env" ]; then
    echo "==> .env already exists — skipping. Edit it manually if needed."
else
    echo "==> Creating .env from .env.example..."
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ""
    echo "  ⚠️  ACTION REQUIRED: Edit $APP_DIR/.env with your production values:"
    echo ""
    echo "    nano $APP_DIR/.env"
    echo ""
    echo "  Required values:"
    echo "    APP_ENV=production"
    echo "    APP_BASE_URL=https://dldoctor.app"
    echo "    LLM_API_KEY=<your Gemini/OpenAI key>"
    echo "    LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/"
    echo "    LLM_MODEL=gemini-2.5-flash-preview-04-17"
    echo "    OM_JWT_TOKEN=<your OM token>  OR  OM_ADMIN_EMAIL + OM_ADMIN_PASSWORD"
    echo "    SLACK_WEBHOOK_URL=<optional>"
    echo ""
fi

# ── 4. Monthly certbot renewal cron ─────────────────────────
echo "==> Setting up monthly certbot renewal cron job..."
CRON_JOB="0 3 1 * * cd $APP_DIR && make certbot-renew >> /var/log/certbot-renew.log 2>&1"
# Add only if not already present
(crontab -l 2>/dev/null | grep -qF "certbot-renew") || \
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
echo "    Cron job added (runs 1st of each month at 3:00 AM)."
echo ""

echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Edit $APP_DIR/.env with production secrets"
echo "  2. Obtain SSL certificate (first time, before starting nginx):"
echo ""
echo "       cd $APP_DIR"
echo "       # Start only the app without nginx first (HTTP only for certbot challenge):"
echo "       docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d app worker db redis mysql elasticsearch openmetadata_server prometheus grafana"
echo "       make certbot-init"
echo ""
echo "  3. Start the full stack including nginx:"
echo "       make prod"
echo ""
echo "  4. Run database migrations:"
echo "       make prod-migrate"
echo ""
echo "  5. Verify:"
echo "       curl https://dldoctor.app/health"
echo ""
echo "  6. Add GitHub Secrets at:"
echo "     https://github.com/Mahboob-A/Datalineage-Doctor/settings/secrets/actions"
echo "     LINODE_HOST = 172.236.169.146"
echo "     LINODE_USER = dldoctor"
echo "     LINODE_SSH_KEY = <contents of your ~/.ssh/dldoctor_deploy private key>"
echo ""
