#!/usr/bin/env python3
"""
oauth.py — OAuth 2.0 authentication for WeChat Analysis Tool.

Supports:
  - Google OAuth 2.0 (OpenID Connect)
  - GitHub OAuth 2.0

Usage (standalone server mode):
  python src/auth/oauth.py

Then open: http://localhost:8080/auth/login

The server stores a session token on success.
Other scripts can call: get_session_user() to check login status.
"""

import json
import os
import sys
import hashlib
import hmac
import secrets
import time
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
SESSION_FILE = BASE / "data" / ".session.json"


# ─────────────────────────────────────────────
#  Config loader
# ─────────────────────────────────────────────

def load_config():
    cfg = BASE / "config.json"
    default = BASE / "config.default.json"
    with open(default) as f:
        config = json.load(f)
    if cfg.exists():
        with open(cfg) as f:
            override = json.load(f)
        config.update(override)
    return config


# ─────────────────────────────────────────────
#  Token / session store
# ─────────────────────────────────────────────

def save_session(user_info: dict, provider: str):
    """Save authenticated user to local session file."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    session = {
        "user": user_info,
        "provider": provider,
        "token": secrets.token_hex(32),
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + 86400 * 7,  # 7 days
    }
    SESSION_FILE.write_text(json.dumps(session, indent=2), encoding="utf-8")
    return session["token"]


def get_session_user() -> dict | None:
    """Return the logged-in user dict, or None if not logged in / expired."""
    if not SESSION_FILE.exists():
        return None
    try:
        session = json.loads(SESSION_FILE.read_text())
        if session.get("expires_at", 0) < time.time():
            SESSION_FILE.unlink(missing_ok=True)
            return None
        return session.get("user")
    except Exception:
        return None


def clear_session():
    SESSION_FILE.unlink(missing_ok=True)
    print("🔓 Session cleared")


# ─────────────────────────────────────────────
#  OAuth providers
# ─────────────────────────────────────────────

class GoogleOAuth:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_auth_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
        }
        return self.AUTH_URL + "?" + urllib.parse.urlencode(params)

    def exchange_code(self, code: str) -> dict:
        payload = urllib.parse.urlencode({
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }).encode()
        req = urllib.request.Request(
            self.TOKEN_URL, data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            self.USER_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        return {
            "id": data.get("sub"),
            "email": data.get("email"),
            "name": data.get("name"),
            "avatar": data.get("picture"),
            "provider": "google",
        }


class GitHubOAuth:
    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_URL = "https://api.github.com/user"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_auth_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",
            "state": state,
        }
        return self.AUTH_URL + "?" + urllib.parse.urlencode(params)

    def exchange_code(self, code: str) -> dict:
        payload = json.dumps({
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }).encode()
        req = urllib.request.Request(
            self.TOKEN_URL, data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            self.USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json"
            }
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        return {
            "id": str(data.get("id")),
            "email": data.get("email"),
            "name": data.get("name") or data.get("login"),
            "avatar": data.get("avatar_url"),
            "provider": "github",
        }


# ─────────────────────────────────────────────
#  Lightweight HTTP callback server
# ─────────────────────────────────────────────

_pending_states = {}  # state -> provider


def _make_handler(config: dict):
    oauth_cfg = config.get("oauth", {})
    providers_cfg = oauth_cfg.get("providers", {})
    port = config.get("frontend", {}).get("port", 8080)

    google = None
    if providers_cfg.get("google", {}).get("client_id"):
        g = providers_cfg["google"]
        google = GoogleOAuth(g["client_id"], g["client_secret"], g.get("redirect_uri", f"http://localhost:{port}/auth/google/callback"))

    github = None
    if providers_cfg.get("github", {}).get("client_id"):
        gh = providers_cfg["github"]
        github = GitHubOAuth(gh["client_id"], gh["client_secret"], gh.get("redirect_uri", f"http://localhost:{port}/auth/github/callback"))

    class OAuthHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # suppress default logs

        def send_html(self, html: str, code: int = 200):
            body = html.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            params = dict(urllib.parse.parse_qsl(parsed.query))

            # ── Login page
            if path == "/" or path == "/auth/login":
                providers_html = ""
                if google:
                    state = secrets.token_hex(16)
                    _pending_states[state] = "google"
                    url = google.get_auth_url(state)
                    providers_html += f'<a href="{url}" class="btn google">Sign in with Google</a>'
                if github:
                    state = secrets.token_hex(16)
                    _pending_states[state] = "github"
                    url = github.get_auth_url(state)
                    providers_html += f'<a href="{url}" class="btn github">Sign in with GitHub</a>'

                if not providers_html:
                    providers_html = "<p style='color:#f66'>No OAuth providers configured in config.json</p>"

                self.send_html(LOGIN_PAGE.replace("{{PROVIDERS}}", providers_html))

            # ── Google callback
            elif path == "/auth/google/callback":
                self._handle_callback("google", params, google)

            # ── GitHub callback
            elif path == "/auth/github/callback":
                self._handle_callback("github", params, github)

            # ── Status / current user
            elif path == "/auth/status":
                user = get_session_user()
                self.send_html(
                    f"<pre>{json.dumps({'logged_in': bool(user), 'user': user}, indent=2)}</pre>"
                )

            # ── Logout
            elif path == "/auth/logout":
                clear_session()
                self.send_html('<p>Logged out. <a href="/auth/login">Login again</a></p>')

            else:
                self.send_html("<h1>404</h1>", 404)

        def _handle_callback(self, provider_name: str, params: dict, provider):
            code = params.get("code")
            state = params.get("state")
            error = params.get("error")

            if error:
                self.send_html(ERROR_PAGE.replace("{{ERROR}}", error))
                return

            if not code or state not in _pending_states:
                self.send_html(ERROR_PAGE.replace("{{ERROR}}", "Invalid state parameter"))
                return

            expected_provider = _pending_states.pop(state)
            if expected_provider != provider_name:
                self.send_html(ERROR_PAGE.replace("{{ERROR}}", "Provider mismatch"))
                return

            try:
                token_data = provider.exchange_code(code)
                access_token = token_data.get("access_token")
                if not access_token:
                    raise ValueError(f"No access_token in response: {token_data}")

                user_info = provider.get_user_info(access_token)
                save_session(user_info, provider_name)

                print(f"\n✅ Logged in: {user_info.get('name')} ({user_info.get('email')}) via {provider_name}")
                self.send_html(SUCCESS_PAGE.replace("{{USER}}", json.dumps(user_info, indent=2, ensure_ascii=False)))

            except Exception as e:
                print(f"\n❌ OAuth error ({provider_name}): {e}")
                self.send_html(ERROR_PAGE.replace("{{ERROR}}", str(e)))

    return OAuthHandler


LOGIN_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Login — WeChat Analysis</title>
<style>
body{font-family:system-ui,sans-serif;background:#1a1a2e;color:#eee;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{background:#16213e;padding:40px;border-radius:16px;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,.4);width:340px}
h1{font-size:1.4rem;margin-bottom:8px}
p{color:#aaa;font-size:.9rem;margin-bottom:28px}
.btn{display:block;padding:12px 24px;margin:10px 0;border-radius:8px;text-decoration:none;font-weight:600;font-size:.95rem;transition:.2s}
.btn.google{background:#4285f4;color:#fff}
.btn.google:hover{background:#3367d6}
.btn.github{background:#24292e;color:#fff;border:1px solid #444}
.btn.github:hover{background:#3a3f44}
</style></head>
<body><div class="card">
<h1>🔍 WeChat Analysis</h1>
<p>Sign in to access the analysis tool</p>
{{PROVIDERS}}
</div></body></html>"""

