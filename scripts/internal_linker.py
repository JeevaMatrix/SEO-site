"""
Internal Linker — Zero Cost Programmatic SEO System
Scans all published articles and adds internal links between related content.
Run: python scripts/internal_linker.py
Run weekly via GitHub Actions after content has been building up.
"""

import os
import sys
import re
import subprocess
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "supabase"], check=True)
    from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CONTENT_DIR  = Path("src/content/blog")
SITE_URL     = os.environ.get("SITE_URL", "https://yoursite.com")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Stop words for link matching ─────────────────────────────────────────────

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "during",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "this", "that", "these", "those", "it", "its", "you", "your", "we", "our",
    "they", "their", "he", "she", "his", "her", "best", "top", "free", "how",
}

def extract_link_phrases(keyword: str) -> list[str]:
    """Generate multiple anchor text variations from a keyword."""
    phrases = [keyword]
    words = keyword.lower().split()
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 3]
    if len(meaningful) >= 2:
        # Two-word combos
        for i in range(len(meaningful) - 1):
            phrases.append(f"{meaningful[i]} {meaningful[i+1]}")
    # Key tool names always link
    tool_names = [
        "zapier", "notion", "clickup", "monday", "calendly", "hubspot",
        "airtable", "make.com", "trello", "asana", "slack", "pipedrive"
    ]
    for t in tool_names:
        if t in keyword.lower():
            phrases.append(t)
    return list(set(p for p in phrases if len(p) > 4))

def load_all_articles() -> dict[str, dict]:
    """Load all published article slugs + keywords from Supabase."""
    result = sb.table("articles")\
        .select("slug, title, keyword_id")\
        .eq("status", "published")\
        .execute()

    articles = {}
    for row in result.data:
        slug    = row["slug"]
        keyword = row.get("title", slug.replace("-", " "))
        phrases = extract_link_phrases(keyword)
        articles[slug] = {
            "url": f"/blog/{slug}",
            "keyword": keyword,
            "phrases": phrases,
        }
    return articles

def add_internal_links(content: str, current_slug: str, all_articles: dict, max_links: int = 4) -> tuple[str, int]:
    """
    Adds internal links to article content.
    - Never links to itself
    - Never links inside existing <a> tags or markdown links
    - Maximum max_links new links per article
    - Only links first occurrence of each phrase
    """
    added = 0
    already_linked = set()

    # Extract existing linked phrases to avoid double-linking
    existing_links = re.findall(r'\[([^\]]+)\]\([^)]+\)', content)
    for link in existing_links:
        already_linked.add(link.lower())

    # Build a list of (phrase, url, keyword) sorted by phrase length desc
    # (longer phrases take priority over shorter ones)
    link_targets = []
    for slug, data in all_articles.items():
        if slug == current_slug:
            continue
        for phrase in data["phrases"]:
            link_targets.append((phrase, data["url"], data["keyword"]))
    link_targets.sort(key=lambda x: len(x[0]), reverse=True)

    for phrase, url, anchor_keyword in link_targets:
        if added >= max_links:
            break
        if phrase.lower() in already_linked:
            continue

        # Don't link inside frontmatter (between --- markers)
        # Find first occurrence in body text only
        # Regex: phrase not already inside [] or ()
        pattern = r'(?<!\[)(?<!\()' + re.escape(phrase) + r'(?!\])'
        
        # Only replace FIRST occurrence in body (after frontmatter)
        body_start = content.find("\n---\n", content.find("---")) + 4
        frontmatter = content[:body_start]
        body        = content[body_start:]

        new_body, count = re.subn(
            pattern,
            f"[{phrase}]({url})",
            body,
            count=1,
            flags=re.IGNORECASE
        )
        if count > 0:
            content = frontmatter + new_body
            already_linked.add(phrase.lower())
            added += 1

    return content, added

def process_all_articles(all_articles: dict) -> int:
    """Process each article file and add internal links."""
    if not CONTENT_DIR.exists():
        print(f"Content directory not found: {CONTENT_DIR}")
        return 0

    total_links_added = 0
    files_modified = 0

    for filepath in CONTENT_DIR.glob("*.md"):
        slug    = filepath.stem
        content = filepath.read_text(encoding="utf-8")

        # Skip if article already has many internal links
        existing_internal = len(re.findall(r'\]\(/blog/', content))
        if existing_internal >= 6:
            continue

        new_content, added = add_internal_links(content, slug, all_articles)

        if added > 0:
            filepath.write_text(new_content, encoding="utf-8")
            total_links_added += added
            files_modified += 1
            print(f"  {slug}: +{added} internal links")

    return files_modified

def git_commit(files_modified: int):
    if files_modified == 0:
        return
    try:
        subprocess.run(["git", "add", str(CONTENT_DIR)], check=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode != 0:
            subprocess.run([
                "git", "commit", "-m",
                f"seo: add internal links to {files_modified} articles [automated]"
            ], check=True)
            subprocess.run(["git", "push"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")

def run():
    print("Loading article database...")
    all_articles = load_all_articles()
    print(f"Found {len(all_articles)} published articles")

    if len(all_articles) < 5:
        print("Need at least 5 articles before internal linking is useful. Skipping.")
        return

    print("Processing articles for internal links...")
    files_modified = process_all_articles(all_articles)
    print(f"\nInternal linking complete: {files_modified} files updated")

    git_commit(files_modified)

if __name__ == "__main__":
    run()
