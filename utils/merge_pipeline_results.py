#!/usr/bin/env python
"""
Utilities for merging multiple pipeline result files without duplicate post IDs.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

DEFAULT_REQUIRED_CHUNKS = [
    "chunk-01.json",
    "chunk-02.json",
    "chunk-03.json",
    "chunk-04.json",
]


def parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Support both "Z" and offset formats
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def collect_files(
    base_file: Path,
    chunk_patterns: Iterable[str],
    extra_globs: Iterable[str],
) -> List[Path]:
    files: List[Path] = []

    if base_file.exists():
        files.append(base_file)
    else:
        raise FileNotFoundError(f"Base file '{base_file}' not found.")

    for pattern in chunk_patterns:
        files.extend(sorted(base_file.parent.glob(pattern)))

    for pattern in extra_globs:
        path = Path(pattern)
        if any(ch in pattern for ch in "*?[]"):
            files.extend(sorted(path.parent.glob(path.name)))
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(f"Extra glob or file '{pattern}' does not match anything.")

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for file_path in files:
        if file_path not in seen:
            unique_files.append(file_path)
            seen.add(file_path)

    return unique_files


def ensure_required_inputs(required_paths: Iterable[Path]) -> None:
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Required input files missing: "
            + ", ".join(str(path) for path in missing)
        )


def merge_pipeline_results(file_paths: Iterable[Path]) -> Tuple[dict, List[Tuple[str, str, str]]]:
    posts: dict[str, dict] = {}
    post_sources: dict[str, Path] = {}
    duplicate_records: List[Tuple[str, str, str]] = []
    last_updated: datetime | None = None

    for path in file_paths:
        print(f"Loading {path}...")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        metadata = data.get("metadata", {})
        last_updated_candidate = parse_iso_timestamp(metadata.get("last_updated"))
        if last_updated_candidate and (last_updated is None or last_updated_candidate > last_updated):
            last_updated = last_updated_candidate

        for post_id, post in data.get("posts", {}).items():
            if post_id in posts:
                duplicate_records.append(
                    (post_id, post_sources[post_id].name, path.name)
                )
            posts[post_id] = post
            post_sources[post_id] = path

    merged_data = {
        "metadata": {
            "total_posts": len(posts),
            "last_updated": (
                last_updated.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if last_updated
                else None
            ),
        },
        "posts": posts,
    }

    return merged_data, duplicate_records


def write_output(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Written merged output to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge pipeline result JSON files and remove duplicate posts."
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("pipeline_results/pipeline_results.json"),
        help="Path to the primary pipeline results file.",
    )
    parser.add_argument(
        "--chunk-patterns",
        nargs="*",
        default=["chunk-*.json"],
        help="Glob patterns (relative to base parent) to locate chunk files.",
    )
    parser.add_argument(
        "--extra",
        nargs="*",
        default=[],
        help="Additional files or glob patterns to include.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("pipeline_results/pipeline_results_merged.json"),
        help="Output file that will contain the merged results.",
    )

    args = parser.parse_args()
    required_inputs = {
        args.base,
        *(
            args.base.parent / chunk_name
            for chunk_name in DEFAULT_REQUIRED_CHUNKS
        ),
    }
    ensure_required_inputs(required_inputs)
    file_paths = collect_files(args.base, args.chunk_patterns, args.extra)

    print(f"Files to merge ({len(file_paths)}): {[path.name for path in file_paths]}")
    merged_data, duplicates = merge_pipeline_results(file_paths)

    merged_data["metadata"].update(
        {
            "merged_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sources": [path.name for path in file_paths],
            "duplicates_removed": len(duplicates),
        }
    )

    write_output(merged_data, args.output)

    print(f"Total unique posts in merged file: {len(merged_data['posts'])}")

    if duplicates:
        print(f"Duplicates detected: {len(duplicates)} (samples below)")
        for post_id, original, current in duplicates[:10]:
            print(f"  {post_id}: {original} → {current}")
        if len(duplicates) > 10:
            print(f"  ...and {len(duplicates) - 10} more duplicates")
    else:
        print("No duplicate post IDs were found.")


if __name__ == "__main__":
    main()

