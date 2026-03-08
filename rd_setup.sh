#!/bin/bash
# ============================================================
# AI R&D System — Setup & Cron Installer
# Run once: bash rd_setup.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=$(which python3 || which python)

echo ""
echo "🔬 AI R&D System Setup"
echo "========================"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
$PYTHON -m pip install requests fastapi uvicorn python-dotenv --quiet
echo "✅ Dependencies installed"

# Create .env if not exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cat > "$SCRIPT_DIR/.env" << 'EOF'
# R&D System Environment Variables
GROQ_API_KEY=gsk_...
GITHUB_TOKEN=ghp_...
SENDGRID_API_KEY=SG....
REPORT_EMAIL=your@email.com
DASHBOARD_API_KEY=your-secure-random-key-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
EOF
    echo "✅ Created .env — add your API keys"
fi

# Create directories
mkdir -p "$SCRIPT_DIR/rd_reports"
mkdir -p "$SCRIPT_DIR/rd_upgrades"
echo "✅ Created rd_reports/ and rd_upgrades/ directories"

# Install cron job (every Monday at 8am)
CRON_CMD="0 8 * * MON cd \"$SCRIPT_DIR\" && $PYTHON rd_system.py >> rd_cron.log 2>&1"
(crontab -l 2>/dev/null | grep -v "rd_system.py"; echo "$CRON_CMD") | crontab -
echo "✅ Cron job installed: every Monday at 8:00am"

echo ""
echo "🚀 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your API keys"
echo "  2. Run first cycle: python rd_system.py --force"
echo "  3. Start dashboard: python rd_api.py"
echo "  4. Open: http://localhost:8003"
echo ""
