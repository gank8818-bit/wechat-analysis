#!/usr/bin/env python3
"""
algorithm.py — Pure algorithm analysis (no API needed).

Uses keyword matching and rule-based scoring for:
- Topic classification
- Sentiment analysis
- Affinity scoring

This is the default mode (fast, free, offline).
"""

import json, re, os
from collections import Counter

# ─── Topic Keywords ──────────────────────────────────
TOPIC_KEYWORDS = {
    'gaming': [
        'game', 'games', 'gaming', 'play', 'played', 'player',
        'genshin', '原神', '星铁', 'honkai', '崩坏', 'zzz', 'zenless',
        'delta', '三角洲', 'apex', 'valorant', 'lol', '英雄联盟', '王者',
        'steam', 'switch', 'ps5', 'xbox', 'minecraft', 'roblox'
    ],
    'school': [
        'school', 'homework', 'hw', 'assignment', 'project', 'essay', 'paper',
        'exam', 'test', 'quiz', 'grade', 'gpa', 'class', 'course',
        '学期', '作业', '考试', '测验', '成绩', '分数', '论文', '报告'
    ],
    'daily': [
        'today', 'tomorrow', 'yesterday', 'morning', 'afternoon', 'night',
        'wake', 'sleep', 'breakfast', 'lunch', 'dinner', 'shower',
        '今天', '明天', '昨天', '早上', '晚上', '中午', '周末'
    ],
    'emotion': [
        'feel', 'feeling', 'mood', 'happy', 'sad', 'upset', 'angry',
        'cry', 'lonely', 'anxious', 'stressed', 'depressed',
        '难受', '开心', '难过', '生气', '委屈', '想哭', '孤独', '焦虑'
    ],
    'entertainment': [
        'movie', 'movies', 'film', 'show', 'series', 'tv', 'netflix',
        'anime', 'drama', 'episode', 'season', 'binge', 'watch',
        '综艺', '电视剧', '电影', '动漫', '动画', '番剧', '追剧'
    ],
    'music': [
        'music', 'song', 'songs', 'sing', 'singer', 'band', 'album',
        'concert', 'lyrics', 'melody', 'beat', 'playlist',
        '听歌', '音乐', '歌曲', '唱歌', '歌手', '乐队', '专辑'
    ],
    'food': [
        'food', 'eat', 'ate', 'cooking', 'restaurant', 'cafe', 'coffee',
        'bubble tea', 'boba', 'milk tea', 'snack', 'dessert', 'cake',
        '美食', '吃', '饭', '餐厅', '咖啡', '奶茶', '零食', '甜品'
    ],
    'sports': [
        'sport', 'sports', 'soccer', 'football', 'basketball', 'nba',
        'tennis', 'swim', 'swimming', 'gym', 'workout', 'exercise',
        '运动', '健身', '游泳', '跑步', '瑜伽', '锻炼'
    ],
    'travel': [
        'travel', 'trip', 'vacation', 'holiday', 'flight', 'airport',
        'plane', 'hotel', 'passport', 'visa', 'tour', 'tourist',
        '旅行', '旅游', '出国', '签证', '机票', '酒店', '民宿'
    ],
    'tech': [
        'tech', 'technology', 'phone', 'iphone', 'android', 'computer',
        'laptop', 'pc', 'mac', 'ipad', 'app', 'software', 'code',
        '科技', '手机', '电脑', '笔记本', '平板', '软件', '代码', '编程'
    ],
    'work': [
        'work', 'working', 'job', 'career', 'office', 'boss', 'manager',
        'colleague', 'interview', 'hire', 'fired', 'quit', 'promotion',
        '工作', '上班', '公司', '老板', '经理', '同事', '面试'
    ],
    'complaint': [
        'hate', 'suck', 'awful', 'terrible', 'annoying', 'stupid',
        'ridiculous', 'trash', 'garbage', 'worst', 'hell', 'shit',
        '讨厌', '垃圾', '恶心', '烦人', '受不了', '无语'
    ],
    'care': [
        'care', 'how are you', 'take care', 'get well', 'rest', 'sleep well',
        'good night', 'health', 'sick', 'medicine', 'doctor', 'hospital',
        '关心', '还好吗', '注意身体', '多休息', '早点睡', '晚安', '健康'
    ],
    'money': [
        'money', 'cash', 'dollar', 'expensive', 'cheap', 'price', 'cost',
        'budget', 'save', 'spend', 'shopping', 'sale', 'discount',
        '钱', '贵', '便宜', '价格', '花费', '预算', '购物', '打折'
    ],
    'relationship': [
        'love', 'crush', 'like', 'dating', 'girlfriend', 'boyfriend',
        'ex', 'breakup', 'single', 'married', 'wedding', 'divorce',
        '感情', '恋爱', '喜欢', '暗恋', '对象', '前任', '分手', '结婚'
    ],
    'photos': [
        'photo', 'photos', 'pic', 'picture', 'image', 'selfie', 'filter',
        'edit', 'camera', 'shot', 'aesthetic', 'vibe', 'look',
        '拍照', '照片', '图片', '自拍', '滤镜', '修图', '摄影', '相机'
    ],
    'holiday': [
        'christmas', 'xmas', 'new year', 'birthday', 'halloween',
        'thanksgiving', 'valentine', 'holiday', 'festival', 'celebrate',
        '圣诞', '新年', '生日', '节日', '庆祝', '礼物', '蛋糕', '祝福'
    ]
}


