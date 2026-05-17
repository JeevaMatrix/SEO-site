"""
Affiliate Link Validator — Zero Cost Programmatic SEO System
Checks all affiliate links in published articles are alive (200 response).
Dead links are flagged in Supabase and a report is printed.
Run weekly via GitHub Actions.
"""

import os
import sys
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime

try:
    import requests
    from supabase import create_client
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "supabase"], check=True)
    import requests
    from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CONTENT_DIR  = Path("src/content/blog")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Your affiliate link patterns — customize these
AFFILIATE_PATTERNS = [
    r"https://zapier\.com\?via=\w+",
    r"https://notion\.so/affiliates/\w+",
    r"https://clickup\.com\?fp_ref=\w+",
    r"https://www\.make\.com/en/register\?pc=\w+",
    r"https://monday\.com/\?r=\w+",
    r"https://calendly\.com/pages/pricing\?ref=\w+",
    r"https://www\.hubspot\.com/\?hubs_signup-url=\w+",
]

def extract_links_from_file(filepath: Path) -> list[str]:
    """Extract all URLs from a markdown file."""
    content = filepath.read_text(encoding="utf-8")
    urls = re.findall(r'\(https?://[^\s\)]+\)', content)
    return [u.strip("()") for u in urls]

def is_affiliate_url(url: str) -> bool:
    for pattern in AFFILIATE_PATTERNS:
        if re.search(pattern, url):
            return True
    # Also check for common affiliate params
    return any(p in url for p in ["?via=", "fp_ref=", "?r=", "?ref=", "?pc=", "affiliate"])

def check_url(url: str) -> tuple[bool, int]:
    """Returns (is_alive, status_code)."""
    try:
        r = requests.head(
            url,
            timeout=10,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LinkChecker/1.0)"}
        )
        return r.status_code < 400, r.status_code
    except Exception:
        try:
            # Try GET if HEAD fails (some servers block HEAD)
            r = requests.get(url, timeout=10, allow_redirects=True)
            return r.status_code < 400, r.status_code
        except Exception:
            return False, 0

def run():
    print(f"Affiliate link validator — {datetime.now().strftime('%Y-%m-%d')}")

    if not CONTENT_DIR.exists():
        print("No content directory found.")
        return

    all_links = {}  # url -> list of files
    files_checked = 0

    for filepath in CONTENT_DIR.glob("*.md"):
        links = extract_links_from_file(filepath)
        for link in links:
            if link not in all_links:
                all_links[link] = []
            all_links[link].append(filepath.name)
        files_checked += 1

    affiliate_links = {url: files for url, files in all_links.items() if is_affiliate_url(url)}
    print(f"Files scanned: {files_checked}")
    print(f"Unique affiliate links found: {len(affiliate_links)}")

    dead_links = []
    alive_links = []

    for url, files in affiliate_links.items():
        is_alive, status = check_url(url)
        if is_alive:
            alive_links.append(url)
            print(f"  ✓ {status} {url[:60]}...")
        else:
            dead_links.append({"url": url, "status": status, "files": files})
            print(f"  ✗ {status} DEAD: {url[:60]}...")

    print(f"\n=== SUMMARY ===")
    print(f"Alive: {len(alive_links)}")
    print(f"Dead: {len(dead_links)}")

    if dead_links:
        print("\n=== DEAD LINKS — ACTION REQUIRED ===")
        for dl in dead_links:
            print(f"\nURL: {dl['url']}")
            print(f"Status: {dl['status']}")
            print(f"Found in: {', '.join(dl['files'])}")

    # Save report as JSON for GitHub Actions summary
    report = {
        "date": datetime.now().isoformat(),
        "files_checked": files_checked,
        "affiliate_links_total": len(affiliate_links),
        "alive": len(alive_links),
        "dead": len(dead_links),
        "dead_links": dead_links
    }
    with open("affiliate_report.json", "w") as f:
        json.dump(report, f, indent=2)

    if dead_links:
        print("\nAction: Manually update dead affiliate links or swap to backup affiliate.")
        sys.exit(1)  # Fail the GitHub Actions run to get notified

if __name__ == "__main__":
    run()
