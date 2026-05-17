"""
Rank Tracker — Zero Cost Programmatic SEO System
Checks weekly rankings for published articles using Serper.dev free tier.
2,500 free searches/mo = ~80/day. Checks top 50 articles per week = fine.
Run: python scripts/rank_tracker.py
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime

try:
    from supabase import create_client
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "supabase", "requests"], check=True)
    from supabase import create_client
    import requests

SERPER_KEY   = os.environ.get("SERPER_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SITE_URL     = os.environ.get("SITE_URL", "https://yoursite.com")
ARTICLES_TO_CHECK = 50  # stay within free Serper quota

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_rank(keyword: str, site_domain: str) -> int | None:
    """Returns rank position (1-100) or None if not found."""
    if not SERPER_KEY:
        return None
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": keyword, "num": 30, "gl": "us"},
            timeout=15
        )
        data = r.json()
        for i, result in enumerate(data.get("organic", []), 1):
            link = result.get("link", "")
            if site_domain in link:
                return i
        return None  # not in top 30
    except Exception as e:
        print(f"  Serper error for '{keyword}': {e}")
        return None

def get_articles_to_check() -> list[dict]:
    """Get articles prioritized by: ranking 4-20 (most improvement potential)."""
    result = sb.table("articles")\
        .select("id, slug, title, rank")\
        .eq("status", "published")\
        .limit(ARTICLES_TO_CHECK)\
        .execute()
    
    articles = result.data
    # Sort: articles ranking 4-20 first (best ROI), then unranked, then 1-3
    def priority(a):
        rank = a.get("rank") or 999
        if 4 <= rank <= 20:
            return 0   # highest priority
        if rank > 20:
            return 1
        return 2       # already top 3, lower priority
    
    return sorted(articles, key=priority)

def flag_for_refresh(article_id: str, current_rank: int, prev_rank: int):
    """If article dropped significantly, re-queue its keyword for refresh."""
    if prev_rank and current_rank and (current_rank - prev_rank) > 5:
        # Find the keyword and re-queue it
        result = sb.table("articles").select("keyword_id").eq("id", article_id).execute()
        if result.data and result.data[0]["keyword_id"]:
            sb.table("keywords")\
                .update({"status": "refresh_needed"})\
                .eq("id", result.data[0]["keyword_id"])\
                .execute()
            print(f"    → Flagged for content refresh (dropped {prev_rank} → {current_rank})")

def generate_report(results: list[dict]) -> str:
    """Build a simple text report."""
    top_performers  = [r for r in results if r.get("rank") and r["rank"] <= 10]
    opportunities   = [r for r in results if r.get("rank") and 11 <= r["rank"] <= 20]
    not_ranking     = [r for r in results if not r.get("rank")]
    
    report = f"""
=== RANK REPORT — {datetime.now().strftime('%Y-%m-%d')} ===

TOP 10: {len(top_performers)} articles
POSITIONS 11-20 (optimize these): {len(opportunities)} articles  
NOT IN TOP 30: {len(not_ranking)} articles
TOTAL CHECKED: {len(results)}

TOP PERFORMERS:
"""
    for r in sorted(top_performers, key=lambda x: x.get("rank", 99)):
        report += f"  #{r['rank']} — {r['title']}\n"
    
    report += "\nOPPORTUNITIES (positions 11-20):\n"
    for r in sorted(opportunities, key=lambda x: x.get("rank", 99)):
        change = ""
        if r.get("prev_rank"):
            diff = r["rank"] - r["prev_rank"]
            change = f" ({'+' if diff > 0 else ''}{diff} vs last week)"
        report += f"  #{r['rank']}{change} — {r['title']}\n"
    
    return report

def run():
    print(f"Rank tracker starting — checking up to {ARTICLES_TO_CHECK} articles")
    
    if not SERPER_KEY:
        print("No SERPER_API_KEY configured. Skipping rank check.")
        return
    
    site_domain = SITE_URL.replace("https://", "").replace("http://", "").split("/")[0]
    articles    = get_articles_to_check()
    print(f"Found {len(articles)} articles to check")
    
    results     = []
    
    for i, article in enumerate(articles):
        keyword = article.get("title", "")
        if not keyword:
            continue
        
        print(f"[{i+1}/{len(articles)}] Checking: '{keyword}'")
        
        prev_rank    = article.get("rank")
        current_rank = check_rank(keyword, site_domain)
        
        if current_rank:
            print(f"  Rank: #{current_rank}")
        else:
            print(f"  Not in top 30")
        
        # Update DB
        sb.table("articles").update({
            "rank": current_rank,
            "last_checked": datetime.now().isoformat()
        }).eq("id", article["id"]).execute()
        
        # Log history
        sb.table("rank_history").insert({
            "article_id": article["id"],
            "rank": current_rank,
            "checked_at": datetime.now().isoformat()
        }).execute()
        
        # Check if dropped significantly
        if prev_rank and current_rank:
            flag_for_refresh(article["id"], current_rank, prev_rank)
        
        results.append({**article, "rank": current_rank, "prev_rank": prev_rank})
        
        # Rate limit — Serper allows ~100 req/min, but be conservative
        time.sleep(0.5)
    
    report = generate_report(results)
    print(report)
    
    # Save report as artifact for GitHub Actions to display
    with open("rank_report.txt", "w") as f:
        f.write(report)

if __name__ == "__main__":
    run()
