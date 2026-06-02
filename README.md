# WeChat Analysis Tool 🔍

A powerful WeChat chat analysis tool that helps you understand your relationships and conversation patterns. Supports **two analysis modes**: pure algorithm (free, fast, offline) and AI-powered (accurate, context-aware).

## ✨ Features

- **Contact Affinity Scoring** — Quantitatively measure relationship closeness
- **Topic Analysis** — Auto-classify conversations into 16 categories (gaming, school, daily life, emotions, etc.)
- **Group Chat Analysis** — Extract and analyze group chat messages with contact mapping
- **Interactive Dashboard** — Beautiful HTML report with multiple views (overview, timeline, signals, patterns, deep profile, strategy, quiz, schedule)
- **Evidence-Based Insights** — See actual message samples with keyword highlighting
- **Two Analysis Modes**:
  - 🤖 **Algorithm Mode** — Pure rule-based analysis, no API needed
  - 🧠 **AI Mode** — LLM-powered analysis for deeper insights

## 🎯 Two Modes

### Algorithm Mode (Default)
- Uses keyword matching and rule-based scoring
- No API key required
- Fast, free, works offline
- Good for: privacy-conscious users, quick analysis

### AI Mode
- Uses LLM API (OpenAI/Claude/Local) for analysis
- More accurate topic classification
- Better sentiment analysis
- Deeper relationship insights
- Good for: professional analysis, nuanced conversations

## 📦 Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- Decrypted WeChat database files

### Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/wechat-analysis.git
cd wechat-analysis

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install

# Copy and edit config
cp config.default.json config.json
# Edit config.json with your settings
```

## 🚀 Usage

### Step 1: Prepare WeChat Data

You need decrypted WeChat database files. Use tools like [WeChatDecrypt](https://github.com/yourusername/wechat-decrypt) to decrypt your WeChat data.

Place the decrypted files in `data/raw/wechat-decrypted/`:
```
data/raw/wechat-decrypted/
├── contact/
│   └── contact.db
└── message/
    ├── message_0.db
    └── message_1.db
```

### Step 2: Configure

Edit `config.json`:
```json
{
  "mode": "algorithm",  // or "ai"
  "ai": {
    "provider": "openai",  // or "anthropic", "local"
    "api_key": "your-api-key",
    "model": "gpt-4o-mini"
  },
  "wechat": {
    "decrypted_path": "./data/raw/wechat-decrypted",
    "output_path": "./data/output"
  }
}
```

### Step 3: Run Analysis

```bash
# Full pipeline
./scripts/run.sh

# Or step by step:
# 1. Extract contacts
python src/extract/extract_contacts.py

# 2. Extract group chats
python src/extract/extract_group_chats.py

# 3. Analyze (algorithm or AI mode based on config)
python src/analyze/analyzer.py

# 4. Build frontend
node src/build/build_strategy.js

# 5. Open the report
open data/output/affinity_report.html
```

## 📊 Output

The tool generates an interactive HTML report with:

- **Overview** — Contact tiers, message counts, recency
- **Timeline** — Message history over time
- **Signals** — Emotional signals, care patterns
- **Patterns** — Conversation patterns and rhythms
- **Deep Profile** — In-depth relationship analysis
- **Strategy** — Conversation strategy with evidence
- **Quiz** — Test your knowledge of the relationship
- **Schedule** — Conversation schedule and frequency

## 🏗️ Project Structure

```
wechat-analysis/
├── config.default.json     # Default configuration
├── config.json            # Your configuration (gitignored)
├── package.json           # Node.js dependencies
├── requirements.txt       # Python dependencies
├── README.md
├── LICENSE
├── .gitignore
│
├── src/
│   ├── extract/           # Data extraction scripts
│   │   ├── extract_contacts.py
│   │   └── extract_group_chats.py
│   ├── analyze/           # Analysis modules
│   │   ├── analyzer.py   # Main dispatcher (algorithm/AI)
│   │   ├── algorithm.py  # Pure algorithm analysis
│   │   └── ai.py        # AI-powered analysis
│   ├── build/             # Build scripts
│   │   └── build_strategy.js
│   └── frontend/         # Frontend files
│       ├── index.html
│       ├── app.js
│       └── style.css
│
├── data/
│   ├── raw/              # Raw input data (gitignored)
│   └── output/           # Generated output (gitignored)
│
└── scripts/
    ├── run.sh            # Full pipeline script
    └── setup.sh          # Setup script
```

## ⚙️ Configuration

### Mode Selection
```json
{
  "mode": "algorithm"  // or "ai"
}
```

### AI Configuration
```json
{
  "ai": {
    "provider": "openai",  // "openai" | "anthropic" | "local"
    "api_key": "sk-...",
    "model": "gpt-4o-mini",
    "api_base": "https://api.openai.com/v1"  // optional for local LLM
  }
}
```

### Analysis Parameters
```json
{
  "analysis": {
    "min_messages": 50,      // Minimum messages to include contact
    "top_contacts": 35,      // Maximum contacts to analyze
    "topic_categories": [...] // Topic categories to analyze
  }
}
```

## 🔒 Privacy

- **Algorithm Mode**: All analysis happens locally, no data leaves your machine
- **AI Mode**: Message data is sent to the configured AI API. Use local LLM for privacy
- No data is collected by the tool authors
- We recommend using local LLM (Ollama, LM Studio) for sensitive data

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch
3. Submit a pull request

## 📝 License

MIT License — see [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for **personal use only**. Respect privacy and local laws. Do not use to analyze others' conversations without consent.

## 🙏 Acknowledgments

- WeChat decryption tools
- OpenAI/Anthropic for AI APIs
- The open-source community

---

**Made with ❤️ for better relationship understanding**
