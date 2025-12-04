# Pipeline Results Database Schema

This document describes the schema for posts stored in `pipeline_results/pipeline_results.json`.

## Overall Structure

The `pipeline_results.json` file has the following structure:

```json
{
  "metadata": {
    "total_posts": 1000,
    "last_updated": "2024-01-15T10:30:00Z",
    "chunk_ids": [1, 2, 3, ...]
  },
  "posts": {
    "post_id_1": { ... },
    "post_id_2": { ... },
    ...
  },
  "order": ["post_id_1", "post_id_2", ...]
}
```

### Top-Level Fields

- **`metadata`** (object): Metadata about the pipeline results
  - `total_posts` (integer): Total number of posts in the database
  - `last_updated` (string): ISO 8601 timestamp of last update
  - `chunk_ids` (array of integers): List of chunk IDs that have been created

- **`posts`** (object): Dictionary where keys are post IDs and values are post result objects
  - Key: Post ID (string, e.g., "abc123")
  - Value: Post result object (see schema below)

- **`order`** (array of strings): Ordered list of post IDs in the order they were processed

## Post Result Schema

Each post in the `posts` dictionary has the following structure:

```json
{
  "post_id": "abc123",
  "title": "Post Title",
  "status": "success",
  "correct_link": "https://example.com/story",
  "images": {
    "image_urls": ["https://example.com/img1.jpg", ...],
    "local_images": [
      {
        "url": "https://example.com/img1.jpg",
        "local_path": "downloaded_images/abc123/image_1.jpg"
      },
      ...
    ],
    "downloaded_count": 5
  },
  "ocr": {
    "images_processed": 5,
    "total_chars": 1250,
    "total_lines": 45,
    "image_results": [
      {
        "filename": "image_1.jpg",
        "file_path": "downloaded_images/abc123/image_1.jpg",
        "extraction": {
          "success": true,
          "text": "Extracted text from image...",
          "char_count": 250,
          "line_count": 9,
          "confidence": 0.95
        }
      },
      ...
    ]
  }
}
```

### Post Result Fields

#### Required Fields

- **`post_id`** (string): Reddit post ID (e.g., "abc123")
  - Used as the key to identify the post in the database
  - Must be unique

- **`title`** (string): Title of the Reddit post
  - Original post title from Reddit

- **`status`** (string): Processing status
  - Possible values:
    - `"started"`: Processing started but not completed
    - `"no_link"`: No link found in author's comment
    - `"no_images"`: No images downloaded
    - `"success"`: Successfully processed (has link, images, and OCR)

#### Optional Fields (depending on status)

- **`correct_link`** (string, optional): The identified correct outbound link from the author's comment
  - Present if status is not `"no_link"`
  - URL where images were extracted from

- **`images`** (object, optional): Image download results
  - Present if status is not `"no_link"`
  - Fields:
    - `image_urls` (array of strings): All image URLs found at the link
    - `local_images` (array of objects): Successfully downloaded images
      - Each object has:
        - `url` (string): Original image URL
        - `local_path` (string): Local file path relative to project root
    - `downloaded_count` (integer): Number of successfully downloaded images

- **`ocr`** (object, optional): OCR processing results
  - Present if status is `"success"` (has images)
  - Fields:
    - `images_processed` (integer): Number of images processed by OCR
    - `total_chars` (integer): Total characters extracted from all images
    - `total_lines` (integer): Total lines extracted from all images
    - `image_results` (array of objects): OCR results for each image
      - Each object has:
        - `filename` (string): Image filename
        - `file_path` (string): Full path to the image file
        - `extraction` (object): OCR extraction result
          - `success` (boolean): Whether OCR was successful
          - `text` (string, optional): Extracted text (if successful)
          - `char_count` (integer, optional): Character count (if successful)
          - `line_count` (integer, optional): Line count (if successful)
          - `confidence` (number, optional): OCR confidence score (0-1, if available)
          - `error` (string, optional): Error message (if not successful)

## Status Flow

The status field indicates how far the post processing got:

1. **`"started"`**: Initial state when processing begins
2. **`"no_link"`**: Could not identify the correct link from author's comment
3. **`"no_images"`**: Link found but no images could be downloaded
4. **`"success"`**: Complete processing - has link, images, and OCR results

## Example: Complete Post Object

```json
{
  "post_id": "1p2pj2j",
  "title": "My amazing story part 1",
  "status": "success",
  "correct_link": "https://example.com/story/part1",
  "images": {
    "image_urls": [
      "https://example.com/story/part1/img1.png",
      "https://example.com/story/part1/img2.png"
    ],
    "local_images": [
      {
        "url": "https://example.com/story/part1/img1.png",
        "local_path": "downloaded_images/1p2pj2j/img1.png"
      },
      {
        "url": "https://example.com/story/part1/img2.png",
        "local_path": "downloaded_images/1p2pj2j/img2.png"
      }
    ],
    "downloaded_count": 2
  },
  "ocr": {
    "images_processed": 2,
    "total_chars": 3500,
    "total_lines": 120,
    "image_results": [
      {
        "filename": "img1.png",
        "file_path": "downloaded_images/1p2pj2j/img1.png",
        "extraction": {
          "success": true,
          "text": "Once upon a time...",
          "char_count": 1750,
          "line_count": 60,
          "confidence": 0.92
        }
      },
      {
        "filename": "img2.png",
        "file_path": "downloaded_images/1p2pj2j/img2.png",
        "extraction": {
          "success": true,
          "text": "And then...",
          "char_count": 1750,
          "line_count": 60,
          "confidence": 0.89
        }
      }
    ]
  }
}
```

## Integration with `posts.json`

The pipeline also checks `posts.json` (from the main `run.py` script) for existing post IDs. The schema for `posts.json` is different:

- **File**: `posts.json`
- **Format**: Array of post objects
- **Post Object**: Full Reddit post data with fields:
  - `id` (string): Post ID
  - `title` (string): Post title
  - `subreddit` (string): Subreddit name
  - `author` (string): Author username
  - `comments` (array): Array of comment objects
  - `media_content` (object): Media content object
  - ... (see `posts.py` Post TypedDict for complete schema)

The pipeline uses the `id` field from `posts.json` to check if a post already exists.

## Database Location

- **Main file**: `pipeline_results/pipeline_results.json`
- **Chunks**: `pipeline_results/chunks/pipeline_results_chunk_0001.json`, etc.
- **Images**: `downloaded_images/{post_id}/image_1.jpg`, etc.

