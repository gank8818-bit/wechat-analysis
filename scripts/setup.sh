#!/bin/bash
# setup.sh — Setup WeChat Analysis Tool

echo "🔧 WeChat Analysis Tool — Setup"
echo "======================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 16+"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js $NODE_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Install Node.js dependencies
echo ""
echo "📦 Installing Node.js dependencies..."
npm install

# Create config.json if not exists
if [ ! -f "config.json" ]; then
    echo ""
    echo "📝 Creating config.json from default..."
    cp config.default.json config.json
    echo "⚠️  Please edit config.json with your settings"
fi

# Create directories
mkdir -p data/raw/wechat-decrypted/contact
mkdir -p data/raw/wechat-decrypted/message
mkdir -p data/output

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Edit config.json with your settings"
echo "  2. Place decrypted WeChat files in data/raw/wechat-decrypted/"
echo "  3. Run: ./scripts/run.sh"
echo "  4. Open: data/output/affinity_report.html"
echo ""
