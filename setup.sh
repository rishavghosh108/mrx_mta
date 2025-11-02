#!/bin/bash
# Quick setup script for MTA

set -e

echo "========================================="
echo "MTA Quick Setup Script"
echo "========================================="

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p data/queue/active
mkdir -p data/queue/deferred
mkdir -p data/queue/bounce
mkdir -p data/queue/corrupt
mkdir -p data/maildir
mkdir -p data/dkim
mkdir -p logs
mkdir -p certs

# Generate self-signed certificate if none exists
if [ ! -f "certs/server.crt" ]; then
    echo "Generating self-signed TLS certificate..."
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout certs/server.key \
        -out certs/server.crt \
        -days 365 \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=mail.example.com"
    
    chmod 600 certs/server.key
    chmod 644 certs/server.crt
    echo "✓ TLS certificate generated (self-signed)"
    echo "  For production, use Let's Encrypt!"
fi

# Create default environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating default .env file..."
    cat > .env << 'EOF'
# MTA Configuration
MTA_HOSTNAME=localhost
MTA_DOMAIN=example.com

# Use non-privileged ports for testing (no sudo required)
MTA_PORT_RELAY=2525
MTA_PORT_SUBMISSION=5870
MTA_PORT_SMTPS=4650

# Admin API
MTA_ADMIN_PORT=8080
MTA_ADMIN_TOKEN=change-me-in-production

# TLS
MTA_TLS_CERT=certs/server.crt
MTA_TLS_KEY=certs/server.key
MTA_TLS_REQUIRED_SUBMISSION=True

# Authentication
MTA_AUTH_REQUIRED=True

# Logging
MTA_DEBUG=False
MTA_LOG_LEVEL=INFO

# Features (disabled for quick start)
MTA_SPF_ENABLED=False
MTA_DKIM_ENABLED=False
MTA_DMARC_ENABLED=False
MTA_RBL_ENABLED=False
MTA_GREYLIST_ENABLED=False

# Workers
MTA_DELIVERY_WORKERS=5
EOF
    echo "✓ Created .env file"
    echo "  Edit .env to customize settings"
fi

# Create default user
echo "Setting up default test user..."
mkdir -p data
cat > data/users.json << 'EOF'
{
  "test@example.com": {
    "password_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "enabled": true,
    "rate_limit": 200,
    "admin": false
  }
}
EOF
echo "✓ Default user created:"
echo "  Username: test@example.com"
echo "  Password: test"

echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "To start the MTA:"
echo "  1. Load environment:"
echo "     source venv/bin/activate"
echo "     export \$(cat .env | xargs)"
echo ""
echo "  2. Run the server:"
echo "     python app.py"
echo ""
echo "  3. In another terminal, test with:"
echo "     python test_smtp.py --user test@example.com --password test"
echo ""
echo "Ports (non-privileged for testing):"
echo "  SMTP Relay: 2525"
echo "  SMTP Submission: 5870"
echo "  Admin API: http://localhost:8080"
echo ""
echo "Admin API Token: change-me-in-production"
echo ""
echo "========================================="