def classify_topics(content):
    """Classify message content into topic categories."""
    if not content or content.startswith('http'):
        return []

    content_lower = content.lower()
    matched = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        hit_count = 0
        for keyword in keywords:
            if keyword.lower() in content_lower:
                hit_count += 1

        if hit_count >= 1:
            matched[topic] = hit_count

    return matched


def analyze_sentiment(content):
    """Analyze sentiment of message content."""
    if not content:
        return 0

    content_lower = content.lower()

    # Positive keywords
    positive = ['happy', 'good', 'great', 'excellent', 'wonderful', 'love',
                'like', 'enjoy', 'excited', '开心', '好', '喜欢', '爱', '棒']

    # Negative keywords
    negative = ['sad', 'bad', 'terrible', 'awful', 'hate', 'angry', 'cry',
                '难过', '坏', '讨厌', '生气', '哭', '伤心']

    pos_score = sum(1 for w in positive if w in content_lower)
    neg_score = sum(1 for w in negative if w in content_lower)

    return pos_score - neg_score


def extract_topic_samples(messages, topic_name, max_results=30):
    """Extract sample messages for a topic."""
    if not messages:
        return []

    keywords = TOPIC_KEYWORDS.get(topic_name, [])
    if not keywords:
        return []

    matched = []
    for msg in messages:
        content = msg.get('content', '')
        if not content:
            continue

        content_lower = content.lower()
        for keyword in keywords:
            if keyword.lower() in content_lower:
                matched.append(msg)
                break

        if len(matched) >= max_results:
            break

    return matched


def analyze_contact(contact_data):
    """Analyze a single contact's data."""
    messages = contact_data.get('msgs', [])
    if not messages:
        return contact_data

    # Classify all messages
    topic_counts = Counter()
    sentiment_scores = []

    for msg in messages:
        content = msg.get('content', '')
        topics = classify_topics(content)
        for topic in topics:
            topic_counts[topic] += 1

        sentiment = analyze_sentiment(content)
        if sentiment != 0:
            sentiment_scores.append(sentiment)

    # Top topics
    top_topics = [topic for topic, count in topic_counts.most_common(5)]

    # Average sentiment
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

    # Update contact data
    contact_data['top_topics'] = top_topics
    contact_data['sentiment'] = round(avg_sentiment, 2)
    contact_data['topic_breakdown'] = dict(topic_counts.most_common(10))

    return contact_data


def analyze_all(contacts_data):
    """Analyze all contacts."""
    print("🤖 Running algorithm analysis...")

    for i, contact in enumerate(contacts_data):
        contacts_data[i] = analyze_contact(contact)

        if (i + 1) % 10 == 0:
            print(f"  Analyzed {i + 1}/{len(contacts_data)} contacts...")

    print(f"✅ Analysis complete: {len(contacts_data)} contacts")
    return contacts_data


if __name__ == '__main__':
    # Test
    test_msgs = [
        {'content': 'Let\'s play genshin together!', 'is_me': False},
        {'content': 'I\'m so sad today', 'is_me': False},
        {'content': 'Happy birthday!', 'is_me': True}
    ]

    result = classify_topics(test_msgs[0]['content'])
    print(f"Topic classification: {result}")

    sentiment = analyze_sentiment(test_msgs[1]['content'])
    print(f"Sentiment: {sentiment}")
