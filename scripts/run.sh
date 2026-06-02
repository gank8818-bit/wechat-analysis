#!/bin/bash
# run.sh — Full analysis pipeline

set -e  # Exit on error

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

echo "🔍 WeChat Analysis Tool"
echo "======================================"
echo ""

# Check config
if [ ! -f "config.json" ]; then
    echo "⚠️  config.json not found, using default config"
    cp config.default.json config.json
    echo "📝  Please edit config.json with your settings"
fi

# Read mode from config
MODE=$(python3 -c "import json; print(json.load(open('config.json'))['mode'])" 2>/dev/null || echo "algorithm")
echo "🎯 Mode: $MODE"
echo ""

# Step 1: Extract contacts
echo "📊 Step 1/4: Extracting contacts..."
python3 src/extract/extract_contacts.py

if [ $? -ne 0 ]; then
    echo "❌ Contact extraction failed"
    exit 1
fi

# Step 2: Extract group chats
echo ""
echo "💬 Step 2/4: Extracting group chats..."
python3 src/extract/extract_group_chats.py || echo "⚠️  Group chat extraction skipped (no data)"

# Step 3: Run analysis (algorithm or AI)
echo ""
echo "🧠 Step 3/4: Running analysis ($MODE mode)..."
python3 src/analyze/analyzer.py

if [ $? -ne 0 ]; then
    echo "❌ Analysis failed"
    exit 1
fi

# Step 4: Build frontend
echo ""
echo "🏗️  Step 4/4: Building frontend..."
node src/build/build_strategy.js

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

# Done!
echo ""
echo "✅ Analysis complete!"
echo "======================================"
echo "📱 Open the report:"
echo "   open data/output/affinity_report.html"
echo ""
echo "🎉 Done!"
