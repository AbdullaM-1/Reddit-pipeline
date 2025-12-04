#!/usr/bin/env python
"""
Upload pipeline results from JSON file to Supabase database.

This script reads posts from the pipeline_results JSON file and uploads them
to the Supabase posts table.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dotenv import dotenv_values
from colorama import Fore, Style, init

# Initialize colorama for Windows
init()

try:
    from supabase_client import (
        get_supabase_client,
        upsert_post,
        post_exists,
        hash_post_id
    )
except ImportError as e:
    print(f"{Fore.RED}Error importing supabase_client: {e}{Style.RESET_ALL}")
    sys.exit(1)


def load_config():
    """Load configuration from .env file."""
    config = dotenv_values(".env")
    
    # Check for NEXT_PUBLIC_SUPABASE_URL or SUPABASE_URL
    supabase_url = config.get("NEXT_PUBLIC_SUPABASE_URL") or config.get("SUPABASE_URL")
    supabase_key = (
        config.get("SUPABASE_SERVICE_ROLE_KEY") or 
        config.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or 
        config.get("SUPABASE_ANON_KEY")
    )
    
    if not supabase_url:
        print(f"{Fore.RED}Error: NEXT_PUBLIC_SUPABASE_URL or SUPABASE_URL not found in .env{Style.RESET_ALL}")
        sys.exit(1)
    
    if not supabase_key:
        print(f"{Fore.RED}Error: Supabase key not found in .env{Style.RESET_ALL}")
        sys.exit(1)
    
    return supabase_url, supabase_key


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse JSON file."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"{Fore.RED}Error: File not found: {file_path}{Style.RESET_ALL}")
        sys.exit(1)
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"{Fore.GREEN}Successfully loaded JSON file: {file_path}{Style.RESET_ALL}")
        return data
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}Error: Invalid JSON file: {e}{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error reading file: {e}{Style.RESET_ALL}")
        sys.exit(1)


def extract_post_date(post_data: Dict[str, Any]) -> datetime:
    """
    Extract post date from various possible fields in the JSON.
    
    Tries to find the date in:
    1. created_utc (Unix timestamp)
    2. post_date_utc (Unix timestamp)
    3. created_at (ISO string)
    4. post_date (ISO string or timestamp)
    5. Falls back to current time if not found
    """
    # Try Unix timestamp fields
    timestamp_fields = ['created_utc', 'post_date_utc', 'created_at_utc', 'date_utc']
    for field in timestamp_fields:
        if field in post_data:
            value = post_data[field]
            if value:
                try:
                    if isinstance(value, (int, float)):
                        return datetime.fromtimestamp(value)
                    elif isinstance(value, str) and value.isdigit():
                        return datetime.fromtimestamp(int(value))
                except (ValueError, OSError):
                    continue
    
    # Try ISO string fields
    iso_fields = ['created_at', 'post_date', 'date', 'timestamp']
    for field in iso_fields:
        if field in post_data:
            value = post_data[field]
            if value:
                try:
                    if isinstance(value, str):
                        # Try parsing ISO format
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    continue
    
    # Try to extract from nested metadata
    metadata = post_data.get('metadata', {})
    if isinstance(metadata, dict):
        for field in timestamp_fields + iso_fields:
            if field in metadata:
                value = metadata[field]
                if value:
                    try:
                        if isinstance(value, (int, float)):
                            return datetime.fromtimestamp(value)
                        elif isinstance(value, str):
                            if value.isdigit():
                                return datetime.fromtimestamp(int(value))
                            else:
                                return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, OSError, AttributeError):
                        continue
    
    # Fallback to current time
    print(f"{Fore.YELLOW}Warning: Could not extract post date, using current time{Style.RESET_ALL}")
    return datetime.now()


def extract_posts_from_json(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract posts from the JSON structure.
    
    Handles different possible JSON structures:
    1. {"posts": {"post_id": {...}}} - dictionary of posts
    2. {"posts": [{...}]} - array of posts
    3. Direct array of posts
    """
    posts = []
    
    # Case 1: Dictionary structure with posts key
    if 'posts' in data:
        posts_data = data['posts']
        
        # If it's a dictionary (keyed by post_id)
        if isinstance(posts_data, dict):
            for post_id, post_data in posts_data.items():
                post_data['post_id'] = post_id
                posts.append(post_data)
        # If it's an array
        elif isinstance(posts_data, list):
            posts = posts_data
    
    # Case 2: Direct array
    elif isinstance(data, list):
        posts = data
    
    # Case 3: Single post object
    elif isinstance(data, dict) and 'post_id' in data:
        posts = [data]
    
    else:
        print(f"{Fore.YELLOW}Warning: Unexpected JSON structure. Trying to extract posts from top level...{Style.RESET_ALL}")
        # Try to find any object with post_id
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and 'post_id' in value:
                    posts.append(value)
    
    return posts