SUCCESS_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Login Successful</title>
<style>body{font-family:system-ui,sans-serif;background:#1a1a2e;color:#eee;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}.card{background:#16213e;padding:40px;border-radius:16px;text-align:center;max-width:420px}h1{color:#4ade80}pre{background:#0f3460;padding:16px;border-radius:8px;text-align:left;font-size:.85rem;color:#7dd3fc}a{color:#60a5fa}</style></head>
<body><div class="card">
<h1>✅ Login Successful!</h1>
<p>You're now signed in. You can close this window.</p>
<pre>{{USER}}</pre>
<p><a href="/auth/status">Check status</a> · <a href="/auth/logout">Logout</a></p>
</div></body></html>"""

ERROR_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Auth Error</title>
<style>body{font-family:system-ui,sans-serif;background:#1a1a2e;color:#eee;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}.card{background:#16213e;padding:40px;border-radius:16px;text-align:center;max-width:420px}h1{color:#f87171}p{color:#fca5a5}a{color:#60a5fa}</style></head>
<body><div class="card">
<h1>❌ Authentication Error</h1>
<p>{{ERROR}}</p>
<p><a href="/auth/login">Try again</a></p>
</div></body></html>"""


def start_server(config: dict):
    port = config.get("frontend", {}).get("port", 8080)
    handler = _make_handler(config)
    server = HTTPServer(("localhost", port), handler)
    print(f"🔐 OAuth server running at http://localhost:{port}/auth/login")
    print("   Open the URL above in your browser to log in.")
    print("   Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    config = load_config()
    oauth_cfg = config.get("oauth", {})
    if not oauth_cfg.get("enabled"):
        print("ℹ️  OAuth is disabled in config.json")
        print("   Set oauth.enabled = true and add your client_id/client_secret to enable it.")
        sys.exit(0)
    start_server(config)
