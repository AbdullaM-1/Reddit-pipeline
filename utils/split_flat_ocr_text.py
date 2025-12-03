#!/usr/bin/env python
"""
Split the flattened pipeline results JSON into two files based on OCR presence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Tuple


def load_flat_data(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def partition_entries(
    entries: Iterable[dict],
) -> Tuple[list[dict], list[dict]]:
    with_ocr: list[dict] = []
    without_ocr: list[dict] = []

    for entry in entries:
        text = entry.get("ocr_text")
        if isinstance(text, str) and text.strip():
            with_ocr.append(entry)
        else:
            without_ocr.append(entry)

    return with_ocr, without_ocr


def write_partition(
    entries: Iterable[dict],
    metadata: dict,
    path: Path,
) -> None:
    payload = {
        "metadata": {
            **metadata,
            "generated_from": str(path),
            "total_posts": len(entries),
        },
        "posts": list(entries),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"Written {path} ({len(entries)} entries)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split flattened pipeline results into OCR / non-OCR files."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the flattened JSON to split.",
    )
    parser.add_argument(
        "--with-ocr",
        type=Path,
        default=Path("pipeline_results/pipeline_results_merged.cleaned.flat.with_ocr.json"),
        help="Output file path for entries that contain ocr_text.",
    )
    parser.add_argument(
        "--without-ocr",
        type=Path,
        default=Path("pipeline_results/pipeline_results_merged.cleaned.flat.no_ocr.json"),
        help="Output file path for entries that do not contain ocr_text.",
    )

    args = parser.parse_args()

    data = load_flat_data(args.input)
    entries = data.get("posts", [])
    metadata = data.get("metadata", {})
    with_ocr, without_ocr = partition_entries(entries)

    write_partition(with_ocr, metadata, args.with_ocr)
    write_partition(without_ocr, metadata, args.without_ocr)


if __name__ == "__main__":
    main()


