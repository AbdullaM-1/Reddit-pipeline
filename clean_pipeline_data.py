#!/usr/bin/env python3
"""Clean and summarize the aggregated Reddit pipeline results."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean pipeline_results.json and report duplicate post IDs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("pipeline_results/pipeline_results.json"),
        help="Aggregated pipeline data file to clean.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("pipeline_results/pipeline_results.cleaned.json"),
        help="Path to write the cleaned payload (ignored when --in-place is set).",
    )
    parser.add_argument(
        "--per-post-dir",
        type=Path,
        default=Path("pipeline_results"),
        help="Directory that contains the per-post JSON exports.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file with cleaned data instead of writing to --output.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only show the summary report without writing a cleaned file.",
    )
    parser.add_argument(
        "--text-output",
        type=Path,
        default=Path("pipeline_results/pipeline_results.cleaned.flat.json"),
        help="Path for the flattened text-only dataset produced after cleaning.",
    )
    return parser.parse_args()


def load_json(filepath: Path) -> Dict[str, Any]:
    with filepath.open(encoding="utf-8") as fh:
        return json.load(fh)


def atomic_write(filepath: Path, payload: Dict[str, Any]) -> None:
    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    tmp_path.replace(filepath)


def rebuild_order(posts: Dict[str, Any], order: Iterable[str]) -> List[str]:
    seen = set()
    cleaned_order = []
    for post_id in order:
        if post_id in posts and post_id not in seen:
            cleaned_order.append(post_id)
            seen.add(post_id)
    extras = sorted(pid for pid in posts if pid not in seen)
    cleaned_order.extend(extras)
    return cleaned_order


def summarize_statuses(posts: Dict[str, Any]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for post in posts.values():
        counter[post.get("status", "unknown")] += 1
    return counter


def detect_order_duplicates(order: Iterable[str]) -> Dict[str, int]:
    counts = Counter(order)
    return {pid: count for pid, count in counts.items() if count > 1}


def scan_per_post_files(
    directory: Path, exclude: Iterable[str]
) -> Dict[str, List[Path]]:
    duplicates: Dict[str, List[Path]] = {}
    mapping: Dict[str, List[Path]] = {}
    for candidate in sorted(directory.glob("*.json")):
        if candidate.name in exclude or not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Warning: {candidate.name} is not valid JSON; skipping.")
            continue
        post_id = payload.get("post_id")
        if not post_id:
            continue
        mapping.setdefault(post_id, []).append(candidate)
    for pid, files in mapping.items():
        if len(files) > 1:
            duplicates[pid] = files
    return duplicates


def build_clean_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    posts = data.get("posts", {})
    order = data.get("order", [])
    cleaned_posts = {pid: posts[pid] for pid in posts if isinstance(pid, str)}
    cleaned_order = rebuild_order(cleaned_posts, order)
    metadata = dict(data.get("metadata", {}))
    metadata["total_posts"] = len(cleaned_posts)
    metadata["order_cleaned_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    chunk_ids = metadata.get("chunk_ids", [])
    if isinstance(chunk_ids, list):
        metadata["chunk_ids"] = sorted({_ for _ in chunk_ids if isinstance(_, int)})
    else:
        metadata["chunk_ids"] = []
    return {"metadata": metadata, "posts": cleaned_posts, "order": cleaned_order}


def normalize_path(path: str) -> str:
    if not path:
        return ""
    return str(Path(path).as_posix()).lower()


def text_from_extraction(extraction: Dict[str, Any]) -> str:
    if not extraction:
        return ""
    value = extraction.get("text")
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        lines = [line.strip() for line in value if isinstance(line, str) and line.strip()]
        if lines:
            return "\n".join(lines)
    lines = extraction.get("text_lines") or extraction.get("lines")
    if isinstance(lines, list):
        segments = []
        for line in lines:
            if isinstance(line, str):
                trimmed = line.strip()
                if trimmed:
                    segments.append(trimmed)
            elif isinstance(line, dict):
                line_text = line.get("text")
                if isinstance(line_text, str):
                    trimmed = line_text.strip()
                    if trimmed:
                        segments.append(trimmed)
        if segments:
            return "\n".join(segments)
    return ""


def aggregate_post_text(post: Dict[str, Any]) -> str:
    local_images = [
        item.get("local_path", "")
        for item in post.get("images", {}).get("local_images", [])
    ]
    ocr_entries = post.get("ocr", {}).get("image_results", [])
    path_index: defaultdict[str, List[Dict[str, Any]]] = defaultdict(list)
    name_index: defaultdict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in ocr_entries:
        file_path = entry.get("file_path", "")
        key = normalize_path(file_path)
        if key:
            path_index[key].append(entry)
        name = Path(file_path).name.lower()
        if name:
            name_index[name].append(entry)

    ordered_texts: List[str] = []

    def extract_next_entry(path_key: str, name_key: str | None) -> Dict[str, Any] | None:
        if path_key and path_index.get(path_key):
            return path_index[path_key].pop(0)
        if name_key and name_index.get(name_key):
            return name_index[name_key].pop(0)
        return None

    for local_path in local_images:
        key = normalize_path(local_path)
        name = Path(local_path).name.lower()
        entry = extract_next_entry(key, name)
        if entry:
            text = text_from_extraction(entry.get("extraction", {}))
            if text:
                ordered_texts.append(text)

    # Append any remaining OCR entries that were not matched via local_images order
    for entry_list in list(path_index.values()):
        while entry_list:
            entry = entry_list.pop(0)
            text = text_from_extraction(entry.get("extraction", {}))
            if text:
                ordered_texts.append(text)
    for entry_list in list(name_index.values()):
        while entry_list:
            entry = entry_list.pop(0)
            text = text_from_extraction(entry.get("extraction", {}))
            if text:
                ordered_texts.append(text)

    return "\n".join(ordered_texts)


def build_flat_posts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    posts = data.get("posts", {})
    ordered = data.get("order", [])
    seen = set()
    flat_list: List[Dict[str, Any]] = []

    def append_entry(pid: str, post: Dict[str, Any]) -> None:
        entry = {
            "post_id": pid,
            "title": post.get("title", ""),
            "status": post.get("status", ""),
            "correct_link": post.get("correct_link"),
            "ocr_text": aggregate_post_text(post),
        }
        flat_list.append(entry)

    for post_id in ordered:
        post = posts.get(post_id)
        if not post:
            continue
        seen.add(post_id)
        append_entry(post_id, post)
    for post_id, post in posts.items():
        if post_id in seen:
            continue
        append_entry(post_id, post)
    return flat_list



def print_summary(
    total: int,
    order_length: int,
    status_counts: Counter[str],
    order_dups: Dict[str, int],
    per_post_dups: Dict[str, List[Path]],
    flat_output: Path,
    flat_count: int,
) -> None:
    print(f"\nPipeline Data Summary")
    print(f"{'-'*22}")
    print(f"Total posts in payload : {total}")
    print(f"Order length           : {order_length}")
    print("Statuses:")
    for status, count in status_counts.most_common():
        print(f"  {status:15} {count}")
    if order_dups:
        print("\nOrder duplicates detected:")
        for pid, count in sorted(order_dups.items()):
            print(f"  {pid} (appears {count} times)")
    else:
        print("\nOrder duplicates detected: None")
    if per_post_dups:
        print("\nPer-post JSON duplicates:")
        for pid, paths in sorted(per_post_dups.items()):
            print(f"  {pid} ({len(paths)} files)")
            for path in paths:
                print(f"    - {path}")
    else:
        print("\nPer-post JSON duplicates: None")
    print(f"\nFlattened dataset entries: {flat_count}")
    print(f"Flattened dataset path   : {flat_output}")


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file {input_path} does not exist.")
    raw_data = load_json(input_path)
    cleaned_payload = build_clean_payload(raw_data)
    posts = cleaned_payload["posts"]
    order = cleaned_payload["order"]
    status_counts = summarize_statuses(posts)
    order_dups = detect_order_duplicates(raw_data.get("order", []))
    duplicate_files = scan_per_post_files(
        args.per_post_dir.resolve(),
        {input_path.name, args.output.name, args.text_output.name},
    )
    flat_entries = build_flat_posts(cleaned_payload)
    print_summary(
        len(posts),
        len(order),
        status_counts,
        order_dups,
        duplicate_files,
        args.text_output,
        len(flat_entries),
    )
    if args.report_only:
        return
    target_path = input_path if args.in_place else args.output.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(target_path, cleaned_payload)
    print(f"\nCleaned payload written to: {target_path}")
    flat_payload = {
        "metadata": {
            "source": input_path.name,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_posts": len(flat_entries),
        },
        "posts": flat_entries,
    }
    flat_path = args.text_output.resolve()
    flat_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(flat_path, flat_payload)
    print(f"Flattened dataset written to: {flat_path}")


if __name__ == "__main__":
    main()

