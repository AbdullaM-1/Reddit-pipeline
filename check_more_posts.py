#!/usr/bin/env python
"""Utility to probe whether Reddit still has posts after a given post ID."""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from typing import Iterable, Optional

from colorama import Fore, Style

from posts import getHeaders, getSession, getToken, getUserAgent


DEFAULT_QUERY_SEQUENCE = [chr(code) for code in range(ord("a"), ord("z") + 1)]
PER_BATCH_SLEEP = 1.0


def normalize_fullname(post_id: str) -> str:
    if post_id.startswith("t3_"):
        return post_id
    return f"t3_{post_id}"


def parse_date_to_timestamp(value: str) -> int:
    formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return int(dt.replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    raise ValueError("Invalid date format: use YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS]")


def request_with_retries(session, url: str, headers: dict[str, str], params: dict[str, str | int]) -> dict:
    retries = 0
    while retries < 3:
        response = session.get(url, headers=headers, params=params)
        if response.status_code == 429:
            retries += 1
            backoff = 2**retries
            print(f"{Fore.YELLOW}Rate limited, sleeping {backoff}s…{Style.RESET_ALL}")
            time.sleep(backoff)
            continue
        response.raise_for_status()
        return response.json().get("data", {})
    raise RuntimeError("Too many rate limit retries.")


def fetch_listing_chunk(
    subreddit: str,
    sort_filter: Optional[str],
    after: Optional[str],
    limit: int,
    token: Optional[str],
    after_date: Optional[int],
    before_date: Optional[int],
) -> dict:
    session = getSession()
    headers = getHeaders(getUserAgent(), token or "")
    use_search = after_date is not None or before_date is not None
    if use_search:
        url = (
            f"https://oauth.reddit.com/r/{subreddit}/search.json"
            if token
            else f"https://www.reddit.com/r/{subreddit}/search.json"
        )
        lower = after_date or 0
        upper = before_date or int(time.time())
        params = {
            "limit": limit,
            "show": "all",
            "restrict_sr": "on",
            "q": f"timestamp:{lower}..{upper}",
            "syntax": "cloudsearch",
        }
        if sort_filter:
            params["sort"] = sort_filter
    else:
        sort_key = sort_filter or "new"
        url = (
            f"https://oauth.reddit.com/r/{subreddit}/{sort_key}.json"
            if token
            else f"https://www.reddit.com/r/{subreddit}/{sort_key}.json"
        )
        params = {"limit": limit, "show": "all", "sr_detail": True}
        if after:
            params["after"] = after
    return request_with_retries(session, url, headers, params)


def run_query_cycle(
    subreddit: str,
    queries: Iterable[str],
    sort_filter: Optional[str],
    limit: int,
    token: Optional[str],
    cid: Optional[str],
    iid: Optional[str],
    include_over_18: bool,
    safe: Optional[str],
) -> None:
    session = getSession()
    headers = getHeaders(getUserAgent(), token or "")
    base_url = (
        f"https://oauth.reddit.com/r/{subreddit}/search.json"
        if token
        else f"https://www.reddit.com/r/{subreddit}/search.json"
    )
    for query in queries:
        if not query:
            continue
        print(
            f"{Fore.CYAN}Searching for q={query!r} "
            f"({subreddit} via {base_url}){Style.RESET_ALL}"
        )
        after_token = None
        total_found = 0
        page = 0
        while True:
            params = {
                "limit": limit,
                "restrict_sr": "on",
                "syntax": "cloudsearch",
                "sort": sort_filter or "new",
                "q": query,
            }
            if after_token:
                params["after"] = after_token
            if cid:
                params["cId"] = cid
            if iid:
                params["iId"] = iid
            if include_over_18:
                params["include_over_18"] = "on"
            if safe:
                params["safe"] = safe
            data = request_with_retries(session, base_url, headers, params)
            children = data.get("children", [])
            page += 1
            if not children:
                print(
                    f"{Fore.YELLOW}Query {query!r} page {page} returned 0 posts; moving to next query.{Style.RESET_ALL}"
                )
                break
            total_found += len(children)
            print(f"{Fore.GREEN}Page {page}: {len(children)} hits (total {total_found}){Style.RESET_ALL}")
            for child in children[:3]:
                post = child.get("data", {})
                print(f"  - {post.get('name')} {post.get('title', '')[:60]}")
            after_token = data.get("after")
            if not after_token:
                print(f"{Fore.YELLOW}Query {query!r} exhausted after {total_found} posts.{Style.RESET_ALL}")
                break
            time.sleep(PER_BATCH_SLEEP)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check if there are more Reddit posts after a specific post ID."
    )
    parser.add_argument(
        "--subreddit", "-s", default="SextStories", help="Target subreddit name (without r/)"
    )
    parser.add_argument(
        "--sort",
        "-S",
        help="Optional listing sort (hot/new/top/rising/controversial); defaults to 'new' if omitted.",
    )
    parser.add_argument(
        "--after",
        "-a",
        help="Post ID or fullname (e.g., 1ncqans or t3_1ncqans) to page after (required unless you provide a date range)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=25,
        help="Number of posts to request in the next page",
    )
    parser.add_argument(
        "--after-date",
        help="Earliest UTC date (YYYY-MM-DD or ISO) to include in the next batch",
    )
    parser.add_argument(
        "--before-date",
        help="Latest UTC date (YYYY-MM-DD or ISO) to include in the next batch",
    )
    parser.add_argument(
        "--query-cycle",
        "-Q",
        nargs="?",
        const=",".join(DEFAULT_QUERY_SEQUENCE),
        help=(
            "When set, run the search endpoint for each comma-separated q value "
            "(defaults to the alphabet). Stream moves to the next query when the "
            "current one no longer returns pages."
        ),
    )
    parser.add_argument("--cid", help="Optional cId parameter to pass to search requests.")
    parser.add_argument("--iid", help="Optional iId parameter to pass to search requests.")
    parser.add_argument(
        "--include-over-18",
        action="store_true",
        help="Send include_over_18=on on search requests (needed for NSFW subreddits).",
    )
    parser.add_argument(
        "--safe",
        choices=["true", "false"],
        help="Add the safe parameter (true/false) on search requests.",
    )
    args = parser.parse_args()

    subreddit = args.subreddit.lstrip("r/").lstrip("/")

    token = getToken({}, 10) or ""
    if not token:
        print(f"{Fore.YELLOW}Running without auth token; rate limits may apply{Style.RESET_ALL}")

    try:
        after_ts = parse_date_to_timestamp(args.after_date) if args.after_date else None
    except ValueError as err:
        print(f"{Fore.RED}{err}{Style.RESET_ALL}")
        return
    try:
        before_ts = parse_date_to_timestamp(args.before_date) if args.before_date else None
    except ValueError as err:
        print(f"{Fore.RED}{err}{Style.RESET_ALL}")
        return

    query_cycle_values: Optional[list[str]] = None
    if args.query_cycle:
        query_cycle_values = [q.strip() for q in args.query_cycle.split(",") if q.strip()]

    if not query_cycle_values and not args.after and after_ts is None and before_ts is None:
        print(f"{Fore.RED}Provide --after or at least one date filter (--after-date/--before-date).{Style.RESET_ALL}")
        return

    if query_cycle_values:
        run_query_cycle(
            subreddit,
            query_cycle_values,
            args.sort,
            args.limit,
            token,
            args.cid,
            args.iid,
            args.include_over_18,
            args.safe,
        )
        return

    after_fullname = normalize_fullname(args.after) if args.after else None
    try:
        data = fetch_listing_chunk(
            subreddit,
            args.sort,
            after_fullname,
            args.limit,
            token,
            after_ts,
            before_ts,
        )
    except Exception as err:
        print(f"{Fore.RED}Failed to fetch listing: {err}{Style.RESET_ALL}")
        return

    children = data.get("children", [])
    print(
        f"{Fore.CYAN}Fetched {len(children)} posts after {after_fullname} "
        f"(limit={args.limit}){Style.RESET_ALL}"
    )
    if not children:
        print(f"{Fore.YELLOW}No posts were returned after that ID.{Style.RESET_ALL}")
    else:
        print(f"Post IDs in this batch:")
        for child in children[: min(10, len(children))]:
            post = child.get("data", {})
            print(f"  - {post.get('name')} ({post.get('id')}) {post.get('title', '')[:60]}")
    after = data.get("after")
    if after:
        print(f"{Fore.GREEN}Reddit still has more posts; next after token: {after}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Reddit ended the listing after that page.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()

