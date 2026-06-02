#!/usr/bin/env python3
"""
analyzer.py — Main analyzer dispatcher.

Reads config.json to determine mode:
- 'algorithm': Pure rule-based analysis (no API needed)
- 'ai': LLM-powered analysis (requires API key)

Usage:
  python src/analyze/analyzer.py
"""

import json, os, sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(BASE, 'config.default.json')) as f:
    DEFAULT_CFG = json.load(f)

CONFIG = DEFAULT_CFG.copy()
config_path = os.path.join(BASE, 'config.json')
if os.path.exists(config_path):
    with open(config_path) as f:
        CONFIG.update(json.load(f))

MODE = CONFIG.get('mode', 'algorithm')
OUTPUT_PATH = CONFIG.get('wechat', {}).get('output_path', os.path.join(BASE, 'data/output'))


def load_affinity_data():
    """Load affinity data from JS file."""
    path = os.path.join(OUTPUT_PATH, 'data_affinity.js')
    if not os.path.exists(path):
        print(f"❌ Affinity data not found: {path}")
        print("  Run extract_contacts.py first!")
        sys.exit(1)

    with open(path) as f:
        raw = f.read()

    # Extract JSON from JS file
    import re
    match = re.search(r'var AFFINITY_DATA = ({.*?});', raw, re.DOTALL)
    if not match:
        print("❌ Could not parse affinity data")
        sys.exit(1)

    return json.loads(match.group(1))


def save_affinity_data(data):
    """Save affinity data to JS file."""
    path = os.path.join(OUTPUT_PATH, 'data_affinity.js')
    with open(path, 'w') as f:
        f.write('var AFFINITY_DATA = ')
        json.dump({'results': data}, f, ensure_ascii=False, indent=2)
        f.write(';\n')
    print(f"💾 Saved: {path}")


def run_algorithm_mode(data):
    """Run pure algorithm analysis (no API needed)."""
    print("🤖 Running algorithm mode...")
    print("=" * 50)

    # Import algorithm module
    import importlib.util
    algo_path = os.path.join(BASE, 'src/analyze/algorithm.py')
    spec = importlib.util.spec_from_file_location('algorithm', algo_path)
    algo = importlib.util.module_from_spec(spec)

    # Run algorithm analysis
    # (Currently, the algorithm analysis is done in extract_contacts.py)
    # This function would do additional analysis if needed

    print("✅ Algorithm mode complete")
    return data


def run_ai_mode(data):
    """Run AI-powered analysis."""
    print("🧠 Running AI mode...")
    print("=" * 50)

    ai_config = CONFIG.get('ai', {})
    provider = ai_config.get('provider', 'openai')
    api_key = ai_config.get('api_key', '')
    model = ai_config.get('model', 'gpt-4o-mini')

    if not api_key:
        print("❌ No API key found in config!")
        print("  Please set 'ai.api_key' in config.json")
        sys.exit(1)

    # Import AI module
    import importlib.util
    ai_path = os.path.join(BASE, 'src/analyze/ai.py')
    spec = importlib.util.spec_from_file_location('ai', ai_path)
    ai_module = importlib.util.module_from_spec(spec)

    # Run AI analysis
    # TODO: Implement AI analysis
    print("⚠️  AI mode not yet fully implemented")
    print("  Falling back to algorithm mode...")

    return run_algorithm_mode(data)


def main():
    """Main analysis pipeline."""
    print(f"🔍 WeChat Analysis Tool — Mode: {MODE.upper()}")
    print("=" * 50)

    # Load data
    data = load_affinity_data()
    results = data.get('results', [])
    print(f"📊 Loaded {len(results)} contacts")

    # Dispatch to appropriate mode
    if MODE == 'ai':
        results = run_ai_mode(results)
    else:
        results = run_algorithm_mode(results)

    # Save results
    save_affinity_data(results)

    print("\n🎉 Analysis complete!")
    print(f"  Next step: node src/build/build_strategy.js")


if __name__ == '__main__':
    main()
