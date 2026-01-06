#!/bin/bash

##############################################################################
# MUSIC BINGO - Digital Ocean Deployment Script
# 
# This script automates the deployment process to a Digital Ocean droplet
# Run from your LOCAL machine, not on the server
##############################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "🚀 MUSIC BINGO - DIGITAL OCEAN DEPLOYMENT"
echo "============================================================"
echo ""

# Check if server IP is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Server IP address required${NC}"
    echo "Usage: ./deploy.sh SERVER_IP [DOMAIN]"
    echo "Example: ./deploy.sh 157.230.45.123"
    echo "Example: ./deploy.sh 157.230.45.123 musicbingo.perfectdj.co.uk"
    exit 1
fi

SERVER_IP=$1
DOMAIN=${2:-$SERVER_IP}  # Use IP if domain not provided
SERVER_USER="root"
PROJECT_DIR="/var/www/music-bingo"

echo -e "${GREEN}📋 Deployment Configuration:${NC}"
echo "   Server IP: $SERVER_IP"
echo "   Domain: $DOMAIN"
echo "   Remote Directory: $PROJECT_DIR"
echo ""

# Confirm before proceeding
read -p "Continue with deployment? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "============================================================"
echo "📦 Step 1/6: Creating deployment package"
echo "============================================================"

# Create temporary directory for deployment
TEMP_DIR=$(mktemp -d)
echo "Creating package in: $TEMP_DIR"

# Copy files (exclude .git, node_modules, etc.)
rsync -av --exclude='.git' \
          --exclude='__pycache__' \
          --exclude='*.pyc' \
          --exclude='.DS_Store' \
          --exclude='.vscode' \
          --exclude='.env' \
          . "$TEMP_DIR/"

echo "✓ Package created"

echo ""
echo "============================================================"
echo "🔑 Step 2/6: Checking SSH connection"
echo "============================================================"

if ssh -o ConnectTimeout=5 $SERVER_USER@$SERVER_IP "echo '✓ SSH connection successful'"; then
    echo "✓ Connected to server"
else
    echo -e "${RED}✗ Cannot connect to server${NC}"
    echo "Please check:"
    echo "  1. Server IP is correct: $SERVER_IP"
    echo "  2. SSH key is configured"
    echo "  3. Server is running"
    exit 1
fi

echo ""
echo "============================================================"
echo "📤 Step 3/6: Uploading files to server"
echo "============================================================"

# Create project directory on server
ssh $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR"

# Upload files
echo "Uploading files..."
rsync -avz --delete \
      --exclude='.git' \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      --exclude='.DS_Store' \
      --exclude='.env' \
      "$TEMP_DIR/" $SERVER_USER@$SERVER_IP:$PROJECT_DIR/

echo "✓ Files uploaded"

# Cleanup temp directory
rm -rf "$TEMP_DIR"

echo ""
echo "============================================================"
echo "⚙️  Step 4/6: Installing dependencies on server"
echo "============================================================"

ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /var/www/music-bingo/backend

# Install Python packages
echo "Installing Python packages..."
pip3 install -r requirements.txt

echo "✓ Dependencies installed"
ENDSSH

echo ""
echo "============================================================"
echo "📝 Step 5/6: Configuring environment"
echo "============================================================"

echo -e "${YELLOW}⚠️  IMPORTANT: Configure environment variables${NC}"
echo ""
echo "You need to manually edit .env on the server:"
echo ""
echo "ssh $SERVER_USER@$SERVER_IP"
echo "cd $PROJECT_DIR/backend"
echo "nano .env"
echo ""
echo "Add your ElevenLabs API key:"
echo "ELEVENLABS_API_KEY=sk_your_actual_key_here"
echo "ELEVENLABS_VOICE_ID=cgSgspJ2msm6clMCkdW9"
echo ""
read -p "Press Enter when you've configured the .env file..."

echo ""
echo "============================================================"
echo "🎵 Step 6/6: Generating game assets"
echo "============================================================"

ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /var/www/music-bingo

# Generate song pool
echo "Generating song pool (this takes 2-3 minutes)..."
python3 backend/generate_pool.py

# Generate bingo cards
echo "Generating bingo cards..."
python3 backend/generate_cards.py

echo "✓ Game assets generated"
ENDSSH

echo ""
echo "============================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "============================================================"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo ""
echo "1. Set up Supervisor to keep the app running:"
echo "   Follow instructions in DEPLOYMENT.md (Step 6)"
echo ""
echo "2. Configure Nginx as reverse proxy:"
echo "   Follow instructions in DEPLOYMENT.md (Step 7)"
echo ""
echo "3. Test your deployment:"
echo "   http://$DOMAIN"
echo ""
echo "For detailed instructions, see: DEPLOYMENT.md"
echo ""
echo "============================================================"
