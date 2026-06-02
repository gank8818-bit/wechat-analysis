// app.js — WeChat Analysis Tool Frontend (Simplified Version)
// Supports algorithm mode and AI mode (configured in config.json)

'use strict';

let currentContact = null;
let allContacts = [];
let chatData = {};
let currentPanel = 'overview';

document.addEventListener('DOMContentLoaded', function() {
    // Load data
    allContacts = (typeof AFFINITY_DATA !== 'undefined' && AFFINITY_DATA.results) || [];
    chatData = typeof CHAT_DATA !== 'undefined' ? CHAT_DATA : {};

    console.log(`📊 Loaded ${allContacts.length} contacts`);

    // Init sidebar
    initSidebar();

    // Select first contact
    if (allContacts.length > 0) {
        selectContact(allContacts[0].name);
    }
});

/* ── SIDEBAR ────────────────────────────────── */
function initSidebar() {
    const list = document.getElementById('sidebar-list');
    if (!list) return;

    list.innerHTML = '';

    allContacts.forEach(function(c) {
        const div = document.createElement('div');
        div.className = 'sidebar-item';
        div.dataset.name = c.name;

        const initial = (c.name || '?')[0];
        const tc = ((c.tier || 'C').replace(/[^a-dA-D]/g, '') || 'C').toLowerCase();

        div.innerHTML = `
            <div class="sb-avatar ${tc}">${escH(initial)}</div>
            <div class="sb-info">
                <div class="sb-name">${escH(c.name)}</div>
                <div class="sb-meta">${escH(c.tier || '?')} 级 · ${c.total || 0}条</div>
            </div>
        `;

        div.onclick = function() { selectContact(c.name); };
        list.appendChild(div);
    });
}

function filterSidebar() {
    const q = (document.getElementById('sb-search') || {}).value || '';
    const items = document.querySelectorAll('.sidebar-item');

    for (let i = 0; i < items.length; i++) {
        const el = items[i];
        const nm = (el.dataset.name || '').toLowerCase();
        el.classList.toggle('hidden', q.length > 0 && nm.indexOf(q.toLowerCase()) < 0);
    }
}

function selectContact(name) {
    currentContact = null;

    for (let i = 0; i < allContacts.length; i++) {
        if (allContacts[i].name === name) {
            currentContact = allContacts[i];
            break;
        }
    }

    // Update sidebar active state
    const items = document.querySelectorAll('.sidebar-item');
    for (let i = 0; i < items.length; i++) {
        items[i].classList.toggle('active', items[i].dataset.name === name);
    }

    // Show panel
    showPanel(currentPanel || 'overview');
}

/* ── PANEL DISPATCH ───────────────────────────────── */
function showPanel(panel) {
    currentPanel = panel;

    // Update tab buttons
    const btns = document.querySelectorAll('.tab-btn');
    for (let i = 0; i < btns.length; i++) {
        btns[i].classList.toggle('active', btns[i].dataset.tab === panel);
    }

    const main = document.getElementById('panel-content');
    if (!main) return;

    if (!currentContact) {
        main.innerHTML = '<div class="empty">请选择联系人</div>';
        return;
    }

    // Render panel
    switch (panel) {
        case 'overview': main.innerHTML = renderOverview(currentContact); break;
        case 'timeline': main.innerHTML = renderTimeline(currentContact); break;
        case 'signals': main.innerHTML = renderSignals(currentContact); break;
        case 'patterns': main.innerHTML = renderPatterns(currentContact); break;
        case 'deep': main.innerHTML = renderDeep(currentContact); break;
        case 'strategy': main.innerHTML = renderStrategy(currentContact); break;
        case 'schedule': main.innerHTML = renderSchedule(currentContact); break;
        default: main.innerHTML = renderOverview(currentContact);
    }
}

/* ── UTILITIES ─────────────────────────────────── */
function escH(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escJS(s) {
    if (!s) return '';
    return s.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n');
}

function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts * 1000);
    return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function getMessages(contactName) {
    const cd = chatData[contactName];
    if (!cd || !cd.messages) return [];
    return cd.messages;
}

