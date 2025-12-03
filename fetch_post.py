#!/usr/bin/env python
"""
Simple script to fetch a specific Reddit post by subreddit and post ID.
Modify the SUBREDDIT and POST_ID variables below to fetch different posts.
"""

import json
import re
from posts import fetchSpecificPost
from colorama import Fore, Style

# ============================================
# CONFIGURATION - Modify these values
# ============================================
# Example: For a post URL like: https://www.reddit.com/r/python/comments/abc123/title/
# SUBREDDIT would be "python" or "r/python"
# POST_ID would be "abc123" (the alphanumeric ID from the URL)
SUBREDDIT = "SextStories"  # Change this to your desired subreddit
POST_ID = "1p2pj2j"        # Change this to your desired post ID (e.g., "1abc123")
# ============================================

if __name__ == "__main__":
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Reddit Post Fetcher{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    if not POST_ID:
        print(f"{Fore.RED}Error: Please set POST_ID in the script.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Example: POST_ID = '1abc123'{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}You can find the post ID in the Reddit URL.{Style.RESET_ALL}")
        exit(1)
    
    post = fetchSpecificPost(SUBREDDIT, POST_ID)
    
    if post:
        print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Post Details:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
        
        # Display post information
        print(f"{Fore.YELLOW}Title:{Style.RESET_ALL} {post.get('title', 'N/A')}")
        print(f"{Fore.YELLOW}Subreddit:{Style.RESET_ALL} {post.get('subreddit', 'N/A')}")
        print(f"{Fore.YELLOW}Author:{Style.RESET_ALL} u/{post.get('author', 'N/A')}")
        print(f"{Fore.YELLOW}Upvotes:{Style.RESET_ALL} {post.get('ups', '0')}")
        print(f"{Fore.YELLOW}Comments:{Style.RESET_ALL} {post.get('num_comments', 0)}")
        print(f"{Fore.YELLOW}Created:{Style.RESET_ALL} {post.get('created_human', 'N/A')}")
        print(f"{Fore.YELLOW}NSFW:{Style.RESET_ALL} {post.get('over_18', False)}")
        print(f"{Fore.YELLOW}Spoiler:{Style.RESET_ALL} {post.get('spoiler', False)}")
        
        if post.get('text'):
            print(f"\n{Fore.YELLOW}Post Text:{Style.RESET_ALL}")
            print(f"{post.get('text', '')[:500]}..." if len(post.get('text', '')) > 500 else post.get('text', ''))
        
        if post.get('link_flair_text'):
            print(f"\n{Fore.YELLOW}Flair:{Style.RESET_ALL} {post.get('link_flair_text')}")
        
        if post.get('media_content'):
            media = post.get('media_content', {})
            if isinstance(media, dict):
                media_type = media.get('_type', 'unknown')
                print(f"\n{Fore.YELLOW}Media Type:{Style.RESET_ALL} {media_type}")
        
        # Save to JSON file
        output_file = f"post_{POST_ID}.json"
        with open(output_file, "w", encoding="utf-8") as fp:
            json.dump(post, fp, indent=2, ensure_ascii=False)
        print(f"\n{Fore.GREEN}Post data saved to: {output_file}{Style.RESET_ALL}")
        
        # Show comments with text
        comments = post.get('comments', [])
        if comments:
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Comments ({len(comments)} top-level):{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
            
            def display_comment(comment, depth=0):
                """Recursively display comment and its replies"""
                indent = "  " * depth
                author = comment.get('author', 'N/A')
                body = comment.get('body', '')
                ups = comment.get('ups', 0)
                score = comment.get('score', 0)
                
                prefix = "-> " if depth > 0 else ""
                print(f"{indent}{Fore.YELLOW}{prefix}u/{author}{Style.RESET_ALL} ({ups} upvotes)")
                if body:
                    # Clean up markdown links for display
                    # Remove markdown links but keep the URL text
                    body_display = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', body)
                    # Show full text (or truncate if very long)
                    if len(body_display) > 1000:
                        body_display = body_display[:1000] + "\n... (truncated)"
                    # Split into lines for better readability
                    lines = body_display.split('\n')
                    for line in lines:
                        if line.strip():
                            print(f"{indent}  {Fore.WHITE}{line.strip()}{Style.RESET_ALL}")
                        else:
                            print()  # Empty line
                else:
                    print(f"{indent}  {Fore.GRAY}(No text content){Style.RESET_ALL}")
                
                # Display replies
                replies = comment.get('replies', [])
                if replies:
                    for reply in replies:
                        display_comment(reply, depth + 1)
            
            for i, comment in enumerate(comments, 1):
                print(f"\n{Fore.CYAN}Comment #{i}:{Style.RESET_ALL}")
                display_comment(comment)
        else:
            print(f"\n{Fore.CYAN}No comments found.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}Failed to fetch post. Please check the subreddit name and post ID.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Tip: The post ID is the alphanumeric string in the Reddit URL.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Example: https://www.reddit.com/r/python/comments/abc123/title/{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}The post ID would be: abc123{Style.RESET_ALL}")

