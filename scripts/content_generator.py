"""
Content Generator — Zero Cost Programmatic SEO System
Generates SEO articles using Claude Haiku (cheapest model) and publishes to Astro site via Git.
Run: python scripts/content_generator.py
Env vars required: ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY, UNSPLASH_KEY
"""

import os
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import anthropic
    from supabase import create_client
    import requests
except ImportError:
    print("Installing deps...")
    subprocess.run([sys.executable, "-m", "pip", "install", "anthropic", "supabase", "requests"], check=True)
    import anthropic
    from supabase import create_client
    import requests

# ─── Config ───────────────────────────────────────────────────────────────────

ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL   = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY   = os.environ.get("SUPABASE_KEY", "")
UNSPLASH_KEY   = os.environ.get("UNSPLASH_KEY", "")
ARTICLES_PER_RUN = int(os.environ.get("ARTICLES_PER_RUN", "5"))
CONTENT_DIR    = Path("src/content/blog")
CURRENT_YEAR   = datetime.now().year

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
sb     = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Affiliate data ────────────────────────────────────────────────────────────

AFFILIATES = {
    "zapier":    {"url": "https://zapier.com?via=YOURCODE",               "name": "Zapier",     "commission": "25% recurring"},
    "notion":    {"url": "https://notion.so/affiliates/YOURCODE",         "name": "Notion",     "commission": "50% first year"},
    "clickup":   {"url": "https://clickup.com?fp_ref=YOURCODE",           "name": "ClickUp",    "commission": "20% recurring"},
    "make":      {"url": "https://www.make.com/en/register?pc=YOURCODE",  "name": "Make.com",   "commission": "20% recurring"},
    "monday":    {"url": "https://monday.com/?r=YOURCODE",                "name": "Monday.com", "commission": "$100-200/sale"},
    "calendly":  {"url": "https://calendly.com/pages/pricing?ref=YOURCODE","name": "Calendly",  "commission": "20% recurring"},
    "hubspot":   {"url": "https://www.hubspot.com/?hubs_signup-url=YOURCODE","name":"HubSpot",  "commission": "30% recurring"},
    "default":   {"url": "https://partnerstack.com",                      "name": "tool",       "commission": "varies"},
}

def get_affiliate(product_name: str) -> dict:
    key = product_name.lower().strip() if product_name else "default"
    for k, v in AFFILIATES.items():
        if k in key:
            return v
    return AFFILIATES["default"]

# ─── Prompt templates ─────────────────────────────────────────────────────────

