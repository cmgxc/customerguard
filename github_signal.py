"""
CustomerGuard - Live Signal via GitHub API (Phase 4)
====================================================
Demonstrates real external-API integration. In this demo, each customer account
is mapped to a public GitHub repository that stands in for the customer's
"monitored environment." We pull a genuine live signal (recent commit activity)
from the GitHub REST API and fold it into the account's engagement picture.

Why this design: it proves the tool can integrate a real, authenticated-optional
REST API and handle live data, rate limits, and failures gracefully, while
keeping the health-model logic (in health_model.py) the star. The GitHub API is
used because it is public, well-documented, and needs no paid credentials.

Usage:
    python github_signal.py            # unauthenticated (low rate limit)
    GITHUB_TOKEN=ghp_xxx python github_signal.py   # higher rate limit

This writes live_signals.json, which enrich_accounts() merges into the portfolio.
No token is ever hard-coded; it is read from the environment only.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# Map each demo account to a public repo acting as its "monitored environment."
# These are well-known public repositories; we only READ public commit metadata.
ACCOUNT_REPOS = {
    "Meridian Health Systems": "python/cpython",
    "Coastal Credit Union": "openssl/openssl",
    "Vantage Logistics": "pallets/flask",
    "Brightwave Media": "psf/requests",
    "Ironclad Manufacturing": "torvalds/linux",
    "Northstar Energy": "kubernetes/kubernetes",
    "Cedar Point Software": "django/django",
    "Apex Biotech": "numpy/numpy",
}

GITHUB_API = "https://api.github.com/repos/{repo}/commits?since={since}&per_page=100"


def _headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "CustomerGuard-demo"}
    token = os.environ.get("GITHUB_TOKEN")  # optional; never hard-coded
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_recent_commits(repo, days=30, timeout=10):
    """
    Return the count of commits in the last `days` for a public repo.
    Returns None on any failure (network, rate limit, 404) so callers can
    degrade gracefully rather than crash, the correct posture for a tool that
    depends on a third-party API.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = GITHUB_API.format(repo=repo, since=since)
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return len(data)
    except urllib.error.HTTPError as e:
        reason = "rate limit" if e.code == 403 else f"HTTP {e.code}"
        print(f"  ! {repo}: {reason}", file=sys.stderr)
        return None
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"  ! {repo}: {type(e).__name__}", file=sys.stderr)
        return None


def collect_live_signals(days=30):
    signals = {}
    print(f"Pulling live commit activity (last {days}d) from GitHub API...")
    for account, repo in ACCOUNT_REPOS.items():
        count = fetch_recent_commits(repo, days=days)
        signals[account] = {"repo": repo, "recent_commits": count}
        shown = count if count is not None else "unavailable"
        print(f"  {account:<28} {repo:<26} commits: {shown}")
    with open("live_signals.json", "w") as f:
        json.dump(signals, f, indent=2)
    print("Wrote live_signals.json")
    return signals


def enrich_accounts(accounts, signals=None):
    """
    Merge live signals into scored accounts. If a signal is missing/unavailable,
    the account is left unchanged, so the dashboard still works fully offline.
    Adds a 'live_activity' field describing the real API-sourced data point.
    """
    if signals is None:
        try:
            signals = json.load(open("live_signals.json"))
        except FileNotFoundError:
            return accounts
    for a in accounts:
        sig = signals.get(a["name"])
        if sig and sig.get("recent_commits") is not None:
            a["live_activity"] = {
                "source": "GitHub API",
                "repo": sig["repo"],
                "recent_commits_30d": sig["recent_commits"],
            }
    return accounts


if __name__ == "__main__":
    collect_live_signals()
