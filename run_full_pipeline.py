#!/usr/bin/env python
"""
Single-run pipeline that:
1. Streams every available post from a subreddit (paged via listing + detail calls)
2. For each post, identifies the correct outbound link from the author's comment
3. Downloads every image found at that link
4. Runs OCR on the downloaded images
5. Stores a per-post result JSON under pipeline_results/<post_id>.json

This script stitches together the previously built modules:
    posts.py                        -> low-level Reddit fetching helpers
    identify_correct_links.py       -> link selection logic
    extract_images_from_links.py    -> HTML/image scraping + download
    extract_text_from_images.py     -> EasyOCR / pytesseract text extraction
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence, TextIO, cast
from requests.exceptions import HTTPError
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

from colorama import Fore, Style
from dotenv import dotenv_values

# Force UTF-8 output on Windows terminals so we can dump the raw JSON safely.
if sys.platform.startswith("win"):
    stdout = cast(TextIO, sys.stdout)
    stderr = cast(TextIO, sys.stderr)
    stdout_reconfigure = getattr(stdout, "reconfigure", None)
    if callable(stdout_reconfigure):
        stdout_reconfigure(encoding="utf-8")
    stderr_reconfigure = getattr(stderr, "reconfigure", None)
    if callable(stderr_reconfigure):
        stderr_reconfigure(encoding="utf-8")
    if not callable(stdout_reconfigure):
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from posts import (
    buildComments,
    buildMedia,
    buildPosts,
    fetchAwards,
    fetchPostArticleByPostID,
    getHeaders,
    getSession,
    getToken,
    getUserAgent,
    Post as RedditPost,
)

from identify_correct_links import (
    extract_links_from_text,
    find_author_comment,
    identify_correct_link_with_llm,
)
from extract_images_from_links import (
    download_image,
    extract_images_from_url,
    sanitize_filename,
)
from extract_text_from_images import (
    extract_text_from_image_easyocr,
    extract_text_from_image_pytesseract,
    should_skip_image,
)

# Optional OCR libraries
EASYOCR_AVAILABLE = False
PYTESSERACT_AVAILABLE = False
PYTESSERACT_READY = False
easyocr = None
pytesseract = None
Image = None

try:
    import easyocr  # type: ignore

    EASYOCR_AVAILABLE = True
except Exception:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        PYTESSERACT_AVAILABLE = True
    except Exception:
        pass

# ============================================
# CONFIGURATION
# ============================================
DEFAULT_SUBREDDIT = "SextStories"
SORT_FILTER = "new"  # hot/new/top/rising/controversial
FETCH_ALL = True
MAX_POSTS = None  # None means "as many as Reddit exposes (~1000 per sort)"; set int to cap
POSTS_PER_REQUEST_AUTH = 100
POSTS_PER_REQUEST_ANON = 25
MAX_LISTING_RETRIES = 5
BASE_BACKOFF_SECONDS = 5
PER_BATCH_SLEEP = 1.0
DEFAULT_QUERY_SEQUENCE = [chr(code) for code in range(ord("a"), ord("z") + 1)]

OUTPUT_ROOT = Path("pipeline_results")
IMAGES_DIR = Path("downloaded_images")
STATE_PATH = Path("pagination_state.json")
AGGREGATE_OUTPUT_FILE = OUTPUT_ROOT / "pipeline_results.json"
CHUNKS_DIR = OUTPUT_ROOT / "chunks"
IMAGES_DIR.mkdir(exist_ok=True)
OUTPUT_ROOT.mkdir(exist_ok=True)
CHUNKS_DIR.mkdir(exist_ok=True)

AGGREGATE_LOCK = threading.Lock()
AGGREGATE_DATA: Dict[str, Any] = {"metadata": {}, "posts": {}, "order": []}
CHUNK_SIZE = 50
PROCESSED_CHUNKS_DIR = Path("processed_link_chunks")
PROCESSED_CHUNKS_DIR = Path("processed_link_chunks")


def init_aggregate_storage(output_file: Optional[Path] = None) -> None:
    global AGGREGATE_DATA, AGGREGATE_OUTPUT_FILE
    if output_file:
        AGGREGATE_OUTPUT_FILE = output_file
    AGGREGATE_DATA = {"metadata": {}, "posts": {}, "order": []}
    if AGGREGATE_OUTPUT_FILE.exists():
        try:
            data = json.loads(AGGREGATE_OUTPUT_FILE.read_text(encoding="utf-8"))
            AGGREGATE_DATA["metadata"] = data.get("metadata", {})
            AGGREGATE_DATA["posts"] = data.get("posts", {})
            AGGREGATE_DATA["order"] = data.get("order", [])
        except json.JSONDecodeError:
            print(
                f"{Fore.YELLOW}Aggregated pipeline results corrupted; starting fresh.{Style.RESET_ALL}"
            )
    record_restart_chunk(len(AGGREGATE_DATA.get("order", [])))


def get_existing_result(post_id: str) -> Optional[Dict[str, Any]]:
    with AGGREGATE_LOCK:
        posts = AGGREGATE_DATA.setdefault("posts", {})
        return posts.get(post_id)


def _atomic_replace(tmp_path: Path, target_path: Path, attempts: int = 5) -> bool:
    """Try replacing target with tmp file, retrying on intermittent permission errors."""
    for attempt in range(attempts):
        try:
            tmp_path.replace(target_path)
            return True
        except PermissionError:
            if attempt == attempts - 1:
                return False
            time.sleep(0.1 * (attempt + 1))
    return False


def persist_result(payload: Dict[str, Any]) -> None:
    with AGGREGATE_LOCK:
        posts = AGGREGATE_DATA.setdefault("posts", {})
        order = AGGREGATE_DATA.setdefault("order", [])
        posts[payload["post_id"]] = payload
        if payload["post_id"] not in order:
            order.append(payload["post_id"])
        metadata = AGGREGATE_DATA.setdefault("metadata", {})
        metadata["total_posts"] = len(posts)
        metadata["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        metadata.setdefault("chunk_ids", [])
        maybe_create_chunk(metadata["total_posts"], metadata)
        tmp_path = AGGREGATE_OUTPUT_FILE.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(AGGREGATE_DATA, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if not _atomic_replace(tmp_path, AGGREGATE_OUTPUT_FILE):
            print(
                f"{Fore.YELLOW}Unable to replace {AGGREGATE_OUTPUT_FILE.name}; "
                "falling back to overwriting directly.{Style.RESET_ALL}"
            )
            try:
                AGGREGATE_OUTPUT_FILE.write_text(
                    tmp_path.read_text(encoding="utf-8"), encoding="utf-8"
                )
            except Exception as exc:
                print(
                    f"{Fore.RED}Failed to persist aggregated results: {exc}{Style.RESET_ALL}"
                )
            finally:
                tmp_path.unlink(missing_ok=True)


def maybe_create_chunk(total_posts: int, metadata: Dict[str, Any]) -> None:
    if CHUNK_SIZE <= 0 or total_posts == 0 or total_posts % CHUNK_SIZE != 0:
        return
    chunk_id = total_posts // CHUNK_SIZE
    chunk_ids = metadata.setdefault("chunk_ids", [])
    if chunk_id in chunk_ids:
        return

    order = AGGREGATE_DATA.get("order", [])
    start_index = (chunk_id - 1) * CHUNK_SIZE
    end_index = chunk_id * CHUNK_SIZE
    chunk_post_ids = order[start_index:end_index]
    if len(chunk_post_ids) < CHUNK_SIZE:
        return

    posts = AGGREGATE_DATA.get("posts", {})
    chunk_posts = {pid: posts[pid] for pid in chunk_post_ids if pid in posts}
    chunk_payload = {
        "chunk_id": chunk_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "range": {
            "start": start_index + 1,
            "end": min(end_index, total_posts),
            "count": len(chunk_post_ids),
        },
        "posts": chunk_posts,
    }
    chunk_path = CHUNKS_DIR / f"pipeline_results_chunk_{chunk_id:04d}.json"
    tmp_path = chunk_path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(chunk_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp_path.replace(chunk_path)
    chunk_ids.append(chunk_id)


def record_restart_chunk(processed_posts: int) -> None:
    restart_payload = {
        "type": "restart_snapshot",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "processed_posts": processed_posts,
    }
    filename = f"pipeline_restart_{int(time.time())}.json"
    restart_path = CHUNKS_DIR / filename
    restart_path.write_text(
        json.dumps(restart_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_pagination_state(subreddit: str, sort_filter: str) -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if data.get("subreddit") != subreddit or data.get("sort") != sort_filter:
        return {}
    return data


def save_pagination_state(
    subreddit: str,
    sort_filter: str,
    after: Optional[str],
    last_post_fullname: Optional[str],
    processed_total: int,
) -> None:
    payload = {
        "subreddit": subreddit,
        "sort": sort_filter,
        "after": after,
        "last_post_fullname": last_post_fullname,
        "processed_posts": processed_total,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    tmp_path = STATE_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(STATE_PATH)

# Reddit credentials (optional but recommended to avoid 429s)
config = dotenv_values(".env")
USERNAME = config.get("username", "")
PASSWORD = config.get("password", "")
CLIENT_ID = config.get("client_id", "")
CLIENT_SECRET = config.get("client_secret", "")
# ============================================


def ensure_token() -> str:
    """Fetch OAuth token if creds exist; otherwise empty string."""
    if not all([CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD]):
        return ""
    params = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
    }
    return getToken(params, 10)


def fetch_listing(
    session, url: str, headers: Dict[str, str], params: Dict[str, str]
) -> Optional[dict]:
    """Fetch subreddit listing with retries/backoff."""
    for attempt in range(1, MAX_LISTING_RETRIES + 1):
        try:
            response = session.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 429:
                raise ConnectionError("HTTP 429 Too Many Requests")
            response.raise_for_status()
            return response.json()
        except Exception as err:
            if attempt == MAX_LISTING_RETRIES:
                print(
                    f"{Fore.RED}Listing failed after {attempt} attempts: {err}{Style.RESET_ALL}"
                )
                return None
            backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(
                f"{Fore.YELLOW}Listing attempt {attempt}/{MAX_LISTING_RETRIES} failed: {err}{Style.RESET_ALL}"
            )
            print(f"{Fore.YELLOW}Sleeping {backoff}s before retrying...{Style.RESET_ALL}")
            time.sleep(backoff)
    return None


OCR_LOCK = threading.Lock()


def normalize_fullname(value: str) -> str:
    if value.startswith("t3_"):
        return value
    return f"t3_{value}"


def extract_fullname_from_link(link: str) -> Optional[str]:
    pattern = r"/comments/([a-z0-9]{6,})"
    match = re.search(pattern, link or "", re.IGNORECASE)
    if match:
        return f"t3_{match.group(1)}"
    return None


def load_chunk_links(path: Path) -> List[str]:
    if not path.exists():
        print(f"{Fore.YELLOW}Link chunk {path} not found; skipping.{Style.RESET_ALL}")
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"{Fore.YELLOW}Failed to decode chunk {path}; skipping.{Style.RESET_ALL}")
        return []
    return [link for link in payload.get("unprocessed_links", []) if isinstance(link, str)]


def fetch_post_article(
    subreddit: str, post_id: str, token: str, log_response: bool = False
) -> Dict[str, Any]:
    attempts = 0
    while attempts < 3:
        try:
            detail = cast(
                Dict[str, Any], fetchPostArticleByPostID(subreddit, post_id, token)
            )
            if log_response:
                print(
                    f"{Fore.BLUE}Endpoint payload for {post_id}:{Style.RESET_ALL}\n"
                    f"{json.dumps(detail, indent=2, ensure_ascii=False)}"
                )
            return detail
        except HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                backoff = BASE_BACKOFF_SECONDS * (2 ** attempts)
                print(
                    f"{Fore.YELLOW}Rate limited fetching {post_id}; sleeping {backoff}s...{Style.RESET_ALL}"
                )
                time.sleep(backoff)
                attempts += 1
                continue
            print(
                f"{Fore.RED}Fail to get post by id Status Code:{status or exc} Subreddit name:{subreddit} Error :{exc}{Style.RESET_ALL}"
            )
            return {}
    print(f"{Fore.RED}Giving up on post {post_id} after repeated 429s.{Style.RESET_ALL}")
    return {}


def hydrate_posts_from_links(
    links: Sequence[str],
    subreddit: str,
    token: str,
    *,
    log_endpoint_results: bool = False,
) -> List[RedditPost]:
    if not subreddit.startswith("r/"):
        subreddit = f"r/{subreddit}"
    posts: List[RedditPost] = []
    for link in links:
        fullname = extract_fullname_from_link(link)
        if not fullname:
            continue
        post_id = fullname.split("_", 1)[1]
        detail = fetch_post_article(
            subreddit, post_id, token, log_response=log_endpoint_results
        )
        if log_endpoint_results:
            result_state = detail.get("result_state") or {}
            print(
                f"{Fore.BLUE}Endpoint detail for {post_id}: {result_state}{Style.RESET_ALL}"
            )
        payload = detail.get("post") or []
        post_data: Dict[str, Any] = {
            "id": post_id,
            "name": fullname,
            "subreddit": subreddit,
        }
        if isinstance(payload, list) and payload:
            first = payload[0] if payload else None
            if first:
                first_data = first.get("data", {})
                post_children = first_data.get("children", [])
                if post_children:
                    post_detail_data = post_children[0].get("data", {})
                else:
                    post_detail_data = first_data
                post_data.update(post_detail_data)
                media_children = post_detail_data.get("children", [])
                if media_children:
                    post_data["media_content"] = buildMedia(
                        media_children[0].get("data", {})
                    )
            if len(payload) > 1:
                comments_children = payload[1].get("data", {}).get("children", [])
                subreddit_users = defaultdict(set)
                comments, num_comments = buildComments(
                    comments_children,
                    subreddit_users,
                    post_data.get("subreddit_id", ""),
                    post_data.get("subreddit", subreddit),
                )
                post_data["comments"] = comments
                post_data["num_comments"] = num_comments
        post_data["_detail_payload"] = payload
        posts.append(cast(RedditPost, post_data))
    return posts


def write_processed_chunk(chunk_path: Path, links: Sequence[str]) -> None:
    PROCESSED_CHUNKS_DIR.mkdir(exist_ok=True, parents=True)
    dest = PROCESSED_CHUNKS_DIR / f"{chunk_path.stem}.processed.json"
    dest.write_text(
        json.dumps({"processed_links": list(links)}, indent=2), encoding="utf-8"
    )


def run_chunk_mode(
    chunk_paths: Sequence[Path],
    subreddit: str,
    reader: Any | None,
    workers: int,
    ocr_workers: int,
    max_posts: Optional[int],
) -> None:
    token = ensure_token()
    processed_total = 0
    for chunk in chunk_paths:
        chunk_result_path = OUTPUT_ROOT / f"{chunk.stem}.json"
        init_aggregate_storage(chunk_result_path)
        print(
            f"{Fore.CYAN}Writing chunk results to {chunk_result_path}{Style.RESET_ALL}"
        )
        if max_posts and processed_total >= max_posts:
            break
        links = load_chunk_links(chunk)
        if not links:
            continue
        for offset in range(0, len(links), workers):
            if max_posts and processed_total >= max_posts:
                break
            batch_links = links[offset : offset + workers]
            posts = hydrate_posts_from_links(
                batch_links, subreddit, token, log_endpoint_results=True
            )
            if not posts:
                continue
            if max_posts:
                remaining = max_posts - processed_total
                if remaining <= 0:
                    break
                posts = posts[:remaining]
            process_batch_concurrently(posts, reader, workers, ocr_workers)
            processed_total += len(posts)
        write_processed_chunk(chunk, links)
    print(
        f"\n{Fore.CYAN}Chunk pipeline complete. Processed {processed_total} posts from link chunks.{Style.RESET_ALL}"
    )


def stream_full_post_batches(
    subreddit: str,
    sort_filter: str,
    fetch_all: bool,
    max_posts: Optional[int],
    resume_after: Optional[str] = None,
) -> Generator[List[RedditPost], None, None]:
    """Yield batches of full post objects (with comments, media) by paging through Reddit listings."""
    token = ensure_token()
    session = getSession()
    awards = fetchAwards()

    if not subreddit.startswith("r/"):
        subreddit = f"r/{subreddit}"

    posts_per_request = (
        min(POSTS_PER_REQUEST_AUTH, 100)
        if token
        else min(POSTS_PER_REQUEST_ANON, 25)
    )

    fetched = 0
    state = load_pagination_state(subreddit, sort_filter)
    saved_after = state.get("after")
    if resume_after:
        after = normalize_fullname(resume_after)
        print(
            f"{Fore.YELLOW}Resuming listing from user-specified cursor {after}{Style.RESET_ALL}"
        )
    else:
        after = saved_after
        if after:
            print(f"{Fore.YELLOW}Resuming listing from stored cursor {after}{Style.RESET_ALL}")
    batch = 0
    if after:
        print(f"{Fore.YELLOW}Resuming listing from stored cursor {after}{Style.RESET_ALL}")

    print(f"{Fore.CYAN}Starting stream from {subreddit} ({sort_filter}){Style.RESET_ALL}")
    if fetch_all:
        print(
            f"{Fore.YELLOW}Full-history mode: will fetch until Reddit returns no 'after' token.{Style.RESET_ALL}"
        )

    while True:
        if max_posts and fetched >= max_posts:
            break
        current_limit = posts_per_request
        if max_posts:
            current_limit = min(current_limit, max_posts - fetched)
            if current_limit <= 0:
                break

        batch += 1
        params = {"limit": current_limit, "show": "all", "sr_detail": True}
        if after:
            params["after"] = after

        url = (
            f"https://oauth.reddit.com/{subreddit}/{sort_filter}.json"
            if token
            else f"https://www.reddit.com/{subreddit}/{sort_filter}.json"
        )
        headers = getHeaders(getUserAgent(), token)

        print(
            f"{Fore.CYAN}Fetching batch {batch} (limit={current_limit}, after={after})...{Style.RESET_ALL}"
        )
        listing = fetch_listing(session, url, headers, params)
        if not listing or "data" not in listing:
            print(f"{Fore.YELLOW}No listing data returned; stopping.{Style.RESET_ALL}")
            break

        raw_children = listing["data"].get("children", [])
        if not raw_children:
            print(f"{Fore.YELLOW}Listing returned zero children; stopping.{Style.RESET_ALL}")
            break

        built_posts = buildPosts(listing, awards)
        if max_posts and fetched + len(built_posts) > max_posts:
            remaining = max_posts - fetched
            built_posts = built_posts[:remaining]
        print(
            f"{Fore.GREEN}Received {len(built_posts)} posts in batch {batch}{Style.RESET_ALL}"
        )

        batch_posts: List[RedditPost] = []
        for post in built_posts:
            post_id = post.get("id")
            detail = fetchPostArticleByPostID(
                post.get("subreddit", subreddit), post_id, token
            )
            payload = detail.get("post") or []
            if isinstance(payload, list) and payload:
                first = payload[0] if len(payload) > 0 else None
                if first:
                    media_children = first.get("data", {}).get("children", [])
                    if media_children:
                        post["media_content"] = buildMedia(
                            media_children[0].get("data", {})
                        )
                if len(payload) > 1:
                    comments_children = payload[1].get("data", {}).get("children", [])
                    subreddit_users = defaultdict(set)
                    comments, num_comments = buildComments(
                        comments_children,
                        subreddit_users,
                        post.get("subreddit_id", ""),
                        post.get("subreddit", subreddit),
                    )
                    post["comments"] = comments
                    post["num_comments"] = num_comments

            fetched += 1
            batch_posts.append(post)

        if batch_posts:
            yield batch_posts

        last_fullname = (
            batch_posts[-1].get("name") if batch_posts else state.get("last_post_fullname")
        )
        save_pagination_state(
            subreddit=subreddit,
            sort_filter=sort_filter,
            after=after,
            last_post_fullname=last_fullname,
            processed_total=fetched,
        )
        after = listing["data"].get("after")
        if not after or (not fetch_all and max_posts and fetched >= max_posts):
            break

        time.sleep(PER_BATCH_SLEEP)


def stream_search_query_batches(
    subreddit: str,
    sort_filter: str,
    queries: List[str],
    max_posts: Optional[int],
    page_limit: Optional[int],
    cid: Optional[str],
    iid: Optional[str],
    include_over_18: bool,
    safe: Optional[str],
) -> Generator[List[RedditPost], None, None]:
    token = ensure_token()
    session = getSession()
    awards = fetchAwards()

    if not subreddit.startswith("r/"):
        subreddit = f"r/{subreddit}"

    posts_per_request = (
        min(POSTS_PER_REQUEST_AUTH, 100)
        if token
        else min(POSTS_PER_REQUEST_ANON, 25)
    )
    fetched = 0
    page_counter = defaultdict(int)
    print(
        f"{Fore.CYAN}Starting search-based stream from {subreddit} ({sort_filter}){Style.RESET_ALL}"
    )
    for query in queries:
        if max_posts and fetched >= max_posts:
            break
        if not query:
            continue
        after = None
        while True:
            if max_posts and fetched >= max_posts:
                break
            current_limit = posts_per_request if page_limit is None else min(posts_per_request, page_limit)
            page_counter[query] += 1
            params = {
                "limit": current_limit,
                "restrict_sr": "on",
                "syntax": "cloudsearch",
                "q": query,
                "show": "all",
            }
            if sort_filter:
                params["sort"] = sort_filter
            if include_over_18:
                params["include_over_18"] = "on"
            if safe:
                params["safe"] = safe
            if cid:
                params["cId"] = cid
            if iid:
                params["iId"] = iid
            if after:
                params["after"] = after

            url = (
                f"https://oauth.reddit.com/{subreddit}/search.json"
                if token
                else f"https://www.reddit.com/{subreddit}/search.json"
            )
            headers = getHeaders(getUserAgent(), token)
            print(
                f"{Fore.CYAN}Search query '{query}' page {page_counter[query]} (limit={current_limit}, after={after}){Style.RESET_ALL}"
            )
            listing = fetch_listing(session, url, headers, params)
            if not listing or "data" not in listing:
                print(
                    f"{Fore.YELLOW}Search query '{query}' returned no listing data; moving to next query.{Style.RESET_ALL}"
                )
                break

            raw_children = listing["data"].get("children", [])
            if not raw_children:
                print(
                    f"{Fore.YELLOW}Search query '{query}' returned zero children; moving to next query.{Style.RESET_ALL}"
                )
                break

            built_posts = buildPosts(listing, awards)
            print(
                f"{Fore.GREEN}Search query '{query}' page {page_counter[query]} returned {len(built_posts)} posts{Style.RESET_ALL}"
            )

            batch_posts: List[RedditPost] = []
            for post in built_posts:
                post_id = post.get("id")
                detail = fetchPostArticleByPostID(
                    post.get("subreddit", subreddit), post_id, token
                )
                payload = detail.get("post") or []
                if isinstance(payload, list) and payload:
                    first = payload[0] if len(payload) > 0 else None
                    if first:
                        media_children = first.get("data", {}).get("children", [])
                        if media_children:
                            post["media_content"] = buildMedia(
                                media_children[0].get("data", {})
                            )
                    if len(payload) > 1:
                        comments_children = payload[1].get("data", {}).get("children", [])
                        subreddit_users = defaultdict(set)
                        comments, num_comments = buildComments(
                            comments_children,
                            subreddit_users,
                            post.get("subreddit_id", ""),
                            post.get("subreddit", subreddit),
                        )
                        post["comments"] = comments
                        post["num_comments"] = num_comments

                fetched += 1
                batch_posts.append(post)

            if batch_posts:
                yield batch_posts

            after_token = listing["data"].get("after")
            if not after_token:
                print(
                    f"{Fore.YELLOW}Search query '{query}' exhausted after {page_counter[query]} pages.{Style.RESET_ALL}"
                )
                break
            after = after_token

            time.sleep(PER_BATCH_SLEEP)



def step_identify_correct_link(post: RedditPost) -> Optional[str]:
    post_title = post.get("title", "")
    author_comment = find_author_comment(cast(Dict[str, Any], post))
    if not author_comment:
        author_comment = extract_author_comment_from_payload(post)
        if not author_comment:
            print(f"  {Fore.YELLOW}No author comment found.{Style.RESET_ALL}")
            return None
    links = extract_links_from_text(author_comment.get("body", ""))
    if not links:
        print(f"  {Fore.YELLOW}No links in author comment.{Style.RESET_ALL}")
        return None
    if len(links) == 1:
        return links[0]
    return identify_correct_link_with_llm(
        post_title=post_title,
        author_comment=author_comment.get("body", ""),
        links=links,
        use_openai=True,
    )


def extract_author_comment_from_payload(post: RedditPost) -> Optional[Dict[str, Any]]:
    author = post.get("author")
    payload = post.get("_detail_payload") or []
    if not author or not isinstance(payload, list) or len(payload) < 2:
        return None
    comments_children = payload[1].get("data", {}).get("children", [])
    if not comments_children:
        return None
    subreddit_users = defaultdict(set)
    comments, _ = buildComments(
        comments_children,
        subreddit_users,
        post.get("subreddit_id", ""),
        post.get("subreddit", ""),
    )
    temp_post = {"author": author, "comments": comments}
    return find_author_comment(temp_post)


def step_download_images(post_id: str, correct_link: str) -> Dict:
    session = getSession()
    image_urls = extract_images_from_url(correct_link, session)
    print(
        f"  {Fore.CYAN}Image extraction found {len(image_urls)} URLs for post {post_id}{Style.RESET_ALL}"
    )
    post_dir = IMAGES_DIR / sanitize_filename(post_id)
    post_dir.mkdir(parents=True, exist_ok=True)

    local_images = []
    for idx, url in enumerate(image_urls, 1):
        filename = sanitize_filename(Path(url).name) or f"image_{idx}"
        save_path = post_dir / filename
        counter = 1
        while save_path.exists():
            save_path = post_dir / f"{save_path.stem}_{counter}{save_path.suffix}"
            counter += 1
        if download_image(url, str(save_path), session):
            print(f"    {Fore.GREEN}[saved] Image {idx}: {save_path.name}{Style.RESET_ALL}")
            local_images.append(
                {
                    "url": url,
                    "local_path": str(save_path),
                }
            )
        else:
            print(f"    {Fore.YELLOW}[skip] Failed download {idx}: {url[:80]}{Style.RESET_ALL}")
    return {
        "image_urls": image_urls,
        "local_images": local_images,
        "downloaded_count": len(local_images),
    }


def init_ocr_reader():
    if not EASYOCR_AVAILABLE or easyocr is None:
        return None
    try:
        print(
            f"{Fore.CYAN}Initializing EasyOCR ({'GPU' if False else 'CPU'})...{Style.RESET_ALL}"
        )
        return easyocr.Reader(["en"], gpu=False)
    except Exception as err:
        print(f"{Fore.YELLOW}EasyOCR init failed: {err}{Style.RESET_ALL}")
        return None


def ensure_pytesseract_ready() -> bool:
    """Make sure pytesseract can find the native tesseract binary."""
    global PYTESSERACT_READY
    if not PYTESSERACT_AVAILABLE or pytesseract is None:
        return False
    if PYTESSERACT_READY:
        return True

    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
    ]

    current_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "")
    if current_cmd and os.path.exists(current_cmd):
        PYTESSERACT_READY = True
        return True

    for candidate in candidate_paths:
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            PYTESSERACT_READY = True
            print(f"{Fore.GREEN}Using Tesseract at: {candidate}{Style.RESET_ALL}")
            return True

    print(
        f"{Fore.YELLOW}Tesseract executable not found. Install from https://github.com/UB-Mannheim/tesseract/wiki or set pytesseract.pytesseract.tesseract_cmd manually.{Style.RESET_ALL}"
    )
    return False


def step_ocr_streamed(local_images: List[Dict], reader: Any | None, ocr_workers: int) -> Dict:
    ocr_queue: Queue[Optional[str]] = Queue()
    ocr_results: List[Dict[str, Any]] = []
    summary = {
        "images_processed": 0,
        "total_chars": 0,
        "total_lines": 0,
        "image_results": ocr_results,
    }
    result_lock = threading.Lock()

    def ocr_worker() -> None:
        if not reader and PYTESSERACT_AVAILABLE:
            ensure_pytesseract_ready()

        while True:
            image_path = ocr_queue.get()
            if image_path is None:
                ocr_queue.task_done()
                break

            filename = os.path.basename(image_path)
            if should_skip_image(filename):
                ocr_queue.task_done()
                continue

            if reader:
                with OCR_LOCK:
                    extraction = extract_text_from_image_easyocr(image_path, reader)
            elif PYTESSERACT_AVAILABLE:
                with OCR_LOCK:
                    extraction = extract_text_from_image_pytesseract(image_path)
            else:
                extraction = {"success": False, "error": "No OCR backend available."}

            with result_lock:
                if extraction.get("success"):
                    summary["total_chars"] += extraction.get("char_count", 0)
                    summary["total_lines"] += extraction.get("line_count", 0)
                summary["images_processed"] += 1
                ocr_results.append(
                    {
                        "filename": filename,
                        "file_path": image_path,
                        "extraction": extraction,
                    }
                )

            ocr_queue.task_done()

    with ThreadPoolExecutor(max_workers=ocr_workers) as executor:
        for _ in range(ocr_workers):
            executor.submit(ocr_worker)
        for img in local_images:
            path = img.get("local_path")
            if path and os.path.exists(path):
                ocr_queue.put(path)
        for _ in range(ocr_workers):
            ocr_queue.put(None)
        ocr_queue.join()

    print(
        f"  {Fore.GREEN}OCR summary: {summary['images_processed']} images, "
        f"{summary['total_lines']} lines, {summary['total_chars']} chars{Style.RESET_ALL}"
    )
    return summary


def process_post(post: RedditPost, reader: Any | None, ocr_workers: int) -> Dict[str, Any]:
    post_id = str(post.get("id") or post.get("name") or "unknown_post")
    title = post.get("title", "")
    print(f"\n{Fore.MAGENTA}===== Processing post {post_id}: {title[:60]} ====={Style.RESET_ALL}")

    existing = get_existing_result(post_id)
    if existing:
        print(f"{Fore.YELLOW}Result already exists for {post_id}, skipping.{Style.RESET_ALL}")
        return existing

    result: Dict[str, Any] = {
        "post_id": post_id,
        "title": title,
        "status": "started",
    }

    link = step_identify_correct_link(post)
    if not link:
        result["status"] = "no_link"
        persist_result(result)
        return result

    result["correct_link"] = link
    image_result = step_download_images(post_id, link)
    result["images"] = image_result

    if not image_result["local_images"]:
        result["status"] = "no_images"
        persist_result(result)
        return result

    ocr_result = step_ocr_streamed(image_result["local_images"], reader, ocr_workers)
    result["ocr"] = ocr_result
    result["status"] = "success"

    persist_result(result)
    return result


def process_batch_concurrently(
    posts: List[RedditPost], reader: Any | None, worker_count: int, ocr_workers: int
) -> None:
    if not posts:
        return
    worker_count = max(1, min(worker_count, len(posts)))
    print(
        f"{Fore.CYAN}Processing batch of {len(posts)} posts using {worker_count} workers...{Style.RESET_ALL}"
    )

    failures = 0
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_post = {
            executor.submit(process_post, post, reader, ocr_workers): post for post in posts
        }
        for future in as_completed(future_to_post):
            post = future_to_post[future]
            try:
                future.result()
            except Exception as err:
                failures += 1
                pid = post.get("id") or post.get("name") or "unknown"
                print(
                    f"{Fore.RED}[batch] Post {pid} failed with: {err}{Style.RESET_ALL}"
                )

    if failures:
        print(
            f"{Fore.YELLOW}Batch completed with {failures}/{len(posts)} posts failing.{Style.RESET_ALL}"
        )
    else:
        print(
            f"{Fore.GREEN}Batch completed: all {len(posts)} posts processed successfully.{Style.RESET_ALL}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run full Reddit -> link -> images -> OCR pipeline."
    )
    parser.add_argument("--subreddit", default=DEFAULT_SUBREDDIT)
    parser.add_argument("--sort", default=SORT_FILTER)
    parser.add_argument(
        "--max-posts",
        type=int,
        default=MAX_POSTS if MAX_POSTS is not None else 0,
        help="Cap number of posts to process (0=unlimited).",
    )
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        default=FETCH_ALL,
        help="Keep paging until Reddit stops returning listings.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=20,
        help="Number of concurrent worker threads per batch.",
    )
    parser.add_argument(
        "--ocr-workers",
        type=int,
        default=45,
        help="Number of parallel OCR worker threads per post.",
    )
    parser.add_argument(
        "--resume-after",
        type=str,
        default=None,
        help="Reddit fullname (or post id) to resume after; takes precedence over stored cursor.",
    )
    parser.add_argument(
        "--search-queries",
        "-Q",
        nargs="?",
        const=",".join(DEFAULT_QUERY_SEQUENCE),
        help=(
            "Enable search-based pagination using comma-separated q values "
            "(defaults to the alphabet)."
        ),
    )
    parser.add_argument(
        "--search-limit",
        type=int,
        default=None,
        help="Override per-search request limit (defaults to the API max for authenticated/anon).",
    )
    parser.add_argument("--search-cid", help="Optional cId to send to search requests.")
    parser.add_argument("--search-iid", help="Optional iId to send to search requests.")
    parser.add_argument(
        "--search-include-over-18",
        action="store_true",
        help="Add include_over_18=on when using the search endpoint (required for NSFW subs).",
    )
    parser.add_argument(
        "--link-chunks",
        "-L",
        nargs="+",
        type=Path,
        help="Process pre-collected link chunk files instead of scraping the listing.",
    )
    parser.add_argument(
        "--search-safe",
        choices=["true", "false"],
        help="Set the safe parameter (true/false) when using search mode.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    max_posts = args.max_posts if args.max_posts > 0 else None

    reader = init_ocr_reader()
    processed = 0

    workers = max(1, args.workers)
    ocr_workers = max(1, args.ocr_workers)
    chunk_paths = [path for path in (args.link_chunks or []) if path]
    search_queries = None
    if args.search_queries:
        search_queries = [q.strip() for q in args.search_queries.split(",") if q.strip()]

    if chunk_paths:
        run_chunk_mode(
            chunk_paths=chunk_paths,
            subreddit=args.subreddit,
            reader=reader,
            workers=workers,
            ocr_workers=ocr_workers,
            max_posts=max_posts,
        )
        return

    init_aggregate_storage()

    stream_args = (
            stream_search_query_batches(
                subreddit=args.subreddit,
                sort_filter=args.sort,
                queries=search_queries,
                max_posts=max_posts,
                page_limit=args.search_limit,
                cid=args.search_cid,
                iid=args.search_iid,
                include_over_18=args.search_include_over_18,
                safe=args.search_safe,
            )
            if search_queries
            else stream_full_post_batches(
                subreddit=args.subreddit,
                sort_filter=args.sort,
                fetch_all=args.fetch_all,
                max_posts=max_posts,
                resume_after=args.resume_after or None,
            )
        )

    for batch in stream_args:
        process_batch_concurrently(batch, reader, workers, ocr_workers)
        processed += len(batch)
        if max_posts and processed >= max_posts:
            break

    print(
        f"\n{Fore.CYAN}Pipeline complete. Processed {processed} posts from {args.subreddit}.{Style.RESET_ALL}"
    )


if __name__ == "__main__":
    main()

