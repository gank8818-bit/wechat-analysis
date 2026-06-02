#!/usr/bin/env python3
"""
extract_contacts.py — Extract WeChat messages for contacts and compute affinity.

Supports two modes (set in config.json):
- 'algorithm': Pure rule-based analysis (no API needed)
- 'ai': LLM-powered analysis (requires API key)

Usage:
  python src/extract/extract_contacts.py
"""

import json, sqlite3, hashlib, os, sys, re, math
from collections import defaultdict
from datetime import datetime

# ─── Load Config ──────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(BASE, 'config.default.json')) as f:
    DEFAULT_CFG = json.load(f)

CONFIG = DEFAULT_CFG.copy()
config_path = os.path.join(BASE, 'config.json')
if os.path.exists(config_path):
    with open(config_path) as f:
        CONFIG.update(json.load(f))

MODE = CONFIG.get('mode', 'algorithm')
WECHAT_PATH = CONFIG.get('wechat', {}).get('decrypted_path', os.path.join(BASE, 'data/raw/wechat-decrypted'))
OUTPUT_PATH = CONFIG.get('wechat', {}).get('output_path', os.path.join(BASE, 'data/output'))
MIN_MSG = CONFIG.get('analysis', {}).get('min_messages', 50)

# ─── Paths ────────────────────────────────────────────
DB_DIR = os.path.join(WECHAT_PATH, 'message')
CONTACT_DB = os.path.join(WECHAT_PATH, 'contact/contact.db')

ME_USER = 2  # real_sender_id for 'me'

# ─── Emotion Keywords (for algorithm mode) ───────────
EMOTION = {
    'miss you': 3, '想你': 3, 'love you': 3, '爱你': 3,
    '喜欢你': 2.5, 'i like you': 2.5,
    'fuck': 2, 'sad': 2, '哭': 2, '难过': 2,
    'cooked': 1.5, '焦虑': 2, 'anxious': 2,
    'bro': 2, 'baby': 2,
    '晚安': 1, 'gn': 1, '早安': 1,
    'thank': 1.5, '谢谢': 1.5, 'help': 1.5,
    'lmao': 1.5, 'lol': 1.5, 'haha': 1, '哈哈': 1,
    'sorry': 1.5, '道歉': 1.5,
}
QRE = re.compile(r'\?|？|什么|why|how|when|where|who|你知道吗|你觉得')


def wxid_to_table(wxid):
    """Convert wxid to MD5 table name."""
    return 'Msg_' + hashlib.md5(wxid.encode()).hexdigest()


def safe_str(x):
    """Safely convert to string."""
    if isinstance(x, str):
        return x
    if isinstance(x, bytes):
        try:
            return x.decode('utf-8')
        except:
            return x.decode('utf-8', errors='replace')
    return str(x)


def load_messages(wxid):
    """Load all messages for a wxid from WeChat databases."""
    table = wxid_to_table(wxid)
    msgs = []
    for db_name in ['message_0.db', 'message_1.db']:
        db_path = os.path.join(DB_DIR, db_name)
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cur.fetchone():
                conn.close()
                continue
            cur.execute(f'SELECT local_type, real_sender_id, create_time, message_content FROM "{table}" ORDER BY create_time ASC')
            for ltype, sender_id, ctime, content in cur.fetchall():
                is_me = (sender_id == ME_USER)
                msgs.append({
                    'is_me': is_me,
                    'time': ctime,
                    'content': safe_str(content),
                    'type': ltype
                })
            conn.close()
        except Exception as e:
            print(f"  Error reading {db_name}: {e}")
    return msgs