/* ── OVERVIEW PANEL ────────────────────────────── */
function renderOverview(r) {
    const tc = (r.tier || 'C').toLowerCase();
    const initial = (r.name || '?')[0];

    return `
        <div class="overview-header">
            <div class="overview-avatar ${tc}">${escH(initial)}</div>
            <div class="overview-info">
                <h2>${escH(r.name)} <span class="tier-badge ${tc}">${escH(r.tier || 'C')}</span></h2>
                <div class="overview-meta">
                    ${r.total || 0} 条消息 · Affinity: ${r.affinity ? r.affinity.toFixed(2) : 'N/A'}
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">📊 基本信息</div>
            <p>消息总数: ${r.total || 0}</p>
            <p>我的比例: ${(r.my_ratio * 100).toFixed(1)}%</p>
            <p>情感分数: ${r.emotion_score ? r.emotion_score.toFixed(2) : 'N/A'}</p>
            <p>提问次数: ${r.question_score || 0}</p>
            <p>最近: ${r.recency_days ? r.recency_days.toFixed(1) + ' 天前' : 'N/A'}</p>
            <p>平均长度: ${r.avg_length ? r.avg_length.toFixed(1) : 'N/A'} 字</p>
        </div>

        ${renderTopics(r)}

        ${renderGroupChatSummary(r)}
    `;
}

function renderTopics(r) {
    if (!r.top_topics || r.top_topics.length === 0) return '';

    const topics = r.top_topics.slice(0, 5);
    const items = topics.map(t => `<li>${escH(t)}</li>`).join('');

    return `
        <div class="card">
            <div class="card-title">🏷️ 热门话题</div>
            <ul>${items}</ul>
        </div>
    `;
}

function renderGroupChatSummary(r) {
    if (!r.group_chat || r.group_chat.total_msgs === 0) return '';

    const gc = r.group_chat;
    return `
        <div class="card">
            <div class="card-title">💬 群聊概要</div>
            <p>群消息: ${gc.total_msgs} 条</p>
            <p>群数量: ${gc.room_count} 个</p>
            <p>时间跨度: ${gc.days_span ? gc.days_span.toFixed(1) + ' 天' : 'N/A'}</p>
            <p>平均长度: ${gc.avg_len ? gc.avg_len.toFixed(1) : 'N/A'} 字</p>
        </div>
    `;
}

/* ── TIMELINE PANEL ────────────────────────────── */
function renderTimeline(r) {
    const msgs = getMessages(r.name);
    if (msgs.length === 0) return '<div class="empty">No message data</div>';

    // Group by date
    const groups = {};
    msgs.forEach(function(m) {
        if (!m.time) return;
        const d = new Date(m.time * 1000).toLocaleDateString('zh-CN');
        if (!groups[d]) groups[d] = [];
        groups[d].push(m);
    });

    const dates = Object.keys(groups).sort().reverse().slice(0, 10);

    let html = '<div class="timeline">';
    dates.forEach(function(date) {
        const dayMsgs = groups[date];
        html += `<div class="timeline-item">
            <div class="timeline-date">${escH(date)} (${dayMsgs.length})</div>
            <div class="timeline-content">
                ${dayMsgs.slice(0, 3).map(m => `<div>${escH((m.content || '').slice(0, 80))}</div>`).join('')}
            </div>
        </div>`;
    });
    html += '</div>';

    return html;
}

/* ── SIGNALS PANEL ────────────────────────────── */
function renderSignals(r) {
    const msgs = getMessages(r.name);
    if (msgs.length === 0) return '<div class="empty">No message data</div>';

    const theirMsgs = msgs.filter(m => m.side === '对方' || !m.is_me);
    const myMsgs = msgs.filter(m => m.side === '我' || m.is_me);

    // Count emotions
    const posCount = theirMsgs.filter(m => hasPositive(m.content)).length;
    const negCount = theirMsgs.filter(m => hasNegative(m.content)).length;

    return `
        <div class="card">
            <div class="card-title">😊 情绪信号</div>
            <p>积极消息: ${posCount} (${(posCount / theirMsgs.length * 100).toFixed(1)}%)</p>
            <p>消极消息: ${negCount} (${(negCount / theirMsgs.length * 100).toFixed(1)}%)</p>
        </div>

        <div class="card">
            <div class="card-title">❓ 提问频率</div>
            <p>TA提问: ${countQuestions(theirMsgs)} 次</p>
            <p>你提问: ${countQuestions(myMsgs)} 次</p>
        </div>
    `;
}

