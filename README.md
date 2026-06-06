# WeChat Analysis Tool 🔍

A WeChat chat analysis tool powered entirely by LLM APIs — no rule-based heuristics, no local ML models. Feed it your decrypted WeChat database and it produces deep relationship insights, communication strategies, and topic analysis for all your contacts.

## ✨ Features

- **LLM-Powered Analysis** — Affinity scoring, topic extraction, and strategy generation via your choice of 5 AI providers
- **5 Provider Options** — DeepSeek, Qwen, GPT, Claude, Gemini (switchable in one config line)
- **Contact Affinity Scoring** — Quantitative closeness scores with dimensional breakdown
- **Topic Analysis** — AI-classified conversation themes with evidence quotes
- **Group Chat Analysis** — Extract and cross-reference group chat messages per contact
- **Communication Strategy** — Personalized boosters, landmines, and next steps per contact
- **Deep Profile** — Personality traits, values, and communication patterns
- **OAuth Login** — Optional Google + GitHub login to gate access to your report
- **Interactive Dashboard** — HTML report with multi-view layout (overview, timeline, deep profile, strategy, schedule)

## 🤖 Supported LLM Providers

| Provider | Models | Notes |
|----------|--------|-------|
| **DeepSeek** | `deepseek-chat`, `deepseek-reasoner` | Best value, fast, Chinese-language excellent |
| **Qwen** | `qwen-max`, `qwen-plus`, `qwen-turbo` | Alibaba Cloud — excellent Chinese understanding |
| **OpenAI** | `gpt-4o-mini`, `gpt-4o`, `o1-mini` | Best overall quality |
| **Anthropic** | `claude-3-5-sonnet`, `claude-3-haiku` | Best for nuanced analysis |
| **Gemini** | `gemini-1.5-flash`, `gemini-1.5-pro` | Good multilingual, generous free tier |

## 📦 Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- Decrypted WeChat database files (`contact.db`, `message_0.db`, `message_1.db`)
- An API key from any of the 5 supported providers

### Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/wechat-analysis.git
cd wechat-analysis

# Install dependencies (minimal — no ML libs required)
pip install python-dateutil

# Install Node.js dependencies
npm install

# Configure
cp config.default.json config.json
```

Edit `config.json` — the only required change is your API key:

```json
{
  "llm": {
    "provider": "deepseek",
    "providers": {
      "deepseek": {
        "api_key": "sk-your-deepseek-key-here",
        "model": "deepseek-chat"
      }
    }
  }
}
```

## 🔑 Getting API Keys

| Provider | Sign up | Pricing |
|----------|---------|---------|
| **DeepSeek** | https://platform.deepseek.com | ~$0.001/1K tokens (very cheap) |
| **Qwen** | https://dashscope.aliyuncs.com | Free tier + pay-as-you-go |
| **OpenAI** | https://platform.openai.com | $0.15–$2.50/1M tokens |
| **Anthropic** | https://console.anthropic.com | $0.25–$3/1M tokens |
| **Gemini** | https://aistudio.google.com | Free tier (60 req/min) |

## 🚀 Usage

### Step 1: Prepare WeChat Data

Place your decrypted WeChat databases here:
```
data/raw/wechat-decrypted/
├── contact/
│   └── contact.db
└── message/
    ├── message_0.db
    └── message_1.db
```

### Step 2: Test API connection
```bash
python test_connection.py
```

### Step 3: Run full pipeline
```bash
./scripts/run.sh
```

This runs:
1. Extract contacts + messages from WeChat DB
2. LLM analysis for all contacts
3. Build HTML report

### Run options
```bash
# Analyze only one contact
./scripts/run.sh --contact "Alice"

# Analyze first 10 contacts
./scripts/run.sh --limit 10

# Skip contacts already analyzed (for resuming)
./scripts/run.sh --skip-analyzed

# Switch provider temporarily (overrides config.json)
LLM_PROVIDER=gemini ./scripts/run.sh
```

## 🔐 OAuth Login (Optional)

To protect your report with a login wall:

1. Create an OAuth app on [Google Cloud Console](https://console.cloud.google.com/) or [GitHub Developer Settings](https://github.com/settings/developers)
2. Set redirect URI to `http://localhost:8080/auth/google/callback` (or github)
3. Add credentials to `config.json`:

```json
{
  "oauth": {
    "enabled": true,
    "providers": {
      "google": {
        "client_id": "your-google-client-id.apps.googleusercontent.com",
        "client_secret": "your-google-client-secret"
      },
      "github": {
        "client_id": "your-github-client-id",
        "client_secret": "your-github-client-secret"
      }
    }
  }
}
```

4. Start the auth server:
```bash
python src/auth/oauth.py
```

5. Open `http://localhost:8080/auth/login` to log in

## 📁 Project Structure

```
wechat-analysis/
├── config.default.json      # Default config (commit this)
├── config.json              # Your config (gitignored)
├── test_connection.py       # Test LLM API connection
│
├── src/
│   ├── extract/
│   │   ├── extract_contacts.py    # Extract from WeChat DB
│   │   └── extract_group_chats.py # Extract group chat data
│   ├── analyze/
│   │   ├── ai.py                  # Unified LLM client (5 providers)
│   │   └── analyzer.py            # Main analysis pipeline
│   ├── auth/
│   │   └── oauth.py               # Google + GitHub OAuth
│   ├── build/
│   │   └── build_strategy.js      # Build HTML report
│   └── frontend/
│       ├── index.html             # Report template
│       ├── app.js                 # Frontend logic
│       └── style.css              # Styles
│
├── data/
│   ├── raw/wechat-decrypted/      # Your WeChat DB files (gitignored)
│   └── output/                    # Generated reports (gitignored)
│
└── scripts/
    ├── setup.sh                   # First-time setup
    └── run.sh                     # Full pipeline runner
```

## 🔒 Privacy

- All data stays local — nothing is uploaded except the text you send to the LLM API
- The LLM API receives only message text samples (not your full database)
- `data/` and `config.json` are gitignored by default — never commit your WeChat data
- OAuth session stored locally at `data/.session.json`

## 🛠 Switching Providers

One line change in `config.json`:

```json
{
  "llm": {
    "provider": "anthropic"  // change to: openai | anthropic | gemini | deepseek | qwen
  }
}
```

Each provider can have its own key and model set — they don't interfere with each other.

## 🤝 Contributing

PRs welcome. Adding a new provider takes ~20 lines in `src/analyze/ai.py` — see the `PROVIDER_DEFAULTS` dict.

## 📄 License

MIT — see [LICENSE](LICENSE)
