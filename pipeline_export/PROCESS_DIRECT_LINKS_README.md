# Process Direct Links - Quick Guide

This script processes links directly without needing Reddit fetching or link identification.

## What It Does

1. **Downloads images** from the provided links
2. **Runs OCR** on all downloaded images
3. **Saves results** in JSON and text formats

## Usage

### Basic Usage

```bash
python3 process_direct_links.py
```

The script is pre-configured with these 3 links:
- The Sext Search Engine Part 1: https://imgchest.com/p/9p4nzndmz4n
- The SextSearch Engine Part 2: https://imgchest.com/p/m9yxnrmk37q
- The SextSearch Engine Part 3: https://imgchest.com/p/o24a6qa82yl

### Customize Links

Edit the `LINKS_TO_PROCESS` list in the script:

```python
LINKS_TO_PROCESS = [
    {
        "title": "Your Title Here",
        "url": "https://imgchest.com/p/your-link-id"
    },
    # Add more links...
]
```

## Output

The script creates:

1. **Individual JSON files** (`direct_link_results/{link_id}.json`)
   - Contains all metadata, image URLs, local paths, and OCR results

2. **Text files** (`direct_link_results/{link_id}.txt`)
   - Plain text extracted from all images

3. **Aggregated results** (`direct_link_results/all_results.json`)
   - All results in one file

## Requirements

- Python 3.9+
- EasyOCR or pytesseract (for OCR)
- Dependencies from `requirements.txt`

## Example Output Structure

```
direct_link_results/
├── 9p4nzndmz4n.json      # Part 1 results
├── 9p4nzndmz4n.txt       # Part 1 text
├── m9yxnrmk37q.json      # Part 2 results
├── m9yxnrmk37q.txt       # Part 2 text
├── o24a6qa82yl.json      # Part 3 results
├── o24a6qa82yl.txt       # Part 3 text
└── all_results.json      # All results combined
```

## Notes

- Images are downloaded to `downloaded_images/{link_id}/`
- The script automatically skips favicons and small icons
- OCR uses EasyOCR if available, falls back to pytesseract
- Processing happens sequentially (one link at a time)

