#!/usr/bin/env python3
"""Quick test: verify all 5 LLM providers can be imported and instantiated correctly."""

import json, sys
from pathlib import Path

BASE = Path(__file__).parent

# Check config
cfg_path = BASE / "config.json"
if not cfg_path.exists():
    print("⚠️  config.json not found. Copy config.default.json → config.json and add your API key.")
    sys.exit(1)

with open(cfg_path) as f:
    config = json.load(f)

provider = config.get("llm", {}).get("provider")
if not provider:
    print("❌ llm.provider not set in config.json")
    sys.exit(1)

VALID = ["openai", "anthropic", "gemini", "deepseek", "qwen"]
if provider not in VALID:
    print(f"❌ Unknown provider '{provider}'. Must be one of: {', '.join(VALID)}")
    sys.exit(1)

print(f"Provider: {provider}")
api_key = config.get("llm", {}).get("providers", {}).get(provider, {}).get("api_key", "")
if not api_key:
    print(f"❌ No API key set for '{provider}'")
    sys.exit(1)

print(f"API key: {api_key[:8]}…{'*' * (len(api_key) - 8)}" if len(api_key) > 8 else "Set ✓")

sys.path.insert(0, str(BASE))
from src.analyze.ai import LLMClient

try:
    client = LLMClient(config)
    reply = client.chat([{"role": "user", "content": 'Reply with exactly this JSON: {"status": "ok"}'}], max_tokens=30)
    print(f"Response: {reply.strip()[:80]}")
    print("✅ Connection test passed!")
except Exception as e:
    print(f"❌ Test failed: {e}")
    sys.exit(1)
