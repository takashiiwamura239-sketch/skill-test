#!/usr/bin/env python3
"""
Sync social media content to the agent's reference library.

Usage:
    python sync.py                  # One-time sync
    python sync.py --watch          # Watch for changes and auto-sync
"""

import json
import re
import sys
import time
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

CONTENT_DIR = Path("content/posts")
LIBRARY_FILE = Path("library/knowledge_base.json")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-style frontmatter and return (metadata, body)."""
    meta = {}
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    value = value.strip()
                    # Parse list values like [a, b, c]
                    if value.startswith("[") and value.endswith("]"):
                        value = [v.strip() for v in value[1:-1].split(",")]
                    meta[key.strip()] = value
            body = parts[2].strip()

    return meta, body


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_library() -> dict:
    if LIBRARY_FILE.exists():
        return json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "last_synced": None,
        "posts": {},
        "stats": {
            "total_posts": 0,
            "platforms": {},
            "tags": {},
        },
    }


def save_library(library: dict):
    LIBRARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    library["last_synced"] = datetime.now().isoformat()
    LIBRARY_FILE.write_text(
        json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def rebuild_stats(library: dict):
    platforms: dict[str, int] = {}
    tags: dict[str, int] = {}

    for post in library["posts"].values():
        platform = post.get("platform", "未知")
        platforms[platform] = platforms.get(platform, 0) + 1

        for tag in post.get("tags", []):
            tags[tag] = tags.get(tag, 0) + 1

    library["stats"] = {
        "total_posts": len(library["posts"]),
        "platforms": platforms,
        "tags": tags,
    }


def sync_once(verbose: bool = True) -> int:
    """Sync all content files to the library. Returns number of changed files."""
    library = load_library()
    changed = 0

    md_files = list(CONTENT_DIR.glob("*.md")) if CONTENT_DIR.exists() else []

    # Track which files still exist
    existing_keys = set()

    for path in md_files:
        key = path.stem
        existing_keys.add(key)
        current_hash = file_hash(path)

        if library["posts"].get(key, {}).get("hash") == current_hash:
            continue  # unchanged

        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)

        library["posts"][key] = {
            "filename": path.name,
            "hash": current_hash,
            "platform": meta.get("platform", ""),
            "date": meta.get("date", ""),
            "tags": meta.get("tags", []),
            "title": meta.get("title", ""),
            "content": body,
            "synced_at": datetime.now().isoformat(),
        }

        changed += 1
        if verbose:
            print(f"  [updated] {path.name}")

    # Remove deleted files from library
    deleted_keys = set(library["posts"].keys()) - existing_keys
    for key in deleted_keys:
        del library["posts"][key]
        changed += 1
        if verbose:
            print(f"  [removed] {key}.md")

    rebuild_stats(library)
    save_library(library)

    if verbose:
        stats = library["stats"]
        print(f"\n参考库已更新: 共 {stats['total_posts']} 篇文案")
        print(f"平台分布: {stats['platforms']}")
        print(f"热门标签: {dict(sorted(stats['tags'].items(), key=lambda x: -x[1])[:5])}")

    return changed


def watch(interval: int = 5):
    """Watch content directory and sync on changes."""
    print(f"监听模式启动，每 {interval} 秒检查一次文件变化...")
    print(f"内容目录: {CONTENT_DIR.resolve()}")
    print("按 Ctrl+C 停止\n")

    last_state: dict[str, str] = {}

    while True:
        try:
            current_state = {
                str(p): file_hash(p)
                for p in CONTENT_DIR.glob("*.md")
                if CONTENT_DIR.exists()
            }

            if current_state != last_state:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 检测到文件变化，同步中...")
                sync_once(verbose=True)
                last_state = current_state

            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n监听已停止。")
            break


def main():
    parser = argparse.ArgumentParser(description="同步自媒体文案到智能体参考库")
    parser.add_argument(
        "--watch", action="store_true", help="监听模式：自动检测文件变化并同步"
    )
    parser.add_argument(
        "--interval", type=int, default=5, help="监听间隔（秒），默认 5 秒"
    )
    args = parser.parse_args()

    if args.watch:
        watch(interval=args.interval)
    else:
        print("开始同步自媒体文案到参考库...")
        changed = sync_once()
        if changed == 0:
            print("无变化，参考库已是最新。")


if __name__ == "__main__":
    main()
