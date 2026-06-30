#!/usr/bin/env python
"""
Image → AI Analysis → Obsidian Note

Reads an image, sends it to DeepSeek VL2 for analysis,
generates a structured note and saves to Obsidian vault.

Usage:
    python img2note.py f:/Screenshots/photo.png
    python img2note.py --batch f:/Screenshots/
"""
import os
import sys
import json
import base64
import time
import httpx

# Config
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", ""))
DEEPSEEK_BASE = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"  # DeepSeek V3 supports vision via this endpoint
OBSIDIAN_VAULT = "f:/Knowledge"

CATEGORY_MAP = {
    "ai": "3-Resources/AI",
    "programming": "3-Resources/编程",
    "design": "3-Resources/产品设计",
    "life": "2-Areas",
    "learning": "3-Resources/读书笔记",
    "project": "1-Projects/MiniShop",
    "health": "2-Areas/健康",
    "finance": "2-Areas/财务",
}


def image_to_base64(filepath: str) -> str:
    """Read image file and encode as base64 data URL."""
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(filepath)[1].lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{data}"


def analyze_image(image_path: str) -> dict:
    """Send image to DeepSeek API and get structured analysis."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set")

    image_url = image_to_base64(image_path)

    prompt = """Analyze this image and output ONLY valid JSON (no markdown, no explanations):

{
  "title": "A concise Chinese title for this image (max 30 chars)",
  "summary": "A 2-3 sentence Chinese summary of what this image shows",
  "category": "ai | programming | design | life | learning | project | health | finance",
  "tags": ["tag1", "tag2", "tag3"],
  "key_points": ["point 1", "point 2", "point 3"],
  "action_items": ["optional action item 1"]
}

Choose the category that best fits the image content."""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1000,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{DEEPSEEK_BASE}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        print(f"API Error: {e}")
        if resp:
            print(f"Response: {resp.text[:300]}")
        raise

    content = data["choices"][0]["message"]["content"]
    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("\n", 1)[0]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON from: {content[:200]}")
        raise


def save_to_obsidian(result: dict, source_image: str = "") -> str:
    """Write analysis result to Obsidian vault with frontmatter."""
    category = result.get("category", "learning")
    folder = CATEGORY_MAP.get(category, "0-Inbox")
    full_dir = os.path.join(OBSIDIAN_VAULT, folder)
    os.makedirs(full_dir, exist_ok=True)

    # Sanitize filename
    title = result.get("title", "未命名")
    safe_title = title.replace("/", "-").replace("\\", "-").replace(":", "：")
    filename = f"{safe_title}.md"
    filepath = os.path.join(full_dir, filename)

    # Avoid overwrite
    if os.path.exists(filepath):
        filename = f"{safe_title}-{int(time.time())}.md"
        filepath = os.path.join(full_dir, filename)

    # Build note
    tags_str = ", ".join(result.get("tags", []))
    key_points = "\n".join(f"- {p}" for p in result.get("key_points", []))
    action_items = "\n".join(f"- [ ] {a}" for a in result.get("action_items", []))
    image_ref = f"\n![image]({source_image})\n" if source_image else ""

    note = f"""---
created: {time.strftime('%Y-%m-%d')}
tags: [{tags_str}]
source: {source_image or 'image'}
category: {category}
---

# {title}

{image_ref}

## 摘要

{result.get('summary', '')}

## 要点

{key_points}

## 行动

{action_items}

## 相关链接

- [[AI开发]] | [[MiniShop]]
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(note)

    return filepath


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Image → Obsidian Note")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--batch", metavar="DIR", help="Process all images in directory")
    args = parser.parse_args()

    if args.batch:
        images = [os.path.join(args.batch, f) for f in os.listdir(args.batch)
                  if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))]
        print(f"Processing {len(images)} images...")
        for i, img in enumerate(images, 1):
            print(f"[{i}/{len(images)}] {os.path.basename(img)}")
            try:
                result = analyze_image(img)
                path = save_to_obsidian(result, img)
                print(f"  -> {path}")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(1)  # Rate limit
    else:
        print(f"Analyzing: {args.image}")
        result = analyze_image(args.image)
        path = save_to_obsidian(result, args.image)
        print(f"Saved: {path}")
        print(f"Title: {result.get('title')}")
        print(f"Category: {result.get('category')}")
