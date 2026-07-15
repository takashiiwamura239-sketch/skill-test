#!/usr/bin/env python3
"""
Social media content agent powered by Claude.

Reads the reference library and helps generate new content
that matches the user's established writing style.

Usage:
    python agent/agent.py --prompt "写一篇关于旅行的小红书文案"
    python agent/agent.py --interactive
"""

import json
import argparse
from pathlib import Path

import anthropic

LIBRARY_FILE = Path("library/knowledge_base.json")
MODEL = "claude-sonnet-5"


def load_library() -> dict:
    if not LIBRARY_FILE.exists():
        return {}
    return json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))


def build_system_prompt(library: dict) -> str:
    if not library or not library.get("posts"):
        return (
            "你是一个专业的自媒体文案助手，帮助用户创作吸引人的社交媒体内容。"
        )

    posts = list(library["posts"].values())
    stats = library.get("stats", {})

    examples = "\n\n---\n\n".join(
        f"平台: {p.get('platform', '未知')}\n"
        f"标题: {p.get('title', '')}\n"
        f"标签: {', '.join(p.get('tags', []))}\n\n"
        f"{p.get('content', '')}"
        for p in posts[:10]  # Use up to 10 recent posts as examples
    )

    return f"""你是一个专业的自媒体文案助手，深度了解该用户的创作风格。

## 用户的参考文案库

共收录 {stats.get('total_posts', 0)} 篇文案。
常用平台：{json.dumps(stats.get('platforms', {}), ensure_ascii=False)}
常用标签：{json.dumps(stats.get('tags', {}), ensure_ascii=False)}

## 历史文案示例

{examples}

## 你的任务

根据以上参考文案，学习并模仿用户的写作风格（语气、排版、emoji使用习惯、互动方式等），
帮助用户创作新的自媒体文案。创作时：
1. 保持与用户一致的语气和风格
2. 合理使用 emoji 和排版
3. 加入互动引导（如提问、抽奖、评论引导）
4. 根据目标平台调整内容长度和格式
"""


def generate_content(prompt: str, system: str) -> str:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def interactive_mode(system: str):
    print("智能体已启动（输入 'quit' 退出）\n")
    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            break

        if user_input.lower() in ("quit", "exit", "退出"):
            print("退出。")
            break

        if not user_input:
            continue

        print("\n智能体: ", end="", flush=True)
        result = generate_content(user_input, system)
        print(result)
        print()


def main():
    parser = argparse.ArgumentParser(description="自媒体文案智能体")
    parser.add_argument("--prompt", type=str, help="生成内容的提示词")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    args = parser.parse_args()

    library = load_library()
    system = build_system_prompt(library)

    post_count = library.get("stats", {}).get("total_posts", 0)
    print(f"参考库已加载：{post_count} 篇文案\n")

    if args.interactive:
        interactive_mode(system)
    elif args.prompt:
        result = generate_content(args.prompt, system)
        print(result)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
