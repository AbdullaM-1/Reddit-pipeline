#!/usr/bin/env python3
"""
Split the existing `unprocessed_links.json` into four chunk files for easier batching.

Usage:
  python split_unprocessed_links.py --input unprocessed_links.json

Each chunk is written to `unprocessed_links_chunks/chunk-{index}.json`.
"""

from __future__ import annotations

import argparse
import json
from math import ceil
from pathlib import Path
from typing import Iterable, List


def load_links(path: Path) -> List[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [link for link in data.get("unprocessed_links", []) if isinstance(link, str)]


def chunk_links(links: Iterable[str], parts: int = 4) -> List[List[str]]:
    links = list(links)
    if not links:
        return [[] for _ in range(parts)]
    chunk_size = ceil(len(links) / parts)
    return [links[i * chunk_size : (i + 1) * chunk_size] for i in range(parts)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Split unprocessed links into multiple chunk files.")
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("unprocessed_links.json"),
        help="Source JSON file with unprocessed_links array.",
    )
    parser.add_argument(
        "--parts",
        "-p",
        type=int,
        default=4,
        help="How many chunks to produce.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("unprocessed_links_chunks"),
        help="Directory where chunk files will be written.",
    )
    args = parser.parse_args()

    links = load_links(args.input)
    chunks = chunk_links(links, args.parts)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for idx, chunk in enumerate(chunks, start=1):
        chunk_path = args.output_dir / f"chunk-{idx:02d}.json"
        chunk_path.write_text(json.dumps({"unprocessed_links": chunk}, indent=2), encoding="utf-8")
        print(f"Wrote {len(chunk)} links to {chunk_path}")


if __name__ == "__main__":
    main()

