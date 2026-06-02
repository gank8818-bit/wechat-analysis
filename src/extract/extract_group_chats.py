#!/usr/bin/env python3
"""
extract_group_chats.py — Extract group chat messages for matched contacts.

Matches chatroom senders with contacts via wxid/alias/remark/nick_name mapping.
Handles binary message_content, builds evidence for each contact.

Usage:
  python src/extract/extract_group_chats.py
"""

import sqlite3, hashlib, os, re, json, sys
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(BASE, 'config.default.json')) as f:
    DEFAULT_CFG = json.load(f)

CONFIG = DEFAULT_CFG.copy()
config_path = os.path.join(BASE, 'config.json')
if os.path.exists(config_path):
    with open(config_path) as f:
        CONFIG.update(json.load(f))

WECHAT_PATH = CONFIG.get('wechat', {}).get('decrypted_path', os.path.join(BASE, 'data/raw/wechat-decrypted'))
OUTPUT_PATH = CONFIG.get('wechat', {}).get('output_path', os.path.join(BASE, 'data/output'))

MSG_DB_0 = os.path.join(WECHAT_PATH, 'message/message_0.db')
MSG_DB_1 = os.path.join(WECHAT_PATH, 'message/message_1.db')
CONTACT_DB = os.path.join(WECHAT_PATH, 'contact/contact.db')


def safe_decode(val):
    """Handle both bytes and str message_content."""
    if val is None:
        return ''
    if isinstance(val, bytes):
        try:
            s = val.decode('utf-8', errors='replace')
        except:
            return ''
        # Remove binary junk (non-printable chars)
        s = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', s)
        return s
    return str(val)


def get_tables(db_path):
    """Get all Msg_* tables from a database."""
    if not os.path.exists(db_path):
        return []
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
        tables = [r[0] for r in cur.fetchall()]
        con.close()
        return tables
    except Exception as e:
        print(f"  Error reading {db_path}: {e}")
        return []


def load_contact_map():
    """Load contact display names from contact DB."""
    conn = sqlite3.connect(CONTACT_DB)
    c = conn.cursor()
    c.execute("SELECT username, remark, nick_name, alias FROM contact")
    contact_rows = c.fetchall()
    conn.close()

    # Build wxid → display name mapping
    wxid_display = {}
    for username, remark, nick_name, alias in contact_rows:
        wxid_display[username] = remark or nick_name or alias or username

    return wxid_display


def load_affinity_contacts():
    """Load contacts from affinity data (only top contacts)."""
    affinity_path = os.path.join(OUTPUT_PATH, 'data_affinity.js')
    if not os.path.exists(affinity_path):
        print(f"❌ Affinity data not found: {affinity_path}")
        print("  Run extract_contacts.py first!")
        sys.exit(1)

    with open(affinity_path) as f:
        raw = f.read()

    # Extract JSON from JS file
    match = re.search(r'var AFFINITY_DATA = ({.*?});', raw, re.DOTALL)
    if not match:
        print("❌ Could not parse affinity data")
        sys.exit(1)

    data = json.loads(match.group(1))
    return data['results']


