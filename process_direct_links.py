#!/usr/bin/env python
"""
Direct Link Processor - Process links directly without Reddit fetching
Downloads images and runs OCR on them.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any
from colorama import Fore, Style

# Import existing functions
from extract_images_from_links import (
    extract_images_from_url,
    download_image,
    sanitize_filename,
    get_session,
)
from extract_text_from_images import (
    extract_text_from_image_easyocr,
    extract_text_from_image_pytesseract,
    should_skip_image,
)

# Try to import OCR libraries
EASYOCR_AVAILABLE = False
PYTESSERACT_AVAILABLE = False
easyocr = None
pytesseract = None
Image = None

try:
    import easyocr
    # Test if it actually works (not just imports)
    try:
        test_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        EASYOCR_AVAILABLE = True
        del test_reader  # Clean up test reader
    except Exception as e:
        print(f"{Fore.YELLOW}EasyOCR import succeeded but initialization failed: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Falling back to pytesseract...{Style.RESET_ALL}")
        EASYOCR_AVAILABLE = False
except Exception as e:
    print(f"{Fore.YELLOW}EasyOCR not available: {e}{Style.RESET_ALL}")

# Try pytesseract if EasyOCR failed
if not EASYOCR_AVAILABLE:
    try:
        import pytesseract
        from PIL import Image
        PYTESSERACT_AVAILABLE = True
    except ImportError:
        pass

# Configuration
IMAGES_DIR = Path("downloaded_images")
OUTPUT_DIR = Path("direct_link_results")
OUTPUT_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# Links to process
LINKS_TO_PROCESS = [
    {
        "title": "The Sext Search Engine Part 1",
        "url": "https://imgchest.com/p/9p4nzndmz4n"
    },
    {
        "title": "The SextSearch Engine Part 2",
        "url": "https://imgchest.com/p/m9yxnrmk37q"
    },
    {
        "title": "The SextSearch Engine Part 3",
        "url": "https://imgchest.com/p/o24a6qa82yl"
    }
]


def init_ocr_reader():
    """Initialize EasyOCR reader if available"""
    if not EASYOCR_AVAILABLE:
        return None
    try:
        print(f"{Fore.CYAN}Initializing EasyOCR (CPU)...{Style.RESET_ALL}")
        return easyocr.Reader(["en"], gpu=False, verbose=False)
    except Exception as err:
        print(f"{Fore.YELLOW}EasyOCR init failed: {err}{Style.RESET_ALL}")
        return None


def ensure_pytesseract_ready() -> bool:
    """Make sure pytesseract can find the native tesseract binary"""
    if not PYTESSERACT_AVAILABLE or pytesseract is None:
        return False
    
    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    
    current_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "")
    if current_cmd and os.path.exists(current_cmd):
        return True
    
    for candidate in candidate_paths:
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            print(f"{Fore.GREEN}Using Tesseract at: {candidate}{Style.RESET_ALL}")
            return True
    
    print(f"{Fore.YELLOW}Tesseract executable not found.{Style.RESET_ALL}")
    return False


def process_link(link_data: Dict[str, str], reader: Any, session) -> Dict[str, Any]:
    """
    Process a single link: download images and run OCR
    
    Args:
        link_data: Dictionary with 'title' and 'url'
        reader: EasyOCR reader instance (or None)
        session: Requests session
    
    Returns:
        Dictionary with processing results
    """
    title = link_data["title"]
    url = link_data["url"]
    
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Processing: {title}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}URL: {url}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    result = {
        "title": title,
        "url": url,
        "status": "started",
        "images": {
            "image_urls": [],
            "local_images": [],
            "downloaded_count": 0
        },
        "ocr": {
            "images_processed": 0,
            "total_chars": 0,
            "total_lines": 0,
            "image_results": []
        }
    }
    
    # Step 1: Extract image URLs
    print(f"{Fore.CYAN}Step 1: Extracting image URLs...{Style.RESET_ALL}")
    image_urls = extract_images_from_url(url, session)
    result["images"]["image_urls"] = image_urls
    
    if not image_urls:
        result["status"] = "no_images"
        print(f"{Fore.YELLOW}No images found at this URL{Style.RESET_ALL}")
        return result
    
    print(f"{Fore.GREEN}Found {len(image_urls)} image URLs{Style.RESET_ALL}")
    
    # Step 2: Download images
    print(f"\n{Fore.CYAN}Step 2: Downloading images...{Style.RESET_ALL}")
    link_id = sanitize_filename(url.split('/')[-1])
    post_dir = IMAGES_DIR / link_id
    post_dir.mkdir(parents=True, exist_ok=True)
    
    local_images = []
    for idx, img_url in enumerate(image_urls, 1):
        filename = sanitize_filename(Path(img_url).name) or f"image_{idx}"
        save_path = post_dir / filename
        
        # Ensure unique filename
        counter = 1
        while save_path.exists():
            save_path = post_dir / f"{save_path.stem}_{counter}{save_path.suffix}"
            counter += 1
        
        print(f"  [{idx}/{len(image_urls)}] Downloading: {save_path.name}...")
        if download_image(img_url, str(save_path), session):
            local_images.append({
                "url": img_url,
                "local_path": str(save_path),
            })
            print(f"    {Fore.GREEN}✓ Saved{Style.RESET_ALL}")
        else:
            print(f"    {Fore.YELLOW}✗ Failed{Style.RESET_ALL}")
        
        time.sleep(0.5)  # Small delay between downloads
    
    result["images"]["local_images"] = local_images
    result["images"]["downloaded_count"] = len(local_images)
    
    if not local_images:
        result["status"] = "download_failed"
        print(f"{Fore.YELLOW}Failed to download any images{Style.RESET_ALL}")
        return result
    
    print(f"{Fore.GREEN}Downloaded {len(local_images)} images{Style.RESET_ALL}")
    
    # Step 3: Run OCR
    print(f"\n{Fore.CYAN}Step 3: Running OCR on images...{Style.RESET_ALL}")
    ocr_results = []
    total_chars = 0
    total_lines = 0
    
    for img_data in local_images:
        image_path = img_data["local_path"]
        filename = os.path.basename(image_path)
        
        if should_skip_image(filename):
            print(f"  {Fore.YELLOW}Skipping: {filename} (icon/favicon){Style.RESET_ALL}")
            continue
        
        print(f"  Processing: {filename}...")
        
        # Run OCR
        if reader:
            extraction = extract_text_from_image_easyocr(image_path, reader)
        elif PYTESSERACT_AVAILABLE:
            ensure_pytesseract_ready()
            extraction = extract_text_from_image_pytesseract(image_path)
        else:
            extraction = {"success": False, "error": "No OCR backend available"}
        
        if extraction.get("success"):
            total_chars += extraction.get("char_count", 0)
            total_lines += extraction.get("line_count", 0)
            print(f"    {Fore.GREEN}✓ Extracted {extraction.get('char_count', 0)} chars, {extraction.get('line_count', 0)} lines{Style.RESET_ALL}")
        else:
            print(f"    {Fore.YELLOW}✗ OCR failed: {extraction.get('error', 'Unknown error')}{Style.RESET_ALL}")
        
        ocr_results.append({
            "filename": filename,
            "file_path": image_path,
            "extraction": extraction,
        })
    
    result["ocr"]["image_results"] = ocr_results
    result["ocr"]["images_processed"] = len(ocr_results)
    result["ocr"]["total_chars"] = total_chars
    result["ocr"]["total_lines"] = total_lines
    result["status"] = "success"
    
    print(f"\n{Fore.GREEN}OCR Summary: {len(ocr_results)} images, {total_lines} lines, {total_chars} chars{Style.RESET_ALL}")
    
    return result


def aggregate_text(result: Dict[str, Any]) -> str:
    """Aggregate all OCR text from a result"""
    texts = []
    for img_result in result.get("ocr", {}).get("image_results", []):
        extraction = img_result.get("extraction", {})
        if extraction.get("success"):
            text = extraction.get("text", "")
            if text:
                texts.append(text)
    return "\n\n".join(texts)


def main():
    """Main processing function"""
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Direct Link Processor{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Processing {len(LINKS_TO_PROCESS)} links{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # Initialize OCR
    reader = init_ocr_reader()
    if not reader and not PYTESSERACT_AVAILABLE:
        print(f"{Fore.RED}ERROR: No OCR backend available!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Install EasyOCR: pip install easyocr{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Or install pytesseract: pip install pytesseract{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Note: pytesseract also requires Tesseract OCR binary installed{Style.RESET_ALL}")
        return
    
    if reader:
        print(f"{Fore.GREEN}Using EasyOCR for text extraction{Style.RESET_ALL}")
    elif PYTESSERACT_AVAILABLE:
        print(f"{Fore.GREEN}Using pytesseract for text extraction{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Note: Make sure Tesseract OCR is installed on your system{Style.RESET_ALL}")
    
    # Create session
    session = get_session()
    
    # Process each link
    all_results = []
    for link_data in LINKS_TO_PROCESS:
        result = process_link(link_data, reader, session)
        all_results.append(result)
        time.sleep(1)  # Delay between links
    
    # Save results
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Saving results...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # Save individual results
    for result in all_results:
        link_id = sanitize_filename(result["url"].split('/')[-1])
        output_file = OUTPUT_DIR / f"{link_id}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"{Fore.GREEN}Saved: {output_file}{Style.RESET_ALL}")
    
    # Save aggregated results
    aggregated_file = OUTPUT_DIR / "all_results.json"
    with open(aggregated_file, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "total_links": len(LINKS_TO_PROCESS),
            },
            "results": all_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"{Fore.GREEN}Saved aggregated results: {aggregated_file}{Style.RESET_ALL}")
    
    # Create text-only files
    print(f"\n{Fore.CYAN}Creating text-only files...{Style.RESET_ALL}")
    for result in all_results:
        link_id = sanitize_filename(result["url"].split('/')[-1])
        text_file = OUTPUT_DIR / f"{link_id}.txt"
        
        text = aggregate_text(result)
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"Title: {result['title']}\n")
            f.write(f"URL: {result['url']}\n")
            f.write(f"{'='*60}\n\n")
            f.write(text)
        
        print(f"{Fore.GREEN}Saved text: {text_file}{Style.RESET_ALL}")
    
    # Summary
    print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Processing Complete!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
    
    total_images = sum(r["images"]["downloaded_count"] for r in all_results)
    total_chars = sum(r["ocr"]["total_chars"] for r in all_results)
    
    print(f"Total links processed: {len(all_results)}")
    print(f"Total images downloaded: {total_images}")
    print(f"Total characters extracted: {total_chars}")
    print(f"\nResults saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

