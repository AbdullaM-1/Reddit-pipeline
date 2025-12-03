#!/usr/bin/env python3
"""
Use Playwright to scroll a subreddit feed and collect the Reddit post IDs that appear.

Usage:
  python playwright_scroller.py --subreddit SextStories \
        --max-posts 200 \
        --storage-state auth.json \
        --output post_ids.json

Make sure Playwright is installed (`pip install playwright`) and the browser binaries are installed
(`playwright install`). If you are logged in, pass the saved storage state (JSON from Playwright) via
`--storage-state`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Iterable, Optional, Set

from playwright.async_api import Page, async_playwright  # type: ignore[import]

POST_SELECTOR = "shreddit-post[data-ks-item][permalink]"
COMMENT_LINK_SELECTOR = "a[data-click-id='comments']"
POST_ID_REGEX = re.compile(r"/comments/([a-z0-9]{6,})", re.IGNORECASE)


def sanitize_post_id(value: Optional[str]) -> Optional[str]:
    """Normalize either a Reddit fullname or an ID found in a URL."""
    if not value:
        return None
    value = value.strip()
    if value.startswith("t3_"):
        return value
    match = POST_ID_REGEX.search(value)
    if match:
        return f"t3_{match.group(1)}"
    return None


def qualifies_for_subreddit(link: str, subreddit: str) -> bool:
    if not link:
        return False
    normalized = link.lower()
    target = f"/r/{subreddit.lower()}/"
    return target in normalized


async def collect_ids_from_page(page: Page, subreddit: str) -> Set[str]:
    """Gather all post IDs currently rendered on the page."""
    ids: Set[str] = set()
    posts = await page.query_selector_all(POST_SELECTOR)
    for post in posts:
        permalink = await post.get_attribute("permalink")
        if permalink:
            link = permalink if permalink.startswith("http") else f"https://www.reddit.com{permalink}"
            if qualifies_for_subreddit(link, subreddit):
                ids.add(link)
    if ids:
        return ids
    comment_links = await page.query_selector_all("a[href*='/comments/']")
    for anchor in comment_links:
        href = await anchor.get_attribute("href")
        if href:
            link = href if href.startswith("http") else f"https://www.reddit.com{href}"
            if qualifies_for_subreddit(link, subreddit):
                ids.add(link)
    return ids


def load_existing_links(output_path: Path) -> Set[str]:
    if not output_path.exists():
        return set()
    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return set(data.get("post_ids", []))


def write_output(output_path: Path, links: Iterable[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"post_ids": sorted(links)}, indent=2), encoding="utf-8")


async def scroll_and_collect(
    page: Page,
    max_posts: Optional[int],
    max_iterations: Optional[int],
    scroll_delay: float,
    output_path: Path,
    existing_links: Set[str],
    subreddit: str,
) -> list[str]:
    seen: Set[str] = set(existing_links)
    iteration = 0
    while True:
        iteration += 1
        current_ids = await collect_ids_from_page(page, subreddit)
        before = len(seen)
        new_links = [link for link in current_ids if link not in seen]
        if new_links:
            seen.update(new_links)
        else:
            seen.update(current_ids)
        after = len(seen)
        write_output(output_path, seen)
        print(f"[{iteration:03d}] Collected {len(current_ids)} visible posts (total {after})")
        if max_posts and len(seen) >= max_posts:
            print(f"Reached requested max of {max_posts} posts.")
            break
        if max_iterations and iteration >= max_iterations:
            print(f"Reached scroll iteration cap ({max_iterations}).")
            break

        await page.evaluate("window.scrollBy(0, window.innerHeight * 1.4)")
        await page.wait_for_timeout(scroll_delay * 1000)
    return sorted(seen)


async def run(
    subreddit: str,
    headless: bool,
    storage_state: Optional[Path],
    max_posts: Optional[int],
    max_iterations: Optional[int],
    scroll_delay: float,
    output_path: Path,
    view_path: Optional[str],
) -> list[str]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        if storage_state:
            context = await browser.new_context(storage_state=str(storage_state))
        else:
            context = await browser.new_context()
        page = await context.new_page()
        try:
            base = "https://www.reddit.com"
            if view_path:
                target = f"{base}/r/{subreddit}/{view_path}"
            else:
                target = f"{base}/r/{subreddit}/"
            await page.goto(target, wait_until="domcontentloaded", timeout=60_000)
        except Exception as err:
            print(f"Failed to navigate: {err}")
            await browser.close()
            raise
        existing = load_existing_links(output_path)
        if existing:
            print(f"Found {len(existing)} previously collected links; skipping duplicates.")
        return await scroll_and_collect(
            page,
            max_posts,
            max_iterations,
            scroll_delay,
            output_path,
            existing,
            subreddit,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scroll Reddit and gather post IDs via Playwright.")
    parser.add_argument("--subreddit", "-s", default="SextStories", help="Target subreddit.")
    parser.add_argument(
        "--storage-state",
        "-S",
        type=Path,
        help="Path to Playwright storage state JSON to reuse a logged-in session.",
    )
    parser.add_argument(
        "--max-posts",
        "-m",
        type=int,
        default=None,
        help="Optional cap on the number of unique links; omit for unlimited.",
    )
    parser.add_argument(
        "--max-iterations",
        "-i",
        type=int,
        default=None,
        help="Maximum number of scroll iterations before quitting (omit for unlimited).",
    )
    parser.add_argument(
        "--view-path",
        "-v",
        default="top/?t=all",
        help="Suffix to append to /r/<subreddit>/ when opening the page (e.g., top/?t=all).",
    )
    parser.add_argument(
        "--scroll-delay",
        "-d",
        type=float,
        default=1.5,
        help="Seconds to wait after each scroll to let new content load.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Playwright in headless mode (default is headed).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("scroller_post_ids.json"),
        help="Where to write the list of collected post IDs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    max_posts = args.max_posts if args.max_posts is not None and args.max_posts > 0 else None
    result = asyncio.run(
        run(
            subreddit=args.subreddit,
            headless=args.headless,
            storage_state=args.storage_state,
            max_posts=max_posts,
            max_iterations=args.max_iterations,
            scroll_delay=args.scroll_delay,
            output_path=args.output,
            view_path=args.view_path,
        )
    )
    print(f"Wrote {len(result)} post IDs to {args.output}")
    print(f"Wrote {len(result)} post IDs to {args.output}")


if __name__ == "__main__":
    main()

