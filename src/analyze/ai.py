#!/usr/bin/env python3
"""
ai.py — Unified LLM interface for WeChat Analysis Tool.

Supports 5 providers via a single LLMClient class:
  - OpenAI  (GPT-4o, GPT-4o-mini)
  - Anthropic (Claude 3.5 Sonnet / Haiku)
  - Google  (Gemini 1.5 Flash / Pro)
  - DeepSeek (deepseek-chat / deepseek-reasoner)
  - Qwen    (qwen-max / qwen-plus)

All providers share the same call interface:
  client = LLMClient(config)
  result = client.chat(messages, max_tokens=1500)

Usage:
  from src.analyze.ai import LLMClient, build_analysis_prompt
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Optional

# ─────────────────────────────────────────────
#  Provider routing table
# ─────────────────────────────────────────────

PROVIDER_DEFAULTS = {
    "openai": {
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "chat_path": "/chat/completions",
        "auth_header": "Bearer",
        "request_format": "openai",
    },
    "anthropic": {
        "api_base": "https://api.anthropic.com",
        "model": "claude-3-5-sonnet-20241022",
        "chat_path": "/v1/messages",
        "auth_header": "x-api-key",
        "request_format": "anthropic",
        "extra_headers": {"anthropic-version": "2023-06-01"},
    },
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-1.5-flash",
        "chat_path": None,  # dynamic: /models/{model}:generateContent
        "auth_header": "query_param",  # uses ?key= instead of header
        "request_format": "gemini",
    },
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "chat_path": "/chat/completions",
        "auth_header": "Bearer",
        "request_format": "openai",  # DeepSeek is OpenAI-compatible
    },
    "qwen": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max",
        "chat_path": "/chat/completions",
        "auth_header": "Bearer",
        "request_format": "openai",  # DashScope compatible-mode is OpenAI-compatible
    },
}


class LLMClient:
    """
    Unified LLM client. Initialize once, call chat() repeatedly.
    Handles auth, request formatting, and response parsing per provider.
    """

    def __init__(self, config: dict):
        """
        config: the full config dict (loaded from config.json).
        Reads config['llm']['provider'] and config['llm']['providers'][provider].
        """
        llm_cfg = config.get("llm", {})
        self.provider = llm_cfg.get("provider", "openai")

        provider_cfg = llm_cfg.get("providers", {}).get(self.provider, {})
        defaults = PROVIDER_DEFAULTS.get(self.provider, {})

        self.api_key = provider_cfg.get("api_key", "") or os.environ.get(
            f"{self.provider.upper()}_API_KEY", ""
        )
        self.model = provider_cfg.get("model") or defaults.get("model", "")
        self.api_base = (provider_cfg.get("api_base") or defaults.get("api_base", "")).rstrip("/")
        self.chat_path = defaults.get("chat_path")
        self.auth_header = defaults.get("auth_header", "Bearer")
        self.request_format = defaults.get("request_format", "openai")
        self.extra_headers = defaults.get("extra_headers", {})

        if not self.api_key:
            raise ValueError(
                f"No API key for provider '{self.provider}'. "
                f"Set it in config.json under llm.providers.{self.provider}.api_key "
                f"or via env var {self.provider.upper()}_API_KEY"
            )

        print(f"  🔌 LLM provider: {self.provider} / {self.model}")

    def chat(
        self,
        messages: list,
        max_tokens: int = 1500,
        temperature: float = 0.3,
        system: Optional[str] = None,
        retry: int = 3,
    ) -> str:
        """
        Send a chat request. Returns the assistant reply as a string.

        messages: list of {"role": "user"|"assistant", "content": "..."}
        system:   optional system prompt (handled per-provider)
        """
        for attempt in range(retry):
            try:
                if self.request_format == "anthropic":
                    return self._call_anthropic(messages, max_tokens, temperature, system)
                elif self.request_format == "gemini":
                    return self._call_gemini(messages, max_tokens, temperature, system)
                else:
                    return self._call_openai_compat(messages, max_tokens, temperature, system)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    wait = 2 ** attempt
                    print(f"  ⚠️  Rate limited, retrying in {wait}s…")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"HTTP {e.code} from {self.provider}: {body}") from e
            except Exception as e:
                if attempt < retry - 1:
                    time.sleep(1)
                    continue
                raise
        raise RuntimeError(f"All {retry} attempts failed for {self.provider}")

    # ──────────────────────────────────────────
    #  OpenAI-compatible (OpenAI, DeepSeek, Qwen)
    # ──────────────────────────────────────────

    def _call_openai_compat(self, messages, max_tokens, temperature, system):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)

        payload = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        url = self.api_base + (self.chat_path or "/chat/completions")
        response = self._http_post(url, payload, headers)
        return response["choices"][0]["message"]["content"]

    # ──────────────────────────────────────────
    #  Anthropic (Claude)
    # ──────────────────────────────────────────

    def _call_anthropic(self, messages, max_tokens, temperature, system):
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        headers.update(self.extra_headers)

        url = self.api_base + "/v1/messages"
        response = self._http_post(url, payload, headers)
        return response["content"][0]["text"]

    # ──────────────────────────────────────────
    #  Google Gemini
    # ──────────────────────────────────────────

    def _call_gemini(self, messages, max_tokens, temperature, system):
        # Gemini uses "parts" format and ?key= auth
        contents = []
        if system:
            contents.append({
                "role": "user",
                "parts": [{"text": f"[System context]: {system}"}]
            })
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})

        role_map = {"user": "user", "assistant": "model"}
        for m in messages:
            contents.append({
                "role": role_map.get(m["role"], "user"),
                "parts": [{"text": m["content"]}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }
        }

        model_slug = self.model.replace("models/", "")
        url = f"{self.api_base}/models/{model_slug}:generateContent?key={self.api_key}"
        response = self._http_post(url, payload, {"Content-Type": "application/json"})
        return response["candidates"][0]["content"]["parts"][0]["text"]

    # ──────────────────────────────────────────
    #  HTTP helper
    # ──────────────────────────────────────────

    def _http_post(self, url: str, payload: dict, headers: dict) -> dict:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))


# ─────────────────────────────────────────────
#  Prompt builders
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert relationship analyst. You analyze WeChat chat history to produce
structured, evidence-based insights about the user's social relationships. Always respond in JSON.
Never invent evidence — base all analysis strictly on the messages provided. Be concise, honest, and specific."""