def build_prompt(keyword: str, article_type: str, affiliate_product: str) -> str:
    aff = get_affiliate(affiliate_product)
    
    type_instructions = {
        "comparison": f"""This is a comparison article. Include:
- A detailed comparison table (tool, price, best for, pros, cons) with 5+ columns
- Clear winner recommendation for specific use cases
- "vs" framing in H2 headings""",
        "review": f"""This is a review article. Include:
- Pricing table with all plan tiers
- Feature breakdown by use case
- Real pros and cons (be honest about limitations)
- Who it's best for / who should avoid it""",
        "listicle": f"""This is a listicle (best X for Y). Include:
- Numbered list format with H3 for each item
- Quick comparison table at the top
- Each item: what it is, price, best for, pros/cons""",
        "how-to": f"""This is a how-to guide. Include:
- Step-by-step numbered instructions
- Screenshots described in text (describe what user should see)
- Troubleshooting section
- Time estimate for each step""",
        "alternatives": f"""This is an alternatives article. Include:
- Comparison table of all alternatives vs the original
- Why someone would switch (price, features, ease of use)
- Quick recommendation matrix (best for X, best for Y)""",
    }

    type_instr = type_instructions.get(article_type, type_instructions["review"])

    return f"""Write a comprehensive, genuinely helpful article for small business owners and freelancers searching for the best tools to run their business.

TARGET KEYWORD: "{keyword}"
ARTICLE TYPE: {article_type}
YEAR: {CURRENT_YEAR}
PRIMARY TOOL/AFFILIATE: {aff["name"]}
AFFILIATE LINK: {aff["url"]}

{type_instr}

UNIVERSAL REQUIREMENTS:
- Length: 1,400–2,000 words
- Tone: direct, practical, zero fluff. No corporate speak. Write like a knowledgeable friend who has actually used these tools.
- Include specific, accurate pricing data (use your knowledge of current pricing — note "as of {CURRENT_YEAR}" for any prices)
- Add 2–3 "Pro tip:" callouts with genuinely useful advice not found elsewhere
- Insert the affiliate link naturally 2–3 times (in introduction, in recommendation section, and in CTA)
- Never say "I" — write as authoritative third-person
- Do NOT use these words/phrases: delve, it's worth noting, certainly, absolutely, straightforward, embark, utilize, leverage (as a verb), game-changer, in conclusion, to summarize
- Last sentence should be a clear call to action with the affiliate link

REQUIRED SECTIONS:
1. Introduction (hook + what article covers + who it's for)
2. Main content (type-specific format above)
3. FAQ (4 questions with detailed answers — real questions people search)

OUTPUT FORMAT — return valid Markdown with frontmatter:

---
title: "{keyword} — Complete Guide [{CURRENT_YEAR}]"
description: "WRITE A COMPELLING META DESCRIPTION HERE (120–155 chars, include keyword)"
pubDate: {datetime.now().strftime('%Y-%m-%d')}
updatedDate: {datetime.now().strftime('%Y-%m-%d')}
tags: ["ai tools", "small business", "{affiliate_product.lower()}", "automation"]
image: "PLACEHOLDER_IMAGE"
affiliate: "{aff['name']}"
---

[FULL ARTICLE CONTENT]

<!-- FAQ_SCHEMA_START -->
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {{
      "@type": "Question",
      "name": "QUESTION 1",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "ANSWER 1"
      }}
    }},
    {{
      "@type": "Question", 
      "name": "QUESTION 2",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "ANSWER 2"
      }}
    }},
    {{
      "@type": "Question",
      "name": "QUESTION 3",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "ANSWER 3"
      }}
    }},
    {{
      "@type": "Question",
      "name": "QUESTION 4",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "ANSWER 4"
      }}
    }}
  ]
}}
<!-- FAQ_SCHEMA_END -->"""

# ─── Generation ───────────────────────────────────────────────────────────────

def generate_article(keyword: str, article_type: str, affiliate_product: str) -> str:
    prompt = build_prompt(keyword, article_type, affiliate_product)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # cheapest, ~$0.01/article
        max_tokens=3500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

# ─── Image fetching ────────────────────────────────────────────────────────────

def get_featured_image(topic: str) -> str:
    if not UNSPLASH_KEY:
        return "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80"
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": topic, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            timeout=10
        )
        data = r.json()
        if data.get("results"):
            return data["results"][0]["urls"]["regular"]
    except Exception:
        pass
    return "https://images.unsplash.com/photo-1551434678-e076c223a692?w=1200&q=80"

# ─── QA check ─────────────────────────────────────────────────────────────────

AI_TELLS = [
    "delve", "it's worth noting", "i'd be happy", "certainly!", "absolutely!",
    "game-changer", "game changer", "straightforward", "embark on", "utilize",
    "in conclusion", "to summarize", "leveraging", "in the realm of",
    "it is important to note", "in today's", "in this article, we will"
]

def qa_check(content: str, keyword: str) -> tuple[int, list]:
    score = 100
    issues = []
    kw_lower = keyword.lower()
    content_lower = content.lower()
    words = content.split()

    if kw_lower not in content_lower[:500]:
        score -= 15
        issues.append("Keyword not in first 500 chars")

    if len(words) < 900:
        score -= 20
        issues.append(f"Too short: {len(words)} words (need 900+)")

    if "faq" not in content_lower and "frequently asked" not in content_lower:
        score -= 10
        issues.append("No FAQ section")

    if "## " not in content and "### " not in content:
        score -= 10
        issues.append("No H2/H3 headings")

    found_tells = [t for t in AI_TELLS if t in content_lower]
    if found_tells:
        score -= len(found_tells) * 3
        issues.append(f"AI tells found: {found_tells}")

    if "| " not in content and article_type_is_comparison(content):
        score -= 5
        issues.append("Comparison article missing table")

    return max(0, score), issues

