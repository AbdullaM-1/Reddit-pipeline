#!/usr/bin/env python
"""
Script to fetch posts from a subreddit with their full contents (media, comments, awards, etc.).
Supports grabbing a fixed number of posts or crawling the ENTIRE subreddit history via pagination.

Configuration lives near the top of this file:
    SUBREDDIT        - target subreddit (without the leading r/ is fine)
    POST_LIMIT       - number of posts to fetch when FETCH_ALL_POSTS is False
    SORT_FILTER      - listing to use (hot/new/top/rising/controversial)
    FETCH_ALL_POSTS  - set to True to walk through every available post (may take hours/days)

Important: Reddit's official listing endpoints only expose ~1000 items per sort filter.
To scrape beyond that limit (e.g., hundreds of thousands of historical posts), you must
combine multiple time windows or rely on a third-party archive such as Pushshift.
"""

import json
import sys
import time
from posts import (
    fetchPostsBySubreddt,
    buildPosts,
    fetchPostArticleByPostID,
    buildMedia,
    buildComments,
    fetchAwards,
    getToken,
    getHeaders,
    getUserAgent,
    getSession,
    unix_epoch_to_human_readable,
)
from colorama import Fore, Style
from dotenv import dotenv_values
from collections import defaultdict

# ============================================
# CONFIGURATION - Modify these values
# ============================================
SUBREDDIT = "SextStories"   # Change this to your desired subreddit (e.g., "python", "funny")
POST_LIMIT = 1000           # Number of posts to fetch when FETCH_ALL_POSTS=False
SORT_FILTER = "new"         # Options: "hot", "new", "top", "rising", "controversial"
FETCH_ALL_POSTS = True      # Set to True to paginate through every available post (can be hundreds of thousands)
MAX_POSTS_PER_REQUEST = 100 # Reddit API allows up to 100 items per request when authenticated
# ============================================

# Load environment variables
config = dotenv_values(".env")
username = config.get("username", "")
password = config.get("password", "")
client_id = config.get("client_id", "")
client_secret = config.get("client_secret", "")