def extract_group_messages():
    """Extract group chat messages for matched contacts."""
    print("🔍 Extracting group chat messages...")
    print("=" * 50)

    # Load contact mapping
    wxid_display = load_contact_map()

    # Load affinity contacts (the ones we're analyzing)
    affinity_contacts = load_affinity_contacts()
    print(f"📇 Loaded {len(affinity_contacts)} contacts from affinity data")

    # Build contact map (wxid → contact info)
    contact_map = {}
    for r in affinity_contacts:
        wxid = r.get('wxid', '')
        if wxid.startswith('wxid_'):
            contact_map[wxid] = r

    # Also build id → name mapping for matching
    id_to_name = {}
    for r in affinity_contacts:
        wxid = r.get('wxid', '')
        id_to_name[wxid] = r['name']
        # Also map by remark/alias/nick_name
        for key in ['remark', 'alias', 'nick_name']:
            val = r.get(key, '')
            if val:
                id_to_name[val] = r['name']

    # Find chatroom tables
    tables_0 = get_tables(MSG_DB_0)
    tables_1 = get_tables(MSG_DB_1)
    all_tables = list(set(tables_0 + tables_1))
    print(f"📊 Found {len(all_tables)} message tables")

    # Get chatroom list
    conn = sqlite3.connect(CONTACT_DB)
    c = conn.cursor()
    c.execute("SELECT username, nick_name, remark FROM contact WHERE username LIKE '%chatroom%'")
    chatrooms = [(r[0], r[1] or r[2] or r[0]) for r in c.fetchall()]
    conn.close()

    print(f"💬 Found {len(chatrooms)} chatrooms")

    # Map table → room name
    table_to_room = {}
    for username, display in chatrooms:
        md5 = hashlib.md5(username.encode('utf-8')).hexdigest()
        table_to_room[f"Msg_{md5}"] = display

    # Extract messages
    contact_msgs = defaultdict(list)

    for table in all_tables:
        if table not in table_to_room:
            continue  # Not a chatroom

        room_name = table_to_room[table]
        db_path = MSG_DB_0 if table in tables_0 else MSG_DB_1

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(f'SELECT local_type, real_sender_id, create_time, message_content FROM "{table}" ORDER BY create_time ASC')

            for ltype, sender_id, ctime, content in cur.fetchall():
                # Parse sender from message_content
                content_str = safe_decode(content)
                
                # In group chats, message_content often starts with "wxid_xxx\nmessage"
                lines = content_str.split('\n', 1)
                if len(lines) >= 2:
                    sender_wxid = lines[0].strip()
                    msg_text = lines[1]
                else:
                    sender_wxid = f"unknown_{sender_id}"
                    msg_text = content_str

                # Check if sender is in our contact map
                if sender_wxid in contact_map:
                    contact_msgs[sender_wxid].append({
                        'room': room_name,
                        'time': ctime,
                        'content': msg_text,
                        'is_me': (sender_id == 2)  # ME_USER = 2
                    })

            conn.close()
        except Exception as e:
            print(f"  Error processing {table}: {e}")
            continue

    print(f"✅ Extracted group messages for {len(contact_msgs)} contacts")

    # Build group_chat data for each contact
    for r in affinity_contacts:
        wxid = r.get('wxid', '')
        if wxid not in contact_msgs:
            r['group_chat'] = {
                'total_msgs': 0,
                'rooms': [],
                'room_count': 0,
                'days_span': 0,
                'avg_len': 0,
                'sentiment': 0,
                'top_topics': [],
                'evidence_msgs': []
            }
            continue

        msgs = contact_msgs[wxid]
        if not msgs:
            r['group_chat'] = {'total_msgs': 0, 'rooms': []}
            continue

        # Analyze group messages
        rooms = list(set(m['room'] for m in msgs))
        times = [m['time'] for m in msgs if m.get('time')]
        
        days_span = 0
        if times:
            try:
                from datetime import datetime
                t0 = min(times) / 1000  # Assuming milliseconds
                t1 = max(times) / 1000
                days_span = (t1 - t0) / 86400
            except:
                days_span = 0

        avg_len = sum(len(m.get('content', '')) for m in msgs) / len(msgs) if msgs else 0

        r['group_chat'] = {
            'total_msgs': len(msgs),
            'rooms': rooms,
            'room_count': len(rooms),
            'days_span': round(days_span, 1),
            'avg_len': round(avg_len, 1),
            'sentiment': 0,  # TODO: sentiment analysis
            'top_topics': [],  # TODO: topic classification
            'evidence_msgs': msgs[:10]  # Keep sample messages
        }

    # Save updated affinity data
    output_path = os.path.join(OUTPUT_PATH, 'data_affinity.js')
    with open(output_path, 'w') as f:
        f.write('var AFFINITY_DATA = ')
        json.dump({'results': affinity_contacts}, f, ensure_ascii=False, indent=2)
        f.write(';\n')

    print(f"💾 Saved group chat data to {output_path}")
    print(f"📊 Total group messages extracted: {sum(len(msgs) for msgs in contact_msgs.values())}")


if __name__ == '__main__':
    extract_group_messages()
