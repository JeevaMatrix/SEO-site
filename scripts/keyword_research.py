"""
Keyword Research — Zero Cost Programmatic SEO System
Uses Serper.dev (2,500 free searches/mo) + Claude Haiku to find and expand keywords.
Run: python scripts/keyword_research.py
Env vars required: SERPER_API_KEY, ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY
"""

import os
import json
import sys
import subprocess
import time
from datetime import datetime

try:
    import anthropic
    from supabase import create_client
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "anthropic", "supabase", "requests"], check=True)
    import anthropic
    from supabase import create_client
    import requests

# ─── Config ───────────────────────────────────────────────────────────────────

SERPER_KEY   = os.environ.get("SERPER_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY", "")

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
sb     = create_client(SUPABASE_URL, SUPABASE_KEY)

CURRENT_YEAR = datetime.now().year

# ─── Seed terms — AI tools for small business niche ───────────────────────────
# Edit this list to change your niche focus.

SEED_TERMS = [
    # Tool comparisons (highest buyer intent)
    "Zapier alternatives",
    "Notion alternatives",
    "ClickUp alternatives",
    "Monday.com alternatives",
    "Calendly alternatives",
    "HubSpot alternatives free",
    "Asana alternatives",
    "Slack alternatives",
    "Airtable alternatives",

    # AI tool categories
    "best AI writing tool small business",
    "best AI email tool",
    "best AI scheduling tool",
    "best AI invoice generator",
    "best free CRM 2026",
    "best automation tool freelancers",
    "best project management AI",
    "best AI chatbot for small business",

    # Use case + profession combos
    "ChatGPT for real estate agents",
    "AI tools for freelancers",
    "automation tools for restaurants",
    "AI tools for coaches",
    "CRM for solopreneurs",
    "project management for agencies",

    # How-to + tool combos
    "how to use Zapier for beginners",
    "Make.com tutorial",
    "how to automate invoices free",
    "Notion for client management",
]

# ─── Article type classification ──────────────────────────────────────────────

def classify_article_type(keyword: str) -> str:
    kw = keyword.lower()
    if " vs " in kw:
        return "comparison"
    if "alternative" in kw:
        return "alternatives"
    if kw.startswith("how to") or kw.startswith("how do"):
        return "how-to"
    if kw.startswith("best "):
        return "listicle"
    if "review" in kw or "pricing" in kw or "cost" in kw:
        return "review"
    return "review"

def extract_affiliate_product(keyword: str) -> str:
    """Extract the primary tool name from a keyword."""
    known_tools = [
        "zapier", "notion", "clickup", "monday", "calendly", "hubspot",
        "asana", "slack", "airtable", "make", "trello", "todoist",
        "pipedrive", "salesforce", "freshdesk", "intercom", "zendesk",
        "jasper", "copy.ai", "writesonic", "surfer", "semrush", "ahrefs",
        "chatgpt", "claude", "gemini", "openai"
    ]
    kw_lower = keyword.lower()
    for tool in known_tools:
        if tool in kw_lower:
            return tool
    return ""

# ─── Serper API ───────────────────────────────────────────────────────────────

def serper_search(query: str) -> dict:
    if not SERPER_KEY:
        print("  Warning: No SERPER_API_KEY — skipping SERP data")
        return {}
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 10, "gl": "us", "hl": "en"},
            timeout=15
        )
        return r.json()
    except Exception as e:
        print(f"  Serper error: {e}")
        return {}

def extract_serper_suggestions(data: dict) -> list[str]:
    suggestions = []
    for item in data.get("peopleAlsoAsk", []):
        q = item.get("question", "")
        if q:
            suggestions.append(q)
    for item in data.get("relatedSearches", []):
        q = item.get("query", "")
        if q:
            suggestions.append(q)
    return suggestions[:15]

def estimate_competition(data: dict) -> str:
    """Rough competition score from SERP data."""
    organic = data.get("organic", [])
    if not organic:
        return "unknown"
    # Check if top results are from high-authority sites
    high_auth_domains = [
        "g2.com", "capterra.com", "techradar.com", "pcmag.com",
        "forbes.com", "businessinsider.com", "techcrunch.com"
    ]
    top_3_links = [r.get("link", "") for r in organic[:3]]
    ha_count = sum(1 for link in top_3_links if any(d in link for d in high_auth_domains))
    if ha_count >= 2:
        return "high"
    if ha_count == 1:
        return "medium"
    return "low"

