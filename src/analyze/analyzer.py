#!/usr/bin/env python3
"""
analyzer.py — LLM-powered analysis dispatcher.

Reads config.json, loads extracted chat data, and runs LLM analysis
for all contacts. Produces enriched data_affinity.js with AI insights.

Usage:
  python src/analyze/analyzer.py [--contact NAME] [--limit N]
"""

import json
import os
import sys
import re
import argparse
import time
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE))

from src.analyze.ai import LLMClient, build_affinity_prompt, build_strategy_prompt, build_group_analysis_prompt


def load_config():
    cfg_path = BASE / "config.json"
    default_path = BASE / "config.default.json"
    with open(default_path) as f:
        config = json.load(f)
    if cfg_path.exists():
        with open(cfg_path) as f:
            override = json.load(f)
        _deep_merge(config, override)
    return config


def _deep_merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def load_affinity_data(output_path: str):
    path = Path(output_path) / "data_affinity.js"
    if not path.exists():
        print(f"❌ Not found: {path}")
        print("   Run extract_contacts.py first.")
        sys.exit(1)
    raw = path.read_text(encoding="utf-8")
    m = re.search(r"var AFFINITY_DATA = ({.*?});", raw, re.DOTALL)
    if not m:
        print("❌ Could not parse data_affinity.js")
        sys.exit(1)
    return json.loads(m.group(1))


def load_chat_data(output_path: str):
    path = Path(output_path) / "data_chat.js"
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    m = re.search(r"var CHAT_DATA = ({.*?});", raw, re.DOTALL)
    if not m:
        return {}
    data = json.loads(m.group(1))
    # Index by contact name
    return {c["name"]: c for c in data.get("contacts", [])}


def save_affinity_data(data: dict, output_path: str):
    Path(output_path).mkdir(parents=True, exist_ok=True)
    out = Path(output_path) / "data_affinity.js"
    out.write_text(
        "var AFFINITY_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8"
    )
    print(f"  💾 Saved: {out}")


def analyze_contact(client: LLMClient, contact: dict, chat_data: dict) -> dict:
    """Run full LLM analysis for a single contact. Returns enriched contact dict."""
    name = contact["name"]
    messages = chat_data.get(name, {}).get("messages", [])
    meta = {
        "total": contact.get("total_msgs", 0),
        "days_span": contact.get("days_span", 0),
        "init_rate": contact.get("init_rate", 0),
        "avg_len": contact.get("avg_len", 0),
    }

    print(f"  🤖 Analyzing {name}… ({meta['total']} msgs)")

    # ── Step 1: Affinity analysis
    try:
        system, user_msg = build_affinity_prompt(name, messages, meta)
        raw = client.chat([{"role": "user", "content": user_msg}], system=system, max_tokens=1500)
        ai_affinity = json.loads(_extract_json(raw))
    except Exception as e:
        print(f"    ⚠️  Affinity analysis failed: {e}")
        ai_affinity = {}

    # ── Step 2: Strategy + deep profile
    try:
        system2, user_msg2 = build_strategy_prompt(name, ai_affinity, messages)
        raw2 = client.chat([{"role": "user", "content": user_msg2}], system=system2, max_tokens=2000)
        ai_strategy = json.loads(_extract_json(raw2))
    except Exception as e:
        print(f"    ⚠️  Strategy analysis failed: {e}")
        ai_strategy = {}

    # ── Step 3: Group chat analysis (if data exists)
    group_analysis = {}
    group_data = contact.get("group_chat", {})
    if group_data and group_data.get("evidence_msgs"):
        top_room = max(group_data.get("rooms", {}).items(),
                       key=lambda x: x[1].get("count", 0),
                       default=(None, None))
        if top_room[0]:
            room_msgs = group_data["evidence_msgs"][:20]
            try:
                sys3, usr3 = build_group_analysis_prompt(name, top_room[0], room_msgs)
                raw3 = client.chat([{"role": "user", "content": usr3}], system=sys3, max_tokens=800)
                group_analysis = json.loads(_extract_json(raw3))
            except Exception as e:
                print(f"    ⚠️  Group analysis failed: {e}")

    # ── Merge results into contact record
    updated = contact.copy()
    if ai_affinity:
        updated["affinity_score"] = ai_affinity.get("affinity_score", contact.get("affinity_score", 0))
        updated["dimensions"] = ai_affinity.get("dimensions", contact.get("dimensions", {}))
        updated["top_topics"] = ai_affinity.get("top_topics", contact.get("top_topics", []))
        updated["sentiment"] = ai_affinity.get("sentiment", contact.get("sentiment", "neutral"))
        updated["relationship_type"] = ai_affinity.get("relationship_type", "")
        updated["ai_summary"] = ai_affinity.get("summary", "")
        updated["strengths"] = ai_affinity.get("strengths", [])
        updated["growth_areas"] = ai_affinity.get("growth_areas", [])

    if ai_strategy:
        updated["emotional_strategy"] = ai_strategy.get("emotional_strategy", contact.get("emotional_strategy", {}))
        updated["deep_profile"] = ai_strategy.get("deep_profile", contact.get("deep_profile", {}))

    if group_analysis:
        gc = updated.get("group_chat", {})
        gc["ai_analysis"] = group_analysis
        updated["group_chat"] = gc

    updated["ai_analyzed"] = True
    updated["ai_provider"] = client.provider
    updated["ai_model"] = client.model

    return updated


