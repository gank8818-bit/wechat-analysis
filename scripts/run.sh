#!/usr/bin/env bash
# run.sh — Full pipeline: extract → analyze (LLM) → build → open report
set -e

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"

# ── Check config
if [ ! -f config.json ]; then
  echo "⚠️  config.json not found."
  echo "   Run: cp config.default.json config.json"
  echo "   Then add your LLM API key."
  exit 1
fi

PROVIDER=$($PYTHON -c "import json; c=json.load(open('config.json')); print(c.get('llm',{}).get('provider','?'))" 2>/dev/null || echo "?")
echo "🔌 Provider: $PROVIDER"

# ── Step 1: Extract raw data from WeChat DB
echo ""
echo "📥 Step 1/3: Extracting contacts from WeChat DB…"
$PYTHON src/extract/extract_contacts.py
$PYTHON src/extract/extract_group_chats.py

# ── Step 2: LLM analysis
echo ""
echo "🤖 Step 2/3: Running LLM analysis ($PROVIDER)…"
$PYTHON src/analyze/analyzer.py "$@"

# ── Step 3: Build HTML report
echo ""
echo "🏗️  Step 3/3: Building HTML report…"
$NODE src/build/build_strategy.js

# ── Open report
REPORT="data/output/affinity_report.html"
if [ -f "$REPORT" ]; then
  echo ""
  echo "✅ Done! Opening report…"
  open "$REPORT" 2>/dev/null || xdg-open "$REPORT" 2>/dev/null || echo "Report: $BASE/$REPORT"
else
  echo "✅ Done! Report: $BASE/data/output/"
fi
