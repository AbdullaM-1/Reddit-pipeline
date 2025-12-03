#!/usr/bin/env python
"""
Script to split each post from a JSON file into individual files.
Structured for Amazon Bedrock knowledge base ingestion with:
- content field: OCR text (gets chunked and embedded)
- metadata fields: post_id, title, correct_link (associated with each chunk)
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any
import re
from datetime import datetime


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove or replace invalid characters for Windows filesystem
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    # Limit length to avoid filesystem issues
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized


def split_posts_into_files(
    input_file: str,
    output_dir: str | None = None
):
    """
    Split each post from JSON file into individual files optimized for Amazon Bedrock knowledge base.
    
    For each post, creates ONE file: {post_id}.json
    Contains nested metadata and content:
    {
        "metadata": {
            "post_id": "...",
            "title": "...",
            "correct_link": "...",
            "status": "...",
            // ... all other metadata fields
        },
        "content": "OCR text here..."  // Gets chunked and embedded
    }
    
    Args:
        input_file: Path to the input JSON file
        output_dir: Directory to save individual post files (default: input_dir/posts)
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"Loading {input_file}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    posts = data.get('posts', [])
    original_metadata = data.get('metadata', {})
    
    total_posts = len(posts)
    print(f"Total posts: {total_posts}")
    
    if total_posts == 0:
        print("No posts to split!")
        return
    
    # Determine output directory
    if output_dir is None:
        # Create a new folder with timestamp to avoid overwriting existing files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir_path = input_path.parent / f"posts_{timestamp}"
    else:
        output_dir_path = Path(output_dir)
    
    # Create output directory
    output_dir_path.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir_path}\n")
    
    # Process each post
    saved_count = 0
    skipped_count = 0
    
    for i, post in enumerate(posts, 1):
        post_id = post.get('post_id', f'post_{i}')
        title = post.get('title', 'Untitled')
        correct_link = post.get('correct_link', '')
        ocr_text = post.get('ocr_text', '')
        
        # Create filename: post_id,title,correct_link.json
        # Sanitize title and correct_link for filesystem safety
        sanitized_title = sanitize_filename(title)
        # For correct_link, remove protocol and sanitize
        sanitized_link = correct_link
        if sanitized_link:
            # Remove http:// or https://
            sanitized_link = sanitized_link.replace('https://', '').replace('http://', '')
            # Replace remaining problematic characters
            sanitized_link = sanitize_filename(sanitized_link)
        
        # Build filename: post_id,title,correct_link.json
        filename_parts = [post_id, sanitized_title, sanitized_link]
        filename = f"{','.join(filename_parts)}.json"
        
        output_file = output_dir_path / filename
        
        # Skip if file already exists (to avoid overwriting)
        if output_file.exists():
            print(f"[{i}/{total_posts}] Skipping {filename} (already exists)")
            skipped_count += 1
            continue
        
        # Create single file with content (OCR text) and nested metadata
        # Structure: metadata object + content field
        metadata_fields = {k: v for k, v in post.items() if k != 'ocr_text'}
        
        file_data = {
            "metadata": metadata_fields,  # All fields except ocr_text nested in metadata
            "content": ocr_text  # Content field for chunking and embedding
        }
        
        # Save post to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(file_data, f, indent=2, ensure_ascii=False)
            
            saved_count += 1
            if saved_count % 100 == 0:
                print(f"[{i}/{total_posts}] Saved {saved_count} posts...")
        except Exception as e:
            print(f"[{i}/{total_posts}] Error saving {filename}: {e}")
            skipped_count += 1
    
    print(f"\n✓ Successfully saved {saved_count} posts")
    if skipped_count > 0:
        print(f"⚠ Skipped {skipped_count} posts (already exist or errors)")
    print(f"✓ Output directory: {output_dir_path}")
    print(f"✓ Each post has 1 file: {{post_id}}.json (contains content + metadata)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split each post from a JSON file into individual files"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="pipeline_results/pipeline_results_merged.cleaned.flat.with_ocr.json",
        help="Input JSON file to split"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for individual post files (default: input_dir/posts)"
    )
    
    args = parser.parse_args()
    
    split_posts_into_files(
        input_file=args.input,
        output_dir=args.output_dir
    )