/* ── PATTERNS PANEL ───────────────────────────── */
function renderPatterns(r) {
    const msgs = getMessages(r.name);
    if (msgs.length === 0) return '<div class="empty">No message data</div>';

    // Analyze response times
    let totalGap = 0;
    let gapCount = 0;

    for (let i = 1; i < msgs.length; i++) {
        if (msgs[i].time && msgs[i-1].time) {
            const gap = msgs[i].time - msgs[i-1].time;
            if (gap > 0 && gap < 86400) {  // Within 24 hours
                totalGap += gap;
                gapCount++;
            }
        }
    }

    const avgGap = gapCount > 0 ? totalGap / gapCount : 0;

    return `
        <div class="card">
            <div class="card-title">⏱️ 对话节奏</div>
            <p>平均消息间隔: ${avgGap > 0 ? (avgGap / 60).toFixed(1) + ' 分钟' : 'N/A'}</p>
            <p>消息总数: ${msgs.length}</p>
        </div>
    `;
}

/* ── DEEP PROFILE PANEL ────────────────────────── */
function renderDeep(r) {
    if (!r.deep_profile) {
        return `
            <div class="card">
                <div class="card-title">🧠 深度画像</div>
                <p>暂无深度分析数据。</p>
                <p>使用 AI 模式可以获得更深入的分析。</p>
            </div>
        `;
    }

    const dp = r.deep_profile;

    return `
        <div class="deep-section">
            <h3>🧠 性格特征</h3>
            ${dp.personality ? dp.personality.map(p => `<div class="deep-item">${escH(p)}</div>`).join('') : '<p>暂无数据</p>'}
        </div>

        <div class="deep-section">
            <h3>💪 优势</h3>
            ${dp.strengths ? dp.strengths.map(s => `<div class="deep-item">${escH(s)}</div>`).join('') : '<p>暂无数据</p>'}
        </div>

        <div class="deep-section">
            <h3>⚠️ 弱点</h3>
            ${dp.weaknesses ? dp.weaknesses.map(w => `<div class="deep-item">${escH(w)}</div>`).join('') : '<p>暂无数据</p>'}
        </div>
    `;
}

/* ── STRATEGY PANEL ────────────────────────────── */
function renderStrategy(r) {
    if (!r.emotional_strategy) {
        return `
            <div class="card">
                <div class="card-title">🧠 对话策略</div>
                <p>暂无策略数据。</p>
                <p>运行完整分析以生成对话策略。</p>
            </div>
        `;
    }

    const es = r.emotional_strategy;

    return `
        ${renderBoosters(es.boosters)}
        ${renderLandmines(es.landmines)}
        ${renderDependency(es.dependency)}
        ${renderPreferences(es.preferences)}
        ${renderPrimeTime(es.prime_time)}
        ${renderStrategies(es.strategies)}
    `;
}

function renderBoosters(boosters) {
    if (!boosters || boosters.length === 0) return '';

    const items = boosters.map(b => `
        <div class="strategy-item">
            <h4>📈 ${escH(b.topic)} (+${b.boost_pct}%)</h4>
            <p>${escH(b.evidence || '')}</p>
            <p>置信度: ${escH(b.confidence || 'medium')}</p>
        </div>
    `).join('');

    return `
        <div class="strategy-section">
            <h3>📈 话题助推器</h3>
            ${items}
        </div>
    `;
}

function renderLandmines(landmines) {
    if (!landmines || landmines.length === 0) return '';

    const items = landmines.map(l => `
        <div class="strategy-item">
            <h4>⚠️ ${escH(l.topic)} (-${l.drop_pct}%)</h4>
            <p>${escH(l.evidence || '')}</p>
            <p>严重程度: ${escH(l.severity || 'medium')}</p>
        </div>
    `).join('');

    return `
        <div class="strategy-section">
            <h3>⚠️ 话题地雷</h3>
            ${items}
        </div>
    `;
}

function renderDependency(dep) {
    if (!dep) return '';

    const items = (dep.breakdown || []).map(b => `<p>${escH(b)}</p>`).join('');

    return `
        <div class="strategy-section">
            <h3>🔗 依赖度分析 (${dep.score}/100 - ${escH(dep.level)})</h3>
            ${items}
        </div>
    `;
}