def upload_post(post_data: Dict[str, Any], client) -> bool:
    """
    Upload a single post to Supabase.
    
    Args:
        post_data: Post data dictionary
        client: Supabase client
    
    Returns:
        True if successful, False otherwise
    """
    # Extract required fields
    post_id = post_data.get('post_id') or str(post_data.get('id', ''))
    
    if not post_id:
        print(f"{Fore.YELLOW}Warning: Skipping post without post_id{Style.RESET_ALL}")
        return False
    
    title = post_data.get('title', '')
    correct_link = post_data.get('correct_link') or post_data.get('link') or post_data.get('url')
    
    # Extract post date
    post_date = extract_post_date(post_data)
    
    # Upload to Supabase
    try:
        result_id = upsert_post(
            post_id=str(post_id),
            title=title,
            correct_link=correct_link,
            post_date=post_date,
            client=client
        )
        
        if result_id:
            print(f"{Fore.GREEN}[OK] Uploaded post {post_id}: {title[:50]}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}[WARN] Failed to upload post {post_id}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error uploading post {post_id}: {e}{Style.RESET_ALL}")
        return False


def main():
    """Main function to upload posts from JSON to Supabase."""
    # Configuration
    input_file = r"C:\Users\AL FATAH LAPTOP\Desktop\pipeline_results\pipeline_results_merged.cleaned.flat.no_ocr.json"
    
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Uploading Pipeline Results to Supabase{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # Load configuration
    supabase_url, supabase_key = load_config()
    print(f"{Fore.CYAN}Supabase URL: {supabase_url}{Style.RESET_ALL}\n")
    
    # Get Supabase client
    client = get_supabase_client()
    if not client:
        print(f"{Fore.RED}Error: Failed to create Supabase client{Style.RESET_ALL}")
        sys.exit(1)
    
    # Load JSON file
    print(f"{Fore.CYAN}Loading JSON file...{Style.RESET_ALL}")
    data = load_json_file(input_file)
    
    # Extract posts from JSON
    print(f"{Fore.CYAN}Extracting posts from JSON...{Style.RESET_ALL}")
    posts = extract_posts_from_json(data)
    
    if not posts:
        print(f"{Fore.YELLOW}Warning: No posts found in JSON file{Style.RESET_ALL}")
        sys.exit(1)
    
    print(f"{Fore.GREEN}Found {len(posts)} posts in JSON file{Style.RESET_ALL}\n")
    
    # Upload posts
    print(f"{Fore.CYAN}Uploading posts to Supabase...{Style.RESET_ALL}\n")
    successful = 0
    failed = 0
    skipped = 0
    
    for i, post_data in enumerate(posts, 1):
        post_id = post_data.get('post_id') or str(post_data.get('id', ''))
        
        if not post_id:
            skipped += 1
            continue
        
        print(f"[{i}/{len(posts)}] Processing post {post_id}...", end=" ")
        
        # Check if post already exists (optional - you can skip this if you want to always update)
        # if post_exists(post_id, client):
        #     print(f"{Fore.YELLOW}Already exists, updating...{Style.RESET_ALL}", end=" ")
        
        if upload_post(post_data, client):
            successful += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Upload Summary{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Successful: {successful}{Style.RESET_ALL}")
    if failed > 0:
        print(f"{Fore.RED}Failed: {failed}{Style.RESET_ALL}")
    if skipped > 0:
        print(f"{Fore.YELLOW}Skipped: {skipped}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Total: {len(posts)}{Style.RESET_ALL}\n")
    
    if successful > 0:
        print(f"{Fore.GREEN}[SUCCESS] Upload completed successfully!{Style.RESET_ALL}")


if __name__ == "__main__":
    main()