def fetchSubredditPostsWithContents(
    subreddit: str,
    limit: int = 50,
    sort_filter: str = "hot",
    fetch_all: bool = False,
) -> list:
    """
    Fetch posts from a subreddit with their full contents (comments, media, etc.)
    
    Args:
        subreddit: Subreddit name (e.g., "python" or "r/python")
        limit: Number of posts to fetch (default: 50)
        sort_filter: Sort filter ("hot", "new", "top", "rising", "controversial")
        fetch_all: When True, ignore limit and exhaust the entire listing via pagination
    
    Returns:
        List of Post objects with full details
    """
    # Get token (optional)
    params = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    acc_token = getToken(params, 10)
    
    if not acc_token:
        print(f"{Fore.YELLOW}Running without authentication. Rate limits may apply.{Style.RESET_ALL}")
        acc_token = ""
    
    # Normalize subreddit name
    if not subreddit.startswith("r/"):
        subreddit = f"r/{subreddit}"
    
    target_description = "ALL available posts" if fetch_all else f"{limit} posts"
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Fetching {target_description} from {subreddit} (sorted by: {sort_filter}){Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    if fetch_all:
        print(f"{Fore.YELLOW}Full-history mode enabled. This may take a very long time and produce very large files.{Style.RESET_ALL}\n")
    
    # Reddit API returns max 100 posts per request
    posts_per_request = min(MAX_POSTS_PER_REQUEST, 100)
    all_posts = []
    after = None
    request_num = 0
    
    if fetch_all:
        total_target = float("inf")
    else:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer when fetch_all=False")
        total_target = limit
        posts_per_request = min(posts_per_request, total_target)
    
    # Get awards (needed for building posts)
    print(f"{Fore.CYAN}Loading awards...{Style.RESET_ALL}")
    awards = fetchAwards()
    
    session = getSession()
    
    while True:
        if not fetch_all and len(all_posts) >= total_target:
            break
        
        request_num += 1
        if fetch_all:
            current_limit = posts_per_request
        else:
            remaining = total_target - len(all_posts)
            current_limit = min(posts_per_request, remaining)
            if current_limit <= 0:
                break
        
        batch_label = f"batch {request_num}" if fetch_all else f"batch {request_num}/{(total_target + posts_per_request - 1) // posts_per_request}"
        print(f"{Fore.CYAN}Fetching {batch_label} ({current_limit} posts)...{Style.RESET_ALL}")
        
        # Fetch posts with pagination using direct API call to support 'after' parameter
        try:
            params = {"limit": current_limit, "show": "all", "sr_detail": True}
            if after:
                params["after"] = after
            
            if acc_token:
                response = session.get(
                    f"https://oauth.reddit.com/{subreddit}/{sort_filter}.json",
                    headers=getHeaders(getUserAgent(), acc_token),
                    params=params,
                )
            else:
                response = session.get(
                    f"https://www.reddit.com/{subreddit}/{sort_filter}.json",
                    headers=getHeaders(getUserAgent(), acc_token),
                    params=params,
                )
            response.raise_for_status()
            raw_json = response.json()
            
            print(f"{Fore.GREEN}Success got posts Status Code:{response.status_code}{Style.RESET_ALL}")
        except Exception as err:
            print(f"{Fore.RED}Failed to fetch posts: {err}{Style.RESET_ALL}")
            break
        
        if not raw_json or not raw_json.get("data"):
            print(f"{Fore.YELLOW}No posts data received{Style.RESET_ALL}")
            break
        
        # Build basic post objects
        batch_posts = buildPosts(raw_json, awards)
        print(f"{Fore.GREEN}Retrieved {len(batch_posts)} posts in this batch{Style.RESET_ALL}")
        
        # Get 'after' token for next page
        after = raw_json.get("data", {}).get("after")
        
        # Fetch full details for each post (comments, media, etc.)
        print(f"{Fore.CYAN}Fetching full details for posts...{Style.RESET_ALL}")
        for i, post in enumerate(batch_posts, 1):
            post_id = post.get("id", "")
            post_title = post.get("title", "")[:50]  # Truncate for display
            print(f"  [{i}/{len(batch_posts)}] Fetching details for: {post_title}...")
            
            # Fetch full post article with comments
            raw_json_post = fetchPostArticleByPostID(
                post.get("subreddit", subreddit),
                post_id,
                acc_token
            )
            
            post_payload = raw_json_post.get("post") or []
            if isinstance(post_payload, list) and post_payload:
                # Media Content
                first_entry = post_payload[0] if len(post_payload) > 0 else None
                if first_entry:
                    post_detail_media = first_entry.get("data", {}).get("children", [])
                    if post_detail_media:
                        post_detail_media_data = post_detail_media[0].get("data", {})
                        post["media_content"] = buildMedia(post_detail_media_data)
                
                # Comments
                if len(post_payload) > 1:
                    post_detail_comment = post_payload[1].get("data", {}).get("children", [])
                    subreddit_users: dict[str, set[str]] = defaultdict(set[str])
                    subreddit_id = post.get("subreddit_id", "")
                    subreddit_name = post.get("subreddit", subreddit)
                    
                    comments, num_comments = buildComments(
                        post_detail_comment,
                        subreddit_users,
                        subreddit_id,
                        subreddit_name,
                    )
                    post["comments"] = comments
                    post["num_comments"] = num_comments
        
        all_posts.extend(batch_posts)
        
        # Stop if we've reached requested amount
        if not fetch_all and len(all_posts) >= total_target:
            break
        
        if not after:
            print(f"{Fore.YELLOW}No more posts available{Style.RESET_ALL}")
            break
        
        # Friendly pacing to reduce rate-limit risk
        time.sleep(1)
    
    if not fetch_all and limit:
        all_posts = all_posts[:limit]
    
    print(f"\n{Fore.GREEN}Successfully fetched {len(all_posts)} posts with full contents{Style.RESET_ALL}")
    return all_posts


if __name__ == "__main__":
    posts = fetchSubredditPostsWithContents(
        SUBREDDIT,
        POST_LIMIT,
        SORT_FILTER,
        fetch_all=FETCH_ALL_POSTS,
    )
    
    if posts:
        print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Summary:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        print(f"Total posts fetched: {len(posts)}")
        print(f"Subreddit: {SUBREDDIT}")
        print(f"Sort filter: {SORT_FILTER}")
        
        # Display first few posts
        print(f"\n{Fore.CYAN}First 5 posts:{Style.RESET_ALL}")
        for i, post in enumerate(posts[:5], 1):
            print(f"\n{i}. {Fore.YELLOW}{post.get('title', 'N/A')[:60]}...{Style.RESET_ALL}")
            print(f"   Author: u/{post.get('author', 'N/A')} | Upvotes: {post.get('ups', 0)} | Comments: {post.get('num_comments', 0)}")
            if post.get('text'):
                text_preview = post.get('text', '')[:100].replace('\n', ' ')
                print(f"   Text: {text_preview}...")
        
        # Save to JSON file
        output_file = f"subreddit_{SUBREDDIT.replace('r/', '')}_{SORT_FILTER}_posts.json"
        with open(output_file, "w", encoding="utf-8") as fp:
            json.dump(posts, fp, indent=2, ensure_ascii=False)
        print(f"\n{Fore.GREEN}All posts saved to: {output_file}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}File contains {len(posts)} posts with full details (comments, media, etc.){Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}Failed to fetch posts. Please check the subreddit name.{Style.RESET_ALL}")