def article_type_is_comparison(content: str) -> bool:
    return " vs " in content.lower() or "comparison" in content.lower()

# ─── File operations ──────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text[:80]

def save_article(slug: str, content: str, image_url: str) -> Path:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    content = content.replace("PLACEHOLDER_IMAGE", image_url)
    filepath = CONTENT_DIR / f"{slug}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath

def git_commit_and_push(count: int):
    try:
        subprocess.run(["git", "add", str(CONTENT_DIR)], check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        if result.returncode != 0:  # there are changes
            subprocess.run([
                "git", "commit", "-m",
                f"content: add {count} articles [{datetime.now().strftime('%Y-%m-%d')}] [automated]"
            ], check=True)
            subprocess.run(["git", "push"], check=True)
            print(f"Git: pushed {count} new articles")
        else:
            print("Git: no changes to push")
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")

# ─── GSC indexing ping ─────────────────────────────────────────────────────────

def ping_gsc_indexing(urls: list[str]):
    """
    Submits URLs to Google Indexing API.
    Requires service account JSON in env var GOOGLE_SERVICE_ACCOUNT_JSON.
    Skip if not configured — GSC will crawl naturally.
    """
    gsa = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    site_url = os.environ.get("SITE_URL", "")
    if not gsa or not site_url:
        return
    try:
        import json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_info(
            json.loads(gsa),
            scopes=["https://www.googleapis.com/auth/indexing"]
        )
        service = build("indexing", "v3", credentials=creds)
        for url in urls[:200]:  # free quota: 200/day
            full_url = f"{site_url.rstrip('/')}/blog/{url}"
            service.urlNotifications().publish(
                body={"url": full_url, "type": "URL_UPDATED"}
            ).execute()
    except Exception as e:
        print(f"GSC indexing ping failed (non-critical): {e}")

# ─── Main pipeline ─────────────────────────────────────────────────────────────

def run():
    print(f"Starting content pipeline — target: {ARTICLES_PER_RUN} articles")

    # Fetch pending keywords from Supabase
    result = sb.table("keywords")\
        .select("*")\
        .eq("status", "pending")\
        .order("created_at")\
        .limit(ARTICLES_PER_RUN)\
        .execute()

    if not result.data:
        print("No pending keywords. Run keyword_research.py first.")
        return

    generated = 0
    published_slugs = []

    for row in result.data:
        keyword       = row["keyword"]
        article_type  = row.get("article_type", "review")
        affiliate     = row.get("affiliate_product", "")

        print(f"\n[{generated+1}/{len(result.data)}] Generating: '{keyword}'")

        try:
            content = generate_article(keyword, article_type, affiliate)
            score, issues = qa_check(content, keyword)
            print(f"  QA score: {score}/100")

            if score >= 65:
                slug      = slugify(keyword)
                image_url = get_featured_image(affiliate or keyword.split()[0])
                filepath  = save_article(slug, content, image_url)

                # Update Supabase
                sb.table("keywords").update({"status": "published"}).eq("id", row["id"]).execute()
                sb.table("articles").insert({
                    "keyword_id": row["id"],
                    "slug": slug,
                    "title": keyword,
                    "qa_score": score,
                    "status": "published",
                    "published_at": datetime.now().isoformat()
                }).execute()

                published_slugs.append(slug)
                generated += 1
                print(f"  Published: {slug} ({len(content.split())} words)")
            else:
                print(f"  Failed QA: {issues}")
                sb.table("keywords").update({"status": "qa_failed"}).eq("id", row["id"]).execute()

        except Exception as e:
            print(f"  Error: {e}")
            sb.table("keywords").update({"status": "error"}).eq("id", row["id"]).execute()

    if generated > 0:
        git_commit_and_push(generated)
        ping_gsc_indexing(published_slugs)

    print(f"\nPipeline complete: {generated}/{len(result.data)} articles published")

if __name__ == "__main__":
    run()
