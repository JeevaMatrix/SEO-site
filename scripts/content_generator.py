"""
Content Generator — 100% FREE, Zero Cost Programmatic SEO System
Uses Groq API (FREE - no card) for generation + Google Gemini Flash (FREE - no card) for QA.

FREE AI APIs used:
  Groq:   console.groq.com       → 14,400 requests/day FREE, no credit card
  Gemini: aistudio.google.com    → 1,500 requests/day FREE, no credit card (optional)

Run locally:
    python scripts/content_generator.py

Required env vars (put in .env file — see README Step 8):
    GROQ_API_KEY
    SUPABASE_URL
    SUPABASE_KEY
    UNSPLASH_KEY   (optional — for images)
    GEMINI_API_KEY (optional — for extra QA)
    ARTICLES_PER_RUN (default 5)
"""

import os, json, re, subprocess, sys
from datetime import datetime
from pathlib import Path

def install(pkg):
    subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"], check=True)

try:
    import requests
except ImportError:
    install("requests"); import requests
try:
    from supabase import create_client
except ImportError:
    install("supabase"); from supabase import create_client

# ── Load .env automatically ──────────────────────────────────────────────────
def load_dotenv():
    p = Path(".env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
GROQ_KEY         = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY       = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL     = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY     = os.environ.get("SUPABASE_KEY", "")
UNSPLASH_KEY     = os.environ.get("UNSPLASH_KEY", "")
ARTICLES_PER_RUN = int(os.environ.get("ARTICLES_PER_RUN", "5"))
CONTENT_DIR      = Path("src/content/blog")
YEAR             = datetime.now().year

missing = [v for v in ["GROQ_API_KEY","SUPABASE_URL","SUPABASE_KEY"] if not os.environ.get(v)]
if missing:
    print(f"ERROR: Missing env vars: {', '.join(missing)}")
    print("See README.md Step 8 — create a .env file with these values.")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Affiliates ───────────────────────────────────────────────────────────────
AFFILIATES = {
    "zapier":   {"url":"https://zapier.com?via=YOURCODE",              "name":"Zapier"},
    "notion":   {"url":"https://notion.so/affiliates/YOURCODE",        "name":"Notion"},
    "clickup":  {"url":"https://clickup.com?fp_ref=YOURCODE",          "name":"ClickUp"},
    "make":     {"url":"https://www.make.com/en/register?pc=YOURCODE", "name":"Make.com"},
    "monday":   {"url":"https://monday.com/?r=YOURCODE",               "name":"Monday.com"},
    "calendly": {"url":"https://calendly.com/pages/pricing?ref=YOURCODE","name":"Calendly"},
    "hubspot":  {"url":"https://hubspot.com/?hubs_signup-url=YOURCODE","name":"HubSpot"},
    "default":  {"url":"#",                                            "name":"the tool"},
}

def get_aff(product):
    key = (product or "").lower()
    for k, v in AFFILIATES.items():
        if k in key: return v
    return AFFILIATES["default"]

# ── Groq API (FREE — no card, 14,400 req/day) ────────────────────────────────
def groq(prompt, max_tokens=3500):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type":"application/json"},
        json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],
              "max_tokens":max_tokens,"temperature":0.7},
        timeout=90,
    )
    if r.status_code != 200:
        raise Exception(f"Groq {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]

# ── Gemini API (FREE — no card, 1500 req/day, OPTIONAL) ─────────────────────
def gemini(prompt, max_tokens=100):
    if not GEMINI_KEY: return ""
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            headers={"Content-Type":"application/json"},
            json={"contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"maxOutputTokens":max_tokens,"temperature":0.1}},
            timeout=20,
        )
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return ""

# ── Prompt ───────────────────────────────────────────────────────────────────
TYPE_GUIDE = {
    "comparison": "Include a markdown comparison table (min 5 data points: price, features, ease, best for, support). End with clear winner per use case.",
    "review":     "Include pricing table (all plan tiers). List 3+ specific pros AND 3+ specific cons. Add 'Who should avoid this' section.",
    "listicle":   "Start with a quick comparison table. Each item as H3 with: price, best for, one key limitation.",
    "how-to":     "Use numbered steps. Describe what user sees after each step. Add troubleshooting section. State time required.",
    "alternatives":"Compare vs the original tool in a table. Explain why someone switches. Separate free vs paid options.",
}

def make_prompt(keyword, article_type, affiliate_product):
    aff = get_aff(affiliate_product)
    guide = TYPE_GUIDE.get(article_type, TYPE_GUIDE["review"])
    return f"""You are a tech writer for a site helping small business owners find the best AI tools.

TARGET KEYWORD: "{keyword}"
ARTICLE TYPE: {article_type}
YEAR: {YEAR}
FEATURED TOOL: {aff["name"]}
AFFILIATE LINK (use 2-3 times naturally): {aff["url"]}

FORMAT REQUIREMENT: {guide}

WRITING RULES:
- Start with a hook that names the reader's problem in sentence 1
- Write for non-technical SMB owners — practical, specific, honest
- Include real pricing numbers (use your knowledge; note "as of {YEAR}")
- 2-3 "Pro tip:" callouts with genuinely useful advice
- Insert affiliate link naturally: [Try {aff["name"]} free]({aff["url"]}) style
- NEVER use: delve, leverage, utilize, embark, game-changer, straightforward, certainly, absolutely, in conclusion
- Length: 1400-2000 words
- End with 4 FAQ questions people actually Google, with full answers

RETURN: Only valid Markdown starting with this exact frontmatter block:

---
title: "{keyword} — Complete Guide [{YEAR}]"
description: "WRITE REAL META DESC: 130-155 chars, include keyword"
pubDate: {datetime.now().strftime('%Y-%m-%d')}
updatedDate: {datetime.now().strftime('%Y-%m-%d')}
tags: ["ai tools", "small business", "{(affiliate_product or 'productivity').lower()}"]
image: "PLACEHOLDER_IMAGE"
affiliate: "{aff['name']}"
---

[article body]

<!-- FAQ_SCHEMA_START -->
{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
  {{"@type":"Question","name":"Q1","acceptedAnswer":{{"@type":"Answer","text":"A1"}}}},
  {{"@type":"Question","name":"Q2","acceptedAnswer":{{"@type":"Answer","text":"A2"}}}},
  {{"@type":"Question","name":"Q3","acceptedAnswer":{{"@type":"Answer","text":"A3"}}}},
  {{"@type":"Question","name":"Q4","acceptedAnswer":{{"@type":"Answer","text":"A4"}}}}
]}}
<!-- FAQ_SCHEMA_END -->"""

# ── QA ───────────────────────────────────────────────────────────────────────
BAD_PHRASES = ["delve","it's worth noting","certainly!","absolutely!","game-changer",
               "straightforward","embark on","in conclusion,","leveraging","utilize"]

def qa(content, keyword):
    score, issues = 100, []
    kw, cl = keyword.lower(), content.lower()
    words  = content.split()

    if kw not in cl[:600]:       score -= 15; issues.append("Keyword missing from intro")
    if len(words) < 900:         score -= 20; issues.append(f"Too short ({len(words)} words)")
    elif len(words) < 1200:      score -= 8;  issues.append(f"Short ({len(words)} words)")
    if content.count("\n## ") < 2: score -= 10; issues.append("Need 2+ H2 headings")
    if "faq" not in cl:          score -= 10; issues.append("Missing FAQ section")
    if "| " not in content:      score -= 5;  issues.append("Missing markdown table")
    if "---\n" not in content[:300]: score -= 10; issues.append("Missing frontmatter")

    bad = [p for p in BAD_PHRASES if p in cl]
    if bad: score -= min(len(bad)*4, 20); issues.append(f"AI phrases: {bad[:2]}")

    # Optional Gemini quality check (adds up to 20 bonus pts)
    bonus = 0
    if GEMINI_KEY:
        try:
            result = gemini(f'Rate 0-20: is this article genuinely useful (not generic AI fluff) for a small business owner? Keyword: "{keyword}". Article start: {content[300:1200]}\nReply ONLY with a number.', 10)
            bonus = int(re.search(r"\d+", result).group())
            bonus = min(bonus, 20)
        except Exception:
            bonus = 10
    else:
        bonus = 10  # default if no Gemini

    return min(100, score + bonus), issues

# ── Images ───────────────────────────────────────────────────────────────────
FALLBACKS = [
    "https://images.unsplash.com/photo-1551434678-e076c223a692?w=1200&q=80",
    "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",
    "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1200&q=80",
]
_img_i = 0

def get_image(topic):
    global _img_i
    if UNSPLASH_KEY:
        try:
            r = requests.get("https://api.unsplash.com/search/photos",
                params={"query":topic,"per_page":1,"orientation":"landscape"},
                headers={"Authorization":f"Client-ID {UNSPLASH_KEY}"}, timeout=10)
            res = r.json().get("results",[])
            if res: return res[0]["urls"]["regular"]
        except Exception:
            pass
    img = FALLBACKS[_img_i % len(FALLBACKS)]; _img_i += 1
    return img

# ── Helpers ──────────────────────────────────────────────────────────────────
def slugify(t):
    t = t.lower().strip()
    t = re.sub(r"[^\w\s-]","",t); t = re.sub(r"[\s_-]+","-",t)
    return t[:80].strip("-")

def save(slug, content, image_url):
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    content = content.replace("PLACEHOLDER_IMAGE", image_url)
    (CONTENT_DIR / f"{slug}.md").write_text(content, encoding="utf-8")

def git_push(count):
    try:
        subprocess.run(["git","add",str(CONTENT_DIR)], check=True)
        diff = subprocess.run(["git","diff","--cached","--quiet"], capture_output=True)
        if diff.returncode != 0:
            subprocess.run(["git","commit","-m",
                f"content: add {count} articles [{datetime.now().strftime('%Y-%m-%d')}] [bot]"], check=True)
            subprocess.run(["git","push"], check=True)
            print(f"\n✓ Pushed to GitHub → Vercel auto-deploys in ~30 seconds")
    except subprocess.CalledProcessError as e:
        print(f"Git note: {e}")

# ── Main ─────────────────────────────────────────────────────────────────────
def run():
    print(f"\n{'='*55}")
    print(f" Content Generator  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f" AI: Groq llama-3.3-70b (FREE)  |  Target: {ARTICLES_PER_RUN} articles")
    print(f"{'='*55}\n")

    rows = (sb.table("keywords").select("*").eq("status","pending")
              .order("created_at").limit(ARTICLES_PER_RUN).execute().data)

    if not rows:
        print("No pending keywords. Run: python scripts/keyword_research.py")
        return

    generated = 0
    for i, row in enumerate(rows):
        keyword      = row["keyword"]
        article_type = row.get("article_type","review")
        affiliate    = row.get("affiliate_product","")

        print(f"[{i+1}/{len(rows)}] {keyword}")

        try:
            content = groq(make_prompt(keyword, article_type, affiliate))
            score, issues = qa(content, keyword)
            status_str = f"QA {score}/100"
            if issues: status_str += f" ({issues[0]})"
            print(f"      {status_str} — {len(content.split())} words")

            if score >= 58:
                slug = slugify(keyword)
                save(slug, content, get_image(affiliate or keyword.split()[0]))
                sb.table("keywords").update({"status":"published"}).eq("id",row["id"]).execute()
                sb.table("articles").insert({
                    "keyword_id":row["id"],"slug":slug,"title":keyword,
                    "qa_score":score,"status":"published",
                    "published_at":datetime.now().isoformat()
                }).execute()
                generated += 1
                print(f"      ✓ src/content/blog/{slug}.md")
            else:
                print(f"      ✗ Failed QA — issues: {issues}")
                sb.table("keywords").update({"status":"qa_failed"}).eq("id",row["id"]).execute()

        except Exception as e:
            print(f"      ✗ Error: {e}")
            sb.table("keywords").update({"status":"error"}).eq("id",row["id"]).execute()
        print()

    if generated > 0:
        git_push(generated)
    print(f"Done: {generated}/{len(rows)} published  |  API cost: $0.00")

if __name__ == "__main__":
    run()
