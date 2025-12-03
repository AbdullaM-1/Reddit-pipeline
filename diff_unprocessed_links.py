#!/usr/bin/env python3
"""
Compare the Playwright-collected URLs (`scroller_post_ids.json`) with the pipeline
results to generate a deduplicated list of links that still need processing.

Usage:
  python diff_unprocessed_links.py \
    --scroller scroller_post_ids.json \
    --pipeline pipeline_results/pipeline_results.json \
    --output unprocessed_links.json

The script writes every `https://.../comments/<id>/...` URL whose `t3_` ID
is not present in the pipeline output. If the pipeline file is large, this
still works because we only read the `posts` map keys.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

POST_ID_REGEX = re.compile(r"/comments/([a-z0-9]{6,})", re.IGNORECASE)


def parse_link_to_fullname(link: str) -> str | None:
    if not link:
        return None
    match = POST_ID_REGEX.search(link)
    if match:
        return f"t3_{match.group(1)}"
    return None


def load_scroller_links(path: Path) -> Iterable[str]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [link for link in data.get("post_ids") or [] if isinstance(link, str)]


def load_processed_post_ids(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    posts = data.get("posts", {})
    processed = set()
    for payload in posts.values():
        post_id = payload.get("post_id")
        if isinstance(post_id, str):
            processed.add(post_id)
    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Identify scroller links not yet processed.")
    parser.add_argument("--scroller", type=Path, default=Path("scroller_post_ids.json"))
    parser.add_argument(
        "--pipeline",
        type=Path,
        default=Path("pipeline_results/pipeline_results.json"),
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("unprocessed_links.json"),
    )
    args = parser.parse_args()

    scroller_links = list(load_scroller_links(args.scroller))
    processed_ids = load_processed_post_ids(args.pipeline)

    new_links = []
    seen_ids = set()
    for link in scroller_links:
        fullname = parse_link_to_fullname(link)
        if fullname:
            if fullname in processed_ids or fullname in seen_ids:
                continue
            seen_ids.add(fullname)
        new_links.append(link)

    args.output.write_text(
        json.dumps({"unprocessed_links": new_links}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(new_links)} unprocessed links to {args.output}")


if __name__ == "__main__":
    main()