# ─── AI keyword expansion ─────────────────────────────────────────────────────

def expand_keywords_with_ai(seed: str, suggestions: list[str]) -> list[dict]:
    prompt = f"""You are an SEO keyword researcher specializing in AI and automation tools for small businesses.

Seed topic: "{seed}"
Related searches found: {json.dumps(suggestions[:12])}

Generate 25 highly specific, long-tail keyword ideas that:
1. Have clear buyer or research intent (someone evaluating or comparing tools)
2. Target small business owners, freelancers, solopreneurs, or specific professions
3. Are 4–8 words long
4. Are specific enough to have low competition
5. Relate to AI tools, automation, productivity software, or SaaS tools for business

AVOID:
- Single-word or 2-word keywords (too competitive)
- Generic terms like "best software" with no specificity
- Medical, legal, or financial keywords
- Keywords targeting enterprise/Fortune 500 companies

For each keyword also specify:
- article_type: "comparison" | "review" | "listicle" | "how-to" | "alternatives"
- affiliate_target: the primary tool name the article should promote (e.g. "zapier", "notion")

Return ONLY a valid JSON array, no other text:
[
  {{"keyword": "zapier vs make for ecommerce stores", "article_type": "comparison", "affiliate_target": "zapier"}},
  ...
]"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        # Clean up in case model adds markdown fences
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"  AI expansion error: {e}")
        return []

# ─── Deduplication & save ─────────────────────────────────────────────────────

def keyword_exists(keyword: str) -> bool:
    result = sb.table("keywords").select("id").eq("keyword", keyword).execute()
    return bool(result.data)

def save_keywords(keywords: list[dict]) -> int:
    saved = 0
    for kw in keywords:
        keyword_text = kw.get("keyword", "").strip().lower()
        if not keyword_text or len(keyword_text) < 10:
            continue
        if keyword_exists(keyword_text):
            continue
        try:
            sb.table("keywords").insert({
                "keyword": keyword_text,
                "article_type": kw.get("article_type", "review"),
                "affiliate_product": kw.get("affiliate_target", ""),
                "status": "pending",
            }).execute()
            saved += 1
        except Exception as e:
            print(f"  DB error saving '{keyword_text}': {e}")
    return saved

# ─── Main ─────────────────────────────────────────────────────────────────────

def run():
    print(f"Keyword research starting — {len(SEED_TERMS)} seeds")
    total_saved = 0

    for i, seed in enumerate(SEED_TERMS):
        print(f"\n[{i+1}/{len(SEED_TERMS)}] Seed: '{seed}'")

        # 1. Get SERP suggestions
        serp_data    = serper_search(seed)
        suggestions  = extract_serper_suggestions(serp_data)
        competition  = estimate_competition(serp_data)
        print(f"  Competition: {competition} | SERP suggestions: {len(suggestions)}")

        # Skip high-competition seeds (better to find gaps)
        if competition == "high":
            print(f"  Skipping (too competitive at root level, will use suggestions only)")

        # 2. Expand with AI
        keywords = expand_keywords_with_ai(seed, suggestions)
        print(f"  AI generated: {len(keywords)} keywords")

        # 3. Save
        saved = save_keywords(keywords)
        total_saved += saved
        print(f"  New keywords saved: {saved}")

        # Rate limit: be gentle with free API quotas
        time.sleep(1)

    # Also add the SERP suggestions directly as potential keywords
    print("\nAdding PAA questions as keyword candidates...")
    for seed in SEED_TERMS[:10]:  # conserve Serper quota
        serp_data   = serper_search(f"{seed} {CURRENT_YEAR}")
        suggestions = extract_serper_suggestions(serp_data)
        paa_kws = [
            {
                "keyword": q.lower().rstrip("?"),
                "article_type": classify_article_type(q),
                "affiliate_target": extract_affiliate_product(q),
            }
            for q in suggestions
            if 10 <= len(q) <= 80
        ]
        saved = save_keywords(paa_kws)
        total_saved += saved
        time.sleep(0.5)

    print(f"\nKeyword research complete. Total new keywords: {total_saved}")

    # Show queue status
    result = sb.table("keywords").select("status").execute()
    status_counts = {}
    for row in result.data:
        s = row["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    print(f"Keyword queue: {json.dumps(status_counts, indent=2)}")

if __name__ == "__main__":
    run()