function renderPreferences(prefs) {
    if (!prefs) return '';

    const likes = (prefs.likes || []).map(l => `<li>${escH(l.topic)}: ${escH(l.evidence || '')}</li>`).join('');
    const dislikes = (prefs.dislikes || []).map(d => `<li>${escH(d.topic)}: ${escH(d.evidence || '')}</li>`).join('');

    return `
        <div class="strategy-section">
            <h3>❤️ TA 喜欢</h3>
            <ul>${likes || '<li>暂无数据</li>'}</ul>
        </div>
        <div class="strategy-section">
            <h3>💔 TA 不喜欢</h3>
            <ul>${dislikes || '<li>暂无数据</li>'}</ul>
        </div>
    `;
}

function renderPrimeTime(pt) {
    if (!pt) return '';

    return `
        <div class="strategy-section">
            <h3>⏰ 最佳时间</h3>
            <p>最佳时段: ${escH(pt.best_window || pt.best_hour || 'N/A')}</p>
            <p>最差时段: ${escH(pt.worst_hour || 'N/A')}</p>
            <p>${escH(pt.evidence || '')}</p>
        </div>
    `;
}

function renderStrategies(strategies) {
    if (!strategies || strategies.length === 0) return '';

    const items = strategies.map(s => `
        <div class="strategy-item">
            <h4>${escH(s.name)} (风险: ${escH(s.risk)})</h4>
            <p><strong>方法:</strong> ${escH(s.method)}</p>
            <p><strong>原因:</strong> ${escH(s.why)}</p>
            <p><strong>时机:</strong> ${escH(s.timing)}</p>
        </div>
    `).join('');

    return `
        <div class="strategy-section">
            <h3>🧠 推荐策略</h3>
            ${items}
        </div>
    `;
}

/* ── SCHEDULE PANEL ────────────────────────────── */
function renderSchedule(r) {
    const msgs = getMessages(r.name);
    if (msgs.length === 0) return '<div class="empty">No message data</div>';

    // Count by hour
    const hourCounts = {};
    for (let h = 0; h < 24; h++) hourCounts[h] = 0;

    msgs.forEach(function(m) {
        if (!m.time) return;
        const h = new Date(m.time * 1000).getHours();
        hourCounts[h]++;
    });

    // Find best hours
    let bestHour = 12, bestCount = 0;
    for (let h = 0; h < 24; h++) {
        if (hourCounts[h] > bestCount) {
            bestCount = hourCounts[h];
            bestHour = h;
        }
    }

    // Build table
    let tableRows = '';
    for (let h = 0; h < 24; h++) {
        if (hourCounts[h] > 0) {
            tableRows += `
                <tr>
                    <td>${h.toString().padStart(2, '0')}:00</td>
                    <td>${hourCounts[h]}</td>
                </tr>
            `;
        }
    }

    return `
        <div class="card">
            <div class="card-title">📅 对话时间表</div>
            <p>最佳联系时间: ${bestHour.toString().padStart(2, '0')}:00 (${bestCount} 条消息)</p>
        </div>

        <div class="card">
            <div class="card-title">⏰ 小时分布</div>
            <table class="schedule-table">
                <tr><th>时间</th><th>消息数</th></tr>
                ${tableRows}
            </table>
        </div>
    `;
}

/* ── HELPER FUNCTIONS ───────────────────────────── */
function hasPositive(content) {
    if (!content) return false;
    const lower = content.toLowerCase();
    const posWords = ['好', '棒', '厉害', 'love', 'great', 'awesome', 'nice', '喜欢', '开心', '哈哈'];
    return posWords.some(w => lower.indexOf(w) >= 0);
}

function hasNegative(content) {
    if (!content) return false;
    const lower = content.toLowerCase();
    const negWords = ['烦', '累', '难', 'bad', 'hate', 'tired', '压力', '忙'];
    return negWords.some(w => lower.indexOf(w) >= 0);
}

function countQuestions(msgs) {
    return msgs.filter(m => {
        const c = (m.content || '').toLowerCase();
        return c.indexOf('?') >= 0 || c.indexOf('？') >= 0 ||
               c.indexOf('什么') >= 0 || c.indexOf('why') >= 0 ||
               c.indexOf('how') >= 0 || c.indexOf('when') >= 0;
    }).length;
}