def _extract_json(text: str) -> str:
    """Extract the first JSON object from LLM response text."""
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find first { ... }
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in: {text[:200]}")
    # Find matching closing brace
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError(f"Unbalanced braces in: {text[:200]}")


def main():
    parser = argparse.ArgumentParser(description="LLM-powered WeChat chat analyzer")
    parser.add_argument("--contact", help="Analyze only this contact (by name)")
    parser.add_argument("--limit", type=int, default=0, help="Max contacts to analyze (0 = all)")
    parser.add_argument("--skip-analyzed", action="store_true",
                        help="Skip contacts already analyzed by AI")
    args = parser.parse_args()

    print("📊 WeChat Analysis — LLM Mode")
    print("=" * 50)

    config = load_config()
    output_path = config["wechat"]["output_path"]

    # Initialize LLM client
    try:
        client = LLMClient(config)
    except ValueError as e:
        print(f"\n❌ {e}")
        print("\nQuick fix:")
        print("  1. Copy config: cp config.default.json config.json")
        print("  2. Edit config.json and add your API key")
        print("  3. Set llm.provider to: openai | anthropic | gemini | deepseek | qwen")
        sys.exit(1)

    # Load data
    affinity_data = load_affinity_data(output_path)
    chat_data = load_chat_data(output_path)
    contacts = affinity_data.get("results", [])

    # Filter
    if args.contact:
        contacts = [c for c in contacts if c["name"] == args.contact]
        if not contacts:
            print(f"❌ Contact '{args.contact}' not found")
            sys.exit(1)

    if args.skip_analyzed:
        contacts = [c for c in contacts if not c.get("ai_analyzed")]
        print(f"  Skipping already-analyzed contacts. Remaining: {len(contacts)}")

    if args.limit > 0:
        contacts = contacts[:args.limit]

    print(f"  Contacts to analyze: {len(contacts)}")
    print()

    # Run analysis
    updated_contacts = []
    failed = []

    for i, contact in enumerate(contacts):
        name = contact["name"]
        print(f"[{i+1}/{len(contacts)}] {name}")
        try:
            updated = analyze_contact(client, contact, chat_data)
            updated_contacts.append(updated)
            print(f"    ✅ Done (score: {updated.get('affinity_score', '?')})")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            failed.append(name)
            updated_contacts.append(contact)  # keep original

        # Polite pause to avoid rate limits
        if i < len(contacts) - 1:
            time.sleep(0.5)

    # Merge back
    name_to_updated = {c["name"]: c for c in updated_contacts}
    all_contacts = [name_to_updated.get(c["name"], c)
                    for c in affinity_data.get("results", [])]
    # Add any contacts we didn't process
    processed_names = {c["name"] for c in updated_contacts}
    for c in affinity_data.get("results", []):
        if c["name"] not in processed_names:
            all_contacts.append(c)

    # Deduplicate
    seen = set()
    deduped = []
    for c in all_contacts:
        if c["name"] not in seen:
            seen.add(c["name"])
            deduped.append(c)

    affinity_data["results"] = deduped
    save_affinity_data(affinity_data, output_path)

    print()
    print("=" * 50)
    print(f"✅ Analysis complete: {len(updated_contacts) - len(failed)}/{len(updated_contacts)} succeeded")
    if failed:
        print(f"⚠️  Failed: {', '.join(failed)}")
    print(f"📁 Output: {output_path}/data_affinity.js")


if __name__ == "__main__":
    main()