def compute_affinity(msgs, contact_name):
    """Compute affinity score from messages."""
    if not msgs:
        return None

    my_msgs = [m for m in msgs if m['is_me']]
    their_msgs = [m for m in msgs if not m['is_me']]
    
    if not my_msgs and not their_msgs:
        return None

    total = len(msgs)
    my_ratio = len(my_msgs) / total if total > 0 else 0

    # Emotion score
    emotion_score = 0
    for m in msgs:
        ct = (m.get('content') or '').lower()
        for kw, weight in EMOTION.items():
            if kw.lower() in ct:
                emotion_score += weight * (0.5 if m['is_me'] else 1.0)
                break

    # Question score (they ask you questions)
    question_score = 0
    for m in their_msgs:
        ct = m.get('content') or ''
        if QRE.search(ct):
            question_score += 1

    # Recency score
    now = datetime.now().timestamp()
    latest_time = max(m['time'] for m in msgs) if msgs else 0
    days_ago = (now - latest_time) / 86400 if latest_time > 0 else 999
    recency_score = max(0, 10 - days_ago / 30)  # Decay over months

    # Length score
    avg_len = sum(len(m.get('content') or '') for m in msgs) / total if total > 0 else 0
    length_score = min(avg_len / 20, 5)  # Cap at 5

    # Composite affinity
    affinity = (
        emotion_score * 0.3 +
        question_score * 0.2 +
        recency_score * 0.2 +
        length_score * 0.15 +
        min(total / 100, 5) * 0.15  # Volume bonus
    )

    # Determine tier
    if affinity >= 15:
        tier = 'S'
    elif affinity >= 10:
        tier = 'A'
    elif affinity >= 5:
        tier = 'B'
    elif affinity >= 2:
        tier = 'C'
    else:
        tier = 'D'

    return {
        'name': contact_name,
        'total': total,
        'my_ratio': round(my_ratio, 3),
        'affinity': round(affinity, 2),
        'tier': tier,
        'emotion_score': round(emotion_score, 2),
        'question_score': question_score,
        'recency_days': round(days_ago, 1),
        'avg_length': round(avg_len, 1),
        'msgs': msgs  # Keep messages for further analysis
    }


def main():
    """Main extraction and analysis pipeline."""
    print(f"🔍 WeChat Analysis Tool — Mode: {MODE.upper()}")
    print(f"=" * 50)

    # Load contact database
    if not os.path.exists(CONTACT_DB):
        print(f"❌ Contact DB not found: {CONTACT_DB}")
        print("Please place decrypted WeChat files in data/raw/wechat-decrypted/")
        return

    conn = sqlite3.connect(CONTACT_DB)
    c = conn.cursor()
    c.execute("SELECT username, remark, nick_name, alias FROM contact")
    contact_rows = c.fetchall()
    conn.close()

    # Build contact list (filter for individual contacts, not chatrooms)
    contacts = []
    for username, remark, nick_name, alias in contact_rows:
        if 'chatroom' in username.lower():
            continue
        if not username.startswith('wxid_'):
            continue
        display_name = remark or nick_name or alias or username
        contacts.append({
            'wxid': username,
            'name': display_name,
            'remark': remark,
            'nick_name': nick_name,
            'alias': alias
        })

    print(f"📇 Found {len(contacts)} contacts in database")

    # Extract messages and compute affinity
    results = []
    for i, contact in enumerate(contacts):
        wxid = contact['wxid']
        name = contact['name']

        msgs = load_messages(wxid)
        if len(msgs) < MIN_MSG:
            continue

        affinity_data = compute_affinity(msgs, name)
        if affinity_data:
            affinity_data['wxid'] = wxid
            results.append(affinity_data)

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(contacts)} contacts...")

    # Sort by affinity
    results.sort(key=lambda x: x['affinity'], reverse=True)

    # Limit to top contacts
    top_n = CONFIG.get('analysis', {}).get('top_contacts', 35)
    results = results[:top_n]

    print(f"\n✅ Analysis complete: {len(results)} contacts")
    for r in results[:5]:
        print(f"  {r['tier']} | {r['name']:20s} | Affinity: {r['affinity']:5.2f} | Msgs: {r['total']}")

    # Save results
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    # Format for JS (matching existing format)
    js_data = {
        'results': [{
            'name': r['name'],
            'wxid': r['wxid'],
            'tier': r['tier'],
            'total': r['total'],
            'affinity': r['affinity'],
            'my_ratio': r['my_ratio'],
            'emotion_score': r['emotion_score'],
            'question_score': r['question_score'],
            'recency_days': r['recency_days'],
            'avg_length': r['avg_length'],
            'msgs': r['msgs'][:200]  # Limit stored messages
        } for r in results]
    }

    # Write data_affinity.js
    with open(os.path.join(OUTPUT_PATH, 'data_affinity.js'), 'w') as f:
        f.write('var AFFINITY_DATA = ')
        json.dump(js_data, f, ensure_ascii=False, indent=2)
        f.write(';\n')
    print(f"\n💾 Saved: {OUTPUT_PATH}/data_affinity.js")

    # Write data_chat.js
    chat_data = {r['name']: {'msgs': r['msgs'][:200]} for r in results}
    with open(os.path.join(OUTPUT_PATH, 'data_chat.js'), 'w') as f:
        f.write('var CHAT_DATA = ')
        json.dump(chat_data, f, ensure_ascii=False, indent=2)
        f.write(';\n')
    print(f"💾 Saved: {OUTPUT_PATH}/data_chat.js")

    print("\n🎉 Done! Run: node src/build/build_strategy.js")


if __name__ == '__main__':
    main()