def build_affinity_prompt(contact_name: str, messages: list, meta: dict) -> tuple:
    """
    Build messages list for affinity analysis.
    Returns (system_prompt, user_message_content).
    """
    # Truncate messages to avoid token overflow
    sample = messages[:30]
    msg_block = "\n".join([
        f"[{'Me' if m.get('is_me') else contact_name}] {m.get('text','')}"
        for m in sample if m.get('text')
    ])

    user_content = f"""Analyze this WeChat chat history between me and {contact_name}.

Total messages: {meta.get('total', 0)}
Days active: {meta.get('days_span', 0)}
My initiation rate: {meta.get('init_rate', 0):.0%}
Average message length: {meta.get('avg_len', 0):.0f} chars

Sample messages (most recent 30):
---
{msg_block}
---

Respond ONLY with this JSON structure (no markdown, no extra text):
{{
  "affinity_score": <0-100, overall closeness>,
  "dimensions": {{
    "frequency": <0-100>,
    "depth": <0-100>,
    "responsiveness": <0-100>,
    "initiative": <0-100>,
    "emotional_tone": <0-100>,
    "humor": <0-100>,
    "vulnerability": <0-100>,
    "mutual_interest": <0-100>
  }},
  "top_topics": [
    {{"name": "<topic>", "weight": <0-100>, "evidence": "<quote from messages>"}}
  ],
  "sentiment": "<positive|neutral|mixed|negative>",
  "relationship_type": "<close friend|acquaintance|colleague|romantic interest|family|other>",
  "summary": "<2 sentence relationship summary>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "growth_areas": ["<area 1>", "<area 2>"]
}}"""

    return SYSTEM_PROMPT, user_content


def build_strategy_prompt(contact_name: str, affinity_data: dict, messages: list) -> tuple:
    """Build messages list for strategy generation."""
    sample = messages[:20]
    msg_block = "\n".join([
        f"[{'Me' if m.get('is_me') else contact_name}] {m.get('text','')}"
        for m in sample if m.get('text')
    ])

    topics = affinity_data.get("top_topics", [])
    topics_str = ", ".join([t["name"] for t in topics[:5]])

    user_content = f"""Based on this chat analysis for {contact_name}, generate a relationship strategy.

Affinity score: {affinity_data.get('affinity_score', 0)}/100
Relationship type: {affinity_data.get('relationship_type', 'unknown')}
Top topics: {topics_str}
Sentiment: {affinity_data.get('sentiment', 'neutral')}

Recent messages sample:
---
{msg_block}
---

Respond ONLY with this JSON (no markdown, no extra text):
{{
  "emotional_strategy": {{
    "boosters": [
      {{"label": "<topic>", "reason": "<why it works>", "sample_msg": "<exact quote or paraphrase from chats>"}}
    ],
    "landmines": [
      {{"label": "<avoid topic>", "reason": "<why to avoid>", "sample_msg": "<evidence from chats>"}}
    ],
    "best_time_to_reach": "<morning|afternoon|evening|night|weekend>",
    "communication_style": "<brief|detailed|casual|formal|emoji-heavy|voice-preferred>",
    "current_phase": "<warming up|comfortable|close|very close|distant|cooling>",
    "next_step": "<specific actionable recommendation>"
  }},
  "deep_profile": {{
    "personality_traits": ["<trait>"],
    "values": ["<value>"],
    "interests": ["<interest>"],
    "communication_patterns": "<description>",
    "emotional_needs": "<description>",
    "notable_observations": ["<specific observation from messages>"]
  }}
}}"""

    return SYSTEM_PROMPT, user_content


def build_group_analysis_prompt(contact_name: str, room_name: str, messages: list) -> tuple:
    """Build prompt for group chat analysis."""
    msg_block = "\n".join([
        f"[{contact_name}] {m.get('text','')}"
        for m in messages[:25] if m.get('text')
    ])

    user_content = f"""Analyze {contact_name}'s messages in WeChat group "{room_name}".

Messages (up to 25 samples):
---
{msg_block}
---

Respond ONLY with this JSON:
{{
  "group_role": "<leader|contributor|observer|humorist|connector|other>",
  "dominant_topics": ["<topic>"],
  "tone": "<formal|casual|supportive|critical|humorous>",
  "key_insights": ["<specific observation based on the messages above>"],
  "sample_highlight": "<most revealing quote from the messages>"
}}"""

    return SYSTEM_PROMPT, user_content


# ─────────────────────────────────────────────
#  Main: test connection
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    config_path = os.path.join(BASE, "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(BASE, "config.default.json")

    with open(config_path) as f:
        config = json.load(f)

    print("Testing LLM connection…")
    client = LLMClient(config)
    reply = client.chat([
        {"role": "user", "content": "Reply with exactly: {\"status\": \"ok\"}"}
    ], max_tokens=20)
    print("Response:", reply)
    print("✅ Connection test passed!")
