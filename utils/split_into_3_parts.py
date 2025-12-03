#!/usr/bin/env python
"""
Script to split a JSON file into 3 equal parts.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
import math


def split_into_3_parts(
    input_file: str,
    output_dir: str | None = None,
    output_prefix: str | None = None
):
    """
    Split a JSON file with posts array into 3 equal parts.
    
    Args:
        input_file: Path to the input JSON file
        output_dir: Directory to save split files (default: same as input)
        output_prefix: Prefix for output files (default: input filename without extension)
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"Loading {input_file}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    posts = data.get('posts', [])
    metadata = data.get('metadata', {})
    
    total_posts = len(posts)
    print(f"Total posts: {total_posts}")
    
    if total_posts == 0:
        print("No posts to split!")
        return
    
    # Calculate split sizes
    part_size = math.ceil(total_posts / 3)
    print(f"Posts per part: ~{part_size}")
    print(f"Splitting into 3 parts...\n")
    
    # Determine output directory and prefix
    if output_dir is None:
        output_dir_path = input_path.parent
    else:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
    
    if output_prefix is None:
        output_prefix_str = input_path.stem
    else:
        output_prefix_str = output_prefix
    
    # Split into 3 parts
    parts = [
        posts[0:part_size],
        posts[part_size:2*part_size],
        posts[2*part_size:]
    ]
    
    for i, part_posts in enumerate(parts, 1):
        if not part_posts:  # Skip empty parts
            continue
            
        # Create part data with updated metadata
        part_data = {
            "metadata": {
                **metadata,
                "part_number": i,
                "total_parts": 3,
                "posts_in_part": len(part_posts),
                "total_posts_original": total_posts,
                "source_file": input_path.name
            },
            "posts": part_posts
        }
        
        # Save part
        output_file = output_dir_path / f"{output_prefix_str}_part{i}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(part_data, f, indent=2, ensure_ascii=False)
        
        print(f"Created {output_file.name} ({len(part_posts)} posts)")
    
    print(f"\n✓ Successfully split into 3 parts")
    print(f"✓ Output directory: {output_dir_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split a JSON file into 3 equal parts"
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
        help="Output directory (default: same as input file directory)"
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=None,
        help="Prefix for output files (default: input filename without extension)"
    )
    
    args = parser.parse_args()
    
    split_into_3_parts(
        input_file=args.input,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix
    )

